"""
Module Metrics System

Tracks execution time, success/failure rates, and resource usage for modules.
"""

import time
from typing import Dict, List, Optional, Any
from dataclasses import dataclass, field
from datetime import datetime
from collections import defaultdict
import threading

from mavaia_core.brain.base_module import BaseBrainModule


@dataclass
class OperationMetrics:
    """Metrics for a single operation"""
    operation: str
    call_count: int = 0
    total_time: float = 0.0
    success_count: int = 0
    failure_count: int = 0
    min_time: Optional[float] = None
    max_time: Optional[float] = None
    last_call_time: Optional[datetime] = None
    errors: List[str] = field(default_factory=list)


@dataclass
class ModuleMetrics:
    """Metrics for a module"""
    module_name: str
    operations: Dict[str, OperationMetrics] = field(default_factory=dict)
    total_calls: int = 0
    total_time: float = 0.0
    last_activity: Optional[datetime] = None
    resource_usage: Dict[str, Any] = field(default_factory=dict)


class MetricsCollector:
    """
    Collects and aggregates metrics for brain modules
    """
    
    def __init__(self):
        """Initialize metrics collector"""
        self._metrics: Dict[str, ModuleMetrics] = {}
        self._lock = threading.RLock()
    
    def record_operation(
        self,
        module_name: str,
        operation: str,
        execution_time: float,
        success: bool = True,
        error: Optional[str] = None
    ) -> None:
        """
        Record an operation execution
        
        Args:
            module_name: Name of the module
            operation: Operation name
            execution_time: Execution time in seconds
            success: Whether operation succeeded
            error: Optional error message
        """
        with self._lock:
            if module_name not in self._metrics:
                self._metrics[module_name] = ModuleMetrics(module_name=module_name)
            
            module_metrics = self._metrics[module_name]
            
            if operation not in module_metrics.operations:
                module_metrics.operations[operation] = OperationMetrics(operation=operation)
            
            op_metrics = module_metrics.operations[operation]
            
            # Update operation metrics
            op_metrics.call_count += 1
            op_metrics.total_time += execution_time
            op_metrics.last_call_time = datetime.now()
            
            if success:
                op_metrics.success_count += 1
            else:
                op_metrics.failure_count += 1
                if error:
                    op_metrics.errors.append(error)
                    # Keep only last 10 errors
                    if len(op_metrics.errors) > 10:
                        op_metrics.errors = op_metrics.errors[-10:]
            
            # Update min/max times
            if op_metrics.min_time is None or execution_time < op_metrics.min_time:
                op_metrics.min_time = execution_time
            if op_metrics.max_time is None or execution_time > op_metrics.max_time:
                op_metrics.max_time = execution_time
            
            # Update module metrics
            module_metrics.total_calls += 1
            module_metrics.total_time += execution_time
            module_metrics.last_activity = datetime.now()
    
    def get_module_metrics(self, module_name: str) -> Optional[ModuleMetrics]:
        """
        Get metrics for a module
        
        Args:
            module_name: Name of the module
        
        Returns:
            Module metrics or None if not found
        """
        with self._lock:
            return self._metrics.get(module_name)
    
    def get_operation_metrics(
        self,
        module_name: str,
        operation: str
    ) -> Optional[OperationMetrics]:
        """
        Get metrics for a specific operation
        
        Args:
            module_name: Name of the module
            operation: Operation name
        
        Returns:
            Operation metrics or None if not found
        """
        with self._lock:
            module_metrics = self._metrics.get(module_name)
            if module_metrics:
                return module_metrics.operations.get(operation)
            return None
    
    def get_all_metrics(self) -> Dict[str, ModuleMetrics]:
        """
        Get all collected metrics
        
        Returns:
            Dictionary mapping module names to metrics
        """
        with self._lock:
            return self._metrics.copy()
    
    def get_summary(self) -> Dict[str, Any]:
        """
        Get summary of all metrics
        
        Returns:
            Summary dictionary with aggregated statistics
        """
        with self._lock:
            total_modules = len(self._metrics)
            total_operations = sum(
                len(m.operations) for m in self._metrics.values()
            )
            total_calls = sum(m.total_calls for m in self._metrics.values())
            total_time = sum(m.total_time for m in self._metrics.values())
            
            avg_time_per_call = (
                total_time / total_calls if total_calls > 0 else 0.0
            )
            
            return {
                "total_modules": total_modules,
                "total_operations": total_operations,
                "total_calls": total_calls,
                "total_time": total_time,
                "avg_time_per_call": avg_time_per_call,
                "modules": {
                    name: {
                        "total_calls": m.total_calls,
                        "total_time": m.total_time,
                        "operations": len(m.operations),
                        "last_activity": m.last_activity.isoformat() if m.last_activity else None
                    }
                    for name, m in self._metrics.items()
                }
            }
    
    def reset(self, module_name: Optional[str] = None) -> None:
        """
        Reset metrics
        
        Args:
            module_name: Optional module name to reset, or None to reset all
        """
        with self._lock:
            if module_name:
                if module_name in self._metrics:
                    del self._metrics[module_name]
            else:
                self._metrics.clear()
    
    def export_metrics(self) -> Dict[str, Any]:
        """
        Export metrics in a serializable format
        
        Returns:
            Dictionary with all metrics
        """
        with self._lock:
            return {
                name: {
                    "module_name": m.module_name,
                    "total_calls": m.total_calls,
                    "total_time": m.total_time,
                    "last_activity": m.last_activity.isoformat() if m.last_activity else None,
                    "operations": {
                        op: {
                            "call_count": om.call_count,
                            "total_time": om.total_time,
                            "avg_time": om.total_time / om.call_count if om.call_count > 0 else 0.0,
                            "success_count": om.success_count,
                            "failure_count": om.failure_count,
                            "success_rate": om.success_count / om.call_count if om.call_count > 0 else 0.0,
                            "min_time": om.min_time,
                            "max_time": om.max_time,
                            "last_call_time": om.last_call_time.isoformat() if om.last_call_time else None,
                            "error_count": len(om.errors)
                        }
                        for op, om in m.operations.items()
                    }
                }
                for name, m in self._metrics.items()
            }


# Global metrics collector instance
_global_collector = MetricsCollector()


def get_metrics_collector() -> MetricsCollector:
    """Get global metrics collector instance"""
    return _global_collector


def record_operation(
    module_name: str,
    operation: str,
    execution_time: float,
    success: bool = True,
    error: Optional[str] = None
) -> None:
    """
    Record an operation execution (convenience function)
    
    Args:
        module_name: Name of the module
        operation: Operation name
        execution_time: Execution time in seconds
        success: Whether operation succeeded
        error: Optional error message
    """
    _global_collector.record_operation(
        module_name, operation, execution_time, success, error
    )

