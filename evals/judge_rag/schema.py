"""Pydantic output schema for the knowledge validation judge.

Self-contained copy — does not import from judge_service.
"""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field


class CriterionEvaluation(BaseModel):
    explanation: str = Field(default="")
    score: bool = Field(default=False)


class KnowledgeStepOutput(BaseModel):
    tariff_accuracy: CriterionEvaluation
    limits_commissions_accuracy: CriterionEvaluation
    objection_handling: CriterionEvaluation
    critical_errors: list[str] = Field(default_factory=list)
    feedback_positive: list[str] = Field(default_factory=list)
    feedback_improvement: list[str] = Field(default_factory=list)
    client_profile: dict[str, Any] = Field(default_factory=dict)
