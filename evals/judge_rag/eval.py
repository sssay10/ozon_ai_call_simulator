"""RAGAS + custom criterion-accuracy evaluation for the knowledge validation judge.

Metric design
-------------
Primary (custom binary classifier metrics):
  error_detection_rate   — recall on error cases: did the judge catch every mistake?
  false_positive_rate    — rate of incorrect flags on clean cases (lower is better)
  criterion_accuracy     — per-criterion % of correct True/False verdicts

Secondary (RAGAS):
  answer_relevancy       — judge explanation is on-topic relative to the transcript

Dropped from primary thresholds:
  faithfulness           — inherently low because the judge uses embedded tariff
                           knowledge not present in the transcript; this is by design,
                           not a defect. Kept in results as info-only.
  context_precision/recall — relevant only when testing retrieval quality separately.

Two run modes (KNOWLEDGE_RAG env var):
  0 (default) — transcript as context; primary + answer_relevancy active.
  1           — FAQ snippets from ChromaDB as context; retrieval metrics also computed.
"""

from __future__ import annotations

import logging

from ragas import evaluate
from ragas.dataset_schema import EvaluationDataset, SingleTurnSample
from ragas.llms import LangchainLLMWrapper
from ragas.metrics import AnswerRelevancy, Faithfulness, LLMContextPrecisionWithReference, LLMContextRecall

from .dataset import EvalCase
from .judge import run_knowledge_judge
from .schema import KnowledgeStepOutput

logger = logging.getLogger(__name__)

# RAGAS metrics computed on every run (results always included).
RAGAS_METRICS = [
    Faithfulness(),
    AnswerRelevancy(),
    LLMContextPrecisionWithReference(),
    LLMContextRecall(),
]

# All RAGAS metrics are info-only: structurally incompatible with an embedded-knowledge judge.
# answer_relevancy is volatile (0.25–0.61 across runs) because RAGAS expects a Q&A format,
# not transcript → structured evaluation. faithfulness is low by design (embedded tariff knowledge).
RAGAS_THRESHOLDS: dict[str, float] = {}

# Primary thresholds for custom classifier metrics.
CLASSIFIER_THRESHOLDS: dict[str, float] = {
    "error_detection_rate": 0.8,
    "false_positive_rate": 0.2,   # max allowed (lower is better)
    "criterion_accuracy": 0.85,
}

CRITERIA = ("tariff_accuracy", "limits_commissions_accuracy", "objection_handling")


def _format_response(output: KnowledgeStepOutput) -> str:
    lines = [
        f"tariff_accuracy: {output.tariff_accuracy.score} — {output.tariff_accuracy.explanation}",
        f"limits_commissions_accuracy: {output.limits_commissions_accuracy.score} — {output.limits_commissions_accuracy.explanation}",
        f"objection_handling: {output.objection_handling.score} — {output.objection_handling.explanation}",
    ]
    if output.critical_errors:
        lines.append(f"critical_errors: {'; '.join(output.critical_errors)}")
    return "\n".join(lines)


def _extract_scores(output: KnowledgeStepOutput) -> dict[str, bool]:
    return {
        "tariff_accuracy": output.tariff_accuracy.score,
        "limits_commissions_accuracy": output.limits_commissions_accuracy.score,
        "objection_handling": output.objection_handling.score,
    }


async def build_sample(
    case: EvalCase,
    llm,
    faq_snippets: list[str] | None = None,
) -> tuple[SingleTurnSample, dict[str, bool]]:
    """Run one evaluation case.

    Returns:
        A tuple of (RAGAS sample, actual judge scores dict).
    """
    if faq_snippets:
        retrieved_contexts = faq_snippets
        logger.info("case=%s: using %d FAQ snippets as context", case["id"], len(faq_snippets))
    else:
        retrieved_contexts = [case["transcript_text"]]
        logger.info("case=%s: transcript mode", case["id"])

    output = await run_knowledge_judge(
        llm,
        persona_description=case["persona_description"],
        transcript_text=case["transcript_text"],
        faq_snippets=faq_snippets,
    )

    sample = SingleTurnSample(
        user_input=case["transcript_text"],
        retrieved_contexts=retrieved_contexts,
        response=_format_response(output),
        reference=case["ground_truth"],
    )
    return sample, _extract_scores(output)


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
        case_total = len(CRITERIA)

        for criterion in CRITERIA:
            exp = expected[criterion]
            act = actual[criterion]
            correct = exp == act
            total_pairs += 1
            if correct:
                total_correct += 1
                case_correct += 1

            if not exp:  # expected error
                error_total += 1
                if not act:  # judge caught it
                    error_correct += 1
                    per_criterion[criterion]["tp"] += 1
                else:
                    per_criterion[criterion]["fn"] += 1
            else:  # expected clean
                clean_total += 1
                if act:  # judge correctly said clean
                    per_criterion[criterion]["tn"] += 1
                else:  # false positive
                    fp_incorrect += 1
                    per_criterion[criterion]["fp"] += 1

        per_case.append({
            "id": case["id"],
            "correct": case_correct,
            "total": case_total,
            "all_correct": case_correct == case_total,
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


def compute_ragas_metrics(
    samples: list[SingleTurnSample],
    ragas_llm: LangchainLLMWrapper,
) -> dict:
    """Run RAGAS evaluation and return metric means."""
    dataset = EvaluationDataset(samples=samples)
    result = evaluate(dataset=dataset, metrics=RAGAS_METRICS, llm=ragas_llm)

    df = result.to_pandas()
    metric_cols = [
        c for c in df.columns
        if c not in ("user_input", "retrieved_contexts", "response", "reference")
    ]

    means: dict[str, float] = {}
    for col in metric_cols:
        values = [v for v in df[col].tolist() if v is not None]
        means[col] = round(sum(values) / len(values), 4) if values else 0.0

    passed = {
        metric: means.get(metric, 0.0) >= threshold
        for metric, threshold in RAGAS_THRESHOLDS.items()
    }

    return {
        "metrics": means,
        "thresholds": RAGAS_THRESHOLDS,
        "passed": passed,
    }
