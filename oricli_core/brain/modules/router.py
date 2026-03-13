from __future__ import annotations
"""Router module.

This module exposes routing utilities implemented in `cognitive_generator` so other
parts of the system can call them without reaching into private helpers.
"""

from typing import Any, Dict, List, Tuple
import sys

from oricli_core.brain.base_module import BaseBrainModule, ModuleMetadata
from oricli_core.exceptions import InvalidParameterError


class RouterModule(BaseBrainModule):
    """Routes requests to appropriate cognitive modules based on intent."""

    def __init__(self):
        self._module_registry = None

    @property
    def metadata(self) -> ModuleMetadata:
        return ModuleMetadata(
            name="router",
            version="1.0.0",
            description="Routes requests to appropriate cognitive modules based on intent",
            operations=[
                "select_modules_for_intent",
                "execute_module_chain",
                "learned_route",
                "update_routing_learning",
                "get_routing_statistics",
                "get_router_state",
                "discover_modules_for_intent",
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
                from oricli_core.brain.registry import ModuleRegistry

                self._module_registry = ModuleRegistry
            except ImportError:
                print("[RouterModule] ModuleRegistry not available", file=sys.stderr)
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

        if operation == "select_modules_for_intent":
            input_text = params.get("input") or params.get("text") or params.get("query") or ""
            context = params.get("context", "") or ""
            intent_info = params.get("intent_info")
            if not isinstance(intent_info, dict):
                intent_info = cg._detect_intent(str(input_text), str(context))
            chain = cg._select_modules_for_intent(intent_info)
            # Ensure JSON-friendly structure.
            chain_list = [[m, op] for (m, op) in chain]
            return {"success": True, "intent_info": intent_info, "module_chain": chain_list}

        if operation == "execute_module_chain":
            chain_raw = params.get("modules") or params.get("module_chain") or []
            chain = self._coerce_module_chain(chain_raw)
            result = cg._execute_module_chain(chain, params)
            return {"success": True, "result": result}

        if operation == "learned_route":
            input_text = params.get("input") or params.get("text") or params.get("query") or ""
            context = params.get("context", "") or ""
            return {"success": True, "route": cg._learned_route(str(input_text), str(context))}

        if operation == "update_routing_learning":
            chain = self._coerce_module_chain(params.get("module_chain") or params.get("modules") or [])
            success = bool(params.get("success", False))
            confidence = float(params.get("confidence", 0.0) or 0.0)
            cg._update_routing_learning(chain, success, confidence)
            return {"success": True}

        if operation == "get_routing_statistics":
            return {"success": True, "statistics": cg.get_routing_statistics()}

        if operation == "get_router_state":
            return {"success": True, "state": cg.get_router_state()}

        if operation == "discover_modules_for_intent":
            intent = str(params.get("intent") or "general")
            query_text = str(params.get("query") or params.get("input") or "")
            return {
                "success": True,
                "modules": cg._discover_modules_for_intent(intent, query_text),
            }

        raise InvalidParameterError(
            parameter="operation",
            value=str(operation),
            reason="Unknown operation for router",
        )
