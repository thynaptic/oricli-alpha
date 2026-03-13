from __future__ import annotations
"""
Chain-of-Thought Complexity Detector

Automatic complexity detection for Chain-of-Thought activation.
Ported from Swift CoTComplexityDetector.swift
"""

import re
from typing import Any
import logging

from oricli_core.brain.base_module import BaseBrainModule, ModuleMetadata
from oricli_core.brain.modules.cot_models import (
    CoTConfiguration,
    CoTComplexityScore,
    ComplexityFactor,
)
from oricli_core.brain.modules.tot_models import ToTComplexityScore
from oricli_core.exceptions import InvalidParameterError

logger = logging.getLogger(__name__)


class CoTComplexityDetector(BaseBrainModule):
    """
    Automatic complexity detection for Chain-of-Thought activation.
    Analyzes queries to determine if CoT or ToT should be used.
    """

    def __init__(self) -> None:
        """Initialize the module"""
        super().__init__()

    @property
    def metadata(self) -> ModuleMetadata:
        return ModuleMetadata(
            name="cot_complexity_detector",
            version="1.0.0",
            description="Automatic complexity detection for Chain-of-Thought activation",
            operations=[
                "analyze_complexity",
                "should_activate_cot",
                "analyze_tot_complexity",
                "should_use_tot",
            ],
            dependencies=[],
            enabled=True,
            model_required=False,
        )

    def initialize(self) -> bool:
        """Initialize the module"""
        return True

    def execute(self, operation: str, params: dict[str, Any]) -> dict[str, Any]:
        """
        Execute complexity detection operations.

        Supported operations:
        - analyze_complexity: Full CoT complexity analysis
        - should_activate_cot: Quick check if CoT should be activated
        - analyze_tot_complexity: Full ToT complexity analysis
        - should_use_tot: Quick check if ToT should be used
        """
        if operation == "analyze_complexity":
            return self._analyze_complexity(params)
        elif operation == "should_activate_cot":
            return self._should_activate_cot(params)
        elif operation == "analyze_tot_complexity":
            return self._analyze_tot_complexity(params)
        elif operation == "should_use_tot":
            return self._should_use_tot(params)
        else:
            raise InvalidParameterError(
                parameter="operation",
                value=operation,
                reason="Unknown operation for cot_complexity_detector",
            )

    def _analyze_complexity(self, params: dict[str, Any]) -> dict[str, Any]:
        """
        Analyze query complexity and determine if CoT should be activated.

        Args:
            params: Dictionary with:
                - query (str): The query to analyze
                - context (str, optional): Additional context
                - configuration (dict, optional): CoTConfiguration as dict

        Returns:
            CoTComplexityScore as dictionary
        """
        query = params.get("query", "")
        if not isinstance(query, str) or not query.strip():
            raise InvalidParameterError(
                parameter="query",
                value=str(query),
                reason="query parameter is required and must be a non-empty string",
            )

        context = params.get("context")
        config_dict = params.get("configuration", {})
        if context is not None and not isinstance(context, str):
            raise InvalidParameterError(
                parameter="context",
                value=str(type(context).__name__),
                reason="context must be a string when provided",
            )
        if config_dict is None:
            config_dict = {}
        if not isinstance(config_dict, dict):
            raise InvalidParameterError(
                parameter="configuration",
                value=str(type(config_dict).__name__),
                reason="configuration must be a dict when provided",
            )

        config = (
            CoTConfiguration.from_dict(config_dict)
            if config_dict
            else CoTConfiguration.default()
        )

        factors: list[ComplexityFactor] = []
        total_score: float = 0.0

        query_lower = query.lower()
        query_length = len(query)
        full_text = f"{query}\n{context}" if context else query

        # Factor 1: Query Length
        length_score = min(query_length / 500.0, 1.0) * 0.15
        if length_score > 0.1:
            factors.append(
                ComplexityFactor(
                    name="query_length",
                    contribution=length_score,
                    description=f"Query length: {query_length} characters",
                )
            )
        total_score += length_score

        # Factor 2: Reasoning Keywords
        reasoning_keywords: list[tuple[str, float]] = [
            ("analyze", 0.25),
            ("compare", 0.20),
            ("calculate", 0.25),
            ("derive", 0.30),
            ("prove", 0.30),
            ("explain why", 0.20),
            ("step by step", 0.25),
            ("reasoning", 0.20),
            ("solve", 0.20),
            ("evaluate", 0.20),
            ("determine", 0.15),
            ("find", 0.15),
        ]

        keyword_score: float = 0.0
        matched_keywords: list[str] = []
        for keyword, weight in reasoning_keywords:
            if keyword in query_lower:
                keyword_score += weight
                matched_keywords.append(keyword)

        keyword_score = min(keyword_score, 0.35)  # Cap at 35%

        if keyword_score > 0.1:
            factors.append(
                ComplexityFactor(
                    name="reasoning_keywords",
                    contribution=keyword_score,
                    description=f"Matched keywords: {', '.join(matched_keywords)}",
                )
            )
        total_score += keyword_score

        # Factor 3: Mathematical Expressions
        math_patterns = [
            r"\d+\s*[+\-*/=<>≤≥]\s*\d+",  # Basic arithmetic
            r"\d+\s*\^\s*\d+",  # Exponents
            r"sqrt|√|∫|∑|∏|π|∞",  # Math symbols
            r"equation|formula|theorem|proof|derivative|integral",
        ]

        math_score: float = 0.0
        for pattern in math_patterns:
            if re.search(pattern, query):
                math_score += 0.15

        math_score = min(math_score, 0.30)  # Cap at 30%

        if math_score > 0.05:
            factors.append(
                ComplexityFactor(
                    name="mathematical_content",
                    contribution=math_score,
                    description="Contains mathematical expressions or symbols",
                )
            )
        total_score += math_score

        # Factor 4: Multi-part Questions
        multi_part_indicators = [
            "first",
            "second",
            "third",
            "then",
            "next",
            "finally",
            "part a",
            "part b",
            "part 1",
            "part 2",
            "question 1",
            "question 2",
        ]

        multi_part_count = sum(1 for indicator in multi_part_indicators if indicator in query_lower)
        multi_part_score = min(multi_part_count * 0.10, 0.20)

        if multi_part_score > 0.05:
            factors.append(
                ComplexityFactor(
                    name="multi_part_question",
                    contribution=multi_part_score,
                    description=f"Contains {multi_part_count} multi-part indicators",
                )
            )
        total_score += multi_part_score

        # Factor 5: Domain-Specific Complexity
        domain_keywords: list[tuple[str, float]] = [
            ("algorithm", 0.15),
            ("complexity", 0.20),
            ("optimization", 0.15),
            ("architecture", 0.10),
            ("hypothesis", 0.15),
            ("experiment", 0.10),
            ("theoretical", 0.15),
            ("practical", 0.10),
        ]

        domain_score: float = 0.0
        matched_domains: list[str] = []
        for keyword, weight in domain_keywords:
            if keyword in query_lower:
                domain_score += weight
                matched_domains.append(keyword)

        domain_score = min(domain_score, 0.25)  # Cap at 25%

        if domain_score > 0.05:
            factors.append(
                ComplexityFactor(
                    name="domain_complexity",
                    contribution=domain_score,
                    description=f"Domain keywords: {', '.join(matched_domains)}",
                )
            )
        total_score += domain_score

        # Factor 6: Question Structure
        question_count = query.count("?")
        question_structure_score = min((question_count - 1) * 0.10, 0.15) if question_count > 1 else 0.0

        if question_structure_score > 0.05:
            factors.append(
                ComplexityFactor(
                    name="question_structure",
                    contribution=question_structure_score,
                    description=f"Contains {question_count} question(s)",
                )
            )
        total_score += question_structure_score

        # Normalize score to 0.0-1.0 range
        total_score = min(total_score, 1.0)

        # Determine if CoT is required
        requires_cot = total_score >= config.min_complexity_score

        # Calculate timeout multiplier based on complexity
        if total_score < 0.4:
            timeout_multiplier = 1.0
        elif total_score < 0.6:
            timeout_multiplier = 1.5
        elif total_score < 0.8:
            timeout_multiplier = 2.0
        else:
            timeout_multiplier = 3.0

        result = CoTComplexityScore(
            score=total_score,
            factors=factors,
            requires_cot=requires_cot,
            estimated_timeout_multiplier=timeout_multiplier,
        )

        return result.to_dict()

    def _should_activate_cot(self, params: dict[str, Any]) -> dict[str, Any]:
        """Quick check if CoT should be activated (without full analysis)"""
        query = params.get("query", "")
        if not isinstance(query, str) or not query.strip():
            raise InvalidParameterError(
                parameter="query",
                value=str(query),
                reason="query parameter is required and must be a non-empty string",
            )

        config_dict = params.get("configuration", {})
        config = (
            CoTConfiguration.from_dict(config_dict)
            if config_dict
            else CoTConfiguration.default()
        )

        score_dict = self._analyze_complexity({"query": query, "configuration": config_dict})
        score = CoTComplexityScore.from_dict(score_dict)

        return {"should_use": score.requires_cot}

    def _analyze_tot_complexity(self, params: dict[str, Any]) -> dict[str, Any]:
        """
        Analyze query to determine if Tree-of-Thought should be used.

        Args:
            params: Dictionary with:
                - query (str): The query to analyze
                - context (str, optional): Additional context

        Returns:
            ToTComplexityScore as dictionary
        """
        query = params.get("query", "")
        if not isinstance(query, str) or not query.strip():
            raise InvalidParameterError(
                parameter="query",
                value=str(query),
                reason="query parameter is required and must be a non-empty string",
            )

        context = params.get("context")

        from oricli_core.brain.modules.tot_models import ComplexityFactor as ToTComplexityFactor

        factors: list[ToTComplexityFactor] = []
        total_score: float = 0.0
        tot_score: float = 0.0  # ToT-specific score
        cot_score: float = 0.0  # CoT-specific score

        query_lower = query.lower()
        full_text = f"{query}\n{context}" if context else query
        full_text_lower = full_text.lower()

        # ToT Indicators - Multi-path exploration problems

        # Factor 1: Comparative Queries
        comparative_keywords = [
            "compare",
            "choose between",
            "which is better",
            "versus",
            "vs",
            "different options",
            "alternatives",
            "pros and cons",
            "trade-off",
            "tradeoff",
            "weigh",
            "contrast",
        ]

        comparative_score: float = 0.0
        matched_comparatives: list[str] = []
        for keyword in comparative_keywords:
            if keyword in query_lower:
                comparative_score += 0.25
                matched_comparatives.append(keyword)

        comparative_score = min(comparative_score, 0.30)

        if comparative_score > 0.05:
            factors.append(
                ToTComplexityFactor(
                    name="comparative_query",
                    contribution=comparative_score,
                    description=f"Comparative keywords: {', '.join(matched_comparatives)}",
                )
            )
            tot_score += comparative_score

        # Factor 2: Exploration Queries
        exploration_keywords = [
            "what are all possible",
            "explore options",
            "brainstorm",
            "generate ideas",
            "list all",
            "find all",
            "enumerate",
            "what could",
            "how many ways",
            "possible solutions",
            "potential approaches",
            "various methods",
        ]

        exploration_score: float = 0.0
        matched_explorations: list[str] = []
        for keyword in exploration_keywords:
            if keyword in query_lower:
                exploration_score += 0.20
                matched_explorations.append(keyword)

        exploration_score = min(exploration_score, 0.30)

        if exploration_score > 0.05:
            factors.append(
                ToTComplexityFactor(
                    name="exploration_query",
                    contribution=exploration_score,
                    description=f"Exploration keywords: {', '.join(matched_explorations)}",
                )
            )
            tot_score += exploration_score

        # Factor 3: Multi-step Decision Queries
        decision_keywords = [
            "decide",
            "evaluate options",
            "select",
            "pick",
            "recommend",
            "suggest",
            "advise",
            "should i",
            "which should",
            "what should",
            "how should",
            "plan",
            "strategy",
            "approach",
        ]

        decision_score: float = 0.0
        matched_decisions: list[str] = []
        for keyword in decision_keywords:
            if keyword in query_lower:
                decision_score += 0.15
                matched_decisions.append(keyword)

        decision_score = min(decision_score, 0.25)

        if decision_score > 0.05:
            factors.append(
                ToTComplexityFactor(
                    name="decision_query",
                    contribution=decision_score,
                    description=f"Decision keywords: {', '.join(matched_decisions)}",
                )
            )
            tot_score += decision_score

        # Factor 4: Creative Problem-Solving
        creative_keywords = [
            "creative",
            "innovative",
            "novel",
            "unique",
            "out of the box",
            "unconventional",
            "multiple perspectives",
            "different viewpoints",
            "various angles",
        ]

        creative_score: float = 0.0
        matched_creatives: list[str] = []
        for keyword in creative_keywords:
            if keyword in query_lower:
                creative_score += 0.10
                matched_creatives.append(keyword)

        creative_score = min(creative_score, 0.20)

        if creative_score > 0.05:
            factors.append(
                ToTComplexityFactor(
                    name="creative_problem_solving",
                    contribution=creative_score,
                    description=f"Creative keywords: {', '.join(matched_creatives)}",
                )
            )
            tot_score += creative_score

        # Factor 5: Sequential/Linear Indicators (CoT preferred)
        sequential_keywords = [
            "step by step",
            "first then",
            "sequentially",
            "in order",
            "calculate",
            "derive",
            "prove",
            "solve",
            "compute",
        ]

        sequential_score: float = 0.0
        for keyword in sequential_keywords:
            if keyword in query_lower:
                sequential_score += 0.15

        sequential_score = min(sequential_score, 0.25)
        cot_score += sequential_score

        # Factor 6: Mathematical/Logical (usually sequential)
        math_patterns = [
            r"\d+\s*[+\-*/=<>≤≥]\s*\d+",
            r"\d+\s*\^\s*\d+",
            r"sqrt|√|∫|∑|∏|π|∞",
            r"equation|formula|theorem|proof",
        ]

        math_score: float = 0.0
        for pattern in math_patterns:
            if re.search(pattern, query):
                math_score += 0.10

        math_score = min(math_score, 0.20)
        cot_score += math_score

        # Calculate total complexity score
        total_score = max(tot_score, cot_score * 0.7)  # ToT gets priority if both present
        total_score = min(total_score, 1.0)

        # Determine requirements
        # ToT is required if ToT-specific score is high and exceeds CoT score
        requires_tot = tot_score > 0.3 and tot_score >= cot_score * 0.8
        # CoT is required if sequential score is high or general complexity is high
        requires_cot = cot_score > 0.3 or total_score > 0.6

        # Calculate timeout multiplier
        if total_score < 0.4:
            timeout_multiplier = 1.0
        elif total_score < 0.6:
            timeout_multiplier = 1.5
        elif total_score < 0.8:
            timeout_multiplier = 2.5  # ToT takes more time
        else:
            timeout_multiplier = 4.0  # Deep ToT exploration

        result = ToTComplexityScore(
            score=total_score,
            factors=factors,
            requires_tot=requires_tot,
            requires_cot=requires_cot,
            estimated_timeout_multiplier=timeout_multiplier,
        )

        return result.to_dict()

    def _should_use_tot(self, params: dict[str, Any]) -> dict[str, Any]:
        """Quick check if ToT should be used (without full analysis)"""
        query = params.get("query", "")
        if not isinstance(query, str) or not query.strip():
            raise InvalidParameterError(
                parameter="query",
                value=str(query),
                reason="query parameter is required and must be a non-empty string",
            )

        context = params.get("context")

        score_dict = self._analyze_tot_complexity({"query": query, "context": context})
        score = ToTComplexityScore.from_dict(score_dict)

        return {"should_use": score.requires_tot}

