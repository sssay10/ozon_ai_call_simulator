# Load Tests

Нагрузочные тесты на базе [Locust](https://locust.io/).
Три независимых тестовых блока — каждый запускается одной командой через Docker Compose.

## Структура

```
load_tests/
├── requirements.txt          # зависимости для convert_report.py (locust, numpy, playwright)
├── .gitignore                # исключает сгенерированные отчёты
│
├── stt_service/              # изолированный тест STT (T-one / ONNX)
│   ├── locustfile.py         # сценарий: POST /recognize с синтетическим аудио
│   ├── docker-compose.yml    # stt_service + locust
│   ├── Dockerfile.locust     # locust + numpy
│   ├── convert_report.py     # HTML → PDF через playwright
│   ├── run.sh                # точка входа
│   └── reports/              # HTML, CSV, PDF (в git не коммитятся)
│
├── tts_service/              # изолированный тест TTS (Silero v5)
│   ├── locustfile.py         # сценарий: POST /synthesize, 3 категории текста
│   ├── docker-compose.yml    # tts_service + locust
│   ├── convert_report.py
│   ├── run.sh
│   └── reports/
│
└── system/                   # E2E тест всего стека
    ├── locustfile.py         # 3 UserClass: BackendApiUser, AgentTurnUser, JudgeUser
    ├── docker-compose.yml    # postgres + stt + tts + backend + judge + chroma + locust
    ├── Dockerfile.locust     # locust + numpy
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

Устанавливается один раз из корня проекта:

```bash
pip install -r load_tests/requirements.txt
playwright install chromium   # скачивает headless Chromium (~150 МБ), однократно
```

### 3. Модели T-one для STT (обязательно для stt_service и system тестов)

Модели **не входят в репозиторий** из-за размера (~5.5 ГБ). Их нужно скачать отдельно и положить в папку `stt_service/tone_models/`.

Проверь что файлы на месте:

```bash
ls stt_service/tone_models/
# должны быть: model.onnx, kenlm.bin и другие файлы модели
```

Без этих файлов `stt_service` не запустится.

### 4. Модель Silero TTS (для tts_service и system тестов)

Скачивается **автоматически** при первом запуске (~100 МБ) и кэшируется в Docker volume `tts_model_cache`. Последующие запуски используют кэш.

---

## Запуск тестов

Все тесты запускаются из соответствующей директории. Параметры переопределяются переменными окружения.

### STT сервис (изолированный)

```bash
cd load_tests/stt_service
./run.sh                                           # 100 пользователей, 120 сек
LOCUST_USERS=50 LOCUST_RUN_TIME=60s ./run.sh      # кастомные параметры
```

**Важно:** первый запуск занимает 3–4 минуты пока загружается `kenlm.bin` (5.4 ГБ). Это нормально — скрипт ждёт автоматически.

### TTS сервис (изолированный)

```bash
cd load_tests/tts_service
./run.sh                                           # 100 пользователей, 120 сек
LOCUST_USERS=50 LOCUST_RUN_TIME=60s ./run.sh
```

**Важно:** первый запуск скачивает Silero модель (~100 МБ). Последующие запуски используют кэш — старт занимает ~10 сек.

### E2E системный тест

Тестирует полный стек: backend_service + STT + TTS + judge_service под одновременной нагрузкой. LLM-шаг опциональный.

```bash
cd load_tests/system

# Без LLM (рекомендуется для начала — бесплатно, STT+TTS под нагрузкой)
./run.sh                                           # 30 пользователей, 180 сек
LOCUST_USERS=80 LOCUST_RUN_TIME=240s ./run.sh     # стресс-тест

# С реальным LLM (OpenRouter)
OPENROUTER_API_KEY=sk-or-... ./run.sh
OPENROUTER_API_KEY=sk-or-... LOCUST_USERS=50 LOCUST_RUN_TIME=300s ./run.sh
```

**Важно:**
- Нужны файлы T-one модели (см. требования выше)
- Первый запуск: ~4 мин ожидания старта STT + скачивание Silero. Последующие — ~4 мин только на STT.
- E2E тест поднимает postgres с чистой БД каждый раз, `seed_test_data.sql` вставляет тестовые данные автоматически.

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

После завершения в `reports/` появляются:

| Файл | Содержимое |
|---|---|
| `report.html` | Интерактивный Locust-отчёт с графиками |
| `report.pdf` | PDF-версия (генерируется через playwright) |
| `stats_stats.csv` | Агрегированные метрики по эндпоинтам |
| `stats_stats_history.csv` | Временной ряд: RPS, p50/p95/p99 каждую секунду |
| `stats_failures.csv` | Все ошибки с деталями |
| `stats_exceptions.csv` | Python-исключения в locustfile |

> Отчёты исключены из git (`.gitignore`). Папки `reports/` сохранены через `.gitkeep`.

---

## E2E тест — что тестируется

В `system/locustfile.py` три класса пользователей работают одновременно:

| UserClass | Вес | Что делает |
|---|---|---|
| `BackendApiUser` | 30% | Логин → список сессий → список сценариев |
| `AgentTurnUser` | 60% | STT → (LLM опционально) → TTS последовательно |
| `JudgeUser` | 10% | Запрос результатов оценки звонка из БД |

В отчёте каждый шаг виден отдельно:

```
[backend] auth/login
[backend] sessions/list
[backend] scenarios/list
[turn] 1_stt/recognize        ← основная нагрузка на STT
[turn] 2_llm/chat             ← только если OPENROUTER_API_KEY задан
[turn] 3_tts/synthesize       ← нагрузка на TTS
[judge] session-results
```

---

## Известные ограничения

- **LiveKit / WebRTC** не тестируется — требует UDP-медиапоток, несовместим с Locust
- **LLM в E2E тесте** без OPENROUTER_API_KEY заменяется фиксированной короткой фразой — STT и TTS при этом тестируются корректно, но сквозная задержка не учитывает реальное время LLM
- **exit code 1** от Locust при наличии любых failures — это нормально если % ошибок мал (< 1%); PDF отчёт всегда генерируется

---

## Результаты тестирования (апрель 2026)

| Тест | Конфигурация | Ключевой результат |
|---|---|---|
| STT isolated | 100 users, 2s audio | Потолок 7 RPS, комфорт до 30–35 users |
| TTS isolated | 100 users, mixed text | Потолок 5.5 RPS, комфорт до 25–30 users |
| E2E system | 30 users | 0 ошибок, STT p50=260мс, TTS p50=130мс |
| E2E system | 80 users | STT достиг потолка (p50=2100мс), TTS в норме |

**Вывод:** один инстанс STT достаточен для 80 одновременных пользователей в реальном сценарии (с LLM цикл длиннее, нагрузка на STT ниже).
