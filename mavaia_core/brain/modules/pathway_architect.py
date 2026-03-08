from __future__ import annotations
"""
Pathway Architect Module - Maps out dynamic cognitive DAGs for query execution.
Translates intent and mental state into a graph of module operations.
"""

from typing import List, Dict, Any, Optional
import logging

from mavaia_core.brain.base_module import BaseBrainModule, ModuleMetadata
from mavaia_core.exceptions import InvalidParameterError

logger = logging.getLogger(__name__)

class PathwayArchitectModule(BaseBrainModule):
    """Architects bespoke execution graphs for every query."""

    def __init__(self) -> None:
        super().__init__()

    @property
    def metadata(self) -> ModuleMetadata:
        return ModuleMetadata(
            name="pathway_architect",
            version="1.0.0",
            description="Generates dynamic execution DAGs for module orchestration",
            operations=["architect_graph"],
            dependencies=[],
            model_required=False,
        )

    def execute(self, operation: str, params: Dict[str, Any]) -> Dict[str, Any]:
        if operation != "architect_graph":
            raise InvalidParameterError(parameter="operation", value=operation, reason="Unsupported operation")

        intent_info = params.get("intent_info", {})
        query = params.get("query", "")
        vision_context = params.get("vision_context")
        audio_context = params.get("audio_context")
        
        graph = self._architect_graph(intent_info, query, vision_context, audio_context)
        
        return {
            "success": True,
            "graph": graph,
            "intent": intent_info.get("intent", "general")
        }

    def _architect_graph(self, intent_info: Dict[str, Any], query: str, vision_context: Optional[Dict] = None, audio_context: Optional[Dict] = None) -> Dict[str, Any]:
        intent = intent_info.get("intent", "general")
        
        # 1. CORE GRAPH TEMPLATES
        if intent == "search":
            graph = self._build_search_graph(query)
        elif intent == "code":
            graph = self._build_code_graph(query)
        elif intent == "math_logic":
            graph = self._build_math_graph(query)
        elif intent == "reasoning":
            graph = self._build_reasoning_graph(query)
        else:
            graph = self._build_general_graph(query)

        # 2. MULTI-MODAL INJECTION
        if vision_context:
            # Prepend vision encoding
            graph["nodes"].insert(0, {"id": "vision", "module": "vision_encoder", "operation": "encode_image", "params": vision_context})
            # Connect vision to synthesis/reasoning
            target = "synthesize" if "synthesize" in [n["id"] for n in graph["nodes"]] else graph["nodes"][-1]["id"]
            graph["edges"].append({"source": "vision", "target": target})

        if audio_context:
            # Prepend transcription
            graph["nodes"].insert(0, {"id": "audio", "module": "whisper_stt", "operation": "transcribe", "params": audio_context})
            # Audio feeds into everything
            for node in graph["nodes"][1:]:
                graph["edges"].append({"source": "audio", "target": node["id"]})

        return graph

    def _build_search_graph(self, query: str) -> Dict[str, Any]:
        return {
            "nodes": [
                {"id": "search", "module": "web_search", "operation": "search_web", "params": {"query": query}},
                {"id": "memory", "module": "memory_graph", "operation": "search", "params": {"query": query}},
                {"id": "rank", "module": "ranking_agent", "operation": "rank", "params": {"query": query}},
                {"id": "synthesize", "module": "synthesis_agent", "operation": "synthesize", "params": {"query": query}}
            ],
            "edges": [
                {"source": "search", "target": "rank"},
                {"source": "memory", "target": "rank"},
                {"source": "rank", "target": "synthesize"}
            ]
        }

    def _build_code_graph(self, query: str) -> Dict[str, Any]:
        return {
            "nodes": [
                {"id": "search_code", "module": "python_codebase_search", "operation": "search", "params": {"query": query}},
                {"id": "generate", "module": "reasoning_code_generator", "operation": "generate_code_reasoning", "params": {"requirements": query}},
                {"id": "verify", "module": "test_generation_reasoning", "operation": "generate_tests", "params": {}}
            ],
            "edges": [
                {"source": "search_code", "target": "generate"},
                {"source": "generate", "target": "verify"}
            ]
        }

    def _build_math_graph(self, query: str) -> Dict[str, Any]:
        # Math often benefits from symbolic solving first
        return {
            "nodes": [
                {"id": "solve_symbolic", "module": "reasoning", "operation": "reason", "params": {"query": query}},
                {"id": "verify_math", "module": "reasoning_verification_loop", "operation": "verify", "params": {}}
            ],
            "edges": [
                {"source": "solve_symbolic", "target": "verify_math"}
            ]
        }

    def _build_reasoning_graph(self, query: str) -> Dict[str, Any]:
        # Reasoning uses MCTS or CoT
        return {
            "nodes": [
                {"id": "thought_graph", "module": "tree_of_thought", "operation": "generate_thoughts", "params": {"input": query}},
                {"id": "mcts", "module": "mcts_reasoning", "operation": "execute_mcts", "params": {"query": query}},
                {"id": "synthesize", "module": "synthesis_agent", "operation": "synthesize", "params": {"query": query}}
            ],
            "edges": [
                {"source": "thought_graph", "target": "mcts"},
                {"source": "mcts", "target": "synthesize"}
            ]
        }

    def _build_general_graph(self, query: str) -> Dict[str, Any]:
        return {
            "nodes": [
                {"id": "core_reasoning", "module": "reasoning", "operation": "reason", "params": {"query": query}}
            ],
            "edges": []
        }
