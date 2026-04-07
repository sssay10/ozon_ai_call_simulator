"""Compliance / script step judge class."""

from __future__ import annotations

from langchain_core.language_models import BaseChatModel
from langchain_core.messages import HumanMessage, SystemMessage

from judge.steps.compliance.schema import ComplianceStepOutput
from judge.steps.compliance.system_prompt import SYSTEM_PROMPT
from judge.steps.shared.transcript import transcript_block


class ComplianceScriptStepJudge:
    """Шаг 1: скрипт, стоп-слова, комплаенс."""

    def __init__(self, llm: BaseChatModel) -> None:
        self._structured = llm.with_structured_output(
            ComplianceStepOutput,
            method="function_calling",
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
        if isinstance(out, ComplianceStepOutput):
            return out
        if isinstance(out, dict):
            return ComplianceStepOutput.model_validate(out)
        raise ValueError(f"Unexpected compliance step output: {type(out)}")
