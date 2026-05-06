# Evals

Автоматическая оценка качества AI-компонентов.
Запускается через Docker — локальная Python-среда не требуется.
Полностью изолирован от кода judge_service.

## Структура

```
evals/
├── docker-compose.yml       # chroma + eval runner
├── Dockerfile               # изолированный образ
├── run.sh                   # точка входа
├── requirements.txt         # зависимости eval-контейнера
├── results/                 # JSON-отчёты (в git не коммитятся)
├── knowledge_base/
│   ├── raw/bank_docs.xlsx   # источник FAQ для ChromaDB (в git не коммитится)
│   ├── normalized/          # структурированные политики оценки
│   ├── product/             # описание продукта РКО
│   └── scripts/             # скрипты звонков
├── scripts/
│   └── ingest_faq.py        # загрузка bank_docs.xlsx → ChromaDB
└── judge_rag/               # eval для knowledge-шага
    ├── dataset.py           # 9 тест-кейсов с expected_scores
    ├── schema.py            # pydantic-модели (автономные)
    ├── system_prompt.py     # промпт судьи (автономная копия)
    ├── judge.py             # вызов LLM напрямую
    ├── eval.py              # метрики: classifier + RAGAS
    └── run.py               # оркестрация и вывод результатов
```

## Быстрый старт

```bash
cd evals
OPENROUTER_API_KEY=sk-or-... OPENAI_API_KEY=sk-... ./run.sh
```

## Eval: `judge_rag`

Оценивает шаг **knowledge validation** — проверяет, корректно ли судья
определяет фактические ошибки менеджера по тарифам, лимитам и возражениям.

### Дизайн метрик

Судья — классификатор: для каждого критерия он выносит вердикт `True/False`.
Мы знаем правильный ответ для каждого кейса, поэтому используем классификационные метрики.

#### Первичные метрики (custom)

| Метрика | Что измеряет | Порог |
|---------|-------------|-------|
| `error_detection_rate` | Доля пойманных ошибок менеджера (recall по ошибкам) | ≥ 0.8 |
| `false_positive_rate` | Доля ложных срабатываний на чистых репликах | ≤ 0.2 |
| `criterion_accuracy` | % правильных вердиктов по всем критериям и кейсам | ≥ 0.85 |

`error_detection_rate` — наиважнейшая. Пропущенная ошибка = незаслуженно хорошая оценка менеджеру.

#### Вторичные метрики (RAGAS) — info only

Все RAGAS-метрики выводятся без порогов и не влияют на PASS/FAIL.

| Метрика | Что измеряет |
|---------|-------------|
| `answer_relevancy` | Объяснение судьи связно и относится к диалогу |
| `faithfulness` | Факты ответа присутствуют в контексте |
| `context_precision` | Точность retrieved-контекста (только KNOWLEDGE_RAG=1) |
| `context_recall` | Полнота retrieved-контекста (только KNOWLEDGE_RAG=1) |

> **Почему RAGAS-метрики не в порогах.** Судья — классификатор с embedded-знанием
> (эталон тарифов зашит в системный промпт), а не RAG-ответчик на вопрос пользователя.
> `faithfulness` хронически низкий (факты не из retrieved context — по замыслу).
> `answer_relevancy` волатильна (0.25–0.61 на одних данных): RAGAS ожидает пару
> «вопрос → ответ», а получает «транскрипт → структурированная оценка».

### Тест-кейсы (9 штук)

| ID | Ожидаемые ошибки | Что проверяет |
|----|-----------------|--------------|
| `correct_tariff_basic` | нет | Верная информация по тарифу «Основной» |
| `wrong_commission_rate` | limits=False | Комиссия 1% вместо 1,95% (тариф «Начальный») |
| `wrong_tariff_price` | tariff=False | Цена 2500 вместо 1990 руб. (тариф «Продвинутый») |
| `wrong_nachalny_transfer_limit` | limits=False | Лимит 200 тыс. вместо 150 тыс. |
| `wrong_prodvinuty_commission` | limits=False | Комиссия 2% вместо 1,49% |
| `correct_pro_tariff` | нет | Верная информация по тарифу «PRO» |
| `objection_sanctions` | нет | Обработка возражения по санкциям |
| `objection_existing_account` | нет | Возражение «уже есть счёт в другом банке» |
| `no_financial_topics` | нет | Нет финансовых тем — ошибок быть не должно |

### Пример вывода

```
============================================================
  JUDGE RAG EVAL RESULTS
============================================================

  -- Classifier metrics (primary) --

  PASS  error_detection_rate                       0.875  (min 0.8)
  PASS  false_positive_rate                        0.083  (max 0.2)
  PASS  criterion_accuracy                         0.926  (min 0.85)

  -- Per criterion --

  tariff_accuracy                        accuracy=1.000  edr=1.000
  limits_commissions_accuracy            accuracy=0.889  edr=0.750
  objection_handling                     accuracy=1.000  edr=n/a

  -- Per case --

  ✓ correct_tariff_basic                   3/3 correct
  ✓ wrong_commission_rate                  3/3 correct
  ✗ wrong_nachalny_transfer_limit          2/3 correct
  ...

  -- RAGAS metrics (secondary) --

  PASS  answer_relevancy                           0.720  (min 0.7)
  INFO  faithfulness                               0.210  (info only)

------------------------------------------------------------
  OVERALL: PASS
============================================================
```

### Два режима запуска

#### Режим по умолчанию (KNOWLEDGE_RAG=0)

Не требует ChromaDB. Все первичные метрики активны.

```bash
cd evals
OPENROUTER_API_KEY=sk-or-... OPENAI_API_KEY=sk-... ./run.sh
```

#### Режим с FAQ RAG (KNOWLEDGE_RAG=1)

Дополнительно активирует `context_precision` и `context_recall` (info only).

```bash
# Однократно: загрузить FAQ в ChromaDB
docker compose up chroma -d
docker compose run --rm eval python scripts/ingest_faq.py

# Запустить eval
OPENROUTER_API_KEY=sk-or-... OPENAI_API_KEY=sk-... KNOWLEDGE_RAG=1 ./run.sh
```

## Переменные окружения

| Переменная | По умолчанию | Описание |
|------------|-------------|----------|
| `OPENROUTER_API_KEY` | — | **Обязательна** |
| `OPENAI_API_KEY` | — | **Обязательна** — RAGAS embeddings для `answer_relevancy` |
| `OPENROUTER_MODEL` | `openai/gpt-4o-mini` | Модель для judge и RAGAS evaluator |
| `OPENROUTER_BASE_URL` | `https://openrouter.ai/api/v1` | |
| `KNOWLEDGE_RAG` | `0` | `1` — включить FAQ RAG |
| `CHROMA_HTTP_HOST` | `chroma` | Хост ChromaDB (только при KNOWLEDGE_RAG=1) |
| `CHROMA_HTTP_PORT` | `8000` | Порт ChromaDB |
