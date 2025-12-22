"""
Query Complexity Analyzer Module

Service to determine if a query warrants supervised self-consistency
or complex reasoning methods.
Ported from Swift QueryComplexityAnalyzer.swift
"""

from dataclasses import dataclass
from typing import Any

from mavaia_core.brain.base_module import BaseBrainModule, ModuleMetadata
from mavaia_core.exceptions import InvalidParameterError


@dataclass
class ComplexityScore:
    """Complexity score result"""

    overall: float
    factors: dict[str, float]
    reasoning: bool
    threshold: float

    @property
    def should_trigger(self) -> bool:
        """Whether complexity score should trigger complex reasoning"""
        return self.overall >= self.threshold


class QueryComplexityAnalyzer(BaseBrainModule):
    """
    Service to determine if a query warrants supervised self-consistency.

    Analyzes query complexity based on length, reasoning keywords,
    domain complexity, and other factors.
    """

    # Complexity thresholds
    _length_threshold = 200  # characters
    _default_threshold = 0.6

    # Reasoning keywords
    _reasoning_keywords = [
        "analyze",
        "compare",
        "explain why",
        "reasoning",
        "step by step",
        "calculate",
        "derive",
        "prove",
        "evaluate",
        "assess",
        "critique",
        "examine",
        "investigate",
        "determine",
        "solve",
        "demonstrate",
    ]

    # Complex domains
    _complex_domains = [
        "mathematics",
        "computer_science",
        "physics",
        "engineering",
        "chemistry",
        "biology",
        "philosophy",
        "logic",
        "theorem",
        "algorithm",
        "proof",
    ]

    def __init__(self) -> None:
        super().__init__()

    @property
    def metadata(self) -> ModuleMetadata:
        return ModuleMetadata(
            name="query_complexity",
            version="1.0.0",
            description=(
                "Analyzes query complexity to determine if supervised "
                "self-consistency or complex reasoning is needed"
            ),
            operations=[
                "analyze_complexity",
                "should_use_supervised_consistency",
            ],
            dependencies=[],
            enabled=True,
            model_required=False,
        )

    def execute(
        self, operation: str, params: dict[str, Any]
    ) -> dict[str, Any]:
        """
        Execute query complexity analysis operations.

        Supported operations:
        - analyze_complexity: Full complexity analysis
        - should_use_supervised_consistency: Quick decision
        """
        if operation == "analyze_complexity":
            return self._analyze_complexity(params)
        elif operation == "should_use_supervised_consistency":
            return self._should_use_supervised_consistency(params)
        else:
            raise InvalidParameterError(
                parameter="operation",
                value=operation,
                reason="Unknown operation for query_complexity",
            )

    def _analyze_complexity(
        self, params: dict[str, Any]
    ) -> dict[str, Any]:
        """
        Analyze query complexity.

        Args:
            params: Dictionary with:
                - query (str): The query to analyze
                - context (str, optional): Additional context
                - self_chaining_metadata (dict, optional): Metadata from self-chaining

        Returns:
            Dictionary with ComplexityScore data
        """
        query = params.get("query", "")
        if not isinstance(query, str) or not query.strip():
            raise InvalidParameterError(
                parameter="query",
                value=str(query),
                reason="query parameter is required and must be a non-empty string",
            )

        context = params.get("context")
        self_chaining_metadata = params.get("self_chaining_metadata")
        if self_chaining_metadata is not None and not isinstance(self_chaining_metadata, dict):
            raise InvalidParameterError(
                parameter="self_chaining_metadata",
                value=str(type(self_chaining_metadata).__name__),
                reason="self_chaining_metadata must be a dict when provided",
            )

        factors: dict[str, float] = {}
        overall = 0.0

        # Factor 1: Query length
        length_score = 0.2 if len(query) > self._length_threshold else 0.0
        factors["length"] = length_score
        overall += length_score

        # Factor 2: Reasoning keywords
        query_lower = query.lower()
        has_reasoning_keywords = any(
            keyword in query_lower
            for keyword in self._reasoning_keywords
        )
        keyword_score = 0.3 if has_reasoning_keywords else 0.0
        factors["reasoning_keywords"] = keyword_score
        overall += keyword_score

        # Factor 3: Complex domain
        has_complex_domain = any(
            domain in query_lower for domain in self._complex_domains
        )
        domain_score = 0.2 if has_complex_domain else 0.0
        factors["complex_domain"] = domain_score
        overall += domain_score

        # Factor 4: Self-chaining estimated complexity
        if self_chaining_metadata:
            estimated_complexity = self_chaining_metadata.get(
                "estimated_complexity", 0.0
            )
            complexity_score = (
                0.3 if estimated_complexity > 0.7 else estimated_complexity * 0.3
            )
            factors["estimated_complexity"] = complexity_score
            overall += complexity_score

        # Factor 5: Number of reasoning modules (if self-chaining was used)
        if self_chaining_metadata:
            reasoning_type = self_chaining_metadata.get("reasoning_type", "")
            estimated_complexity = self_chaining_metadata.get(
                "estimated_complexity", 0.0
            )
            module_count = self._estimate_module_count(
                reasoning_type, estimated_complexity
            )
            module_score = (
                0.2 if module_count >= 3 else (module_count / 3.0) * 0.2
            )
            factors["module_count"] = module_score
            overall += module_score

        # Cap overall at 1.0
        overall = min(overall, 1.0)

        # Determine if reasoning is required
        requires_reasoning = (
            has_reasoning_keywords or has_complex_domain or overall >= 0.5
        )

        score = ComplexityScore(
            overall=overall,
            factors=factors,
            reasoning=requires_reasoning,
            threshold=self._default_threshold,
        )

        return {
            "overall": score.overall,
            "factors": score.factors,
            "reasoning": score.reasoning,
            "threshold": score.threshold,
            "should_trigger": score.should_trigger,
        }

    def _should_use_supervised_consistency(
        self, params: dict[str, Any]
    ) -> dict[str, Any]:
        """
        Determine if supervised self-consistency should be used.

        Args:
            params: Dictionary with:
                - query (str): The query to analyze
                - context (str, optional): Additional context
                - self_chaining_metadata (dict, optional): Metadata

        Returns:
            Dictionary with should_use boolean
        """
        query = params.get("query", "")
        if not isinstance(query, str) or not query.strip():
            raise InvalidParameterError(
                parameter="query",
                value=str(query),
                reason="query parameter is required and must be a non-empty string",
            )

        context = params.get("context")
        self_chaining_metadata = params.get("self_chaining_metadata")

        score_result = self._analyze_complexity(
            {
                "query": query,
                "context": context,
                "self_chaining_metadata": self_chaining_metadata,
            }
        )

        return {"should_use": score_result["should_trigger"]}

    def _estimate_module_count(
        self, reasoning_type: str, complexity: float
    ) -> int:
        """Estimate module count from reasoning type and complexity"""
        type_lower = reasoning_type.lower()

        if "analytical" in type_lower or "comparative" in type_lower:
            return 4 if complexity > 0.7 else 3
        elif "strategic" in type_lower or "diagnostic" in type_lower:
            return 5 if complexity > 0.7 else 3
        elif "creative" in type_lower:
            return 4 if complexity > 0.7 else 2

        # Default based on complexity
        if complexity > 0.8:
            return 4
        elif complexity > 0.6:
            return 3
        else:
            return 2

