import sys
from pathlib import Path
import json

sys.path.append(str(Path(__file__).resolve().parent.parent))

from rag.retriever import SimpleJudgeRetriever
from scenarios import get_scenario_config


fixture_path = Path("evals/fixtures/novice_ip_good_01.json")
data = json.loads(fixture_path.read_text(encoding="utf-8"))

retriever = SimpleJudgeRetriever()
scenario_config = get_scenario_config(data["scenario_id"])

context = retriever.retrieve(
    transcript=data["transcript"],
    scenario_config=scenario_config,
)

print("=== RETRIEVED CONTEXT START ===")
print(context)
print("=== RETRIEVED CONTEXT END ===")
print(f"\nLength: {len(context)}")