from __future__ import annotations
"""
Adapter Router Module Wrapper
"""

from typing import Dict, Any
from oricli_core.brain.base_module import BaseBrainModule, ModuleMetadata
from oricli_core.exceptions import InvalidParameterError

class AdapterRouterModule(BaseBrainModule):
    """Module wrapper for AdapterRouter"""

    @property
    def metadata(self) -> ModuleMetadata:
        return ModuleMetadata(
            name="adapter_router_module",
            version="1.0.0",
            description="Module wrapper for AdapterRouter",
            operations=["noop"],
            dependencies=[],
            model_required=False,
        )

    def execute(self, operation: str, params: Dict[str, Any]) -> Dict[str, Any]:
        if operation == "noop":
            return {
                "success": True,
                "status": "ok",
                "module": self.metadata.name,
                "operation": operation,
            }
        raise InvalidParameterError(
            parameter="operation",
            value=str(operation),
            reason="Unsupported operation",
        )
