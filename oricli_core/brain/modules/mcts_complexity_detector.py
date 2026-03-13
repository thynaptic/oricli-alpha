from __future__ import annotations
"""
Monte-Carlo Thought Search Complexity Detector

Automatic complexity detection for Monte-Carlo Thought Search (MCTS) activation.
Analyzes queries for MCTS suitability: uncertainty, exploration/exploitation balance,
sequential decision-making, and multi-path reasoning.
Ported from Swift MCTSComplexityDetector.swift
"""

from typing import Any

from oricli_core.brain.base_module import BaseBrainModule, ModuleMetadata
from oricli_core.brain.modules.mcts_models import MCTSComplexityScore, ComplexityFactor
from oricli_core.exceptions import InvalidParameterError


class MCTSComplexityDetector(BaseBrainModule):
    """
    Automatic complexity detection for Monte-Carlo Thought Search (MCTS) activation.
    Analyzes queries for MCTS suitability.
    """

    def __init__(self) -> None:
        """Initialize the module"""
        super().__init__()

    @property
    def metadata(self) -> ModuleMetadata:
        return ModuleMetadata(
            name="mcts_complexity_detector",
            version="1.0.0",
            description="Automatic complexity detection for MCTS activation",
            operations=[
                "analyze_mcts_complexity",
                "should_activate_mcts",
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
        - analyze_mcts_complexity: Full MCTS complexity analysis
        - should_activate_mcts: Quick check if MCTS should be activated
        """
        if operation == "analyze_mcts_complexity":
            return self._analyze_mcts_complexity(params)
        elif operation == "should_activate_mcts":
            return self._should_activate_mcts(params)
        else:
            raise InvalidParameterError(
                parameter="operation",
                value=operation,
                reason="Unknown operation for mcts_complexity_detector",
            )

    def _analyze_mcts_complexity(self, params: dict[str, Any]) -> dict[str, Any]:
        """
        Analyze query complexity and determine if MCTS should be activated.

        Args:
            params: Dictionary with:
                - query (str): The query to analyze
                - context (str, optional): Additional context

        Returns:
            MCTSComplexityScore as dictionary
        """
        query = params.get("query", "")
        if not isinstance(query, str) or not query.strip():
            raise InvalidParameterError(
                parameter="query",
                value=str(query),
                reason="query parameter is required and must be a non-empty string",
            )

        context = params.get("context")

        factors: list[ComplexityFactor] = []
        total_score: float = 0.0
        exploration_benefit: float = 0.0

        query_lower = query.lower()
        full_text = f"{query}\n{context}" if context else query
        full_text_lower = full_text.lower()

        # Factor 1: Uncertainty and Probabilistic Reasoning
        uncertainty_keywords: list[tuple[str, float]] = [
            ("uncertain", 0.25),
            ("uncertainty", 0.25),
            ("probability", 0.20),
            ("likely", 0.15),
            ("possibly", 0.15),
            ("maybe", 0.10),
            ("might", 0.10),
            ("could", 0.10),
            ("estimate", 0.15),
            ("approximate", 0.15),
            ("risk", 0.20),
            ("chance", 0.15),
            ("odds", 0.15),
        ]

        uncertainty_score: float = 0.0
        matched_uncertainties: list[str] = []
        for keyword, weight in uncertainty_keywords:
            if keyword in query_lower:
                uncertainty_score += weight
                matched_uncertainties.append(keyword)

        uncertainty_score = min(uncertainty_score, 0.30)  # Cap at 30%

        if uncertainty_score > 0.05:
            factors.append(
                ComplexityFactor(
                    name="uncertainty_reasoning",
                    contribution=uncertainty_score,
                    description=f"Uncertainty keywords: {', '.join(matched_uncertainties)}",
                )
            )
            total_score += uncertainty_score
            exploration_benefit += uncertainty_score * 0.8  # High exploration benefit

        # Factor 2: Sequential Decision-Making
        sequential_decision_keywords = [
            "decide step by step",
            "sequential decisions",
            "multi-step decision",
            "choose then",
            "first decide",
            "then choose",
            "decision tree",
            "decision path",
            "choose path",
            "select then",
            "pick then",
            "strategy step",
            "plan step",
            "multi-stage",
            "iterative decision",
        ]

        sequential_decision_score: float = 0.0
        matched_sequential: list[str] = []
        for keyword in sequential_decision_keywords:
            if keyword in query_lower:
                sequential_decision_score += 0.20
                matched_sequential.append(keyword)

        sequential_decision_score = min(sequential_decision_score, 0.30)

        if sequential_decision_score > 0.05:
            factors.append(
                ComplexityFactor(
                    name="sequential_decision_making",
                    contribution=sequential_decision_score,
                    description=f"Sequential decision keywords: {', '.join(matched_sequential)}",
                )
            )
            total_score += sequential_decision_score
            exploration_benefit += sequential_decision_score * 0.7

        # Factor 3: Exploration/Exploitation Balance
        exploration_keywords = [
            "explore options",
            "try different",
            "test multiple",
            "experiment with",
            "compare approaches",
            "evaluate alternatives",
            "weigh options",
            "balance",
            "trade-off",
            "tradeoff",
            "explore vs exploit",
            "exploration",
            "exploitation",
            "sampling",
            "search space",
        ]

        exploration_score: float = 0.0
        matched_explorations: list[str] = []
        for keyword in exploration_keywords:
            if keyword in query_lower:
                exploration_score += 0.20
                matched_explorations.append(keyword)

        exploration_score = min(exploration_score, 0.35)

        if exploration_score > 0.05:
            factors.append(
                ComplexityFactor(
                    name="exploration_exploitation",
                    contribution=exploration_score,
                    description=f"Exploration keywords: {', '.join(matched_explorations)}",
                )
            )
            total_score += exploration_score
            exploration_benefit += exploration_score * 0.9  # Very high exploration benefit

        # Factor 4: Game Theory / Competitive Scenarios
        game_theory_keywords = [
            "game theory",
            "optimal strategy",
            "best response",
            "nash equilibrium",
            "minimax",
            "adversarial",
            "opponent",
            "compete",
            "competing",
            "winning strategy",
            "optimal play",
            "move sequence",
            "game tree",
        ]

        game_theory_score: float = 0.0
        matched_game_theory: list[str] = []
        for keyword in game_theory_keywords:
            if keyword in query_lower:
                game_theory_score += 0.25
                matched_game_theory.append(keyword)

        game_theory_score = min(game_theory_score, 0.30)

        if game_theory_score > 0.05:
            factors.append(
                ComplexityFactor(
                    name="game_theory",
                    contribution=game_theory_score,
                    description=f"Game theory keywords: {', '.join(matched_game_theory)}",
                )
            )
            total_score += game_theory_score
            exploration_benefit += game_theory_score * 0.85

        # Factor 5: Multi-Path Reasoning with Unknown Outcomes
        multi_path_keywords = [
            "multiple paths",
            "different outcomes",
            "various scenarios",
            "possible futures",
            "what if",
            "scenario analysis",
            "path analysis",
            "branching",
            "fork",
            "diverging",
            "converging paths",
            "alternative futures",
            "possible results",
            "potential outcomes",
        ]

        multi_path_score: float = 0.0
        matched_multi_path: list[str] = []
        for keyword in multi_path_keywords:
            if keyword in query_lower:
                multi_path_score += 0.18
                matched_multi_path.append(keyword)

        multi_path_score = min(multi_path_score, 0.30)

        if multi_path_score > 0.05:
            factors.append(
                ComplexityFactor(
                    name="multi_path_reasoning",
                    contribution=multi_path_score,
                    description=f"Multi-path keywords: {', '.join(matched_multi_path)}",
                )
            )
            total_score += multi_path_score
            exploration_benefit += multi_path_score * 0.75

        # Factor 6: Optimization with Exploration
        optimization_keywords = [
            "optimize",
            "find best",
            "maximize",
            "minimize",
            "optimal solution",
            "best approach",
            "search for best",
            "optimization problem",
            "search space",
            "solution space",
            "global optimum",
            "local optimum",
            "hill climbing",
            "simulated annealing",
        ]

        optimization_score: float = 0.0
        matched_optimizations: list[str] = []
        for keyword in optimization_keywords:
            if keyword in query_lower:
                optimization_score += 0.15
                matched_optimizations.append(keyword)

        optimization_score = min(optimization_score, 0.25)

        if optimization_score > 0.05:
            factors.append(
                ComplexityFactor(
                    name="optimization",
                    contribution=optimization_score,
                    description=f"Optimization keywords: {', '.join(matched_optimizations)}",
                )
            )
            total_score += optimization_score
            exploration_benefit += optimization_score * 0.6

        # Factor 7: Reinforcement Learning / Trial and Error
        rl_keywords = [
            "learn from",
            "trial and error",
            "reinforcement",
            "reward",
            "penalty",
            "feedback loop",
            "iterative improvement",
            "learn by doing",
            "adaptive",
            "self-improving",
            "evolve",
        ]

        rl_score: float = 0.0
        matched_rl: list[str] = []
        for keyword in rl_keywords:
            if keyword in query_lower:
                rl_score += 0.20
                matched_rl.append(keyword)

        rl_score = min(rl_score, 0.25)

        if rl_score > 0.05:
            factors.append(
                ComplexityFactor(
                    name="reinforcement_learning",
                    contribution=rl_score,
                    description=f"RL keywords: {', '.join(matched_rl)}",
                )
            )
            total_score += rl_score
            exploration_benefit += rl_score * 0.8

        # Factor 8: Query Length and Complexity
        query_length = len(query)
        length_score = min(query_length / 800.0, 1.0) * 0.10

        if length_score > 0.05:
            factors.append(
                ComplexityFactor(
                    name="query_length",
                    contribution=length_score,
                    description=f"Query length: {query_length} characters",
                )
            )
            total_score += length_score

        # Factor 9: Question Count (multiple questions suggest exploration)
        question_count = query.count("?")
        question_score = (
            min((question_count - 1) * 0.08, 0.15) if question_count > 1 else 0.0
        )

        if question_score > 0.03:
            factors.append(
                ComplexityFactor(
                    name="multiple_questions",
                    contribution=question_score,
                    description=f"Contains {question_count} question(s)",
                )
            )
            total_score += question_score
            if question_count > 2:
                exploration_benefit += 0.1

        # Normalize scores
        total_score = min(total_score, 1.0)
        exploration_benefit = min(exploration_benefit, 1.0)

        # Determine if MCTS is required
        # MCTS is beneficial when there's significant exploration benefit or uncertainty
        requires_mcts = total_score >= 0.4 and exploration_benefit >= 0.3

        # Estimate rollout budget based on complexity
        if total_score < 0.4:
            estimated_rollout_budget = 50
        elif total_score < 0.6:
            estimated_rollout_budget = 100
        elif total_score < 0.8:
            estimated_rollout_budget = 150
        else:
            estimated_rollout_budget = 200

        result = MCTSComplexityScore(
            score=total_score,
            factors=factors,
            requires_mcts=requires_mcts,
            estimated_rollout_budget=estimated_rollout_budget,
            exploration_benefit=exploration_benefit,
        )

        return result.to_dict()

    def _should_activate_mcts(self, params: dict[str, Any]) -> dict[str, Any]:
        """Quick check if MCTS should be activated (without full analysis)"""
        query = params.get("query", "")
        if not isinstance(query, str) or not query.strip():
            raise InvalidParameterError(
                parameter="query",
                value=str(query),
                reason="query parameter is required and must be a non-empty string",
            )

        context = params.get("context")

        score_dict = self._analyze_mcts_complexity({"query": query, "context": context})
        score = MCTSComplexityScore.from_dict(score_dict)

        return {"should_use": score.requires_mcts}

