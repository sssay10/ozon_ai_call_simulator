"""Output schema for the knowledge validation step."""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field

from judge.steps.shared.criterion import CriterionEvaluation


class KnowledgeStepOutput(BaseModel):
    tariff_accuracy: CriterionEvaluation = Field(
        ...,
        description=(
            "Корректность названной стоимости тарифа и условий, если они звучали в диалоге. "
            "Если не обсуждалось — в explanation «не обсуждалось», score=true (нет ошибки по теме)."
        ),
    )
    limits_commissions_accuracy: CriterionEvaluation = Field(
        ...,
        description=(
            "Корректность лимитов и комиссий, если обсуждались. "
            "Если не обсуждалось — explanation «не обсуждалось», score=true."
        ),
    )
    objection_handling: CriterionEvaluation = Field(
        ...,
        description=(
            "Корректность и уместность ответов на возражения (налоги, переводы, санкции и т.п.) "
            "относительно типичной линии банка."
        ),
    )
    critical_errors: list[str] = Field(
        default_factory=list,
        description="Фактические ошибки в цифрах, формулировках или опасные советы по знаниям.",
    )
    feedback_positive: list[str] = Field(
        default_factory=list,
        description="Где менеджер говорил корректно и убедительно по фактам.",
    )
    feedback_improvement: list[str] = Field(
        default_factory=list,
        description="Что поправить в фактуре и ответах на возражения.",
    )
    client_profile: dict[str, Any] = Field(
        default_factory=dict,
        description="Кратко: кто клиент по диалогу (для итогового отчёта).",
    )
