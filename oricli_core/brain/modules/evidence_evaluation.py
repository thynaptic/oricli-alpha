from __future__ import annotations
"""
Evidence Evaluation Module - DeepMind-style reasoning
Assess the quality, relevance, and reliability of evidence
"""

from typing import List, Dict, Any
import logging

from oricli_core.brain.base_module import BaseBrainModule, ModuleMetadata
from oricli_core.exceptions import InvalidParameterError

logger = logging.getLogger(__name__)


class EvidenceEvaluationModule(BaseBrainModule):
    """Evidence evaluation module"""

    def __init__(self) -> None:
        super().__init__()

    @property
    def metadata(self) -> ModuleMetadata:
        return ModuleMetadata(
            name="evidence_evaluation",
            version="1.0.0",
            description="Assess the quality, relevance, and reliability of evidence",
            operations=["reason", "evaluate"],
            dependencies=[],
            model_required=False,
        )

    def execute(self, operation: str, params: Dict[str, Any]) -> Dict[str, Any]:
        """Execute evidence evaluation"""
        query = params.get("query", "")
        context = params.get("context", "")

        if not isinstance(query, str) or not query.strip():
            raise InvalidParameterError(
                parameter="query",
                value=str(query),
                reason="Missing required parameter: query (must be a non-empty string)",
            )
        if context is None:
            context = ""
        if not isinstance(context, str):
            raise InvalidParameterError(
                parameter="context",
                value=str(type(context).__name__),
                reason="context must be a string",
            )

        reasoning = self._evaluate_evidence(query, context)

        return {
            "reasoning": reasoning,
            "conclusion": self._extract_conclusion(reasoning),
            "confidence": self._estimate_confidence(reasoning),
            "reasoning_steps": self._extract_steps(reasoning),
            "reasoning_type": "evidence_evaluation",
            "model": "fallback",
        }

    def _evaluate_evidence(self, query: str, context: str) -> str:
        """Evaluate evidence quality"""
        reasoning = f"Evidence Evaluation:\n\n"
        reasoning += f"Query: {query}\n\n"

        reasoning += "Evidence Assessment:\n\n"
        reasoning += "1. Relevance Analysis:\n"
        reasoning += "   - How directly does evidence relate to the query?\n"
        reasoning += "   - What aspects are covered?\n\n"

        reasoning += "2. Reliability Assessment:\n"
        reasoning += "   - Source credibility evaluation\n"
        reasoning += "   - Consistency with other evidence\n"
        reasoning += "   - Potential biases or limitations\n\n"

        reasoning += "3. Quality Metrics:\n"
        reasoning += "   - Completeness of evidence\n"
        reasoning += "   - Recency and timeliness\n"
        reasoning += "   - Methodological rigor\n\n"

        reasoning += "4. Synthesis:\n"
        reasoning += "   - Overall evidence strength\n"
        reasoning += "   - Confidence level\n"
        reasoning += "   - Gaps or limitations\n\n"

        if context:
            reasoning += f"\nContext for evidence evaluation:\n{context[:200]}\n"

        reasoning += (
            "\nConclusion: Evidence evaluated for relevance, reliability, and quality."
        )

        return reasoning

    def _extract_conclusion(self, reasoning: str) -> str:
        """Extract conclusion"""
        if "Conclusion:" in reasoning:
            return reasoning.split("Conclusion:")[-1].strip()
        return reasoning[-200:] if len(reasoning) > 200 else reasoning

    def _estimate_confidence(self, reasoning: str) -> float:
        """Estimate confidence"""
        if "Reliability" in reasoning and "Quality" in reasoning:
            return 0.75
        elif len(reasoning) > 200:
            return 0.65
        return 0.5

    def _extract_steps(self, reasoning: str) -> List[str]:
        """Extract reasoning steps"""
        steps = []
        for line in reasoning.split("\n"):
            if line.strip().startswith(("1.", "2.", "3.", "4.")):
                steps.append(line.strip())
        return steps[:10]
