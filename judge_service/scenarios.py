from dataclasses import dataclass
from typing import Dict, List, Optional, Any


@dataclass
class ScenarioConfig:
    """
    Описание одного сценария оценки:

    - id: внутренний идентификатор сценария (то, что будем хранить в TrainingSession)
    - title / description: понятное описание для логов/отладки
    - difficulty: уровень сложности, который выбирает менеджер в ЛК ("easy" | "medium" | "hard")
    - client_archetype: архетип клиента из ТЗ/ЛК ("novice_ip", "silent_ip", "expert_ooo" и т.п.)
    - client_profile_conditions: базовые условия по профилю клиента (ИП/ООО, есть ли сотрудники и т.д.)
    - relevant_criteria: какие критерии мы вообще оцениваем в этом сценарии
    - compliance_must_have: какие обязательные смыслы/фразы должны быть (в любом формулировочном виде)
    - compliance_must_avoid: какие фразы/паттерны недопустимы
    - weights: веса критериев для расчёта total_score (используем на бэкенде)
    """
    id: str
    title: str
    description: str
    difficulty: str
    client_archetype: str
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
    # сюда будем маппить то, что менеджер выбирает в ЛК
    difficulty="easy",            # уровень сложности из UI
    client_archetype="novice_ip",  # архетип клиента из ТЗ/ЛК (ID, не русское название)

    # минимальные условия по профилю клиента, чтобы этот сценарий был релевантен
    client_profile_conditions={
        "type": "IP",
        "has_employees": False,
        "has_other_account": False,
    },

    # критерии, которые в этом сценарии реально оцениваем
    relevant_criteria=[
        "greeting_correct",                       # корректное приветствие + самопрезентация
        "congratulation_given",                   # поздравление с регистрацией
        "compliance_free_account_ip",             # правильно объяснена бесплатность счёта для ИП
        "compliance_account_docs_ip",             # корректно озвучены документы для ИП
        "compliance_buh_free_usn_income",         # аккуратное упоминание бухгалтерии (если всплывает)
        "verification_agreement_correctly_understood",  # менеджер проверил понимание клиента
        "closing_success",                        # логичное завершение звонка
        "politeness",                             # вежливость, отсутствие жёстких формулировок
    ],

    # обязательные смыслы / элементы скрипта для этой ветки
    compliance_must_have=[
        "Менеджер в приветствии представляется в формате 'Это <имя> из Ozon' (без слова 'банк').",
        "Менеджер поздравляет клиента с регистрацией на Ozon в начале разговора.",
        "Счёт для новых продавцов Ozon бесплатен на старте, без формулировки 'бесплатно навсегда'.",
        "Для открытия счёта ИП нужен только оригинал паспорта РФ.",
        "Менеджер уточняет систему налогообложения и наличие/отсутствие сотрудников.",
    ],

    # запрещённые формулировки/паттерны для этой ветки
    compliance_must_avoid=[
        "Использование слова 'банк' в самопрезентации в приветствии (например, 'вас приветствует Анна из Ozon Банка').",
        "Обещания вида 'гарантируем одобрение'.",
        "Формулировка 'бесплатно навсегда' в описании счёта.",
        "Формулировка 'просто пришлите фото документов' без уточнения про оригиналы.",
        "Агрессивные или вводящие в заблуждение формулировки про обязательное подключение услуг.",
    ],

    # веса критериев при подсчёте итогового балла (используем на бэкенде, не в LLM)
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


# Реестр всех сценариев (сюда потом добавим medium/hard и другие архетипы)
SCENARIO_CONFIG: Dict[str, ScenarioConfig] = {
    NOVICE_IP_NO_ACCOUNT_EASY.id: NOVICE_IP_NO_ACCOUNT_EASY,
}


def get_scenario_id(difficulty: str, client_archetype: str) -> Optional[str]:
    """
    Маппинг выбора менеджера (сложность + архетип клиента из ЛК) -> scenario_id.

    difficulty: "easy" | "medium" | "hard"
    client_archetype: строка-идентификатор архетипа, которую отдаёт UI,
                      например: "novice_ip", "expert_ip", "complainer_ooo" и т.п.
    """
    for scenario in SCENARIO_CONFIG.values():
        if (
            scenario.difficulty == difficulty
            and scenario.client_archetype == client_archetype
        ):
            return scenario.id
    return None


def get_scenario_config(scenario_id: str) -> ScenarioConfig:
    return SCENARIO_CONFIG[scenario_id]
