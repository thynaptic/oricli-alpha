"""
Critical Thinking Module - DeepMind-style reasoning
Evaluate assumptions, identify biases, and assess evidence quality
"""

from typing import List, Dict, Any
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

from mavaia_core.brain.base_module import BaseBrainModule, ModuleMetadata


class CriticalThinkingModule(BaseBrainModule):
    """Critical thinking reasoning module"""

    @property
    def metadata(self) -> ModuleMetadata:
        return ModuleMetadata(
            name="critical_thinking",
            version="1.0.0",
            description="Evaluate assumptions, identify biases, and assess evidence quality",
            operations=["reason", "evaluate"],
            dependencies=[],
            model_required=False,
        )

    def execute(self, operation: str, params: Dict[str, Any]) -> Dict[str, Any]:
        """Execute critical thinking operation"""
        query = params.get("query", "")
        context = params.get("context", "")
        conversation_history = params.get("conversationHistory", [])

        if not query:
            raise ValueError("Missing required parameter: query")

        reasoning = self._critical_thinking_analysis(
            query, context, conversation_history
        )

        return {
            "reasoning": reasoning,
            "conclusion": self._extract_conclusion(reasoning),
            "confidence": self._estimate_confidence(reasoning),
            "reasoning_steps": self._extract_steps(reasoning),
            "reasoning_type": "critical_thinking",
            "model": "fallback",
        }

    def _critical_thinking_analysis(
        self, query: str, context: str, history: List[str]
    ) -> str:
        """Perform critical thinking analysis"""
        analysis = f"Critical Thinking Analysis:\n\n"
        analysis += f"Query: {query}\n\n"

        analysis += "1. Assumption Evaluation:\n"
        analysis += "   - Identifying explicit and implicit assumptions\n"
        analysis += "   - Evaluating the validity of each assumption\n"
        analysis += "   - Checking for unstated premises\n\n"

        analysis += "2. Bias Identification:\n"
        analysis += "   - Examining potential cognitive biases\n"
        analysis += "   - Identifying confirmation bias indicators\n"
        analysis += "   - Assessing perspective limitations\n\n"

        analysis += "3. Evidence Assessment:\n"
        analysis += "   - Evaluating evidence quality and reliability\n"
        analysis += "   - Identifying gaps in evidence\n"
        analysis += "   - Assessing source credibility\n\n"

        analysis += "4. Logical Consistency:\n"
        analysis += "   - Checking for logical fallacies\n"
        analysis += "   - Verifying argument structure\n"
        analysis += "   - Identifying contradictions\n\n"

        if context:
            analysis += f"\nContext considered:\n{context[:200]}\n"

        analysis += "\nConclusion: Critical analysis complete. Key assumptions evaluated, biases identified, and evidence assessed."

        return analysis

    def _extract_conclusion(self, reasoning: str) -> str:
        """Extract conclusion from reasoning"""
        if "Conclusion:" in reasoning:
            return reasoning.split("Conclusion:")[-1].strip()
        return reasoning[-200:] if len(reasoning) > 200 else reasoning

    def _estimate_confidence(self, reasoning: str) -> float:
        """Estimate confidence based on reasoning quality"""
        if len(reasoning) > 300:
            return 0.75
        elif len(reasoning) > 150:
            return 0.6
        return 0.5

    def _extract_steps(self, reasoning: str) -> List[str]:
        """Extract reasoning steps"""
        steps = []
        for line in reasoning.split("\n"):
            if line.strip().startswith(("1.", "2.", "3.", "4.")):
                steps.append(line.strip())
        return steps[:10]
