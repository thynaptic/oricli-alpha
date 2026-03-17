from __future__ import annotations
"""
Module Recovery Service

Automatically recovers failed or offline modules with retry logic
and exponential backoff.
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

from oricli_core.brain.registry import ModuleRegistry
from oricli_core.brain.base_module import BaseBrainModule
from oricli_core.brain.modules.monitor import ModuleMonitorService, ModuleState, get_monitor_service
from oricli_core.exceptions import ModuleInitializationError, ModuleNotFoundError

logger = logging.getLogger(__name__)


class RecoveryStatus(Enum):
    """Recovery attempt status"""
    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    SUCCESS = "success"
    FAILED = "failed"
    MAX_ATTEMPTS_REACHED = "max_attempts_reached"


@dataclass
class RecoveryAttempt:
    """Record of a recovery attempt"""
    module_name: str
    attempt_number: int
    status: RecoveryStatus
    start_time: datetime
    end_time: Optional[datetime] = None
    duration: Optional[float] = None
    error: Optional[str] = None
    backoff_duration: Optional[float] = None
    details: Dict[str, Any] = field(default_factory=dict)


@dataclass
class RecoveryHistory:
    """Recovery history for a module"""
    module_name: str
    attempts: List[RecoveryAttempt] = field(default_factory=list)
    last_attempt: Optional[datetime] = None
    total_attempts: int = 0
    successful_attempts: int = 0
    failed_attempts: int = 0


class ModuleRecoveryService:
    """
    Service for automatically recovering failed modules
    
    Listens to monitor events and attempts to recover failed modules
    with exponential backoff retry logic.
    """
    
    def __init__(self):
        """Initialize recovery service"""
        self._recovery_history: Dict[str, RecoveryHistory] = {}
        self._recovery_lock = threading.RLock()
        self._recovering: Dict[str, bool] = {}
        self._monitor_service: Optional[ModuleMonitorService] = None
        self._callbacks: List[Callable[[str, RecoveryAttempt]]] = []
        
        # Configuration from environment variables
        self._enabled = os.getenv("MAVAIA_RECOVERY_ENABLED", "true").lower() in ("true", "1", "yes")
        # Use very high max attempts (effectively infinite) to ensure modules always come online
        max_attempts_str = os.getenv("MAVAIA_RECOVERY_MAX_ATTEMPTS", "unlimited")
        if max_attempts_str.lower() in ("unlimited", "inf", "infinite", "-1"):
            self._max_attempts = float('inf')  # Infinite retries
        else:
            self._max_attempts = int(max_attempts_str)
        self._backoff_base = float(os.getenv("MAVAIA_RECOVERY_BACKOFF_BASE", "2.0"))
        self._backoff_max = float(os.getenv("MAVAIA_RECOVERY_BACKOFF_MAX", "300.0"))
        self._ensure_online = os.getenv("MAVAIA_RECOVERY_ENSURE_ONLINE", "true").lower() in ("true", "1", "yes")
        
        logger.info(
            f"ModuleRecoveryService initialized: enabled={self._enabled}, "
            f"max_attempts={self._max_attempts}, backoff_base={self._backoff_base}, "
            f"backoff_max={self._backoff_max}s"
        )
    
    def initialize(self, monitor_service: Optional[ModuleMonitorService] = None) -> None:
        """
        Initialize recovery service with monitor service
        
        Args:
            monitor_service: Monitor service to listen to (uses global if not provided)
        """
        if monitor_service:
            self._monitor_service = monitor_service
        else:
            self._monitor_service = get_monitor_service()
        
        # Register callback for module failures
        if self._monitor_service:
            self._monitor_service.register_status_callback(self._on_module_status_change)
            logger.info("Recovery service registered with monitor service")
    
    def _on_module_status_change(
        self,
        module_name: str,
        new_status: Any,
        previous_status: Optional[Any]
    ) -> None:
        """
        Handle module status change from monitor
        
        Args:
            module_name: Name of module
            new_status: New module status
            previous_status: Previous module status
        """
        if not self._enabled:
            return
        
        # Only attempt recovery if module went offline or degraded
        if new_status.state in (ModuleState.OFFLINE, ModuleState.DEGRADED):
            # Check if we should attempt recovery
            history = self._get_recovery_history(module_name)
            
            if history.total_attempts < self._max_attempts:
                # Start recovery in background thread
                thread = threading.Thread(
                    target=self._recover_module_background,
                    args=(module_name,),
                    daemon=True,
                    name=f"Recovery-{module_name}"
                )
                thread.start()
    
    def _recover_module_background(self, module_name: str) -> None:
        """Recover module in background thread"""
        try:
            self.recover_module(module_name)
        except Exception as e:
            logger.error(f"Error in background recovery for {module_name}: {e}", exc_info=True)
    
    def recover_module(self, module_name: str) -> RecoveryAttempt:
        """
        Attempt to recover a module
        
        Args:
            module_name: Name of module to recover
        
        Returns:
            RecoveryAttempt with result
        """
        if not self._enabled:
            logger.debug(f"Recovery is disabled, skipping recovery for {module_name}")
            return RecoveryAttempt(
                module_name=module_name,
                attempt_number=0,
                status=RecoveryStatus.PENDING,
                start_time=datetime.now(),
                error="Recovery is disabled"
            )
        
        # Check if already recovering
        with self._recovery_lock:
            if self._recovering.get(module_name, False):
                logger.debug(f"Recovery already in progress for {module_name}")
                return RecoveryAttempt(
                    module_name=module_name,
                    attempt_number=0,
                    status=RecoveryStatus.IN_PROGRESS,
                    start_time=datetime.now(),
                    error="Recovery already in progress"
                )
            
            self._recovering[module_name] = True
        
        try:
            history = self._get_recovery_history(module_name)
            
            # Check if max attempts reached (only if not ensuring online)
            if not self._ensure_online and history.total_attempts >= self._max_attempts:
                logger.warning(
                    f"Max recovery attempts ({self._max_attempts}) reached for {module_name}"
                )
                return RecoveryAttempt(
                    module_name=module_name,
                    attempt_number=history.total_attempts,
                    status=RecoveryStatus.MAX_ATTEMPTS_REACHED,
                    start_time=datetime.now(),
                    error=f"Max attempts ({self._max_attempts}) reached"
                )
            
            # If ensuring online, continue retrying indefinitely
            if self._ensure_online and history.total_attempts > 0:
                logger.info(
                    f"Ensuring {module_name} comes online (attempt {history.total_attempts + 1})"
                )
            
            # Calculate backoff
            attempt_number = history.total_attempts + 1
            backoff_duration = min(
                self._backoff_base ** (attempt_number - 1),
                self._backoff_max
            )
            
            # Wait for backoff period (except for first attempt)
            if attempt_number > 1:
                logger.info(
                    f"Waiting {backoff_duration:.1f}s before recovery attempt {attempt_number} "
                    f"for {module_name}"
                )
                time.sleep(backoff_duration)
            
            # Start recovery attempt
            start_time = datetime.now()
            logger.info(f"Starting recovery attempt {attempt_number} for {module_name}")
            
            attempt = RecoveryAttempt(
                module_name=module_name,
                attempt_number=attempt_number,
                status=RecoveryStatus.IN_PROGRESS,
                start_time=start_time,
                backoff_duration=backoff_duration if attempt_number > 1 else None
            )
            
            try:
                # Step 1: Unregister module if it exists
                try:
                    ModuleRegistry.unregister_module(module_name)
                    attempt.details["unregistered"] = True
                except Exception as e:
                    logger.debug(f"Failed to unregister {module_name}: {e}")
                    attempt.details["unregistered"] = False
                    # Continue anyway
                
                # Step 2: Attempt to reload module
                try:
                    module = ModuleRegistry.get_module(
                        module_name,
                        auto_discover=True,
                        wait_timeout=60.0
                    )
                    
                    if module is None:
                        raise ModuleNotFoundError(module_name)
                    
                    attempt.details["reloaded"] = True
                    
                except Exception as e:
                    raise ModuleInitializationError(
                        module_name,
                        f"Failed to reload module: {e}"
                    ) from e
                
                # Step 3: Reinitialize module
                try:
                    if not module.initialize():
                        raise ModuleInitializationError(
                            module_name,
                            "initialize() returned False"
                        )
                    attempt.details["reinitialized"] = True
                    
                except Exception as e:
                    raise ModuleInitializationError(
                        module_name,
                        f"Reinitialization failed: {e}"
                    ) from e
                
                # Step 4: Test with lightweight operation
                try:
                    metadata = module.metadata
                    operations = metadata.operations
                    
                    if operations:
                        # Try a simple operation
                        test_operation = None
                        test_params = {}
                        
                        for op in ["health_check", "ping", "status"]:
                            if op in operations:
                                test_operation = op
                                break
                        
                        if not test_operation:
                            test_operation = operations[0]
                            test_params = {"test": True}
                        
                        result = module.execute(test_operation, test_params)
                        attempt.details["test_passed"] = True
                        attempt.details["test_operation"] = test_operation
                    else:
                        attempt.details["test_passed"] = True
                        attempt.details["test_operation"] = None
                    
                except Exception as e:
                    logger.warning(f"Test operation failed for recovered {module_name}: {e}")
                    attempt.details["test_passed"] = False
                    attempt.details["test_error"] = str(e)
                    # Don't fail recovery if test fails, module might still be usable
                
                # Mark as successful
                end_time = datetime.now()
                duration = (end_time - start_time).total_seconds()
                
                attempt.status = RecoveryStatus.SUCCESS
                attempt.end_time = end_time
                attempt.duration = duration
                
                logger.info(
                    f"Successfully recovered {module_name} in {duration:.2f}s "
                    f"(attempt {attempt_number})"
                )
                
                # If ensuring online, also trigger warmup to ensure module is fully ready
                if self._ensure_online and self._warmup_service:
                    try:
                        from oricli_core.brain.warmup import get_warmup_service
                        warmup_service = get_warmup_service()
                        warmup_service.warmup_module(module_name, verbose=False)
                    except Exception:
                        pass
                
            except Exception as e:
                # Recovery failed
                end_time = datetime.now()
                duration = (end_time - start_time).total_seconds()
                
                attempt.status = RecoveryStatus.FAILED
                attempt.end_time = end_time
                attempt.duration = duration
                attempt.error = str(e)
                
                logger.warning(
                    f"Recovery attempt {attempt_number} failed for {module_name}: {e}"
                )
                
                # If ensuring online, schedule another recovery attempt
                if self._ensure_online:
                    logger.info(
                        f"Will retry recovery for {module_name} (ensuring all modules online)"
                    )
                    # Schedule next recovery attempt after backoff
                    next_backoff = min(
                        self._backoff_base ** attempt_number,
                        self._backoff_max
                    )
                    def retry_recovery():
                        time.sleep(next_backoff)
                        if self._enabled:
                            self.recover_module(module_name)
                    
                    thread = threading.Thread(
                        target=retry_recovery,
                        daemon=True,
                        name=f"RecoveryRetry-{module_name}"
                    )
                    thread.start()
            
            # Update history
            history.attempts.append(attempt)
            history.total_attempts += 1
            history.last_attempt = end_time
            
            if attempt.status == RecoveryStatus.SUCCESS:
                history.successful_attempts += 1
            else:
                history.failed_attempts += 1
            
            # Trigger callbacks
            for callback in self._callbacks:
                try:
                    callback(module_name, attempt)
                except Exception as e:
                    logger.error(f"Error in recovery callback: {e}", exc_info=True)
            
            return attempt
            
        finally:
            with self._recovery_lock:
                self._recovering[module_name] = False
    
    def recover_all_failed(self) -> Dict[str, RecoveryAttempt]:
        """
        Recover all failed modules
        
        Returns:
            Dictionary mapping module names to recovery attempts
        """
        if not self._monitor_service:
            logger.warning("Monitor service not available, cannot recover all failed")
            return {}
        
        results = {}
        all_statuses = self._monitor_service.get_all_statuses()
        
        for module_name, status in all_statuses.items():
            if status.state in (ModuleState.OFFLINE, ModuleState.DEGRADED):
                try:
                    attempt = self.recover_module(module_name)
                    results[module_name] = attempt
                except Exception as e:
                    logger.error(f"Error recovering {module_name}: {e}", exc_info=True)
        
        return results
    
    def _get_recovery_history(self, module_name: str) -> RecoveryHistory:
        """Get or create recovery history for a module"""
        with self._recovery_lock:
            if module_name not in self._recovery_history:
                self._recovery_history[module_name] = RecoveryHistory(module_name=module_name)
            return self._recovery_history[module_name]
    
    def get_recovery_status(self) -> Dict[str, RecoveryHistory]:
        """
        Get recovery attempt history for all modules
        
        Returns:
            Dictionary mapping module names to recovery histories
        """
        with self._recovery_lock:
            return {
                name: RecoveryHistory(
                    module_name=history.module_name,
                    attempts=history.attempts.copy(),
                    last_attempt=history.last_attempt,
                    total_attempts=history.total_attempts,
                    successful_attempts=history.successful_attempts,
                    failed_attempts=history.failed_attempts
                )
                for name, history in self._recovery_history.items()
            }
    
    def register_recovery_callback(
        self,
        callback: Callable[[str, RecoveryAttempt], None]
    ) -> None:
        """
        Register callback for recovery events
        
        Args:
            callback: Function called when recovery attempt completes
                Signature: (module_name, attempt) -> None
        """
        with self._recovery_lock:
            self._callbacks.append(callback)


# Global recovery service instance
_global_recovery_service: Optional[ModuleRecoveryService] = None


def get_recovery_service() -> ModuleRecoveryService:
    """Get global recovery service instance"""
    global _global_recovery_service
    if _global_recovery_service is None:
        _global_recovery_service = ModuleRecoveryService()
    return _global_recovery_service

