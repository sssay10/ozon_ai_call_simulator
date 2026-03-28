from __future__ import annotations

from .schemas import CriterionResult


POSITIVE_FEEDBACK = {
    "greeting_correct": "Менеджер корректно представилась в приветствии.",
    "congratulation_given": "Менеджер корректно поздравила клиента с регистрацией.",
    "compliance_free_account_ip": "Менеджер явно обозначила бесплатный старт для расчетного счета.",
    "compliance_account_docs_ip": "Менеджер уточнила, какие документы нужны для открытия счета.",
    "skeptic_no_pressure": "Менеджер не давила на клиента и не использовала завышающие обещания.",
    "busy_owner_concise_pitch": "Менеджер изложила суть предложения коротко и без лишней перегрузки.",
}

IMPROVEMENT_FEEDBACK = {
    "greeting_correct": "Менеджер не представилась в правильном формате без лишних запрещенных формулировок.",
    "congratulation_given": "В начале разговора не было четкого поздравления клиента с регистрацией.",
    "compliance_free_account_ip": "Не было четкого указания, что счет для ИП бесплатен на старте.",
    "compliance_account_docs_ip": "Не было четкого указания, что для открытия счета ИП нужен оригинал паспорта РФ.",
    "skeptic_no_pressure": "В разговоре с осторожным клиентом прозвучало давление или обещания, которые подрывают доверие.",
    "busy_owner_concise_pitch": "Основной питч получился слишком длинным для занятого клиента.",
}

RECOMMENDATIONS = {
    "greeting_correct": "Использовать правильный формат самопрезентации в приветствии: имя и звонок из Ozon.",
    "congratulation_given": "В начале разговора явно поздравлять клиента с регистрацией перед переходом к продуктовому предложению.",
    "compliance_free_account_ip": "Четко указывать, что счет для новых продавцов ИП бесплатен на старте, без размытых формулировок.",
    "compliance_account_docs_ip": "Уточнять, что для открытия счета ИП нужен оригинал паспорта РФ.",
    "skeptic_no_pressure": "При работе со скептичным клиентом избегать давления, категоричных обещаний и формулировок вроде 'обязательно нужно'.",
    "busy_owner_concise_pitch": "Для занятого клиента быстрее переходить к сути и укладывать основное предложение в короткий структурный блок.",
}


def _greeting_improvement_message(result: CriterionResult) -> str:
    failure_reason = str(result.metadata.get("failure_reason") or "").strip()
    rationale = result.rationale_short.lower()
    if failure_reason == "bank_in_greeting" or "банка" in rationale or "банк" in rationale:
        return "В приветствии было лишнее запрещенное упоминание банка."
    return "Менеджер не представилась в правильном формате приветствия."


def _greeting_recommendation_message(result: CriterionResult) -> str:
    failure_reason = str(result.metadata.get("failure_reason") or "").strip()
    rationale = result.rationale_short.lower()
    if failure_reason == "bank_in_greeting" or "банка" in rationale or "банк" in rationale:
        return "Использовать правильный формат самопрезентации в приветствии: имя и звонок из Ozon без слова 'банк'."
    return "Использовать правильный формат самопрезентации в приветствии: имя и звонок из Ozon."


def _improvement_message(result: CriterionResult) -> str | None:
    if result.criterion_id == "greeting_correct":
        return _greeting_improvement_message(result)
    return IMPROVEMENT_FEEDBACK.get(result.criterion_id)


def _recommendation_message(result: CriterionResult) -> str | None:
    if result.criterion_id == "greeting_correct":
        return _greeting_recommendation_message(result)
    return RECOMMENDATIONS.get(result.criterion_id)


def build_feedback_payload(results: list[CriterionResult]) -> dict[str, list[str]]:
    feedback_positive: list[str] = []
    feedback_improvement: list[str] = []
    recommendations: list[str] = []

    for result in results:
        criterion_id = result.criterion_id
        if result.decision == "pass":
            message = POSITIVE_FEEDBACK.get(criterion_id)
            if message and message not in feedback_positive:
                feedback_positive.append(message)
            continue

        if result.decision == "fail":
            improve = _improvement_message(result)
            recommend = _recommendation_message(result)

            if improve and improve not in feedback_improvement:
                feedback_improvement.append(improve)
            if recommend and recommend not in recommendations:
                recommendations.append(recommend)

    return {
        "feedback_positive": feedback_positive,
        "feedback_improvement": feedback_improvement,
        "recommendations": recommendations,
    }
