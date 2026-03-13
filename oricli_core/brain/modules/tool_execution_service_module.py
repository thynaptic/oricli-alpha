from __future__ import annotations
"""
Tool Execution Service Module Wrapper
"""

from typing import Dict, Any
from oricli_core.brain.base_module import BaseBrainModule, ModuleMetadata
from oricli_core.brain.modules.tool_execution_service import ToolExecutionService

class ToolExecutionServiceModule(BaseBrainModule):
    """Module wrapper for ToolExecutionService"""

    def __init__(self):
        super().__init__()
        self.service = ToolExecutionService()

    @property
    def metadata(self) -> ModuleMetadata:
        return ModuleMetadata(
            name="tool_execution_service_module",
            version="1.0.0",
            description="Module wrapper for ToolExecutionService",
            operations=["execute_tool"],
            dependencies=[],
            model_required=False,
        )

    def execute(self, operation: str, params: Dict[str, Any]) -> Dict[str, Any]:
        if operation == "execute_tool":
            return {"success": False, "error": "Not implemented in wrapper"}
        return {"success": False, "error": f"Unknown operation: {operation}"}
