from __future__ import annotations
from mavaia_core.brain.base_module import BaseBrainModule, ModuleMetadata
from typing import Any

class ModuleExample(BaseBrainModule):
    """Example brain module providing simple text utilities."""

    @property
    def metadata(self) -> ModuleMetadata:
        return ModuleMetadata(
            name="module_example",
            version="0.1.0",
            description="Example module with simple text operations: echo, word_count, reverse",
            operations=["echo", "word_count", "reverse"],
            dependencies=[],
            enabled=True,
            model_required=False,
        )

    def initialize(self) -> bool:
        """Initialize resources if needed."""
        self._initialized = True
        return True

    def validate_params(self, operation: str, params: dict[str, Any]) -> bool:
        """Validate params for supported operations."""
        if operation in {"echo", "word_count", "reverse"}:
            return isinstance(params.get("text"), str)
        return True

    def execute(self, operation: str, params: dict[str, Any]) -> dict[str, Any]:
        """Execute a supported operation and return a result dict."""
        if not getattr(self, "_initialized", False):
            self.initialize()

        if not self.validate_params(operation, params):
            raise ValueError(f"Invalid parameters for operation: {operation}")

        text = params.get("text", "")

        if operation == "echo":
            return {"result": text}
        elif operation == "word_count":
            words = text.split()
            return {"result": len(words), "words": words}
        elif operation == "reverse":
            return {"result": text[::-1]}
        else:
            raise ValueError(f"Unknown operation: {operation}")

    def cleanup(self) -> None:
        """Cleanup any allocated resources."""
        if hasattr(self, "_initialized"):
            del self._initialized