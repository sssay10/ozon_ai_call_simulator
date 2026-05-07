#!/usr/bin/env python3
"""
Run LLMJudge on eval_dataset/cases.json and write results to JSON — no DB writes.
Designed for model comparison experiments.

Usage (from judge_service/):
  uv run python eval_dataset/run_compare.py --output eval_dataset/results/ideal.json
  uv run python eval_dataset/run_compare.py --model qwen/qwen3-235b-a22b-2507 --output eval_dataset/results/qwen3.json
  uv run python eval_dataset/run_compare.py --model openai/gpt-4o-mini --temperature 0.5 --concurrency 3 --output eval_dataset/results/gpt4o_t05.json
  uv run python eval_dataset/run_compare.py --case compliance_greeting_bank_word --output eval_dataset/results/debug.json

Requires: DATABASE_URL, OPENROUTER_API_KEY (or LLM_PROVIDER=ollama)
Chroma: set CHROMA_HTTP_HOST / CHROMA_HTTP_PORT or defaults (0.0.0.0:8005) are used.

After collecting results, compare with:
  uv run python eval_dataset/compare_report.py \\
      --ideal eval_dataset/results/ideal.json \\
      --results eval_dataset/results/qwen3.json eval_dataset/results/gpt4o_t05.json
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
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

_ROOT = Path(__file__).resolve().parents[1]
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

from dotenv import load_dotenv
load_dotenv(_ROOT.parent / ".env")

os.environ.setdefault("CHROMA_HTTP_HOST", os.getenv("CHROMA_HTTP_HOST", "0.0.0.0"))
os.environ.setdefault("CHROMA_HTTP_PORT", os.getenv("CHROMA_HTTP_PORT", "8005"))
os.environ.setdefault("JUDGE_SERVICE_ROOT", str(_ROOT))
os.environ.setdefault("DATABASE_URL", "postgresql://dialogue:dialogue@0.0.0.0:5433/dialogues")
os.environ.setdefault("INTERNAL_DATABASE_URL", "postgresql://dialogue:dialogue@0.0.0.0:5433/dialogues")

from api.db import Database
from judge import LLMJudge
from judge.merged_evaluation import JudgeEvaluation

logging.basicConfig(level=logging.INFO, format="%(levelname)s %(name)s: %(message)s")
logger = logging.getLogger("run_compare")

SPEAKER_TO_DB_ROLE = {"manager": "user", "client": "assistant"}
DEFAULT_OWNER = os.getenv("EVAL_OWNER_USER_ID", "00000000-0000-0000-0000-000000000101")
DEFAULT_CASES_FILE = _ROOT / "eval_dataset" / "cases.json"
DEFAULT_OUTPUT = _ROOT / "eval_dataset" / "results" / "result.json"
DEFAULT_CONCURRENCY = 4


def _load_cases(path: Path) -> list[dict[str, Any]]:
    with path.open(encoding="utf-8") as f:
        data = json.load(f)
    return data.get("cases") or []


def _turns_to_db_messages(turns: list[dict[str, Any]]) -> list[tuple[str, str]]:
    out: list[tuple[str, str]] = []
    for t in turns:
        sp = t.get("speaker")
        text = (t.get("text") or "").strip()
        if sp not in SPEAKER_TO_DB_ROLE:
            raise ValueError(f"Invalid speaker {sp!r}")
        if text:
            out.append((SPEAKER_TO_DB_ROLE[sp], text))
    if not out:
        raise ValueError("No non-empty turns")
    return out


def _eval_to_dict(ev: JudgeEvaluation) -> dict[str, Any]:
    if hasattr(ev, "model_dump"):
        return ev.model_dump()
    if hasattr(ev, "dict"):
        return ev.dict()
    return vars(ev)


async def _process_case(
    case: dict[str, Any],
    db: Database,
    judge: LLMJudge,
    sem: asyncio.Semaphore,
) -> dict[str, Any]:
    case_id = case.get("id", "unknown")
    async with sem:
        t0 = time.perf_counter()

        ts_name = case["training_scenario_name"]
        ts_uuid = await db.get_training_scenario_id_by_name(ts_name)
        if not ts_uuid:
            raise RuntimeError(f"Training scenario not found: {ts_name!r}")

        room = f"compare-{case_id}-{uuid.uuid4().hex[:8]}"
        messages = _turns_to_db_messages(case.get("turns") or [])
        session_id = await db.insert_session_with_messages(
            room_name=room,
            product=str(case.get("product") or "rko"),
            owner_user_id=DEFAULT_OWNER,
            training_scenario_id=ts_uuid,
            messages=messages,
            job_id=f"compare:{case_id}",
        )

        ctx = await db.get_session_context(session_id)
        if ctx is None:
            raise RuntimeError(f"get_session_context failed for session {session_id}")

        transcript = await db.get_session_transcript(session_id)

        try:
            ev = await judge.evaluate(
                persona_description=ctx["persona_description"],
                transcript=transcript,
            )
        except Exception as exc:
            logger.exception("Judge failed for case %s", case_id)
            ev = JudgeEvaluation.service_stub(
                details="run_compare: judge raised",
                model_used=str(getattr(judge.llm, "model", "unknown")),
                error=str(exc),
            )

        elapsed = time.perf_counter() - t0
        logger.info(
            "case=%s session=%s score=%s elapsed=%.2fs",
            case_id, session_id, ev.total_score, elapsed,
        )

        return {
            "case_id": case_id,
            "session_id": str(session_id),
            "training_scenario_name": ts_name,
            "intent": case.get("intent", ""),
            "elapsed_seconds": round(elapsed, 2),
            "evaluation": _eval_to_dict(ev),
        }


async def _run() -> int:
    parser = argparse.ArgumentParser(
        description="Run LLMJudge on eval cases and write results to JSON (no DB writes)"
    )
    parser.add_argument("--cases-file", type=Path, default=DEFAULT_CASES_FILE)
    parser.add_argument("--case", type=str, default=None, help="Run only this case id")
    parser.add_argument("--model", type=str, default=None, help="Override OPENROUTER_MODEL")
    parser.add_argument("--temperature", type=float, default=None, help="Override LLM temperature")
    parser.add_argument(
        "--concurrency", type=int, default=DEFAULT_CONCURRENCY,
        help=f"Max parallel cases (default: {DEFAULT_CONCURRENCY})",
    )
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT, help="Output JSON path")
    args = parser.parse_args()

    if args.model:
        os.environ["OPENROUTER_MODEL"] = args.model
    if args.temperature is not None:
        os.environ["LLM_TEMPERATURE"] = str(args.temperature)

    cases = _load_cases(args.cases_file)
    if args.case:
        cases = [c for c in cases if c.get("id") == args.case]
        if not cases:
            logger.error("No case with id=%r", args.case)
            return 1

    model_name = os.getenv("OPENROUTER_MODEL", "unknown")
    logger.info(
        "model=%s temperature=%s concurrency=%d cases=%d output=%s",
        model_name, args.temperature, args.concurrency, len(cases), args.output,
    )

    db = Database()
    await db.initialize()
    judge = LLMJudge()
    sem = asyncio.Semaphore(args.concurrency)

    try:
        t0 = time.perf_counter()
        tasks = [_process_case(case, db, judge, sem) for case in cases]
        raw = await asyncio.gather(*tasks, return_exceptions=True)

        results: list[dict[str, Any]] = []
        errors: list[dict[str, Any]] = []
        for case, res in zip(cases, raw):
            if isinstance(res, Exception):
                logger.error("case=%s failed: %s", case.get("id"), res)
                errors.append({"case_id": case.get("id"), "error": str(res)})
            else:
                results.append(res)

        output = {
            "model": model_name,
            "temperature": args.temperature,
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "cases_total": len(cases),
            "cases_ok": len(results),
            "elapsed_total_seconds": round(time.perf_counter() - t0, 2),
            "results": results,
            "errors": errors,
        }

        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(json.dumps(output, ensure_ascii=False, indent=2), encoding="utf-8")
        logger.info("results written to %s", args.output)

        if errors:
            logger.warning("%d case(s) failed", len(errors))
            return 1
        return 0

    finally:
        await db.close()


def main() -> None:
    raise SystemExit(asyncio.run(_run()))


if __name__ == "__main__":
    main()
