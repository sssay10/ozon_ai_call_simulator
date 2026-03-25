# 🧠 `llm_judge` — Модуль оценки тренировочных диалогов

Модуль `llm_judge` автоматически оценивает тренировочные звонки менеджеров в голосовом тренажёре Ozon Bank по продаже расчётно-кассового обслуживания (РКО).  
Он выдаёт **структурированную, объективную и диагностическую обратную связь**, основанную на:
- compliance-фразах,
- сценарии продаж (AIDA + этапы),
- навыках продаж (вежливость, работа с возражениями, эмоциональная устойчивость).

---

## 🎯 Цель

Заменить ручной разбор звонков тренером на **автоматизированную, масштабируемую и воспроизводимую оценку**, которая:
- проверяет соблюдение compliance-фраз,
- выявляет ошибки с таймкодами,
- даёт рекомендации по улучшению навыков.

---

## 🧱 Архитектура
```
judge_service/
    ├── main.py              # FastAPI-приложение
    ├── database.py          # Подключение к БД и модель TrainingSession
    ├── models.py            # Pydantic-модели
    ├── judge.py             # Основной класс LLMJudge
    ├── parser.py            # Парсер ответов LLM
    ├── client_classifier.py # Классификация клиента
    ├── scenarios.py         # Конфигурация сценариев
    ├── judge_prompt.txt     # Единый промпт для оценки
    └── backends/
        ├── ollama_backend.py
        └── openrouter_backend.py
```

---

## 🚀 Запуск

### Требования

- macOS 14 Sonoma или новее (для Ollama).
- Python 3.10+
- PostgreSQL

### Установка

1. Установите Ollama: [https://ollama.com/download](https://ollama.com/download)
   - Требуется macOS 14 Sonoma или новее.
2. Запустите Ollama:

```bash
ollama serve
```

3. Установите зависимости:

```bash
cd judge_service
uv sync
```

4. Задайте переменные окружения:

- `DATABASE_URL` — Postgres с таблицами `dialogue_sessions`, `dialogue_messages`, `judge_results`
- `LLM_PROVIDER` — `openrouter` или `ollama`
- Если `LLM_PROVIDER=openrouter`:
  - `OPENROUTER_API_KEY`
  - `OPENROUTER_MODEL` (опционально)
  - `OPENROUTER_BASE_URL` (опционально, по умолчанию OpenRouter)
- Если `LLM_PROVIDER=ollama`:
  - `OLLAMA_BASE_URL`
  - `OLLAMA_MODEL`

Можно начать с `.env.example`.

5. Запустите приложение:

```bash
uv run uvicorn main:app --host 0.0.0.0 --port 8003 --reload
```

---

## 🧪 Функциональность

- `/start_training` — создаёт новую сессию в БД.
- `/generate_client_response` — генерирует ответ ИИ-клиента (через Ollama).
- `/evaluate` — оценивает диалог, используя `LLMJudge`.
- `/sessions/{session_id}` — возвращает данные сессии (включая оценку).

---

## 🧪 Тестирование

### Тест через `curl`

```bash
curl -X 'POST' \
  'http://127.0.0.1:8003/api/judge-session' \
  -H 'Content-Type: application/json' \
  -d '{
  "session_id": "<dialogue_session_uuid>",
  "product": "RKO / novice / level 1"
}'
```

---

## 📋 Пример ответа `/evaluate`

```json
{
  "scores": {
    "greeting_correct": true,
    "compliance_free_account_ip": true
  },
  "total_score": 85,
  "critical_errors": [],
  "feedback_positive": ["Хорошее начало звонка"],
  "feedback_improvement": ["Уточните тарифы"],
  "compliance_check": {
    "Расчетный счет от Озон Банка — бесплатный для новых продавцов.": true
  }
}
```

---

## 🧩 Интеграции

- **PostgreSQL** — хранение сессий и транскриптов.
- **Ollama** — генерация ответов и оценка (модели `qwen2:1.5b` и `qwen2:7b`).
- **Pydantic** — валидация запросов и ответов.
- **SQLAlchemy** — ORM для работы с БД.




