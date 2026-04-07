"""Shared criterion shape for all step outputs."""

from __future__ import annotations

from pydantic import BaseModel, Field


class CriterionEvaluation(BaseModel):
    """Один критерий: бинарный проход/провал и пояснение."""

    explanation: str = Field(
        default="",
        description="Кратко: что увидели в транскрипте, цитата или вывод.",
    )
    score: bool = Field(
        default=False,
        description="Бинарно: true — критерий выполнен, false — нарушение или не выполнено.",
    )
