"""
Symbolic Reasoning Detector Module

Detects if a query requires symbolic reasoning and classifies the problem type.
Ported from Swift SymbolicReasoningDetector.swift
"""

import re
from dataclasses import dataclass
from typing import Any

from mavaia_core.brain.base_module import BaseBrainModule, ModuleMetadata
from mavaia_core.exceptions import InvalidParameterError


@dataclass
class SymbolicAnalysis:
    """Result from symbolic reasoning detection"""

    requires_symbolic_reasoning: bool
    complexity: float
    problem_type: str  # "sat", "symbolic_math", "planning", "verification", "unknown"
    indicators: list[str]


class SymbolicReasoningDetector(BaseBrainModule):
    """
    Detects if a query requires symbolic reasoning.

    Analyzes queries to determine if they need symbolic solvers
    (SAT, SMT, constraint solving, etc.) and classifies the problem type.
    """

    # Keywords that indicate symbolic reasoning needs
    _logical_keywords: set[str] = {
        "prove",
        "proof",
        "theorem",
        "lemma",
        "corollary",
        "contradiction",
        "logical",
        "logic",
        "boolean",
        "satisfiable",
        "unsatisfiable",
        "constraint",
        "constraints",
        "satisfy",
        "satisfies",
        "satisfying",
    }

    _mathematical_keywords: set[str] = {
        "solve",
        "equation",
        "equations",
        "system of equations",
        "algebra",
        "calculate",
        "compute",
        "derive",
        "formula",
        "formulas",
        "variable",
        "variables",
        "unknown",
        "unknowns",
    }

    _planning_keywords: set[str] = {
        "plan",
        "schedule",
        "optimize",
        "minimize",
        "maximize",
        "resource",
        "resources",
        "allocation",
        "assignment",
    }

    _verification_keywords: set[str] = {
        "verify",
        "validation",
        "validate",
        "correctness",
        "correct",
        "check",
        "ensure",
        "guarantee",
    }

    @property
    def metadata(self) -> ModuleMetadata:
        return ModuleMetadata(
            name="symbolic_reasoning_detector",
            version="1.0.0",
            description=(
                "Detects if a query requires symbolic reasoning and "
                "classifies the problem type"
            ),
            operations=["analyze"],
            dependencies=[],
            enabled=True,
            model_required=False,
        )

    def execute(
        self, operation: str, params: dict[str, Any]
    ) -> dict[str, Any]:
        """
        Execute symbolic reasoning detection operations.

        Supported operations:
        - analyze: Analyze query for symbolic reasoning needs
        """
        if operation == "analyze":
            return self._analyze(params)
        else:
            raise InvalidParameterError(
                parameter="operation",
                value=str(operation),
                reason="Unknown operation for symbolic_reasoning_detector",
            )

    def _analyze(self, params: dict[str, Any]) -> dict[str, Any]:
        """
        Analyze query to determine if symbolic reasoning is needed.

        Args:
            params: Dictionary with:
                - query (str): The query to analyze

        Returns:
            Dictionary with SymbolicAnalysis data
        """
        query = params.get("query", "")
        if not isinstance(query, str) or not query.strip():
            raise InvalidParameterError(
                parameter="query",
                value=str(query),
                reason="query parameter is required and must be a non-empty string",
            )

        query_lower = query.lower()

        # Check for logical problems
        has_logical_keywords = any(
            keyword in query_lower for keyword in self._logical_keywords
        )
        has_mathematical_keywords = any(
            keyword in query_lower
            for keyword in self._mathematical_keywords
        )
        has_planning_keywords = any(
            keyword in query_lower for keyword in self._planning_keywords
        )
        has_verification_keywords = any(
            keyword in query_lower
            for keyword in self._verification_keywords
        )

        # Determine problem type
        if has_logical_keywords:
            problem_type = "sat"
        elif has_mathematical_keywords:
            problem_type = "symbolic_math"
        elif has_planning_keywords:
            problem_type = "planning"
        elif has_verification_keywords:
            problem_type = "verification"
        else:
            problem_type = "unknown"

        # Calculate complexity
        complexity = 0.0

        if has_logical_keywords:
            complexity += 0.4
        if has_mathematical_keywords:
            complexity += 0.3
        if has_planning_keywords:
            complexity += 0.3
        if has_verification_keywords:
            complexity += 0.2

        # Check for constraint indicators
        if "constraint" in query_lower or "satisfy" in query_lower:
            complexity += 0.2

        # Check for multiple variables
        variable_pattern = r"\b[a-z]\b"
        matches = re.findall(variable_pattern, query, re.IGNORECASE)
        if len(matches) > 2:
            complexity += 0.1

        complexity = min(complexity, 1.0)

        requires_symbolic_reasoning = (
            complexity > 0.3 or problem_type != "unknown"
        )

        # Build indicators list
        indicators: list[str] = []
        if has_logical_keywords:
            indicators.append("logical")
        if has_mathematical_keywords:
            indicators.append("mathematical")
        if has_planning_keywords:
            indicators.append("planning")
        if has_verification_keywords:
            indicators.append("verification")

        analysis = SymbolicAnalysis(
            requires_symbolic_reasoning=requires_symbolic_reasoning,
            complexity=complexity,
            problem_type=problem_type,
            indicators=indicators,
        )

        return {
            "requires_symbolic_reasoning": analysis.requires_symbolic_reasoning,
            "complexity": analysis.complexity,
            "problem_type": analysis.problem_type,
            "indicators": analysis.indicators,
        }

