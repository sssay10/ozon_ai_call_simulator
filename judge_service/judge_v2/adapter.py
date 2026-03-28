from __future__ import annotations

from typing import Any, Iterable

from .feedback import build_feedback_payload
from .schemas import CriterionResult


def aggregate_criterion_scores(results: Iterable[CriterionResult]) -> dict[str, Any]:
    scores: dict[str, Any] = {}

    for result in results:
        if result.decision == "pass":
            scores[result.criterion_id] = True
        elif result.decision == "fail":
            scores[result.criterion_id] = False
        else:
            scores[result.criterion_id] = None

    return scores


def build_legacy_response(
    *,
    session_id: str,
    scenario_id: str,
    criterion_results: list[CriterionResult],
    total_score: float,
    critical_errors: list[str],
    relevant_criteria: list[str],
    debug: dict[str, Any] | None = None,
    judge_backend: str = "hybrid_kb_v2",
    model_used: str = "unknown",
) -> dict[str, Any]:
    feedback = build_feedback_payload(criterion_results)

    return {
        "session_id": session_id,
        "scenario_id": scenario_id,
        "scores": aggregate_criterion_scores(criterion_results),
        "total_score": total_score,
        "critical_errors": critical_errors,
        "feedback_positive": feedback["feedback_positive"],
        "feedback_improvement": feedback["feedback_improvement"],
        "recommendations": feedback["recommendations"],
        "client_profile": {},
        "relevant_criteria": relevant_criteria,
        "model_used": model_used,
        "judge_backend": judge_backend,
        "criterion_results": [result.model_dump() for result in criterion_results],
        "debug": debug or {},
    }
