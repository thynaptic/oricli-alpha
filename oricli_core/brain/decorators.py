from __future__ import annotations
"""
Module Decorators

Decorators for automatic metrics tracking and other module enhancements.
"""

import time
import functools
from typing import Any, Callable

from oricli_core.brain.metrics import record_operation


def track_metrics(module_name: str):
    """
    Decorator to automatically track metrics for module operations
    
    Usage:
        @track_metrics("my_module")
        def my_operation(self, params):
            # operation code
            return result
    
    Args:
        module_name: Name of the module
    """
    def decorator(func: Callable) -> Callable:
        @functools.wraps(func)
        def wrapper(self, operation: str, params: dict[str, Any], *args, **kwargs) -> Any:
            start_time = time.time()
            success = True
            error = None
            
            try:
                result = func(self, operation, params, *args, **kwargs)
                return result
            except Exception as e:
                success = False
                error = str(e)
                raise
            finally:
                execution_time = time.time() - start_time
                try:
                    record_operation(
                        module_name=module_name,
                        operation=operation,
                        execution_time=execution_time,
                        success=success,
                        error=error
                    )
                except Exception:
                    # Silently fail if metrics not available
                    pass
        
        return wrapper
    return decorator

