from __future__ import annotations

import re
from typing import List

from .schemas import CriterionResult


DEFAULT_CRITERION_WEIGHTS = {
    "greeting_correct": 0.30,
    "congratulation_given": 0.20,
    "compliance_free_account_ip": 0.20,
    "compliance_account_docs_ip": 0.30,
}

RKO_SKEPTIC_WEIGHTS = {
    "greeting_correct": 0.25,
    "congratulation_given": 0.15,
    "compliance_free_account_ip": 0.20,
    "compliance_account_docs_ip": 0.25,
    "skeptic_no_pressure": 0.15,
}

RKO_BUSY_OWNER_WEIGHTS = {
    "greeting_correct": 0.20,
    "congratulation_given": 0.15,
    "compliance_free_account_ip": 0.20,
    "compliance_account_docs_ip": 0.25,
    "busy_owner_concise_pitch": 0.20,
}

DIFFICULTY_FAIL_PENALTY = {
    1: 0.0,
    2: 4.0,
    3: 8.0,
    4: 12.0,
}


def _scenario_level(scenario_id: str) -> int:
    match = re.search(r"_l(?P<level>[1-4])_core$", scenario_id)
    if not match:
        return 1
    return int(match.group("level"))


def _criterion_weights_for_scenario(scenario_id: str) -> dict[str, float]:
    if scenario_id == "novice_ip_no_account_easy" or scenario_id.startswith("rko_novice_l"):
        return DEFAULT_CRITERION_WEIGHTS
    if scenario_id.startswith("rko_skeptic_l"):
        return RKO_SKEPTIC_WEIGHTS
    if scenario_id.startswith("rko_busy_owner_l"):
        return RKO_BUSY_OWNER_WEIGHTS
    return DEFAULT_CRITERION_WEIGHTS


def _critical_criteria_for_scenario(scenario_id: str) -> set[str]:
    if scenario_id.startswith("rko_skeptic_l"):
        return {"greeting_correct", "compliance_account_docs_ip", "skeptic_no_pressure"}
    return {"greeting_correct", "compliance_account_docs_ip"}


class SimpleScoring:
    def calculate(self, results: List[CriterionResult], scenario_id: str = "novice_ip_no_account_easy") -> dict:
        criterion_weights = _criterion_weights_for_scenario(scenario_id)
        critical_criteria = _critical_criteria_for_scenario(scenario_id)
        level = _scenario_level(scenario_id)
        total = 0.0
        max_total = 0.0
        critical_errors = []
        failed_criteria_count = 0

        for result in results:
            weight = criterion_weights.get(result.criterion_id, 0.0)
            max_total += weight

            if result.decision == "pass":
                total += weight
            elif result.decision == "fail" and weight > 0:
                failed_criteria_count += 1

            if result.criterion_id in critical_criteria and result.decision == "fail":
                critical_errors.append(result.criterion_id)

        total_score = round((total / max_total) * 100, 2) if max_total else 0.0
        difficulty_penalty = DIFFICULTY_FAIL_PENALTY.get(level, 0.0) * failed_criteria_count
        total_score = max(0.0, round(total_score - difficulty_penalty, 2))

        return {
            "total_score": total_score,
            "critical_errors": critical_errors,
            "difficulty_level": level,
            "difficulty_penalty": difficulty_penalty,
            "failed_criteria_count": failed_criteria_count,
        }
