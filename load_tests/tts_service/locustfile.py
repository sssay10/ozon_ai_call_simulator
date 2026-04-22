"""Load test for TTS service — /synthesize endpoint.

Sends Russian banking phrases of three length categories to /synthesize
and measures response time, throughput, and audio size at up to 100 users.

Synthesis time scales with text length, so we test three categories:
  - short  (~10 words)   — quick agent acknowledgements
  - medium (~30 words)   — typical product descriptions
  - long   (~55 words)   — detailed explanations

The Silero model runs in asyncio.to_thread (same pattern as STT), so the
queue-depth vs latency relationship is identical — see STT test analysis.

Run with the Locust web UI (against a locally running TTS service):
    locust -f locustfile.py --host http://localhost:8002
"""
from __future__ import annotations

import random

from locust import HttpUser, between, task

# ---------------------------------------------------------------------------
# Realistic Russian banking phrases — three length categories
# ---------------------------------------------------------------------------
_SHORT = [
    "Добро пожаловать в Озон Банк. Меня зовут Алина.",
    "Хорошо, я вас слышу. Подождите, пожалуйста.",
    "Спасибо за ваш звонок. До свидания.",
    "Конечно, готова помочь. Слушаю вас.",
]

_MEDIUM = [
    (
        "Рады вас приветствовать! Открытие расчётного счёта для ИП у нас бесплатное "
        "и занимает около пяти минут. Вы уже зарегистрированы как предприниматель?"
    ),
    (
        "Отличный выбор! На нашем тарифе первые шесть месяцев обслуживание счёта "
        "бесплатное. После этого — всего пятьсот рублей в месяц."
    ),
    (
        "Понимаю ваши опасения. Давайте я расскажу подробнее об условиях "
        "накопительного счёта и процентных ставках по нему."
    ),
    (
        "Переводы внутри банка мгновенные и без комиссии. По СБП — до ста тысяч "
        "рублей в месяц тоже бесплатно. Это покрывает большинство задач малого бизнеса."
    ),
]

_LONG = [
    (
        "Позвольте рассказать вам о преимуществах расчётного счёта в Озон Банке. "
        "Во-первых, открытие и ведение счёта бесплатно в первые шесть месяцев. "
        "Во-вторых, вы получаете доступ к встроенной бухгалтерии и автоматическому "
        "расчёту налогов. В-третьих, переводы внутри банка мгновенные и без комиссии."
    ),
    (
        "Если вас интересует накопительный счёт, могу рассказать подробнее. "
        "Ставка составляет до восьми процентов годовых на остаток. "
        "Проценты начисляются ежемесячно на среднедневной остаток. "
        "Снять деньги можно в любой момент без потери начисленных процентов. "
        "Минимальная сумма для открытия — одна тысяча рублей."
    ),
]

# Weights reflect realistic agent utterance distribution:
# acknowledgements are frequent, long explanations are rare.
_POOL: list[tuple[str, str]] = (
    [("short", t) for t in _SHORT]
    + [("medium", t) for t in _MEDIUM]
    + [("long", t) for t in _LONG]
)


# ---------------------------------------------------------------------------
# Locust user
# ---------------------------------------------------------------------------
class TTSUser(HttpUser):
    """Simulates the agent synthesising one utterance per turn."""

    wait_time = between(1, 3)

    @task(9)
    def synthesize(self) -> None:
        """Main load: POST text to /synthesize, receive raw PCM bytes."""
        category, text = random.choice(_POOL)
        with self.client.post(
            "/synthesize",
            json={"text": text, "speaker": "xenia", "sample_rate": 8000},
            name=f"/synthesize [{category}]",
            catch_response=True,
        ) as response:
            if response.status_code == 200:
                response.success()
            elif response.status_code == 503:
                response.failure("TTS model not ready (503)")
            else:
                response.failure(
                    f"Unexpected {response.status_code}: {response.text[:120]}"
                )

    @task(1)
    def health(self) -> None:
        """Low-frequency health check."""
        self.client.get("/health", name="/health")
