from __future__ import annotations
"""
Unified Interface Module - Single API layer for all cognitive operations
Standardized input/output, auto-routing, auto-context merging,
multi-module orchestration
"""

from pathlib import Path
from typing import Any, Dict, List, Optional
import logging

from oricli_core.brain.base_module import BaseBrainModule, ModuleMetadata
from oricli_core.brain.registry import ModuleRegistry
from oricli_core.exceptions import InvalidParameterError

logger = logging.getLogger(__name__)


class UnifiedInterfaceModule(BaseBrainModule):
    """Unified interface for all cognitive operations"""

    def __init__(self):
        super().__init__()
        self.module_registry = None
        self._initialize_module_registry()

    def _initialize_module_registry(self) -> None:
        """Initialize module registry for routing"""
        try:
            self.module_registry = ModuleRegistry
        except ImportError:
            # Fallback if registry not available
            self.module_registry = None

    @property
    def metadata(self) -> ModuleMetadata:
        return ModuleMetadata(
            name="unified_interface",
            version="1.0.0",
            description=(
                "Unified API layer: single entry point, standardized input/output, "
                "auto-routing, auto-context merging, multi-module orchestration"
            ),
            operations=[
                "process_request",
                "route_request",
                "merge_context",
                "orchestrate_modules",
                "format_output",
            ],
            dependencies=[],
            model_required=False,
        )

    def initialize(self) -> bool:
        """Initialize the module"""
        return True

    def execute(self, operation: str, params: Dict[str, Any]) -> Dict[str, Any]:
        """Execute a unified interface operation"""
        if operation == "process_request":
            request = params.get("request", {})
            return self.process_request(request)

        elif operation == "route_request":
            request = params.get("request", {})
            return self.route_request(request)

        elif operation == "merge_context":
            contexts = params.get("contexts", [])
            return self.merge_context(contexts)

        elif operation == "orchestrate_modules":
            request = params.get("request", {})
            modules = params.get("modules", [])
            return self.orchestrate_modules(request, modules)

        elif operation == "format_output":
            result = params.get("result", {})
            metadata = params.get("metadata", {})
            return self.format_output(result, metadata)

        else:
            raise InvalidParameterError(
                parameter="operation",
                value=operation,
                reason="Unknown operation for unified_interface",
            )

    def process_request(self, request: Dict[str, Any]) -> Dict[str, Any]:
        """Process a request through the unified interface"""
        if not request:
            return {
                "success": False,
                "error": "Empty request",
                "result": None,
            }

        # Extract request components
        input_text = request.get("input", "")
        intent = request.get("intent")
        context = request.get("context", {})
        modules_requested = request.get("modules", [])

        # Normalize input if needed
        if "intent_correction" in modules_requested or not modules_requested:
            try:
                intent_module = self._get_module("intent_correction")
                if intent_module:
                    normalize_result = intent_module.execute(
                        "normalize_intent",
                        {"text": input_text, "context": str(context)},
                    )
                    input_text = normalize_result.get("normalized", input_text)
            except Exception:
                pass  # Continue with original input

        # Route request
        routing_result = self.route_request(request)

        # Process through routed modules
        results = {}
        for module_name, operation in routing_result.get("routed_modules", []):
            try:
                module = self._get_module(module_name)
                if module:
                    module_params = {
                        "text": input_text,
                        "query": input_text,
                        "input": input_text,
                        "context": context,
                        **request.get("params", {}),
                    }

                    # Add module-specific params
                    if module_name == "emotional_inference":
                        module_params["text"] = input_text
                    elif module_name == "reasoning":
                        module_params["query"] = input_text
                    elif module_name == "state_manager":
                        module_params["state_type"] = request.get("state_type", "conversation")
                        module_params["state_id"] = request.get("state_id")

                    result = module.execute(operation, module_params)
                    results[module_name] = result
            except Exception as e:
                results[module_name] = {"error": str(e)}

        # Merge context from results
        merged_context = self.merge_context(
            [context] + [r for r in results.values() if isinstance(r, dict)]
        )

        # Format output
        output = self.format_output(results, {"request": request, "context": merged_context})

        return output

    def route_request(self, request: Dict[str, Any]) -> Dict[str, Any]:
        """Automatically route request to appropriate modules"""
        if not request:
            return {
                "routed_modules": [],
                "routing_strategy": "none",
            }

        input_text = request.get("input", "").lower()
        intent = request.get("intent")
        modules_requested = request.get("modules", [])

        routed_modules = []

        # If modules explicitly requested, use those
        if modules_requested:
            for module_name in modules_requested:
                operation = self._get_default_operation(module_name)
                if operation:
                    routed_modules.append((module_name, operation))
        else:
            # Auto-route based on input analysis
            routing_strategy = self._determine_routing_strategy(input_text, intent)

            for module_name, operation in routing_strategy:
                routed_modules.append((module_name, operation))

        return {
            "routed_modules": routed_modules,
            "routing_strategy": "explicit" if modules_requested else "auto",
            "module_count": len(routed_modules),
        }

    def _determine_routing_strategy(
        self, input_text: str, intent: Optional[str]
    ) -> List[tuple[str, str]]:
        """Determine which modules to route to based on input"""
        strategy = []

        # Always include intent correction for normalization
        strategy.append(("intent_correction", "normalize_intent"))

        # Emotional detection
        emotional_keywords = [
            "feel", "emotion", "sad", "happy", "angry", "excited",
            "worried", "anxious", "stressed", "tired",
        ]
        if any(keyword in input_text for keyword in emotional_keywords):
            strategy.append(("emotional_inference", "infer_emotion"))

        # Reasoning
        reasoning_keywords = [
            "analyze", "reason", "why", "how", "explain", "compare",
            "solve", "calculate", "determine",
        ]
        if any(keyword in input_text for keyword in reasoning_keywords):
            strategy.append(("reasoning", "reason"))

        # State management
        state_keywords = ["state", "status", "current", "update", "track"]
        if any(keyword in input_text for keyword in state_keywords):
            strategy.append(("state_manager", "get_state"))

        # Memory
        memory_keywords = ["remember", "recall", "memory", "forgot", "learn"]
        if any(keyword in input_text for keyword in memory_keywords):
            strategy.append(("memory_dynamics", "replay_memories"))

        # Document operations
        doc_keywords = ["document", "file", "read", "analyze document"]
        if any(keyword in input_text for keyword in doc_keywords):
            strategy.append(("document_orchestration", "route_multi_document"))

        # Default: if no specific routing, use reasoning
        if len(strategy) == 1:  # Only intent correction
            strategy.append(("reasoning", "reason"))

        return strategy

    def _get_default_operation(self, module_name: str) -> Optional[str]:
        """Get default operation for a module"""
        defaults = {
            "emotional_inference": "infer_emotion",
            "reasoning": "reason",
            "intent_correction": "normalize_intent",
            "state_manager": "get_state",
            "memory_dynamics": "score_importance",
            "document_orchestration": "route_multi_document",
        }
        return defaults.get(module_name)

    def merge_context(
        self, contexts: List[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """Merge context from multiple sources"""
        if not contexts:
            return {}

        merged = {}

        for context in contexts:
            if not isinstance(context, dict):
                continue

            for key, value in context.items():
                if key not in merged:
                    merged[key] = value
                elif isinstance(value, list) and isinstance(merged.get(key), list):
                    # Merge lists (avoid duplicates)
                    merged[key] = list(set(merged[key] + value))
                elif isinstance(value, dict) and isinstance(merged.get(key), dict):
                    # Merge dicts recursively
                    merged[key] = {**merged[key], **value}
                else:
                    # Prefer newer value (last one wins)
                    merged[key] = value

        return merged

    def orchestrate_modules(
        self, request: Dict[str, Any], modules: List[str]
    ) -> Dict[str, Any]:
        """Orchestrate multiple modules for complex tasks"""
        if not modules:
            return {
                "success": False,
                "error": "No modules specified",
                "results": {},
            }

        input_text = request.get("input", "")
        context = request.get("context", {})

        results = {}
        execution_order = []

        # Determine execution order based on dependencies
        execution_order = self._determine_execution_order(modules)

        # Execute modules in order
        accumulated_context = context.copy()

        for module_name in execution_order:
            try:
                module = self._get_module(module_name)
                if not module:
                    continue

                operation = self._get_default_operation(module_name)
                if not operation:
                    continue

                # Prepare params
                module_params = {
                    "text": input_text,
                    "query": input_text,
                    "input": input_text,
                    "context": accumulated_context,
                    **request.get("params", {}),
                }

                # Execute
                result = module.execute(operation, module_params)
                results[module_name] = result

                # Update accumulated context
                if isinstance(result, dict):
                    accumulated_context = self.merge_context([accumulated_context, result])

            except Exception as e:
                results[module_name] = {"error": str(e)}

        return {
            "success": True,
            "results": results,
            "execution_order": execution_order,
            "final_context": accumulated_context,
        }

    def _determine_execution_order(self, modules: List[str]) -> List[str]:
        """Determine optimal execution order for modules"""
        # Dependency order: intent -> emotional -> reasoning -> others
        order = []

        # Intent correction first
        if "intent_correction" in modules:
            order.append("intent_correction")
            modules = [m for m in modules if m != "intent_correction"]

        # Emotional inference early
        if "emotional_inference" in modules:
            order.append("emotional_inference")
            modules = [m for m in modules if m != "emotional_inference"]

        # State management
        if "state_manager" in modules:
            order.append("state_manager")
            modules = [m for m in modules if m != "state_manager"]

        # Reasoning
        if "reasoning" in modules:
            order.append("reasoning")
            modules = [m for m in modules if m != "reasoning"]

        # Memory
        if "memory_dynamics" in modules:
            order.append("memory_dynamics")
            modules = [m for m in modules if m != "memory_dynamics"]

        # Document orchestration
        if "document_orchestration" in modules:
            order.append("document_orchestration")
            modules = [m for m in modules if m != "document_orchestration"]

        # Add remaining modules
        order.extend(modules)

        return order

    def format_output(
        self, result: Dict[str, Any], metadata: Dict[str, Any] = None
    ) -> Dict[str, Any]:
        """Format output with standardized schema"""
        if metadata is None:
            metadata = {}

        # Standard output format
        output = {
            "success": True,
            "result": result,
            "metadata": {
                "timestamp": self._get_timestamp(),
                "modules_used": list(result.keys()) if isinstance(result, dict) else [],
                **metadata,
            },
        }

        # Check for errors
        if isinstance(result, dict):
            errors = [
                k for k, v in result.items()
                if isinstance(v, dict) and "error" in v
            ]
            if errors:
                output["success"] = False
                output["errors"] = errors

        return output

    def _get_module(self, module_name: str):
        """Get module instance from registry"""
        if not self.module_registry:
            return None

        try:
            return self.module_registry.get_module(module_name)
        except Exception:
            return None

    def _get_timestamp(self) -> str:
        """Get current timestamp as ISO string"""
        from datetime import datetime

        return datetime.now().isoformat()

    def validate_params(self, operation: str, params: Dict[str, Any]) -> bool:
        """Validate parameters for operations"""
        if operation == 'process_request' or operation == 'route_request' or operation == 'orchestrate_modules':
            return "request" in params
        elif operation == "merge_context":
            return "contexts" in params
        elif operation == "format_output":
            return "result" in params
        else:
            return True


# Module export
def create_module():
    return UnifiedInterfaceModule()

