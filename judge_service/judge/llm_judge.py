from __future__ import annotations

import logging
import os
import time
from typing import Any, TypeVar

from langchain_community.chat_models import ChatOllama

from judge.knowledge_rag.chroma_store import get_faq_store
from langchain_core.language_models.chat_models import BaseChatModel
from langchain_openai import ChatOpenAI

from .graph import JudgeGraphState, build_evaluation_graph
from .merged_evaluation import JudgeEvaluation, merge_step_outputs
from .steps.compliance.schema import ComplianceStepOutput
from .steps.knowledge.schema import KnowledgeStepOutput
from .steps.sales_skills.schema import SalesSkillsStepOutput

logger = logging.getLogger(__name__)

_TStep = TypeVar("_TStep", ComplianceStepOutput, SalesSkillsStepOutput, KnowledgeStepOutput)


def _as_step(raw: Any, model: type[_TStep]) -> _TStep:
    if isinstance(raw, model):
        return raw
    return model.model_validate(raw)


class LLMJudge:
    def __init__(self) -> None:
        llm_provider = os.getenv("LLM_PROVIDER", "openrouter").lower().strip()

        openrouter_api_key = os.getenv("OPENROUTER_API_KEY", "")
        openrouter_model = os.getenv("OPENROUTER_MODEL", "openai/gpt-4o-mini")
        openrouter_base_url = os.getenv("OPENROUTER_BASE_URL", "https://openrouter.ai/api/v1")

        ollama_base_url = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434")
        ollama_model = os.getenv("OLLAMA_MODEL", "qwen2:7b-instruct-q4_K_M")

        base_llm: BaseChatModel
        if llm_provider == "ollama":
            base_llm = ChatOllama(
                model=ollama_model,
                base_url=ollama_base_url,
                temperature=0.2,
            )
            self.backend_name = "ollama"
            logger.info(
                "LLMJudge: ChatOllama model=%s base_url=%s",
                ollama_model,
                ollama_base_url,
            )
        else:
            if not openrouter_api_key:
                logger.warning("OPENROUTER_API_KEY not set. LLM will not work.")
            base_llm = ChatOpenAI(
                model=openrouter_model,
                api_key=openrouter_api_key,
                base_url=openrouter_base_url,
                temperature=0.2,
                extra_body={"reasoning": {"max_tokens": 0}},
            )
            self.backend_name = "openrouter"
            logger.info("LLMJudge: OpenRouter model=%s", openrouter_model)

        self._base_llm = base_llm
        use_rag = os.getenv("KNOWLEDGE_RAG", "1").strip().lower() in ("1", "true", "yes", "on")
        faq_store = get_faq_store() if use_rag else None
        if not use_rag:
            logger.info("KNOWLEDGE_RAG disabled — knowledge step runs without Chroma RAG")
        else:
            n = faq_store.collection_count()
            logger.info(
                "Chroma FAQ count=%s CHROMA_HTTP_HOST=%s CHROMA_HTTP_PORT=%s",
                n,
                os.getenv("CHROMA_HTTP_HOST", "chroma"),
                os.getenv("CHROMA_HTTP_PORT", "8000"),
            )
            if n == 0:
                logger.warning(
                    "KNOWLEDGE_RAG enabled but Chroma FAQ is empty — run ingest: "
                    "docker compose run --rm judge_service uv run python scripts/ingest_rko_faq.py"
                )
        self._graph = build_evaluation_graph(base_llm, faq_store=faq_store)

        self.model_name = getattr(base_llm, "model", None) or getattr(
            base_llm, "model_name", "unknown"
        )

        logger.info("LLMJudge LangGraph pipeline ready (3 steps)")

    @property
    def llm(self) -> BaseChatModel:
        """Backward-compatible handle for logging / health."""
        return self._base_llm

    async def evaluate(
        self,
        persona_description: str | None,
        scenario_description: str | None,
        transcript: list[dict[str, Any]],
    ) -> JudgeEvaluation:
        transcript_text = "\n".join(
            f"{turn.get('role', 'unknown')}: {turn.get('text', '')}" for turn in transcript
        )
        logger.info(
            "evaluate: transcript_turns=%s chars=%s",
            len(transcript),
            len(transcript_text),
        )
        state: JudgeGraphState = {
            "persona_description": persona_description or "",
            "scenario_description": scenario_description or "",
            "transcript_text": transcript_text,
        }
        t0 = time.perf_counter()
        result = await self._graph.ainvoke(state)
        graph_s = time.perf_counter() - t0
        c = _as_step(result.get("compliance"), ComplianceStepOutput)
        s = _as_step(result.get("sales"), SalesSkillsStepOutput)
        k = _as_step(result.get("knowledge"), KnowledgeStepOutput)
        merged = merge_step_outputs(
            compliance=c,
            sales=s,
            knowledge=k,
            model_used=str(self.model_name),
        )
        logger.info(
            "evaluate: graph+merge done in %.2fs total_score=%.2f critical_errors=%s",
            graph_s,
            merged.total_score,
            len(merged.critical_errors),
        )
        return merged
