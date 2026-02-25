from __future__ import annotations
"""
Optimization Helpers - Batch execution and performance utilities
Provides batch execution support for multiple module operations
"""

from typing import List, Dict, Any
import logging

from mavaia_core.brain.registry import ModuleRegistry

logger = logging.getLogger(__name__)


def execute_batch_operations(operations: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """
    Execute multiple module operations in batch to reduce Python process overhead

    Args:
        operations: List of operation dicts with keys:
            - module: Module name
            - operation: Operation name
            - params: Operation parameters

    Returns:
        List of results corresponding to input operations
    """
    results = []

    for op in operations:
        module_name = op.get("module")
        operation_name = op.get("operation")
        params = op.get("params", {})

        if not module_name or not operation_name:
            results.append({"success": False, "error": "Missing module or operation"})
            continue

        try:
            module = ModuleRegistry.get_module(module_name)
            if not module:
                results.append(
                    {"success": False, "error": f"Module '{module_name}' not found"}
                )
                continue

            result = module.execute(operation_name, params)
            results.append({"success": True, "result": result})
        except Exception as e:
            logger.debug(
                "Batch operation failed",
                exc_info=True,
                extra={
                    "module_name": "optimization_helpers",
                    "target_module": str(module_name),
                    "target_operation": str(operation_name),
                    "error_type": type(e).__name__,
                },
            )
            results.append(
                {
                    "success": False,
                    "error": "Batch operation failed",
                    "module": module_name,
                    "operation": operation_name,
                }
            )

    return results


def get_module_load_status() -> Dict[str, bool]:
    """Get status of which modules are loaded"""
    # Best-effort: "loaded" means instantiated in the registry cache.
    try:
        instances = getattr(ModuleRegistry, "_instances", {})
        if isinstance(instances, dict):
            return {name: True for name in instances.keys()}
    except Exception as e:
        logger.debug(
            "Failed to read ModuleRegistry instance cache",
            exc_info=True,
            extra={"module_name": "optimization_helpers", "error_type": type(e).__name__},
        )
    return {}


def preload_modules(module_names: List[str]) -> Dict[str, bool]:
    """
    Pre-load specified modules

    Args:
        module_names: List of module names to preload

    Returns:
        Dict mapping module names to load success status
    """
    results = {}

    for module_name in module_names:
        try:
            module = ModuleRegistry.get_module(module_name)
            results[module_name] = module is not None
        except Exception as e:
            logger.debug(
                "Module preload failed",
                exc_info=True,
                extra={
                    "module_name": "optimization_helpers",
                    "target_module": str(module_name),
                    "error_type": type(e).__name__,
                },
            )
            results[module_name] = False

    return results
