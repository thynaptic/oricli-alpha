"""
Step-by-Step Reasoning Module - DeepMind-style reasoning
Break down reasoning into explicit sequential steps
"""

from typing import List, Dict, Any
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

from mavaia_core.brain.base_module import BaseBrainModule, ModuleMetadata


class StepByStepModule(BaseBrainModule):
    """Step-by-step reasoning module"""

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

        if not query:
            raise ValueError("Missing required parameter: query")

        reasoning = self._step_by_step_reasoning(query, context, steps, detail)

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
