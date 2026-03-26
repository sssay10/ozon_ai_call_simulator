"""
TTS service: single instance of Silero TTS in one process.
All requests are handled via asyncio.to_thread() — no model copy, no multiprocessing.
"""
import asyncio
import logging

import numpy as np
import torch
from contextlib import asynccontextmanager
from fastapi import FastAPI, HTTPException
from fastapi.responses import Response
from pydantic import BaseModel

logger = logging.getLogger("tts_service")

SILERO_SAMPLE_RATE = 8000
SILERO_SPEAKER = "xenia"
SILERO_MODEL_ID = "v5_ru"

# One global model instance — loaded once at startup
_silero_model = None


def _synthesize_sync(text: str, speaker: str, sample_rate: int) -> bytes:
    """Run Silero TTS. Called in thread; uses global _silero_model."""
    if _silero_model is None:
        raise RuntimeError("TTS model not loaded")

    audio = _silero_model.apply_tts(
        text=text,
        speaker=speaker,
        sample_rate=sample_rate,
        put_accent=True,
        put_yo=True,
        put_stress_homo=True,
        put_yo_homo=True
    )

    if isinstance(audio, torch.Tensor):
        audio = audio.numpy()
    audio_int16 = (np.clip(audio, -1.0, 1.0) * 32767).astype(np.int16)
    return audio_int16.tobytes()


def _load_silero():
    model, _ = torch.hub.load(
        repo_or_dir="snakers4/silero-models",
        model="silero_tts",
        language="ru",
        speaker=SILERO_MODEL_ID,
    )
    return model


@asynccontextmanager
async def lifespan(app: FastAPI):
    global _silero_model
    logger.info("Loading Silero TTS (single instance)")
    _silero_model = await asyncio.to_thread(_load_silero)
    logger.info("Silero TTS ready")
    yield
    _silero_model = None


app = FastAPI(title="TTS Service (Silero)", lifespan=lifespan)


class SynthesizeRequest(BaseModel):
    text: str
    speaker: str = SILERO_SPEAKER
    sample_rate: int = SILERO_SAMPLE_RATE


@app.post("/synthesize")
async def synthesize(req: SynthesizeRequest):
    """
    Synthesize speech from text. Returns raw PCM int16, mono, at given sample_rate.
    """
    global _silero_model
    if _silero_model is None:
        raise HTTPException(status_code=503, detail="TTS model not loaded")
    if not req.text.strip():
        return Response(content=b"", media_type="application/octet-stream")
    try:
        pcm_bytes = await asyncio.to_thread(
            _synthesize_sync,
            req.text,
            req.speaker,
            req.sample_rate,
        )
    except Exception as e:
        logger.exception("TTS synthesis failed")
        raise HTTPException(status_code=500, detail=str(e)) from e
    return Response(content=pcm_bytes, media_type="application/octet-stream")


@app.get("/health")
async def health():
    return {"status": "ok", "model_loaded": _silero_model is not None}
