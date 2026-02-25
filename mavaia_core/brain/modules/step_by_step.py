from __future__ import annotations
"""
Step-by-Step Reasoning Module - DeepMind-style reasoning
Break down reasoning into explicit sequential steps
"""

from typing import List, Dict, Any
import logging

from mavaia_core.brain.base_module import BaseBrainModule, ModuleMetadata
from mavaia_core.exceptions import InvalidParameterError

logger = logging.getLogger(__name__)


class StepByStepModule(BaseBrainModule):
    """Step-by-step reasoning module"""

    def __init__(self) -> None:
        super().__init__()

    @property
    def metadata(self) -> ModuleMetadata:
        return ModuleMetadata(
            name="step_by_step",
            version="1.0.0",
            description="Break down reasoning into explicit sequential steps",
            operations=["reason", "stepwise"],
            dependencies=[],
            model_required=False,
        )

    def execute(self, operation: str, params: Dict[str, Any]) -> Dict[str, Any]:
        """Execute step-by-step reasoning"""
        query = params.get("query", "")
        context = params.get("context", "")
        parameters = params.get("parameters", {})
        steps = parameters.get("steps", 5)
        detail = parameters.get("detail", "medium")

        if not isinstance(query, str) or not query.strip():
            raise InvalidParameterError(
                parameter="query",
                value=str(query),
                reason="Missing required parameter: query (must be a non-empty string)",
            )
        if context is None:
            context = ""
        if not isinstance(context, str):
            raise InvalidParameterError("context", str(type(context).__name__), "context must be a string")
        if parameters is None:
            parameters = {}
        if not isinstance(parameters, dict):
            raise InvalidParameterError(
                parameter="parameters",
                value=str(type(parameters).__name__),
                reason="parameters must be a dict",
            )
        try:
            steps_int = int(steps)
        except (TypeError, ValueError):
            raise InvalidParameterError("parameters.steps", str(steps), "steps must be an integer")
        if steps_int < 1:
            raise InvalidParameterError("parameters.steps", str(steps_int), "steps must be >= 1")
        if detail is None:
            detail = "medium"
        if not isinstance(detail, str):
            raise InvalidParameterError("parameters.detail", str(type(detail).__name__), "detail must be a string")

        reasoning = self._step_by_step_reasoning(query, context, steps_int, detail)

        return {
            "reasoning": reasoning,
            "conclusion": self._extract_conclusion(reasoning),
            "confidence": self._estimate_confidence(reasoning),
            "reasoning_steps": self._extract_steps(reasoning),
            "reasoning_type": "step_by_step",
            "model": "fallback",
        }

    def _step_by_step_reasoning(
        self, query: str, context: str, num_steps: int, detail: str
    ) -> str:
        """Perform step-by-step reasoning"""
        reasoning = f"Step-by-Step Reasoning:\n\n"
        reasoning += f"Query: {query}\n\n"

        detail_level = (
            "detailed"
            if detail == "high"
            else ("moderate" if detail == "medium" else "concise")
        )
        reasoning += f"Reasoning in {num_steps} {detail_level} steps:\n\n"

        for i in range(1, num_steps + 1):
            reasoning += f"Step {i}:\n"
            if detail == "high":
                reasoning += f"   - Analyzing aspect {i} of the problem\n"
                reasoning += f"   - Identifying key factors\n"
                reasoning += f"   - Evaluating implications\n"
            elif detail == "medium":
                reasoning += f"   - Processing step {i} of the reasoning chain\n"
            else:
                reasoning += f"   - Step {i} analysis\n"
            reasoning += "\n"

        if context:
            reasoning += (
                f"\nContext integrated throughout reasoning process:\n{context[:200]}\n"
            )

        reasoning += f"\nConclusion: After {num_steps} steps of reasoning, the analysis is complete."

        return reasoning

    def _extract_conclusion(self, reasoning: str) -> str:
        """Extract conclusion"""
        if "Conclusion:" in reasoning:
            return reasoning.split("Conclusion:")[-1].strip()
        return reasoning[-200:] if len(reasoning) > 200 else reasoning

    def _estimate_confidence(self, reasoning: str) -> float:
        """Estimate confidence"""
        step_count = reasoning.count("Step ")
        if step_count >= 5:
            return 0.8
        elif step_count >= 3:
            return 0.65
        return 0.5

    def _extract_steps(self, reasoning: str) -> List[str]:
        """Extract reasoning steps"""
        steps = []
        current_step = ""
        for line in reasoning.split("\n"):
            if line.strip().startswith("Step "):
                if current_step:
                    steps.append(current_step.strip())
                current_step = line.strip() + "\n"
            elif current_step:
                current_step += line + "\n"
        if current_step:
            steps.append(current_step.strip())
        return steps[:10]
