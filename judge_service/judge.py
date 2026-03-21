import logging
import os
import re
from pathlib import Path
from typing import Any, Dict, List, Tuple

from langchain_core.output_parsers import PydanticOutputParser
from langchain_core.prompts import ChatPromptTemplate
from langchain_community.llms import Ollama
from langchain_openai import ChatOpenAI

from evaluation_models import EvaluationResponse
from rag.retriever import SimpleJudgeRetriever
from scenarios import get_scenario_config

BASE_DIR = Path(__file__).resolve().parent
PROMPT_TEMPLATE_PATH = BASE_DIR / "judge_prompt.txt"

logger = logging.getLogger(__name__)


class LLMJudge:
    def __init__(self) -> None:
        llm_provider = os.getenv("LLM_PROVIDER", "openrouter").lower().strip()

        openrouter_api_key = os.getenv("OPENROUTER_API_KEY", "")
        openrouter_model = os.getenv("OPENROUTER_MODEL", "openai/gpt-4o-mini")
        openrouter_base_url = os.getenv("OPENROUTER_BASE_URL", "https://openrouter.ai/api/v1")

        ollama_base_url = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434")
        ollama_model = os.getenv("OLLAMA_MODEL", "qwen2:7b-instruct-q4_K_M")

        self.prompt_template = self._load_prompt_template()
        self.retriever = SimpleJudgeRetriever(logger=logger)

        if llm_provider == "ollama":
            try:
                self.llm = Ollama(
                    model=ollama_model,
                    base_url=ollama_base_url,
                    temperature=0.2,
                )
                self.backend_name = "ollama"
                self.use_structured_output = False
                logger.info(
                    "LLMJudge: Initialized with Ollama model %s at %s",
                    ollama_model,
                    ollama_base_url,
                )
            except Exception as e:
                logger.error("Failed to initialize Ollama: %s", e)
                raise
        else:
            if not openrouter_api_key:
                logger.warning("OPENROUTER_API_KEY not set. LLM will not work.")

            self.llm = ChatOpenAI(
                model=openrouter_model,
                api_key=openrouter_api_key,
                base_url=openrouter_base_url,
                default_headers={
                    "HTTP-Referer": "https://github.com/your-repo",
                    "X-Title": "Judge Service",
                },
                temperature=0.2,
                extra_body={"reasoning": {"max_tokens": 0}},
            )
            self.backend_name = "openrouter"
            self.use_structured_output = True
            logger.info(
                "LLMJudge: Initialized with OpenRouter model %s",
                openrouter_model,
            )

        self.output_parser = PydanticOutputParser(pydantic_object=EvaluationResponse)
        logger.info("LLMJudge initialized: provider=%s", self.backend_name)

    def _load_prompt_template(self) -> str:
        with open(PROMPT_TEMPLATE_PATH, "r", encoding="utf-8") as f:
            return f.read()

    def _build_prompt(
        self,
        transcript: List[Dict[str, str]],
        scenario_config: Any,
        retrieved_context: str = "",
    ) -> str:
        transcript_str = "\n".join(
            f"{(msg.get('role') or '').upper()}: {msg.get('text') or ''}"
            for msg in transcript
        )

        compliance_must_have = "\n".join(
            f"- {item}" for item in (scenario_config.compliance_must_have or [])
        )
        compliance_must_avoid = "\n".join(
            f"- {item}" for item in (scenario_config.compliance_must_avoid or [])
        )
        relevant_criteria_str = ", ".join(scenario_config.relevant_criteria or [])

        return self.prompt_template.format(
            scenario_title=scenario_config.title,
            scenario_description=scenario_config.description,
            scenario_difficulty=scenario_config.difficulty,
            scenario_archetype=scenario_config.client_archetype,
            transcript=transcript_str,
            compliance_must_have=compliance_must_have,
            compliance_must_avoid=compliance_must_avoid,
            relevant_criteria=relevant_criteria_str,
            retrieved_context=retrieved_context or "Контекст не найден.",
        )

    @staticmethod
    def _first_manager_utterance(transcript: List[Dict[str, str]]) -> str:
        for m in transcript:
            if (m.get("role") or "").lower() == "manager":
                return (m.get("text") or "").strip()
        return ""

    @staticmethod
    def _manager_text(transcript: List[Dict[str, str]]) -> str:
        return " ".join(
            (m.get("text") or "").lower()
            for m in transcript
            if (m.get("role") or "").lower() == "manager"
        )

    @staticmethod
    def _client_text(transcript: List[Dict[str, str]]) -> str:
        return " ".join(
            (m.get("text") or "").lower()
            for m in transcript
            if (m.get("role") or "").lower() == "client"
        )

    @staticmethod
    def _has_bank_word(text: str) -> bool:
        return re.search(r"\bбанк(а|у|ом|е)?\b", (text or "").lower()) is not None

    @staticmethod
    def _looks_like_self_intro(text: str) -> bool:
        t = (text or "").lower()
        return (
            re.search(r"\b(меня зовут|это|я|вас приветствует|я из|это .+ из)\b", t)
            is not None
            and "озон" in t
        )

    @staticmethod
    def _has_congratulation(transcript: List[Dict[str, str]]) -> bool:
        manager_text = " ".join(
            (m.get("text") or "").lower()
            for m in transcript
            if (m.get("role") or "").lower() == "manager"
        )
        return (
            "поздрав" in manager_text
            and (
                "регистрац" in manager_text
                or "старт" in manager_text
                or "озон" in manager_text
                or "ozon" in manager_text
            )
        )

    @staticmethod
    def _extract_client_profile(transcript: List[Dict[str, str]]) -> Dict[str, Any]:
        text = " ".join(
            (m.get("text") or "").lower()
            for m in transcript
            if (m.get("role") or "").lower() == "client"
        )

        client_type = "unknown"
        if re.search(r"\b(я\s+ип|я\s+индивидуальный\s+предприниматель|я\s+предприниматель)\b", text):
            client_type = "ip"
        elif re.search(r"\b(я\s+ооо|у\s+нас\s+ооо|мы\s+ооо|общество\s+с\s+ограниченной\s+ответственностью)\b", text):
            client_type = "ooo"
        elif re.search(r"\b(я\s+не\s+ип|я\s+физическое\s+лицо|я\s+частное\s+лицо)\b", text):
            client_type = "physical_person"

        has_employees: bool | None = None
        if re.search(r"\b(есть\s+сотрудники|у\s+меня\s+есть\s+сотрудники|у\s+нас\s+есть\s+сотрудники)\b", text):
            has_employees = True
        elif re.search(r"\b(нет\s+сотрудников|без\s+сотрудников|сотрудников\s+нет|работаю\s+один)\b", text):
            has_employees = False

        return {
            "client_type": client_type,
            "has_employees": has_employees,
        }

    @staticmethod
    def _remove_items_by_patterns(items: List[str], patterns: List[str]) -> List[str]:
        if not items:
            return []
        lowered_patterns = [p.lower() for p in patterns]
        filtered = []
        for item in items:
            item_lower = item.lower()
            if any(p in item_lower for p in lowered_patterns):
                continue
            filtered.append(item)
        return filtered

    @staticmethod
    def _filter_timecodes_by_patterns(
        items: List[Dict[str, Any]],
        patterns: List[str],
    ) -> List[Dict[str, Any]]:
        if not items:
            return []
        lowered_patterns = [p.lower() for p in patterns]
        filtered = []
        for item in items:
            label = str(item.get("label") or "").lower()
            comment = str(item.get("comment") or "").lower()
            combined = f"{label} {comment}"
            if any(p in combined for p in lowered_patterns):
                continue
            filtered.append(item)
        return filtered

    @staticmethod
    def _ensure_politeness(scores: Dict[str, Any]) -> Tuple[Dict[str, Any], int]:
        val = scores.get("politeness", None)
        if val is None:
            scores["politeness"] = 5
            return scores, 5
        try:
            iv = int(val)
            iv = max(0, min(10, iv))
            scores["politeness"] = iv
            return scores, iv
        except Exception:
            scores["politeness"] = 5
            return scores, 5

    @staticmethod
    def _recompute_total_score(
        scores: Dict[str, Any],
        relevant_criteria: List[str],
        critical_errors: List[str],
    ) -> float:
        rel = relevant_criteria or []

        expected_binary = [k for k in rel if k != "politeness"]
        expected_binary_count = len(expected_binary)

        applicable = 0
        passed = 0

        for key in expected_binary:
            val = scores.get(key, None)
            if isinstance(val, bool):
                applicable += 1
                passed += 1 if val else 0

        binary = (passed / applicable) if applicable else 0.0
        coverage = (applicable / expected_binary_count) if expected_binary_count else 0.0

        pol = max(0, min(10, int(scores.get("politeness", 5)))) / 10.0
        total = (0.8 * binary + 0.2 * pol) * 10.0

        if coverage < 0.34:
            total = min(total, 6.5)
        elif coverage < 0.5:
            total = min(total, 7.5)
        elif coverage < 0.67:
            total = min(total, 8.5)

        if critical_errors:
            total = max(0.0, total - 3.0)

        return round(total, 1)

    @staticmethod
    def _ensure_all_relevant_scores_present(
        scores: Dict[str, Any],
        relevant_criteria: List[str],
    ) -> Dict[str, Any]:
        scores = scores or {}
        for key in relevant_criteria or []:
            scores.setdefault(key, None)
        return scores

    def _apply_deterministic_score_fixes(
        self,
        result: Dict[str, Any],
        transcript: List[Dict[str, str]],
    ) -> Dict[str, Any]:
        scores = result.get("scores") or {}
        manager_text = self._manager_text(transcript)
        client_text = self._client_text(transcript)

        greeting_utt = self._first_manager_utterance(transcript)
        has_bank_in_greeting = self._has_bank_word(greeting_utt)

        if self._looks_like_self_intro(greeting_utt) and not has_bank_in_greeting:
            scores["greeting_correct"] = True
            logger.info("DEBUG deterministic score fix: greeting_correct=True")

        if self._has_congratulation(transcript):
            scores["congratulation_given"] = True
            logger.info("DEBUG deterministic score fix: congratulation_given=True")

        if (
            ("индивидуальный предприниматель" in client_text or "я ип" in client_text)
            and (
                ("бесплат" in manager_text and ("тариф" in manager_text or "счет" in manager_text or "счёт" in manager_text))
                or "бесплатный тариф" in manager_text
                or "стартовый бесплатный тариф" in manager_text
            )
        ):
            scores["compliance_free_account_ip"] = True
            logger.info("DEBUG deterministic score fix: compliance_free_account_ip=True")

        if (
            ("индивидуальный предприниматель" in client_text or "я ип" in client_text)
            and "паспорт" in manager_text
            and (
                "документ" in manager_text
                or "из документов" in manager_text
                or "нужен" in manager_text
            )
        ):
            scores["compliance_account_docs_ip"] = True
            logger.info("DEBUG deterministic score fix: compliance_account_docs_ip=True")

        closing_signals = 0
        if "встреч" in manager_text or "подъех" in manager_text or "договор" in manager_text:
            closing_signals += 1
        if any(x in manager_text for x in ["понедель", "вторник", "сред", "четверг", "пятниц", "будний", "10 утра", "9", "17"]):
            closing_signals += 1
        if any(x in manager_text for x in ["смс", "подтвержден", "подтверждени", "адрес"]):
            closing_signals += 1
        if "город" in manager_text or "москв" in client_text:
            closing_signals += 1

        if closing_signals >= 3:
            scores["closing_success"] = True
            logger.info(
                "DEBUG deterministic score fix: closing_success=True (signals=%s)",
                closing_signals,
            )

        result["scores"] = scores
        return result

    def _apply_accounting_semantic_fix(
        self,
        result: Dict[str, Any],
        transcript: List[Dict[str, str]],
    ) -> Dict[str, Any]:
        scores = result.get("scores") or {}
        feedback_improvement = result.get("feedback_improvement") or []
        recommendations = result.get("recommendations") or []
        relevant_criteria = result.get("relevant_criteria") or []

        transcript_text = " ".join((m.get("text") or "").lower() for m in transcript)
        client_profile = result.get("client_profile") or {}

        has_ip_signal = any(
            x in transcript_text
            for x in ["ип", "индивидуальный предприниматель"]
        )
        has_no_employees_signal = any(
            x in transcript_text
            for x in ["нет сотрудников", "без сотрудников", "работаю один", "сотрудников пока нет"]
        )
        has_accounting_signal = any(
            x in transcript_text
            for x in [
                "бухгалтер",
                "бухгалтерия",
                "онлайн-бухгалтерия",
                "бухгалтерское обслуживание",
                "будем делать бухгалтерию",
                "бухгалтерия в подарок",
                "обслуживание в подарок",
            ]
        )

        if (
            "compliance_buh_free_usn_income" in relevant_criteria
            and has_accounting_signal
            and (has_ip_signal or client_profile.get("client_type") == "ip")
            and (has_no_employees_signal or client_profile.get("has_employees") is False)
        ):
            scores["compliance_buh_free_usn_income"] = True
            logger.info(
                "DEBUG semantic accounting fix: compliance_buh_free_usn_income=True"
            )

            feedback_improvement = self._remove_items_by_patterns(
                feedback_improvement,
                [
                    "не было упоминания о бесплатной онлайн-бухгалтерии",
                    "не было упоминания бухгалтерии",
                    "не предложил бухгалтерию",
                    "не упомянул бухгалтерию",
                    "не было упоминания о бухгалтерии",
                ],
            )

            recommendations = self._remove_items_by_patterns(
                recommendations,
                [
                    "предложить бесплатную онлайн-бухгалтерию",
                    "предложить бухгалтерию",
                    "упомянуть бухгалтерию",
                ],
            )

        result["scores"] = scores
        result["feedback_improvement"] = feedback_improvement
        result["recommendations"] = recommendations
        return result

    def _apply_profile_guardrails(
        self,
        result: Dict[str, Any],
        transcript: List[Dict[str, str]],
    ) -> Dict[str, Any]:
        scores = result.get("scores") or {}
        feedback_improvement = result.get("feedback_improvement") or []
        recommendations = result.get("recommendations") or []
        relevant_criteria = result.get("relevant_criteria") or []

        client_profile = self._extract_client_profile(transcript)
        result["client_profile"] = client_profile
        logger.info("DEBUG extracted client_profile=%s", client_profile)

        client_type = client_profile.get("client_type")
        has_employees = client_profile.get("has_employees")

        if client_type in {"physical_person", "ooo"}:
            for key in [
                "compliance_free_account_ip",
                "compliance_account_docs_ip",
                "compliance_buh_free_usn_income",
            ]:
                if key in relevant_criteria:
                    scores[key] = None

            feedback_improvement = self._remove_items_by_patterns(
                feedback_improvement,
                [
                    "ип",
                    "паспорта рф",
                    "оригинал паспорта",
                    "для открытия счёта ип",
                    "для открытия счета ип",
                    "бесплатном обслуживании для новых продавцов",
                    "бесплатности расчётного счёта",
                    "бесплатности расчетного счета",
                    "бесплатен на старте",
                    "новых продавцов",
                ],
            )
            recommendations = self._remove_items_by_patterns(
                recommendations,
                [
                    "ип",
                    "паспорта рф",
                    "оригинал паспорта",
                    "для открытия счёта ип",
                    "для открытия счета ип",
                    "бесплатен на старте",
                    "новых продавцов",
                    "бесплатное обслуживание",
                    "расчётного счёта",
                    "расчетного счета",
                ],
            )

            logger.info(
                "DEBUG applied non-IP guardrail: client_type=%s; nulled IP-only criteria",
                client_type,
            )

        if has_employees is True and "compliance_buh_free_usn_income" in relevant_criteria:
            scores["compliance_buh_free_usn_income"] = None
            logger.info(
                "DEBUG applied employees guardrail: nulled compliance_buh_free_usn_income"
            )

        result["scores"] = scores
        result["feedback_improvement"] = feedback_improvement
        result["recommendations"] = recommendations
        return result

    def _apply_feedback_consistency(self, result: Dict[str, Any]) -> Dict[str, Any]:
        scores = result.get("scores") or {}
        feedback_positive = result.get("feedback_positive") or []
        feedback_improvement = result.get("feedback_improvement") or []
        recommendations = result.get("recommendations") or []
        timecodes = result.get("timecodes") or []

        if scores.get("greeting_correct") is True:
            feedback_improvement = self._remove_items_by_patterns(
                feedback_improvement,
                [
                    "некорректное приветствие",
                    "не представ",
                    "корректное приветствие",
                    "формате 'это <имя> из ozon'",
                    "формате 'это <имя> из озон'",
                    "приветств",
                ],
            )
            recommendations = self._remove_items_by_patterns(
                recommendations,
                [
                    "корректное приветствие",
                    "это <имя> из ozon",
                    "это <имя> из озон",
                    "самопрезентации",
                    "приветств",
                    "представ",
                ],
            )
            timecodes = self._filter_timecodes_by_patterns(
                timecodes,
                [
                    "greeting_correct",
                    "приветств",
                    "представ",
                    "некорректное приветствие",
                ],
            )
            if not any("представ" in x.lower() for x in feedback_positive):
                feedback_positive.append("Менеджер корректно представился как сотрудник Ozon.")

        if scores.get("congratulation_given") is True:
            feedback_improvement = self._remove_items_by_patterns(
                feedback_improvement,
                [
                    "поздравление",
                    "поздравил клиента",
                    "поздравить клиента",
                    "не было поздравления",
                    "регистрац",
                ],
            )
            recommendations = self._remove_items_by_patterns(
                recommendations,
                [
                    "поздравить клиента",
                    "поздравление",
                    "регистрац",
                ],
            )
            timecodes = self._filter_timecodes_by_patterns(
                timecodes,
                [
                    "congratulation_given",
                    "поздрав",
                    "регистрац",
                ],
            )
            if not any("поздрав" in x.lower() for x in feedback_positive):
                feedback_positive.append("Менеджер корректно поздравил клиента с регистрацией на Ozon.")

        if scores.get("compliance_free_account_ip") is True:
            feedback_improvement = self._remove_items_by_patterns(
                feedback_improvement,
                [
                    "бесплатном обслуживании",
                    "бесплатности расчётного счёта",
                    "бесплатности расчетного счета",
                    "счёт для новых продавцов бесплатен",
                    "счет для новых продавцов бесплатен",
                    "бесплатный тариф",
                ],
            )
            recommendations = self._remove_items_by_patterns(
                recommendations,
                [
                    "счёт для новых продавцов бесплатен",
                    "счет для новых продавцов бесплатен",
                    "бесплатен на старте",
                    "бесплатный тариф",
                ],
            )
            timecodes = self._filter_timecodes_by_patterns(
                timecodes,
                [
                    "compliance_free_account_ip",
                    "бесплат",
                    "тариф",
                    "новых продавцов",
                ],
            )

        if scores.get("compliance_account_docs_ip") is True:
            feedback_improvement = self._remove_items_by_patterns(
                feedback_improvement,
                [
                    "оригинал паспорта",
                    "для открытия счёта ип",
                    "для открытия счета ип",
                    "нужен только оригинал паспорта",
                    "паспорт",
                    "документ",
                ],
            )
            recommendations = self._remove_items_by_patterns(
                recommendations,
                [
                    "оригинал паспорта",
                    "для открытия счёта ип",
                    "для открытия счета ип",
                    "паспорт",
                    "документ",
                ],
            )
            timecodes = self._filter_timecodes_by_patterns(
                timecodes,
                [
                    "compliance_account_docs_ip",
                    "паспорт",
                    "документ",
                    "открытия счёта ип",
                    "открытия счета ип",
                ],
            )

        if scores.get("closing_success") is True:
            feedback_improvement = self._remove_items_by_patterns(
                feedback_improvement,
                [
                    "закрытие разговора не было успешным",
                    "не были собраны ключевые детали",
                    "не было четкого закрытия",
                    "успешного закрытия разговора",
                    "закрытия разговора",
                ],
            )
            recommendations = self._remove_items_by_patterns(
                recommendations,
                [
                    "собрать ключевые детали",
                    "успешного закрытия",
                    "закрытия разговора",
                    "встреч",
                ],
            )
            timecodes = self._filter_timecodes_by_patterns(
                timecodes,
                [
                    "closing_success",
                    "закрыти",
                    "встреч",
                    "ключевые детали",
                    "подтверждени",
                ],
            )

        result["feedback_positive"] = feedback_positive
        result["feedback_improvement"] = feedback_improvement
        result["recommendations"] = recommendations
        result["timecodes"] = timecodes
        return result

    def evaluate(
        self,
        transcript: List[Dict[str, str]],
        scenario_id: str = "novice_ip_no_account_easy",
    ) -> Dict[str, Any]:
        try:
            scenario_config = get_scenario_config(scenario_id)

            retrieved_context = self.retriever.retrieve(
                transcript=transcript,
                scenario_config=scenario_config,
            )
            logger.info(
                "RAG retrieved context length=%s for scenario_id=%s",
                len(retrieved_context),
                scenario_id,
            )

            prompt_text = self._build_prompt(
                transcript=transcript,
                scenario_config=scenario_config,
                retrieved_context=retrieved_context,
            )

            evaluation = None

            if self.use_structured_output:
                try:
                    escaped_prompt_text = prompt_text.replace("{", "{{").replace("}", "}}")
                    prompt = ChatPromptTemplate.from_messages(
                        [
                            ("system", "You are a strict evaluator. Follow the instructions precisely."),
                            ("user", escaped_prompt_text),
                        ]
                    )
                    structured_llm = self.llm.with_structured_output(
                        EvaluationResponse,
                        method="function_calling",
                    )
                    chain = prompt | structured_llm
                    evaluation = chain.invoke({})

                    if evaluation is None:
                        raise ValueError("Structured output returned None")

                except Exception as struct_err:
                    logger.warning(
                        "Structured output failed (%s), falling back to manual parsing",
                        struct_err,
                    )
                    format_instructions = self.output_parser.get_format_instructions()
                    full_prompt_text = prompt_text + "\n\n" + format_instructions

                    escaped_full_prompt_text = full_prompt_text.replace("{", "{{").replace("}", "}}")
                    prompt = ChatPromptTemplate.from_messages(
                        [
                            ("system", "You are a strict evaluator. Follow the instructions precisely."),
                            ("user", escaped_full_prompt_text),
                        ]
                    )
                    raw_chain = prompt | self.llm
                    raw_response = raw_chain.invoke({})
                    content = raw_response.content if hasattr(raw_response, "content") else str(raw_response)

                    try:
                        evaluation = self.output_parser.parse(content)
                    except Exception as parse_err:
                        logger.warning(
                            "Failed to parse response, trying to extract JSON: %s",
                            parse_err,
                        )
                        json_match = re.search(r"\{.*\}", content, re.DOTALL)
                        if json_match:
                            content = json_match.group(0)
                        evaluation = self.output_parser.parse(content)
            else:
                format_instructions = self.output_parser.get_format_instructions()
                full_prompt_text = prompt_text + "\n\n" + format_instructions

                escaped_full_prompt_text = full_prompt_text.replace("{", "{{").replace("}", "}}")
                prompt = ChatPromptTemplate.from_messages(
                    [
                        ("system", "You are a strict evaluator. Follow the instructions precisely."),
                        ("user", escaped_full_prompt_text),
                    ]
                )
                chain = prompt | self.llm
                raw_response = chain.invoke({})

                if hasattr(raw_response, "content"):
                    content = raw_response.content
                elif isinstance(raw_response, str):
                    content = raw_response
                else:
                    content = str(raw_response)

                try:
                    evaluation = self.output_parser.parse(content)
                except Exception as parse_err:
                    logger.warning(
                        "Failed to parse Ollama response, trying to extract JSON: %s",
                        parse_err,
                    )
                    json_match = re.search(r"\{.*\}", content, re.DOTALL)
                    if json_match:
                        content = json_match.group(0)
                    evaluation = self.output_parser.parse(content)

            if evaluation is None:
                raise ValueError("LLM evaluation returned None - unable to parse response")

            result = evaluation.model_dump()
            result["scenario_id"] = scenario_id
            result["relevant_criteria"] = scenario_config.relevant_criteria or []
            result["model_used"] = getattr(
                self.llm,
                "model_name",
                getattr(self.llm, "model", "unknown"),
            )
            result["judge_backend"] = self.backend_name
            result["client_profile"] = result.get("client_profile", {}) or {}

            scores = result.get("scores") or {}
            scores = self._ensure_all_relevant_scores_present(
                scores=scores,
                relevant_criteria=result["relevant_criteria"],
            )
            critical_errors = result.get("critical_errors") or []

            greeting_utt = self._first_manager_utterance(transcript)
            logger.info("DEBUG first manager utterance: %r", greeting_utt)

            has_bank_in_greeting = self._has_bank_word(greeting_utt)

            if critical_errors and not has_bank_in_greeting:
                before = list(critical_errors)
                critical_errors = [e for e in critical_errors if "банк" not in e.lower()]
                if len(before) != len(critical_errors):
                    logger.info(
                        "DEBUG removed hallucinated 'банк' critical_errors. greeting=%r",
                        greeting_utt,
                    )

            if scores.get("greeting_correct") is False and not has_bank_in_greeting:
                if self._looks_like_self_intro(greeting_utt):
                    scores["greeting_correct"] = True
                    logger.info(
                        "DEBUG greeting_correct corrected by deterministic check. greeting=%r",
                        greeting_utt,
                    )

            result["scores"] = scores
            result["critical_errors"] = critical_errors

            result = self._apply_deterministic_score_fixes(result=result, transcript=transcript)
            result = self._apply_profile_guardrails(result=result, transcript=transcript)
            result = self._apply_accounting_semantic_fix(result=result, transcript=transcript)
            result = self._apply_feedback_consistency(result=result)

            scores = result.get("scores") or {}
            scores = self._ensure_all_relevant_scores_present(
                scores=scores,
                relevant_criteria=result.get("relevant_criteria") or [],
            )
            critical_errors = result.get("critical_errors") or []

            scores, _ = self._ensure_politeness(scores)

            total = self._recompute_total_score(
                scores=scores,
                relevant_criteria=result.get("relevant_criteria") or [],
                critical_errors=critical_errors,
            )

            result["scores"] = scores
            result["critical_errors"] = critical_errors
            result["total_score"] = total

            return result

        except Exception as e:
            logger.error("Error in LLMJudge.evaluate: %s", e, exc_info=True)
            return {
                "error": "LLM evaluation failed",
                "details": str(e),
                "scores": {},
                "total_score": 0.0,
                "critical_errors": ["Не удалось обработать диалог"],
                "feedback_positive": [],
                "feedback_improvement": [],
                "recommendations": [],
                "client_profile": {},
                "scenario_id": scenario_id,
                "relevant_criteria": [],
                "model_used": "unknown",
                "judge_backend": "unknown",
            }
        
        