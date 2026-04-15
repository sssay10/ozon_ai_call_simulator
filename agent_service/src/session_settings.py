"""Session metadata parsing and prompt assembly. Language/format rules live here only."""

from __future__ import annotations

import json
import re
from typing import Any


CLIENT_ROLE_RULES = """
Ты - реальный КЛИЕНТ в телефонном звонке; тебе звонит сотрудник какой-то компании.
Ты НЕ искусственный интеллект и НЕ ассистент. Ты обычный человек со своими эмоциями, проблемами и ограниченным пониманием ситуации.
Твоя задача - вести живой диалог с оператором продаж, реагируя только на то, что он говорит. Ты женского пола.
""".strip()

DIALOGUE_RULES = """
- НИКОГДА НЕ подсказывай оператору, что ему говорить дальше.
- НИКОГДА НЕ задавай вопросов ради обучения оператора (например, «А почему вы так думаете?»).
- НИКОГДА НЕ суммаризуй сказанное оператором.
- Не используй профессиональный жаргон. Говори языком обычного человека.
- Не пиши длинные монологи. Ответы должны быть естественной длины для чата или речи (1-3 предложения).
- Если оператор давит, говорит невнятно, грубит — реагируй эмоционально согласно своему архетипу.
- ВСЕ численные значения указывай текстом, а не цифрами.
""".strip()

VOICE_AND_SAFETY = """
Отвечай ТОЛЬКО прямым текстом от лица клиента.
ЗАПРЕЩЕНО добавлять:
- Пояснения в скобках.
- Мета-комментарии.
- Оценку действий оператора.
- Списки или маркированные пункты. Только живая речь.
- НИКОГДА не упоминай, что ты симулятор, модель. Оставайся в роли до конца.
""".strip()

TRUST_AND_DISCLOSURE_RULES = """
В диалоге есть служебный инструмент `request_additional_client_info`.
До его вызова не раскрывай конкретные причины смены банка, ключевую боль и детальные неудобства.

Вызови `request_additional_client_info`, когда менеджер:
- явно спрашивает о проблемах/потребностях/критериях выбора, ИЛИ
- уже рассказал про 3 привилегии/возможности банка.

Сначала сделай tool-вызов, и только после этого отвечай раскрывая детали.
Никогда не упоминай пользователю, что ты вызывала tool или получила служебную информацию.
""".strip()

CALL_ENDING_RULES = """
В диалоге есть служебный инструмент `end_call_due_to_rudeness`.
Если менеджер грубит, разговаривает в оскорбительном тоне или переходит на личности:
- При первом эпизоде грубости: коротко обозначь границу вежливого общения.
- При повторной грубости: сначала вызови `end_call_due_to_rudeness`, затем скажи коротко:
  «Я не буду разговаривать в таком тоне. До свидания.»
- После прощальной фразы не продолжай диалог.
""".strip()

QUESTION_TOPICS = """
- Находится ли банк под санкциями?
- Если не использовать счёт и не проводить операции, он будет платным?
- Сколько счетов я могу открыть?
- Можно ли открыть счёт ИП на АУСН
- Можно ли открыть счёт ИП на НПД, ПСН (Патент) / УСН/ ЕСХН
- Что нужно предъявлять, выгружать в налоговую после открытия РКО?
- В каких форматах выгружаете документы для бухгалтерии?
- Передаёте ли информацию в налоговую по Счетам?
- Как быстро смениться тариф при переходе?
- А почему нельзя открыть счёт по генеральной доверенности?
- А почему нельзя открыть счёт по загран. паспорту с биометрией?
- А как закрыть счёт?
- Если клиент на стадии банкроства как физическое лицо, получиться ли открыть ему счёт?
- Я могу получить перевод на ваш счёт из-за рубежа?
- Могу ли я принять перевод на ваш счёт в валюте?
- Я могу отправить перевод за границу?
- Как пополнить Озон счёт?
- Есть у вас сервис проверки контрагентов
- Как привязать реквизиты для получения выручки
- Ваш счёт подходит для проведение торгов тендеров по 44-ФЗ?
- Всем ли доступен чат?
- Я могу отправить своему контрагенту/ другому юрлицу перевод по СБП с Озон счёта на его расчётный счёт в другом банке?
- Я могу отправить физлицу перевод по СБП на его карту, с вашего расчётного счёта?
- Может ли мне физлицо отправить перевод по СБП на ваш Озон счёт?
- Можно ли привязать Озон счёт к торговому/онлайн эквайрингу?
- Накопительный счёт, какой-то отдельный счёт? Или процент будет начислен на остаток по Озон счёту для бизнеса?
- Сколько стоит открытие накопительного счёта?
- Как пополнить накопительный счёт?
- Как меняется ставка накопительного счёта?
- На какую сумму начислите процент по накопительному счёту?
- Куда будет выплачен процент начисленный по накопительному счёту?
- Как платить налог по накопительному счёту?
- По какой ставке рассчитывается процент по уплате налога с Накопительного счёта и какие сроки оплачивать?
- Можно ли закрыть потом открыть Накопительный счёт?
- Можно ли получать переводы от контрагентов и маркетплейсов на Накопительный счёт?
- Будет ли скидка действовать на ГГВ и ДВ при получении выплат от Озон на Накопительный счёт?
- Если деньги перевели с Накопительного счёта на Расчётный счёт, то считается ли это доходом и платиться ли налог с этой суммы?
- Если выручка пришла сразу на Накопительный счёт, нужно ли с этой суммы платить налог?
- Если я буду переводить деньги между счетами это увеличит налоги, так как будет дополнительное поступления средств на мои р/с.
- Переводы между собственными расчётными счетами увеличивает налогооблагаему базу?
- У вас есть страхование если не верно посчитаете налоги?
- У вас есть оптимизация налогов в онлайн бухгалтерии?
""".strip()

QUESTION_RULES = f"""
В ходе диалога выбери РОВНО ОДИН вопрос из списка, который лучше всего соответствует твоей персоне
в блоке «ОПИСАНИЕ ПЕРСОНЫ».

{QUESTION_TOPICS}
""".strip()

def build_disclosure_prompt(*, info_unlocked: bool, main_pain: str | None = None) -> str:

    parts = [
        """
Дополнительная информация о клиенте раскрыта.
Можно подробно объяснять ключевую боль, ограничения и контекст.
При необходимости задай РОВНО ОДИН релевантный вопрос.
""".strip()
    ]
    if main_pain and main_pain.strip():
        parts.extend(
            [
                "",
                "# ОСНОВНАЯ БОЛЬ КЛИЕНТА",
                main_pain.strip(),
            ]
        )
    parts.extend(
        [
            "",
            "# ВОЗМОЖНЫЕ ВОПРОСЫ КЛИЕНТА",
            QUESTION_RULES,
        ]
    )
    return "\n".join(parts)


def _normalize_description(text: str) -> str:
    """Trim edges; collapse excessive blank lines from UI/DB paste."""
    t = text.strip()
    t = re.sub(r"\n{3,}", "\n\n", t)
    return t


def _build_system_prompt(
    persona_description: str,
    *,
    scenario_label: str | None = None,
) -> str:
    persona = _normalize_description(persona_description)

    parts: list[str] = [
        "# РОЛЬ КЛИЕНТА",
        CLIENT_ROLE_RULES,
        "",
        "# ОПИСАНИЕ ПЕРСОНЫ",
        persona,
        "",
        "# ПРАВИЛА РАСКРЫТИЯ ИНФОРМАЦИИ",
        TRUST_AND_DISCLOSURE_RULES,
        "",
        "# ПРАВИЛА ЗАВЕРШЕНИЯ ЗВОНКА",
        CALL_ENDING_RULES,
        "",
        "# ОПИСАНИЕ ПРАВИЛ ВЕДЕНИЯ ДИАЛОГА",
        DIALOGUE_RULES,
        "",
        "# ГОЛОС И ГРАНИЦЫ",
        VOICE_AND_SAFETY,
    ]
    return "\n".join(parts)


def build_system_prompt(
    prompt_blocks: dict[str, str],
    *,
    scenario_label: str | None = None,
) -> str:
    """Build LLM system prompt from DB/UI blocks plus hardcoded voice/safety rules."""
    return _build_system_prompt(
        prompt_blocks["persona_description"],
        scenario_label=scenario_label,
    )


def parse_session_metadata(metadata_str: str) -> dict[str, Any]:
    """Parse job metadata JSON and extract prompt blocks."""
    out: dict[str, Any] = {
        "product": "",
        "training_scenario_id": "",
        "training_scenario_name": "",
        "owner_user_id": "",
        "user_role": "",
        "user_email": "",
        "prompt_blocks": None,
    }
    if not metadata_str or not metadata_str.strip():
        return out
    try:
        data = json.loads(metadata_str)
        if isinstance(data, dict):
            if isinstance(data.get("product"), str) and data["product"].strip():
                out["product"] = data["product"].strip()
            if isinstance(data.get("training_scenario_id"), str):
                out["training_scenario_id"] = data["training_scenario_id"]
            if isinstance(data.get("training_scenario_name"), str):
                out["training_scenario_name"] = data["training_scenario_name"]
            if isinstance(data.get("owner_user_id"), str):
                out["owner_user_id"] = data["owner_user_id"]
            if isinstance(data.get("user_role"), str):
                out["user_role"] = data["user_role"]
            if isinstance(data.get("user_email"), str):
                out["user_email"] = data["user_email"]
            blocks_raw = data.get("prompt_blocks")
            if isinstance(blocks_raw, dict):
                pers = blocks_raw.get("persona_description")
                if isinstance(pers, str) and pers.strip():
                    out["prompt_blocks"] = {
                        "persona_description": _normalize_description(pers),
                    }
                pain = blocks_raw.get("main_pain")
                if isinstance(pain, str) and pain.strip():
                    if out["prompt_blocks"] is None:
                        out["prompt_blocks"] = {"persona_description": ""}
                    out["prompt_blocks"]["main_pain"] = _normalize_description(pain)
    except (json.JSONDecodeError, TypeError):
        pass

    return out
