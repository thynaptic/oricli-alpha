from __future__ import annotations
"""
Module Warmup Service

Pre-loads, initializes, tests, and pre-warms all brain modules to ensure
they are ready for use and achieve 0% downtime.
"""

import os
import sys
import threading
import time
import logging
from typing import Dict, List, Optional, Tuple, Any
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum

from oricli_core.brain.registry import ModuleRegistry
from oricli_core.brain.base_module import BaseBrainModule
from oricli_core.exceptions import ModuleInitializationError

logger = logging.getLogger(__name__)


class WarmupStatus(Enum):
    """Warmup status for a module"""
    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    WARMED = "warmed"
    FAILED = "failed"
    SKIPPED = "skipped"


@dataclass
class WarmupResult:
    """Result of warming up a module"""
    module_name: str
    status: WarmupStatus
    start_time: datetime
    end_time: Optional[datetime] = None
    duration: Optional[float] = None
    error: Optional[str] = None
    test_passed: bool = False
    details: Dict[str, Any] = field(default_factory=dict)


class ModuleWarmupService:
    """
    Service for warming up brain modules
    
    Pre-loads, initializes, tests, and pre-warms all modules to ensure
    they are ready for use before requests come in.
    """
    
    def __init__(self):
        """Initialize warmup service"""
        self._warmup_status: Dict[str, WarmupResult] = {}
        self._warmup_lock = threading.RLock()
        
        # Configuration from environment variables
        self._enabled = os.getenv("MAVAIA_WARMUP_ENABLED", "true").lower() in ("true", "1", "yes")
        self._timeout = float(os.getenv("MAVAIA_WARMUP_TIMEOUT", "300.0"))
        self._concurrency = int(os.getenv("MAVAIA_WARMUP_CONCURRENCY", "4"))
        self._test_operations = os.getenv("MAVAIA_WARMUP_TEST_OPERATIONS", "true").lower() in ("true", "1", "yes")
        
        logger.info(
            f"ModuleWarmupService initialized: enabled={self._enabled}, "
            f"timeout={self._timeout}s, concurrency={self._concurrency}, "
            f"test_operations={self._test_operations}"
        )
    
    def warmup_all_modules(
        self,
        modules_dir: Optional[str] = None,
        verbose: bool = False
    ) -> Dict[str, WarmupResult]:
        """
        Warm up all discovered modules
        
        Args:
            modules_dir: Optional modules directory (uses default if not provided)
            verbose: Enable verbose logging
        
        Returns:
            Dictionary mapping module names to warmup results
        """
        if not self._enabled:
            logger.info("Module warmup is disabled")
            return {}
        
        # Ensure modules are discovered
        if not ModuleRegistry.list_modules():
            logger.info("No modules discovered yet, running discovery...")
            ModuleRegistry.discover_modules(modules_dir=modules_dir, verbose=verbose)
        
        module_names = ModuleRegistry.list_modules()
        if not module_names:
            logger.warning("No modules found to warm up")
            return {}
        
        logger.info(f"Starting warmup for {len(module_names)} modules...")
        
        # Warm up modules in discovery order
        load_order = module_names
        
        # Warm up modules in dependency order
        # Use semaphore to limit concurrency
        semaphore = threading.Semaphore(self._concurrency)
        threads = []
        results = {}
        
        def warmup_with_semaphore(module_name: str):
            """Warm up a module with semaphore control"""
            with semaphore:
                result = self.warmup_module(module_name, verbose=verbose)
                with self._warmup_lock:
                    results[module_name] = result
        
        # Start warmup threads
        for module_name in load_order:
            thread = threading.Thread(
                target=warmup_with_semaphore,
                args=(module_name,),
                daemon=True
            )
            thread.start()
            threads.append(thread)
        
        # Wait for all threads to complete
        for thread in threads:
            thread.join(timeout=self._timeout * len(module_names))
        
        # Check for any threads that didn't complete
        for i, thread in enumerate(threads):
            if thread.is_alive():
                module_name = load_order[i]
                logger.warning(f"Warmup for {module_name} did not complete within timeout")
                with self._warmup_lock:
                    if module_name not in results:
                        results[module_name] = WarmupResult(
                            module_name=module_name,
                            status=WarmupStatus.FAILED,
                            start_time=datetime.now(),
                            error="Warmup timeout"
                        )
        
        # Log summary
        warmed = sum(1 for r in results.values() if r.status == WarmupStatus.WARMED)
        failed = sum(1 for r in results.values() if r.status == WarmupStatus.FAILED)
        logger.info(f"Warmup complete: {warmed} warmed, {failed} failed out of {len(results)} modules")
        
        # Retry failed modules (up to max_retries)
        max_retries = int(os.getenv("MAVAIA_WARMUP_MAX_RETRIES", "3"))
        retry_delay = float(os.getenv("MAVAIA_WARMUP_RETRY_DELAY", "5.0"))
        
        failed_modules = [name for name, r in results.items() if r.status == WarmupStatus.FAILED]
        if failed_modules and max_retries > 0:
            logger.info(f"Retrying {len(failed_modules)} failed modules (max {max_retries} retries)...")
            
            for retry_num in range(1, max_retries + 1):
                if not failed_modules:
                    break
                
                logger.info(f"Warmup retry {retry_num}/{max_retries} for {len(failed_modules)} modules...")
                time.sleep(retry_delay)
                
                retry_results = {}
                for module_name in failed_modules.copy():
                    result = self.warmup_module(module_name, verbose=verbose)
                    retry_results[module_name] = result
                    
                    if result.status == WarmupStatus.WARMED:
                        failed_modules.remove(module_name)
                        logger.info(f"Module {module_name} warmed successfully on retry {retry_num}")
                
                results.update(retry_results)
                
                if not failed_modules:
                    logger.info("All modules warmed successfully after retries")
                    break
        
        # Final summary
        final_warmed = sum(1 for r in results.values() if r.status == WarmupStatus.WARMED)
        final_failed = sum(1 for r in results.values() if r.status == WarmupStatus.FAILED)
        logger.info(f"Final warmup status: {final_warmed} warmed, {final_failed} failed out of {len(results)} modules")
        
        with self._warmup_lock:
            self._warmup_status.update(results)
        
        return results
    
    def warmup_module(
        self,
        module_name: str,
        verbose: bool = False
    ) -> WarmupResult:
        """
        Warm up a specific module
        
        Args:
            module_name: Name of module to warm up
            verbose: Enable verbose logging
        
        Returns:
            WarmupResult with status and details
        """
        start_time = datetime.now()
        
        # Check if already warmed
        with self._warmup_lock:
            if module_name in self._warmup_status:
                existing = self._warmup_status[module_name]
                if existing.status == WarmupStatus.WARMED:
                    if verbose:
                        logger.debug(f"Module {module_name} already warmed")
                    return existing
                # If failed or in progress, try again
                if existing.status == WarmupStatus.IN_PROGRESS:
                    # Wait a bit and check again
                    time.sleep(0.5)
                    if module_name in self._warmup_status:
                        existing = self._warmup_status[module_name]
                        if existing.status == WarmupStatus.WARMED:
                            return existing
            
            # Mark as in progress
            result = WarmupResult(
                module_name=module_name,
                status=WarmupStatus.IN_PROGRESS,
                start_time=start_time
            )
            self._warmup_status[module_name] = result
        
        try:
            if verbose:
                logger.info(f"Warming up module: {module_name}")
            
            # Step 1: Ensure module is discovered first
            if not ModuleRegistry.is_module_available(module_name):
                # Try to discover modules if not already discovered
                if not ModuleRegistry._discovered:
                    ModuleRegistry.discover_modules(background=False, verbose=verbose)
                
                # Check again after discovery
                if not ModuleRegistry.is_module_available(module_name):
                    raise ModuleInitializationError(
                        module_name,
                        f"Module not found after discovery. Available modules: {ModuleRegistry.list_modules()[:10]}"
                    )
            
            # Step 2: Get module instance (this will load and initialize if needed)
            try:
                module = ModuleRegistry.get_module(
                    module_name,
                    auto_discover=False,  # Already discovered above
                    wait_timeout=min(self._timeout, 60.0)
                )
            except ModuleNotFoundError as e:
                # Module not found - this shouldn't happen if is_module_available returned True
                raise ModuleInitializationError(
                    module_name,
                    f"Module not found: {e}"
                ) from e
            except Exception as e:
                raise ModuleInitializationError(
                    module_name,
                    f"Failed to get module instance: {e}"
                ) from e
            
            if module is None:
                raise ModuleInitializationError(
                    module_name,
                    "Module instance is None"
                )
            
            # Step 3: Ensure module is initialized
            # Note: get_module() already initializes, but we verify
            if not hasattr(module, '_initialized') or not getattr(module, '_initialized', False):
                # Try to initialize
                try:
                    if not module.initialize():
                        raise ModuleInitializationError(
                            module_name,
                            "initialize() returned False"
                        )
                except Exception as e:
                    raise ModuleInitializationError(
                        module_name,
                        f"Initialization failed: {e}"
                    ) from e
            
            # Step 4: Test with lightweight operation (if enabled)
            test_passed = False
            if self._test_operations:
                test_passed = self._test_module_operation(module, module_name, verbose)
            
            # Step 5: Pre-load resources (execute warmup operations if available)
            warmup_ops_executed = self._preload_resources(module, module_name, verbose)
            
            # Mark as warmed
            end_time = datetime.now()
            duration = (end_time - start_time).total_seconds()
            
            result.status = WarmupStatus.WARMED
            result.end_time = end_time
            result.duration = duration
            result.test_passed = test_passed
            result.details = {
                "warmup_operations_executed": warmup_ops_executed,
                "test_passed": test_passed
            }
            
            if verbose:
                logger.info(f"Module {module_name} warmed successfully in {duration:.2f}s")
            
            return result
            
        except ModuleNotFoundError as e:
            # Module not found - log but don't treat as critical failure
            end_time = datetime.now()
            duration = (end_time - start_time).total_seconds()
            
            error_msg = f"Module not found: {e}"
            logger.warning(f"Module {module_name} not found during warmup: {error_msg}")
            
            result.status = WarmupStatus.FAILED
            result.end_time = end_time
            result.duration = duration
            result.error = error_msg
            result.details["module_not_found"] = True
            
            return result
        except Exception as e:
            end_time = datetime.now()
            duration = (end_time - start_time).total_seconds()
            
            error_msg = str(e)
            error_type = type(e).__name__
            logger.warning(
                f"Failed to warm up module {module_name} ({error_type}): {error_msg}",
                exc_info=verbose  # Only show full traceback if verbose
            )
            
            result.status = WarmupStatus.FAILED
            result.end_time = end_time
            result.duration = duration
            result.error = error_msg
            result.details["error_type"] = error_type
            
            return result
    
    def _test_module_operation(
        self,
        module: BaseBrainModule,
        module_name: str,
        verbose: bool = False
    ) -> bool:
        """
        Test module with a lightweight operation
        
        Args:
            module: Module instance
            module_name: Module name
            verbose: Enable verbose logging
        
        Returns:
            True if test passed, False otherwise
        """
        try:
            metadata = module.metadata
            operations = metadata.operations
            
            if not operations:
                if verbose:
                    logger.debug(f"Module {module_name} has no operations to test")
                return True  # No operations to test, consider it passed
            
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
                # Use minimal test parameters
                test_params = {"test": True}
            
            # Execute test operation with timeout
            start_time = time.time()
            try:
                result = module.execute(test_operation, test_params)
                duration = time.time() - start_time
                
                if verbose:
                    logger.debug(
                        f"Module {module_name} test operation '{test_operation}' "
                        f"completed in {duration:.3f}s"
                    )
                
                return True
                
            except Exception as e:
                if verbose:
                    logger.debug(
                        f"Module {module_name} test operation '{test_operation}' "
                        f"failed: {e}"
                    )
                return False
                
        except Exception as e:
            if verbose:
                logger.debug(f"Failed to test module {module_name}: {e}")
            return False
    
    def _preload_resources(
        self,
        module: BaseBrainModule,
        module_name: str,
        verbose: bool = False
    ) -> int:
        """
        Pre-load heavy resources by executing warmup operations
        
        Args:
            module: Module instance
            module_name: Module name
            verbose: Enable verbose logging
        
        Returns:
            Number of warmup operations executed
        """
        warmup_ops_executed = 0
        
        try:
            metadata = module.metadata
            operations = metadata.operations
            
            # Look for warmup operations
            warmup_operations = [
                op for op in operations
                if "warmup" in op.lower() or "preload" in op.lower()
            ]
            
            if warmup_operations:
                for op in warmup_operations:
                    try:
                        if verbose:
                            logger.debug(f"Executing warmup operation '{op}' for {module_name}")
                        
                        # Execute warmup operation with minimal params
                        module.execute(op, {})
                        warmup_ops_executed += 1
                        
                    except Exception as e:
                        if verbose:
                            logger.debug(
                                f"Warmup operation '{op}' failed for {module_name}: {e}"
                            )
                        # Continue with other warmup operations
                        pass
            else:
                # No explicit warmup operations, try to trigger resource loading
                # by calling a simple operation if available
                if verbose:
                    logger.debug(f"No warmup operations found for {module_name}")
        
        except Exception as e:
            if verbose:
                logger.debug(f"Failed to preload resources for {module_name}: {e}")
        
        return warmup_ops_executed
    
    def get_warmup_status(self) -> Dict[str, WarmupResult]:
        """
        Get warmup status for all modules
        
        Returns:
            Dictionary mapping module names to warmup results
        """
        with self._warmup_lock:
            return self._warmup_status.copy()
    
    def is_module_warmed(self, module_name: str) -> bool:
        """
        Check if a module is warmed
        
        Args:
            module_name: Name of module to check
        
        Returns:
            True if module is warmed, False otherwise
        """
        with self._warmup_lock:
            if module_name not in self._warmup_status:
                return False
            return self._warmup_status[module_name].status == WarmupStatus.WARMED


# Global warmup service instance
_global_warmup_service: Optional[ModuleWarmupService] = None


def get_warmup_service() -> ModuleWarmupService:
    """Get global warmup service instance"""
    global _global_warmup_service
    if _global_warmup_service is None:
        _global_warmup_service = ModuleWarmupService()
    return _global_warmup_service
