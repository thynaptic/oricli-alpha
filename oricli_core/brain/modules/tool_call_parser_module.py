from __future__ import annotations
"""
Tool Call Parser Module Wrapper
"""

from typing import Dict, Any
from oricli_core.brain.base_module import BaseBrainModule, ModuleMetadata
from oricli_core.brain.modules.tool_call_parser import ToolCallParser

class ToolCallParserModule(BaseBrainModule):
    """Module wrapper for ToolCallParser"""

    def __init__(self):
        super().__init__()
        self.parser = ToolCallParser()

    @property
    def metadata(self) -> ModuleMetadata:
        return ModuleMetadata(
            name="tool_call_parser_module",
            version="1.0.0",
            description="Module wrapper for ToolCallParser",
            operations=["parse"],
            dependencies=[],
            model_required=False,
        )

    def execute(self, operation: str, params: Dict[str, Any]) -> Dict[str, Any]:
        if operation == "parse":
            text = params.get("text", "")
            return {"success": True, "calls": self.parser.parse_from_text(text)}
        return {"success": False, "error": f"Unknown operation: {operation}"}
