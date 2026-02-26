from __future__ import annotations
"""Thought builder module.

Delegates to `cognitive_generator` thought graph utilities.
"""

from typing import Any, Dict
import sys

from mavaia_core.brain.base_module import BaseBrainModule, ModuleMetadata
from mavaia_core.exceptions import InvalidParameterError


class ThoughtBuilderModule(BaseBrainModule):
    """Builds and manages thought graphs for cognitive processing."""

    def __init__(self):
        self._module_registry = None

    @property
    def metadata(self) -> ModuleMetadata:
        return ModuleMetadata(
            name="thought_builder",
            version="1.0.0",
            description="Builds and manages thought graphs for cognitive processing",
            operations=[
                "build_thought_graph",
                "select_best_thoughts",
                "extract_thoughts_from_mcts",
                "extract_thoughts_from_tree",
                "generate_thoughts_from_input",
            ],
            dependencies=[],
            model_required=False,
        )

    def initialize(self) -> bool:
        self._init_module_registry()
        return True

    def _init_module_registry(self) -> None:
        if self._module_registry is None:
            try:
                from mavaia_core.brain.registry import ModuleRegistry

                self._module_registry = ModuleRegistry
            except ImportError:
                print("[ThoughtBuilderModule] ModuleRegistry not available", file=sys.stderr)
                self._module_registry = None

    def _get_cognitive_generator(self):
        self._init_module_registry()
        if not self._module_registry:
            return None
        return self._module_registry.get_module("cognitive_generator")

    def execute(self, operation: str, params: Dict[str, Any]) -> Dict[str, Any]:
        cg = self._get_cognitive_generator()
        if not cg:
            return {"success": False, "error": "cognitive_generator module unavailable"}

        if operation == "build_thought_graph":
            input_text = params.get("input") or params.get("text") or params.get("query") or ""
            context = params.get("context") or ""
            return cg.build_thought_graph(str(input_text), str(context))

        if operation == "select_best_thoughts":
            thought_graph = params.get("thought_graph")
            max_thoughts = int(params.get("max_thoughts", 5) or 5)
            return cg.select_best_thoughts(thought_graph, max_thoughts)

        if operation == "extract_thoughts_from_mcts":
            mcts_result = params.get("mcts_result") or params.get("result") or {}
            return {"success": True, **cg._extract_thoughts_from_mcts(mcts_result)}

        if operation == "extract_thoughts_from_tree":
            tree = params.get("tree") or params.get("reasoning_tree") or params.get("result") or {}
            return {"success": True, **cg._extract_thoughts_from_tree(tree)}

        if operation == "generate_thoughts_from_input":
            input_text = params.get("input") or params.get("text") or params.get("query") or ""
            context = params.get("context") or ""
            latency_pressure = float(params.get("latency_pressure", 0.0) or 0.0)
            return {
                "success": True,
                "thoughts": cg._generate_thoughts_from_input(str(input_text), str(context), latency_pressure),
            }

        raise InvalidParameterError(
            parameter="operation",
            value=str(operation),
            reason="Unknown operation for thought_builder",
        )
