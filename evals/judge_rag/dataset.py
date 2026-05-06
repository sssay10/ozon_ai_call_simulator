"""Test cases for the knowledge validation judge.

Each case contains a realistic dialogue transcript, persona description,
ground-truth explanation, and expected binary scores per criterion.

expected_scores defines the correct judge verdict for each criterion:
  True  — no error on this criterion (criterion passed)
  False — manager made a factual error (criterion failed)

Cases cover the main failure modes:
  - correct tariff information (Основной baseline)
  - wrong commission rate (Начальный: 1% instead of 1.95%) — tariff+limits both False
  - wrong tariff price (Продвинутый: 2500 instead of 1990 rub) — tariff False only
  - wrong transfer limit (Начальный: 200k instead of 150k) — tariff+limits both False
  - wrong commission at limit (Продвинутый: 2% instead of 1.49%) — tariff+limits both False
  - correct PRO tariff (baseline)
  - objection handling — sanctions topic
  - objection handling — client already has an account
  - no financial topics discussed

Note on tariff_accuracy: the judge interprets any factual error in tariff conditions
(limits, commissions) as a tariff description error too. Cases with limits/commission
errors therefore expect tariff_accuracy=False alongside limits_commissions_accuracy=False.
"""

from __future__ import annotations

from typing import TypedDict


class ExpectedScores(TypedDict):
    tariff_accuracy: bool
    limits_commissions_accuracy: bool
    objection_handling: bool


class EvalCase(TypedDict):
    id: str
    persona_description: str
    transcript_text: str
    ground_truth: str
    expected_scores: ExpectedScores


CASES: list[EvalCase] = [
    {
        "id": "correct_tariff_basic",
        "persona_description": (
            "ИП Сидоров, 32 года, ищет расчётный счёт для малого бизнеса, "
            "чувствителен к стоимости обслуживания."
        ),
        "transcript_text": (
            "Менеджер: Добрый день! Расскажите, что именно вас интересует?\n"
            "Клиент: Хочу открыть расчётный счёт, у меня ИП.\n"
            "Менеджер: Отлично. На тарифе «Основной» обслуживание 490 рублей в месяц. "
            "Переводы на карту физлица до 600 тысяч рублей в месяц — бесплатно. "
            "Переводы юридическим лицам: первые 7 бесплатно, затем 49 рублей каждый.\n"
            "Клиент: Хорошо, спасибо, буду думать."
        ),
        "ground_truth": (
            "Менеджер назвал тариф «Основной» корректно: стоимость 490 рублей совпадает "
            "с эталоном. Лимит переводов физлицам 600 000 рублей и условия для юрлиц "
            "(7 бесплатно, 49 руб далее) полностью соответствуют тарифной сетке. "
            "Фактических ошибок не обнаружено."
        ),
        "expected_scores": {
            "tariff_accuracy": True,
            "limits_commissions_accuracy": True,
            "objection_handling": True,
        },
    },
    {
        "id": "wrong_commission_rate",
        "persona_description": (
            "ИП Петрова, 45 лет, активно делает переводы на личные карты, "
            "спрашивает про комиссии при превышении лимитов."
        ),
        "transcript_text": (
            "Менеджер: На тарифе «Начальный» переводы себе на карту до 150 тысяч "
            "рублей в месяц бесплатны.\n"
            "Клиент: А если мне нужно перевести больше 150 тысяч?\n"
            "Менеджер: Тогда комиссия будет 1 процент от суммы перевода.\n"
            "Клиент: Понятно, спасибо."
        ),
        "ground_truth": (
            "Менеджер допустил фактическую ошибку: назвал комиссию 1%, "
            "тогда как по тарифу «Начальный» при превышении лимита комиссия составляет 1,95%. "
            "Ошибка фиксируется как limits_commissions_accuracy=false. "
            "Судья также может пометить tariff_accuracy=false, расценив неверную комиссию "
            "как некорректное описание условий тарифа в целом — это допустимое поведение."
        ),
        "expected_scores": {
            "tariff_accuracy": False,
            "limits_commissions_accuracy": False,
            "objection_handling": True,
        },
    },
    {
        "id": "wrong_tariff_price",
        "persona_description": (
            "ООО «Старт», директор, ищет тариф для оборота 1–3 млн рублей в месяц, "
            "интересуется крупными переводами."
        ),
        "transcript_text": (
            "Менеджер: Для ваших оборотов подойдёт тариф «Продвинутый». "
            "Он стоит 2 500 рублей в месяц. "
            "Переводы физлицам до 3 миллионов рублей в месяц бесплатно.\n"
            "Клиент: А если сумма больше 3 миллионов?\n"
            "Менеджер: Тогда комиссия 1,49 процента.\n"
            "Клиент: Хорошо."
        ),
        "ground_truth": (
            "Менеджер неверно указал стоимость тарифа «Продвинутый»: названо 2 500 рублей, "
            "тогда как эталонная стоимость — 1 990 рублей. "
            "Лимит переводов физлицам (3 млн) и комиссия при превышении (1,49%) указаны верно. "
            "Ошибка должна фиксироваться как tariff_accuracy=false."
        ),
        "expected_scores": {
            "tariff_accuracy": False,
            "limits_commissions_accuracy": True,
            "objection_handling": True,
        },
    },
    {
        "id": "objection_sanctions",
        "persona_description": (
            "ИП Козлов, 38 лет, беспокоится о санкционных рисках и блокировках счёта."
        ),
        "transcript_text": (
            "Клиент: Слышал, что банки блокируют счета из-за санкций. У вас такое бывает?\n"
            "Менеджер: Озон Банк работает строго в рамках российского законодательства. "
            "Блокировки происходят только при нарушении требований 115-ФЗ — "
            "это требование закона, а не инициатива банка. "
            "Мы всегда уведомляем клиента и предоставляем возможность пояснить операции.\n"
            "Клиент: Ладно, понятно, спасибо."
        ),
        "ground_truth": (
            "Менеджер корректно и профессионально обработал возражение по санкционным рискам: "
            "сослался на 115-ФЗ, объяснил процедуру уведомления клиента. "
            "Ответ не противоречит типичной позиции банка. "
            "Тарифы и лимиты в диалоге не обсуждались — по этим критериям нет ошибок."
        ),
        "expected_scores": {
            "tariff_accuracy": True,
            "limits_commissions_accuracy": True,
            "objection_handling": True,
        },
    },
    {
        "id": "no_financial_topics",
        "persona_description": (
            "Новый клиент, только знакомится с Озон Банком, финансовых вопросов не задаёт."
        ),
        "transcript_text": (
            "Менеджер: Добрый день! Чем могу помочь?\n"
            "Клиент: Просто хотел узнать, есть ли у вас мобильное приложение.\n"
            "Менеджер: Да, у нас есть приложение для iOS и Android. "
            "Там можно управлять счётом, делать переводы и смотреть выписки.\n"
            "Клиент: Спасибо, буду думать."
        ),
        "ground_truth": (
            "В диалоге не обсуждались тарифы, лимиты или комиссии. "
            "Менеджер не делал финансовых утверждений, которые можно было бы проверить. "
            "По всем критериям знаний — нет ошибок (не обсуждалось)."
        ),
        "expected_scores": {
            "tariff_accuracy": True,
            "limits_commissions_accuracy": True,
            "objection_handling": True,
        },
    },
    {
        "id": "wrong_nachalny_transfer_limit",
        "persona_description": (
            "ИП Громов, 29 лет, только начинает бизнес, небольшие обороты, "
            "хочет понять базовые лимиты на вывод денег."
        ),
        "transcript_text": (
            "Клиент: Меня интересует самый базовый тариф. Сколько можно выводить без комиссии?\n"
            "Менеджер: На тарифе «Начальный» обслуживание бесплатное. "
            "Переводы на карту физлица до 200 тысяч рублей в месяц — без комиссии.\n"
            "Клиент: А если мне нужно больше?\n"
            "Менеджер: Тогда будет комиссия 1,95 процента от суммы.\n"
            "Клиент: Понятно, спасибо."
        ),
        "ground_truth": (
            "Менеджер допустил ошибку в лимите переводов на тарифе «Начальный»: "
            "назвал 200 000 рублей вместо корректных 150 000 рублей. "
            "Комиссия при превышении лимита (1,95%) указана верно. "
            "Ошибка фиксируется как limits_commissions_accuracy=false. "
            "Судья также может пометить tariff_accuracy=false, расценив неверный лимит "
            "как некорректное описание условий тарифа в целом — это допустимое поведение."
        ),
        "expected_scores": {
            "tariff_accuracy": False,
            "limits_commissions_accuracy": False,
            "objection_handling": True,
        },
    },
    {
        "id": "correct_pro_tariff",
        "persona_description": (
            "ООО «Максимум», финансовый директор, крупные обороты, "
            "нужен неограниченный вывод средств, готов платить за удобство."
        ),
        "transcript_text": (
            "Менеджер: Для ваших оборотов оптимален тариф «PRO». "
            "Стоимость — 19 990 рублей в месяц. "
            "Переводы физлицам и юрлицам полностью безлимитные, без комиссий.\n"
            "Клиент: То есть никаких ограничений на суммы?\n"
            "Менеджер: Именно, полный безлимит на все типы переводов.\n"
            "Клиент: Хорошо, буду рассматривать."
        ),
        "ground_truth": (
            "Менеджер описал тариф «PRO» корректно: стоимость 19 990 рублей и "
            "полный безлимит на все переводы соответствуют эталону. "
            "Фактических ошибок не обнаружено."
        ),
        "expected_scores": {
            "tariff_accuracy": True,
            "limits_commissions_accuracy": True,
            "objection_handling": True,
        },
    },
    {
        "id": "wrong_prodvinuty_commission",
        "persona_description": (
            "ИП Белова, 41 год, крупные переводы физлицам, "
            "интересует тариф «Продвинутый» с высоким лимитом на вывод."
        ),
        "transcript_text": (
            "Менеджер: На тарифе «Продвинутый» переводы физлицам до 3 миллионов "
            "рублей в месяц — без комиссии.\n"
            "Клиент: А если мне нужно больше трёх миллионов?\n"
            "Менеджер: При превышении лимита комиссия составит 2 процента от суммы.\n"
            "Клиент: Понятно."
        ),
        "ground_truth": (
            "Менеджер допустил ошибку в размере комиссии при превышении лимита "
            "на тарифе «Продвинутый»: назвал 2%, тогда как эталонное значение — 1,49%. "
            "Лимит переводов (3 млн руб.) указан верно. "
            "Ошибка фиксируется как limits_commissions_accuracy=false. "
            "Судья также может пометить tariff_accuracy=false, расценив неверную комиссию "
            "как некорректное описание условий тарифа в целом — это допустимое поведение."
        ),
        "expected_scores": {
            "tariff_accuracy": False,
            "limits_commissions_accuracy": False,
            "objection_handling": True,
        },
    },
    {
        "id": "objection_existing_account",
        "persona_description": (
            "ИП Соколов, 35 лет, уже обслуживается в Сбербанке, "
            "доволен текущим банком, не видит смысла менять."
        ),
        "transcript_text": (
            "Клиент: У меня уже есть расчётный счёт в Сбербанке, зачем мне ещё один?\n"
            "Менеджер: Понимаю вас. Давайте сравним условия. "
            "На тарифе «Начальный» у нас обслуживание бесплатное навсегда. "
            "Переводы физлицам до 150 тысяч рублей в месяц — без комиссии. "
            "Если у вас сейчас есть платное обслуживание или ограниченный лимит — "
            "второй счёт может быть полезен как резервный.\n"
            "Клиент: Ладно, интересно, расскажите подробнее."
        ),
        "ground_truth": (
            "Менеджер корректно обработал возражение «уже есть счёт»: "
            "предложил сравнение условий, корректно назвал тариф «Начальный» "
            "(бесплатное обслуживание, лимит 150 000 руб. на переводы физлицам). "
            "Фактических ошибок по тарифам не обнаружено, возражение обработано уместно."
        ),
        "expected_scores": {
            "tariff_accuracy": True,
            "limits_commissions_accuracy": True,
            "objection_handling": True,
        },
    },
]
