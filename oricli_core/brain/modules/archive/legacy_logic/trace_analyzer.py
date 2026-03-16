from __future__ import annotations
"""Trace analyzer module.

Delegates to `cognitive_generator` trace graph builders and confidence utilities.
"""

from typing import Any, Dict, List, Tuple
import sys

from oricli_core.brain.base_module import BaseBrainModule, ModuleMetadata
from oricli_core.exceptions import InvalidParameterError


class TraceAnalyzerModule(BaseBrainModule):
    """Analyzes trace graphs for cognitive processing."""

    def __init__(self):
        self._module_registry = None

    @property
    def metadata(self) -> ModuleMetadata:
        return ModuleMetadata(
            name="trace_analyzer",
            version="1.0.0",
            description="Analyzes trace graphs for cognitive processing",
            operations=["build_trace_graph", "get_trace_graphs", "calculate_structural_confidence"],
            dependencies=[],
            model_required=False,
        )

    def initialize(self) -> bool:
        self._init_module_registry()
        return True

    def _init_module_registry(self) -> None:
        if self._module_registry is None:
            try:
                from oricli_core.brain.registry import ModuleRegistry

                self._module_registry = ModuleRegistry
            except ImportError:
                print("[TraceAnalyzerModule] ModuleRegistry not available", file=sys.stderr)
                self._module_registry = None

    def _get_cognitive_generator(self):
        self._init_module_registry()
        if not self._module_registry:
            return None
        return self._module_registry.get_module("cognitive_generator")

    @staticmethod
    def _coerce_module_chain(chain: Any) -> List[Tuple[str, str]]:
        if not chain:
            return []
        out: List[Tuple[str, str]] = []
        for item in chain:
            if isinstance(item, tuple) and len(item) == 2:
                out.append((str(item[0]), str(item[1])))
            elif isinstance(item, list) and len(item) == 2:
                out.append((str(item[0]), str(item[1])))
            elif isinstance(item, dict):
                mod = item.get("module") or item.get("module_name")
                op = item.get("operation")
                if mod and op:
                    out.append((str(mod), str(op)))
        return out

    def execute(self, operation: str, params: Dict[str, Any]) -> Dict[str, Any]:
        cg = self._get_cognitive_generator()
        if not cg:
            return {"success": False, "error": "cognitive_generator module unavailable"}

        if operation == "build_trace_graph":
            input_text = str(params.get("input") or params.get("query") or "")
            intent_info = params.get("intent_info") or {"intent": "general"}
            module_chain = self._coerce_module_chain(params.get("module_chain") or params.get("modules") or [])
            execution_results = params.get("execution_results") or params.get("results") or {}
            verification_result = params.get("verification_result") or params.get("verification") or {}
            final_output = str(params.get("final_output") or params.get("output") or params.get("text") or "")
            trace = cg._build_trace_graph(
                input_text,
                intent_info if isinstance(intent_info, dict) else {"intent": "general"},
                module_chain,
                execution_results if isinstance(execution_results, dict) else {},
                verification_result if isinstance(verification_result, dict) else {},
                final_output,
            )
            return {"success": True, "trace_graph": trace}

        if operation == "get_trace_graphs":
            limit = int(params.get("limit", 10) or 10)
            return {"success": True, **cg.get_trace_graphs(limit)}

        if operation == "calculate_structural_confidence":
            output = str(params.get("output") or params.get("text") or "")
            intent_info = params.get("intent_info") or {"intent": "general"}
            verification_result = params.get("verification_result") or params.get("verification") or {}
            module_chain = self._coerce_module_chain(params.get("module_chain") or params.get("modules") or [])
            conf = cg._calculate_structural_confidence(
                output,
                intent_info if isinstance(intent_info, dict) else {"intent": "general"},
                verification_result if isinstance(verification_result, dict) else {},
                module_chain,
            )
            return {"success": True, "structural_confidence": conf}

        raise InvalidParameterError(
            parameter="operation",
            value=str(operation),
            reason="Unknown operation for trace_analyzer",
        )
