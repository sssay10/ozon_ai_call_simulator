# judge_v2

`judge_v2` запускается как альтернативный backend для `judge_service` через feature flag.

## Что это

- `legacy` backend: старый `LLMJudge`
- `hybrid_v2` backend: новый `Hybrid KB-backed judge`

Переключение делается через переменную окружения:

```bash
JUDGE_BACKEND=hybrid_v2
```

## Локальный запуск через Docker

Для локальной среды используйте `.env.development`:

```bash
JUDGE_BACKEND=hybrid_v2 docker compose --env-file .env.development -f docker-compose.dev.yml up -d --build
```

Если нужно пересобрать только `judge_service`:

```bash
JUDGE_BACKEND=hybrid_v2 docker compose --env-file .env.development -f docker-compose.dev.yml up -d --build --force-recreate judge_service
```

## Проверка, что включён именно judge_v2

```bash
curl http://localhost:8003/health
```

Ожидаемый ответ:

```json
{
  "status": "healthy",
  "judge_backend": "hybrid_kb_v2"
}
```

## Ручной запуск оценки

По `session_id`:

```bash
curl -X POST http://localhost:8003/api/judge-session \
  -H 'Content-Type: application/json' \
  -d '{"session_id":"<SESSION_ID>"}'
```

По `room_name`:

```bash
curl -X POST http://localhost:8003/api/judge-session \
  -H 'Content-Type: application/json' \
  -d '{"room_name":"<ROOM_NAME>"}'
```

## Важно

- Для локального запуска используйте `.env.development`, а не `.env`
- `judge_v2` включается только флагом и не заменяет legacy backend автоматически

