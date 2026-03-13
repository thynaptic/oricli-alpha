from __future__ import annotations
"""
Tool Schema Generator Module Wrapper
"""

from typing import Dict, Any
from oricli_core.brain.base_module import BaseBrainModule, ModuleMetadata
from oricli_core.brain.modules.tool_schema_generator import ToolSchemaGenerator

class ToolSchemaGeneratorModule(BaseBrainModule):
    """Module wrapper for ToolSchemaGenerator"""

    def __init__(self):
        super().__init__()
        self.generator = ToolSchemaGenerator()

    @property
    def metadata(self) -> ModuleMetadata:
        return ModuleMetadata(
            name="tool_schema_generator_module",
            version="1.0.0",
            description="Module wrapper for ToolSchemaGenerator",
            operations=["generate"],
            dependencies=[],
            model_required=False,
        )

    def execute(self, operation: str, params: Dict[str, Any]) -> Dict[str, Any]:
        if operation == "generate":
            return {"success": False, "error": "Not implemented in wrapper"}
        return {"success": False, "error": f"Unknown operation: {operation}"}
