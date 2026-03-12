import sys
import json
from pathlib import Path
from typing import Any

sys.path.append(str(Path(__file__).resolve().parent.parent))

from judge import LLMJudge  # noqa: E402


FIXTURES_DIR = Path("evals/fixtures")


def load_fixtures() -> list[dict]:
    fixtures = []
    for path in sorted(FIXTURES_DIR.glob("*.json")):
        data = json.loads(path.read_text(encoding="utf-8"))
        data["_file"] = str(path)
        fixtures.append(data)
    return fixtures


def check_expected(result: dict[str, Any], expected: dict[str, Any]) -> dict[str, Any]:
    checks: list[dict[str, Any]] = []

    result_scores = result.get("scores", {}) or {}
    result_critical_errors = result.get("critical_errors", []) or []
    result_total_score = result.get("total_score", 0.0) or 0.0

    expected_scores = expected.get("scores", {}) or {}
    for key, expected_value in expected_scores.items():
        actual_value = result_scores.get(key)
        passed = actual_value == expected_value
        checks.append(
            {
                "type": "score",
                "field": key,
                "expected": expected_value,
                "actual": actual_value,
                "passed": passed,
            }
        )

    if "critical_errors" in expected:
        expected_critical_errors = expected.get("critical_errors", [])
        passed = result_critical_errors == expected_critical_errors
        checks.append(
            {
                "type": "critical_errors_exact",
                "field": "critical_errors",
                "expected": expected_critical_errors,
                "actual": result_critical_errors,
                "passed": passed,
            }
        )

    if "critical_errors_contains" in expected:
        required_substrings = expected.get("critical_errors_contains", [])
        for needle in required_substrings:
            passed = any(needle.lower() in err.lower() for err in result_critical_errors)
            checks.append(
                {
                    "type": "critical_errors_contains",
                    "field": "critical_errors",
                    "expected": needle,
                    "actual": result_critical_errors,
                    "passed": passed,
                }
            )

    if "min_total_score" in expected:
        min_score = expected["min_total_score"]
        passed = result_total_score >= min_score
        checks.append(
            {
                "type": "min_total_score",
                "field": "total_score",
                "expected": f">= {min_score}",
                "actual": result_total_score,
                "passed": passed,
            }
        )

    if "max_total_score" in expected:
        max_score = expected["max_total_score"]
        passed = result_total_score <= max_score
        checks.append(
            {
                "type": "max_total_score",
                "field": "total_score",
                "expected": f"<= {max_score}",
                "actual": result_total_score,
                "passed": passed,
            }
        )

    soft_checks = expected.get("soft_checks", {}) or {}
    for key, expected_value in soft_checks.items():
        actual_value = result_scores.get(key)
        checks.append(
            {
                "type": "soft_check",
                "field": key,
                "expected": expected_value,
                "actual": actual_value,
                "passed": True,
            }
        )

    passed_all_hard_checks = all(
        item["passed"] for item in checks if item["type"] != "soft_check"
    )

    return {
        "passed": passed_all_hard_checks,
        "checks": checks,
    }


def print_case_report(case_id: str, scenario_id: str, result: dict[str, Any], validation: dict[str, Any]) -> None:
    print("\n" + "=" * 80)
    print(f"CASE: {case_id}")
    print(f"SCENARIO: {scenario_id}")
    print("-" * 80)
    print("RESULT:")
    print(json.dumps(result, ensure_ascii=False, indent=2))
    print("-" * 80)
    print("CHECKS:")

    for item in validation["checks"]:
        mark = "PASS" if item["passed"] else "FAIL"
        print(
            f"[{mark}] {item['type']} | {item['field']} | "
            f"expected={item['expected']} | actual={item['actual']}"
        )

    print("-" * 80)
    print(f"CASE STATUS: {'PASS' if validation['passed'] else 'FAIL'}")


def main() -> None:
    fixtures = load_fixtures()
    if not fixtures:
        print("No fixtures found in evals/fixtures")
        return

    judge = LLMJudge()

    total_cases = 0
    passed_cases = 0

    for fixture in fixtures:
        total_cases += 1

        case_id = fixture["id"]
        scenario_id = fixture["scenario_id"]
        transcript = fixture["transcript"]
        expected = fixture.get("expected", {})

        result = judge.evaluate(
            transcript=transcript,
            scenario_id=scenario_id,
        )

        validation = check_expected(result, expected)
        print_case_report(case_id, scenario_id, result, validation)

        if validation["passed"]:
            passed_cases += 1

    print("\n" + "=" * 80)
    print("SUMMARY")
    print("=" * 80)
    print(f"Passed cases: {passed_cases}/{total_cases}")
    print(f"Failed cases: {total_cases - passed_cases}/{total_cases}")


if __name__ == "__main__":
    main()
    