"""Output schema for the compliance / script step."""

from __future__ import annotations

from pydantic import BaseModel, Field

from judge.steps.shared.criterion import CriterionEvaluation


class ComplianceStepOutput(BaseModel):
    greeting_ozon: CriterionEvaluation = Field(
        ...,
        description=(
            "Приветствие: менеджер представился как сотрудник OZON кириллицей (Озон), без склонения слова «Озон»; "
            "в духе «Это [Имя] из OZON». Оцени соблюдение и кратко обоснуй по транскрипту."
        ),
    )
    stop_words: CriterionEvaluation = Field(
        ...,
        description=(
            "Стоп-слова: не использовалось слово «банк»; нет фраз вроде «Удобно говорить?», «Уделите пару минут?» "
            "и аналогичных просьб «разрешить» разговор после того как клиент уже ответил на звонок."
        ),
    )
    forbidden_qualification: CriterionEvaluation = Field(
        ...,
        description=(
            "Запретные квалификационные вопросы на раннем контакте вне сценария (например «Вы ИП или ООО?», "
            "система налогообложения и т.п.). Сверяйся с scenario_description: если сценарий не требует — это нарушение."
        ),
    )
    novoreg_scenario: CriterionEvaluation = Field(
        ...,
        description=(
            "Сценарий «Новорег»: если в persona/scenario клиент новый / только зарегистрировался — поздравление "
            "с регистрацией и упоминание бесплатного счёта без лишней детализации в начале. "
            "Если сценарий не новорег — в explanation укажи, что критерий не применим; score=true если нет нарушения по смыслу."
        ),
    )
    escalation: CriterionEvaluation = Field(
        ...,
        description=(
            "Эскалация: вопросы не по продажам (декларация, поддержка и т.д.) — перевод в поддержку, "
            "а не ответ «эксперта» вместо поддержки."
        ),
    )
    critical_errors: list[str] = Field(
        default_factory=list,
        description="Грубые нарушения комплаенса/скрипта на этом шаге; короткие формулировки с привязкой к фактам из диалога.",
    )
    feedback_positive: list[str] = Field(
        default_factory=list,
        description="Что по этому шагу сделано хорошо (конкретика по репликам или паттернам).",
    )
    feedback_improvement: list[str] = Field(
        default_factory=list,
        description="Что улучшить по этому шагу: практичные подсказки без общих фраз.",
    )
