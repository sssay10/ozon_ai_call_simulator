from typing import Any

from rag.loader import load_knowledge_documents


class SimpleJudgeRetriever:
    def __init__(self) -> None:
        self.docs = load_knowledge_documents()

    def retrieve(self, transcript: list[dict], scenario_config: Any, top_k: int = 5) -> str:
        scenario_id = getattr(scenario_config, "id", "")
        relevant_criteria = set(getattr(scenario_config, "relevant_criteria", []) or [])

        scored_docs = []

        for doc in self.docs:
            score = 0
            content = doc["content"].lower()

            if scenario_id and scenario_id.lower() in content:
                score += 3

            for criterion in relevant_criteria:
                if criterion.lower() in content:
                    score += 2

            if doc["category"] == "eval_policy":
                score += 1

            if score > 0:
                scored_docs.append((score, doc))

        scored_docs.sort(key=lambda x: x[0], reverse=True)
        top_docs = [doc for _, doc in scored_docs[:top_k]]

        return "\n\n---\n\n".join(
            f"[SOURCE: {doc['name']}]\n{doc['content']}" for doc in top_docs
        )