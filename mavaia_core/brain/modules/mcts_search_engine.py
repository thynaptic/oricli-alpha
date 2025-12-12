"""
Monte-Carlo Thought Search Engine

Monte-Carlo Tree Search engine implementing UCB1 selection, expansion,
simulation (rollout), and backpropagation phases.
Ported from Swift MCTSSearchEngine.swift
"""

import sys
import time
import math
import uuid
from pathlib import Path
from typing import Any

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent))

from mavaia_core.brain.base_module import BaseBrainModule, ModuleMetadata
from mcts_models import (
    MCTSNode,
    MCTSTreeState,
    MCTSConfiguration,
    MCTSSearchResult,
    SearchStatistics,
    RolloutStatistics,
)
from tot_models import ToTThoughtNode, ToTConfiguration


class MCTSSearchEngine(BaseBrainModule):
    """
    Monte-Carlo Tree Search engine implementing UCB1 selection, expansion,
    simulation (rollout), and backpropagation phases.
    """

    def __init__(self) -> None:
        """Initialize the module"""
        self._thought_generator = None
        self._rollout_service = None
        self._cognitive_generator = None
        self._safety_filter = None
        self._verification_loop = None

    @property
    def metadata(self) -> ModuleMetadata:
        return ModuleMetadata(
            name="mcts_search_engine",
            version="1.0.0",
            description="Monte-Carlo Tree Search engine implementing UCB1 algorithm",
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
            from module_registry import ModuleRegistry

            self._thought_generator = ModuleRegistry.get_module(
                "tot_thought_generator"
            )
            self._rollout_service = ModuleRegistry.get_module("mcts_rollout_service")
            self._cognitive_generator = ModuleRegistry.get_module(
                "cognitive_generator"
            )
            # Optional dependencies
            try:
                self._safety_filter = ModuleRegistry.get_module("safety_framework")
            except Exception:
                pass
            try:
                self._verification_loop = ModuleRegistry.get_module("verification")
            except Exception:
                pass

            return True
        except Exception:
            return False

    def execute(self, operation: str, params: dict[str, Any]) -> dict[str, Any]:
        """
        Execute search operations.

        Supported operations:
        - search: Execute Monte-Carlo Tree Search
        """
        if operation == "search":
            return self._search(params)
        else:
            raise ValueError(f"Unknown operation: {operation}")

    def _search(self, params: dict[str, Any]) -> dict[str, Any]:
        """
        Execute Monte-Carlo Tree Search.

        Args:
            params: Dictionary with:
                - query (str): The query to search
                - context (str, optional): Additional context
                - configuration (dict, optional): MCTSConfiguration as dict
                - session_id (str, optional): Session identifier

        Returns:
            MCTSSearchResult as dictionary
        """
        if not self._thought_generator or not self._rollout_service:
            self.initialize()
            if not self._thought_generator or not self._rollout_service:
                raise RuntimeError(
                    "Required modules not available (thought_generator, rollout_service)"
                )

        query = params.get("query", "")
        if not query:
            raise ValueError("query parameter is required")

        context = params.get("context")
        config_dict = params.get("configuration", {})
        session_id = params.get("session_id", str(uuid.uuid4()))

        config = (
            MCTSConfiguration.from_dict(config_dict)
            if config_dict
            else MCTSConfiguration.default()
        )

        start_time = time.time()

        # Initialize root node
        root_tot_node = ToTThoughtNode(
            depth=0,
            thought=query,
            state={"type": "root", "query": query},
            metadata={"type": "root"},
        )
        root_node = MCTSNode.from_tot_node(root_tot_node)

        # Initialize tree state
        tree_state = MCTSTreeState(root_node=root_node, max_depth=config.max_depth)

        # Statistics tracking
        total_rollouts = 0
        heuristic_rollouts = 0
        llm_rollouts = 0
        rollout_depths: list[int] = []
        rollout_values: list[float] = []
        nodes_per_depth: dict[int, int] = {0: 1}
        max_depth_reached = 0
        exploration_selections = 0
        exploitation_selections = 0
        termination_reason = "rollout_budget_exhausted"

        # MCTS main loop
        while total_rollouts < config.rollout_budget:
            # Check timeout
            elapsed = time.time() - start_time
            if elapsed > config.max_search_time:
                termination_reason = "timeout"
                break

            # Phase 1: Selection - Use UCB1 to select path from root to leaf
            selected_path, is_exploration = self._select_path(tree_state, config)

            if not selected_path:
                break

            selected_node = selected_path[-1]

            # Track selection type
            if is_exploration:
                exploration_selections += 1
            else:
                exploitation_selections += 1

            # Check if we've reached max depth
            if selected_node.tot_node.depth >= config.max_depth:
                termination_reason = "max_depth"

                # Still perform rollout for value estimation
                if total_rollouts < config.rollout_budget:
                    rollout_result = self._rollout_service.execute(
                        "perform_adaptive_rollout",
                        {
                            "node": selected_node.to_dict(),
                            "query": query,
                            "context": context,
                            "configuration": config.to_dict(),
                        },
                    )

                    rollout_value = rollout_result.get("value", 0.5)
                    rollout_values.append(rollout_value)
                    total_rollouts += 1

                    # Backpropagate
                    self._backpropagate(
                        selected_path, rollout_value, tree_state, config
                    )

                # Check for early termination
                if config.enable_early_termination and selected_node.value_estimate >= 0.9:
                    termination_reason = "perfect_solution"
                    break

                continue

            # Phase 2: Expansion - Add new child nodes if node has sufficient visits
            expanded_node = selected_node
            children_added = False

            if selected_node.visit_count >= config.min_visits_for_expansion:
                try:
                    children = self._expand_node(
                        selected_node, query, context, config, session_id
                    )

                    if children:
                        for child in children:
                            tree_state.add_node(child)
                            nodes_per_depth[child.tot_node.depth] = (
                                nodes_per_depth.get(child.tot_node.depth, 0) + 1
                            )
                            max_depth_reached = max(
                                max_depth_reached, child.tot_node.depth
                            )

                        # Select one of the new children for rollout
                        if children:
                            expanded_node = children[0]
                            children_added = True

                except Exception as e:
                    print(
                        f"[MCTSSearchEngine] Error expanding node: {e}",
                        file=sys.stderr,
                    )

            # Phase 3: Simulation - Perform rollout from selected/expanded node
            rollout_value: float
            rollout_depth: int

            if expanded_node.visit_count == 0 or children_added:
                # Perform parallel rollouts for better value estimate
                parallel_count = min(
                    config.parallel_rollouts, config.rollout_budget - total_rollouts
                )

                rollout_result = self._rollout_service.execute(
                    "perform_parallel_rollouts",
                    {
                        "node": expanded_node.to_dict(),
                        "query": query,
                        "context": context,
                        "count": parallel_count,
                        "configuration": config.to_dict(),
                    },
                )

                parallel_values = rollout_result.get("values", [0.5])
                rollout_value = sum(parallel_values) / len(parallel_values)
                rollout_depth = expanded_node.tot_node.depth
                rollout_depths.append(rollout_depth)

                total_rollouts += parallel_count
                heuristic_rollouts += parallel_count  # Simplified tracking
            else:
                # Single rollout
                rollout_result = self._rollout_service.execute(
                    "perform_adaptive_rollout",
                    {
                        "node": expanded_node.to_dict(),
                        "query": query,
                        "context": context,
                        "configuration": config.to_dict(),
                    },
                )

                rollout_value = rollout_result.get("value", 0.5)
                rollout_depth = expanded_node.tot_node.depth
                rollout_depths.append(rollout_depth)
                total_rollouts += 1

            rollout_values.append(rollout_value)

            # Phase 4: Backpropagation - Update value estimates up the path
            backprop_path = selected_path.copy()
            if children_added:
                updated_expanded = tree_state.get_node(expanded_node.id)
                if updated_expanded:
                    backprop_path.append(updated_expanded)

            self._backpropagate(backprop_path, rollout_value, tree_state, config)

            # Check for convergence
            if total_rollouts >= 20 and self._check_convergence(
                tree_state, config.convergence_threshold
            ):
                termination_reason = "convergence"
                break

            # Check for perfect solution (early termination)
            if config.enable_early_termination:
                best_node = self._get_best_node(tree_state)
                if best_node and best_node.value_estimate >= 0.9:
                    termination_reason = "perfect_solution"
                    break

        # Reconstruct best path
        best_path = self._reconstruct_best_path(tree_state)

        if not best_path:
            termination_reason = "no_valid_path"
            raise ValueError("No valid path found in MCTS search")

        # Generate final answer from best path
        final_answer = self._synthesize_final_answer(best_path, query)

        # Calculate statistics
        total_latency = time.time() - start_time
        average_rollout_depth = (
            sum(rollout_depths) / len(rollout_depths) if rollout_depths else 0.0
        )
        average_rollout_value = (
            sum(rollout_values) / len(rollout_values) if rollout_values else 0.5
        )
        rollout_value_variance = self._calculate_variance(rollout_values)
        convergence_score = self._calculate_convergence_score(tree_state)
        exploration_ratio = (
            exploration_selections / (exploration_selections + exploitation_selections)
            if (exploration_selections + exploitation_selections) > 0
            else 0.5
        )
        value_distribution = [
            node.value_estimate for node in tree_state.all_nodes.values()
        ]

        all_evaluation_scores = [
            node.tot_node.evaluation_score
            for node in tree_state.all_nodes.values()
            if node.tot_node.evaluation_score is not None
        ]
        average_evaluation_score = (
            sum(all_evaluation_scores) / len(all_evaluation_scores)
            if all_evaluation_scores
            else 0.5
        )

        best_score = best_path[-1].value_estimate if best_path else 0.5

        rollout_statistics = RolloutStatistics(
            total_rollouts=total_rollouts,
            heuristic_rollouts=heuristic_rollouts,
            llm_rollouts=llm_rollouts,
            average_rollout_depth=average_rollout_depth,
            average_rollout_value=average_rollout_value,
            rollout_value_variance=rollout_value_variance,
        )

        statistics = SearchStatistics(
            nodes_per_depth=nodes_per_depth,
            average_evaluation_score=average_evaluation_score,
            max_depth_reached=max_depth_reached,
            search_strategy="mcts_ucb1",
            termination_reason=termination_reason,
            rollout_statistics=rollout_statistics,
        )

        result = MCTSSearchResult(
            best_path=best_path,
            final_answer=final_answer,
            evaluation_score=best_score,
            explored_nodes=len(tree_state.all_nodes),
            total_rollouts=total_rollouts,
            average_rollout_depth=average_rollout_depth,
            convergence_score=convergence_score,
            exploration_ratio=exploration_ratio,
            value_distribution=value_distribution,
            search_statistics=statistics,
            model_used="cognitive_generator",
            total_latency=total_latency,
        )

        return result.to_dict()

    # MARK: - Selection (UCB1)

    def _select_path(
        self, tree_state: MCTSTreeState, configuration: MCTSConfiguration
    ) -> tuple[list[MCTSNode], bool]:
        """Select path from root to leaf using UCB1 formula"""
        path: list[MCTSNode] = []
        current_node = tree_state.root_node
        path.append(current_node)

        is_exploration = False

        # Traverse tree using UCB1
        while current_node.tot_node.children:
            children = tree_state.get_children(current_node.id)

            if not children:
                break

            # Calculate UCB1 scores for all children
            parent_visits = current_node.visit_count
            best_child: MCTSNode | None = None
            best_score: float = float("-inf")
            is_exploration_selection = False

            for child in children:
                ucb1_score = self._calculate_ucb1(
                    child, parent_visits, configuration.ucb1_constant
                )

                if ucb1_score > best_score:
                    best_score = ucb1_score
                    best_child = child

                    # Determine if this is exploration or exploitation
                    exploitation = child.value_estimate
                    exploration = configuration.ucb1_constant * math.sqrt(
                        math.log(max(1, parent_visits)) / max(1, child.visit_count)
                    )
                    is_exploration_selection = exploration > exploitation

            if not best_child:
                break

            current_node = best_child
            path.append(current_node)
            is_exploration = is_exploration_selection

        return (path, is_exploration)

    def _calculate_ucb1(
        self, node: MCTSNode, parent_visits: int, ucb1_constant: float
    ) -> float:
        """Calculate UCB1 score for a node"""
        if node.visit_count == 0:
            return float("inf")  # Unvisited nodes prioritized

        exploitation = node.value_estimate
        exploration = ucb1_constant * math.sqrt(
            math.log(max(1, parent_visits)) / node.visit_count
        )

        return exploitation + exploration

    # MARK: - Expansion

    def _expand_node(
        self,
        node: MCTSNode,
        query: str,
        context: str | None,
        configuration: MCTSConfiguration,
        session_id: str,
    ) -> list[MCTSNode]:
        """Expand a node by generating child thoughts"""
        if not self._thought_generator:
            return []

        thought_count = configuration.adaptive_thought_count(node.tot_node.depth)

        # Convert MCTS config to ToT config for thought generator
        tot_config = self._mcts_to_tot_config(configuration)

        try:
            generator_result = self._thought_generator.execute(
                "generate_thoughts",
                {
                    "current_state": node.tot_node.to_dict(),
                    "query": query,
                    "context": context,
                    "count": thought_count,
                    "configuration": tot_config.to_dict(),
                },
            )

            child_thoughts_dicts = generator_result.get("thoughts", [])
            child_thoughts = [
                ToTThoughtNode.from_dict(t) for t in child_thoughts_dicts
            ]

            # Verify each child thought
            valid_child_thoughts: list[ToTThoughtNode] = []
            previous_nodes = [node.tot_node]

            for child in child_thoughts:
                try:
                    # Step 1: Safety filtering (if available)
                    if self._safety_filter:
                        try:
                            safety_result = self._safety_filter.execute(
                                "filter_tot_node",
                                {
                                    "node": child.to_dict(),
                                    "previous_nodes": [n.to_dict() for n in previous_nodes],
                                    "session_id": session_id,
                                },
                            )
                            if not safety_result.get("is_safe", True):
                                continue
                        except Exception:
                            pass  # Fail open

                    # Step 2: Use verification loop (if available)
                    if self._verification_loop:
                        try:
                            verification_result = self._verification_loop.execute(
                                "verify_tot_node",
                                {
                                    "node": child.to_dict(),
                                    "previous_nodes": [n.to_dict() for n in previous_nodes],
                                    "complexity": 0.7,
                                    "confidence": child.evaluation_score or 0.5,
                                },
                            )
                            if not verification_result.get("is_valid", True):
                                continue

                            # Update node with verification confidence
                            verified_confidence = verification_result.get("confidence")
                            if verified_confidence is not None:
                                child = child.with_evaluation_score(verified_confidence)
                        except Exception:
                            pass  # Fail open

                    valid_child_thoughts.append(child)

                except Exception as e:
                    print(
                        f"[MCTSSearchEngine] Error verifying MCTS node: {e}",
                        file=sys.stderr,
                    )
                    # On error, include the child (fail open)
                    valid_child_thoughts.append(child)

            # Convert valid ToT nodes to MCTS nodes
            return [MCTSNode.from_tot_node(child) for child in valid_child_thoughts]

        except Exception as e:
            print(
                f"[MCTSSearchEngine] Error generating child thoughts: {e}",
                file=sys.stderr,
            )
            return []

    def _mcts_to_tot_config(
        self, mcts_config: MCTSConfiguration
    ) -> ToTConfiguration:
        """Convert MCTSConfiguration to ToTConfiguration for compatibility"""
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

    # MARK: - Backpropagation

    def _backpropagate(
        self,
        path: list[MCTSNode],
        value: float,
        tree_state: MCTSTreeState,
        configuration: MCTSConfiguration,
    ) -> None:
        """Backpropagate rollout value up the path"""
        # Backpropagate from leaf to root
        for index, node in enumerate(reversed(path)):
            depth = node.tot_node.depth
            discount = configuration.discount_factor ** (len(path) - index - 1)
            discounted_value = value * discount

            updated_node = node.with_rollout_value(discounted_value)
            tree_state.update_node(updated_node)

            # Update node in path for next iteration
            path[-(index + 1)] = updated_node

    # MARK: - Path Reconstruction

    def _reconstruct_best_path(self, tree_state: MCTSTreeState) -> list[MCTSNode]:
        """Reconstruct best path from tree state"""
        # Find all leaf nodes
        leaves = tree_state.get_leaves()

        if not leaves:
            # No leaves found, return path to deepest node
            all_nodes = list(tree_state.all_nodes.values())
            if not all_nodes:
                return [tree_state.root_node]

            deepest_node = max(all_nodes, key=lambda n: n.tot_node.depth)
            return tree_state.get_path_to_root(deepest_node.id)

        # Find best leaf (highest value estimate)
        best_leaf = max(leaves, key=lambda n: n.value_estimate)

        # Reconstruct path from root to best leaf
        return tree_state.get_path_to_root(best_leaf.id)

    # MARK: - Convergence Detection

    def _check_convergence(
        self, tree_state: MCTSTreeState, threshold: float
    ) -> bool:
        """Check if search has converged"""
        # Get top nodes by value
        all_nodes = list(tree_state.all_nodes.values())
        top_nodes = sorted(all_nodes, key=lambda n: n.value_estimate, reverse=True)[:5]

        if len(top_nodes) < 2:
            return False

        # Check variance of top nodes
        values = [node.value_estimate for node in top_nodes]
        variance = self._calculate_variance(values)

        return variance < threshold

    def _calculate_variance(self, values: list[float]) -> float:
        """Calculate variance of values"""
        if len(values) <= 1:
            return 0.0

        mean = sum(values) / len(values)
        squared_diffs = [(v - mean) ** 2 for v in values]
        return sum(squared_diffs) / len(values)

    def _calculate_convergence_score(self, tree_state: MCTSTreeState) -> float:
        """Calculate convergence score (lower = more converged)"""
        all_nodes = list(tree_state.all_nodes.values())
        if len(all_nodes) <= 1:
            return 0.0

        values = [node.value_estimate for node in all_nodes]
        return self._calculate_variance(values)

    def _get_best_node(self, tree_state: MCTSTreeState) -> MCTSNode | None:
        """Get best node in tree"""
        all_nodes = list(tree_state.all_nodes.values())
        if not all_nodes:
            return None

        return max(all_nodes, key=lambda n: n.value_estimate)

    # MARK: - Final Answer Synthesis

    def _synthesize_final_answer(self, path: list[MCTSNode], query: str) -> str:
        """Synthesize final answer from best path"""
        if not path:
            return "Unable to synthesize answer from empty path."

        if not self._cognitive_generator:
            self.initialize()
            if not self._cognitive_generator:
                # Fallback: use last node's thought
                return path[-1].tot_node.thought if path else ""

        # Build synthesis prompt
        path_description = "\n\n".join(
            [
                f"Step {index}: {node.tot_node.thought}"
                for index, node in enumerate(path)
            ]
        )

        synthesis_prompt = f"""Based on the following reasoning path through the Monte-Carlo Thought Search exploration, provide a clear, concise, and complete final answer to the original question.

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
                    "context": path_description,
                    "persona": "mavaia",
                },
            )

            return response_result.get("text", "").strip()
        except Exception as e:
            print(
                f"[MCTSSearchEngine] Error synthesizing final answer: {e}",
                file=sys.stderr,
            )
            # Fallback: use last node's thought
            return path[-1].tot_node.thought if path else ""

