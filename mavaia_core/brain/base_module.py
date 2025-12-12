"""
Base Module Interface - All intelligence modules must inherit from this
Enables plug-and-play architecture for easy module addition/removal
"""

from abc import ABC, abstractmethod
from typing import Any
from dataclasses import dataclass
import time

@dataclass
class ModuleMetadata:
    """
    Metadata describing a brain module
    
    Attributes:
        name: Module identifier (e.g., "reasoning", "embeddings")
        version: Module version (semantic versioning recommended)
        description: Human-readable description of what this module does
        operations: List of operation names this module supports
        dependencies: Required Python packages (for documentation and validation)
        enabled: Whether module is enabled (default: True)
        model_required: Whether this module requires a HuggingFace model (default: False)
    """

    name: str
    version: str
    description: str
    operations: list[str]
    dependencies: list[str]
    enabled: bool = True
    model_required: bool = False


class BaseBrainModule(ABC):
    """
    Base class that all intelligence modules must implement
    
    All brain modules must inherit from this class and implement the required
    abstract methods. Modules are automatically discovered by the ModuleRegistry
    and made available via the MavaiaClient.
    """

    @property
    @abstractmethod
    def metadata(self) -> ModuleMetadata:
        """
        Return metadata about this module
        
        Returns:
            ModuleMetadata instance describing the module's capabilities
        """
        pass

    @abstractmethod
    def execute(self, operation: str, params: dict[str, Any]) -> dict[str, Any]:
        """
        Execute an operation supported by this module

        Args:
            operation: The operation name (e.g., "generate_embeddings", "reason")
            params: Operation parameters

        Returns:
            Result dictionary containing the operation result

        Raises:
            ValueError: If the operation is not supported by this module
            InvalidParameterError: If parameters are invalid or missing
            ModuleOperationError: If the operation execution fails
        """
        pass
    
    def _execute_with_metrics(
        self,
        operation: str,
        params: dict[str, Any]
    ) -> dict[str, Any]:
        """
        Execute operation with automatic metrics tracking
        
        This method wraps execute() to automatically track execution time,
        success/failure, and errors. Modules can override execute() to call
        this method for built-in metrics collection.
        
        Metrics are collected via lazy import to avoid circular dependencies.
        If metrics collection fails, it fails silently to prevent disrupting
        module operations.
        
        Args:
            operation: Operation name
            params: Operation parameters
        
        Returns:
            Operation result from execute()
        
        Raises:
            Any exception raised by execute() is re-raised after metrics
            collection. The original exception is preserved.
        """
        start_time = time.time()
        success = True
        error: str | None = None
        
        try:
            result = self.execute(operation, params)
            return result
        except Exception as e:
            success = False
            error = str(e)
            raise
        finally:
            execution_time = time.time() - start_time
            try:
                from mavaia_core.brain.metrics import record_operation
                record_operation(
                    module_name=self.metadata.name,
                    operation=operation,
                    execution_time=execution_time,
                    success=success,
                    error=error
                )
            except Exception:
                # Silently fail if metrics not available to avoid disrupting
                # module operations. This can happen if metrics module is not
                # initialized or there's a circular import issue.
                pass

    def validate_params(self, operation: str, params: dict[str, Any]) -> bool:
        """
        Validate parameters for an operation (optional override)
        
        This method can be overridden by modules to validate operation
        parameters before execution. The default implementation accepts
        all parameters.
        
        Note: For better error handling, consider raising
        InvalidParameterError instead of returning False. This provides
        more context about validation failures.
        
        Args:
            operation: Operation name
            params: Operation parameters to validate
        
        Returns:
            True if parameters are valid, False otherwise
        
        Raises:
            InvalidParameterError: Recommended approach - raise this exception
                with details about invalid parameters instead of returning False
        """
        return True

    def initialize(self) -> bool:
        """
        Initialize the module (load models, etc.) - called once
        
        This method is called once when the module is registered. Override
        this method to perform initialization tasks such as loading models,
        connecting to external services, or setting up resources.
        
        Note: For better error handling, consider raising
        ModuleInitializationError instead of returning False. This provides
        more context about initialization failures.
        
        Returns:
            True if initialization succeeded, False otherwise
        
        Raises:
            ModuleInitializationError: Recommended approach - raise this
                exception with details about initialization failure instead
                of returning False
        """
        return True

    def cleanup(self) -> None:
        """
        Cleanup resources (optional override)
        
        This method is called when the module is unregistered or the system
        is shutting down. Override this method to perform cleanup tasks such
        as closing connections, releasing resources, or saving state.
        
        This method should not raise exceptions. Any errors during cleanup
        should be logged but not propagated to avoid disrupting shutdown.
        """
        pass

