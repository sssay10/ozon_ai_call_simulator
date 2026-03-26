from __future__ import annotations

import json
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from judge_v2.pipeline import JudgeV2Pipeline
from judge_v2.testing import fake_llm_generate_json, load_fixture_as_transcript


def main() -> None:
    project_root = Path(__file__).resolve().parent.parent
    kb_root = project_root / "knowledge_base" / "normalized"
    fixture_path = project_root / "evals" / "fixtures" / "novice_ip_bad_01.json"

    pipeline = JudgeV2Pipeline(
        kb_root=kb_root,
        llm_generate_json=fake_llm_generate_json,
    )

    transcript = load_fixture_as_transcript(fixture_path)
    result = pipeline.run(transcript)

    print(json.dumps(result, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
