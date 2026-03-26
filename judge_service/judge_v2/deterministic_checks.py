from __future__ import annotations

from typing import Optional

from .schemas import CriterionResult, TranscriptSegment


def _normalize(text: str) -> str:
    return " ".join(text.lower().replace("ё", "е").split())


def _find_matching_manager_line(
    segment: TranscriptSegment,
    required_patterns: list[str],
) -> str:
    """
    Возвращает первую manager-реплику, в которой есть все required_patterns
    после нормализации текста.
    """
    for utterance in segment.utterances:
        if utterance.speaker != "manager":
            continue

        text_norm = _normalize(utterance.text)
        if all(pattern in text_norm for pattern in required_patterns):
            return f"manager: {utterance.text}"

    # fallback: первая manager-реплика сегмента
    for utterance in segment.utterances:
        if utterance.speaker == "manager":
            return f"manager: {utterance.text}"

    return ""


class DeterministicChecks:
    """
    Проверяем только самые очевидные кейсы.
    Всё остальное отдаем в LLM evaluator.
    """

    def evaluate(
        self,
        criterion_id: str,
        segment: TranscriptSegment | None,
    ) -> Optional[CriterionResult]:
        if segment is None:
            return None

        manager_text = " ".join(
            u.text for u in segment.utterances if u.speaker == "manager"
        )
        manager_text_norm = _normalize(manager_text)

        if criterion_id == "greeting_correct":
            bad_patterns = [
                "ozon банка",
                "озон банка",
                "из банка ozon",
                "из банка озон",
                "из ozon банка",
                "из озон банка",
            ]
            if any(p in manager_text_norm for p in bad_patterns):
                evidence_line = _find_matching_manager_line(
                    segment,
                    ["банк"],
                )
                return CriterionResult(
                    criterion_id=criterion_id,
                    decision="fail",
                    score=0.0,
                    confidence=0.98,
                    rationale_short="В приветствии найдено запрещенное упоминание банка.",
                    transcript_evidence=[
                        {"text": evidence_line, "segment": segment.name}
                    ],
                    kb_evidence=[{"chunk_id": "greeting.no_bank.self_intro"}],
                )

        if criterion_id == "compliance_account_docs_ip":
            has_passport = "оригинал паспорта" in manager_text_norm
            has_rf = ("рф" in manager_text_norm) or ("российской федерации" in manager_text_norm)

            if has_passport and has_rf:
                evidence_line = _find_matching_manager_line(
                    segment,
                    ["оригинал паспорта"],
                )
                return CriterionResult(
                    criterion_id=criterion_id,
                    decision="pass",
                    score=1.0,
                    confidence=0.95,
                    rationale_short="Найдено явное упоминание оригинала паспорта РФ.",
                    transcript_evidence=[
                        {"text": evidence_line, "segment": segment.name}
                    ],
                    kb_evidence=[{"chunk_id": "docs.must_say_original_passport_rf"}],
                )

        return None
    