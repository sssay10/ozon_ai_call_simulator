# Load Tests

Нагрузочные тесты на базе [Locust](https://locust.io/).
Три независимых тестовых блока — каждый запускается одной командой через Docker Compose.

## Структура

```
load_tests/
├── requirements.txt          # зависимости для convert_report.py (locust, numpy, playwright)
├── .gitignore
│
├── stt_service/              # изолированный тест STT (T-one / ONNX)
│   ├── locustfile.py         # сценарий: POST /recognize с синтетическим аудио
│   ├── docker-compose.yml
│   ├── Dockerfile.locust
│   ├── convert_report.py     # HTML → PDF через playwright
│   ├── run.sh
│   └── reports/              # HTML, CSV, PDF (в git не коммитятся)
│
├── tts_service/              # изолированный тест TTS (Silero v5)
│   ├── locustfile.py         # сценарий: POST /synthesize, 3 категории текста
│   ├── docker-compose.yml
│   ├── convert_report.py
│   ├── run.sh
│   └── reports/
│
└── system/                   # E2E тест всего стека
    ├── locustfile.py         # 3 UserClass: BackendApiUser (30%), AgentTurnUser (60%), JudgeUser (10%)
    ├── docker-compose.yml    # postgres + stt + tts + backend + judge + chroma + locust
    ├── Dockerfile.locust
    ├── seed_test_data.sql    # тестовый пользователь + сессии + кэшированные оценки
    ├── convert_report.py
    ├── run.sh
    └── reports/
```

---

## Предварительные требования

### 1. Docker и Docker Compose

```bash
docker --version        # >= 24
docker compose version  # >= 2.20
```

### 2. Python 3.10+ (только для convert_report.py)

```bash
pip install -r load_tests/requirements.txt
playwright install chromium
```

### 3. Модели T-one для STT

Модели **не входят в репозиторий** (~5.5 ГБ). Скачать отдельно и положить в `stt_service/tone_models/` (нужны `model.onnx`, `kenlm.bin` и сопутствующие файлы). Без них `stt_service` не запустится.

### 4. Модель Silero TTS

Скачивается **автоматически** при первом запуске (~100 МБ), кэшируется в Docker volume `tts_model_cache`.

---

## Запуск тестов

### STT сервис

```bash
cd load_tests/stt_service
./run.sh                                           # 100 пользователей, 120 сек
LOCUST_USERS=50 LOCUST_RUN_TIME=60s ./run.sh
```

> Первый запуск: 3–4 мин на загрузку `kenlm.bin` (5.4 ГБ) — скрипт ждёт автоматически.

### TTS сервис

```bash
cd load_tests/tts_service
./run.sh                                           # 100 пользователей, 120 сек
LOCUST_USERS=50 LOCUST_RUN_TIME=60s ./run.sh
```

### E2E системный тест

```bash
cd load_tests/system

# Без LLM (STT + TTS под нагрузкой, бесплатно)
./run.sh                                           # 30 пользователей, 180 сек
LOCUST_USERS=80 LOCUST_RUN_TIME=240s ./run.sh

# С реальным LLM
OPENROUTER_API_KEY=sk-or-... ./run.sh
```

> Первый запуск: ~4 мин на старт STT + скачивание Silero. Последующие — ~4 мин только на STT.

---

## Параметры запуска

| Переменная | По умолчанию | Описание |
|---|---|---|
| `LOCUST_USERS` | 100 (stt/tts), 30 (system) | Количество виртуальных пользователей |
| `LOCUST_RUN_TIME` | 120s (stt/tts), 180s (system) | Длительность теста |
| `LOCUST_SPAWN_RATE` | 10 (stt/tts), 5 (system) | Пользователей в секунду при рампе |
| `OPENROUTER_API_KEY` | — | Ключ для LLM-шага в system тесте |
| `AGENT_OPENROUTER_MODEL` | openai/gpt-4o-mini | Модель LLM |

---

## Отчёты

После завершения в `reports/`:

| Файл | Содержимое |
|---|---|
| `report.html` | Интерактивный Locust-отчёт с графиками |
| `report.pdf` | PDF-версия |
| `stats_stats.csv` | Агрегированные метрики по эндпоинтам |
| `stats_stats_history.csv` | Временной ряд: RPS, p50/p95/p99 |
| `stats_failures.csv` | Ошибки с деталями |
| `stats_exceptions.csv` | Python-исключения в locustfile |

> Отчёты исключены из git (`.gitignore`).

---

## Известные ограничения

- **LiveKit / WebRTC** не тестируется — требует UDP-медиапоток, несовместим с Locust
- **LLM в E2E тесте** без `OPENROUTER_API_KEY` заменяется фиксированной фразой — STT и TTS тестируются корректно, сквозная задержка без учёта реального LLM
- **exit code 1** от Locust при наличии failures — нормально, если % ошибок < 1%; PDF-отчёт генерируется всегда

---

## Тестовое окружение

| Параметр | Значение |
|---|---|
| Модель | MacBook Air 15", M3, 2024 |
| Чип | Apple M3 (8-core CPU) |
| ОЗУ | 16 ГБ |
| ОС | macOS Sonoma 14.7.1 |

> Результаты актуальны для этого окружения. На серверном железе показатели будут отличаться.

---

## Результаты тестирования (апрель 2026)

| Тест | Конфигурация | Ключевой результат |
|---|---|---|
| STT isolated | 100 users, 2s audio | Потолок 7 RPS, комфорт до 30–35 users |
| TTS isolated | 100 users, mixed text | Потолок 5.5 RPS, комфорт до 25–30 users |
| E2E system | 30 users | 0 ошибок, STT p50=260мс, TTS p50=130мс |
| E2E system | 80 users | STT достиг потолка (p50=2100мс), TTS в норме |

**Вывод:** один инстанс STT достаточен для ~80 одновременных пользователей в реальном сценарии (с LLM цикл длиннее — нагрузка на STT ниже).
