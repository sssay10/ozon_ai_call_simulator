import sys
import json
from pathlib import Path

sys.path.append(str(Path(__file__).resolve().parent.parent))

from judge import LLMJudge


fixture_path = Path("evals/fixtures/novice_ip_good_01.json")
data = json.loads(fixture_path.read_text(encoding="utf-8"))

judge = LLMJudge()

result = judge.evaluate(
    transcript=data["transcript"],
    scenario_id=data["scenario_id"],
)

print("=== JUDGE RESULT START ===")
print(json.dumps(result, ensure_ascii=False, indent=2))
print("=== JUDGE RESULT END ===")