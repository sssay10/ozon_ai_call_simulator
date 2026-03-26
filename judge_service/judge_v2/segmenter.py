from __future__ import annotations

from typing import List, Optional

from .schemas import Transcript, TranscriptSegment


class SimpleSegmenter:
    """
    MVP-segmenter:
    - первые 4 реплики -> greeting_block
    - середина -> body_block
    - последние 4 реплики -> closing_block
    """

    def segment(self, transcript: Transcript) -> List[TranscriptSegment]:
        utts = transcript.utterances
        if not utts:
            return []

        greeting = utts[:4]
        closing = utts[-4:] if len(utts) >= 4 else utts
        body = utts[4:-4] if len(utts) > 8 else utts[4:]

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