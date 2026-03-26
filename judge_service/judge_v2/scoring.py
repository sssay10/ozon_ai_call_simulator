from __future__ import annotations

from typing import List

from .schemas import CriterionResult


CRITERION_WEIGHTS = {
    "greeting_correct": 0.30,
    "congratulation_given": 0.20,
    "compliance_free_account_ip": 0.20,
    "compliance_account_docs_ip": 0.30,
}


class SimpleScoring:
    def calculate(self, results: List[CriterionResult]) -> dict:
        total = 0.0
        max_total = 0.0
        critical_errors = []

        for result in results:
            weight = CRITERION_WEIGHTS.get(result.criterion_id, 0.0)
            max_total += weight

            if result.decision == "pass":
                total += weight

            if (
                result.criterion_id in {"greeting_correct", "compliance_account_docs_ip"}
                and result.decision == "fail"
            ):
                critical_errors.append(result.criterion_id)

        total_score = round((total / max_total) * 100, 2) if max_total else 0.0

        return {
            "total_score": total_score,
            "critical_errors": critical_errors,
        }
