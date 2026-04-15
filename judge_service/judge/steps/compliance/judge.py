"""Compliance / script step judge class."""

from __future__ import annotations

import logging
import re
from typing import ClassVar

from langchain_core.language_models import BaseChatModel
from langchain_core.messages import HumanMessage, SystemMessage

from judge.steps.compliance.schema import ComplianceLlmOutput, ComplianceStepOutput
from judge.steps.compliance.system_prompt import SYSTEM_PROMPT
from judge.steps.shared.criterion import CriterionEvaluation
from judge.steps.shared.transcript import transcript_block

logger = logging.getLogger(__name__)

# Расширяйте этим списком: каждый паттерн ищет одну «семью» стоп-формулировок (без LLM).
_DEFAULT_STOP_WORD_PATTERNS: tuple[re.Pattern[str], ...] = (
    re.compile(r"(?iu)\bбанк(?!рот)\w*\b"),
)


class ComplianceScriptStepJudge:
    """Шаг 1: скрипт, стоп-слова, комплаенс."""

    _stop_word_patterns: ClassVar[tuple[re.Pattern[str], ...]] = _DEFAULT_STOP_WORD_PATTERNS

    def __init__(self, llm: BaseChatModel) -> None:
        self._structured = llm.with_structured_output(
            ComplianceLlmOutput,
            method="function_calling",
            include_raw=True,
        )

    def find_stop_word_hits_in_manager_turns(self, transcript_text: str) -> list[str]:
        """
        Ищет вхождения по `_stop_word_patterns` только в строках транскрипта с ролью `manager`
        (как в `LLMJudge`: «manager: …»), без учёта реплик клиента.
        """
        if not transcript_text:
            return []
        hits: list[str] = []
        for raw_line in transcript_text.splitlines():
            line = raw_line.strip()
            m = re.match(r"^manager:\s*(.*)$", line, flags=re.IGNORECASE | re.DOTALL)
            if not m:
                continue
            chunk = m.group(1)
            for pat in self._stop_word_patterns:
                hits.extend(match.group(0) for match in pat.finditer(chunk))
        return hits

    def _stop_words_criterion(self, transcript_text: str) -> CriterionEvaluation:
        """Критерий `stop_words`: только правила из кода, реплики менеджера."""
        hits = self.find_stop_word_hits_in_manager_turns(transcript_text)
        if not hits:
            return CriterionEvaluation(
                score=True,
                explanation="Запрещённых формулировок по правилам шага в репликах менеджера не найдено.",
            )
        unique = list(dict.fromkeys(hits))
        return CriterionEvaluation(
            score=False,
            explanation="Обнаружены стоп-формулировки в репликах менеджера: "
            + ", ".join(f"«{h}»" for h in unique)
            + ".",
        )

    async def run(
        self,
        *,
        persona_description: str,
        transcript_text: str,
    ) -> ComplianceStepOutput:
        user = transcript_block(persona_description, transcript_text)
        messages = [
            SystemMessage(content=SYSTEM_PROMPT),
            HumanMessage(content=user),
        ]
        out = await self._structured.ainvoke(messages)
        try:
            payload = out["parsed"]  # Expect include_raw envelope from with_structured_output.
            partial = ComplianceLlmOutput.model_validate(payload)
            return ComplianceStepOutput(
                **partial.model_dump(),
                stop_words=self._stop_words_criterion(transcript_text),
            )
        except Exception as exc:
            parsing_error = getattr(out, "get", lambda _key: None)("parsing_error")
            logger.exception(
                "Compliance parsing failed: parsing_error=%r raw_response=%r",
                parsing_error,
                out,
            )
            raise ValueError("Compliance parsing failed; see raw_response in logs") from exc
