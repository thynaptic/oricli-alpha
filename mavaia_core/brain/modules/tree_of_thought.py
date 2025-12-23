"""
Tree-of-Thought Reasoning Module

Main orchestrator service for Tree-of-Thought reasoning framework.
Orchestrates multi-path exploration, evaluation, and best path selection.
Ported from Swift TreeOfThoughtService.swift
"""

import time
import uuid
from typing import Any
import logging

from mavaia_core.brain.base_module import BaseBrainModule, ModuleMetadata
from mavaia_core.brain.modules.tot_models import (
    ToTThoughtNode,
    ToTConfiguration,
    ToTResult,
    ToTComplexityScore,
    ToTSearchResult,
)
from mavaia_core.brain.registry import ModuleRegistry
from mavaia_core.exceptions import InvalidParameterError, ModuleOperationError

logger = logging.getLogger(__name__)


class TreeOfThought(BaseBrainModule):
    """
    Tree-of-Thought reasoning orchestrator.

    Executes multi-path reasoning exploration with best-first search,
    evaluation, and path selection.
    """

    def __init__(self) -> None:
        """Initialize the module"""
        super().__init__()
        self._complexity_detector = None
        self._search_engine = None
        self._memory_graph = None
        self._cognitive_generator = None

    @property
    def metadata(self) -> ModuleMetadata:
        return ModuleMetadata(
            name="tree_of_thought",
            version="1.0.0",
            description=(
                "Tree-of-Thought reasoning orchestrator with multi-path "
                "exploration and best path selection"
            ),
            operations=[
                "execute_tot",
                "analyze_tot_complexity",
                "should_activate",
                "format_reasoning_output",
            ],
            dependencies=[],
            enabled=True,
            model_required=False,
        )

    def initialize(self) -> bool:
        """Initialize dependent modules"""
        try:
            # Lazy load complexity detector (optional)
            try:
                self._complexity_detector = ModuleRegistry.get_module(
                    "complexity_detector"
                )
            except Exception as e:
                logger.debug(
                    "Optional dependency 'complexity_detector' unavailable for tree_of_thought",
                    exc_info=True,
                    extra={"module_name": "tree_of_thought", "error_type": type(e).__name__},
                )

            # Load search engine
            self._search_engine = ModuleRegistry.get_module("tot_search_engine")
            if not self._search_engine:
                # Try to discover modules if not found
                ModuleRegistry.discover_modules()
                self._search_engine = ModuleRegistry.get_module("tot_search_engine")

            # Lazy load cognitive generator
            self._cognitive_generator = ModuleRegistry.get_module(
                "cognitive_generator"
            )

            # Lazy load memory graph (optional)
            try:
                self._memory_graph = ModuleRegistry.get_module("memory_graph")
            except Exception as e:
                logger.debug(
                    "Optional dependency 'memory_graph' unavailable for tree_of_thought",
                    exc_info=True,
                    extra={"module_name": "tree_of_thought", "error_type": type(e).__name__},
                )

            return True
        except Exception as e:
            logger.debug(
                "Failed to initialize tree_of_thought dependencies",
                exc_info=True,
                extra={"module_name": "tree_of_thought", "error_type": type(e).__name__},
            )
            return False

    def execute(self, operation: str, params: dict[str, Any]) -> dict[str, Any]:
        """
        Execute Tree-of-Thought operations.

        Supported operations:
        - execute_tot: Full ToT execution
        - analyze_tot_complexity: Complexity analysis
        - should_activate: Activation decision
        - format_reasoning_output: Format path as text
        """
        if operation == "execute_tot":
            return self._execute_tot(params)
        elif operation == "analyze_tot_complexity":
            return self._analyze_tot_complexity(params)
        elif operation == "should_activate":
            return self._should_activate(params)
        elif operation == "format_reasoning_output":
            return self._format_reasoning_output(params)
        else:
            raise InvalidParameterError(
                parameter="operation",
                value=operation,
                reason="Unknown operation for tree_of_thought",
            )

    def _execute_tot(self, params: dict[str, Any]) -> dict[str, Any]:
        """
        Execute full Tree-of-Thought reasoning process.

        Args:
            params: Dictionary with:
                - query (str): The query to reason about
                - context (str, optional): Additional context
                - configuration (dict, optional): ToT configuration
                - session_id (str, optional): Session identifier

        Returns:
            Dictionary with ToTResult data
        """
        if not self._search_engine:
            self.initialize()
            if not self._search_engine:
                raise ModuleOperationError(
                    module_name="tree_of_thought",
                    operation="execute_tot",
                    reason="Search engine module not available (tot_search_engine)",
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

        # Step 3: Analyze complexity to confirm ToT is appropriate
        complexity_score = self._analyze_tot_complexity_internal(
            query, combined_context
        )

        if not complexity_score.get("requires_tot", False):
            logger.info(
                "ToT complexity analysis suggests ToT may not be needed; continuing because ToT was requested",
                extra={"module_name": "tree_of_thought"},
            )

        # Step 4: Execute search
        search_result_dict: dict[str, Any]
        try:
            search_result_dict = self._search_engine.execute(
                "search",
                {
                    "query": query,
                    "context": combined_context,
                    "configuration": config.to_dict(),
                    "session_id": session_id,
                },
            )
        except Exception as e:
            logger.debug(
                "ToT search failed",
                exc_info=True,
                extra={"module_name": "tree_of_thought", "error_type": type(e).__name__},
            )
            raise

        search_result = ToTSearchResult.from_dict(search_result_dict)

        # Step 5: Store best path nodes in memory (optional)
        if self._memory_graph:
            for node in search_result.best_path:
                try:
                    self._memory_graph.execute(
                        "store_memory",
                        {
                            "content": node.thought,
                            "type": "tot_reasoning_step",
                            "metadata": {
                                "node_id": node.id,
                                "depth": str(node.depth),
                                "evaluation_score": str(
                                    node.evaluation_score or 0.5
                                ),
                            },
                            "importance": node.evaluation_score or 0.5,
                            "tags": ["tot", "reasoning"],
                            "keywords": self._extract_keywords(node.thought),
                        },
                    )
                except Exception:
                    pass  # Memory storage is optional

        # Step 6: Convert search result to ToTResult
        result = ToTResult.from_search_result(search_result)

        logger.info(
            "ToT execution completed",
            extra={
                "module_name": "tree_of_thought",
                "steps": int(len(result.path)),
                "confidence": round(float(result.confidence), 6),
                "latency_s": round(float(result.total_latency), 6),
            },
        )

        return result.to_dict()

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
            Dictionary with ToT complexity score data
        """
        query = params.get("query", "")
        if not isinstance(query, str) or not query.strip():
            raise InvalidParameterError(
                parameter="query",
                value=str(query),
                reason="query parameter is required and must be a non-empty string",
            )

        context = params.get("context")
        return self._analyze_tot_complexity_internal(query, context)

    def _analyze_tot_complexity_internal(
        self, query: str, context: str | None
    ) -> dict[str, Any]:
        """Internal ToT complexity analysis"""
        if self._complexity_detector:
            try:
                return self._complexity_detector.execute(
                    "analyze_tot_complexity",
                    {
                        "query": query,
                        "context": context,
                    },
                )
            except Exception:
                pass

        # Fallback: simple heuristic
        query_length = len(query)
        context_length = len(context) if context else 0
        total_length = query_length + context_length

        # Simple heuristics for complexity
        requires_cot = total_length > 100
        requires_tot = total_length > 300 or query.count("?") > 1

        complexity_score = min(1.0, total_length / 500.0)

        return {
            "score": complexity_score,
            "requires_tot": requires_tot,
            "requires_cot": requires_cot,
            "factors": [
                {
                    "name": "query_length",
                    "contribution": min(0.5, query_length / 200.0),
                    "description": f"Query length: {query_length} characters",
                },
                {
                    "name": "context_length",
                    "contribution": min(0.3, context_length / 300.0),
                    "description": f"Context length: {context_length} characters",
                },
            ],
            "estimated_timeout_multiplier": 1.0 + (complexity_score * 2.0),
        }

    def _should_activate(self, params: dict[str, Any]) -> dict[str, Any]:
        """
        Determine if ToT should be activated.

        Args:
            params: Dictionary with:
                - query (str): The query to analyze
                - context (str, optional): Additional context

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

        context = params.get("context")

        if not self._complexity_detector:
            self.initialize()

        if self._complexity_detector:
            try:
                result = self._complexity_detector.execute(
                    "should_use_tot",
                    {
                        "query": query,
                        "context": context,
                    },
                )
                return {"should_activate": result.get("should_use", False)}
            except Exception:
                pass

        # Fallback
        complexity = self._analyze_tot_complexity_internal(query, context)
        return {"should_activate": complexity.get("requires_tot", False)}

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
        path = [ToTThoughtNode.from_dict(n) for n in path_data]
        output = self._format_reasoning_output_internal(path)

        return {"formatted_output": output}

    def _format_reasoning_output_internal(
        self, path: list[ToTThoughtNode]
    ) -> str:
        """Internal formatting"""
        output_lines: list[str] = []

        for i, node in enumerate(path):
            output_lines.append(f"Depth {node.depth}: {node.thought}")

            if node.evaluation_score is not None:
                output_lines.append(
                    f"Evaluation Score: {node.evaluation_score:.2f}"
                )

            if i < len(path) - 1:
                output_lines.append("")  # Blank line between steps

        return "\n".join(output_lines)

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

