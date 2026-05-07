#!/usr/bin/env python3
"""
Compare multiple run_compare.py result JSONs against a baseline (ideal.json).

Usage (from judge_service/):
  uv run python eval_dataset/compare_report.py \\
      --ideal   eval_dataset/results/ideal.json \\
      --results eval_dataset/results/qwen3.json eval_dataset/results/gpt4o_t05.json

  uv run python eval_dataset/compare_report.py \\
      --ideal eval_dataset/results/ideal.json \\
      --results eval_dataset/results/*.json \\
      --output eval_dataset/results/comparison.json
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any


# ── helpers ──────────────────────────────────────────────────────────────────

def _load(path: Path) -> dict[str, Any]:
    with path.open(encoding="utf-8") as f:
        return json.load(f)


def _index_by_case(results: list[dict]) -> dict[str, dict]:
    return {r["case_id"]: r for r in results}


def _criterion_agreement(ideal_scores: dict, other_scores: dict) -> float:
    """Fraction of criteria where both files agree (both True or both False)."""
    if not ideal_scores:
        return 0.0
    matches = sum(
        1 for k, v in ideal_scores.items()
        if other_scores.get(k) == v
    )
    return matches / len(ideal_scores)


# ── report builder ────────────────────────────────────────────────────────────

def build_report(
    ideal_path: Path,
    result_paths: list[Path],
) -> dict[str, Any]:
    ideal_raw = _load(ideal_path)
    ideal_idx = _index_by_case(ideal_raw["results"])

    models: list[dict] = []
    for rp in result_paths:
        if rp.resolve() == ideal_path.resolve():
            continue
        raw = _load(rp)
        models.append({"path": str(rp), "raw": raw})

    # collect all case_ids present in ideal
    case_ids = [r["case_id"] for r in ideal_raw["results"]]

    # ── per-case table ────────────────────────────────────────────────────────
    per_case: list[dict] = []
    for cid in case_ids:
        ideal_res = ideal_idx.get(cid)
        ideal_score = ideal_res["evaluation"]["total_score"] if ideal_res else None
        ideal_scores_dict = ideal_res["evaluation"]["scores"] if ideal_res else {}

        row: dict[str, Any] = {
            "case_id": cid,
            "ideal_score": round(ideal_score, 2) if ideal_score is not None else None,
            "models": {},
        }

        for m in models:
            label = _model_label(m["raw"])
            idx = _index_by_case(m["raw"]["results"])
            res = idx.get(cid)
            if res is None:
                row["models"][label] = {"score": None, "delta": None, "criterion_agreement": None}
            else:
                score = res["evaluation"]["total_score"]
                delta = score - ideal_score if ideal_score is not None else None
                agreement = _criterion_agreement(
                    ideal_scores_dict, res["evaluation"]["scores"]
                )
                row["models"][label] = {
                    "score": round(score, 2),
                    "delta": round(delta, 2) if delta is not None else None,
                    "criterion_agreement": round(agreement, 3),
                }

        per_case.append(row)

    # ── per-criterion table ───────────────────────────────────────────────────
    all_criteria = list(next(iter(ideal_idx.values()))["evaluation"]["scores"].keys())

    per_criterion: list[dict] = []
    for crit in all_criteria:
        ideal_vals = [
            ideal_idx[cid]["evaluation"]["scores"].get(crit)
            for cid in case_ids
            if cid in ideal_idx
        ]
        ideal_pass_rate = sum(1 for v in ideal_vals if v) / len(ideal_vals) if ideal_vals else 0.0

        crit_row: dict[str, Any] = {
            "criterion": crit,
            "ideal_pass_rate": round(ideal_pass_rate, 3),
            "models": {},
        }

        for m in models:
            label = _model_label(m["raw"])
            idx = _index_by_case(m["raw"]["results"])
            vals = [
                idx[cid]["evaluation"]["scores"].get(crit)
                for cid in case_ids
                if cid in idx
            ]
            if not vals:
                crit_row["models"][label] = {"pass_rate": None, "agreement_with_ideal": None}
                continue
            pass_rate = sum(1 for v in vals if v) / len(vals)
            # agreement per-criterion across all cases
            agreement = sum(
                1 for cid in case_ids
                if cid in ideal_idx and cid in idx
                and idx[cid]["evaluation"]["scores"].get(crit)
                == ideal_idx[cid]["evaluation"]["scores"].get(crit)
            ) / len(case_ids)
            crit_row["models"][label] = {
                "pass_rate": round(pass_rate, 3),
                "agreement_with_ideal": round(agreement, 3),
            }

        per_criterion.append(crit_row)

    # ── summary ───────────────────────────────────────────────────────────────
    ideal_mean = sum(
        ideal_idx[cid]["evaluation"]["total_score"]
        for cid in case_ids if cid in ideal_idx
    ) / len(case_ids)

    summary_models: list[dict] = []
    for m in models:
        label = _model_label(m["raw"])
        idx = _index_by_case(m["raw"]["results"])
        scores = [
            idx[cid]["evaluation"]["total_score"]
            for cid in case_ids if cid in idx
        ]
        if not scores:
            continue
        mean_score = sum(scores) / len(scores)
        mean_delta = mean_score - ideal_mean
        mean_agreement = sum(
            _criterion_agreement(
                ideal_idx[cid]["evaluation"]["scores"],
                idx[cid]["evaluation"]["scores"],
            )
            for cid in case_ids if cid in ideal_idx and cid in idx
        ) / len(case_ids)
        summary_models.append({
            "label": label,
            "model": m["raw"].get("model", "unknown"),
            "temperature": m["raw"].get("temperature"),
            "cases_ok": m["raw"].get("cases_ok"),
            "mean_score": round(mean_score, 2),
            "mean_delta_vs_ideal": round(mean_delta, 2),
            "mean_criterion_agreement": round(mean_agreement, 3),
            "elapsed_total_seconds": m["raw"].get("elapsed_total_seconds"),
        })

    return {
        "ideal": {
            "path": str(ideal_path),
            "model": ideal_raw.get("model", "unknown"),
            "temperature": ideal_raw.get("temperature"),
            "mean_score": round(ideal_mean, 2),
            "cases_ok": ideal_raw.get("cases_ok"),
        },
        "summary": summary_models,
        "per_case": per_case,
        "per_criterion": per_criterion,
    }


def _model_label(raw: dict) -> str:
    model = raw.get("model") or "unknown"
    temp = raw.get("temperature")
    label = model.split("/")[-1] if "/" in model else model
    if temp is not None:
        label += f"_t{temp}"
    return label


# ── pretty printer ────────────────────────────────────────────────────────────

def _print_report(report: dict) -> None:
    ideal = report["ideal"]
    summary = report["summary"]
    per_case = report["per_case"]
    per_criterion = report["per_criterion"]

    model_labels = [m["label"] for m in summary]

    print("=" * 80)
    print("MODEL COMPARISON REPORT")
    print("=" * 80)
    print(f"Baseline: {ideal['model']}  mean={ideal['mean_score']:.1f}  cases={ideal['cases_ok']}")
    print()

    # summary table
    print("── SUMMARY ──────────────────────────────────────────────────────────────────")
    header = f"{'model':<30} {'mean':>6} {'delta':>7} {'crit_agree':>11} {'cases':>6} {'sec':>6}"
    print(header)
    print("-" * len(header))
    for m in summary:
        print(
            f"{m['label']:<30} "
            f"{m['mean_score']:>6.1f} "
            f"{m['mean_delta_vs_ideal']:>+7.1f} "
            f"{m['mean_criterion_agreement']:>11.1%} "
            f"{str(m['cases_ok'] or '?'):>6} "
            f"{str(m['elapsed_total_seconds'] or '?'):>6}"
        )
    print()

    # per-case table
    print("── PER CASE ─────────────────────────────────────────────────────────────────")
    col_w = 12
    hdr = f"{'case_id':<42} {'ideal':>6}"
    for lbl in model_labels:
        short = lbl[:col_w]
        hdr += f"  {short:>{col_w}} {'Δ':>5}"
    print(hdr)
    print("-" * (len(hdr) + 4))
    for row in per_case:
        line = f"{row['case_id']:<42} {row['ideal_score']:>6.1f}"
        for lbl in model_labels:
            md = row["models"].get(lbl, {})
            s = md.get("score")
            d = md.get("delta")
            s_str = f"{s:.1f}" if s is not None else "   ?"
            d_str = f"{d:+.1f}" if d is not None else "    ?"
            line += f"  {s_str:>{col_w}} {d_str:>5}"
        print(line)
    print()

    # per-criterion agreement
    print("── PER CRITERION (agreement with ideal) ─────────────────────────────────────")
    hdr2 = f"{'criterion':<42} {'ideal%':>7}"
    for lbl in model_labels:
        short = lbl[:10]
        hdr2 += f"  {short:>10} {'agree':>6}"
    print(hdr2)
    print("-" * (len(hdr2) + 4))
    for cr in per_criterion:
        line = f"{cr['criterion']:<42} {cr['ideal_pass_rate']:>7.0%}"
        for lbl in model_labels:
            md = cr["models"].get(lbl, {})
            pr = md.get("pass_rate")
            ag = md.get("agreement_with_ideal")
            pr_str = f"{pr:.0%}" if pr is not None else "    ?"
            ag_str = f"{ag:.0%}" if ag is not None else "     ?"
            line += f"  {pr_str:>10} {ag_str:>6}"
        print(line)
    print()
    print("=" * 80)


# ── main ──────────────────────────────────────────────────────────────────────

def main() -> None:
    parser = argparse.ArgumentParser(description="Compare run_compare result JSONs vs ideal")
    parser.add_argument("--ideal", type=Path, required=True, help="Baseline result JSON")
    parser.add_argument("--results", type=Path, nargs="+", required=True, help="Result JSONs to compare")
    parser.add_argument("--output", type=Path, default=None, help="Optional: write full report to JSON")
    args = parser.parse_args()

    if not args.ideal.exists():
        print(f"ERROR: ideal file not found: {args.ideal}", file=sys.stderr)
        sys.exit(1)

    result_paths = [p for p in args.results if p.exists() and p.resolve() != args.ideal.resolve()]
    missing = [p for p in args.results if not p.exists()]
    if missing:
        print(f"WARNING: files not found (skipped): {missing}", file=sys.stderr)

    if not result_paths:
        print("No result files to compare (all missing or same as ideal).", file=sys.stderr)
        sys.exit(1)

    report = build_report(args.ideal, result_paths)
    _print_report(report)

    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
        print(f"Full report written to {args.output}")


if __name__ == "__main__":
    main()
