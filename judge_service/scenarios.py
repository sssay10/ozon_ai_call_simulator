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


CORE_RKO_CRITERIA = [
    "greeting_correct",
    "congratulation_given",
    "compliance_free_account_ip",
    "compliance_account_docs_ip",
]

CORE_RKO_MUST_HAVE = [
    "Менеджер в приветствии представляется в формате 'Это <имя> из Ozon' (без слова 'банк').",
    "Менеджер поздравляет клиента с регистрацией на Ozon в начале разговора.",
    "Счёт для новых продавцов Ozon бесплатен на старте, без формулировки 'бесплатно навсегда'.",
    "Для открытия счёта ИП нужен только оригинал паспорта РФ.",
]

CORE_RKO_MUST_AVOID = [
    "Использование слова 'банк' в самопрезентации в приветствии (например, 'вас приветствует Анна из Ozon Банка').",
    "Обещания вида 'гарантируем одобрение'.",
    "Формулировка 'бесплатно навсегда' в описании счёта.",
    "Формулировка 'просто пришлите фото документов' без уточнения про оригиналы.",
    "Агрессивные или вводящие в заблуждение формулировки про обязательное подключение услуг.",
]

CORE_RKO_WEIGHTS = {
    "greeting_correct": 1,
    "congratulation_given": 1,
    "compliance_free_account_ip": 2,
    "compliance_account_docs_ip": 2,
}


def _build_rko_core_scenario(
    *,
    scenario_id: str,
    title: str,
    description: str,
    client_segment: str,
    difficulty_level: int = 1,
) -> ScenarioConfig:
    return ScenarioConfig(
        id=scenario_id,
        title=title,
        description=description,
        level=f"level_{difficulty_level}",
        client_segment=client_segment,
        client_profile_conditions={
            "type": "IP",
            "has_employees": False,
            "has_other_account": False,
        },
        relevant_criteria=list(CORE_RKO_CRITERIA),
        compliance_must_have=list(CORE_RKO_MUST_HAVE),
        compliance_must_avoid=list(CORE_RKO_MUST_AVOID),
        weights=dict(CORE_RKO_WEIGHTS),
    )


# === Legacy baseline scenario ===

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


RKO_NOVICE_L1_CORE = _build_rko_core_scenario(
    scenario_id="rko_novice_l1_core",
    title="РКО / novice / level 1",
    description=(
        "Клиент — начинающий продавец или ИП с низкой финансовой насмотренностью. "
        "Ожидается спокойное и понятное объяснение базовых условий РКО простым языком, "
        "без лишнего давления и перегруза терминами. На текущем этапе judge проверяет "
        "core compliance и базовую корректность начала звонка."
    ),
    client_segment="rko_novice",
)

RKO_SKEPTIC_L1_CORE = _build_rko_core_scenario(
    scenario_id="rko_skeptic_l1_core",
    title="РКО / skeptic / level 1",
    description=(
        "Клиент относится к предложению осторожно и склонен проверять формулировки. "
        "Даже в базовой rubric ожидается аккуратность, отсутствие завышенных обещаний "
        "и корректное донесение обязательных условий по счёту и документам. "
        "На текущем этапе judge проверяет core compliance и базовую корректность начала звонка."
    ),
    client_segment="rko_skeptic",
)

RKO_BUSY_OWNER_L1_CORE = _build_rko_core_scenario(
    scenario_id="rko_busy_owner_l1_core",
    title="РКО / busy_owner / level 1",
    description=(
        "Клиент занят, предпочитает короткий и структурный диалог. "
        "Даже в базовой rubric ожидается быстрый выход к сути без потери обязательных условий "
        "по бесплатному старту и документам. На текущем этапе judge проверяет "
        "core compliance и базовую корректность начала звонка."
    ),
    client_segment="rko_busy_owner",
)

RKO_SCENARIO_IDS: Dict[str, Dict[int, str]] = {
    "novice": {
        1: "rko_novice_l1_core",
        2: "rko_novice_l2_core",
        3: "rko_novice_l3_core",
        4: "rko_novice_l4_core",
    },
    "skeptic": {
        1: "rko_skeptic_l1_core",
        2: "rko_skeptic_l2_core",
        3: "rko_skeptic_l3_core",
        4: "rko_skeptic_l4_core",
    },
    "busy_owner": {
        1: "rko_busy_owner_l1_core",
        2: "rko_busy_owner_l2_core",
        3: "rko_busy_owner_l3_core",
        4: "rko_busy_owner_l4_core",
    },
}

RKO_LEVEL_NOTES = {
    1: "Базовый уровень сложности: judge проверяет core compliance и базовую корректность звонка.",
    2: "Уровень 2: judge применяет более строгий modifier к тем же core-критериям.",
    3: "Уровень 3: judge применяет заметно более строгий modifier к тем же core-критериям.",
    4: "Уровень 4: judge применяет максимальную строгость внутри текущего core-rubric.",
}


def _register_rko_level_variants() -> Dict[str, ScenarioConfig]:
    variants: Dict[str, ScenarioConfig] = {}

    base_descriptions = {
        "novice": (
            "Клиент — начинающий продавец или ИП с низкой финансовой насмотренностью. "
            "Ожидается спокойное и понятное объяснение базовых условий РКО простым языком, "
            "без лишнего давления и перегруза терминами."
        ),
        "skeptic": (
            "Клиент относится к предложению осторожно и склонен проверять формулировки. "
            "Ожидается аккуратность, отсутствие завышенных обещаний и корректное донесение "
            "обязательных условий по счёту и документам."
        ),
        "busy_owner": (
            "Клиент занят, предпочитает короткий и структурный диалог. "
            "Ожидается быстрый выход к сути без потери обязательных условий "
            "по бесплатному старту и документам."
        ),
    }

    for archetype, levels in RKO_SCENARIO_IDS.items():
        for level, scenario_id in levels.items():
            if scenario_id in {
                RKO_NOVICE_L1_CORE.id,
                RKO_SKEPTIC_L1_CORE.id,
                RKO_BUSY_OWNER_L1_CORE.id,
            }:
                continue

            variants[scenario_id] = _build_rko_core_scenario(
                scenario_id=scenario_id,
                title=f"РКО / {archetype} / level {level}",
                description=f"{base_descriptions[archetype]} {RKO_LEVEL_NOTES[level]}",
                client_segment=f"rko_{archetype}",
                difficulty_level=level,
            )

    return variants


SCENARIO_CONFIG: Dict[str, ScenarioConfig] = {
    NOVICE_IP_NO_ACCOUNT_EASY.id: NOVICE_IP_NO_ACCOUNT_EASY,
    RKO_NOVICE_L1_CORE.id: RKO_NOVICE_L1_CORE,
    RKO_SKEPTIC_L1_CORE.id: RKO_SKEPTIC_L1_CORE,
    RKO_BUSY_OWNER_L1_CORE.id: RKO_BUSY_OWNER_L1_CORE,
    **_register_rko_level_variants(),
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
