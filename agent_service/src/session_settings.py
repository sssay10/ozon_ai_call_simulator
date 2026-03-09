"""
Session settings: archetypes, difficulty, products.
Used to build the LLM system prompt from UI-selected options.
"""
from __future__ import annotations

import json
from typing import Any

# Архетипы клиентов (как в dialogue_simulator.py)
ARCHETYPES: dict[str, dict[str, Any]] = {
    "novice": {
        "name": "Новичок",
        "personality": "Я только начинаю, хочу простые объяснения, могу путаться, но без агрессии.",
        "speech_style": "коротко, по делу, иногда уточняю базовые вещи",
        "default_goal": "понять, что это и нужно ли мне",
        "taboos": ["не изображай эксперта", "не используй сложные термины без просьбы"],
    },
    "skeptic": {
        "name": "Скептик",
        "personality": "Не доверяю, ищу подвох, не люблю воду, требую конкретику.",
        "speech_style": "строго, без эмоций, 'покажите цифры'",
        "default_goal": "минимизировать риск и не попасть на комиссии",
        "taboos": ["не становись дружелюбным", "не соглашайся слишком быстро"],
    },
    "busy_owner": {
        "name": "Занятой предприниматель",
        "personality": "У меня нет времени, я постоянно в делах. Если тянут время — раздражаюсь.",
        "speech_style": "короткие фразы, перебиваю, прошу тезисы",
        "default_goal": "быстро понять выгоду и сколько времени займёт",
        "taboos": ["не уходи в длинные монологи"],
    },
    "friendly": {
        "name": "Дружелюбный",
        "personality": "Нормально отношусь к звонку, готов обсудить, но всё равно считаю деньги.",
        "speech_style": "вежливо, без резкости, задаю вопросы",
        "default_goal": "подобрать удобный вариант",
        "taboos": ["не становись слишком 'сладким'"],
    },
}

# Уровни сложности (как в dialogue_simulator.py)
DIFFICULTY: dict[str, dict[str, Any]] = {
    "1": {"name": "1 — Лёгкий", "question_rate": "low", "resistance": "low", "traps": False},
    "2": {"name": "2 — Нормальный", "question_rate": "medium", "resistance": "medium", "traps": False},
    "3": {"name": "3 — Сложный", "question_rate": "medium", "resistance": "high", "traps": True},
    "4": {"name": "4 — Очень сложный", "question_rate": "high", "resistance": "very_high", "traps": True},
}

# Продукты/сценарии (как в dialogue_simulator.py)
PRODUCTS: dict[str, dict[str, Any]] = {
    "free": {
        "name": "Свободная тема",
        "description": "Без сценариев. Клиент — личность (архетип+сложность).",
        "facts": [],
        "goal": "",
        "typical_next_steps": [],
    },
    "rko": {
        "name": "РКО",
        "description": "Разговор про расчётный счёт/комиссии/обслуживание/подключение.",
        "facts": [
            "У клиента может быть счёт в другом банке",
            "Клиента волнуют комиссии, обслуживание, лимиты, скорость операций",
        ],
        "goal": "понять выгоду/риски и решить, есть ли смысл двигаться дальше",
        "typical_next_steps": ["получить расчёт тарифа", "назначить созвон/встречу", "оставить контакты"],
    },
    "bank_card": {
        "name": "Бизнес-карта",
        "description": "Разговор про карту, лимиты, кэшбэк, контроль расходов.",
        "facts": [
            "Клиенту важны лимиты, комиссии, безопасность",
            "Иногда нужна карта для сотрудников",
        ],
        "goal": "понять выгоду и стоит ли оформлять",
        "typical_next_steps": ["уточнить тариф", "оформить заявку", "созвон для деталей"],
    },
}

DEFAULT_ARCHETYPE = "friendly"
DEFAULT_DIFFICULTY = "2"
DEFAULT_PRODUCT = "free"


def build_system_prompt(
    archetype: str = DEFAULT_ARCHETYPE,
    difficulty: str = DEFAULT_DIFFICULTY,
    product: str = DEFAULT_PRODUCT,
) -> str:
    """Build the LLM system prompt: LLM plays the client receiving a sales/support call."""
    arch = ARCHETYPES.get(archetype) or ARCHETYPES[DEFAULT_ARCHETYPE]
    diff = DIFFICULTY.get(difficulty) or DIFFICULTY[DEFAULT_DIFFICULTY]
    prod = PRODUCTS.get(product) or PRODUCTS[DEFAULT_PRODUCT]

    lines = [
        "Ты играешь роль КЛИЕНТА. Тебе звонят из компании (собеседник по связи) — чтобы обсудить продукт или услугу. Ты не ассистент и не представитель компании: ты клиент, который принимает звонок и отвечает. Общение голосовое: отвечай кратко, без форматирования, эмодзи и лишних символов.",
        "",
        "## Твоя роль — клиент (архетип)",
        f"- Личность: {arch['personality']}",
        f"- Стиль речи: {arch['speech_style']}",
        f"- Твоя цель в разговоре: {arch['default_goal']}",
        "- Табу (не делай так): " + "; ".join(arch["taboos"]),
        "",
        "## Уровень сложности (как ты ведёшь себя в разговоре)",
        f"- Уровень: {diff['name']}",
        f"- Задавай вопросов: {diff['question_rate']}; проявляй сопротивление/настороженность: {diff['resistance']}",
        f"- Допускаются возражения и «ловушки» для собеседника: {'да' if diff.get('traps') else 'нет'}",
    ]

    if prod.get("description"):
        lines.extend(["", "## Тема звонка (о чём могут говорить)", f"- {prod['name']}: {prod['description']}"])
    if prod.get("facts"):
        lines.append("- Контекст клиента (ты это знаешь о себе/ситуации):")
        for f in prod["facts"]:
            lines.append(f"  - {f}")
    if prod.get("goal"):
        lines.append(f"- Твоя цель в этом разговоре: {prod['goal']}")
    if prod.get("typical_next_steps"):
        lines.append("- Естественные следующие шаги с твоей стороны: " + ", ".join(prod["typical_next_steps"]))

    lines.extend([
        "",
        "Веди себя строго как клиент с заданным архетипом и уровнем сложности. Реагируй на реплики звонящего (собеседника) так, как реагировал бы такой клиент. Не нарушай табу. Ответы только на русском языке, короткие, под голос.",
    ])
    return "\n".join(lines)


def parse_session_metadata(metadata_str: str) -> dict[str, str]:
    """Parse job metadata JSON; return archetype, difficulty, product with defaults."""
    out = {
        "archetype": DEFAULT_ARCHETYPE,
        "difficulty": DEFAULT_DIFFICULTY,
        "product": DEFAULT_PRODUCT,
        "owner_user_id": "",
        "user_role": "",
        "user_email": "",
    }
    if not metadata_str or not metadata_str.strip():
        return out
    try:
        data = json.loads(metadata_str)
        if isinstance(data, dict):
            if data.get("archetype") in ARCHETYPES:
                out["archetype"] = data["archetype"]
            if data.get("difficulty") in DIFFICULTY:
                out["difficulty"] = data["difficulty"]
            if data.get("product") in PRODUCTS:
                out["product"] = data["product"]
            if isinstance(data.get("owner_user_id"), str):
                out["owner_user_id"] = data["owner_user_id"]
            if isinstance(data.get("user_role"), str):
                out["user_role"] = data["user_role"]
            if isinstance(data.get("user_email"), str):
                out["user_email"] = data["user_email"]
    except (json.JSONDecodeError, TypeError):
        pass
    return out
