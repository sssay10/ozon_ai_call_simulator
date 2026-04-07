"""Output schema for the sales skills step."""

from __future__ import annotations

from pydantic import BaseModel, Field

from judge.steps.shared.criterion import CriterionEvaluation


class SalesSkillsStepOutput(BaseModel):
    empathy_joining: CriterionEvaluation = Field(
        ...,
        description=(
            "Перед серией вопросов — фраза присоединения / эмпатии (в духе «Уверен, что подобрали комфортные условия…» "
            "или другая уместная; не обязательно дословно)."
        ),
    )
    question_format_open_alternative: CriterionEvaluation = Field(
        ...,
        description=(
            "Формат вопросов: преобладают открытые или альтернативные вопросы. "
            "Много закрытых «да/нет» подряд без развития темы — score=false."
        ),
    )
    summarizing: CriterionEvaluation = Field(
        ...,
        description=(
            "Резюмирование: менеджер собрал ответы клиента в итоговую фразу (например «Значит вы сейчас обслуживаетесь…»)."
        ),
    )
    critical_errors: list[str] = Field(
        default_factory=list,
        description="Серьёзные ошибки ведения диалога на этом шаге (если есть).",
    )
    feedback_positive: list[str] = Field(
        default_factory=list,
        description="Сильные стороны по продажным навыкам в этом отрезке звонка.",
    )
    feedback_improvement: list[str] = Field(
        default_factory=list,
        description="Рекомендации по улучшению вопросов, присоединения, резюме.",
    )
