"""Load test for STT service — /recognize endpoint.

Sends pre-generated int32 mono 8 kHz audio to /recognize and measures
response time, throughput, and error rate at up to 100 concurrent users.

The T-one pipeline is single-threaded (asyncio.to_thread serialises inference),
so requests queue up under load. p95/p99 growth directly reflects queue depth.
The client-side timeout in stt_tone.py is 30 s; errors spike when that is hit.

Run headless (via docker compose):
    docker compose up --abort-on-container-exit

Run with the Locust web UI (against a locally running STT service):
    locust -f locustfile.py --host http://localhost:8001
"""
from __future__ import annotations

import numpy as np
from locust import HttpUser, between, task

# ---------------------------------------------------------------------------
# Test audio fixture — generated once at import time, reused across all workers
# ---------------------------------------------------------------------------
_SAMPLE_RATE = 8_000      # T-one expects 8 kHz
_DURATION_SEC = 2         # 2 s ≈ real VAD-split utterance (stt_tone.py splits on silence)
_N_SAMPLES = _SAMPLE_RATE * _DURATION_SEC

_rng = np.random.default_rng(seed=42)
_t = np.arange(_N_SAMPLES, dtype=np.float32) / _SAMPLE_RATE
# Low-frequency carrier (200 Hz) + white noise → speech-like amplitude envelope
_carrier = np.sin(2 * np.pi * 200 * _t)
_noise = _rng.standard_normal(_N_SAMPLES).astype(np.float32)
_signal = 0.7 * _carrier + 0.3 * _noise
TEST_AUDIO_BYTES: bytes = (_signal * 8_000).astype(np.int32).tobytes()


# ---------------------------------------------------------------------------
# Locust user
# ---------------------------------------------------------------------------
class STTUser(HttpUser):
    """Simulates a single agent sending one audio chunk per turn."""

    # Realistic inter-request pause: agent speaks, then waits 1–3 s before next turn
    wait_time = between(1, 3)

    @task(9)
    def recognize(self) -> None:
        """Main load: POST audio bytes to /recognize."""
        with self.client.post(
            "/recognize",
            data=TEST_AUDIO_BYTES,
            headers={"Content-Type": "application/octet-stream"},
            name="/recognize",
            catch_response=True,
        ) as response:
            if response.status_code == 200:
                response.success()
            elif response.status_code == 503:
                response.failure("STT pipeline not ready (503)")
            else:
                response.failure(
                    f"Unexpected {response.status_code}: {response.text[:120]}"
                )

    @task(1)
    def health(self) -> None:
        """Low-frequency health check — baseline for connectivity errors."""
        self.client.get("/health", name="/health")
