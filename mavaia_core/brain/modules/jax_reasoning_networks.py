from __future__ import annotations
"""JAX reasoning networks module.

This module is intentionally lightweight: it performs lazy availability checks so
the rest of the system can remain functional on hosts without JAX installed.
"""

from typing import Any, Dict
import sys

from mavaia_core.brain.base_module import BaseBrainModule, ModuleMetadata
from mavaia_core.exceptions import InvalidParameterError


def _check_jax() -> tuple[bool, str | None]:
    try:
        import jax  # noqa: F401
        import jaxlib  # noqa: F401
        return True, None
    except Exception as e:
        return False, str(e)


class JaxReasoningNetworksModule(BaseBrainModule):
    """JAX-based reasoning networks for high-performance cognitive processing."""

    def __init__(self):
        self._module_registry = None

    @property
    def metadata(self) -> ModuleMetadata:
        return ModuleMetadata(
            name="jax_reasoning_networks",
            version="1.0.0",
            description="JAX-based reasoning networks for high-performance cognitive processing",
            operations=["check_jax_available", "ensure_jax_available", "create_jax_network"],
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
                print("[JaxReasoningNetworksModule] ModuleRegistry not available", file=sys.stderr)
                self._module_registry = None

    def execute(self, operation: str, params: Dict[str, Any]) -> Dict[str, Any]:
        if operation == "check_jax_available":
            ok, err = _check_jax()
            return {"success": True, "available": ok, "error": err}

        if operation == "ensure_jax_available":
            ok, err = _check_jax()
            if ok:
                return {"success": True, "available": True}
            return {
                "success": False,
                "available": False,
                "error": f"JAX not available: {err}",
            }

        if operation == "create_jax_network":
            ok, err = _check_jax()
            if not ok:
                return {
                    "success": False,
                    "error": f"JAX not available: {err}",
                }
            # Keep this JSON-friendly: return a declarative spec rather than live objects.
            spec = {
                "type": params.get("type") or "mlp",
                "hidden_sizes": params.get("hidden_sizes") or [128, 128],
                "activation": params.get("activation") or "relu",
                "output_size": params.get("output_size") or None,
            }
            return {"success": True, "network_spec": spec}

        raise InvalidParameterError(
            parameter="operation",
            value=str(operation),
            reason="Unknown operation for jax_reasoning_networks",
        )
