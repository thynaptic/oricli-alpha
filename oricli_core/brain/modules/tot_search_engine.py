from __future__ import annotations
"""
Tree-of-Thought Search Engine

Best-first search engine for Tree-of-Thought exploration.
Implements priority queue, pruning, and path reconstruction.
Ported from Swift ToTSearchEngine.swift
"""

import time
import uuid
from typing import Any
import logging

from oricli_core.brain.base_module import BaseBrainModule, ModuleMetadata
from oricli_core.brain.modules.tot_models import (
    ToTThoughtNode,
    ToTTreeState,
    ToTConfiguration,
    ToTSearchResult,
    SearchStatistics,
)
from oricli_core.brain.registry import ModuleRegistry
from oricli_core.exceptions import InvalidParameterError, ModuleOperationError

logger = logging.getLogger(__name__)


class ToTSearchEngine(BaseBrainModule):
    """
    Best-first search engine for Tree-of-Thought exploration.
    Implements priority queue, pruning, and path reconstruction.
    """

    def __init__(self) -> None:
        """Initialize the module"""
        super().__init__()
        self._thought_generator = None
        self._state_evaluator = None
        self._cognitive_generator = None
        self._safety_filter = None
        self._verification_loop = None

    @property
    def metadata(self) -> ModuleMetadata:
        return ModuleMetadata(
            name="tot_search_engine",
            version="1.0.0",
            description="Best-first search engine for Tree-of-Thought exploration",
            operations=[
                "search",
            ],
            dependencies=[],
            enabled=True,
            model_required=False,
        )

    def initialize(self) -> bool:
        """Initialize dependent modules"""
        try:
            self._thought_generator = ModuleRegistry.get_module(
                "tot_thought_generator"
            )
            self._state_evaluator = ModuleRegistry.get_module("tot_state_evaluator")
            self._cognitive_generator = ModuleRegistry.get_module(
                "cognitive_generator"
            )
            # Optional dependencies
            try:
                self._safety_filter = ModuleRegistry.get_module("safety_framework")
            except Exception as e:
                logger.debug(
                    "Optional dependency 'safety_framework' unavailable for tot_search_engine",
                    exc_info=True,
                    extra={"module_name": "tot_search_engine", "error_type": type(e).__name__},
                )
            try:
                self._verification_loop = ModuleRegistry.get_module("verification")
            except Exception as e:
                logger.debug(
                    "Optional dependency 'verification' unavailable for tot_search_engine",
                    exc_info=True,
                    extra={"module_name": "tot_search_engine", "error_type": type(e).__name__},
                )

            return True
        except Exception as e:
            logger.debug(
                "Failed to initialize tot_search_engine dependencies",
                exc_info=True,
                extra={"module_name": "tot_search_engine", "error_type": type(e).__name__},
            )
            return False

    def execute(self, operation: str, params: dict[str, Any]) -> dict[str, Any]:
        """
        Execute search operations.

        Supported operations:
        - search: Execute best-first search on the Tree-of-Thought
        """
        if operation == "search":
            return self._search(params)
        else:
            raise InvalidParameterError(
                parameter="operation",
                value=operation,
                reason="Unknown operation for tot_search_engine",
            )

    def _search(self, params: dict[str, Any]) -> dict[str, Any]:
        """
        Execute best-first search on the Tree-of-Thought.

        Args:
            params: Dictionary with:
                - query (str): The query to search
                - context (str, optional): Additional context
                - configuration (dict, optional): ToTConfiguration as dict
                - session_id (str, optional): Session identifier

        Returns:
            ToTSearchResult as dictionary
        """
        if not self._thought_generator or not self._state_evaluator:
            self.initialize()
            if not self._thought_generator or not self._state_evaluator:
                raise ModuleOperationError(
                    module_name="tot_search_engine",
                    operation="search",
                    reason="Required modules not available (tot_thought_generator, tot_state_evaluator)",
                )

        query = params.get("query", "")
        if not isinstance(query, str) or not query.strip():
            raise InvalidParameterError(
                parameter="query",
                value=str(query),
                reason="query parameter is required and must be a non-empty string",
            )

        context = params.get("context")
        config_dict = params.get("configuration", {})
        session_id = params.get("session_id", str(uuid.uuid4()))

        config = (
            ToTConfiguration.from_dict(config_dict)
            if config_dict
            else ToTConfiguration.default()
        )

        start_time = time.time()

        # Initialize root node
        root_node = ToTThoughtNode(
            depth=0,
            thought=query,
            state={"type": "root", "query": query},
            metadata={"type": "root"},
        )

        # Initialize tree state
        tree_state = ToTTreeState(root_node=root_node, max_depth=config.max_depth)

        # Priority queue: nodes sorted by evaluation score (highest first)
        priority_queue: list[tuple[ToTThoughtNode, float]] = [(root_node, 1.0)]

        explored_count = 0
        pruned_count = 0
        nodes_per_depth: dict[int, int] = {0: 1}
        all_evaluation_scores: list[float] = []
        max_depth_reached = 0
        termination_reason = "queue_exhausted"

        # Search loop
        while priority_queue:
            # Check timeout
            elapsed = time.time() - start_time
            if elapsed > config.max_search_time:
                termination_reason = "timeout"
                break

            # Pop highest-scoring node
            priority_queue.sort(key=lambda x: x[1], reverse=True)
            prioritized = priority_queue.pop(0)
            current_node = prioritized[0]
            current_score = prioritized[1]
            explored_count += 1

            # Track max depth
            max_depth_reached = max(max_depth_reached, current_node.depth)

            # Check if we've reached max depth
            if current_node.depth >= config.max_depth:
                termination_reason = "max_depth"
                # Don't expand further, but check if this is a perfect solution
                if current_score >= 0.9 and config.enable_early_termination:
                    termination_reason = "perfect_solution"
                    # Add this node back to queue so it's considered in final selection
                    priority_queue.insert(0, (current_node, current_score))
                    break
                continue

            # Check for perfect solution (early termination)
            if current_score >= 0.9 and config.enable_early_termination:
                termination_reason = "perfect_solution"
                # Add this node back to queue so it's considered in final selection
                priority_queue.insert(0, (current_node, current_score))
                break

            # Generate child thoughts
            thought_count = config.adaptive_thought_count(current_node.depth)

            try:
                # Generate child thoughts
                generator_result = self._thought_generator.execute(
                    "generate_thoughts",
                    {
                        "current_state": current_node.to_dict(),
                        "query": query,
                        "context": context,
                        "count": thought_count,
                        "configuration": config.to_dict(),
                    },
                )

                child_thoughts_dicts = generator_result.get("thoughts", [])
                if not child_thoughts_dicts:
                    continue

                child_thoughts = [
                    ToTThoughtNode.from_dict(c) for c in child_thoughts_dicts
                ]

                # Verify each child thought using verification loop (if available)
                valid_child_thoughts: list[ToTThoughtNode] = []
                previous_nodes = [
                    node
                    for node in tree_state.all_nodes.values()
                    if node.depth < current_node.depth
                ]
                previous_nodes.sort(key=lambda x: x.depth)

                for child in child_thoughts:
                    try:
                        # Step 1: Safety filtering (if available)
                        if self._safety_filter:
                            try:
                                safety_result = self._safety_filter.execute(
                                    "filter_tot_node",
                                    {
                                        "node": child.to_dict(),
                                        "previous_nodes": [
                                            n.to_dict() for n in previous_nodes
                                        ],
                                        "session_id": session_id,
                                    },
                                )
                                if not safety_result.get("is_safe", True):
                                    pruned_count += 1
                                    continue
                            except Exception:
                                # Fail open if safety filter errors
                                pass

                        # Step 2: Use verification loop for adaptive verification (if available)
                        if self._verification_loop:
                            try:
                                verification_result = self._verification_loop.execute(
                                    "verify_tot_node",
                                    {
                                        "node": child.to_dict(),
                                        "previous_nodes": [
                                            n.to_dict() for n in previous_nodes
                                        ],
                                        "complexity": 0.6,
                                        "confidence": child.evaluation_score or 0.5,
                                    },
                                )
                                if not verification_result.get("is_valid", True):
                                    pruned_count += 1
                                    continue

                                # Update node with verification confidence if available
                                verified_confidence = verification_result.get(
                                    "confidence"
                                )
                                if verified_confidence is not None:
                                    child = child.with_evaluation_score(
                                        verified_confidence
                                    )
                            except Exception:
                                # Fail open if verification errors
                                pass

                        valid_child_thoughts.append(child)

                    except Exception as e:
                        logger.debug(
                            "Error verifying ToT node; failing open",
                            exc_info=True,
                            extra={"module_name": "tot_search_engine", "error_type": type(e).__name__},
                        )
                        # On error, include the child (fail open)
                        valid_child_thoughts.append(child)

                if not valid_child_thoughts:
                    continue

                # Evaluate all valid child thoughts
                evaluator_result = self._state_evaluator.execute(
                    "evaluate_thoughts",
                    {
                        "thoughts": [c.to_dict() for c in valid_child_thoughts],
                        "query": query,
                        "configuration": config.to_dict(),
                    },
                )

                evaluation_scores = evaluator_result.get("scores", {})

                # Update nodes with scores and add to tree
                evaluated_children: list[ToTThoughtNode] = []
                for child in valid_child_thoughts:
                    score = evaluation_scores.get(child.id, 0.5)
                    updated_child = child.with_evaluation_score(score)

                    tree_state.add_node(updated_child)
                    evaluated_children.append(updated_child)
                    all_evaluation_scores.append(updated_child.evaluation_score or 0.5)

                # Apply pruning
                pruned_children = self._apply_pruning(
                    children=evaluated_children,
                    depth=current_node.depth + 1,
                    configuration=config,
                )

                pruned_count += len(evaluated_children) - len(pruned_children)

                # Add pruned children to priority queue
                for child in pruned_children:
                    score = child.evaluation_score or 0.5
                    priority_queue.append((child, score))

                # Update statistics
                current_depth = current_node.depth + 1
                nodes_per_depth[current_depth] = (
                    nodes_per_depth.get(current_depth, 0) + len(pruned_children)
                )

            except Exception as e:
                logger.debug(
                    "Failed to generate or evaluate children; continuing search",
                    exc_info=True,
                    extra={"module_name": "tot_search_engine", "error_type": type(e).__name__},
                )
                # Continue search with remaining nodes
                continue

        # Reconstruct best path
        best_path = self._reconstruct_best_path(
            tree_state=tree_state,
            termination_reason=termination_reason,
            query=query,
        )

        if not best_path:
            termination_reason = "no_valid_path"
            raise ModuleOperationError(
                module_name="tot_search_engine",
                operation="search",
                reason="No valid path found in Tree-of-Thought search",
            )

        # Generate final answer from best path
        final_answer = self._synthesize_final_answer(path=best_path, query=query)

        total_latency = time.time() - start_time
        avg_evaluation_score = (
            sum(all_evaluation_scores) / len(all_evaluation_scores)
            if all_evaluation_scores
            else 0.5
        )

        statistics = SearchStatistics(
            nodes_per_depth=nodes_per_depth,
            average_evaluation_score=avg_evaluation_score,
            max_depth_reached=max_depth_reached,
            search_strategy=config.search_strategy,
            termination_reason=termination_reason,
        )

        best_score = best_path[-1].evaluation_score if best_path else 0.5

        result = ToTSearchResult(
            best_path=best_path,
            final_answer=final_answer,
            evaluation_score=best_score or 0.5,
            explored_nodes=explored_count,
            pruned_nodes=pruned_count,
            search_statistics=statistics,
            model_used="cognitive_generator",
            total_latency=total_latency,
        )

        return result.to_dict()

    # MARK: - Pruning

    def _apply_pruning(
        self,
        children: list[ToTThoughtNode],
        depth: int,
        configuration: ToTConfiguration,
    ) -> list[ToTThoughtNode]:
        """Apply pruning strategy to children"""
        # Filter by minimum score threshold
        filtered = [
            c
            for c in children
            if (c.evaluation_score or 0.0) >= configuration.min_score_threshold
        ]

        # Sort by score (descending)
        filtered.sort(
            key=lambda x: x.evaluation_score or 0.0, reverse=True
        )

        # Apply top-K pruning
        top_k = configuration.top_k(depth)
        pruned = filtered[:top_k]

        return pruned

    # MARK: - Path Reconstruction

    def _reconstruct_best_path(
        self,
        tree_state: ToTTreeState,
        termination_reason: str,
        query: str,
    ) -> list[ToTThoughtNode]:
        """Reconstruct best path from tree state"""
        # Find all leaf nodes (nodes with no children or highest depth)
        leaves = tree_state.get_leaves()

        if not leaves:
            # No leaves found, return path to deepest node
            all_nodes = list(tree_state.all_nodes.values())
            if not all_nodes:
                return [tree_state.root_node]

            deepest_node = max(all_nodes, key=lambda n: n.depth)
            return tree_state.get_path_to_root(deepest_node.id)

        # Find best leaf (highest evaluation score)
        best_leaf = max(
            leaves,
            key=lambda n: n.evaluation_score or 0.0,
        )

        # Reconstruct path from root to best leaf
        path = tree_state.get_path_to_root(best_leaf.id)

        return path

    # MARK: - Final Answer Synthesis

    def _synthesize_final_answer(
        self, path: list[ToTThoughtNode], query: str
    ) -> str:
        """Synthesize final answer from best path"""
        if not path:
            return "Unable to synthesize answer from empty path."

        if not self._cognitive_generator:
            self.initialize()
            if not self._cognitive_generator:
                # Fallback: use last node's thought
                return path[-1].thought if path else ""

        # Build synthesis prompt
        path_description = "\n\n".join(
            [f"Step {index + 1}: {node.thought}" for index, node in enumerate(path)]
        )

        synthesis_prompt = f"""Based on the following reasoning path through the Tree-of-Thought exploration, provide a clear, concise, and complete final answer to the original question.

Original Question: {query}

Reasoning Path:
{path_description}

Final Answer:
"""

        try:
            response_result = self._cognitive_generator.execute(
                "generate_response",
                {
                    "input": synthesis_prompt,
                    "context": "",
                    "persona": "oricli",
                },
            )

            return response_result.get("text", "").strip()
        except Exception as e:
            logger.debug(
                "Error synthesizing final answer; using fallback",
                exc_info=True,
                extra={"module_name": "tot_search_engine", "error_type": type(e).__name__},
            )
            # Fallback: use last node's thought
            return path[-1].thought if path else ""

