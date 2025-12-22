"""
Module Monitor Service

Continuously monitors module health, detects failures, and measures
performance to identify degraded modules.
"""

import os
import sys
import threading
import time
import logging
from typing import Dict, List, Optional, Any, Callable
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum

from mavaia_core.brain.registry import ModuleRegistry
from mavaia_core.brain.base_module import BaseBrainModule
from mavaia_core.brain.health import HealthChecker, HealthStatus, HealthCheck
from mavaia_core.exceptions import ModuleNotFoundError

logger = logging.getLogger(__name__)


class ModuleState(Enum):
    """Module state for monitoring"""
    ONLINE = "online"
    OFFLINE = "offline"
    DEGRADED = "degraded"
    UNKNOWN = "unknown"


@dataclass
class ModuleStatus:
    """Status of a module from monitoring"""
    module_name: str
    state: ModuleState
    health_status: HealthStatus
    last_check: datetime
    response_time: Optional[float] = None
    degradation_reason: Optional[str] = None
    details: Dict[str, Any] = field(default_factory=dict)
    consecutive_failures: int = 0
    last_success: Optional[datetime] = None


class ModuleMonitorService:
    """
    Service for continuously monitoring module health
    
    Periodically checks all modules, measures performance, and detects
    degradation or failures.
    """
    
    def __init__(self):
        """Initialize monitor service"""
        self._statuses: Dict[str, ModuleStatus] = {}
        self._status_lock = threading.RLock()
        self._monitoring = False
        self._monitor_thread: Optional[threading.Thread] = None
        self._health_checker = HealthChecker()
        self._callbacks: List[Callable[[str, ModuleStatus, Optional[ModuleStatus]]]] = []
        
        # Configuration from environment variables
        self._enabled = os.getenv("MAVAIA_MONITOR_ENABLED", "true").lower() in ("true", "1", "yes")
        self._interval = float(os.getenv("MAVAIA_MONITOR_INTERVAL", "30.0"))
        self._timeout = float(os.getenv("MAVAIA_MONITOR_TIMEOUT", "10.0"))
        self._slow_threshold = float(os.getenv("MAVAIA_MONITOR_SLOW_THRESHOLD", "5.0"))
        
        logger.info(
            f"ModuleMonitorService initialized: enabled={self._enabled}, "
            f"interval={self._interval}s, timeout={self._timeout}s, "
            f"slow_threshold={self._slow_threshold}s"
        )
    
    def start_monitoring(self) -> None:
        """Start background monitoring thread"""
        if not self._enabled:
            logger.info("Module monitoring is disabled")
            return
        
        if self._monitoring:
            logger.warning("Monitoring already started")
            return
        
        self._monitoring = True
        self._monitor_thread = threading.Thread(
            target=self._monitor_loop,
            daemon=True,
            name="ModuleMonitor"
        )
        self._monitor_thread.start()
        logger.info("Module monitoring started")
    
    def stop_monitoring(self) -> None:
        """Stop background monitoring"""
        if not self._monitoring:
            return
        
        self._monitoring = False
        if self._monitor_thread:
            self._monitor_thread.join(timeout=5.0)
        logger.info("Module monitoring stopped")
    
    def _monitor_loop(self) -> None:
        """Main monitoring loop"""
        while self._monitoring:
            try:
                # Get all registered modules
                module_names = ModuleRegistry.list_modules()
                
                if not module_names:
                    time.sleep(self._interval)
                    continue
                
                # Check each module
                for module_name in module_names:
                    if not self._monitoring:
                        break
                    
                    try:
                        self.check_module(module_name)
                    except Exception as e:
                        logger.error(f"Error checking module {module_name}: {e}", exc_info=True)
                
                # Sleep until next check
                time.sleep(self._interval)
                
            except Exception as e:
                logger.error(f"Error in monitor loop: {e}", exc_info=True)
                time.sleep(self._interval)
    
    def check_module(self, module_name: str) -> ModuleStatus:
        """
        Manually check a module
        
        Args:
            module_name: Name of module to check
        
        Returns:
            ModuleStatus with current state
        """
        start_time = time.time()
        previous_status = None
        
        with self._status_lock:
            if module_name in self._statuses:
                previous_status = self._statuses[module_name]
        
        try:
            # Check if module exists
            if not ModuleRegistry.is_module_available(module_name):
                status = ModuleStatus(
                    module_name=module_name,
                    state=ModuleState.OFFLINE,
                    health_status=HealthStatus.UNHEALTHY,
                    last_check=datetime.now(),
                    degradation_reason="Module not found",
                    consecutive_failures=(
                        previous_status.consecutive_failures + 1
                        if previous_status else 1
                    )
                )
                self._update_status(module_name, status, previous_status)
                return status
            
            # Get module instance
            try:
                module = ModuleRegistry.get_module(
                    module_name,
                    auto_discover=False,
                    wait_timeout=min(self._timeout, 5.0)
                )
            except Exception as e:
                status = ModuleStatus(
                    module_name=module_name,
                    state=ModuleState.OFFLINE,
                    health_status=HealthStatus.UNHEALTHY,
                    last_check=datetime.now(),
                    degradation_reason=f"Failed to get module: {e}",
                    consecutive_failures=(
                        previous_status.consecutive_failures + 1
                        if previous_status else 1
                    )
                )
                self._update_status(module_name, status, previous_status)
                return status
            
            if module is None:
                status = ModuleStatus(
                    module_name=module_name,
                    state=ModuleState.OFFLINE,
                    health_status=HealthStatus.UNHEALTHY,
                    last_check=datetime.now(),
                    degradation_reason="Module instance is None",
                    consecutive_failures=(
                        previous_status.consecutive_failures + 1
                        if previous_status else 1
                    )
                )
                self._update_status(module_name, status, previous_status)
                return status
            
            # Perform health check
            try:
                health_check = self._health_checker.check_module_health(
                    module_name,
                    include_metrics=True
                )
            except Exception as e:
                logger.warning(f"Health check failed for {module_name}: {e}")
                health_check = HealthCheck(
                    module_name=module_name,
                    status=HealthStatus.UNKNOWN,
                    message=f"Health check error: {e}",
                    timestamp=datetime.now(),
                    details={},
                    checks=[]
                )
            
            # Test with lightweight operation to measure response time
            response_time = None
            operation_test_passed = False
            operation_error = None
            
            try:
                response_time = self._test_module_operation(module, module_name)
                operation_test_passed = True
            except Exception as e:
                operation_error = str(e)
                logger.debug(f"Operation test failed for {module_name}: {e}")
            
            # Determine state based on health and performance
            state = ModuleState.UNKNOWN
            degradation_reason = None
            
            if health_check.status == HealthStatus.HEALTHY:
                if operation_test_passed:
                    if response_time is not None and response_time > self._slow_threshold:
                        state = ModuleState.DEGRADED
                        degradation_reason = f"Slow response time: {response_time:.2f}s (threshold: {self._slow_threshold}s)"
                    else:
                        state = ModuleState.ONLINE
                else:
                    state = ModuleState.DEGRADED
                    degradation_reason = f"Operation test failed: {operation_error}"
            elif health_check.status == HealthStatus.DEGRADED:
                state = ModuleState.DEGRADED
                degradation_reason = health_check.message
            elif health_check.status == HealthStatus.UNHEALTHY:
                state = ModuleState.OFFLINE
                degradation_reason = health_check.message
            else:
                state = ModuleState.UNKNOWN
                degradation_reason = "Unknown health status"
            
            # Update consecutive failures
            consecutive_failures = 0
            last_success = None
            if state == ModuleState.ONLINE:
                consecutive_failures = 0
                last_success = datetime.now()
            else:
                consecutive_failures = (
                    previous_status.consecutive_failures + 1
                    if previous_status else 1
                )
                if previous_status:
                    last_success = previous_status.last_success
            
            # Create status
            status = ModuleStatus(
                module_name=module_name,
                state=state,
                health_status=health_check.status,
                last_check=datetime.now(),
                response_time=response_time,
                degradation_reason=degradation_reason,
                details={
                    "health_check": {
                        "status": health_check.status.value,
                        "message": health_check.message,
                        "checks": health_check.checks
                    },
                    "operation_test_passed": operation_test_passed,
                    "operation_error": operation_error
                },
                consecutive_failures=consecutive_failures,
                last_success=last_success
            )
            
            self._update_status(module_name, status, previous_status)
            return status
            
        except Exception as e:
            logger.error(f"Unexpected error checking module {module_name}: {e}", exc_info=True)
            status = ModuleStatus(
                module_name=module_name,
                state=ModuleState.OFFLINE,
                health_status=HealthStatus.UNHEALTHY,
                last_check=datetime.now(),
                degradation_reason=f"Unexpected error: {e}",
                consecutive_failures=(
                    previous_status.consecutive_failures + 1
                    if previous_status else 1
                )
            )
            self._update_status(module_name, status, previous_status)
            return status
    
    def _test_module_operation(
        self,
        module: BaseBrainModule,
        module_name: str
    ) -> float:
        """
        Test module with lightweight operation and measure response time
        
        Args:
            module: Module instance
            module_name: Module name
        
        Returns:
            Response time in seconds
        
        Raises:
            Exception: If operation test fails
        """
        metadata = module.metadata
        operations = metadata.operations
        
        if not operations:
            # No operations to test, return 0
            return 0.0
        
        # Try health_check or ping operations first
        test_operation = None
        test_params = {}
        
        for op in ["health_check", "ping", "status"]:
            if op in operations:
                test_operation = op
                break
        
        # If no health check operation, use first available operation with minimal params
        if not test_operation:
            test_operation = operations[0]
            test_params = {"test": True}
        
        # Execute with timeout
        start_time = time.time()
        try:
            result = module.execute(test_operation, test_params)
            response_time = time.time() - start_time
            return response_time
        except Exception as e:
            raise Exception(f"Operation '{test_operation}' failed: {e}") from e
    
    def _update_status(
        self,
        module_name: str,
        status: ModuleStatus,
        previous_status: Optional[ModuleStatus]
    ) -> None:
        """Update module status and trigger callbacks if changed"""
        with self._status_lock:
            self._statuses[module_name] = status
        
        # Trigger callbacks if status changed
        if previous_status is None or previous_status.state != status.state:
            for callback in self._callbacks:
                try:
                    callback(module_name, status, previous_status)
                except Exception as e:
                    logger.error(f"Error in status callback: {e}", exc_info=True)
    
    def get_module_status(self, module_name: str) -> Optional[ModuleStatus]:
        """
        Get current status of a module
        
        Args:
            module_name: Name of module
        
        Returns:
            ModuleStatus or None if not found
        """
        with self._status_lock:
            return self._statuses.get(module_name)
    
    def get_all_statuses(self) -> Dict[str, ModuleStatus]:
        """
        Get status of all modules
        
        Returns:
            Dictionary mapping module names to statuses
        """
        with self._status_lock:
            return self._statuses.copy()
    
    def register_status_callback(
        self,
        callback: Callable[[str, ModuleStatus, Optional[ModuleStatus]], None]
    ) -> None:
        """
        Register callback for status changes
        
        Args:
            callback: Function called when module status changes
                Signature: (module_name, new_status, previous_status) -> None
        """
        with self._status_lock:
            self._callbacks.append(callback)


# Global monitor service instance
_global_monitor_service: Optional[ModuleMonitorService] = None


def get_monitor_service() -> ModuleMonitorService:
    """Get global monitor service instance"""
    global _global_monitor_service
    if _global_monitor_service is None:
        _global_monitor_service = ModuleMonitorService()
    return _global_monitor_service

