from __future__ import annotations

from typing import Callable, List

from .schemas import KBChunk, CriterionResult, TranscriptSegment


class LLMEvaluator:
    """
    llm_generate_json: функция, которая принимает prompt и возвращает dict.
    Это удобно, потому что пока можно передать любой твой текущий клиент.
    """

    def __init__(self, llm_generate_json: Callable[[str], dict]):
        self.llm_generate_json = llm_generate_json

    def build_prompt(
        self,
        criterion_id: str,
        segment: TranscriptSegment | None,
        kb_chunks: List[KBChunk],
    ) -> str:
        transcript_block = ""
        if segment:
            transcript_block = "\n".join(
                f"{u.speaker}: {u.text}" for u in segment.utterances
            )

        kb_block = "\n\n".join(
            [
                (
                    f"[{c.id}]\n"
                    f"doc_type={c.doc_type.value}\n"
                    f"priority={c.priority.value}\n"
                    f"rule={c.canonical_rule}\n"
                    f"positive_examples={c.positive_examples}\n"
                    f"negative_examples={c.negative_examples}\n"
                    f"pass_conditions={c.pass_conditions}\n"
                    f"fail_conditions={c.fail_conditions}\n"
                    f"null_conditions={c.null_conditions}"
                )
                for c in kb_chunks
            ]
        )

        return f"""
Ты оцениваешь один критерий звонка менеджера.

Критерий: {criterion_id}

Фрагмент транскрипта:
{transcript_block}

Релевантные правила:
{kb_block}

Верни строго JSON такого вида:
{{
  "decision": "pass|fail|null",
  "confidence": 0.0,
  "rationale_short": "краткое объяснение",
  "transcript_evidence": [{{"text": "цитата"}}],
  "kb_evidence": [{{"chunk_id": "rule_id"}}]
}}
""".strip()

    def evaluate(
        self,
        criterion_id: str,
        segment: TranscriptSegment | None,
        kb_chunks: List[KBChunk],
    ) -> CriterionResult:
        prompt = self.build_prompt(
            criterion_id=criterion_id,
            segment=segment,
            kb_chunks=kb_chunks,
        )
        raw = self.llm_generate_json(prompt)

        decision = raw.get("decision", "null")
        score = 1.0 if decision == "pass" else 0.0

        return CriterionResult(
            criterion_id=criterion_id,
            decision=decision,
            score=score,
            confidence=float(raw.get("confidence", 0.7)),
            rationale_short=raw.get("rationale_short", ""),
            transcript_evidence=raw.get("transcript_evidence", []),
            kb_evidence=raw.get("kb_evidence", []),
            metadata={"raw_llm": raw},
        )