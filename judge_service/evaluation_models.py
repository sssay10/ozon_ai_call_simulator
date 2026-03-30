from typing import Dict, List
from pydantic import BaseModel, Field


class TimecodeItem(BaseModel):
    label: str | None = Field(default=None, description="Type of note or issue")
    timestamp: str | None = Field(default=None, description="Timestamp if available")
    comment: str | None = Field(default=None, description="Short explanation")


class EvaluationResponse(BaseModel):
    """Complete evaluation response from LLM judge."""

    scores: Dict[str, bool | int | None] = Field(
        default_factory=dict,
        description=(
            "Individual criterion scores. "
            "Values must be: boolean for binary criteria, "
            "integer 0-10 for politeness, or null if not applicable."
        ),
    )
    total_score: float = Field(0, description="Total calculated score")
    critical_errors: List[str] = Field(default_factory=list, description="List of critical errors found")
    feedback_positive: List[str] = Field(default_factory=list, description="Positive feedback points")
    feedback_improvement: List[str] = Field(default_factory=list, description="Areas for improvement")
    recommendations: List[str] = Field(default_factory=list, description="Specific recommendations")
    timecodes: List[TimecodeItem] = Field(default_factory=list, description="Timecodes for errors/feedback")