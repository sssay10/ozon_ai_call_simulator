# STT service (T-one)

Single instance of T-one (StreamingCTCPipeline) in one process. All requests use the same model via `asyncio.to_thread()`.

- **Port:** 8001 (default)
- **Env:** `TONE_MODELS_DIR` — path to T-one model files (required)
- **Endpoints:** `POST /recognize` (raw int32 LE 8 kHz mono → `{"text": "..."}`), `GET /health`

```bash
cd stt_service
uv sync
export TONE_MODELS_DIR=./tone_models   # or absolute path to T-one model files
uv run uvicorn main:app --host 0.0.0.0 --port 8001
```
