from __future__ import annotations

import json
from pathlib import Path

from .schemas import Transcript


def fake_llm_generate_json(prompt: str) -> dict:
    prompt_lower = prompt.lower()

    transcript_marker = "фрагмент транскрипта:"
    kb_marker = "релевантные правила:"

    transcript_part = ""
    if transcript_marker in prompt_lower and kb_marker in prompt_lower:
        start = prompt_lower.index(transcript_marker) + len(transcript_marker)
        end = prompt_lower.index(kb_marker)
        transcript_part = prompt[start:end].strip()

    transcript_part_lower = transcript_part.lower()

    def extract_manager_lines(text: str) -> list[str]:
        lines = []
        for line in text.splitlines():
            line = line.strip()
            if line.lower().startswith("manager:"):
                lines.append(line)
        return lines

    def first_matching_line(lines: list[str], patterns: list[str]) -> str:
        for line in lines:
            line_lower = line.lower()
            if any(p in line_lower for p in patterns):
                return line
        return lines[0] if lines else ""

    manager_lines = extract_manager_lines(transcript_part)

    if "критерий: greeting_correct" in prompt_lower:
        bad_patterns = [
            "ozon банка",
            "озон банка",
            "из банка ozon",
            "из банка озон",
            "из ozon банка",
            "из озон банка",
        ]
        evidence_line = manager_lines[0] if manager_lines else ""

        if any(p in transcript_part_lower for p in bad_patterns):
            return {
                "decision": "fail",
                "confidence": 0.96,
                "rationale_short": "В приветствии есть запрещенное упоминание банка.",
                "transcript_evidence": [{"text": evidence_line}],
                "kb_evidence": [{"chunk_id": "greeting.no_bank.self_intro"}],
            }

        return {
            "decision": "pass",
            "confidence": 0.88,
            "rationale_short": "Приветствие выглядит корректным.",
            "transcript_evidence": [{"text": evidence_line}],
            "kb_evidence": [{"chunk_id": "greeting.no_bank.self_intro"}],
        }

    if "критерий: congratulation_given" in prompt_lower:
        evidence_line = first_matching_line(
            manager_lines,
            ["поздрав", "регистрац"],
        )

        if "поздрав" in transcript_part_lower:
            return {
                "decision": "pass",
                "confidence": 0.91,
                "rationale_short": "Найдено поздравление с регистрацией.",
                "transcript_evidence": [{"text": evidence_line}],
                "kb_evidence": [{"chunk_id": "onboarding.must_congratulate"}],
            }

        return {
            "decision": "fail",
            "confidence": 0.82,
            "rationale_short": "Поздравление с регистрацией не найдено.",
            "transcript_evidence": [],
            "kb_evidence": [{"chunk_id": "onboarding.must_congratulate"}],
        }

    if "критерий: compliance_free_account_ip" in prompt_lower:
        evidence_line = first_matching_line(
            manager_lines,
            ["бесплат", "счет", "счёт", "расчетн", "расчётн"],
        )

        if "бесплат" in transcript_part_lower and (
            "счет" in transcript_part_lower or "счёт" in transcript_part_lower
        ):
            return {
                "decision": "pass",
                "confidence": 0.89,
                "rationale_short": "Менеджер сообщил про бесплатный расчетный счет.",
                "transcript_evidence": [{"text": evidence_line}],
                "kb_evidence": [{"chunk_id": "onboarding.must_offer_free_account"}],
            }

        return {
            "decision": "fail",
            "confidence": 0.80,
            "rationale_short": "Упоминание бесплатного расчетного счета не найдено.",
            "transcript_evidence": [],
            "kb_evidence": [{"chunk_id": "onboarding.must_offer_free_account"}],
        }

    if "критерий: compliance_account_docs_ip" in prompt_lower:
        evidence_line = first_matching_line(
            manager_lines,
            ["оригинал паспорта", "паспорт рф", "российской федерации"],
        )

        if "оригинал паспорта" in transcript_part_lower and (
            "рф" in transcript_part_lower or "российской федерации" in transcript_part_lower
        ):
            return {
                "decision": "pass",
                "confidence": 0.95,
                "rationale_short": "Найдено требование про оригинал паспорта РФ.",
                "transcript_evidence": [{"text": evidence_line}],
                "kb_evidence": [{"chunk_id": "docs.must_say_original_passport_rf"}],
            }

        return {
            "decision": "fail",
            "confidence": 0.83,
            "rationale_short": "Требование про оригинал паспорта РФ не найдено.",
            "transcript_evidence": [],
            "kb_evidence": [{"chunk_id": "docs.must_say_original_passport_rf"}],
        }

    return {
        "decision": "null",
        "confidence": 0.50,
        "rationale_short": "Нет логики для данного критерия в fake LLM.",
        "transcript_evidence": [],
        "kb_evidence": [],
    }


def load_fixture_as_transcript(path: Path) -> Transcript:
    data = json.loads(path.read_text(encoding="utf-8"))

    utterances = []
    for i, msg in enumerate(data.get("transcript", [])):
        utterances.append(
            {
                "turn_index": i,
                "speaker": msg.get("role", "unknown"),
                "text": msg.get("text", ""),
            }
        )

    return Transcript.model_validate(
        {
            "session_id": data.get("id", path.stem),
            "scenario_id": data.get("scenario_id", "unknown_scenario"),
            "utterances": utterances,
        }
    )
