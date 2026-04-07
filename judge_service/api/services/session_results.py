"""Orchestration for session transcript + judge evaluation (HTTP-agnostic)."""

from __future__ import annotations

import logging
import time
from datetime import datetime, timezone

from api.db import Database
from api.schemas import (
    JudgeResultResponse,
    SessionMetadataResponse,
    SessionResultResponse,
    TranscriptTurn,
)
from judge import LLMJudge
from judge.merged_evaluation import JudgeEvaluation

logger = logging.getLogger(__name__)


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def build_session_result_response(
    *,
    session_id: str,
    room_name: str,
    product: str,
    started_at: str | None,
    ended_at: str | None,
    transcript: list[TranscriptTurn],
    training_scenario_id: str | None,
    persona_description: str | None,
    scenario_description: str | None,
    evaluation: JudgeEvaluation,
    judge_result_saved_at: str | None = None,
) -> SessionResultResponse:
    details_parts: list[str] = ["Static response for frontend contract testing."]
    if training_scenario_id:
        details_parts.append(f"training_scenario_id={training_scenario_id}")
    if persona_description:
        details_parts.append(f"persona_description={persona_description}")
    if scenario_description:
        details_parts.append(f"scenario_description={scenario_description}")

    dumped = evaluation.model_dump()
    details_val = dumped.pop("details", None)
    static_suffix = "\n".join(details_parts)
    details_final = ((str(details_val) + "\n") if details_val else "") + static_suffix

    return SessionResultResponse(
        session=SessionMetadataResponse(
            session_id=session_id,
            room_name=room_name,
            product=product,
            started_at=started_at,
            ended_at=ended_at,
        ),
        transcript=transcript,
        judge_result=JudgeResultResponse(
            **dumped,
            scenario_id=training_scenario_id or "dummy-scenario-v1",
            details=details_final,
            created_at=judge_result_saved_at or _now_iso(),
        ),
    )


async def run_session_results(
    database: Database,
    judge: LLMJudge | None,
    *,
    session_id: str | None,
    room_name: str | None,
    refresh: bool,
) -> SessionResultResponse:
    """Load session, return cached judge row when possible, otherwise run LLM and persist."""
    sid = (session_id or "").strip()
    rname = (room_name or "").strip()
    if not sid and not rname:
        raise ValueError("session_id or room_name is required")
    if sid and rname:
        raise ValueError("Provide only one of session_id or room_name")

    if sid:
        session_context = await database.get_session_context(sid)
    else:
        session_context = await database.get_session_context_by_room_name(rname)
    if session_context is None:
        raise LookupError("Session not found")

    resolved_session_id = session_context["session_id"]
    transcript_rows = await database.get_session_transcript(resolved_session_id)
    transcript = [TranscriptTurn(**row) for row in transcript_rows]
    logger.info(
        "session-results: session=%s room=%s transcript_turns=%s refresh=%s",
        resolved_session_id,
        session_context.get("room_name"),
        len(transcript),
        refresh,
    )

    if not refresh:
        stored = await database.get_stored_judge_evaluation(resolved_session_id)
        if stored is not None:
            logger.info(
                "session-results: serving cached judge_results for session=%s",
                resolved_session_id,
            )
            return build_session_result_response(
                session_id=session_context["session_id"],
                room_name=session_context["room_name"],
                product=session_context["product"],
                started_at=session_context["started_at"],
                ended_at=session_context["ended_at"],
                transcript=transcript,
                training_scenario_id=session_context["training_scenario_id"],
                persona_description=session_context["persona_description"],
                scenario_description=session_context["scenario_description"],
                evaluation=stored.evaluation,
                judge_result_saved_at=stored.updated_at,
            )

    llm_result: JudgeEvaluation
    if judge is None:
        logger.warning("session-results: judge not initialized — returning stub evaluation")
        llm_result = JudgeEvaluation.service_stub(
            details="LLM judge is not initialized.",
            error="judge_not_initialized",
        )
    else:
        try:
            t_eval = time.perf_counter()
            llm_result = await judge.evaluate(
                persona_description=session_context["persona_description"],
                scenario_description=session_context["scenario_description"],
                transcript=transcript_rows,
            )
            logger.info(
                "session-results: judge.evaluate finished in %.2fs total_score=%.2f model=%s",
                time.perf_counter() - t_eval,
                llm_result.total_score,
                llm_result.model_used,
            )
        except Exception as exc:
            logger.exception("judge evaluate failed: %s", exc)
            llm_result = JudgeEvaluation.service_stub(
                details="LLM evaluation failed.",
                model_used=str(getattr(judge.llm, "model", "unknown")),
                error=str(exc),
            )

    scenario_id = session_context["training_scenario_id"] or "dummy-scenario-v1"
    judge_backend = (
        getattr(judge, "backend_name", "unknown") if judge is not None else "not_initialized"
    )
    saved_times = await database.upsert_judge_result(
        session_context["session_id"],
        scenario_id,
        llm_result,
        judge_backend=judge_backend,
    )
    logger.info(
        "session-results: upserted judge_results session=%s backend=%s updated_at=%s",
        session_context["session_id"],
        judge_backend,
        saved_times.get("updated_at"),
    )

    return build_session_result_response(
        session_id=session_context["session_id"],
        room_name=session_context["room_name"],
        product=session_context["product"],
        started_at=session_context["started_at"],
        ended_at=session_context["ended_at"],
        transcript=transcript,
        training_scenario_id=session_context["training_scenario_id"],
        persona_description=session_context["persona_description"],
        scenario_description=session_context["scenario_description"],
        evaluation=llm_result,
        judge_result_saved_at=saved_times["updated_at"],
    )
