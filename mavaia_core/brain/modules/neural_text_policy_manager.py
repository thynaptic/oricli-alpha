from __future__ import annotations
"""Neural text policy manager.

Exposes adaptive policy helpers implemented inside `neural_text_generator`.
"""

from typing import Any, Dict
import sys

from mavaia_core.brain.base_module import BaseBrainModule, ModuleMetadata
from mavaia_core.exceptions import InvalidParameterError


class NeuralTextPolicyManagerModule(BaseBrainModule):
    """Manages adaptive policies for neural text generation."""

    def __init__(self):
        self._module_registry = None

    @property
    def metadata(self) -> ModuleMetadata:
        return ModuleMetadata(
            name="neural_text_policy_manager",
            version="1.0.0",
            description="Manages adaptive policies for neural text generation",
            operations=[
                "load_adaptive_policies",
                "save_adaptive_policies",
                "get_adaptive_policy",
                "apply_adaptive_policy",
                "save_successful_policy",
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
                print("[NeuralTextPolicyManagerModule] ModuleRegistry not available", file=sys.stderr)
                self._module_registry = None

    def _get_neural_text_generator(self):
        self._init_module_registry()
        if not self._module_registry:
            return None
        return self._module_registry.get_module("neural_text_generator")

    def execute(self, operation: str, params: Dict[str, Any]) -> Dict[str, Any]:
        ntg = self._get_neural_text_generator()
        if not ntg:
            return {"success": False, "error": "neural_text_generator module unavailable"}

        if operation == "load_adaptive_policies":
            return {"success": True, "policies": ntg._load_adaptive_policies()}

        if operation == "save_adaptive_policies":
            policies = params.get("policies")
            if not isinstance(policies, dict):
                return {"success": False, "error": "policies must be a dict"}
            ok = ntg._save_adaptive_policies(policies)
            return {"success": bool(ok)}

        if operation == "get_adaptive_policy":
            device = str(params.get("device") or "cpu")
            model_type = str(params.get("model_type") or "both")
            source = params.get("source") or "unknown"
            data_size = params.get("data_size")
            categories = params.get("categories")
            policy = ntg._get_adaptive_policy(device, model_type, source, data_size, categories)
            return {"success": True, "policy": policy}

        if operation == "apply_adaptive_policy":
            base_params = params.get("params") or {}
            policy = params.get("policy") or {}
            if not isinstance(base_params, dict) or not isinstance(policy, dict):
                return {"success": False, "error": "params and policy must be dicts"}
            merged = ntg._apply_adaptive_policy(base_params, policy)
            return {"success": True, "params": merged}

        if operation == "save_successful_policy":
            device = str(params.get("device") or "cpu")
            model_type = str(params.get("model_type") or "both")
            source = params.get("source") or "unknown"
            data_size = params.get("data_size")
            categories = params.get("categories")
            training_params = params.get("training_params") or {}
            training_result = params.get("training_result") or {}
            if not isinstance(training_params, dict) or not isinstance(training_result, dict):
                return {"success": False, "error": "training_params and training_result must be dicts"}
            ok = ntg._save_successful_policy(
                device,
                model_type,
                source,
                data_size,
                categories if isinstance(categories, list) else None,
                training_params,
                training_result,
            )
            return {"success": bool(ok)}

        raise InvalidParameterError(
            parameter="operation",
            value=str(operation),
            reason="Unknown operation for neural_text_policy_manager",
        )
