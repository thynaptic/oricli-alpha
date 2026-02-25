from __future__ import annotations
"""
Base Module Interface - All intelligence modules must inherit from this
Enables plug-and-play architecture for easy module addition/removal
"""

from abc import ABC, abstractmethod
from typing import Any
from dataclasses import dataclass


@dataclass
class ModuleMetadata:
    """Metadata describing a brain module"""

    name: str  # Module identifier (e.g., "reasoning", "embeddings")
    version: str  # Module version
    description: str  # What this module does
    operations: list[str]  # List of operations this module supports
    dependencies: list[str]  # Required Python packages
    enabled: bool = True  # Can be disabled via config
    model_required: bool = False  # Whether this module needs a HuggingFace model


class BaseBrainModule(ABC):
    """Base class that all intelligence modules must implement"""

    @property
    @abstractmethod
    def metadata(self) -> ModuleMetadata:
        """Return metadata about this module"""
        pass

    @abstractmethod
    def execute(self, operation: str, params: dict[str, Any]) -> dict[str, Any]:
        """
        Execute an operation supported by this module

        Args:
            operation: The operation name (e.g., "generate_embeddings", "reason")
            params: Operation parameters

        Returns:
            Result dictionary
        """
        pass

    def validate_params(self, operation: str, params: dict[str, Any]) -> bool:
        """Validate parameters for an operation (optional override)"""
        return True

    def initialize(self) -> bool:
        """Initialize the module (load models, etc.) - called once"""
        return True

    def cleanup(self) -> None:
        """Cleanup resources (optional override)"""
        pass
