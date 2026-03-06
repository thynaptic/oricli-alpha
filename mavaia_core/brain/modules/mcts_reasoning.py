from __future__ import annotations
"""
Monte-Carlo Thought Search (MCTS) Reasoning Module

Orchestrates MCTS reasoning process with UCB1 selection, rollouts,
and backpropagation. Ported from Swift MCTSService.swift
"""

import time
import math
from typing import Any, Dict, List, Optional
import logging

from mavaia_core.brain.base_module import BaseBrainModule, ModuleMetadata
from mavaia_core.brain.modules.mcts_models import (
    MCTSNode,
    MCTSTreeState,
    MCTSConfiguration,
    MCTSResult,
)
from mavaia_core.brain.modules.tot_models import ToTThoughtNode
from mavaia_core.brain.registry import ModuleRegistry
from mavaia_core.exceptions import InvalidParameterError, ModuleOperationError

logger = logging.getLogger(__name__)


class MCTSReasoning(BaseBrainModule):
    """
    Monte-Carlo Thought Search reasoning orchestrator.

    Executes MCTS with UCB1 selection, rollouts, and backpropagation
    for optimal reasoning path discovery.
    """

    def __init__(self) -> None:
        """Initialize the module"""
        super().__init__()
        self._cognitive_generator = None
        self._memory_graph = None
        self._text_engine = None

    @property
    def metadata(self) -> ModuleMetadata:
        return ModuleMetadata(
            name="mcts_reasoning",
            version="1.0.1",
            description=(
                "Monte-Carlo Thought Search reasoning orchestrator with "
                "UCB1 selection and rollouts"
            ),
            operations=[
                "execute_mcts",
                "should_activate",
                "format_reasoning_output",
                "status",
            ],
            dependencies=[],
            enabled=True,
            model_required=False,
        )

    def initialize(self) -> bool:
        """Initialize dependent modules"""
        try:
            # Lazy load cognitive generator
            self._cognitive_generator = ModuleRegistry.get_module(
                "cognitive_generator"
            )
            
            # Lazy load text generation engine directly to avoid recursion
            try:
                self._text_engine = ModuleRegistry.get_module("text_generation_engine")
            except Exception:
                self._text_engine = None

            # Lazy load memory graph (optional)
            try:
                self._memory_graph = ModuleRegistry.get_module("memory_graph")
            except Exception as e:
                logger.debug(
                    "Optional dependency 'memory_graph' unavailable for mcts_reasoning",
                    exc_info=True,
                    extra={"module_name": "mcts_reasoning", "error_type": type(e).__name__},
                )

            return True
        except Exception as e:
            logger.debug(
                "Failed to initialize mcts_reasoning dependencies",
                exc_info=True,
                extra={"module_name": "mcts_reasoning", "error_type": type(e).__name__},
            )
            return False

    def execute(
        self, operation: str, params: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Execute MCTS operations.

        Supported operations:
        - execute_mcts: Full MCTS execution
        - should_activate: Activation decision
        - format_reasoning_output: Format path as text
        - status: Check module health
        """
        if operation == "status":
            return {
                "success": True,
                "status": "active",
                "initialized": True,
                "version": self.metadata.version
            }

        if operation == "execute_mcts":
            res = self._execute_mcts(params)
            return {
                "success": True,
                "result": res,
                "metadata": {
                    "confidence": res.get("confidence", 0.0),
                    "total_rollouts": res.get("total_rollouts", 0)
                }
            }
        elif operation == "should_activate":
            res = self._should_activate(params)
            res["success"] = True
            return res
        elif operation == "format_reasoning_output":
            res = self._format_reasoning_output(params)
            res["success"] = True
            return res
        else:
            return {"success": False, "error": f"Unknown operation: {operation}"}

    def _execute_mcts(self, params: dict[str, Any]) -> dict[str, Any]:
        """
        Execute full MCTS reasoning process.

        Args:
            params: Dictionary with:
                - query (str): The query to reason about
                - context (str, optional): Additional context
                - configuration (dict, optional): MCTS configuration
                - session_id (str, optional): Session identifier

        Returns:
            Dictionary with MCTSResult data
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
        session_id = params.get("session_id", "")

        config = (
            MCTSConfiguration.from_dict(config_dict)
            if config_dict
            else MCTSConfiguration.default()
        )

        start_time = time.time()

        # Step 1: Retrieve long-term memory context (optional)
        memory_context = ""
        if self._memory_graph:
            try:
                memory_result = self._memory_graph.execute(
                    "recall_memories",
                    {
                        "query": query,
                        "limit": 5,
                        "use_graph": True,
                    },
                )
                if memory_result.get("memories"):
                    memories = memory_result["memories"]
                    memory_context = "Relevant memories:\n"
                    for i, memory in enumerate(memories[:5], 1):
                        memory_context += (
                            f"{i}. {memory.get('content', '')}\n"
                        )
                        if memory.get("summary"):
                            memory_context += (
                                f"   Summary: {memory['summary']}\n"
                            )
                    memory_context += "\n"
            except Exception:
                pass  # Memory retrieval is optional

        # Step 2: Combine context
        context_parts = [c for c in [context, memory_context] if c]
        combined_context = "\n\n".join(context_parts) if context_parts else ""

        # Step 3: Execute MCTS search
        search_result = self._search(
            query=query,
            context=combined_context,
            configuration=config,
            session_id=session_id,
        )

        # Step 4: Synthesize final answer
        final_answer = self._synthesize_final_answer(
            search_result["best_path"], query
        )

        # Step 5: Calculate overall confidence
        confidence = self._calculate_overall_confidence(
            search_result["best_path"]
        )

        # Step 6: Format total reasoning
        total_reasoning = "\n\n---\n\n".join(
            [node.tot_node.thought for node in search_result["best_path"]]
        )

        result = MCTSResult(
            path=search_result["best_path"],
            final_answer=final_answer,
            total_reasoning=total_reasoning,
            confidence=confidence,
            model_used="cognitive_generator",
            total_latency=time.time() - start_time,
            total_rollouts=search_result["total_rollouts"],
            exploration_ratio=search_result["exploration_ratio"],
        )

        return result.to_dict()

    def _search(
        self,
        query: str,
        context: str | None,
        configuration: MCTSConfiguration,
        session_id: str,
    ) -> dict[str, Any]:
        """Execute Monte-Carlo Tree Search"""
        if not self._cognitive_generator:
            self.initialize()
            if not self._cognitive_generator:
                raise ModuleOperationError(
                    module_name="mcts_reasoning",
                    operation="execute_mcts",
                    reason="Cognitive generator module not available",
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
        tree_state = MCTSTreeState(
            root_node=root_node, max_depth=configuration.max_depth
        )

        # Statistics tracking
        total_rollouts = 0
        exploration_selections = 0
        exploitation_selections = 0
        rollout_values: list[float] = []

        # MCTS main loop
        while total_rollouts < configuration.rollout_budget:
            # Check timeout
            elapsed = time.time() - start_time
            if elapsed > configuration.max_search_time:
                logger.info(
                    "MCTS search timeout reached",
                    extra={"module_name": "mcts_reasoning", "elapsed_s": round(float(elapsed), 6)},
                )
                break

            # Phase 1: Selection - Use UCB1 to select path from root to leaf
            selected_path, is_exploration = self._select_path(
                tree_state, configuration
            )

            if not selected_path:
                break

            selected_node = selected_path[-1]

            # Track selection type
            if is_exploration:
                exploration_selections += 1
            else:
                exploitation_selections += 1

            # Check if we've reached max depth
            if selected_node.tot_node.depth >= configuration.max_depth:
                # Still perform rollout for value estimation
                if total_rollouts < configuration.rollout_budget:
                    rollout_value = self._perform_rollout(
                        selected_node, query, context, configuration
                    )

                    rollout_values.append(rollout_value)
                    total_rollouts += 1

                    # Backpropagate
                    self._backpropagate(
                        selected_path, rollout_value, tree_state, configuration
                    )

                # Check for early termination
                if (
                    configuration.enable_early_termination
                    and selected_node.value_estimate >= 0.9
                ):
                    break

                continue

            # Phase 2: Expansion - Add new child nodes if node has sufficient visits
            expanded_node = selected_node
            children_added = False

            if selected_node.visit_count >= configuration.min_visits_for_expansion:
                children = self._expand_node(
                    selected_node, query, context, configuration, session_id
                )

                if children:
                    for child in children:
                        tree_state.add_node(child)

                    # Select one of the new children for rollout
                    if children:
                        expanded_node = children[0]
                        children_added = True

            # Phase 3: Simulation (Rollout)
            rollout_value = self._perform_rollout(
                expanded_node, query, context, configuration
            )

            rollout_values.append(rollout_value)
            total_rollouts += 1

            # Phase 4: Backpropagation
            # Add expanded node to path if it was just added
            if children_added:
                rollout_path = selected_path + [expanded_node]
            else:
                rollout_path = selected_path

            self._backpropagate(
                rollout_path, rollout_value, tree_state, configuration
            )

        # Find best path (highest value estimate)
        best_path = self._find_best_path(tree_state)

        # Calculate exploration ratio
        total_selections = exploration_selections + exploitation_selections
        exploration_ratio = (
            exploration_selections / total_selections
            if total_selections > 0
            else 0.0
        )

        return {
            "best_path": best_path,
            "total_rollouts": total_rollouts,
            "exploration_ratio": exploration_ratio,
        }

    def _select_path(
        self,
        tree_state: MCTSTreeState,
        configuration: MCTSConfiguration,
    ) -> tuple[list[MCTSNode], bool]:
        """
        Select path from root to leaf using UCB1.

        Returns:
            Tuple of (path, is_exploration)
        """
        path: list[MCTSNode] = [tree_state.root_node]
        current = tree_state.root_node
        is_exploration = False

        while current.tot_node.children:
            children = tree_state.get_children(current.id)
            if not children:
                break

            # Calculate UCB1 scores for all children
            parent_visits = current.visit_count
            ucb1_scores = [
                (
                    child,
                    child.ucb1_score(parent_visits, configuration.ucb1_constant),
                )
                for child in children
            ]

            # Select child with highest UCB1 score
            best_child, best_score = max(ucb1_scores, key=lambda x: x[1])

            # Check if this is exploration (high exploration component)
            exploitation = best_child.value_estimate
            exploration = (
                configuration.ucb1_constant
                * math.sqrt(
                    math.log(parent_visits + 1) / best_child.visit_count
                )
                if best_child.visit_count > 0
                else float("inf")
            )

            if exploration > exploitation:
                is_exploration = True

            path.append(best_child)
            current = best_child

        return path, is_exploration

    def _expand_node(
        self,
        node: MCTSNode,
        query: str,
        context: str | None,
        configuration: MCTSConfiguration,
        session_id: str,
    ) -> list[MCTSNode]:
        """Expand a node by generating child thoughts"""
        thought_count = configuration.adaptive_thought_count(
            node.tot_node.depth
        )

        # Generate child thoughts (similar to ToT)
        child_thoughts = self._generate_child_thoughts(
            node.tot_node, query, context, thought_count, configuration
        )

        # Convert to MCTS nodes
        mcts_children: list[MCTSNode] = []
        for tot_child in child_thoughts:
            mcts_child = MCTSNode.from_tot_node(tot_child)
            mcts_children.append(mcts_child)

        return mcts_children

    def _generate_child_thoughts(
        self,
        current_node: ToTThoughtNode,
        query: str,
        context: str | None,
        count: int,
        configuration: MCTSConfiguration,
    ) -> list[ToTThoughtNode]:
        """Generate child thoughts from current node"""
        if not self._cognitive_generator and not getattr(self, "_text_engine", None):
            return []

        # Use an imperative prompt for the SLM to get real ideas
        prompt = (
            f"Instructions: Generate {count} diverse, next logical reasoning steps for the task below.\n"
            f"Task: {query}\n"
            f"Current state: {current_node.thought}\n"
            f"Next Idea:"
        )

        try:
            # Prefer the text engine directly to avoid recursion and template-traps
            if getattr(self, "_text_engine", None):
                gen_res = self._text_engine.execute(
                    "generate_with_neural",
                    {
                        "prompt": prompt,
                        "temperature": 0.85,
                        "max_length": 300,
                    }
                )
                response_text = gen_res.get("text", "")
            else:
                response_result = self._cognitive_generator.execute(
                    "generate_response",
                    {
                        "input_text": prompt,
                        "context": context or "",
                        "persona": "mavaia",
                    },
                )
                response_text = response_result.get("text", "")
            if not response_text:
                return []

            # Split response into individual thoughts
            thoughts = []
            lines = response_text.split("\n")

            current_thought = ""
            for line in lines:
                line = line.strip()
                if not line:
                    if current_thought:
                        thoughts.append(current_thought)
                        current_thought = ""
                    continue

                if (
                    line[0].isdigit()
                    or line.startswith("-")
                    or line.startswith("*")
                    or line.startswith("•")
                ):
                    if current_thought:
                        thoughts.append(current_thought)
                    current_thought = line.lstrip("0123456789.-*• ").strip()
                else:
                    if current_thought:
                        current_thought += " " + line
                    else:
                        current_thought = line

            if current_thought:
                thoughts.append(current_thought)

            thoughts = thoughts[:count]

            # Create child nodes
            child_nodes: list[ToTThoughtNode] = []
            for thought in thoughts:
                if thought:
                    child_node = ToTThoughtNode(
                        parent_id=current_node.id,
                        depth=current_node.depth + 1,
                        thought=thought,
                        state={"type": "thought", "parent": current_node.id},
                        metadata={"generated": "true"},
                    )
                    child_nodes.append(child_node)

            return child_nodes

        except Exception as e:
            logger.debug(
                "Error generating thoughts",
                exc_info=True,
                extra={"module_name": "mcts_reasoning", "error_type": type(e).__name__},
            )
            return []

    def _perform_rollout(
        self,
        node: MCTSNode,
        query: str,
        context: str | None,
        configuration: MCTSConfiguration,
    ) -> float:
        """
        Perform a rollout (simulation) from a node.

        Returns a value estimate (0.0-1.0).
        """
        # Simple heuristic rollout
        # Can be enhanced with LLM-based rollouts

        # Base value from node's thought quality
        value = 0.5

        # Length heuristic
        thought_length = len(node.tot_node.thought)
        if 50 <= thought_length <= 500:
            value += 0.2
        elif thought_length < 20:
            value -= 0.2

        # Depth penalty
        if node.tot_node.depth > 2:
            value -= 0.1 * (node.tot_node.depth - 2)

        # Keyword matching
        query_words = set(query.lower().split())
        thought_words = set(node.tot_node.thought.lower().split())
        overlap = len(query_words & thought_words)
        if overlap > 0:
            value += min(0.2, overlap * 0.05)

        return max(0.0, min(1.0, value))

    def _backpropagate(
        self,
        path: list[MCTSNode],
        value: float,
        tree_state: MCTSTreeState,
        configuration: MCTSConfiguration,
    ) -> None:
        """Backpropagate rollout value up the tree"""
        # Traverse path backwards and update nodes
        for i in range(len(path) - 1, -1, -1):
            node = path[i]

            # Apply discount factor based on depth
            discounted_value = value * (
                configuration.discount_factor ** (len(path) - 1 - i)
            )

            # Update node with rollout value
            updated_node = node.with_rollout_value(discounted_value)
            tree_state.update_node(updated_node)

    def _find_best_path(
        self, tree_state: MCTSTreeState
    ) -> list[MCTSNode]:
        """Find the best path (highest value estimate)"""
        # Find leaf with highest value estimate
        leaves = tree_state.get_leaves()

        if not leaves:
            return [tree_state.root_node]

        best_leaf = max(leaves, key=lambda n: n.value_estimate)
        return tree_state.get_path_to_root(best_leaf.id)

    def _synthesize_final_answer(
        self, path: list[MCTSNode], query: str
    ) -> str:
        """Synthesize final answer from MCTS path"""
        if not path:
            return "Unable to generate answer"

        path_description = "\n\n".join(
            [
                f"Step {i+1}: {node.tot_node.thought}"
                for i, node in enumerate(path)
            ]
        )

        prompt = f"""Based on the following MCTS reasoning path, provide a clear, concise final answer to the original question.

Original Question: {query}

Reasoning Path:
{path_description}

Final Answer:
"""

        if not self._cognitive_generator:
            self.initialize()
            if not self._cognitive_generator:
                return path[-1].tot_node.thought if path else ""

        try:
            response_result = self._cognitive_generator.execute(
                "generate_response",
                {
                    "input_text": prompt,
                    "context": path_description,
                    "persona": "mavaia",
                },
            )
            return response_result.get("text", "").strip()
        except Exception:
            return path[-1].tot_node.thought if path else ""

    def _calculate_overall_confidence(
        self, path: list[MCTSNode]
    ) -> float:
        """Calculate overall confidence from MCTS path"""
        if not path:
            return 0.5

        confidences = [node.value_estimate for node in path]
        return sum(confidences) / len(confidences)

    def _should_activate(self, params: dict[str, Any]) -> dict[str, Any]:
        """
        Determine if MCTS should be activated.

        Args:
            params: Dictionary with:
                - query (str): The query to analyze

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

        # Simple heuristic: MCTS for complex queries
        # Can be enhanced with complexity detector
        return {"should_activate": len(query) > 200}

    def _format_reasoning_output(
        self, params: dict[str, Any]
    ) -> dict[str, Any]:
        """
        Format reasoning output from path.

        Args:
            params: Dictionary with:
                - path (list[dict]): Path nodes to format

        Returns:
            Dictionary with formatted_output string
        """
        path_data = params.get("path", [])
        path = [MCTSNode.from_dict(n) for n in path_data]
        output = self._format_reasoning_output_internal(path)

        return {"formatted_output": output}

    def _format_reasoning_output_internal(
        self, path: list[MCTSNode]
    ) -> str:
        """Internal formatting"""
        output_lines: list[str] = []

        for i, node in enumerate(path):
            output_lines.append(
                f"Depth {node.tot_node.depth}: {node.tot_node.thought}"
            )

            output_lines.append(
                f"MCTS Value: {node.value_estimate:.2f}, "
                f"Visits: {node.visit_count}"
            )

            if i < len(path) - 1:
                output_lines.append("")  # Blank line between steps

        return "\n".join(output_lines)
