"""Canonical merged judge output: built from step Pydantic models, no dict walking."""

from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from judge.steps.compliance.schema import ComplianceStepOutput
from judge.steps.knowledge.schema import KnowledgeStepOutput
from judge.steps.sales_skills.schema import SalesSkillsStepOutput
from judge.steps.shared.criterion import CriterionEvaluation

StepName = Literal["compliance", "sales", "knowledge"]

_MERGE_SKIP: frozenset[str] = frozenset(
    {
        "critical_errors",
        "feedback_positive",
        "feedback_improvement",
        "client_profile",
    }
)

_DEFAULT_RELEVANT_CRITERIA: list[str] = [
    "Шаг 1: скрипт, стоп-слова, комплаенс",
    "Шаг 2: продажные навыки и управление диалогом",
    "Шаг 3: знания (тарифы, лимиты, гайд)",
]


def _criterion_fields(step: BaseModel) -> dict[str, CriterionEvaluation]:
    out: dict[str, CriterionEvaluation] = {}
    for name in step.model_fields:
        if name in _MERGE_SKIP:
            continue
        val = getattr(step, name)
        if isinstance(val, CriterionEvaluation):
            out[name] = val
    return out


def _step_pass_rate_percent(step: BaseModel) -> float:
    passed = 0
    n = 0
    for name in step.model_fields:
        if name in _MERGE_SKIP:
            continue
        val = getattr(step, name)
        if isinstance(val, CriterionEvaluation):
            n += 1
            if val.score:
                passed += 1
    if n == 0:
        return 0.0
    return 100.0 * passed / n


def _flat_scores(prefix: StepName, step: BaseModel) -> dict[str, bool]:
    out: dict[str, bool] = {}
    for name in step.model_fields:
        if name in _MERGE_SKIP:
            continue
        val = getattr(step, name)
        if isinstance(val, CriterionEvaluation):
            out[f"{prefix}.{name}"] = val.score
    return out


class JudgeEvaluation(BaseModel):
    """Single source of truth for pipeline output, API, and persistence (via model_dump)."""

    model_config = ConfigDict(extra="ignore")

    scores: dict[str, bool] = Field(default_factory=dict)
    criteria: dict[str, dict[str, CriterionEvaluation]] = Field(
        default_factory=lambda: {"compliance": {}, "sales": {}, "knowledge": {}},
        description="Шаг → критерий → оценка.",
    )
    total_score: float = 0.0
    critical_errors: list[str] = Field(default_factory=list)
    feedback_positive: list[str] = Field(default_factory=list)
    feedback_improvement: list[str] = Field(default_factory=list)
    recommendations: list[str] = Field(default_factory=list)
    client_profile: dict[str, Any] = Field(default_factory=dict)
    relevant_criteria: list[str] = Field(default_factory=list)
    model_used: str = "unknown"
    error: str | None = None
    details: str | None = None

    @field_validator("scores", mode="before")
    @classmethod
    def _coerce_scores(cls, v: Any) -> dict[str, bool]:
        if not isinstance(v, dict):
            return {}
        out: dict[str, bool] = {}
        for k, val in v.items():
            if isinstance(val, bool):
                out[str(k)] = val
            else:
                out[str(k)] = bool(val)
        return out

    @model_validator(mode="before")
    @classmethod
    def _ensure_criteria_steps(cls, data: Any) -> Any:
        if not isinstance(data, dict):
            return data
        c = data.get("criteria")
        if not isinstance(c, dict):
            data["criteria"] = {"compliance": {}, "sales": {}, "knowledge": {}}
            return data
        for key in ("compliance", "sales", "knowledge"):
            if key not in c or not isinstance(c.get(key), dict):
                c[key] = {}
        data["criteria"] = c
        return data

    @classmethod
    def service_stub(
        cls,
        *,
        details: str,
        model_used: str = "fallback",
        error: str | None = None,
    ) -> JudgeEvaluation:
        """Placeholder when the LLM is off or evaluation failed before merge."""
        return cls(
            scores={},
            criteria={"compliance": {}, "sales": {}, "knowledge": {}},
            total_score=0.0,
            critical_errors=[],
            feedback_positive=[],
            feedback_improvement=[],
            recommendations=[],
            client_profile={},
            relevant_criteria=[],
            model_used=model_used,
            details=details,
            error=error,
        )


def merge_step_outputs(
    *,
    compliance: ComplianceStepOutput,
    sales: SalesSkillsStepOutput,
    knowledge: KnowledgeStepOutput,
    model_used: str,
) -> JudgeEvaluation:
    criteria_nested: dict[str, dict[str, CriterionEvaluation]] = {
        "compliance": _criterion_fields(compliance),
        "sales": _criterion_fields(sales),
        "knowledge": _criterion_fields(knowledge),
    }
    scores: dict[str, bool] = {}
    scores.update(_flat_scores("compliance", compliance))
    scores.update(_flat_scores("sales", sales))
    scores.update(_flat_scores("knowledge", knowledge))

    total_score = (
        _step_pass_rate_percent(compliance)
        + _step_pass_rate_percent(sales)
        + _step_pass_rate_percent(knowledge)
    ) / 3.0

    critical_errors: list[str] = []
    feedback_positive: list[str] = []
    feedback_improvement: list[str] = []
    for block in (compliance, sales, knowledge):
        critical_errors.extend(block.critical_errors)
        feedback_positive.extend(block.feedback_positive)
        feedback_improvement.extend(block.feedback_improvement)

    recommendations: list[str] = []
    for block in (compliance, sales, knowledge):
        for line in block.feedback_improvement:
            if len(recommendations) >= 12:
                break
            if line and line not in recommendations:
                recommendations.append(line)

    return JudgeEvaluation(
        scores=scores,
        criteria=criteria_nested,
        total_score=total_score,
        critical_errors=critical_errors,
        feedback_positive=feedback_positive,
        feedback_improvement=feedback_improvement,
        recommendations=recommendations,
        client_profile=dict(knowledge.client_profile),
        relevant_criteria=list(_DEFAULT_RELEVANT_CRITERIA),
        model_used=model_used,
        details=None,
        error=None,
    )


