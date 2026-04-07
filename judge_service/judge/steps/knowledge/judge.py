"""Knowledge validation step judge class."""

from __future__ import annotations

import logging
import os

from langchain_core.language_models import BaseChatModel
from langchain_core.messages import HumanMessage, SystemMessage

from judge.knowledge_rag.chroma_store import ChromaFAQStore
from judge.steps.knowledge.schema import KnowledgeStepOutput
from judge.steps.knowledge.system_prompt import SYSTEM_PROMPT
from judge.steps.shared.transcript import transcript_block

logger = logging.getLogger(__name__)


class KnowledgeValidationStepJudge:
    """Шаг 3: знания — тарифы, лимиты, возражения; при наличии — сверка с РсВ ФАК через RAG."""

    def __init__(
        self,
        llm: BaseChatModel,
        *,
        faq_store: ChromaFAQStore | None = None,
        rag_top_k: int | None = None,
    ) -> None:
        self._structured = llm.with_structured_output(
            KnowledgeStepOutput,
            method="function_calling",
        )
        self._faq_store = faq_store
        self._rag_top_k = (
            rag_top_k if rag_top_k is not None else int(os.getenv("RAG_TOP_K", "8"))
        )
        self._rag_max_chars = int(os.getenv("RAG_QUERY_MAX_CHARS", "12000"))

    def _rag_prefix(self, transcript_text: str) -> str:
        if self._faq_store is None:
            logger.debug("knowledge step: RAG disabled (no faq_store)")
            return ""
        if self._faq_store.collection_count() == 0:
            logger.warning("knowledge step: Chroma FAQ empty — LLM will not see RAG snippets")
            return (
                "[Справочник РсВ ФАК: векторная база в Chroma пуста — загрузите FAQ: "
                "`docker compose run --rm judge_service uv run python scripts/ingest_rko_faq.py`. "
                "Оценивай по транскрипту.]\n\n"
            )
        q = transcript_text.strip()
        if len(q) > self._rag_max_chars:
            q = q[: self._rag_max_chars]
        snippets = self._faq_store.search(q, n_results=self._rag_top_k)
        if not snippets:
            logger.info(
                "knowledge step: Chroma search returned 0 snippets (query_chars=%s top_k=%s)",
                len(q),
                self._rag_top_k,
            )
            return (
                "[По тексту диалога не найдено близких статей РсВ ФАК; оценивай по транскрипту и здравому смыслу.]\n\n"
            )
        logger.info(
            "knowledge step: Chroma returned %s FAQ snippets (query_chars=%s top_k=%s)",
            len(snippets),
            len(q),
            self._rag_top_k,
        )
        lines = ["### Фрагменты справочника РсВ ФАК (семантический поиск)", ""]
        for i, block in enumerate(snippets, 1):
            lines.append(f"--- {i} ---")
            lines.append(block)
            lines.append("")
        return "\n".join(lines) + "\n"

    async def run(
        self,
        *,
        persona_description: str,
        scenario_description: str,
        transcript_text: str,
    ) -> KnowledgeStepOutput:
        user = self._rag_prefix(transcript_text) + transcript_block(
            persona_description, scenario_description, transcript_text
        )
        messages = [
            SystemMessage(content=SYSTEM_PROMPT),
            HumanMessage(content=user),
        ]
        out = await self._structured.ainvoke(messages)
        if isinstance(out, KnowledgeStepOutput):
            return out
        if isinstance(out, dict):
            return KnowledgeStepOutput.model_validate(out)
        raise ValueError(f"Unexpected knowledge step output: {type(out)}")
