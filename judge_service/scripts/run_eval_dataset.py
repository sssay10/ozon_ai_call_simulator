#!/usr/bin/env python3
"""
Load eval_dataset/cases.json, insert dialogue_sessions + dialogue_messages like production,
run LLMJudge, upsert judge_results.

Usage (from judge_service/):
  uv run python scripts/run_eval_dataset.py
  uv run python scripts/run_eval_dataset.py --case strong_novice_l1
  uv run python scripts/run_eval_dataset.py --seed-only   # DB rows only, no LLM

Requires DATABASE_URL, and for judging: OPENROUTER_API_KEY or LLM_PROVIDER=ollama, etc.

Chroma (RAG): defaults from `chroma_script_defaults.py` are applied to CHROMA_HTTP_HOST / CHROMA_HTTP_PORT
unless already set (e.g. by Docker Compose). For host-side runs, point Chroma at 127.0.0.1:8005 by default.
"""

from __future__ import annotations

import argparse
import asyncio
import json
import logging
import os
import sys
import time
import uuid
from pathlib import Path
from typing import Any

# Repo layout: scripts/ lives next to main.py
_ROOT = Path(__file__).resolve().parents[1]
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

# Chroma for LLMJudge / RAG: same defaults as ingest (see chroma_script_defaults.py).
CHROMA_HOST = os.getenv("CHROMA_HTTP_HOST", "0.0.0.0")
CHROMA_PORT = os.getenv("CHROMA_HTTP_PORT", "8005")
os.environ.setdefault("CHROMA_HTTP_HOST", CHROMA_HOST)
os.environ.setdefault("CHROMA_HTTP_PORT", str(CHROMA_PORT))
os.environ.setdefault("JUDGE_SERVICE_ROOT", str(_ROOT))

from api.db import Database
from judge import LLMJudge
from judge.merged_evaluation import JudgeEvaluation

logging.basicConfig(level=logging.INFO, format="%(levelname)s %(name)s: %(message)s")
logger = logging.getLogger("run_eval_dataset")

SPEAKER_TO_DB_ROLE = {"manager": "user", "client": "assistant"}

DEFAULT_OWNER = os.getenv(
    "EVAL_OWNER_USER_ID",
    "00000000-0000-0000-0000-000000000101",
)


def _load_cases(path: Path) -> dict[str, Any]:
    with path.open(encoding="utf-8") as f:
        return json.load(f)


def _turns_to_db_messages(turns: list[dict[str, Any]]) -> list[tuple[str, str]]:
    out: list[tuple[str, str]] = []
    for t in turns:
        sp = t.get("speaker")
        text = (t.get("text") or "").strip()
        if sp not in SPEAKER_TO_DB_ROLE:
            raise ValueError(f"Invalid speaker {sp!r}")
        if not text:
            continue
        out.append((SPEAKER_TO_DB_ROLE[sp], text))
    if not out:
        raise ValueError("No non-empty turns")
    return out


async def _run() -> int:
    parser = argparse.ArgumentParser(description="Seed eval sessions and run judge")
    parser.add_argument(
        "--cases-file",
        type=Path,
        default=_ROOT / "eval_dataset" / "cases.json",
        help="Path to cases.json",
    )
    parser.add_argument("--case", type=str, default=None, help="Only run this case id")
    parser.add_argument(
        "--seed-only",
        action="store_true",
        help="Insert sessions/messages only; skip LLM and judge_results",
    )
    args = parser.parse_args()

    data = _load_cases(args.cases_file)
    cases: list[dict[str, Any]] = data.get("cases") or []
    if args.case:
        cases = [c for c in cases if c.get("id") == args.case]
        if not cases:
            logger.error("No case with id=%r", args.case)
            return 1

    logger.info(
        "run_eval_dataset: cases=%s seed_only=%s CHROMA_HTTP=%s:%s cases_file=%s",
        len(cases),
        args.seed_only,
        os.environ.get("CHROMA_HTTP_HOST"),
        os.environ.get("CHROMA_HTTP_PORT"),
        args.cases_file,
    )

    db = Database()
    await db.initialize()
    logger.info("run_eval_dataset: database pool ready")
    judge: LLMJudge | None = None
    if not args.seed_only:
        t_j = time.perf_counter()
        judge = LLMJudge()
        logger.info("run_eval_dataset: LLMJudge() init in %.2fs", time.perf_counter() - t_j)

    results_summary: list[dict[str, Any]] = []

    try:
        run_t0 = time.perf_counter()
        for case in cases:
            case_id = case.get("id", "unknown")
            case_t0 = time.perf_counter()
            ts_name = case.get("training_scenario_name")
            if not ts_name:
                logger.error("Case %s: missing training_scenario_name", case_id)
                return 1

            ts_uuid = await db.get_training_scenario_id_by_name(ts_name)
            if not ts_uuid:
                logger.error("Training scenario not found: %r", ts_name)
                return 1

            product = str(case.get("product") or "rko")
            room = f"eval-{case_id}-{uuid.uuid4().hex[:10]}"
            messages = _turns_to_db_messages(case.get("turns") or [])

            session_id = await db.insert_session_with_messages(
                room_name=room,
                product=product,
                owner_user_id=DEFAULT_OWNER,
                training_scenario_id=ts_uuid,
                messages=messages,
                job_id=f"eval:{case_id}",
            )
            logger.info("Inserted session %s case=%s room=%s", session_id, case_id, room)

            ctx = await db.get_session_context(session_id)
            if ctx is None:
                logger.error("get_session_context failed for %s", session_id)
                return 1

            transcript = await db.get_session_transcript(session_id)

            eval_payload: JudgeEvaluation | None = None
            if args.seed_only:
                pass
            else:
                assert judge is not None
                try:
                    eval_payload = await judge.evaluate(
                        persona_description=ctx["persona_description"],
                        scenario_description=ctx["scenario_description"],
                        transcript=transcript,
                    )
                except Exception as exc:
                    logger.exception("Judge failed for case %s", case_id)
                    eval_payload = JudgeEvaluation.service_stub(
                        details="run_eval_dataset: judge raised",
                        model_used=str(getattr(judge.llm, "model", "unknown")),
                        error=str(exc),
                    )

                scenario_key = ctx["training_scenario_id"] or "dummy-scenario-v1"
                assert eval_payload is not None
                await db.upsert_judge_result(
                    session_id,
                    scenario_key,
                    eval_payload,
                    judge_backend=getattr(judge, "backend_name", "unknown"),
                )
                logger.info(
                    "Saved judge_results for session=%s total_score=%s",
                    session_id,
                    eval_payload.total_score,
                )

            logger.info(
                "run_eval_dataset: case %s finished in %.2fs",
                case_id,
                time.perf_counter() - case_t0,
            )

            results_summary.append(
                {
                    "case_id": case_id,
                    "session_id": session_id,
                    "room_name": room,
                    "training_scenario_name": ts_name,
                    "total_score": eval_payload.total_score if eval_payload is not None else None,
                }
            )

        logger.info(
            "run_eval_dataset: all cases done in %.2fs",
            time.perf_counter() - run_t0,
        )
        print(json.dumps({"ok": True, "runs": results_summary}, ensure_ascii=False, indent=2))
        return 0
    finally:
        await db.close()


def main() -> None:
    raise SystemExit(asyncio.run(_run()))


if __name__ == "__main__":
    main()
