"""
STT service: single instance of T-one (StreamingCTCPipeline) in one process.
All requests are handled via asyncio.to_thread() — no model copy, no multiprocessing.
"""
import asyncio
import logging
import os

import numpy as np
from contextlib import asynccontextmanager
from fastapi import FastAPI, HTTPException, Request
from pydantic import BaseModel

from tone import StreamingCTCPipeline

logger = logging.getLogger("stt_service")

# One global pipeline instance — loaded once at startup, shared by all requests
_pipeline: StreamingCTCPipeline | None = None


def _recognize_sync(audio_int32: np.ndarray) -> str:
    """Run T-one offline recognition. Called in thread; uses global _pipeline."""
    if _pipeline is None:
        raise RuntimeError("STT pipeline not loaded")
    if len(audio_int32) == 0:
        return ""
    phrases = _pipeline.forward_offline(audio_int32)
    return " ".join(p.text for p in phrases).strip() if phrases else ""


@asynccontextmanager
async def lifespan(app: FastAPI):
    global _pipeline
    models_dir = os.environ.get("TONE_MODELS_DIR")
    if not models_dir:
        raise RuntimeError("TONE_MODELS_DIR environment variable is required")
    logger.info("Loading T-one pipeline from %s (single instance)", models_dir)
    _pipeline = StreamingCTCPipeline.from_local(models_dir)
    logger.info("T-one pipeline ready")
    yield
    _pipeline = None


app = FastAPI(title="STT Service (T-one)", lifespan=lifespan)


class RecognizeResponse(BaseModel):
    text: str


@app.post("/recognize", response_model=RecognizeResponse)
async def recognize(request: Request):
    """
    Recognize speech from raw audio bytes.
    Body: raw int32 little-endian, 8 kHz mono (same as T-one input).
    """
    global _pipeline
    if _pipeline is None:
        raise HTTPException(status_code=503, detail="STT pipeline not loaded")
    body = await request.body()
    if len(body) == 0:
        return RecognizeResponse(text="")
    try:
        # bytes -> int32 array
        audio = np.frombuffer(body, dtype=np.int32)
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Invalid audio bytes: {e}") from e
    # Run in thread so we don't block the event loop; same process, same model
    text = await asyncio.to_thread(_recognize_sync, audio)
    return RecognizeResponse(text=text)


@app.get("/health")
async def health():
    return {"status": "ok", "model_loaded": _pipeline is not None}
