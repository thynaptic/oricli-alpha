from __future__ import annotations
"""
Complexity Detector Module

Analyzes query complexity to determine if Chain-of-Thought, Tree-of-Thought,
or MCTS reasoning should be activated. Ported from Swift CoTComplexityDetector.
"""

import re
from dataclasses import dataclass
from typing import Any

from oricli_core.brain.base_module import BaseBrainModule, ModuleMetadata
from oricli_core.exceptions import InvalidParameterError


@dataclass
class ComplexityFactor:
    """A factor contributing to complexity score"""

    name: str
    contribution: float
    description: str


@dataclass
class CoTComplexityScore:
    """Result from Chain-of-Thought complexity detection analysis"""

    score: float  # 0.0 to 1.0
    factors: list[ComplexityFactor]
    requires_cot: bool
    estimated_timeout_multiplier: float


@dataclass
class ToTComplexityScore:
    """Result from Tree-of-Thought complexity detection analysis"""

    score: float  # 0.0 to 1.0
    factors: list[ComplexityFactor]
    requires_tot: bool
    requires_cot: bool
    estimated_timeout_multiplier: float


@dataclass
class CoTConfiguration:
    """Configuration for chain-of-thought processing"""

    max_steps: int = 5
    min_complexity_score: float = 0.6
    adaptive_timeout: bool = True
    enable_prompt_chaining: bool = True
    reasoning_depth: str = "medium"  # "shallow", "medium", "deep"

    @classmethod
    def default(cls) -> "CoTConfiguration":
        """Return default configuration"""
        return cls()


class ComplexityDetector(BaseBrainModule):
    """
    Complexity detector for reasoning method selection.

    Analyzes queries to determine if Chain-of-Thought, Tree-of-Thought,
    or MCTS reasoning should be activated based on complexity factors.
    """

    @property
    def metadata(self) -> ModuleMetadata:
        return ModuleMetadata(
            name="complexity_detector",
            version="1.0.0",
            description=(
                "Analyzes query complexity to determine reasoning method "
                "(CoT, ToT, MCTS)"
            ),
            operations=[
                "analyze_cot_complexity",
                "should_activate_cot",
                "analyze_tot_complexity",
                "should_use_tot",
            ],
            dependencies=[],
            enabled=True,
            model_required=False,
        )

    def execute(
        self, operation: str, params: dict[str, Any]
    ) -> dict[str, Any]:
        """
        Execute complexity detection operations.

        Supported operations:
        - analyze_cot_complexity: Full CoT complexity analysis
        - should_activate_cot: Quick CoT activation check
        - analyze_tot_complexity: Full ToT complexity analysis
        - should_use_tot: Quick ToT activation check
        """
        if operation == "analyze_cot_complexity":
            return self._analyze_cot_complexity(params)
        elif operation == "should_activate_cot":
            return self._should_activate_cot(params)
        elif operation == "analyze_tot_complexity":
            return self._analyze_tot_complexity(params)
        elif operation == "should_use_tot":
            return self._should_use_tot(params)
        else:
            raise InvalidParameterError(
                parameter="operation",
                value=str(operation),
                reason="Unknown operation for complexity_detector",
            )

    def _analyze_cot_complexity(
        self, params: dict[str, Any]
    ) -> dict[str, Any]:
        """
        Analyze query complexity for Chain-of-Thought.

        Args:
            params: Dictionary with:
                - query (str): The query to analyze
                - context (str, optional): Additional context
                - configuration (dict, optional): CoT configuration

        Returns:
            Dictionary with CoTComplexityScore data
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
        config = self._parse_config(config_dict)

        score = self._calculate_cot_complexity(query, context, config)

        return {
            "score": score.score,
            "factors": [
                {
                    "name": f.name,
                    "contribution": f.contribution,
                    "description": f.description,
                }
                for f in score.factors
            ],
            "requires_cot": score.requires_cot,
            "estimated_timeout_multiplier": score.estimated_timeout_multiplier,
        }

    def _should_activate_cot(self, params: dict[str, Any]) -> dict[str, Any]:
        """
        Quick check if CoT should be activated.

        Args:
            params: Dictionary with:
                - query (str): The query to analyze
                - configuration (dict, optional): CoT configuration

        Returns:
            Dictionary with should_activate boolean
        """
        query = params.get("query", "")
        if not isinstance(query, str) or not query.strip():
            raise InvalidParameterError(
                parameter="query",
                value=str(query),
                reason="query parameter is required and must be a non-empty string",
            )

        config_dict = params.get("configuration", {})
        config = self._parse_config(config_dict)

        score = self._calculate_cot_complexity(query, None, config)
        return {"should_activate": score.requires_cot}

    def _analyze_tot_complexity(
        self, params: dict[str, Any]
    ) -> dict[str, Any]:
        """
        Analyze query complexity for Tree-of-Thought.

        Args:
            params: Dictionary with:
                - query (str): The query to analyze
                - context (str, optional): Additional context

        Returns:
            Dictionary with ToTComplexityScore data
        """
        query = params.get("query", "")
        if not isinstance(query, str) or not query.strip():
            raise InvalidParameterError(
                parameter="query",
                value=str(query),
                reason="query parameter is required and must be a non-empty string",
            )

        context = params.get("context")
        score = self._calculate_tot_complexity(query, context)

        return {
            "score": score.score,
            "factors": [
                {
                    "name": f.name,
                    "contribution": f.contribution,
                    "description": f.description,
                }
                for f in score.factors
            ],
            "requires_tot": score.requires_tot,
            "requires_cot": score.requires_cot,
            "estimated_timeout_multiplier": score.estimated_timeout_multiplier,
        }

    def _should_use_tot(self, params: dict[str, Any]) -> dict[str, Any]:
        """
        Quick check if ToT should be used.

        Args:
            params: Dictionary with:
                - query (str): The query to analyze
                - context (str, optional): Additional context

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
        score = self._calculate_tot_complexity(query, context)
        return {"should_use": score.requires_tot}

    def _parse_config(
        self, config_dict: dict[str, Any]
    ) -> CoTConfiguration:
        """Parse configuration dictionary to CoTConfiguration"""
        return CoTConfiguration(
            max_steps=config_dict.get("max_steps", 5),
            min_complexity_score=config_dict.get("min_complexity_score", 0.6),
            adaptive_timeout=config_dict.get("adaptive_timeout", True),
            enable_prompt_chaining=config_dict.get(
                "enable_prompt_chaining", True
            ),
            reasoning_depth=config_dict.get("reasoning_depth", "medium"),
        )

    def _calculate_cot_complexity(
        self,
        query: str,
        context: str | None,
        config: CoTConfiguration,
    ) -> CoTComplexityScore:
        """Calculate CoT complexity score"""
        factors: list[ComplexityFactor] = []
        total_score = 0.0

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

        keyword_score = 0.0
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

        math_score = 0.0
        for pattern in math_patterns:
            if re.search(pattern, query, re.IGNORECASE):
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

        multi_part_count = sum(
            1 for indicator in multi_part_indicators if indicator in query_lower
        )

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

        domain_score = 0.0
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
        question_structure_score = min((question_count - 1) * 0.10, 0.15)
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

        return CoTComplexityScore(
            score=total_score,
            factors=factors,
            requires_cot=requires_cot,
            estimated_timeout_multiplier=timeout_multiplier,
        )

    def _calculate_tot_complexity(
        self, query: str, context: str | None
    ) -> ToTComplexityScore:
        """Calculate ToT complexity score"""
        factors: list[ComplexityFactor] = []
        total_score = 0.0
        tot_score = 0.0  # ToT-specific score
        cot_score = 0.0  # CoT-specific score

        query_lower = query.lower()
        full_text_lower = (
            f"{query}\n{context}".lower() if context else query_lower
        )

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

        comparative_score = 0.0
        matched_comparatives: list[str] = []
        for keyword in comparative_keywords:
            if keyword in query_lower:
                comparative_score += 0.25
                matched_comparatives.append(keyword)

        comparative_score = min(comparative_score, 0.30)

        if comparative_score > 0.05:
            factors.append(
                ComplexityFactor(
                    name="comparative_query",
                    contribution=comparative_score,
                    description=(
                        f"Comparative keywords: {', '.join(matched_comparatives)}"
                    ),
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

        exploration_score = 0.0
        matched_explorations: list[str] = []
        for keyword in exploration_keywords:
            if keyword in query_lower:
                exploration_score += 0.20
                matched_explorations.append(keyword)

        exploration_score = min(exploration_score, 0.30)

        if exploration_score > 0.05:
            factors.append(
                ComplexityFactor(
                    name="exploration_query",
                    contribution=exploration_score,
                    description=(
                        f"Exploration keywords: {', '.join(matched_explorations)}"
                    ),
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

        decision_score = 0.0
        matched_decisions: list[str] = []
        for keyword in decision_keywords:
            if keyword in query_lower:
                decision_score += 0.15
                matched_decisions.append(keyword)

        decision_score = min(decision_score, 0.25)

        if decision_score > 0.05:
            factors.append(
                ComplexityFactor(
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

        creative_score = 0.0
        matched_creatives: list[str] = []
        for keyword in creative_keywords:
            if keyword in query_lower:
                creative_score += 0.10
                matched_creatives.append(keyword)

        creative_score = min(creative_score, 0.20)

        if creative_score > 0.05:
            factors.append(
                ComplexityFactor(
                    name="creative_problem_solving",
                    contribution=creative_score,
                    description=(
                        f"Creative keywords: {', '.join(matched_creatives)}"
                    ),
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

        sequential_score = 0.0
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

        math_score = 0.0
        for pattern in math_patterns:
            if re.search(pattern, query, re.IGNORECASE):
                math_score += 0.10

        math_score = min(math_score, 0.20)
        cot_score += math_score

        # Calculate total complexity score
        total_score = max(tot_score, cot_score * 0.7)  # ToT gets priority
        total_score = min(total_score, 1.0)

        # Determine requirements
        requires_tot = tot_score > 0.3 and tot_score >= cot_score * 0.8
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

        return ToTComplexityScore(
            score=total_score,
            factors=factors,
            requires_tot=requires_tot,
            requires_cot=requires_cot,
            estimated_timeout_multiplier=timeout_multiplier,
        )

