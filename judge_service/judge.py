import logging
import os
import re
from pathlib import Path
from typing import Any, Dict, List, Tuple

from langchain_core.prompts import ChatPromptTemplate
from langchain_openai import ChatOpenAI
from langchain_community.llms import Ollama
from langchain_core.output_parsers import PydanticOutputParser

from evaluation_models import EvaluationResponse
from scenarios import get_scenario_config
from rag.retriever import SimpleJudgeRetriever

BASE_DIR = Path(__file__).resolve().parent
PROMPT_TEMPLATE_PATH = BASE_DIR / "judge_prompt.txt"

logger = logging.getLogger(__name__)


class LLMJudge:
    def __init__(self):
        llm_provider = os.getenv("LLM_PROVIDER", "openrouter").lower().strip()

        # OpenRouter
        openrouter_api_key = os.getenv("OPENROUTER_API_KEY", "")
        openrouter_model = os.getenv("OPENROUTER_MODEL", "openai/gpt-4o-mini")
        openrouter_base_url = os.getenv("OPENROUTER_BASE_URL", "https://openrouter.ai/api/v1")

        # Ollama
        ollama_base_url = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434")
        ollama_model = os.getenv("OLLAMA_MODEL", "qwen2:7b-instruct-q4_K_M")

        self.prompt_template = self._load_prompt_template()
        self.retriever = SimpleJudgeRetriever()

        if llm_provider == "ollama":
            try:
                self.llm = Ollama(
                    model=ollama_model,
                    base_url=ollama_base_url,
                    temperature=0.2,
                )
                self.backend_name = "ollama"
                self.use_structured_output = False
                logger.info("LLMJudge: Initialized with Ollama model %s at %s", ollama_model, ollama_base_url)
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
                extra_body={
                    "reasoning": {
                        "max_tokens": 0
                    }
                },
            )
            self.backend_name = "openrouter"
            self.use_structured_output = True
            logger.info("LLMJudge: Initialized with OpenRouter model %s", openrouter_model)

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

        compliance_must_have = "\n".join(f"- {item}" for item in (scenario_config.compliance_must_have or []))
        compliance_must_avoid = "\n".join(f"- {item}" for item in (scenario_config.compliance_must_avoid or []))
        relevant_criteria_str = ", ".join(scenario_config.relevant_criteria or [])

        prompt = self.prompt_template.format(
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
        return prompt

    @staticmethod
    def _first_manager_utterance(transcript: List[Dict[str, str]]) -> str:
        for m in transcript:
            if (m.get("role") or "").lower() == "manager":
                return (m.get("text") or "").strip()
        return ""

    @staticmethod
    def _has_bank_word(text: str) -> bool:
        return re.search(r"\bбанк(а|у|ом|е)?\b", (text or "").lower()) is not None

    @staticmethod
    def _looks_like_self_intro(text: str) -> bool:
        t = (text or "").lower()
        return re.search(r"\b(меня зовут|это|я|вас приветствует|я из|это .+ из)\b", t) is not None and "озон" in t

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
    def _recompute_total_score(scores: Dict[str, Any], relevant_criteria: List[str], critical_errors: List[str]) -> float:
        rel = relevant_criteria or []

        applicable = 0
        passed = 0

        for k in rel:
            if k == "politeness":
                continue
            v = scores.get(k, None)
            if isinstance(v, bool):
                applicable += 1
                passed += 1 if v else 0

        binary = (passed / applicable) if applicable else 0.0
        pol = max(0, min(10, int(scores.get("politeness", 5)))) / 10.0

        total = (0.8 * binary + 0.2 * pol) * 10.0

        if critical_errors:
            total = max(0.0, total - 3.0)

        return round(total, 1)

    def evaluate(self, transcript: List[Dict[str, str]], scenario_id: str = "novice_ip_no_account_easy") -> Dict[str, Any]:
        try:
            scenario_config = get_scenario_config(scenario_id)

            retrieved_context = self.retriever.retrieve(
                transcript=transcript,
                scenario_config=scenario_config,
            )
            logger.info("RAG retrieved context length=%s for scenario_id=%s", len(retrieved_context), scenario_id)

            prompt_text = self._build_prompt(
                transcript=transcript,
                scenario_config=scenario_config,
                retrieved_context=retrieved_context,
            )

            evaluation = None

            if self.use_structured_output:
                try:
                    escaped_prompt_text = prompt_text.replace("{", "{{").replace("}", "}}")
                    prompt = ChatPromptTemplate.from_messages([
                        ("system", "You are a strict evaluator. Follow the instructions precisely."),
                        ("user", escaped_prompt_text),
                    ])
                    structured_llm = self.llm.with_structured_output(EvaluationResponse)
                    chain = prompt | structured_llm
                    evaluation = chain.invoke({})

                    if evaluation is None:
                        raise ValueError("Structured output returned None")

                except Exception as struct_err:
                    logger.warning("Structured output failed (%s), falling back to manual parsing", struct_err)
                    format_instructions = self.output_parser.get_format_instructions()
                    full_prompt_text = prompt_text + "\n\n" + format_instructions

                    escaped_full_prompt_text = full_prompt_text.replace("{", "{{").replace("}", "}}")
                    prompt = ChatPromptTemplate.from_messages([
                        ("system", "You are a strict evaluator. Follow the instructions precisely."),
                        ("user", escaped_full_prompt_text),
                    ])
                    raw_chain = prompt | self.llm
                    raw_response = raw_chain.invoke({})

                    content = raw_response.content if hasattr(raw_response, "content") else str(raw_response)

                    try:
                        evaluation = self.output_parser.parse(content)
                    except Exception as parse_err:
                        logger.warning("Failed to parse response, trying to extract JSON: %s", parse_err)
                        json_match = re.search(r"\{.*\}", content, re.DOTALL)
                        if json_match:
                            content = json_match.group(0)
                        evaluation = self.output_parser.parse(content)

            else:
                format_instructions = self.output_parser.get_format_instructions()
                full_prompt_text = prompt_text + "\n\n" + format_instructions

                escaped_full_prompt_text = full_prompt_text.replace("{", "{{").replace("}", "}}")
                prompt = ChatPromptTemplate.from_messages([
                    ("system", "You are a strict evaluator. Follow the instructions precisely."),
                    ("user", escaped_full_prompt_text),
                ])
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
                    logger.warning("Failed to parse Ollama response, trying to extract JSON: %s", parse_err)
                    json_match = re.search(r"\{.*\}", content, re.DOTALL)
                    if json_match:
                        content = json_match.group(0)
                    evaluation = self.output_parser.parse(content)

            if evaluation is None:
                raise ValueError("LLM evaluation returned None - unable to parse response")

            result = evaluation.model_dump()

            result["scenario_id"] = scenario_id
            result["relevant_criteria"] = scenario_config.relevant_criteria or []
            result["model_used"] = getattr(self.llm, "model_name", getattr(self.llm, "model", "unknown"))
            result["judge_backend"] = self.backend_name
            result["client_profile"] = result.get("client_profile", {}) or {}

            scores = result.get("scores") or {}
            critical_errors = result.get("critical_errors") or []

            greeting_utt = self._first_manager_utterance(transcript)
            logger.info("DEBUG first manager utterance: %r", greeting_utt)

            has_bank_in_greeting = self._has_bank_word(greeting_utt)

            if critical_errors and (not has_bank_in_greeting):
                before = list(critical_errors)
                critical_errors = [e for e in critical_errors if "банк" not in e.lower()]
                if len(before) != len(critical_errors):
                    logger.info("DEBUG removed hallucinated 'банк' critical_errors. greeting=%r", greeting_utt)

            if scores.get("greeting_correct") is False and (not has_bank_in_greeting):
                if self._looks_like_self_intro(greeting_utt):
                    scores["greeting_correct"] = True
                    logger.info("DEBUG greeting_correct corrected by deterministic check. greeting=%r", greeting_utt)

            scores, _ = self._ensure_politeness(scores)

            relevant = result.get("relevant_criteria") or []
            total = self._recompute_total_score(scores=scores, relevant_criteria=relevant, critical_errors=critical_errors)

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
                "timecodes": [],
                "client_profile": {},
                "scenario_id": scenario_id,
                "relevant_criteria": [],
                "model_used": "unknown",
                "judge_backend": "unknown",
            }
        
