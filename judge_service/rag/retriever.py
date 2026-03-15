from typing import Any


class SimpleJudgeRetriever:
    def __init__(self, logger=None) -> None:
        from rag.loader import load_knowledge_documents

        self.docs = load_knowledge_documents()
        self.logger = logger

    @staticmethod
    def _build_transcript_text(transcript: list[dict]) -> str:
        return " ".join((m.get("text") or "").lower() for m in transcript)

    @staticmethod
    def _extract_signals(transcript_text: str) -> set[str]:
        signals = set()

        if any(x in transcript_text for x in ["паспорт", "документ", "оригинал"]):
            signals.add("docs")

        if any(x in transcript_text for x in ["бесплатно", "обслуживание", "счет", "счёт"]):
            signals.add("free_account")

        if any(x in transcript_text for x in ["встреч", "перезвон", "подтверж", "время", "дата", "формат"]):
            signals.add("closing")

        if any(x in transcript_text for x in ["поняли", "правильно", "удобно", "подходит", "подойдёт", "подойдет"]):
            signals.add("verification")

        if any(x in transcript_text for x in ["это", "меня зовут", "я из", "вас приветствует"]):
            signals.add("greeting")

        if any(x in transcript_text for x in ["поздравля", "регистрац", "новый продавец", "старт на озон"]):
            signals.add("congratulation")

        if any(x in transcript_text for x in ["усн", "доходы", "без сотрудников", "бухгалтер", "бухгалтерия"]):
            signals.add("buh")

        return signals

    @staticmethod
    def _doc_preview(text: str, limit: int = 160) -> str:
        text = (text or "").replace("\n", " ").strip()
        return text[:limit] + ("..." if len(text) > limit else "")

    def retrieve(self, transcript: list[dict], scenario_config: Any, top_k: int = 3) -> str:
        scenario_id = getattr(scenario_config, "id", "")
        relevant_criteria = set(getattr(scenario_config, "relevant_criteria", []) or [])
        transcript_text = self._build_transcript_text(transcript)
        signals = self._extract_signals(transcript_text)

        scored_docs: list[tuple[int, dict]] = []

        for doc in self.docs:
            score = 0
            doc_scenario = doc.get("scenario")
            doc_criterion = doc.get("criterion")
            doc_category = doc.get("category")

            if doc_scenario == scenario_id:
                score += 5

            if doc_criterion in relevant_criteria:
                score += 4

            if doc_category == "eval_policy":
                score += 1

            if "greeting" in signals and doc_criterion == "greeting_correct":
                score += 3

            if "free_account" in signals and doc_criterion == "compliance_free_account_ip":
                score += 3

            if "docs" in signals and doc_criterion == "compliance_account_docs_ip":
                score += 3

            if "verification" in signals and doc_criterion == "verification_agreement_correctly_understood":
                score += 3

            if "closing" in signals and doc_criterion == "closing_success":
                score += 3

            if "congratulation" in signals and doc_criterion == "congratulation_given":
                score += 3

            if "buh" in signals and doc_criterion == "compliance_buh_free_usn_income":
                score += 3

            if score > 0:
                scored_docs.append((score, doc))

        scored_docs.sort(key=lambda x: x[0], reverse=True)
        top_scored_docs = scored_docs[:top_k]
        top_docs = [doc for _, doc in top_scored_docs]

        if self.logger:
            self.logger.info(
                "RAG selected docs for scenario_id=%s: %s",
                scenario_id,
                [
                    {
                        "name": doc["name"],
                        "criterion": doc.get("criterion"),
                        "scenario": doc.get("scenario"),
                        "score": score,
                        "preview": self._doc_preview(doc.get("content", "")),
                    }
                    for score, doc in top_scored_docs
                ],
            )

        return "\n\n---\n\n".join(
            f"[SOURCE: {doc['name']} | criterion={doc.get('criterion')} | scenario={doc.get('scenario')}]\n{doc['content']}"
            for doc in top_docs
        )
    