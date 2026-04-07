from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field

from judge.steps.shared.criterion import CriterionEvaluation


class TranscriptTurn(BaseModel):
    role: str
    text: str
    created_at: str | None = None


class SessionMetadataResponse(BaseModel):
    session_id: str
    room_name: str
    product: str
    started_at: str | None = None
    ended_at: str | None = None


class JudgeResultResponse(BaseModel):
    scenario_id: str
    scores: dict[str, bool] = Field(default_factory=dict)
    criteria: dict[str, dict[str, CriterionEvaluation]] = Field(
        default_factory=dict,
        description="По шагам: compliance | sales | knowledge → criterion_id → оценка.",
    )
    total_score: float = 0.0
    critical_errors: list[str] = Field(default_factory=list)
    feedback_positive: list[str] = Field(default_factory=list)
    feedback_improvement: list[str] = Field(default_factory=list)
    recommendations: list[str] = Field(default_factory=list)
    client_profile: dict[str, Any] = Field(default_factory=dict)
    relevant_criteria: list[str] = Field(default_factory=list)
    model_used: str = "stub-model"
    error: str | None = None
    details: str | None = None
    created_at: str | None = None


class SessionResultResponse(BaseModel):
    session: SessionMetadataResponse
    transcript: list[TranscriptTurn] = Field(default_factory=list)
    judge_result: JudgeResultResponse | None = None
