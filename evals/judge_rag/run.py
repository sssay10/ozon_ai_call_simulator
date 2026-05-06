"""Entry point for the judge_rag evaluation.

Fully standalone — no dependency on judge_service code.

Usage:
    cd evals
    OPENROUTER_API_KEY=sk-or-... OPENAI_API_KEY=sk-... ./run.sh

Environment variables:
    OPENROUTER_API_KEY   required — used by the judge and RAGAS LLM metrics
    OPENAI_API_KEY       required — used by RAGAS AnswerRelevancy (embeddings)
    OPENROUTER_BASE_URL  default: https://openrouter.ai/api/v1
    OPENROUTER_MODEL     default: openai/gpt-4o-mini
    KNOWLEDGE_RAG        set to "1" to enable FAQ RAG mode
    CHROMA_HTTP_HOST     default: localhost  (only used when KNOWLEDGE_RAG=1)
    CHROMA_HTTP_PORT     default: 8000       (only used when KNOWLEDGE_RAG=1)
"""

from __future__ import annotations

import asyncio
import json
import logging
import os
import sys
from datetime import datetime, timezone
from pathlib import Path

logging.basicConfig(level=logging.INFO, format="%(levelname)s %(name)s — %(message)s")
logger = logging.getLogger(__name__)


def _build_llm():
    from langchain_openai import ChatOpenAI

    return ChatOpenAI(
        model=os.getenv("OPENROUTER_MODEL", "openai/gpt-4o-mini"),
        base_url=os.getenv("OPENROUTER_BASE_URL", "https://openrouter.ai/api/v1"),
        api_key=os.environ["OPENROUTER_API_KEY"],
        temperature=0,
    )


def _faq_snippets_for(transcript_text: str, top_k: int = 4) -> list[str]:
    """Retrieve FAQ snippets from ChromaDB (Path A only)."""
    import chromadb

    host = os.getenv("CHROMA_HTTP_HOST", "localhost")
    port = int(os.getenv("CHROMA_HTTP_PORT", "8000"))
    client = chromadb.HttpClient(host=host, port=port)

    try:
        collection = client.get_collection("rko_faq")
    except Exception:
        logger.warning("ChromaDB collection 'rko_faq' not found — context metrics will be low")
        return []

    results = collection.query(query_texts=[transcript_text], n_results=top_k)
    docs = results.get("documents", [[]])[0]
    return [d for d in docs if d]


async def _build_samples(cases, llm, use_rag: bool):
    from .eval import build_sample

    samples = []
    actual_scores = []

    for case in cases:
        logger.info("running case: %s", case["id"])
        try:
            faq_snippets = _faq_snippets_for(case["transcript_text"]) if use_rag else None
            sample, scores = await build_sample(case, llm, faq_snippets=faq_snippets)
            samples.append(sample)
            actual_scores.append(scores)
        except Exception:
            logger.exception("case %s failed — skipping", case["id"])

    return samples, actual_scores


async def main() -> None:
    if "OPENROUTER_API_KEY" not in os.environ:
        logger.error("OPENROUTER_API_KEY is not set")
        sys.exit(1)

    from ragas.llms import LangchainLLMWrapper

    from .dataset import CASES
    from .eval import compute_classifier_metrics, compute_ragas_metrics

    use_rag = os.getenv("KNOWLEDGE_RAG", "0") != "0"
    llm = _build_llm()
    ragas_llm = LangchainLLMWrapper(llm)

    mode = "faq_rag" if use_rag else "transcript"
    logger.info("mode=%s", mode)
    logger.info("building %d eval samples…", len(CASES))

    samples, actual_scores = await _build_samples(CASES, llm, use_rag)

    if not samples:
        logger.error("no samples were built — aborting")
        sys.exit(1)

    evaluated_cases = CASES[: len(samples)]

    logger.info("computing classifier metrics…")
    classifier = compute_classifier_metrics(evaluated_cases, actual_scores)

    logger.info("running RAGAS on %d samples…", len(samples))
    ragas = compute_ragas_metrics(samples, ragas_llm)

    results = {
        "classifier": classifier,
        "ragas": ragas,
        "meta": {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "model": os.getenv("OPENROUTER_MODEL", "openai/gpt-4o-mini"),
            "mode": mode,
            "cases_total": len(CASES),
            "cases_evaluated": len(samples),
        },
    }

    output_dir = Path(__file__).resolve().parents[2] / "evals" / "results"
    output_dir.mkdir(exist_ok=True)
    output_path = output_dir / "judge_rag.json"
    output_path.write_text(json.dumps(results, ensure_ascii=False, indent=2))

    _print_summary(results)
    logger.info("results written to %s", output_path)

    overall_pass = classifier["overall_pass"] and all(ragas["passed"].values())
    if not overall_pass:
        sys.exit(1)


def _print_summary(results: dict) -> None:
    clf = results["classifier"]
    ragas = results["ragas"]

    print("\n" + "=" * 60)
    print("  JUDGE RAG EVAL RESULTS")
    print("=" * 60)

    print("\n  -- Classifier metrics (primary) --\n")

    edr = clf["error_detection_rate"]
    fpr = clf["false_positive_rate"]
    acc = clf["criterion_accuracy"]

    _print_metric(
        "error_detection_rate",
        edr,
        clf["passed"].get("error_detection_rate"),
        threshold=0.8,
        note="min",
    )
    _print_metric(
        "false_positive_rate",
        fpr,
        clf["passed"].get("false_positive_rate"),
        threshold=0.2,
        note="max",
    )
    _print_metric(
        "criterion_accuracy",
        acc,
        clf["passed"].get("criterion_accuracy"),
        threshold=0.85,
        note="min",
    )

    print("\n  -- Per criterion --\n")
    for criterion, metrics in clf["per_criterion"].items():
        edr_c = metrics["error_detection_rate"]
        acc_c = metrics["accuracy"]
        edr_str = f"{edr_c:.3f}" if edr_c is not None else "n/a"
        acc_str = f"{acc_c:.3f}" if acc_c is not None else "n/a"
        print(f"  {criterion:<38} accuracy={acc_str}  edr={edr_str}")

    print("\n  -- Per case --\n")
    for case in clf["per_case"]:
        mark = "✓" if case["all_correct"] else "✗"
        print(f"  {mark} {case['id']:<40} {case['correct']}/{case['total']} correct")

    print("\n  -- RAGAS metrics (secondary) --\n")
    for metric, score in ragas["metrics"].items():
        threshold = ragas["thresholds"].get(metric)
        if threshold is not None:
            passed = ragas["passed"].get(metric)
            _print_metric(metric, score, passed, threshold=threshold, note="min")
        else:
            print(f"  INFO  {metric:<42} {score:.3f}  (info only)")

    overall_pass = clf["overall_pass"] and all(ragas["passed"].values())
    print("\n" + "-" * 60)
    print(f"  OVERALL: {'PASS' if overall_pass else 'FAIL'}")
    print("=" * 60 + "\n")


def _print_metric(
    name: str,
    value: float | None,
    passed: bool | None,
    *,
    threshold: float,
    note: str,
) -> None:
    if value is None:
        print(f"  N/A   {name:<42}  n/a   ({note} {threshold})")
        return
    status = "PASS" if passed else "FAIL"
    print(f"  {status}  {name:<42} {value:.3f}  ({note} {threshold})")


if __name__ == "__main__":
    asyncio.run(main())
