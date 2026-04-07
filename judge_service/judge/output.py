"""Legacy module name: canonical model is ``JudgeEvaluation`` in ``judge.merged_evaluation``."""

from __future__ import annotations

from judge.merged_evaluation import JudgeEvaluation

# Backward-compatible alias for imports: ``from judge.output import JudgeLLMOutput``
JudgeLLMOutput = JudgeEvaluation

__all__ = ["JudgeEvaluation", "JudgeLLMOutput"]
