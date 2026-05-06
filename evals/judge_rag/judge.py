"""Standalone knowledge validation judge.

Calls the LLM directly — no dependency on judge_service code.
Replicates the logic of KnowledgeValidationStepJudge.run().
"""

from __future__ import annotations

import logging

from langchain_core.messages import HumanMessage, SystemMessage

from .schema import KnowledgeStepOutput
from .system_prompt import SYSTEM_PROMPT

logger = logging.getLogger(__name__)


async def run_knowledge_judge(
    llm,
    *,
    persona_description: str,
    transcript_text: str,
    faq_snippets: list[str] | None = None,
) -> KnowledgeStepOutput:
    """Evaluate one transcript with the knowledge validation prompt.

    Args:
        llm: LangChain chat model instance.
        persona_description: Client persona context.
        transcript_text: Full dialogue transcript.
        faq_snippets: Optional FAQ snippets from ChromaDB (Path A).
                      When None, the judge uses only the tariff reference
                      embedded in the system prompt (Path B).
    """
    structured = llm.with_structured_output(
        KnowledgeStepOutput,
        method="function_calling",
        include_raw=True,
    )

    faq_prefix = ""
    if faq_snippets:
        lines = ["relevant knowledge snippets:", ""]
        for i, snippet in enumerate(faq_snippets, 1):
            lines += [f"snippet {i}:", snippet, ""]
        faq_prefix = "\n".join(lines) + "\n"

    user = (
        faq_prefix
        + f"persona_description:\n{persona_description or '(не задано)'}\n\n"
        + f"transcript:\n{transcript_text}"
    )

    messages = [SystemMessage(content=SYSTEM_PROMPT), HumanMessage(content=user)]

    out = await structured.ainvoke(messages)
    try:
        payload = out["parsed"]
        return KnowledgeStepOutput.model_validate(payload)
    except Exception as exc:
        logger.exception("knowledge judge parsing failed; raw=%r", out)
        raise ValueError("Knowledge judge parsing failed") from exc
