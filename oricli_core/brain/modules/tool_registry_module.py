from __future__ import annotations
"""
Tool Registry Module Wrapper
"""

from typing import Dict, Any
from oricli_core.brain.base_module import BaseBrainModule, ModuleMetadata
from oricli_core.brain.modules.tool_registry import tool_registry

class ToolRegistryModule(BaseBrainModule):
    """Module wrapper for ToolRegistry"""

    @property
    def metadata(self) -> ModuleMetadata:
        return ModuleMetadata(
            name="tool_registry_module",
            version="1.0.0",
            description="Module wrapper for ToolRegistry",
            operations=["list_tools"],
            dependencies=[],
            model_required=False,
        )

    def execute(self, operation: str, params: Dict[str, Any]) -> Dict[str, Any]:
        if operation == "list_tools":
            return {"success": True, "tools": [t for t in tool_registry.get_all_tools()]}
        return {"success": False, "error": f"Unknown operation: {operation}"}
