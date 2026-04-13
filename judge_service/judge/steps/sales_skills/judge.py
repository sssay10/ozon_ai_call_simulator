"""Sales skills step judge class."""

from __future__ import annotations

import logging

from langchain_core.language_models import BaseChatModel
from langchain_core.messages import HumanMessage, SystemMessage

from judge.steps.sales_skills.schema import SalesSkillsStepOutput
from judge.steps.sales_skills.system_prompt import SYSTEM_PROMPT
from judge.steps.shared.transcript import transcript_block

logger = logging.getLogger(__name__)


class SalesSkillsStepJudge:
    """Шаг 2: продажные навыки и ведение диалога."""

    def __init__(self, llm: BaseChatModel) -> None:
        self._structured = llm.with_structured_output(
            SalesSkillsStepOutput,
            method="function_calling",
            include_raw=True,
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
        try:
            payload = out["parsed"]  # Expect include_raw envelope from with_structured_output.
            return SalesSkillsStepOutput.model_validate(payload)
        except Exception as exc:
            parsing_error = getattr(out, "get", lambda _key: None)("parsing_error")
            logger.exception(
                "Sales parsing failed: parsing_error=%r raw_response=%r",
                parsing_error,
                out,
            )
            raise ValueError("Sales parsing failed; see raw_response in logs") from exc
