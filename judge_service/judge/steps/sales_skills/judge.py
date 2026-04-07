"""Sales skills step judge class."""

from __future__ import annotations

from langchain_core.language_models import BaseChatModel
from langchain_core.messages import HumanMessage, SystemMessage

from judge.steps.sales_skills.schema import SalesSkillsStepOutput
from judge.steps.sales_skills.system_prompt import SYSTEM_PROMPT
from judge.steps.shared.transcript import transcript_block


class SalesSkillsStepJudge:
    """Шаг 2: продажные навыки и ведение диалога."""

    def __init__(self, llm: BaseChatModel) -> None:
        self._structured = llm.with_structured_output(
            SalesSkillsStepOutput,
            method="function_calling",
        )

    async def run(
        self,
        *,
        persona_description: str,
        scenario_description: str,
        transcript_text: str,
    ) -> SalesSkillsStepOutput:
        user = transcript_block(persona_description, scenario_description, transcript_text)
        messages = [
            SystemMessage(content=SYSTEM_PROMPT),
            HumanMessage(content=user),
        ]
        out = await self._structured.ainvoke(messages)
        if isinstance(out, SalesSkillsStepOutput):
            return out
        if isinstance(out, dict):
            return SalesSkillsStepOutput.model_validate(out)
        raise ValueError(f"Unexpected sales step output: {type(out)}")
