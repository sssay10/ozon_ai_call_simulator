"""LiveKit STT plugin for T-one via STT service API (no local model)."""

from __future__ import annotations

import logging
import numpy as np
import httpx
from livekit import rtc
from livekit.agents.stt import (
    STT,
    STTCapabilities,
    SpeechData,
    SpeechEvent,
    SpeechEventType,
)
from livekit.agents.types import (
    DEFAULT_API_CONNECT_OPTIONS,
    NOT_GIVEN,
    APIConnectOptions,
    NotGivenOr,
)
from livekit.agents.utils import AudioBuffer, merge_frames

logger = logging.getLogger("stt_tone")

# T-one expects 8 kHz mono, int32 samples in range [-32768, 32767]
TONE_SAMPLE_RATE = 8000


def _audio_buffer_to_int32_8k(buffer: AudioBuffer) -> np.ndarray:
    """Convert LiveKit audio buffer to int32 mono 8 kHz for T-one."""
    frame = merge_frames(buffer)
    if isinstance(frame, list):
        frame = rtc.combine_audio_frames(frame)
    sr = frame.sample_rate
    # bytes → int16
    data = np.frombuffer(frame.data, dtype=np.int16)
    if frame.num_channels > 1:
        logger.info("Reshaping data from %s channels to 1 channel", frame.num_channels)
        data = data.reshape(-1, frame.num_channels).mean(axis=1).astype(np.int16)
    # resample to 8 kHz if needed
    if sr != TONE_SAMPLE_RATE:
        logger.info("Resampling from %s Hz to %s Hz", sr, TONE_SAMPLE_RATE)
        duration_sec = len(data) / sr
        n_out = int(duration_sec * TONE_SAMPLE_RATE)
        indices = np.linspace(0, len(data) - 1, n_out, dtype=np.float32)
        data = np.interp(indices, np.arange(len(data)), data).astype(np.int16)
    return data.astype(np.int32)


class ToneSTT(STT):
    """Speech-to-text using T-one via STT service API."""

    def __init__(
        self,
        *,
        base_url: str,
    ) -> None:
        super().__init__(
            capabilities=STTCapabilities(
                streaming=False,
                interim_results=False,
                diarization=False,
                offline_recognize=True,
            )
        )
        self._base_url = base_url.rstrip("/")

    @property
    def model(self) -> str:
        return "T-one"

    @property
    def provider(self) -> str:
        return "voicekit"

    async def _recognize_impl(
        self,
        buffer: AudioBuffer,
        *,
        language: NotGivenOr[str] = NOT_GIVEN,
        conn_options: APIConnectOptions = DEFAULT_API_CONNECT_OPTIONS,
    ) -> SpeechEvent:
        audio = _audio_buffer_to_int32_8k(buffer)
        if len(audio) == 0:
            return SpeechEvent(
                type=SpeechEventType.FINAL_TRANSCRIPT,
                alternatives=[SpeechData(language="ru", text="")],
            )
        body = audio.tobytes()
        async with httpx.AsyncClient(timeout=30.0) as client:
            resp = await client.post(
                f"{self._base_url}/recognize",
                content=body,
                headers={"Content-Type": "application/octet-stream"},
            )
        resp.raise_for_status()
        data = resp.json()
        text = data.get("text", "").strip()
        return SpeechEvent(
            type=SpeechEventType.FINAL_TRANSCRIPT,
            alternatives=[SpeechData(language="ru", text=text)],
        )

    async def aclose(self) -> None:
        pass
