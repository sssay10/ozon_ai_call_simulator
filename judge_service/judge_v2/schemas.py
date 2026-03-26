from __future__ import annotations

from enum import Enum
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field


class DocType(str, Enum):
    POLICY = "policy"
    FACT = "fact"
    EVAL_POLICY = "eval_policy"


class RuleKind(str, Enum):
    REQUIRED = "required"
    FORBIDDEN = "forbidden"
    REFERENCE = "reference"


class Priority(str, Enum):
    CRITICAL = "critical"
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"


class Applicability(BaseModel):
    stage: List[str] = Field(default_factory=list)
    legal_form: List[str] = Field(default_factory=list)
    channel: List[str] = Field(default_factory=list)


class RetrievalHints(BaseModel):
    keywords: List[str] = Field(default_factory=list)
    evidence_window: str = "anywhere"
    priority_boost: float = 1.0


class SourceMeta(BaseModel):
    source_type: str
    source_name: str


class KBChunk(BaseModel):
    id: str
    version: int = 1
    doc_type: DocType
    rule_kind: RuleKind
    priority: Priority = Priority.MEDIUM
    title: str

    criterion_tags: List[str] = Field(default_factory=list)
    scenario_tags: List[str] = Field(default_factory=list)

    applicability: Applicability = Field(default_factory=Applicability)
    canonical_rule: str

    positive_examples: List[str] = Field(default_factory=list)
    negative_examples: List[str] = Field(default_factory=list)

    retrieval_hints: RetrievalHints = Field(default_factory=RetrievalHints)
    source: SourceMeta

    pass_conditions: List[str] = Field(default_factory=list)
    fail_conditions: List[str] = Field(default_factory=list)
    null_conditions: List[str] = Field(default_factory=list)


class Utterance(BaseModel):
    turn_index: int
    speaker: str
    text: str
    timestamp: Optional[str] = None


class Transcript(BaseModel):
    session_id: str
    scenario_id: str
    utterances: List[Utterance]


class TranscriptSegment(BaseModel):
    name: str
    start_turn: int
    end_turn: int
    utterances: List[Utterance]


class CriterionResult(BaseModel):
    criterion_id: str
    decision: str  # pass | fail | null
    score: float
    confidence: float
    rationale_short: str
    transcript_evidence: List[Dict[str, Any]] = Field(default_factory=list)
    kb_evidence: List[Dict[str, Any]] = Field(default_factory=list)
    metadata: Dict[str, Any] = Field(default_factory=dict)