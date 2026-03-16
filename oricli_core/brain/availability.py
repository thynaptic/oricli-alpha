from __future__ import annotations
"""
Module Availability Manager

Unified interface coordinating warmup, monitoring, recovery, and fallback routing
to ensure modules are available and achieve 0% downtime.
"""

import os
import sys
import threading
import time
import logging
from typing import Dict, List, Optional, Any, Tuple
from dataclasses import dataclass, field
from datetime import datetime

from oricli_core.brain.registry import ModuleRegistry
from oricli_core.brain.base_module import BaseBrainModule
from oricli_core.brain.warmup import ModuleWarmupService, get_warmup_service, WarmupStatus
from oricli_core.brain.monitor import ModuleMonitorService, get_monitor_service, ModuleState
from oricli_core.brain.recovery import ModuleRecoveryService, get_recovery_service
from oricli_core.brain.degraded_classifier import (
    DegradedModeClassifier,
    get_degraded_classifier,
    DegradationClassification
)
from oricli_core.brain.health import HealthStatus
from oricli_core.exceptions import ModuleNotFoundError

logger = logging.getLogger(__name__)


@dataclass
class AvailabilityStatus:
    """Overall availability status"""
    module_name: str
    available: bool
    state: ModuleState
    warmed: bool
    fallback_available: bool
    fallback_module: Optional[str] = None
    degradation_classification: Optional[DegradationClassification] = None
    details: Dict[str, Any] = field(default_factory=dict)


@dataclass
class SystemStatus:
    """Overall system status"""
    total_modules: int
    available_modules: int
    degraded_modules: int
    offline_modules: int
    warmed_modules: int
    modules_with_fallbacks: int
    timestamp: datetime = field(default_factory=datetime.now)
    details: Dict[str, Any] = field(default_factory=dict)


class ModuleAvailabilityManager:
    """
    Unified manager for module availability
    
    Coordinates warmup, monitoring, recovery, and fallback routing
    to ensure modules are available and achieve 0% downtime.
    
    When MAVAIA_ENSURE_ALL_MODULES_ONLINE=true (default):
    - All modules are kept online through persistent recovery
    - Fallbacks are NOT used - system waits for modules to come online
    - Background thread continuously ensures all modules stay online
    - Warmup retries failed modules until they succeed
    - Recovery retries indefinitely until modules come online
    
    When MAVAIA_ENSURE_ALL_MODULES_ONLINE=false:
    - Fallbacks are used when primary modules are degraded/offline
    - System routes to alternative modules for graceful degradation
    """
    
    def __init__(self):
        """Initialize availability manager"""
        self._initialized = False
        self._lock = threading.RLock()
        
        # Services
        self._warmup_service: Optional[ModuleWarmupService] = None
        self._monitor_service: Optional[ModuleMonitorService] = None
        self._recovery_service: Optional[ModuleRecoveryService] = None
        self._classifier: Optional[DegradedModeClassifier] = None
        
        # Configuration
        self._ensure_all_online = os.getenv("MAVAIA_ENSURE_ALL_MODULES_ONLINE", "true").lower() in ("true", "1", "yes")
        self._use_fallback_only_when_offline = os.getenv("MAVAIA_FALLBACK_ONLY_WHEN_OFFLINE", "false").lower() in ("true", "1", "yes")
        self._max_wait_for_module = float(os.getenv("MAVAIA_MAX_WAIT_FOR_MODULE", "60.0"))
        
        # Background thread to ensure all modules stay online
        self._ensure_online_thread: Optional[threading.Thread] = None
        self._ensuring_online = False
        
        logger.info(
            f"ModuleAvailabilityManager initialized: ensure_all_online={self._ensure_all_online}, "
            f"fallback_only_when_offline={self._use_fallback_only_when_offline}"
        )
    
    def initialize(
        self,
        start_warmup: bool = True,
        start_monitoring: bool = True
    ) -> None:
        """
        Initialize all services and start background processes
        
        Args:
            start_warmup: Whether to start warmup process
            start_monitoring: Whether to start monitoring
        """
        if self._initialized:
            logger.warning("Availability manager already initialized")
            return
        
        with self._lock:
            # Initialize services
            self._warmup_service = get_warmup_service()
            self._monitor_service = get_monitor_service()
            self._recovery_service = get_recovery_service()
            self._classifier = get_degraded_classifier()
            
            # Initialize recovery service with monitor
            self._recovery_service.initialize(self._monitor_service)
            
            # Set warmup service reference in recovery service if available
            if hasattr(self._recovery_service, '_warmup_service'):
                self._recovery_service._warmup_service = self._warmup_service
            
            # Start monitoring
            if start_monitoring:
                self._monitor_service.start_monitoring()
            
            # Start warmup in background if requested
            if start_warmup:
                def warmup_background():
                    try:
                        logger.info("Starting module warmup in background...")
                        self._warmup_service.warmup_all_modules(verbose=False)
                        logger.info("Module warmup completed")
                    except Exception as e:
                        logger.error(f"Error in background warmup: {e}", exc_info=True)
                
                thread = threading.Thread(
                    target=warmup_background,
                    daemon=True,
                    name="WarmupBackground"
                )
                thread.start()
            
            # Start background thread to ensure all modules stay online
            if self._ensure_all_online:
                self._start_ensure_online_thread()
            
            self._initialized = True
            logger.info("ModuleAvailabilityManager initialized and services started")
    
    def shutdown(self) -> None:
        """Stop all services"""
        with self._lock:
            self._ensuring_online = False
            if self._ensure_online_thread:
                self._ensure_online_thread.join(timeout=5.0)
            
            if self._monitor_service:
                self._monitor_service.stop_monitoring()
            
            self._initialized = False
            logger.info("ModuleAvailabilityManager shut down")
    
    def _start_ensure_online_thread(self) -> None:
        """Start background thread to ensure all modules stay online"""
        if self._ensuring_online:
            return
        
        self._ensuring_online = True
        
        def ensure_online_loop():
            """Continuously ensure all modules are online"""
            check_interval = float(os.getenv("MAVAIA_ENSURE_ONLINE_INTERVAL", "30.0"))
            
            while self._ensuring_online:
                try:
                    # Get all modules
                    all_modules = ModuleRegistry.list_modules()
                    
                    if not all_modules:
                        time.sleep(check_interval)
                        continue
                    
                    # Check each module and ensure it's online
                    for module_name in all_modules:
                        if not self._ensuring_online:
                            break
                        
                        try:
                            # Check module status
                            if self._monitor_service:
                                status = self._monitor_service.get_module_status(module_name)
                                
                                if status and status.state in (ModuleState.DEGRADED, ModuleState.OFFLINE):
                                    # Module is not online, trigger recovery
                                    logger.info(
                                        f"Module {module_name} is {status.state.value}, "
                                        f"triggering recovery to bring it online"
                                    )
                                    
                                    # Trigger recovery
                                    if self._recovery_service:
                                        self._recovery_service.recover_module(module_name)
                                    
                                    # Also try warmup
                                    if self._warmup_service:
                                        self._warmup_service.warmup_module(module_name, verbose=False)
                            
                            # Also check if module is warmed
                            if self._warmup_service and not self._warmup_service.is_module_warmed(module_name):
                                logger.info(f"Module {module_name} not warmed, warming up...")
                                self._warmup_service.warmup_module(module_name, verbose=False)
                        
                        except Exception as e:
                            logger.debug(f"Error ensuring {module_name} is online: {e}")
                    
                    # Sleep before next check
                    time.sleep(check_interval)
                    
                except Exception as e:
                    logger.error(f"Error in ensure online loop: {e}", exc_info=True)
                    time.sleep(check_interval)
        
        self._ensure_online_thread = threading.Thread(
            target=ensure_online_loop,
            daemon=True,
            name="EnsureOnline"
        )
        self._ensure_online_thread.start()
        logger.info("Started background thread to ensure all modules stay online")
    
    def ensure_module_available(
        self,
        module_name: str,
        timeout: float = 30.0,
        use_fallback: bool = True
    ) -> Tuple[Optional[BaseBrainModule], Optional[str]]:
        """
        Ensure module is available, or get fallback
        
        Args:
            module_name: Name of module
            timeout: Maximum time to wait for module to become available
            use_fallback: Whether to use fallback if primary is degraded
        
        Returns:
            Tuple of (module_instance, actual_module_name)
            actual_module_name may differ if fallback was used
        """
        start_time = time.time()
        
        # Check if module exists
        if not ModuleRegistry.is_module_available(module_name):
            # Try to discover modules if not already discovered
            if not ModuleRegistry._discovered:
                try:
                    ModuleRegistry.discover_modules(background=False, verbose=False)
                except Exception as e:
                    logger.debug(f"Module discovery failed: {e}")
            
            # Check again after discovery attempt
            if not ModuleRegistry.is_module_available(module_name):
                if use_fallback:
                    fallback = self._classifier.get_fallback_module(module_name) if self._classifier else None
                    if fallback:
                        logger.info(f"Module {module_name} not found, using fallback {fallback}")
                        try:
                            module = ModuleRegistry.get_module(fallback, auto_discover=True)
                            if module:
                                return module, fallback
                        except Exception as e:
                            logger.warning(f"Fallback module {fallback} also failed: {e}")
                
                raise ModuleNotFoundError(module_name)
        
        # Wait for module to be available (with timeout)
        while time.time() - start_time < timeout:
            # Check if module is warmed
            if self._warmup_service and not self._warmup_service.is_module_warmed(module_name):
                # Try to warm it up quickly
                try:
                    self._warmup_service.warmup_module(module_name, verbose=False)
                except Exception as e:
                    logger.debug(f"Quick warmup failed for {module_name}: {e}")
            
            # Get module status
            if self._monitor_service:
                status = self._monitor_service.get_module_status(module_name)
                
                if status:
                    if status.state == ModuleState.ONLINE:
                        # Module is online, get it
                        module = ModuleRegistry.get_module(module_name, auto_discover=False)
                        if module:
                            return module, module_name
                    
                    elif status.state in (ModuleState.DEGRADED, ModuleState.OFFLINE):
                        # Module is not online - ensure it comes online instead of using fallback
                        if self._ensure_all_online:
                            # Trigger recovery
                            if self._recovery_service:
                                self._recovery_service.recover_module(module_name)
                            
                            # Also try warmup
                            if self._warmup_service:
                                try:
                                    self._warmup_service.warmup_module(module_name, verbose=False)
                                except Exception:
                                    pass
                            
                            # Wait a bit for recovery to take effect
                            time.sleep(2.0)
                            continue
                        elif use_fallback and not self._use_fallback_only_when_offline:
                            # Only use fallback if not ensuring all online
                            fallback = self._classifier.get_fallback_module(module_name) if self._classifier else None
                            if fallback:
                                logger.info(
                                    f"Module {module_name} is {status.state.value}, using fallback {fallback}"
                                )
                                fallback_module = ModuleRegistry.get_module(
                                    fallback,
                                    auto_discover=True
                                )
                                if fallback_module:
                                    return fallback_module, fallback
            
            # Wait a bit before retrying
            time.sleep(0.5)
        
        # Timeout - if ensuring all online, keep trying in background but raise error
        if self._ensure_all_online:
            # Trigger recovery in background
            if self._recovery_service:
                thread = threading.Thread(
                    target=self._recovery_service.recover_module,
                    args=(module_name,),
                    daemon=True
                )
                thread.start()
            
            logger.warning(
                f"Timeout waiting for {module_name} to come online. "
                f"Recovery is in progress. System will continue ensuring module comes online."
            )
            # Still try to get the module - it might have come online
            module = ModuleRegistry.get_module(module_name, auto_discover=True)
            if module:
                return module, module_name
        
        # Only use fallback if not ensuring all online
        if use_fallback and not self._ensure_all_online:
            fallback = self._classifier.get_fallback_module(module_name) if self._classifier else None
            if fallback:
                logger.warning(
                    f"Timeout waiting for {module_name}, using fallback {fallback}"
                )
                module = ModuleRegistry.get_module(fallback, auto_discover=True)
                if module:
                    return module, fallback
        
        # Last attempt to get module
        module = ModuleRegistry.get_module(module_name, auto_discover=True)
        if module:
            return module, module_name
        
        raise ModuleNotFoundError(module_name)
    
    def get_module_or_fallback(
        self,
        module_name: str,
        operation: Optional[str] = None
    ) -> Tuple[Optional[BaseBrainModule], Optional[str], bool, Optional[str]]:
        """
        Get primary module or automatic fallback
        
        Args:
            module_name: Name of primary module
            operation: Optional operation name
        
        Returns:
            Tuple of (module_instance, actual_module_name, is_fallback, mapped_operation)
            is_fallback indicates if fallback was used
            mapped_operation is the operation name to use (may differ from input if fallback used)
        """
        mapped_operation = operation
        
        # Check if module is available and healthy
        if self._monitor_service:
            status = self._monitor_service.get_module_status(module_name)
            
            if status:
                if status.state == ModuleState.ONLINE:
                    # Module is online, use it
                    module = ModuleRegistry.get_module(module_name, auto_discover=False)
                    if module:
                        return module, module_name, False, operation
                
                elif status.state in (ModuleState.DEGRADED, ModuleState.OFFLINE):
                    # Module is degraded or offline
                    if self._ensure_all_online:
                        # Wait for module to come online instead of using fallback
                        logger.info(
                            f"Module {module_name} is {status.state.value}, "
                            f"waiting for recovery (ensuring all modules online)"
                        )
                        
                        # Trigger recovery immediately
                        if self._recovery_service:
                            self._recovery_service.recover_module(module_name)
                        
                        # Wait for module to come online (with timeout)
                        wait_start = time.time()
                        while (time.time() - wait_start) < self._max_wait_for_module:
                            time.sleep(1.0)
                            
                            # Check status again
                            new_status = self._monitor_service.get_module_status(module_name)
                            if new_status and new_status.state == ModuleState.ONLINE:
                                # Module is now online!
                                logger.info(f"Module {module_name} is now online after recovery")
                                module = ModuleRegistry.get_module(module_name, auto_discover=False)
                                if module:
                                    return module, module_name, False, operation
                        
                        logger.warning(
                            f"Module {module_name} did not come online within {self._max_wait_for_module}s, "
                            f"but continuing to ensure it comes online in background"
                        )
                    
                    # Only use fallback if configured to do so and module is truly offline (not just degraded)
                    if (self._use_fallback_only_when_offline and status.state == ModuleState.OFFLINE) or \
                       (not self._ensure_all_online):
                        fallback = self._classifier.get_fallback_module(module_name, operation) if self._classifier else None
                        if fallback:
                            logger.info(
                                f"Module {module_name} is {status.state.value}, "
                                f"using fallback {fallback}"
                            )
                            fallback_module = ModuleRegistry.get_module(
                                fallback,
                                auto_discover=True
                            )
                            if fallback_module and operation:
                                # Map the operation for the fallback
                                mapped_operation = self._classifier.get_fallback_operation(
                                    module_name, operation, fallback
                                )
                                logger.debug(
                                    f"Mapped operation '{operation}' -> '{mapped_operation}' "
                                    f"for fallback {fallback}"
                                )
                            if fallback_module:
                                return fallback_module, fallback, True, mapped_operation
                    
                    # If we're ensuring all online, wait for module to come online
                    if self._ensure_all_online:
                        # Trigger recovery immediately
                        if self._recovery_service:
                            self._recovery_service.recover_module(module_name)
                        
                        # Also try warmup
                        if self._warmup_service:
                            try:
                                self._warmup_service.warmup_module(module_name, verbose=False)
                            except Exception:
                                pass
                        
                        # Wait for module to come online (with timeout)
                        wait_start = time.time()
                        max_wait = self._max_wait_for_module
                        while (time.time() - wait_start) < max_wait:
                            time.sleep(1.0)
                            
                            # Check status again
                            new_status = self._monitor_service.get_module_status(module_name)
                            if new_status and new_status.state == ModuleState.ONLINE:
                                # Module is now online!
                                logger.info(f"Module {module_name} is now online after recovery")
                                module = ModuleRegistry.get_module(module_name, auto_discover=False)
                                if module:
                                    return module, module_name, False, operation
                            
                            # Trigger recovery again if still not online
                            if new_status and new_status.state in (ModuleState.DEGRADED, ModuleState.OFFLINE):
                                if self._recovery_service:
                                    self._recovery_service.recover_module(module_name)
                        
                        # If still not online after waiting, log but continue trying in background
                        logger.warning(
                            f"Module {module_name} did not come online within {max_wait}s. "
                            f"Recovery continues in background. Returning module anyway."
                        )
        
        # Try to get primary module (even if degraded, we'll use it if available)
        try:
            module = ModuleRegistry.get_module(module_name, auto_discover=True)
            if module:
                # If ensuring all online, we've already tried to recover it
                # Return it anyway - recovery will continue in background
                return module, module_name, False, operation
        except Exception as e:
            logger.debug(f"Failed to get primary module {module_name}: {e}")
        
        # Only use fallback if not ensuring all online
        if not self._ensure_all_online:
            fallback = self._classifier.get_fallback_module(module_name, operation) if self._classifier else None
            if fallback:
                try:
                    fallback_module = ModuleRegistry.get_module(fallback, auto_discover=True)
                    if fallback_module and operation:
                        # Map the operation for the fallback
                        mapped_operation = self._classifier.get_fallback_operation(
                            module_name, operation, fallback
                        )
                        logger.debug(
                            f"Mapped operation '{operation}' -> '{mapped_operation}' "
                            f"for fallback {fallback}"
                        )
                    if fallback_module:
                        return fallback_module, fallback, True, mapped_operation
                except Exception as e:
                    logger.debug(f"Failed to get fallback module {fallback}: {e}")
        
        # If ensuring all online, trigger recovery and return None (caller should retry)
        if self._ensure_all_online:
            if self._recovery_service:
                self._recovery_service.recover_module(module_name)
            logger.warning(
                f"Module {module_name} not available. Recovery in progress. "
                f"System will ensure it comes online."
            )
        
        return None, None, False, None
    
    def get_availability_status(self) -> SystemStatus:
        """
        Get overall system availability status
        
        Returns:
            SystemStatus with summary information
        """
        all_modules = ModuleRegistry.list_modules()
        total_modules = len(all_modules)
        
        available_count = 0
        degraded_count = 0
        offline_count = 0
        warmed_count = 0
        fallback_count = 0
        
        module_details = {}
        
        for module_name in all_modules:
            # Check availability
            status = None
            if self._monitor_service:
                status = self._monitor_service.get_module_status(module_name)
            
            if status:
                if status.state == ModuleState.ONLINE:
                    available_count += 1
                elif status.state == ModuleState.DEGRADED:
                    degraded_count += 1
                elif status.state == ModuleState.OFFLINE:
                    offline_count += 1
            else:
                # Unknown status, assume available if module exists
                if ModuleRegistry.is_module_available(module_name):
                    available_count += 1
            
            # Check if warmed
            if self._warmup_service and self._warmup_service.is_module_warmed(module_name):
                warmed_count += 1
            
            # Check if has fallback
            if self._classifier and self._classifier.get_fallback_module(module_name):
                fallback_count += 1
            
            # Get degradation classification
            degradation = None
            if status and status.state in (ModuleState.DEGRADED, ModuleState.OFFLINE):
                if self._classifier:
                    degradation = self._classifier.classify_degradation(
                        module_name,
                        module_status=status
                    )
            
            module_details[module_name] = {
                "state": status.state.value if status else "unknown",
                "warmed": self._warmup_service.is_module_warmed(module_name) if self._warmup_service else False,
                "has_fallback": self._classifier.get_fallback_module(module_name) is not None if self._classifier else False,
                "degradation": {
                    "type": degradation.degradation_type.value,
                    "reason": degradation.reason
                } if degradation else None
            }
        
        return SystemStatus(
            total_modules=total_modules,
            available_modules=available_count,
            degraded_modules=degraded_count,
            offline_modules=offline_count,
            warmed_modules=warmed_count,
            modules_with_fallbacks=fallback_count,
            details={"modules": module_details}
        )
    
    def force_warmup(self, module_name: str) -> bool:
        """
        Force warmup of a module
        
        Args:
            module_name: Name of module to warm up
        
        Returns:
            True if warmup succeeded, False otherwise
        """
        if not self._warmup_service:
            return False
        
        try:
            result = self._warmup_service.warmup_module(module_name, verbose=True)
            return result.status == WarmupStatus.WARMED
        except Exception as e:
            logger.error(f"Failed to force warmup {module_name}: {e}")
            return False
    
    def register_fallback_mapping(
        self,
        primary: str,
        fallbacks: List[str]
    ) -> None:
        """
        Register custom fallback mapping
        
        Args:
            primary: Name of primary module
            fallbacks: List of fallback module names
        """
        if self._classifier:
            self._classifier.register_fallback_mapping(primary, fallbacks)
    
    def get_fallback_usage_stats(self) -> Dict[str, Any]:
        """
        Get statistics on fallback usage
        
        Returns:
            Dictionary with fallback statistics
        """
        if not self._classifier:
            return {}
        
        return self._classifier.get_fallback_stats()
    
    def are_all_modules_online(self) -> Tuple[bool, Dict[str, Any]]:
        """
        Check if all modules are online
        
        Returns:
            Tuple of (all_online, details)
            all_online is True if all modules are online
            details contains information about offline/degraded modules
        """
        all_modules = ModuleRegistry.list_modules()
        if not all_modules:
            return True, {"message": "No modules registered"}
        
        offline_modules = []
        degraded_modules = []
        online_modules = []
        
        for module_name in all_modules:
            if self._monitor_service:
                status = self._monitor_service.get_module_status(module_name)
                if status:
                    if status.state == ModuleState.ONLINE:
                        online_modules.append(module_name)
                    elif status.state == ModuleState.DEGRADED:
                        degraded_modules.append(module_name)
                    elif status.state == ModuleState.OFFLINE:
                        offline_modules.append(module_name)
                else:
                    # Unknown status - check if module exists
                    if ModuleRegistry.is_module_available(module_name):
                        online_modules.append(module_name)
                    else:
                        offline_modules.append(module_name)
            else:
                # No monitor service - assume online if module exists
                if ModuleRegistry.is_module_available(module_name):
                    online_modules.append(module_name)
                else:
                    offline_modules.append(module_name)
        
        all_online = len(offline_modules) == 0 and len(degraded_modules) == 0
        
        details = {
            "total_modules": len(all_modules),
            "online": len(online_modules),
            "degraded": len(degraded_modules),
            "offline": len(offline_modules),
            "offline_modules": offline_modules,
            "degraded_modules": degraded_modules
        }
        
        return all_online, details


# Global availability manager instance
_global_availability_manager: Optional[ModuleAvailabilityManager] = None


def get_availability_manager() -> ModuleAvailabilityManager:
    """Get global availability manager instance"""
    global _global_availability_manager
    if _global_availability_manager is None:
        _global_availability_manager = ModuleAvailabilityManager()
    return _global_availability_manager

