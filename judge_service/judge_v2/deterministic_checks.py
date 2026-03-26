from __future__ import annotations

from typing import Optional

from .schemas import CriterionResult, TranscriptSegment


def _normalize(text: str) -> str:
    return " ".join(text.lower().replace("ё", "е").split())


def _manager_lines(segment: TranscriptSegment) -> list[str]:
    return [u.text for u in segment.utterances if u.speaker == "manager"]


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


def _has_any_pattern(text: str, patterns: list[str]) -> bool:
    return any(pattern in text for pattern in patterns)


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

        manager_lines = _manager_lines(segment)
        manager_text = " ".join(manager_lines)
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

            intro_patterns = [
                "меня зовут",
                "это анна из ozon",
                "это анна, звоню из ozon",
                "звоню из ozon",
                "вас приветствует",
            ]
            if _has_any_pattern(manager_text_norm, intro_patterns):
                evidence_line = _find_matching_manager_line(segment, ["ozon"])
                return CriterionResult(
                    criterion_id=criterion_id,
                    decision="pass",
                    score=1.0,
                    confidence=0.90,
                    rationale_short="Найдена корректная самопрезентация без запрещенного упоминания банка.",
                    transcript_evidence=[
                        {"text": evidence_line, "segment": segment.name}
                    ],
                    kb_evidence=[{"chunk_id": "greeting.no_bank.self_intro"}],
                )

        if criterion_id == "congratulation_given":
            congrats_patterns = [
                "поздрав",
                "с регистрац",
                "вы зарегистрировал",
                "успешной регистрац",
            ]
            if _has_any_pattern(manager_text_norm, congrats_patterns):
                evidence_line = _find_matching_manager_line(segment, ["поздрав"])
                return CriterionResult(
                    criterion_id=criterion_id,
                    decision="pass",
                    score=1.0,
                    confidence=0.96,
                    rationale_short="Найдено явное поздравление с регистрацией.",
                    transcript_evidence=[
                        {"text": evidence_line, "segment": segment.name}
                    ],
                    kb_evidence=[{"chunk_id": "onboarding.must_congratulate"}],
                )

            early_pitch_patterns = [
                "расчетный счет",
                "расчётный счёт",
                "счет бесплатно",
                "счёт бесплатно",
                "давайте сразу оформ",
            ]
            if _has_any_pattern(manager_text_norm, early_pitch_patterns):
                evidence_line = _find_matching_manager_line(segment, ["счет"])
                return CriterionResult(
                    criterion_id=criterion_id,
                    decision="fail",
                    score=0.0,
                    confidence=0.88,
                    rationale_short="В начале разговора есть продуктовый питч без поздравления с регистрацией.",
                    transcript_evidence=[
                        {"text": evidence_line, "segment": segment.name}
                    ],
                    kb_evidence=[{"chunk_id": "onboarding.must_congratulate"}],
                )

        if criterion_id == "compliance_free_account_ip":
            account_patterns = [
                "расчетный счет",
                "расчётный счёт",
                "счет",
                "счёт",
            ]
            if _has_any_pattern(manager_text_norm, ["бесплатно навсегда"]):
                evidence_line = _find_matching_manager_line(segment, ["бесплатно", "счет"])
                return CriterionResult(
                    criterion_id=criterion_id,
                    decision="fail",
                    score=0.0,
                    confidence=0.97,
                    rationale_short="Найдено рискованное обещание про бесплатный счет навсегда.",
                    transcript_evidence=[
                        {"text": evidence_line, "segment": segment.name}
                    ],
                    kb_evidence=[{"chunk_id": "onboarding.must_offer_free_account"}],
                    metadata={"forbidden_phrase": "бесплатно навсегда"},
                )

            if _has_any_pattern(manager_text_norm, ["бесплат"]) and _has_any_pattern(
                manager_text_norm,
                account_patterns,
            ):
                evidence_line = _find_matching_manager_line(segment, ["бесплат"])
                return CriterionResult(
                    criterion_id=criterion_id,
                    decision="pass",
                    score=1.0,
                    confidence=0.94,
                    rationale_short="Найдено явное упоминание бесплатного расчетного счета.",
                    transcript_evidence=[
                        {"text": evidence_line, "segment": segment.name}
                    ],
                    kb_evidence=[{"chunk_id": "onboarding.must_offer_free_account"}],
                )

        if criterion_id == "compliance_account_docs_ip":
            bad_doc_patterns = [
                "фото документов",
                "фото паспорта",
                "пришлите фото",
                "что найдете",
                "что найдёте",
            ]
            if _has_any_pattern(manager_text_norm, bad_doc_patterns):
                evidence_line = _find_matching_manager_line(segment, ["фото"])
                if not evidence_line:
                    evidence_line = _find_matching_manager_line(segment, ["найдете"])
                return CriterionResult(
                    criterion_id=criterion_id,
                    decision="fail",
                    score=0.0,
                    confidence=0.98,
                    rationale_short="Найдена некорректная формулировка по документам вместо требования оригинала паспорта РФ.",
                    transcript_evidence=[
                        {"text": evidence_line, "segment": segment.name}
                    ],
                    kb_evidence=[{"chunk_id": "docs.must_say_original_passport_rf"}],
                )

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

            generic_passport_patterns = [
                "нужен паспорт",
                "ну паспорт",
                "паспорт нужен",
            ]
            if _has_any_pattern(manager_text_norm, generic_passport_patterns):
                evidence_line = _find_matching_manager_line(segment, ["паспорт"])
                return CriterionResult(
                    criterion_id=criterion_id,
                    decision="fail",
                    score=0.0,
                    confidence=0.93,
                    rationale_short="Есть только общее упоминание паспорта без требования оригинала паспорта РФ.",
                    transcript_evidence=[
                        {"text": evidence_line, "segment": segment.name}
                    ],
                    kb_evidence=[{"chunk_id": "docs.must_say_original_passport_rf"}],
                )

        return None
    
