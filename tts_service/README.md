# TTS service (Silero)

Single instance of Silero TTS in one process. All requests use the same model via `asyncio.to_thread()`.

- **Port:** 8002 (default)
- **Endpoints:** `POST /synthesize` (JSON `{"text": "...", "speaker": "xenia", "sample_rate": 8000}` → raw PCM int16), `GET /health`

```bash
cd tts_service
uv sync
uv run uvicorn main:app --host 0.0.0.0 --port 8002
```
