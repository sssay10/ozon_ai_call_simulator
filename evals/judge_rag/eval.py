"""Custom binary classifier metrics for the knowledge validation judge.

Primary metrics:
  error_detection_rate   — recall on error cases: did the judge catch every mistake?
  false_positive_rate    — rate of incorrect flags on clean cases (lower is better)
  criterion_accuracy     — per-criterion % of correct True/False verdicts
"""

from __future__ import annotations

import logging

from .dataset import EvalCase
from .judge import run_knowledge_judge
from .schema import KnowledgeStepOutput

logger = logging.getLogger(__name__)

CRITERIA = ("tariff_accuracy", "limits_commissions_accuracy", "objection_handling")

CLASSIFIER_THRESHOLDS: dict[str, float] = {
    "error_detection_rate": 0.8,
    "false_positive_rate": 0.2,   # max allowed (lower is better)
    "criterion_accuracy": 0.85,
}


def _extract_scores(output: KnowledgeStepOutput) -> dict[str, bool]:
    return {
        "tariff_accuracy": output.tariff_accuracy.score,
        "limits_commissions_accuracy": output.limits_commissions_accuracy.score,
        "objection_handling": output.objection_handling.score,
    }


async def run_case(
    case: EvalCase,
    llm,
    faq_snippets: list[str] | None = None,
) -> dict[str, bool]:
    output = await run_knowledge_judge(
        llm,
        persona_description=case["persona_description"],
        transcript_text=case["transcript_text"],
        faq_snippets=faq_snippets,
    )
    return _extract_scores(output)


def compute_classifier_metrics(
    cases: list[EvalCase],
    actual_scores: list[dict[str, bool]],
) -> dict:
    """Compute primary binary classifier metrics across all cases and criteria.

    error_detection_rate: among (case, criterion) pairs where expected=False,
                          what fraction did the judge correctly score False?
    false_positive_rate:  among pairs where expected=True,
                          what fraction did the judge incorrectly score False?
    criterion_accuracy:   overall % of correct verdicts across all pairs.
    per_criterion:        per-criterion breakdown of the same three metrics.
    per_case:             per-case verdict correctness.
    """
    error_correct = error_total = 0
    fp_incorrect = clean_total = 0
    total_correct = total_pairs = 0

    per_criterion: dict[str, dict] = {c: {"tp": 0, "fp": 0, "fn": 0, "tn": 0} for c in CRITERIA}
    per_case: list[dict] = []

    for case, actual in zip(cases, actual_scores):
        expected = case["expected_scores"]
        case_correct = 0

        for criterion in CRITERIA:
            exp = expected[criterion]
            act = actual[criterion]
            correct = exp == act
            total_pairs += 1
            if correct:
                total_correct += 1
                case_correct += 1

            if not exp:
                error_total += 1
                if not act:
                    error_correct += 1
                    per_criterion[criterion]["tp"] += 1
                else:
                    per_criterion[criterion]["fn"] += 1
            else:
                clean_total += 1
                if act:
                    per_criterion[criterion]["tn"] += 1
                else:
                    fp_incorrect += 1
                    per_criterion[criterion]["fp"] += 1

        per_case.append({
            "id": case["id"],
            "correct": case_correct,
            "total": len(CRITERIA),
            "all_correct": case_correct == len(CRITERIA),
        })

    edr = round(error_correct / error_total, 4) if error_total else None
    fpr = round(fp_incorrect / clean_total, 4) if clean_total else None
    acc = round(total_correct / total_pairs, 4) if total_pairs else None

    per_criterion_summary: dict[str, dict] = {}
    for c, counts in per_criterion.items():
        tp, fp, fn, tn = counts["tp"], counts["fp"], counts["fn"], counts["tn"]
        total = tp + fp + fn + tn
        per_criterion_summary[c] = {
            "accuracy": round((tp + tn) / total, 4) if total else None,
            "error_detection_rate": round(tp / (tp + fn), 4) if (tp + fn) else None,
            "false_positive_rate": round(fp / (fp + tn), 4) if (fp + tn) else None,
        }

    passed = {}
    if edr is not None:
        passed["error_detection_rate"] = edr >= CLASSIFIER_THRESHOLDS["error_detection_rate"]
    if fpr is not None:
        passed["false_positive_rate"] = fpr <= CLASSIFIER_THRESHOLDS["false_positive_rate"]
    if acc is not None:
        passed["criterion_accuracy"] = acc >= CLASSIFIER_THRESHOLDS["criterion_accuracy"]

    return {
        "error_detection_rate": edr,
        "false_positive_rate": fpr,
        "criterion_accuracy": acc,
        "per_criterion": per_criterion_summary,
        "per_case": per_case,
        "passed": passed,
        "overall_pass": all(passed.values()),
    }
