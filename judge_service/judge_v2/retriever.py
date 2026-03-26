from __future__ import annotations

from typing import List, Tuple

from .schemas import KBChunk, TranscriptSegment


PRIORITY_SCORE = {
    "critical": 3.0,
    "high": 2.0,
    "medium": 1.0,
    "low": 0.5,
}

DOC_TYPE_SCORE = {
    "eval_policy": 2.5,
    "policy": 2.0,
    "fact": 1.0,
}


class SimpleCriterionRetriever:
    """
    Улучшенный MVP retrieval:
    - сильный приоритет exact criterion match
    - stage/evidence_window учитываются явно
    - stage mismatch штрафуется
    - keyword overlap влияет, но слабее
    - чужие policy/eval chunks штрафуются сильнее
    """

    def __init__(self, chunks: List[KBChunk]):
        self.chunks = chunks

    def retrieve(
        self,
        criterion_id: str,
        scenario_id: str,
        segment: TranscriptSegment | None,
        top_k: int = 3,
    ) -> List[KBChunk]:
        segment_text = ""
        segment_name = ""

        if segment:
            segment_text = " ".join(u.text.lower() for u in segment.utterances)
            segment_name = segment.name

        scored: List[Tuple[float, KBChunk]] = []

        for chunk in self.chunks:
            score = 0.0
            criterion_match = criterion_id in chunk.criterion_tags

            # 1. Exact criterion match — главный сигнал
            if criterion_match:
                score += 10.0
            else:
                # Более сильный штраф за чужой критерий
                score -= 3.0

                # Если это нормативный chunk не того критерия,
                # дополнительно штрафуем, чтобы он не обгонял нужные правила
                if chunk.doc_type.value in {"policy", "eval_policy"}:
                    score -= 2.5

            # 2. Scenario match
            if scenario_id in chunk.scenario_tags:
                score += 3.0

            # 3. Stage match / mismatch
            if segment_name:
                if segment_name in chunk.applicability.stage:
                    score += 3.0
                elif chunk.applicability.stage:
                    score -= 1.5

            # 4. Evidence window match
            if segment_name and chunk.retrieval_hints.evidence_window == segment_name:
                score += 2.0

            # 5. Priority + doc type
            score += PRIORITY_SCORE.get(chunk.priority.value, 0.0)
            score += DOC_TYPE_SCORE.get(chunk.doc_type.value, 0.0)

            # 6. Keywords — полезны, но не должны ломать criterion-first ranking
            keyword_hits = 0
            for kw in chunk.retrieval_hints.keywords:
                if kw.lower() in segment_text:
                    keyword_hits += 1

            score += min(keyword_hits * 0.35, 1.0)

            # 7. Лёгкий multiplier
            score *= chunk.retrieval_hints.priority_boost

            # Оставляем только осмысленные кандидаты
            if score > 0:
                scored.append((score, chunk))

        scored.sort(key=lambda x: x[0], reverse=True)
        return [chunk for _, chunk in scored[:top_k]]
    
    