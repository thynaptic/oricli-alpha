"""
Monte-Carlo Thought Search Service

Main orchestrator service for Monte-Carlo Thought Search (MCTS) reasoning framework.
Orchestrates MCTS search with complexity detection, memory integration, and reflection.
Ported from Swift MCTSService.swift
"""

import sys
import time
import uuid
from pathlib import Path
from typing import Any

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent))

from mavaia_core.brain.base_module import BaseBrainModule, ModuleMetadata

# Lazy imports to avoid timeout during module discovery
def _lazy_import_mcts_models():
    """Lazy import MCTS models only when needed"""
    global MCTSNode, MCTSConfiguration, MCTSResult, MCTSSearchResult, MCTSComplexityScore, ToTThoughtNode
    if MCTSNode is None:
        try:
from mcts_models import (
                MCTSNode as MN,
                MCTSConfiguration as MC,
                MCTSResult as MR,
                MCTSSearchResult as MSR,
                MCTSComplexityScore as MCS,
)
            from tot_models import ToTThoughtNode as TTTN
            MCTSNode = MN
            MCTSConfiguration = MC
            MCTSResult = MR
            MCTSSearchResult = MSR
            MCTSComplexityScore = MCS
            ToTThoughtNode = TTTN
        except ImportError:
            pass

MCTSNode = None
MCTSConfiguration = None
MCTSResult = None
MCTSSearchResult = None
MCTSComplexityScore = None
ToTThoughtNode = None


class MCTSService(BaseBrainModule):
    """
    Main orchestrator service for Monte-Carlo Thought Search (MCTS) reasoning framework.
    Orchestrates MCTS search with complexity detection, memory integration, and reflection.
    """

    def __init__(self) -> None:
        """Initialize the module"""
        self._complexity_detector = None
        self._search_engine = None
        self._memory_graph = None
        self._cognitive_generator = None
        self._reflection_service = None

    @property
    def metadata(self) -> ModuleMetadata:
        return ModuleMetadata(
            name="mcts_service",
            version="1.0.0",
            description=(
                "Monte-Carlo Thought Search orchestrator with UCB1 algorithm, "
                "rollouts, and adaptive exploration"
            ),
            operations=[
                "execute_mcts",
                "analyze_mcts_complexity",
                "should_activate",
                "format_reasoning_output",
            ],
            dependencies=[],
            enabled=True,
            model_required=False,
        )

    def initialize(self) -> bool:
        """Initialize dependent modules"""
        _lazy_import_mcts_models()
        try:
            # Lazy import to avoid circular dependency during module discovery
            from mavaia_core.brain.registry import ModuleRegistry

            # Lazy load complexity detector
            self._complexity_detector = ModuleRegistry.get_module(
                "mcts_complexity_detector"
            )

            # Load search engine
            self._search_engine = ModuleRegistry.get_module("mcts_search_engine")
            # Don't call discover_modules() here - it can cause hangs
            # If module not found, it will be discovered on next discovery cycle

            # Lazy load cognitive generator
            self._cognitive_generator = ModuleRegistry.get_module(
                "cognitive_generator"
            )

            # Optional dependencies
            try:
                self._memory_graph = ModuleRegistry.get_module("memory_graph")
            except Exception:
                pass
            try:
                self._reflection_service = ModuleRegistry.get_module(
                    "reasoning_reflection"
                )
            except Exception:
                pass

            return True
        except Exception:
            return False

    def execute(self, operation: str, params: dict[str, Any]) -> dict[str, Any]:
        """
        Execute MCTS operations.

        Supported operations:
        - execute_mcts: Full MCTS execution
        - analyze_mcts_complexity: Complexity analysis
        - should_activate: Activation decision
        - format_reasoning_output: Format path as text
        """
        _lazy_import_mcts_models()
        if operation == "execute_mcts":
            return self._execute_mcts(params)
        elif operation == "analyze_mcts_complexity":
            return self._analyze_mcts_complexity(params)
        elif operation == "should_activate":
            return self._should_activate(params)
        elif operation == "format_reasoning_output":
            return self._format_reasoning_output(params)
        else:
            raise ValueError(f"Unknown operation: {operation}")

    def _execute_mcts(self, params: dict[str, Any]) -> dict[str, Any]:
        """
        Execute Monte-Carlo Thought Search reasoning process.

        Args:
            params: Dictionary with:
                - query (str): The query to reason about
                - context (str, optional): Additional context
                - configuration (dict, optional): MCTS configuration
                - session_id (str, optional): Session identifier

        Returns:
            Dictionary with MCTSResult data
        """
        if not self._search_engine:
            self.initialize()
            if not self._search_engine:
                raise RuntimeError("Search engine module not available")

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
                        memory_context += f"{i}. {memory.get('content', '')}\n"
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

        # Step 3: Analyze complexity to confirm MCTS is appropriate
        complexity_score = self._analyze_mcts_complexity_internal(
            query, combined_context
        )

        if not complexity_score.requires_mcts:
            print(
                "[MCTSService] MCTS complexity analysis suggests MCTS may not be "
                "needed. Continuing anyway since MCTS was explicitly requested.",
                file=sys.stderr,
            )

        # Step 4: Adjust configuration based on complexity analysis if needed
        final_config = config
        if (
            complexity_score.estimated_rollout_budget > 0
            and complexity_score.estimated_rollout_budget != config.rollout_budget
        ):
            # Create updated configuration with adjusted rollout budget
            final_config = MCTSConfiguration(
                max_depth=config.max_depth,
                base_thoughts_per_step=config.base_thoughts_per_step,
                pruning_top_k=config.pruning_top_k,
                min_score_threshold=config.min_score_threshold,
                evaluation_weights=config.evaluation_weights,
                max_search_time=config.max_search_time,
                enable_early_termination=config.enable_early_termination,
                ucb1_constant=config.ucb1_constant,
                rollout_budget=complexity_score.estimated_rollout_budget,
                rollout_depth=config.rollout_depth,
                min_visits_for_expansion=config.min_visits_for_expansion,
                enable_adaptive_rollout=config.enable_adaptive_rollout,
                heuristic_rollout_threshold=config.heuristic_rollout_threshold,
                parallel_rollouts=config.parallel_rollouts,
                enable_value_caching=config.enable_value_caching,
                convergence_threshold=config.convergence_threshold,
                discount_factor=config.discount_factor,
            )

        # Step 5: Execute search
        search_result_dict: dict[str, Any]
        try:
            search_result_dict = self._search_engine.execute(
                "search",
                {
                    "query": query,
                    "context": combined_context,
                    "configuration": final_config.to_dict(),
                    "session_id": session_id,
                },
            )
        except Exception as e:
            print(
                f"[MCTSService] MCTS search failed: {e}",
                file=sys.stderr,
            )
            raise

        search_result = MCTSSearchResult.from_dict(search_result_dict)

        # Step 6: Store best path nodes in memory (optional)
        if self._memory_graph:
            for node in search_result.best_path:
                try:
                    self._memory_graph.execute(
                        "store_memory",
                        {
                            "content": node.tot_node.thought,
                            "type": "mcts_reasoning_step",
                            "metadata": {
                                "node_id": node.id,
                                "depth": str(node.tot_node.depth),
                                "value_estimate": str(node.value_estimate),
                                "visit_count": str(node.visit_count),
                            },
                            "importance": node.value_estimate,
                            "tags": ["mcts", "reasoning"],
                            "keywords": self._extract_keywords(node.tot_node.thought),
                        },
                    )
                except Exception:
                    pass  # Memory storage is optional

        # Step 7: Convert search result to MCTSResult
        result = MCTSResult.from_search_result(search_result)

        # Step 8: Reflection - review and correct if needed
        if self._reflection_service:
            try:
                reflection_result = self._reflection_service.execute(
                    "reflect_on_mcts_path",
                    {
                        "path": [n.to_dict() for n in result.path],
                        "final_answer": result.final_answer,
                        "confidence": result.confidence,
                        "session_id": session_id,
                    },
                )

                if reflection_result.get("should_reflect"):
                    improved_steps_dicts = reflection_result.get("improved_steps")
                    if improved_steps_dicts:
                        from cot_models import CoTStep

                        # Convert improved CoT steps back to MCTS nodes
                        improved_path = [
                            MCTSNode.from_tot_node(
                                ToTThoughtNode(
                                    id=step["id"],
                                    depth=0,
                                    thought=step.get("reasoning") or step.get("prompt", ""),
                                    state=step.get("intermediate_state"),
                                    evaluation_score=step.get("confidence"),
                                )
                            )
                            for step in improved_steps_dicts
                        ]

                        # Re-synthesize final answer
                        final_answer = self._synthesize_final_answer(
                            improved_path, query
                        )

                        result = MCTSResult(
                            path=improved_path,
                            final_answer=final_answer,
                            total_reasoning="\n\n---\n\n".join(
                                [n.tot_node.thought for n in improved_path]
                            ),
                            confidence=self._calculate_overall_confidence(improved_path),
                            model_used="cognitive_generator",
                            total_latency=result.total_latency,
                            total_rollouts=result.total_rollouts,
                            exploration_ratio=result.exploration_ratio,
                        )

            except Exception:
                pass  # Fail open

        print(
            f"[MCTSService] MCTS execution completed: {len(result.path)} steps, "
            f"confidence {result.confidence:.2f}, {result.total_rollouts} rollouts, "
            f"exploration ratio {result.exploration_ratio:.2f}, "
            f"latency {result.total_latency:.2f}s"
        )

        return result.to_dict()

    def _analyze_mcts_complexity(
        self, params: dict[str, Any]
    ) -> dict[str, Any]:
        """Analyze query complexity for MCTS"""
        query = params.get("query", "")
        if not query:
            raise ValueError("query parameter is required")

        context = params.get("context")
        return self._analyze_mcts_complexity_internal(query, context).to_dict()

    def _analyze_mcts_complexity_internal(
        self, query: str, context: str | None
    ) -> MCTSComplexityScore:
        """Internal MCTS complexity analysis"""
        if not self._complexity_detector:
            self.initialize()
            if not self._complexity_detector:
                # Fallback: simple heuristic
                query_length = len(query)
                requires_mcts = query_length > 150
                return MCTSComplexityScore(
                    score=min(1.0, query_length / 800.0),
                    factors=[],
                    requires_mcts=requires_mcts,
                    estimated_rollout_budget=100,
                    exploration_benefit=0.5,
                )

        result_dict = self._complexity_detector.execute(
            "analyze_mcts_complexity",
            {
                "query": query,
                "context": context,
            },
        )
        return MCTSComplexityScore.from_dict(result_dict)

    def _should_activate(self, params: dict[str, Any]) -> dict[str, Any]:
        """Determine if MCTS should be activated"""
        query = params.get("query", "")
        if not query:
            raise ValueError("query parameter is required")

        context = params.get("context")

        if not self._complexity_detector:
            self.initialize()

        if self._complexity_detector:
            try:
                result = self._complexity_detector.execute(
                    "should_activate_mcts",
                    {
                        "query": query,
                        "context": context,
                    },
                )
                return {"should_activate": result.get("should_use", False)}
            except Exception:
                pass

        # Fallback
        score = self._analyze_mcts_complexity_internal(query, context)
        return {"should_activate": score.requires_mcts}

    def _format_reasoning_output(
        self, params: dict[str, Any]
    ) -> dict[str, Any]:
        """Format reasoning output from path"""
        path_data = params.get("path", [])
        path = [MCTSNode.from_dict(n) for n in path_data]
        output = self._format_reasoning_output_internal(path)

        return {"formatted_output": output}

    def _format_reasoning_output_internal(
        self, path: list[MCTSNode]
    ) -> str:
        """Internal formatting"""
        output_lines: list[str] = []

        for index, node in enumerate(path):
            output_lines.append(
                f"Depth {node.tot_node.depth}: {node.tot_node.thought}"
            )

            if node.tot_node.evaluation_score is not None:
                output_lines.append(
                    f"Evaluation Score: {node.tot_node.evaluation_score:.2f}"
                )

            output_lines.append(
                f"MCTS Value: {node.value_estimate:.2f}, Visits: {node.visit_count}"
            )

            if index < len(path) - 1:
                output_lines.append("")  # Blank line between steps

        return "\n".join(output_lines)

    def _synthesize_final_answer(
        self, path: list[MCTSNode], query: str
    ) -> str:
        """Synthesize final answer from MCTS path"""
        if not path:
            return "Unable to synthesize answer from empty path."

        if not self._cognitive_generator:
            self.initialize()
            if not self._cognitive_generator:
                # Fallback: use last node's thought
                return path[-1].tot_node.thought if path else ""

        path_description = "\n\n".join(
            [
                f"Step {index + 1}: {node.tot_node.thought}"
                for index, node in enumerate(path)
            ]
        )

        prompt = f"""Based on the following MCTS reasoning path, provide a clear, concise final answer to the original question.

Original Question: {query}

Reasoning Path:
{path_description}

Final Answer:
"""

        try:
            response_result = self._cognitive_generator.execute(
                "generate_response",
                {
                    "input": prompt,
                    "context": path_description,
                    "persona": "mavaia",
                },
            )

            return response_result.get("text", "").strip()
        except Exception:
            # Fallback
            return path[-1].tot_node.thought if path else ""

    def _calculate_overall_confidence(self, path: list[MCTSNode]) -> float:
        """Calculate overall confidence from MCTS path"""
        if not path:
            return 0.5

        confidences = [node.value_estimate for node in path]
        return sum(confidences) / len(confidences)

    def _extract_keywords(self, text: str) -> list[str]:
        """Extract keywords from text for memory storage"""
        words = [
            word.lower()
            for word in text.split()
            if len(word) > 4 and word.isalnum()
        ]
        # Return unique keywords, limited to 5
        unique_words = list(set(words))[:5]
        return unique_words

