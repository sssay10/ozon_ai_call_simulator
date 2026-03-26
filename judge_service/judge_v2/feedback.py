from __future__ import annotations

from .schemas import CriterionResult


POSITIVE_FEEDBACK = {
    "greeting_correct": "Менеджер корректно представилась в приветствии.",
    "congratulation_given": "Менеджер корректно поздравила клиента с регистрацией.",
    "compliance_free_account_ip": "Менеджер явно обозначила бесплатный старт для расчетного счета.",
    "compliance_account_docs_ip": "Менеджер уточнила, какие документы нужны для открытия счета.",
}

IMPROVEMENT_FEEDBACK = {
    "greeting_correct": "Менеджер не представилась в правильном формате без лишних запрещенных формулировок.",
    "congratulation_given": "В начале разговора не было четкого поздравления клиента с регистрацией.",
    "compliance_free_account_ip": "Не было четкого указания, что счет для ИП бесплатен на старте.",
    "compliance_account_docs_ip": "Не было четкого указания, что для открытия счета ИП нужен оригинал паспорта РФ.",
}

RECOMMENDATIONS = {
    "greeting_correct": "Использовать правильный формат самопрезентации в приветствии: имя и звонок из Ozon без слова 'банк'.",
    "congratulation_given": "В начале разговора явно поздравлять клиента с регистрацией перед переходом к продуктовому предложению.",
    "compliance_free_account_ip": "Четко указывать, что счет для новых продавцов ИП бесплатен на старте, без размытых формулировок.",
    "compliance_account_docs_ip": "Уточнять, что для открытия счета ИП нужен оригинал паспорта РФ.",
}


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
            improve = IMPROVEMENT_FEEDBACK.get(criterion_id)
            recommend = RECOMMENDATIONS.get(criterion_id)

            if improve and improve not in feedback_improvement:
                feedback_improvement.append(improve)
            if recommend and recommend not in recommendations:
                recommendations.append(recommend)

    return {
        "feedback_positive": feedback_positive,
        "feedback_improvement": feedback_improvement,
        "recommendations": recommendations,
    }
