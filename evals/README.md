# Evals

Автоматическая оценка AI-компонентов. Запускается через Docker.

## Структура

```
evals/
├── judge_rag/        # eval для шага knowledge validation
│   ├── dataset.py    # 9 тест-кейсов с expected_scores
│   ├── eval.py       # метрики
│   ├── judge.py      # вызов LLM
│   ├── run.py        # оркестрация и вывод
│   ├── schema.py     # pydantic-модели
│   └── system_prompt.py
├── knowledge_base/
│   ├── raw/          # bank_docs.xlsx — не коммитится
│   ├── normalized/   # политики оценки (для будущих eval)
│   ├── product/      # описание продукта РКО
│   └── scripts/      # скрипты звонков
├── scripts/
│   └── ingest_faq.py # загрузка bank_docs.xlsx → ChromaDB
├── results/          # JSON-отчёты — не коммитятся
├── Dockerfile
├── docker-compose.yml
├── requirements.txt
└── run.sh
```

## Запуск

```bash
cd evals
OPENROUTER_API_KEY=sk-or-... ./run.sh
```

С FAQ RAG (требует предварительной загрузки bank_docs.xlsx и установки chromadb):

```bash
docker compose up chroma -d
docker compose run --rm eval pip install chromadb
docker compose run --rm eval python scripts/ingest_faq.py
OPENROUTER_API_KEY=sk-or-... KNOWLEDGE_RAG=1 ./run.sh
```

## Метрики

| Метрика | Порог | Описание |
|---------|-------|----------|
| `error_detection_rate` | ≥ 0.8 | Доля пойманных ошибок менеджера |
| `false_positive_rate` | ≤ 0.2 | Доля ложных срабатываний на чистых репликах |
| `criterion_accuracy` | ≥ 0.85 | % правильных вердиктов по всем критериям |

## Тест-кейсы (9 штук)

| ID | Ожидаемые ошибки | Что проверяет |
|----|-----------------|--------------|
| `correct_tariff_basic` | нет | Верная информация по тарифу «Основной» |
| `wrong_commission_rate` | tariff=F, limits=F | Комиссия 1% вместо 1,95% |
| `wrong_tariff_price` | tariff=F | Цена 2500 вместо 1990 руб. |
| `wrong_nachalny_transfer_limit` | tariff=F, limits=F | Лимит 200 тыс. вместо 150 тыс. |
| `wrong_prodvinuty_commission` | tariff=F, limits=F | Комиссия 2% вместо 1,49% |
| `correct_pro_tariff` | нет | Верная информация по тарифу «PRO» |
| `objection_sanctions` | нет | Возражение по санкциям |
| `objection_existing_account` | нет | Возражение «уже есть счёт» |
| `no_financial_topics` | нет | Нет финансовых тем |

## Переменные окружения

| Переменная | По умолчанию | Описание |
|------------|-------------|----------|
| `OPENROUTER_API_KEY` | — | **Обязательна** |
| `OPENROUTER_MODEL` | `openai/gpt-4o-mini` | Модель для judge |
| `OPENROUTER_BASE_URL` | `https://openrouter.ai/api/v1` | |
| `KNOWLEDGE_RAG` | `0` | `1` — включить FAQ RAG |
| `CHROMA_HTTP_HOST` | `chroma` | Хост ChromaDB (только при KNOWLEDGE_RAG=1) |
| `CHROMA_HTTP_PORT` | `8000` | Порт ChromaDB |
