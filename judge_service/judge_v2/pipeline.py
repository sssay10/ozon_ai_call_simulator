from __future__ import annotations

from pathlib import Path
from typing import Callable, List, Optional

from .adapter import build_legacy_response
from .deterministic_checks import DeterministicChecks
from .kb_loader import KBLoader
from .llm_evaluator import LLMEvaluator
from .retriever import SimpleCriterionRetriever
from .schemas import CriterionResult, Transcript
from .scoring import SimpleScoring
from .segmenter import SimpleSegmenter


class JudgeV2Pipeline:
    def __init__(
        self,
        kb_root: str | Path,
        llm_generate_json: Optional[Callable[[str], dict]] = None,
    ):
        self.kb_root = str(kb_root)
        self.segmenter = SimpleSegmenter()
        self.det_checks = DeterministicChecks()
        self.scoring = SimpleScoring()

        chunks = KBLoader(self.kb_root).load_chunks()
        self.retriever = SimpleCriterionRetriever(chunks)

        self.llm_evaluator = None
        if llm_generate_json is not None:
            self.llm_evaluator = LLMEvaluator(llm_generate_json=llm_generate_json)

    @staticmethod
    def _judge_backend_name(llm_configured: bool) -> str:
        return "hybrid_kb_v2" if llm_configured else "hybrid_kb_v2_no_llm"

    def get_plan(self, scenario_id: str) -> List[dict]:
        if scenario_id == "novice_ip_no_account_easy" or scenario_id.startswith("rko_novice_l"):
            return [
                {"criterion_id": "greeting_correct", "segment": "greeting_block"},
                {"criterion_id": "congratulation_given", "segment": "greeting_block"},
                {"criterion_id": "compliance_free_account_ip", "segment": "body_block"},
                {"criterion_id": "compliance_account_docs_ip", "segment": "body_block"},
            ]

        if scenario_id.startswith("rko_skeptic_l"):
            return [
                {"criterion_id": "greeting_correct", "segment": "greeting_block"},
                {"criterion_id": "congratulation_given", "segment": "greeting_block"},
                {"criterion_id": "compliance_free_account_ip", "segment": "body_block"},
                {"criterion_id": "compliance_account_docs_ip", "segment": "body_block"},
                {"criterion_id": "skeptic_no_pressure", "segment": "body_block"},
            ]

        if scenario_id.startswith("rko_busy_owner_l"):
            return [
                {"criterion_id": "greeting_correct", "segment": "greeting_block"},
                {"criterion_id": "congratulation_given", "segment": "greeting_block"},
                {"criterion_id": "compliance_free_account_ip", "segment": "body_block"},
                {"criterion_id": "compliance_account_docs_ip", "segment": "body_block"},
                {"criterion_id": "busy_owner_concise_pitch", "segment": "body_block"},
            ]

        return []

    def run(self, transcript: Transcript) -> dict:
        segments = self.segmenter.segment(transcript)
        plan = self.get_plan(transcript.scenario_id)

        results: List[CriterionResult] = []
        debug = {"retrieval": {}}

        for item in plan:
            criterion_id = item["criterion_id"]
            segment = self.segmenter.get_segment(segments, item["segment"])

            det_result = self.det_checks.evaluate(criterion_id, segment)
            if det_result is not None:
                results.append(det_result)
                debug["retrieval"][criterion_id] = []
                continue

            kb_chunks = self.retriever.retrieve(
                criterion_id=criterion_id,
                scenario_id=transcript.scenario_id,
                segment=segment,
                top_k=2,
            )

            debug["retrieval"][criterion_id] = [
                {"chunk_id": c.id, "title": c.title}
                for c in kb_chunks
            ]

            if self.llm_evaluator is None:
                results.append(
                    CriterionResult(
                        criterion_id=criterion_id,
                        decision="null",
                        score=0.0,
                        confidence=0.0,
                        rationale_short="LLM evaluator is not configured.",
                        transcript_evidence=[],
                        kb_evidence=[{"chunk_id": c.id} for c in kb_chunks],
                    )
                )
                continue

            llm_result = self.llm_evaluator.evaluate(
                criterion_id=criterion_id,
                segment=segment,
                kb_chunks=kb_chunks,
            )
            results.append(llm_result)

        score = self.scoring.calculate(results, scenario_id=transcript.scenario_id)
        relevant_criteria = [item["criterion_id"] for item in plan]
        legacy_response = build_legacy_response(
            session_id=transcript.session_id,
            scenario_id=transcript.scenario_id,
            criterion_results=results,
            total_score=float(score.get("total_score") or 0.0),
            critical_errors=list(score.get("critical_errors") or []),
            relevant_criteria=relevant_criteria,
            debug=debug,
            judge_backend=self._judge_backend_name(self.llm_evaluator is not None),
        )

        return {
            **legacy_response,
            "score": score,
            "segments": [s.model_dump() for s in segments],
        }
