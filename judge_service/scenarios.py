from dataclasses import dataclass
from typing import Any, Dict, List, Optional


@dataclass
class ScenarioConfig:
    """
    Описание одного сценария оценки:

    - id: внутренний идентификатор сценария (то, что будем хранить в judge_results)
    - title / description: понятное описание для логов/отладки
    - level: грубая градация сложности рубрики ("easy" | "medium" | "hard")
    - client_segment: условный сегмент клиента для рубрики (ID, не русское название)
    - client_profile_conditions: базовые условия по профилю клиента (ИП/ООО, есть ли сотрудники и т.д.)
    - relevant_criteria: какие критерии мы вообще оцениваем в этом сценарии
    - compliance_must_have: какие обязательные смыслы/фразы должны быть (в любом формулировочном виде)
    - compliance_must_avoid: какие фразы/паттерны недопустимы
    - weights: веса критериев для расчёта total_score (используем на бэкенде)
    """
    id: str
    title: str
    description: str
    level: str
    client_segment: str
    client_profile_conditions: Dict[str, Any]
    relevant_criteria: List[str]
    compliance_must_have: List[str]
    compliance_must_avoid: List[str]
    weights: Dict[str, int]


# ===  СЦЕНАРИЙ 1: "Новый ИП, нет счёта", уровень сложности easy  ===

NOVICE_IP_NO_ACCOUNT_EASY = ScenarioConfig(
    id="novice_ip_no_account_easy",
    title="Новый продавец ИП, нет расчётного счёта",
    description=(
        "Клиент — новый продавец Ozon, зарегистрирован как ИП, "
        "у него ещё нет расчётного счёта в банке. "
        "Цель тренировки — отработать базовый скрипт: корректное приветствие "
        "в формате 'Это <имя> из Ozon' без слова 'банк', поздравление с регистрацией, "
        "объяснение выгоды бесплатного счёта для новых продавцов, уточнение ситуации клиента "
        "(система налогообложения, сотрудники), рассказ про требования по документам "
        "и аккуратное закрытие звонка без завышенных ожиданий."
    ),
    level="easy",
    client_segment="novice_ip",

    client_profile_conditions={
        "type": "IP",
        "has_employees": False,
        "has_other_account": False,
    },

    relevant_criteria=[
        "greeting_correct",
        "congratulation_given",
        "compliance_free_account_ip",
        "compliance_account_docs_ip",
        "compliance_buh_free_usn_income",
        "verification_agreement_correctly_understood",
        "closing_success",
        "politeness",
    ],

    compliance_must_have=[
        "Менеджер в приветствии представляется в формате 'Это <имя> из Ozon' (без слова 'банк').",
        "Менеджер поздравляет клиента с регистрацией на Ozon в начале разговора.",
        "Счёт для новых продавцов Ozon бесплатен на старте, без формулировки 'бесплатно навсегда'.",
        "Для открытия счёта ИП нужен только оригинал паспорта РФ.",
        "Менеджер уточняет систему налогообложения и наличие/отсутствие сотрудников.",
    ],

    compliance_must_avoid=[
        "Использование слова 'банк' в самопрезентации в приветствии (например, 'вас приветствует Анна из Ozon Банка').",
        "Обещания вида 'гарантируем одобрение'.",
        "Формулировка 'бесплатно навсегда' в описании счёта.",
        "Формулировка 'просто пришлите фото документов' без уточнения про оригиналы.",
        "Агрессивные или вводящие в заблуждение формулировки про обязательное подключение услуг.",
    ],

    weights={
        "greeting_correct": 1,
        "congratulation_given": 1,
        "compliance_free_account_ip": 2,
        "compliance_account_docs_ip": 2,
        "compliance_buh_free_usn_income": 1,
        "verification_agreement_correctly_understood": 2,
        "closing_success": 2,
        "politeness": 2,
    },
)


SCENARIO_CONFIG: Dict[str, ScenarioConfig] = {
    NOVICE_IP_NO_ACCOUNT_EASY.id: NOVICE_IP_NO_ACCOUNT_EASY,
}

DEFAULT_SCENARIO_ID = NOVICE_IP_NO_ACCOUNT_EASY.id


def get_scenario_id(level: str, client_segment: str) -> Optional[str]:
    """
    Маппинг выбора (level + client_segment) -> scenario_id.

    level: "easy" | "medium" | "hard"
    client_segment: строка-идентификатор, например: "novice_ip", "expert_ip", "complainer_ooo" и т.п.
    """
    for scenario in SCENARIO_CONFIG.values():
        if scenario.level == level and scenario.client_segment == client_segment:
            return scenario.id
    return None


def get_scenario_config(scenario_id: str) -> ScenarioConfig:
    return SCENARIO_CONFIG[scenario_id]
