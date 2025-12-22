"""
Monte-Carlo Thought Search Rollout Service

Adaptive rollout service for Monte-Carlo Thought Search.
Implements heuristic (fast) and LLM (accurate) rollouts with caching.
Ported from Swift MCTSRolloutService.swift
"""

import time
from typing import Any
from datetime import datetime, timedelta
import concurrent.futures
import logging

from mavaia_core.brain.base_module import BaseBrainModule, ModuleMetadata
from mavaia_core.brain.registry import ModuleRegistry
from mavaia_core.exceptions import InvalidParameterError, ModuleOperationError

logger = logging.getLogger(__name__)

# Lazy imports to avoid timeout during module discovery
MCTSNode = None
MCTSConfiguration = None
ToTThoughtNode = None
ToTConfiguration = None
_MCTS_MODELS_IMPORT_FAILURE_LOGGED = False

def _lazy_import_mcts_models():
    """Lazy import MCTS models only when needed"""
    global MCTSNode, MCTSConfiguration, ToTThoughtNode, ToTConfiguration
    global _MCTS_MODELS_IMPORT_FAILURE_LOGGED
    if MCTSNode is None:
        try:
            from mavaia_core.brain.modules.mcts_models import (
                MCTSNode as MN,
                MCTSConfiguration as MC,
            )
            from mavaia_core.brain.modules.tot_models import (
                ToTThoughtNode as TTN,
                ToTConfiguration as TC,
            )
            MCTSNode = MN
            MCTSConfiguration = MC
            ToTThoughtNode = TTN
            ToTConfiguration = TC
        except ImportError as e:
            if not _MCTS_MODELS_IMPORT_FAILURE_LOGGED:
                _MCTS_MODELS_IMPORT_FAILURE_LOGGED = True
                logger.debug(
                    "Failed to import MCTS/ToT model types for mcts_rollout_service",
                    exc_info=True,
                    extra={"module_name": "mcts_rollout_service", "error_type": type(e).__name__},
                )


class MCTSRolloutService(BaseBrainModule):
    """
    Adaptive rollout service for Monte-Carlo Thought Search.
    Implements heuristic (fast) and LLM (accurate) rollouts with caching.
    """

    def __init__(self) -> None:
        """Initialize the module"""
        super().__init__()
        self._state_evaluator = None
        self._thought_generator = None
        # Cache for rollout values (node ID -> (value, timestamp))
        self._rollout_cache: dict[str, tuple[float, datetime]] = {}
        self._cache_timeout = timedelta(seconds=300)  # 5 minutes

    @property
    def metadata(self) -> ModuleMetadata:
        return ModuleMetadata(
            name="mcts_rollout_service",
            version="1.0.0",
            description="Adaptive rollout service for Monte-Carlo Thought Search",
            operations=[
                "perform_adaptive_rollout",
                "perform_parallel_rollouts",
                "clear_expired_cache",
                "clear_cache",
                "get_cache_stats",
            ],
            dependencies=[],
            enabled=True,
            model_required=False,
        )

    def initialize(self) -> bool:
        """Initialize dependent modules"""
        # Don't initialize modules here - they're heavy, will initialize lazily
        return True
    
    def _ensure_modules_loaded(self):
        """Lazy load dependent modules only when needed"""
        if self._state_evaluator is None or self._thought_generator is None:
            try:
                if self._state_evaluator is None:
                    self._state_evaluator = ModuleRegistry.get_module("tot_state_evaluator", auto_discover=True, wait_timeout=1.0)
                if self._thought_generator is None:
                    self._thought_generator = ModuleRegistry.get_module("tot_thought_generator", auto_discover=True, wait_timeout=1.0)
            except Exception as e:
                logger.debug(
                    "Failed to load one or more optional dependency modules for mcts_rollout_service",
                    exc_info=True,
                    extra={"module_name": "mcts_rollout_service", "error_type": type(e).__name__},
                )

    def execute(self, operation: str, params: dict[str, Any]) -> dict[str, Any]:
        """
        Execute rollout operations.

        Supported operations:
        - perform_adaptive_rollout: Perform adaptive rollout
        - perform_parallel_rollouts: Perform parallel rollouts
        - clear_expired_cache: Clear expired cache entries
        - clear_cache: Clear all cache
        - get_cache_stats: Get cache statistics
        """
        _lazy_import_mcts_models()
        self._ensure_modules_loaded()
        if operation == "perform_adaptive_rollout":
            return self._perform_adaptive_rollout(params)
        elif operation == "perform_parallel_rollouts":
            return self._perform_parallel_rollouts(params)
        elif operation == "clear_expired_cache":
            return self._clear_expired_cache(params)
        elif operation == "clear_cache":
            return self._clear_cache(params)
        elif operation == "get_cache_stats":
            return self._get_cache_stats(params)
        else:
            raise InvalidParameterError(
                parameter="operation",
                value=operation,
                reason="Unknown operation for mcts_rollout_service",
            )

    def _perform_adaptive_rollout(self, params: dict[str, Any]) -> dict[str, Any]:
        """
        Perform adaptive rollout: start with heuristic, use LLM if promising.

        Args:
            params: Dictionary with:
                - node (dict): MCTSNode as dict
                - query (str): The query
                - context (str, optional): Additional context
                - configuration (dict): MCTSConfiguration as dict

        Returns:
            Dictionary with rollout value
        """
        if not self._state_evaluator:
            self.initialize()
            if not self._state_evaluator:
                raise ModuleOperationError(
                    module_name="mcts_rollout_service",
                    operation="perform_adaptive_rollout",
                    reason="Required module not available: tot_state_evaluator",
                )

        node_dict = params.get("node")
        if not isinstance(node_dict, dict) or not node_dict:
            raise InvalidParameterError(
                parameter="node",
                value=str(type(node_dict).__name__),
                reason="node parameter is required and must be a non-empty dict",
            )

        node = MCTSNode.from_dict(node_dict)
        query = params.get("query", "")
        if not isinstance(query, str) or not query.strip():
            raise InvalidParameterError(
                parameter="query",
                value=str(query),
                reason="query parameter is required and must be a non-empty string",
            )
        context = params.get("context")
        config_dict = params.get("configuration", {})

        config = (
            MCTSConfiguration.from_dict(config_dict)
            if config_dict
            else MCTSConfiguration.default()
        )

        # Check cache first
        if config.enable_value_caching and node.id in self._rollout_cache:
            cached_value, cached_timestamp = self._rollout_cache[node.id]
            if datetime.now() - cached_timestamp < self._cache_timeout:
                return {"value": cached_value}

        # Step 1: Quick heuristic evaluation
        heuristic_value = self._perform_heuristic_rollout(node, query, config)

        # Step 2: Decide if we need LLM rollout
        should_use_llm = config.enable_adaptive_rollout and (
            heuristic_value >= config.heuristic_rollout_threshold
            or node.value_estimate >= 0.7  # Node already promising
            or node.visit_count == 0  # First visit, get accurate estimate
        )

        if should_use_llm:
            final_value = self._perform_llm_rollout(node, query, context, config)
        else:
            final_value = heuristic_value

        # Cache the result
        if config.enable_value_caching:
            self._rollout_cache[node.id] = (final_value, datetime.now())

        return {"value": final_value}

    def _perform_parallel_rollouts(self, params: dict[str, Any]) -> dict[str, Any]:
        """
        Perform parallel rollouts for better value estimates.

        Args:
            params: Dictionary with:
                - node (dict): MCTSNode as dict
                - query (str): The query
                - context (str, optional): Additional context
                - count (int): Number of parallel rollouts
                - configuration (dict): MCTSConfiguration as dict

        Returns:
            Dictionary with list of rollout values
        """
        node_dict = params.get("node")
        if not isinstance(node_dict, dict) or not node_dict:
            raise InvalidParameterError(
                parameter="node",
                value=str(type(node_dict).__name__),
                reason="node parameter is required and must be a non-empty dict",
            )

        node = MCTSNode.from_dict(node_dict)
        query = params.get("query", "")
        if not isinstance(query, str) or not query.strip():
            raise InvalidParameterError(
                parameter="query",
                value=str(query),
                reason="query parameter is required and must be a non-empty string",
            )
        context = params.get("context")
        count = params.get("count", 1)
        try:
            count_int = int(count)
        except (TypeError, ValueError):
            raise InvalidParameterError(
                parameter="count",
                value=str(count),
                reason="count must be an integer",
            )
        if count_int < 1:
            raise InvalidParameterError(
                parameter="count",
                value=str(count_int),
                reason="count must be >= 1",
            )
        config_dict = params.get("configuration", {})

        config = (
            MCTSConfiguration.from_dict(config_dict)
            if config_dict
            else MCTSConfiguration.default()
        )

        rollout_values: list[float] = []

        # Perform rollouts in parallel using thread pool
        with concurrent.futures.ThreadPoolExecutor(
            max_workers=min(count_int, config.parallel_rollouts)
        ) as executor:
            future_to_rollout = {
                executor.submit(
                    self._perform_adaptive_rollout,
                    {
                        "node": node.to_dict(),
                        "query": query,
                        "context": context,
                        "configuration": config.to_dict(),
                    },
                ): i
                for i in range(count_int)
            }

            for future in concurrent.futures.as_completed(future_to_rollout):
                try:
                    result = future.result()
                    rollout_values.append(result.get("value", 0.5))
                except Exception as e:
                    logger.debug(
                        "Error in parallel rollout; using default value",
                        exc_info=True,
                        extra={"module_name": "mcts_rollout_service", "error_type": type(e).__name__},
                    )
                    rollout_values.append(0.5)  # Default value on error

        return {"values": rollout_values}

    def _perform_heuristic_rollout(
        self, node: MCTSNode, query: str, configuration: MCTSConfiguration
    ) -> float:
        """Perform fast heuristic-based rollout"""
        thought = node.tot_node
        score: float = 0.5  # Start with neutral

        thought_text = thought.thought
        thought_length = len(thought_text)
        lower_thought = thought_text.lower()
        query_lower = query.lower()

        # Factor 1: Thought length (not too short, not too long)
        if 100 < thought_length < 1500:
            score += 0.15
        elif thought_length < 30:
            score -= 0.2  # Too short
        elif thought_length > 3000:
            score -= 0.1  # Potentially too verbose

        # Factor 2: Step indicators (shows structured reasoning)
        step_indicators = [
            "step",
            "first",
            "then",
            "next",
            "finally",
            "conclusion",
            "therefore",
            "because",
            "thus",
            "hence",
        ]
        step_count = sum(lower_thought.count(indicator) for indicator in step_indicators)

        if step_count >= 3:
            score += 0.15
        elif step_count >= 1:
            score += 0.1

        # Factor 3: Logical connectors (indicates coherent reasoning)
        logical_connectors = [
            "because",
            "therefore",
            "thus",
            "hence",
            "consequently",
            "as a result",
            "if",
            "then",
            "since",
        ]
        connector_count = sum(
            lower_thought.count(connector) for connector in logical_connectors
        )

        if connector_count >= 2:
            score += 0.1
        elif connector_count >= 1:
            score += 0.05

        # Factor 4: Query relevance
        query_words = set(
            word
            for word in query_lower.split()
            if len(word) > 3
        )
        thought_words = set(
            word
            for word in lower_thought.split()
            if len(word) > 3
        )
        relevant_words = query_words.intersection(thought_words)

        if query_words:
            relevance_ratio = len(relevant_words) / len(query_words)
            score += relevance_ratio * 0.2

        # Factor 5: Depth appropriateness
        if thought.depth >= 3 and thought_length > 200:
            score += 0.1
        elif thought.depth <= 1 and thought_length > 80:
            score += 0.1

        # Factor 6: Existing evaluation score (if available)
        if thought.evaluation_score is not None:
            score = (score * 0.6) + (thought.evaluation_score * 0.4)

        # Cap score between 0.0 and 1.0
        return max(0.0, min(1.0, score))

    def _perform_llm_rollout(
        self,
        node: MCTSNode,
        query: str,
        context: str | None,
        configuration: MCTSConfiguration,
    ) -> float:
        """Perform accurate LLM-based rollout with deeper reasoning"""
        if not self._thought_generator or not self._state_evaluator:
            self.initialize()
            if not self._thought_generator or not self._state_evaluator:
                # Fallback to heuristic
                return self._perform_heuristic_rollout(node, query, configuration)

        # Generate shallow thought extensions (1-2 steps) for rollout
        rollout_thoughts = self._generate_rollout_thoughts(
            node, query, context, min(configuration.rollout_depth, 2), configuration
        )

        # Evaluate the best rollout thought using LLM
        best_value: float = 0.5

        if rollout_thoughts:
            best_thought = rollout_thoughts[0]

            # Use ToTStateEvaluator for comprehensive evaluation
            eval_result = self._state_evaluator.execute(
                "evaluate_thought",
                {
                    "thought": best_thought.to_dict(),
                    "query": query,
                    "all_thoughts": [t.to_dict() for t in rollout_thoughts],
                    "configuration": self._mcts_to_tot_config(configuration).to_dict(),
                },
            )

            best_value = eval_result.get("score", 0.5)
        else:
            # Fallback: evaluate the current node directly
            eval_result = self._state_evaluator.execute(
                "evaluate_thought",
                {
                    "thought": node.tot_node.to_dict(),
                    "query": query,
                    "all_thoughts": [node.tot_node.to_dict()],
                    "configuration": self._mcts_to_tot_config(configuration).to_dict(),
                },
            )

            best_value = eval_result.get("score", 0.5)

        return best_value

    def _generate_rollout_thoughts(
        self,
        node: MCTSNode,
        query: str,
        context: str | None,
        depth: int,
        configuration: MCTSConfiguration,
    ) -> list[ToTThoughtNode]:
        """Generate shallow thought extensions for rollout"""
        if depth <= 0:
            return []

        thoughts: list[ToTThoughtNode] = []
        current_nodes = [node.tot_node]

        for current_depth in range(depth):
            next_nodes: list[ToTThoughtNode] = []

            for currentNode in current_nodes:
                try:
                    # Generate 1-2 thoughts per node for rollout (fast)
                    generator_result = self._thought_generator.execute(
                        "generate_thoughts",
                        {
                            "current_state": currentNode.to_dict(),
                            "query": query,
                            "context": context,
                            "count": min(2, configuration.base_thoughts_per_step),
                            "configuration": self._mcts_to_tot_config(
                                configuration
                            ).to_dict(),
                        },
                    )

                    generated_thoughts_dicts = generator_result.get("thoughts", [])
                    generated_thoughts = [
                        ToTThoughtNode.from_dict(t)
                        for t in generated_thoughts_dicts
                    ]
                    next_nodes.extend(generated_thoughts)

                except Exception as e:
                    logger.debug(
                        "Failed to generate rollout thoughts; continuing",
                        exc_info=True,
                        extra={"module_name": "mcts_rollout_service", "error_type": type(e).__name__},
                    )
                    # Continue with other nodes
                    continue

            if not next_nodes:
                break  # No more thoughts generated

            thoughts.extend(next_nodes)
            current_nodes = next_nodes

        # Sort by depth and return (deeper thoughts first)
        thoughts.sort(key=lambda x: x.depth, reverse=True)
        return thoughts

    def _mcts_to_tot_config(self, mcts_config: MCTSConfiguration) -> "ToTConfiguration":
        """Convert MCTSConfiguration to ToTConfiguration for compatibility"""
        if ToTConfiguration is None:
            raise ModuleOperationError(
                module_name="mcts_rollout_service",
                operation="mcts_to_tot_config",
                reason="ToTConfiguration type is not available (import failed)",
            )

        return ToTConfiguration(
            max_depth=mcts_config.max_depth,
            base_thoughts_per_step=mcts_config.base_thoughts_per_step,
            pruning_top_k=mcts_config.pruning_top_k,
            min_score_threshold=mcts_config.min_score_threshold,
            evaluation_weights=mcts_config.evaluation_weights,
            search_strategy="best_first",
            max_search_time=mcts_config.max_search_time,
            enable_early_termination=mcts_config.enable_early_termination,
        )

    def _clear_expired_cache(self, params: dict[str, Any]) -> dict[str, Any]:
        """Clear expired cache entries"""
        now = datetime.now()
        initial_count = len(self._rollout_cache)
        self._rollout_cache = {
            node_id: (value, timestamp)
            for node_id, (value, timestamp) in self._rollout_cache.items()
            if now - timestamp < self._cache_timeout
        }
        removed_count = initial_count - len(self._rollout_cache)

        return {"removed_count": removed_count}

    def _clear_cache(self, params: dict[str, Any]) -> dict[str, Any]:
        """Clear all cache"""
        count = len(self._rollout_cache)
        self._rollout_cache.clear()
        return {"cleared_count": count}

    def _get_cache_stats(self, params: dict[str, Any]) -> dict[str, Any]:
        """Get cache statistics"""
        # Note: hit rate tracking would require additional state
        return {"size": len(self._rollout_cache), "hit_rate": 0.0}

