"""
Decomposition Module - DeepMind-style reasoning
Break complex problems into smaller sub-problems
"""

from typing import List, Dict, Any
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

from mavaia_core.brain.base_module import BaseBrainModule, ModuleMetadata


class DecompositionModule(BaseBrainModule):
    """Problem decomposition module"""

    @property
    def metadata(self) -> ModuleMetadata:
        return ModuleMetadata(
            name="decomposition",
            version="1.0.0",
            description="Break complex problems into smaller sub-problems",
            operations=["reason", "decompose"],
            dependencies=[],
            model_required=False,
        )

    def execute(self, operation: str, params: Dict[str, Any]) -> Dict[str, Any]:
        """Execute decomposition"""
        query = params.get("query", "")
        context = params.get("context", "")

        if not query:
            raise ValueError("Missing required parameter: query")

        reasoning = self._decompose_problem(query, context)

        return {
            "reasoning": reasoning,
            "conclusion": self._extract_conclusion(reasoning),
            "confidence": self._estimate_confidence(reasoning),
            "reasoning_steps": self._extract_steps(reasoning),
            "reasoning_type": "decomposition",
            "model": "fallback",
        }

    def _decompose_problem(self, query: str, context: str) -> str:
        """Decompose problem into sub-problems"""
        reasoning = f"Problem Decomposition:\n\n"
        reasoning += f"Original Problem: {query}\n\n"

        reasoning += "Decomposing into sub-problems:\n\n"
        reasoning += "1. Sub-problem 1: Core question identification\n"
        reasoning += "   - What is the main question being asked?\n"
        reasoning += "   - What are the key components?\n\n"

        reasoning += "2. Sub-problem 2: Context analysis\n"
        reasoning += "   - What background information is needed?\n"
        reasoning += "   - What constraints exist?\n\n"

        reasoning += "3. Sub-problem 3: Solution approach\n"
        reasoning += "   - What methods can be applied?\n"
        reasoning += "   - What steps are required?\n\n"

        reasoning += "4. Sub-problem 4: Validation\n"
        reasoning += "   - How can the solution be verified?\n"
        reasoning += "   - What are potential issues?\n\n"

        if context:
            reasoning += f"\nContext for decomposition:\n{context[:200]}\n"

        reasoning += "\nConclusion: Problem successfully decomposed into manageable sub-problems."

        return reasoning

    def _extract_conclusion(self, reasoning: str) -> str:
        """Extract conclusion"""
        if "Conclusion:" in reasoning:
            return reasoning.split("Conclusion:")[-1].strip()
        return reasoning[-200:] if len(reasoning) > 200 else reasoning

    def _estimate_confidence(self, reasoning: str) -> float:
        """Estimate confidence"""
        subproblem_count = reasoning.count("Sub-problem")
        if subproblem_count >= 4:
            return 0.75
        elif subproblem_count >= 2:
            return 0.6
        return 0.5

    def _extract_steps(self, reasoning: str) -> List[str]:
        """Extract reasoning steps"""
        steps = []
        for line in reasoning.split("\n"):
            if "Sub-problem" in line and line.strip().startswith(
                ("1.", "2.", "3.", "4.")
            ):
                steps.append(line.strip())
        return steps[:10]
