"""
Optimization Helpers - Batch execution and performance utilities
Provides batch execution support for multiple module operations
"""

from typing import List, Dict, Any, Optional
import sys
from pathlib import Path

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent))

from module_registry import ModuleRegistry


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
            results.append({"success": False, "error": str(e)})

    return results


def get_module_load_status() -> Dict[str, bool]:
    """Get status of which modules are loaded"""
    # This would require tracking in ModuleRegistry
    # For now, return empty dict
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
        except:
            results[module_name] = False

    return results
