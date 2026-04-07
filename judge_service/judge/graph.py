"""Linear LangGraph: compliance → sales skills → knowledge (no branching)."""

from __future__ import annotations

import logging
import time
from typing import Any, NotRequired, TypedDict

from langchain_core.language_models import BaseChatModel
from langgraph.graph import END, START, StateGraph

from judge.knowledge_rag.chroma_store import ChromaFAQStore

from .steps import (
    ComplianceScriptStepJudge,
    KnowledgeValidationStepJudge,
    SalesSkillsStepJudge,
)
from .steps.compliance.schema import ComplianceStepOutput
from .steps.knowledge.schema import KnowledgeStepOutput
from .steps.sales_skills.schema import SalesSkillsStepOutput

logger = logging.getLogger(__name__)


class JudgeGraphState(TypedDict):
    persona_description: str
    scenario_description: str
    transcript_text: str
    compliance: NotRequired[ComplianceStepOutput]
    sales: NotRequired[SalesSkillsStepOutput]
    knowledge: NotRequired[KnowledgeStepOutput]


def build_evaluation_graph(
    base_llm: BaseChatModel,
    *,
    faq_store: ChromaFAQStore | None = None,
):
    compliance_judge = ComplianceScriptStepJudge(base_llm)
    sales_judge = SalesSkillsStepJudge(base_llm)
    knowledge_judge = KnowledgeValidationStepJudge(base_llm, faq_store=faq_store)

    async def node_compliance(state: JudgeGraphState) -> dict[str, Any]:
        t0 = time.perf_counter()
        out = await compliance_judge.run(
            persona_description=state["persona_description"],
            scenario_description=state["scenario_description"],
            transcript_text=state["transcript_text"],
        )
        logger.info("graph node compliance done in %.2fs", time.perf_counter() - t0)
        return {"compliance": out}

    async def node_sales(state: JudgeGraphState) -> dict[str, Any]:
        t0 = time.perf_counter()
        out = await sales_judge.run(
            persona_description=state["persona_description"],
            scenario_description=state["scenario_description"],
            transcript_text=state["transcript_text"],
        )
        logger.info("graph node sales done in %.2fs", time.perf_counter() - t0)
        return {"sales": out}

    async def node_knowledge(state: JudgeGraphState) -> dict[str, Any]:
        t0 = time.perf_counter()
        out = await knowledge_judge.run(
            persona_description=state["persona_description"],
            scenario_description=state["scenario_description"],
            transcript_text=state["transcript_text"],
        )
        logger.info("graph node knowledge done in %.2fs", time.perf_counter() - t0)
        return {"knowledge": out}

    graph = StateGraph(JudgeGraphState)
    graph.add_node("compliance", node_compliance)
    graph.add_node("sales", node_sales)
    graph.add_node("knowledge", node_knowledge)
    graph.add_edge(START, "compliance")
    graph.add_edge("compliance", "sales")
    graph.add_edge("sales", "knowledge")
    graph.add_edge("knowledge", END)
    return graph.compile()
