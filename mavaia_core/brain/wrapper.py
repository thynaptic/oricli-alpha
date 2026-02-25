from __future__ import annotations
"""
Module Wrapper for Automatic Metrics Tracking

Provides wrapper functionality to automatically track metrics for module operations.
"""

import time
from typing import Any, Callable, Dict
from functools import wraps

from mavaia_core.brain.base_module import BaseBrainModule
from mavaia_core.brain.metrics import record_operation


class MetricsTrackingWrapper:
    """
    Wrapper that automatically tracks metrics for module operations
    """
    
    @staticmethod
    def wrap_execute(module: BaseBrainModule) -> Callable:
        """
        Wrap a module's execute method to automatically track metrics
        
        Args:
            module: Module instance to wrap
        
        Returns:
            Wrapped execute method
        """
        original_execute = module.execute
        
        @wraps(original_execute)
        def wrapped_execute(operation: str, params: Dict[str, Any]) -> Dict[str, Any]:
            """Wrapped execute with metrics tracking"""
            start_time = time.time()
            success = True
            error = None
            
            try:
                result = original_execute(operation, params)
                return result
            except Exception as e:
                success = False
                error = str(e)
                raise
            finally:
                execution_time = time.time() - start_time
                try:
                    record_operation(
                        module_name=module.metadata.name,
                        operation=operation,
                        execution_time=execution_time,
                        success=success,
                        error=error
                    )
                except Exception:
                    # Silently fail if metrics not available
                    pass
        
        return wrapped_execute

