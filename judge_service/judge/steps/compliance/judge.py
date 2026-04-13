"""Compliance / script step judge class."""

from __future__ import annotations

import logging

from langchain_core.language_models import BaseChatModel
from langchain_core.messages import HumanMessage, SystemMessage

from judge.steps.compliance.schema import ComplianceStepOutput
from judge.steps.compliance.system_prompt import SYSTEM_PROMPT
from judge.steps.shared.transcript import transcript_block

logger = logging.getLogger(__name__)


class ComplianceScriptStepJudge:
    """Шаг 1: скрипт, стоп-слова, комплаенс."""

    def __init__(self, llm: BaseChatModel) -> None:
        self._structured = llm.with_structured_output(
            ComplianceStepOutput,
            method="function_calling",
            include_raw=True,
        )

    async def run(
        self,
        *,
        persona_description: str,
        scenario_description: str,
        transcript_text: str,
    ) -> ComplianceStepOutput:
        user = transcript_block(persona_description, scenario_description, transcript_text)
        messages = [
            SystemMessage(content=SYSTEM_PROMPT),
            HumanMessage(content=user),
        ]
        out = await self._structured.ainvoke(messages)
        try:
            payload = out["parsed"]  # Expect include_raw envelope from with_structured_output.
            return ComplianceStepOutput.model_validate(payload)
        except Exception as exc:
            parsing_error = getattr(out, "get", lambda _key: None)("parsing_error")
            logger.exception(
                "Compliance parsing failed: parsing_error=%r raw_response=%r",
                parsing_error,
                out,
            )
            raise ValueError("Compliance parsing failed; see raw_response in logs") from exc
