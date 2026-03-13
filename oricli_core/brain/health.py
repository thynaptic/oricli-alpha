from __future__ import annotations
"""
Module Health Checking System

Monitors module health and provides health status reporting.
"""

from enum import Enum
from typing import Dict, List, Optional, Any, Callable
from dataclasses import dataclass
from datetime import datetime, timedelta
import threading

from oricli_core.brain.registry import ModuleRegistry
from oricli_core.brain.base_module import BaseBrainModule
from oricli_core.brain.metrics import get_metrics_collector
from oricli_core.exceptions import ModuleNotFoundError


class HealthStatus(Enum):
    """Health status levels"""
    HEALTHY = "healthy"
    DEGRADED = "degraded"
    UNHEALTHY = "unhealthy"
    UNKNOWN = "unknown"


@dataclass
class HealthCheck:
    """Health check result"""
    module_name: str
    status: HealthStatus
    message: str
    timestamp: datetime
    details: Dict[str, Any]
    checks: List[Dict[str, Any]] = None


class HealthChecker:
    """
    Health checking system for brain modules
    """
    
    def __init__(self):
        """Initialize health checker"""
        self._custom_checks: Dict[str, List[Callable]] = {}
        self._lock = threading.RLock()
        self._failure_threshold = 0.1  # 10% failure rate = degraded
        self._error_threshold = 0.3  # 30% failure rate = unhealthy
    
    def check_module_health(
        self,
        module_name: str,
        include_metrics: bool = True
    ) -> HealthCheck:
        """
        Check health of a module
        
        Args:
            module_name: Name of the module to check
            include_metrics: Whether to include metrics in health check
        
        Returns:
            HealthCheck result
        """
        checks = []
        status = HealthStatus.UNKNOWN
        message = "Health check completed"
        details = {}
        
        # Check if module exists
        if not ModuleRegistry.is_module_available(module_name):
            return HealthCheck(
                module_name=module_name,
                status=HealthStatus.UNHEALTHY,
                message="Module not found",
                timestamp=datetime.now(),
                details={},
                checks=[]
            )
        
        # Check module availability
        module = ModuleRegistry.get_module(module_name)
        if module is None:
            checks.append({
                "check": "module_availability",
                "status": "failed",
                "message": "Module instance not available"
            })
            status = HealthStatus.UNHEALTHY
        else:
            checks.append({
                "check": "module_availability",
                "status": "passed",
                "message": "Module instance available"
            })
        
        # Check initialization
        try:
            if module and hasattr(module, '_initialized'):
                initialized = getattr(module, '_initialized', False)
                checks.append({
                    "check": "initialization",
                    "status": "passed" if initialized else "failed",
                    "message": "Module initialized" if initialized else "Module not initialized"
                })
        except Exception as e:
            checks.append({
                "check": "initialization",
                "status": "error",
                "message": f"Error checking initialization: {e}"
            })
        
        # Check metrics if available
        if include_metrics:
            metrics_check = self._check_metrics(module_name)
            checks.extend(metrics_check["checks"])
            
            if metrics_check["status"] == "unhealthy":
                status = HealthStatus.UNHEALTHY
                message = metrics_check["message"]
            elif metrics_check["status"] == "degraded" and status == HealthStatus.UNKNOWN:
                status = HealthStatus.DEGRADED
                message = metrics_check["message"]
            elif status == HealthStatus.UNKNOWN:
                status = HealthStatus.HEALTHY
        
        # Run custom checks
        custom_results = self._run_custom_checks(module_name, module)
        checks.extend(custom_results)
        
        # Determine final status
        if status == HealthStatus.UNKNOWN:
            # If no issues found, mark as healthy
            status = HealthStatus.HEALTHY
            message = "All health checks passed"
        
        return HealthCheck(
            module_name=module_name,
            status=status,
            message=message,
            timestamp=datetime.now(),
            details=details,
            checks=checks
        )
    
    def _check_metrics(self, module_name: str) -> Dict[str, Any]:
        """
        Check module metrics for health indicators
        
        Args:
            module_name: Name of the module
        
        Returns:
            Dictionary with check results
        """
        checks = []
        metrics_collector = get_metrics_collector()
        module_metrics = metrics_collector.get_module_metrics(module_name)
        
        if not module_metrics:
            checks.append({
                "check": "metrics",
                "status": "info",
                "message": "No metrics available"
            })
            return {"status": "healthy", "message": "No metrics to check", "checks": checks}
        
        # Check failure rate
        total_failures = sum(
            op.failure_count for op in module_metrics.operations.values()
        )
        total_calls = module_metrics.total_calls
        
        if total_calls > 0:
            failure_rate = total_failures / total_calls
            
            if failure_rate >= self._error_threshold:
                checks.append({
                    "check": "failure_rate",
                    "status": "failed",
                    "message": f"High failure rate: {failure_rate:.2%}",
                    "value": failure_rate
                })
                return {
                    "status": "unhealthy",
                    "message": f"Unhealthy: {failure_rate:.2%} failure rate",
                    "checks": checks
                }
            elif failure_rate >= self._failure_threshold:
                checks.append({
                    "check": "failure_rate",
                    "status": "warning",
                    "message": f"Elevated failure rate: {failure_rate:.2%}",
                    "value": failure_rate
                })
                return {
                    "status": "degraded",
                    "message": f"Degraded: {failure_rate:.2%} failure rate",
                    "checks": checks
                }
            else:
                checks.append({
                    "check": "failure_rate",
                    "status": "passed",
                    "message": f"Failure rate acceptable: {failure_rate:.2%}",
                    "value": failure_rate
                })
        
        # Check recent activity
        if module_metrics.last_activity:
            time_since_activity = datetime.now() - module_metrics.last_activity.replace(tzinfo=None)
            if time_since_activity > timedelta(hours=24):
                checks.append({
                    "check": "activity",
                    "status": "warning",
                    "message": f"No activity for {time_since_activity}",
                    "value": str(time_since_activity)
                })
        
        return {"status": "healthy", "message": "Metrics check passed", "checks": checks}
    
    def _run_custom_checks(
        self,
        module_name: str,
        module: Optional[BaseBrainModule]
    ) -> List[Dict[str, Any]]:
        """
        Run custom health checks
        
        Args:
            module_name: Name of the module
            module: Module instance
        
        Returns:
            List of check results
        """
        results = []
        
        with self._lock:
            custom_checks = self._custom_checks.get(module_name, [])
        
        for check_func in custom_checks:
            try:
                result = check_func(module_name, module)
                if isinstance(result, dict):
                    results.append(result)
            except Exception as e:
                results.append({
                    "check": "custom",
                    "status": "error",
                    "message": f"Custom check failed: {e}"
                })
        
        return results
    
    def add_custom_check(
        self,
        module_name: str,
        check_func: Callable[[str, Optional[BaseBrainModule]], Dict[str, Any]]
    ) -> None:
        """
        Add custom health check for a module
        
        Args:
            module_name: Name of the module
            check_func: Check function (module_name, module) -> check_result
        """
        with self._lock:
            if module_name not in self._custom_checks:
                self._custom_checks[module_name] = []
            self._custom_checks[module_name].append(check_func)
    
    def check_all_modules(self) -> Dict[str, HealthCheck]:
        """
        Check health of all modules
        
        Returns:
            Dictionary mapping module names to health checks
        """
        results = {}
        
        for module_name in ModuleRegistry.list_modules():
            results[module_name] = self.check_module_health(module_name)
        
        return results
    
    def get_health_summary(self) -> Dict[str, Any]:
        """
        Get summary of all module health
        
        Returns:
            Summary dictionary
        """
        all_checks = self.check_all_modules()
        
        status_counts = {
            HealthStatus.HEALTHY: 0,
            HealthStatus.DEGRADED: 0,
            HealthStatus.UNHEALTHY: 0,
            HealthStatus.UNKNOWN: 0
        }
        
        for check in all_checks.values():
            status_counts[check.status] += 1
        
        return {
            "total_modules": len(all_checks),
            "status_counts": {
                status.value: count
                for status, count in status_counts.items()
            },
            "checks": {
                name: {
                    "status": check.status.value,
                    "message": check.message,
                    "timestamp": check.timestamp.isoformat()
                }
                for name, check in all_checks.items()
            }
        }


# Global health checker instance
_global_health_checker = HealthChecker()


def get_health_checker() -> HealthChecker:
    """Get global health checker instance"""
    return _global_health_checker

