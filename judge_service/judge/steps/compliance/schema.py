"""Output schema for the compliance / script step."""

from __future__ import annotations

from pydantic import BaseModel, Field

from judge.steps.shared.criterion import CriterionEvaluation


class ComplianceLlmOutput(BaseModel):
    """Поля, которые заполняет только LLM (structured output)."""

    greeting_ozon: CriterionEvaluation = Field(
        ...,
        description=(
            "Приветствие: менеджер представился как сотрудник ОЗОН кириллицей без склонения; "
            "в духе «Это [Имя] из ОЗОН». Оцени соблюдение и кратко обоснуй по транскрипту."
        ),
    )
    post_answer_time_requests: CriterionEvaluation = Field(
        ...,
        description=(
            "Просьбы «разрешить» разговор после того, как клиент уже ответил на звонок: не должно быть вопросов "
            "вроде «Удобно говорить?», «Уделите пару минут?», «Могу уделить минуту?» и близких по смыслу — "
            "клиент уже принял вызов, повторная «вежливая» просьба о времени считается нарушением."
        ),
    )
    forbidden_qualification: CriterionEvaluation = Field(
        ...,
        description=(
            "Запретные квалификационные вопросы на раннем контакте вне сценария (например «Вы ИП или ООО?», "
            "система налогообложения и т.п.). Если по транскрипту это не запрошено клиентом — считай нарушением."
        ),
    )
    novoreg_scenario: CriterionEvaluation = Field(
        ...,
        description=(
            "Сценарий «Новорег»: если в persona клиент новый / только зарегистрировался — поздравление "
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


class ComplianceStepOutput(ComplianceLlmOutput):
    """Полный результат шага: к выводу LLM добавляется критерий стоп-слов из кода."""

    stop_words: CriterionEvaluation = Field(
        ...,
        description=(
            "Стоп-слова по фиксированным правилам шага (без LLM): совпадения с заданными в коде шаблонами "
            "только в репликах менеджера. Поле заполняется кодом судьи, модель его не оценивает."
        ),
    )
