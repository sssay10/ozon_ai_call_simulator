from typing import Any, Dict, List
from pydantic import BaseModel, Field


class EvaluationResponse(BaseModel):
    """Complete evaluation response from LLM judge."""
    scores: Dict[str, Any] = Field(
        default_factory=dict,
        description="Individual criterion scores. Keys are criterion names, values are bool (True/False) for binary criteria or int (0-10) for politeness"
    )
    total_score: float = Field(0, description="Total calculated score")
    critical_errors: List[str] = Field(default_factory=list, description="List of critical errors found")
    feedback_positive: List[str] = Field(default_factory=list, description="Positive feedback points")
    feedback_improvement: List[str] = Field(default_factory=list, description="Areas for improvement")
    recommendations: List[str] = Field(default_factory=list, description="Specific recommendations")
