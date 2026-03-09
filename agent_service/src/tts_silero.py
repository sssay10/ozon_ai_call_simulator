"""LiveKit TTS plugin for Silero v5 Russian via TTS service API (no local model)."""

from __future__ import annotations

import httpx
from livekit.agents.tts import (
    AudioEmitter,
    ChunkedStream,
    TTS,
    TTSCapabilities,
)
from livekit.agents.types import APIConnectOptions, DEFAULT_API_CONNECT_OPTIONS
from livekit.agents.utils import shortuuid

SILERO_SAMPLE_RATE = 8000
SILERO_SPEAKER = "xenia"
SILERO_MODEL_ID = "v5_ru"


class _SileroChunkedStream(ChunkedStream):
    """ChunkedStream that fetches PCM from TTS service and pushes to the emitter."""

    async def _run(self, output_emitter: AudioEmitter) -> None:
        output_emitter.initialize(
            request_id=shortuuid(),
            sample_rate=self._tts.sample_rate,
            num_channels=self._tts.num_channels,
            mime_type="audio/pcm",
            stream=False,
        )
        async with httpx.AsyncClient(timeout=30.0) as client:
            resp = await client.post(
                f"{self._tts._base_url}/synthesize",
                json={
                    "text": self._input_text,
                    "speaker": self._tts._speaker,
                    "sample_rate": self._tts.sample_rate,
                },
            )
        resp.raise_for_status()
        pcm_bytes = resp.content
        if pcm_bytes:
            output_emitter.push(pcm_bytes)
        output_emitter.flush()


class SileroTTS(TTS):
    """Text-to-speech using Silero v5 Russian via TTS service API."""

    def __init__(
        self,
        *,
        base_url: str,
        sample_rate: int = SILERO_SAMPLE_RATE,
        speaker: str = SILERO_SPEAKER,
    ) -> None:
        super().__init__(
            capabilities=TTSCapabilities(streaming=False, aligned_transcript=False),
            sample_rate=sample_rate,
            num_channels=1,
        )
        self._base_url = base_url.rstrip("/")
        self._speaker = speaker

    @property
    def model(self) -> str:
        return f"silero_{SILERO_MODEL_ID}"

    @property
    def provider(self) -> str:
        return "snakers4/silero-models"

    def synthesize(
        self,
        text: str,
        *,
        conn_options: APIConnectOptions = DEFAULT_API_CONNECT_OPTIONS,
    ) -> ChunkedStream:
        return _SileroChunkedStream(
            tts=self,
            input_text=text,
            conn_options=conn_options,
        )
