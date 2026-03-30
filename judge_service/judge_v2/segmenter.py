from __future__ import annotations

from typing import List, Optional

from .schemas import Transcript, TranscriptSegment


class SimpleSegmenter:
    """
    Простой rule-based segmenter:
    - greeting_block: старт разговора до первого явного product/docs pitch
    - body_block: основная продуктовая и документная часть
    - closing_block: финальные договоренности и завершение
    """

    BODY_MARKERS = (
        "счет",
        "счёт",
        "тариф",
        "бесплат",
        "документ",
        "паспорт",
        "оформ",
        "открыт",
    )

    CLOSING_MARKERS = (
        "я подумаю",
        "подумаю",
        "тогда жду",
        "жду документы",
        "сегодня",
    )

    @staticmethod
    def _normalize(text: str) -> str:
        return " ".join(text.lower().replace("ё", "е").split())

    def _find_body_start(self, utts) -> int:
        for i, utterance in enumerate(utts):
            if utterance.speaker != "manager":
                continue

            text_norm = self._normalize(utterance.text)
            if any(marker in text_norm for marker in self.BODY_MARKERS):
                return i

        return min(4, len(utts))

    def _find_closing_start(self, utts, body_start: int) -> int:
        for i in range(max(body_start + 1, 0), len(utts)):
            utterance = utts[i]
            text_norm = self._normalize(utterance.text)

            if utterance.speaker == "client" and any(
                marker in text_norm for marker in ("я подумаю", "подумаю")
            ):
                return i

            if utterance.speaker == "manager" and any(
                marker in text_norm for marker in self.CLOSING_MARKERS
            ):
                return i

        return len(utts)

    def segment(self, transcript: Transcript) -> List[TranscriptSegment]:
        utts = transcript.utterances
        if not utts:
            return []

        body_start = self._find_body_start(utts)
        closing_start = self._find_closing_start(utts, body_start)

        greeting = utts[:body_start]
        body = utts[body_start:closing_start]
        closing = utts[closing_start:]

        segments: List[TranscriptSegment] = []

        if greeting:
            segments.append(
                TranscriptSegment(
                    name="greeting_block",
                    start_turn=greeting[0].turn_index,
                    end_turn=greeting[-1].turn_index,
                    utterances=greeting,
                )
            )

        if body:
            segments.append(
                TranscriptSegment(
                    name="body_block",
                    start_turn=body[0].turn_index,
                    end_turn=body[-1].turn_index,
                    utterances=body,
                )
            )

        if closing:
            segments.append(
                TranscriptSegment(
                    name="closing_block",
                    start_turn=closing[0].turn_index,
                    end_turn=closing[-1].turn_index,
                    utterances=closing,
                )
            )

        return segments

    @staticmethod
    def get_segment(
        segments: List[TranscriptSegment],
        name: str,
    ) -> Optional[TranscriptSegment]:
        for seg in segments:
            if seg.name == name:
                return seg
        return None
