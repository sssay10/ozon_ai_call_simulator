from __future__ import annotations

import logging
import re
from pathlib import Path
from typing import Any, Dict, List

from langchain_core.output_parsers import PydanticOutputParser
from langchain_core.prompts import ChatPromptTemplate
from pydantic import BaseModel, Field

from judge import LLMJudge

from .pipeline import JudgeV2Pipeline
from .schemas import Transcript

logger = logging.getLogger(__name__)


class CriterionLLMResponse(BaseModel):
    decision: str = "null"
    confidence: float = 0.7
    rationale_short: str = ""
    transcript_evidence: list[dict[str, Any]] = Field(default_factory=list)
    kb_evidence: list[dict[str, Any]] = Field(default_factory=list)


class HybridKBJudge:
    """
    Runtime adapter for judge_v2 with the same evaluate() contract as legacy LLMJudge.
    Uses the existing LLM provider setup and falls back to legacy for unsupported scenarios.
    """

    def __init__(self, kb_root: str | Path | None = None) -> None:
        self.legacy_judge = LLMJudge()
        self.backend_name = "hybrid_kb_v2"
        self.model_used = getattr(
            self.legacy_judge.llm,
            "model_name",
            getattr(self.legacy_judge.llm, "model", "unknown"),
        )
        self.output_parser = PydanticOutputParser(pydantic_object=CriterionLLMResponse)

        base_dir = Path(__file__).resolve().parent.parent
        kb_path = Path(kb_root) if kb_root is not None else base_dir / "knowledge_base" / "normalized"
        self.pipeline = JudgeV2Pipeline(
            kb_root=kb_path,
            llm_generate_json=self._generate_json,
        )

    def _generate_json(self, prompt_text: str) -> dict[str, Any]:
        if self.legacy_judge.use_structured_output:
            escaped_prompt_text = prompt_text.replace("{", "{{").replace("}", "}}")
            prompt = ChatPromptTemplate.from_messages(
                [
                    ("system", "You evaluate one call criterion. Return only the requested structured result."),
                    ("user", escaped_prompt_text),
                ]
            )
            structured_llm = self.legacy_judge.llm.with_structured_output(
                CriterionLLMResponse,
                method="function_calling",
            )
            chain = prompt | structured_llm
            response = chain.invoke({})
            if response is None:
                raise ValueError("Criterion structured output returned None")
            return response.model_dump()

        format_instructions = self.output_parser.get_format_instructions()
        full_prompt_text = prompt_text + "\n\n" + format_instructions
        escaped_prompt_text = full_prompt_text.replace("{", "{{").replace("}", "}}")
        prompt = ChatPromptTemplate.from_messages(
            [
                ("system", "You evaluate one call criterion. Return only the requested JSON."),
                ("user", escaped_prompt_text),
            ]
        )
        chain = prompt | self.legacy_judge.llm
        raw_response = chain.invoke({})

        if hasattr(raw_response, "content"):
            content = raw_response.content
        elif isinstance(raw_response, str):
            content = raw_response
        else:
            content = str(raw_response)

        try:
            parsed = self.output_parser.parse(content)
        except Exception as parse_err:
            logger.warning(
                "HybridKBJudge: failed to parse criterion response, trying JSON extract: %s",
                parse_err,
            )
            json_match = re.search(r"\{.*\}", content, re.DOTALL)
            if not json_match:
                raise
            parsed = self.output_parser.parse(json_match.group(0))

        return parsed.model_dump()

    @staticmethod
    def _to_transcript(
        transcript: List[Dict[str, str]],
        scenario_id: str,
    ) -> Transcript:
        utterances = []
        for idx, item in enumerate(transcript):
            utterances.append(
                {
                    "turn_index": idx,
                    "speaker": item.get("role", "unknown"),
                    "text": item.get("text", ""),
                    "timestamp": item.get("created_at"),
                }
            )

        return Transcript.model_validate(
            {
                "session_id": "runtime_session",
                "scenario_id": scenario_id,
                "utterances": utterances,
            }
        )

    def evaluate(
        self,
        transcript: List[Dict[str, str]],
        scenario_id: str = "novice_ip_no_account_easy",
    ) -> Dict[str, Any]:
        try:
            if not self.pipeline.get_plan(scenario_id):
                logger.info(
                    "HybridKBJudge: no plan for scenario_id=%s, falling back to legacy judge",
                    scenario_id,
                )
                return self.legacy_judge.evaluate(transcript, scenario_id=scenario_id)

            transcript_model = self._to_transcript(transcript, scenario_id=scenario_id)
            result = self.pipeline.run(transcript_model)
            result["scenario_id"] = scenario_id
            result["model_used"] = self.model_used
            result["judge_backend"] = self.backend_name
            return result
        except Exception as exc:
            logger.error("Error in HybridKBJudge.evaluate: %s", exc, exc_info=True)
            return {
                "error": "Hybrid judge evaluation failed",
                "details": str(exc),
                "scores": {},
                "total_score": 0.0,
                "critical_errors": ["Не удалось обработать диалог"],
                "feedback_positive": [],
                "feedback_improvement": [],
                "recommendations": [],
                "client_profile": {},
                "scenario_id": scenario_id,
                "relevant_criteria": [],
                "model_used": self.model_used,
                "judge_backend": self.backend_name,
            }
