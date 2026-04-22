"""E2E load test for ozon_ai_call_simulator.

Simulates three concurrent workloads in a single run:

  BackendApiUser  (weight 3) — auth + CRUD  (backend_service:8004)
  AgentTurnUser   (weight 6) — STT → LLM → TTS pipeline
  JudgeUser       (weight 1) — post-call evaluation (judge_service:8003)

Each class reads its target URL from environment variables so the
docker-compose can wire services together without touching this file.

LLM step in AgentTurnUser is optional: if LLM_API_KEY is empty the
step is skipped and a fixed reply phrase is synthesised instead.
This lets you benchmark STT+TTS throughput without incurring API cost.

Run with the Locust web UI (all services must be reachable):
    locust -f locustfile.py
"""
from __future__ import annotations

import os
import random
import time

import numpy as np
import requests as _req
from locust import HttpUser, between, task

# ---------------------------------------------------------------------------
# Service URLs — set by docker-compose; fall back to local defaults
# ---------------------------------------------------------------------------
STT_URL = os.getenv("STT_URL", "http://localhost:8001")
TTS_URL = os.getenv("TTS_URL", "http://localhost:8002")
BACKEND_URL = os.getenv("BACKEND_URL", "http://localhost:8004")
JUDGE_URL = os.getenv("JUDGE_URL", "http://localhost:8003")

LLM_BASE_URL = os.getenv("LLM_BASE_URL", "https://openrouter.ai/api/v1")
LLM_API_KEY = os.getenv("LLM_API_KEY", "")
LLM_MODEL = os.getenv("LLM_MODEL", "openai/gpt-4o-mini")

# Seeded test credentials (added by seed_test_data.sql)
TEST_EMAIL = os.getenv("TEST_EMAIL", "loadtest@example.com")
TEST_PASSWORD = os.getenv("TEST_PASSWORD", "testpass123")

# Pre-seeded session IDs for judge queries (comma-separated env var)
_raw_ids = os.getenv("TEST_SESSION_IDS", "")
TEST_SESSION_IDS: list[str] = [s.strip() for s in _raw_ids.split(",") if s.strip()]

# ---------------------------------------------------------------------------
# Synthetic audio fixture: 2 s, 8 kHz, int32 — matches real VAD-split chunks
# ---------------------------------------------------------------------------
_rng = np.random.default_rng(42)
_SAMPLE_RATE = 8_000
_N_SAMPLES = _SAMPLE_RATE * 2
_t = np.arange(_N_SAMPLES, dtype=np.float32) / _SAMPLE_RATE
_signal = 0.7 * np.sin(2 * np.pi * 200 * _t) + 0.3 * _rng.standard_normal(_N_SAMPLES).astype(np.float32)
TEST_AUDIO_BYTES: bytes = (_signal * 8_000).astype(np.int32).tobytes()

# Short agent replies used when LLM step is skipped
_FALLBACK_REPLIES = [
    "Хорошо, понял вас. Подождите, пожалуйста.",
    "Да, конечно. Расчётный счёт открывается бесплатно.",
    "Спасибо за ваш звонок. Чем могу помочь?",
    "Переводы внутри банка мгновенные и без комиссии.",
    "Открытие счёта занимает около пяти минут. Вы уже зарегистрированы как ИП?",
]

# Single-sentence prompt sent to LLM when key is configured
_LLM_USER_PHRASE = "Расскажите об условиях открытия расчётного счёта для ИП в Озон Банке."


# ---------------------------------------------------------------------------
# Helper: fire a Locust request event for calls made outside self.client
# ---------------------------------------------------------------------------
def _fire(env, method: str, name: str, t0: float, resp=None, exc=None) -> None:
    env.events.request.fire(
        request_type=method,
        name=name,
        response_time=int((time.monotonic() - t0) * 1000),
        response_length=len(resp.content) if resp is not None else 0,
        exception=exc,
    )


# ---------------------------------------------------------------------------
# BackendApiUser — tests backend_service auth + CRUD layer
# ---------------------------------------------------------------------------
class BackendApiUser(HttpUser):
    """Simulates a manager browsing the web UI: login → sessions → scenarios."""

    weight = 3
    wait_time = between(1, 3)
    host = BACKEND_URL

    def on_start(self) -> None:
        resp = self.client.post(
            "/api/auth/login",
            json={"email": TEST_EMAIL, "password": TEST_PASSWORD},
            name="[backend] auth/login",
        )
        self._token = resp.json().get("access_token", "") if resp.status_code == 200 else ""

    def _headers(self) -> dict[str, str]:
        return {"Authorization": f"Bearer {self._token}"} if self._token else {}

    @task(3)
    def list_sessions(self) -> None:
        self.client.get("/api/sessions", headers=self._headers(), name="[backend] sessions/list")

    @task(2)
    def list_scenarios(self) -> None:
        self.client.get(
            "/api/training-scenarios",
            headers=self._headers(),
            name="[backend] scenarios/list",
        )

    @task(1)
    def health(self) -> None:
        self.client.get("/health", name="[backend] health")


# ---------------------------------------------------------------------------
# AgentTurnUser — simulates one agent turn: STT → LLM → TTS
# ---------------------------------------------------------------------------
class AgentTurnUser(HttpUser):
    """Simulates what agent_service does on each conversation turn.

    Primary self.client targets STT service (the first and slowest step).
    LLM and TTS are called via raw requests with manual event reporting
    so each step appears as a separate entry in the Locust stats table.
    """

    weight = 6
    wait_time = between(2, 5)
    host = STT_URL

    def on_start(self) -> None:
        self._tts = _req.Session()

        if LLM_API_KEY:
            self._llm: _req.Session | None = _req.Session()
            self._llm.headers.update(
                {
                    "Authorization": f"Bearer {LLM_API_KEY}",
                    "Content-Type": "application/json",
                }
            )
        else:
            self._llm = None

    @task(9)
    def agent_turn(self) -> None:
        # ── Step 1: STT ──────────────────────────────────────────────────
        with self.client.post(
            "/recognize",
            data=TEST_AUDIO_BYTES,
            headers={"Content-Type": "application/octet-stream"},
            name="[turn] 1_stt/recognize",
            catch_response=True,
        ) as stt_resp:
            if stt_resp.status_code != 200:
                stt_resp.failure(f"STT {stt_resp.status_code}: {stt_resp.text[:80]}")
                return
            stt_resp.success()
            transcript: str = stt_resp.json().get("text", "") or _LLM_USER_PHRASE

        # ── Step 2: LLM (optional) ────────────────────────────────────────
        if self._llm is not None:
            t0 = time.monotonic()
            try:
                llm_resp = self._llm.post(
                    f"{LLM_BASE_URL}/chat/completions",
                    json={
                        "model": LLM_MODEL,
                        "messages": [
                            {
                                "role": "system",
                                "content": (
                                    "Ты клиент Озон Банка. Отвечай одним коротким предложением."
                                ),
                            },
                            {"role": "user", "content": transcript},
                        ],
                        "max_tokens": 60,
                        "temperature": 0.3,
                    },
                    timeout=30,
                )
                reply_text: str = llm_resp.json()["choices"][0]["message"]["content"]
                _fire(self.environment, "POST", "[turn] 2_llm/chat", t0, llm_resp)
            except Exception as exc:
                _fire(self.environment, "POST", "[turn] 2_llm/chat", t0, exc=exc)
                return
        else:
            reply_text = random.choice(_FALLBACK_REPLIES)

        # ── Step 3: TTS ───────────────────────────────────────────────────
        t0 = time.monotonic()
        try:
            tts_resp = self._tts.post(
                f"{TTS_URL}/synthesize",
                json={"text": reply_text[:200], "speaker": "xenia", "sample_rate": 8000},
                timeout=30,
            )
            if tts_resp.status_code != 200:
                _fire(
                    self.environment,
                    "POST",
                    "[turn] 3_tts/synthesize",
                    t0,
                    exc=Exception(f"TTS {tts_resp.status_code}"),
                )
            else:
                _fire(self.environment, "POST", "[turn] 3_tts/synthesize", t0, tts_resp)
        except Exception as exc:
            _fire(self.environment, "POST", "[turn] 3_tts/synthesize", t0, exc=exc)

    @task(1)
    def stt_health(self) -> None:
        self.client.get("/health", name="[turn] stt/health")


# ---------------------------------------------------------------------------
# JudgeUser — tests judge_service post-call evaluation path
# ---------------------------------------------------------------------------
class JudgeUser(HttpUser):
    """Simulates the frontend polling for call results after a session ends.

    Targets judge_service directly (bypasses backend proxy) so we can
    measure judge_service latency in isolation.  Uses pre-seeded sessions
    from seed_test_data.sql with refresh=false to avoid re-triggering LLM.
    """

    weight = 1
    wait_time = between(5, 15)
    host = JUDGE_URL

    def on_start(self) -> None:
        self._ids = list(TEST_SESSION_IDS)

    @task(4)
    def get_session_results(self) -> None:
        if not self._ids:
            return
        session_id = random.choice(self._ids)
        with self.client.get(
            "/api/session-results",
            params={"session_id": session_id, "refresh": "false"},
            name="[judge] session-results",
            catch_response=True,
        ) as resp:
            if resp.status_code in (200, 404):
                resp.success()
            else:
                resp.failure(f"Unexpected {resp.status_code}: {resp.text[:80]}")

    @task(1)
    def health(self) -> None:
        self.client.get("/health", name="[judge] health")
