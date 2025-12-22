"""
Degraded Mode Classifier

Classifies degradation reasons and manages automatic fallback routing
for modules that are slow, missing dependencies, or partially loaded.
"""

import os
import json
import logging
from typing import Dict, List, Optional, Any
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from pathlib import Path

from mavaia_core.brain.registry import ModuleRegistry
from mavaia_core.brain.monitor import ModuleStatus, ModuleState
from mavaia_core.brain.health import HealthCheck, HealthStatus

logger = logging.getLogger(__name__)


class DegradationType(Enum):
    """Types of module degradation"""
    SLOW = "slow"
    MISSING_DEPENDENCY = "missing_dependency"
    HALF_LOADED = "half_loaded"
    TIMEOUT = "timeout"
    PARTIAL_FAILURE = "partial_failure"
    OFFLINE = "offline"
    UNKNOWN = "unknown"


@dataclass
class DegradationClassification:
    """Classification of module degradation"""
    module_name: str
    degradation_type: DegradationType
    reason: str
    details: Dict[str, Any] = field(default_factory=dict)
    timestamp: datetime = field(default_factory=datetime.now)


@dataclass
class FallbackStats:
    """Statistics on fallback usage"""
    module_name: str
    fallback_module: str
    total_uses: int = 0
    successful_uses: int = 0
    failed_uses: int = 0
    last_used: Optional[datetime] = None
    average_response_time: Optional[float] = None


class DegradedModeClassifier:
    """
    Classifies degradation reasons and manages fallback routing
    
    Determines why modules are degraded and provides appropriate
    fallback modules for automatic routing.
    """
    
    def __init__(self):
        """Initialize degraded mode classifier"""
        self._fallback_mappings: Dict[str, List[str]] = {}
        self._fallback_stats: Dict[str, Dict[str, FallbackStats]] = {}
        self._operation_mappings: Dict[tuple[str, str], str] = {}  # (primary_module, operation) -> fallback_operation
        self._load_default_mappings()
        self._load_operation_mappings()
        self._load_custom_mappings()
        
        # Configuration from environment variables
        self._enabled = os.getenv("MAVAIA_FALLBACK_ENABLED", "true").lower() in ("true", "1", "yes")
        self._auto_route = os.getenv("MAVAIA_FALLBACK_AUTO_ROUTE", "true").lower() in ("true", "1", "yes")
        
        logger.info(
            f"DegradedModeClassifier initialized: enabled={self._enabled}, "
            f"auto_route={self._auto_route}, mappings={len(self._fallback_mappings)}, "
            f"operation_mappings={len(self._operation_mappings)}"
        )
    
    def _load_default_mappings(self) -> None:
        """Load default fallback mappings"""
        default_mappings = {
            "mcts_search_engine": ["chain_of_thought", "reasoning"],
            "mcts_reasoning": ["chain_of_thought", "reasoning"],
            "mcts_service": ["chain_of_thought", "reasoning"],
            "mcts_reasoning": ["chain_of_thought", "reasoning"],
            "symbolic_solver": ["reasoning", "fallback_heuristics"],
            "symbolic_solver_service": ["reasoning", "fallback_heuristics"],
            "symbolic_reasoning_detector": ["reasoning"],
            "cognitive_generator": ["text_generation_engine", "neural_text_generator"],
            "neural_text_generator": ["text_generation_engine"],
            "text_generation_engine": ["reasoning"],  # Last resort
        }
        
        self._fallback_mappings.update(default_mappings)
        logger.debug(f"Loaded {len(default_mappings)} default fallback mappings")
    
    def _load_operation_mappings(self) -> None:
        """Load default operation mappings for fallbacks"""
        # Map operations from primary modules to fallback module operations
        # Format: (primary_module, primary_operation) -> fallback_operation
        default_operation_mappings = {
            # cognitive_generator -> text_generation_engine
            ("cognitive_generator", "generate_response"): "generate_full_response",
            ("cognitive_generator", "generate"): "generate_full_response",  # Shorthand
            ("cognitive_generator", "generate_response_streaming"): "generate_full_response",
            ("cognitive_generator", "build_thought_graph"): "generate_full_response",  # Fallback to full generation
            ("cognitive_generator", "select_best_thoughts"): "generate_full_response",
            ("cognitive_generator", "convert_to_text"): "generate_full_response",
            # neural_text_generator -> text_generation_engine
            ("neural_text_generator", "generate"): "generate_full_response",
            ("neural_text_generator", "generate_response"): "generate_full_response",
        }
        
        self._operation_mappings.update(default_operation_mappings)
        logger.debug(f"Loaded {len(default_operation_mappings)} default operation mappings")
    
    def _load_custom_mappings(self) -> None:
        """Load custom fallback mappings from file if specified"""
        mappings_file = os.getenv("MAVAIA_FALLBACK_MAPPINGS_FILE")
        if not mappings_file:
            return
        
        try:
            file_path = Path(mappings_file)
            if file_path.exists():
                with open(file_path, "r") as f:
                    custom_mappings = json.load(f)
                    self._fallback_mappings.update(custom_mappings)
                    logger.info(f"Loaded {len(custom_mappings)} custom fallback mappings from {mappings_file}")
        except Exception as e:
            logger.warning(f"Failed to load custom fallback mappings from {mappings_file}: {e}")
    
    def classify_degradation(
        self,
        module_name: str,
        health_check: Optional[HealthCheck] = None,
        module_status: Optional[ModuleStatus] = None
    ) -> DegradationClassification:
        """
        Classify why a module is degraded
        
        Args:
            module_name: Name of module
            health_check: Optional health check result
            module_status: Optional module status from monitor
        
        Returns:
            DegradationClassification with reason and details
        """
        # Start with unknown
        degradation_type = DegradationType.UNKNOWN
        reason = "Unknown degradation reason"
        details = {}
        
        # Check if module is offline
        if module_status and module_status.state == ModuleState.OFFLINE:
            degradation_type = DegradationType.OFFLINE
            reason = module_status.degradation_reason or "Module is offline"
            details["state"] = "offline"
            details["consecutive_failures"] = module_status.consecutive_failures
            return DegradationClassification(
                module_name=module_name,
                degradation_type=degradation_type,
                reason=reason,
                details=details
            )
        
        # Check response time (slow)
        if module_status and module_status.response_time is not None:
            slow_threshold = float(os.getenv("MAVAIA_MONITOR_SLOW_THRESHOLD", "5.0"))
            if module_status.response_time > slow_threshold:
                degradation_type = DegradationType.SLOW
                reason = f"Slow response time: {module_status.response_time:.2f}s (threshold: {slow_threshold}s)"
                details["response_time"] = module_status.response_time
                details["threshold"] = slow_threshold
                return DegradationClassification(
                    module_name=module_name,
                    degradation_type=degradation_type,
                    reason=reason,
                    details=details
                )
        
        # Check health check details
        if health_check:
            checks = health_check.checks or []
            
            # Check for timeout errors
            for check in checks:
                if "timeout" in check.get("message", "").lower():
                    degradation_type = DegradationType.TIMEOUT
                    reason = check.get("message", "Operations timing out")
                    details["check"] = check
                    return DegradationClassification(
                        module_name=module_name,
                        degradation_type=degradation_type,
                        reason=reason,
                        details=details
                    )
            
            # Check for missing dependencies
            for check in checks:
                message = check.get("message", "").lower()
                if any(keyword in message for keyword in ["missing", "dependency", "not found", "import"]):
                    degradation_type = DegradationType.MISSING_DEPENDENCY
                    reason = check.get("message", "Missing dependency")
                    details["check"] = check
                    return DegradationClassification(
                        module_name=module_name,
                        degradation_type=degradation_type,
                        reason=reason,
                        details=details
                    )
            
            # Check for partial failures
            if health_check.status == HealthStatus.DEGRADED:
                # Check failure rate
                for check in checks:
                    if "failure_rate" in check.get("check", ""):
                        failure_rate = check.get("value", 0)
                        if failure_rate > 0:
                            degradation_type = DegradationType.PARTIAL_FAILURE
                            reason = f"High failure rate: {failure_rate:.2%}"
                            details["failure_rate"] = failure_rate
                            details["check"] = check
                            return DegradationClassification(
                                module_name=module_name,
                                degradation_type=degradation_type,
                                reason=reason,
                                details=details
                            )
        
        # Check module status details
        if module_status:
            details_dict = module_status.details or {}
            
            # Check if operation test failed but module exists
            if details_dict.get("operation_test_passed") is False:
                degradation_type = DegradationType.HALF_LOADED
                reason = "Module partially loaded - some operations fail"
                details["operation_error"] = details_dict.get("operation_error")
                return DegradationClassification(
                    module_name=module_name,
                    degradation_type=degradation_type,
                    reason=reason,
                    details=details
                )
        
        # Default to degraded
        if module_status and module_status.state == ModuleState.DEGRADED:
            degradation_type = DegradationType.UNKNOWN
            reason = module_status.degradation_reason or "Module is degraded"
            details["state"] = "degraded"
        
        return DegradationClassification(
            module_name=module_name,
            degradation_type=degradation_type,
            reason=reason,
            details=details
        )
    
    def get_fallback_module(
        self,
        module_name: str,
        operation: Optional[str] = None
    ) -> Optional[str]:
        """
        Get recommended fallback module for a primary module
        
        Args:
            module_name: Name of primary module
            operation: Optional operation name (for operation-specific fallbacks)
        
        Returns:
            Name of fallback module or None if no fallback available
        """
        if not self._enabled:
            return None
        
        # Get fallback chain
        fallback_chain = self._fallback_mappings.get(module_name, [])
        
        if not fallback_chain:
            return None
        
        # Try each fallback in order
        for fallback_name in fallback_chain:
            # Check if fallback module is available
            if ModuleRegistry.is_module_available(fallback_name):
                # Check if fallback supports the operation (if specified)
                if operation:
                    # First check if there's an operation mapping
                    mapped_operation = self._operation_mappings.get((module_name, operation))
                    if mapped_operation:
                        # Check if fallback supports the mapped operation
                        metadata = ModuleRegistry.get_metadata(fallback_name)
                        if metadata and mapped_operation in metadata.operations:
                            return fallback_name
                    else:
                        # No mapping, check if fallback supports original operation
                        metadata = ModuleRegistry.get_metadata(fallback_name)
                        if metadata and operation in metadata.operations:
                            return fallback_name
                else:
                    return fallback_name
        
        # No available fallback found
        return None
    
    def get_fallback_operation(
        self,
        primary_module: str,
        primary_operation: str,
        fallback_module: str
    ) -> str:
        """
        Get the operation name to use for a fallback module
        
        Args:
            primary_module: Name of primary module
            primary_operation: Operation name from primary module
            fallback_module: Name of fallback module
        
        Returns:
            Operation name to use for fallback module (may be mapped)
        """
        # Check if there's a specific mapping
        mapped_operation = self._operation_mappings.get((primary_module, primary_operation))
        if mapped_operation:
            # Verify fallback supports the mapped operation
            metadata = ModuleRegistry.get_metadata(fallback_module)
            if metadata and mapped_operation in metadata.operations:
                return mapped_operation
        
        # Check if fallback supports the original operation
        metadata = ModuleRegistry.get_metadata(fallback_module)
        if metadata and primary_operation in metadata.operations:
            return primary_operation
        
        # Try to find a similar operation (e.g., generate_response -> generate_full_response)
        if metadata:
            # Common operation name patterns
            operation_lower = primary_operation.lower()
            for op in metadata.operations:
                if "generate" in op.lower() and "generate" in operation_lower:
                    return op
                if "response" in op.lower() and "response" in operation_lower:
                    return op
        
        # Return original operation (caller will handle if it fails)
        return primary_operation
    
    def register_fallback_mapping(
        self,
        primary: str,
        fallbacks: List[str]
    ) -> None:
        """
        Register custom fallback chain for a module
        
        Args:
            primary: Name of primary module
            fallbacks: List of fallback module names in order of preference
        """
        self._fallback_mappings[primary] = fallbacks
        logger.info(f"Registered fallback mapping: {primary} -> {fallbacks}")
    
    def register_operation_mapping(
        self,
        primary_module: str,
        primary_operation: str,
        fallback_operation: str
    ) -> None:
        """
        Register operation mapping for fallback routing
        
        Args:
            primary_module: Name of primary module
            primary_operation: Operation name in primary module
            fallback_operation: Operation name to use in fallback module
        """
        self._operation_mappings[(primary_module, primary_operation)] = fallback_operation
        logger.info(
            f"Registered operation mapping: {primary_module}.{primary_operation} -> {fallback_operation}"
        )
    
    def should_use_fallback(
        self,
        module_name: str,
        operation: Optional[str] = None
    ) -> bool:
        """
        Determine if fallback should be used for a module
        
        Args:
            module_name: Name of module
            operation: Optional operation name
        
        Returns:
            True if fallback should be used, False otherwise
        """
        if not self._enabled or not self._auto_route:
            return False
        
        # Check if fallback is available
        fallback = self.get_fallback_module(module_name, operation)
        return fallback is not None
    
    def record_fallback_use(
        self,
        primary_module: str,
        fallback_module: str,
        success: bool,
        response_time: Optional[float] = None
    ) -> None:
        """
        Record fallback usage for statistics
        
        Args:
            primary_module: Name of primary module
            fallback_module: Name of fallback module used
            success: Whether the fallback operation succeeded
            response_time: Optional response time
        """
        if primary_module not in self._fallback_stats:
            self._fallback_stats[primary_module] = {}
        
        if fallback_module not in self._fallback_stats[primary_module]:
            self._fallback_stats[primary_module][fallback_module] = FallbackStats(
                module_name=primary_module,
                fallback_module=fallback_module
            )
        
        stats = self._fallback_stats[primary_module][fallback_module]
        stats.total_uses += 1
        stats.last_used = datetime.now()
        
        if success:
            stats.successful_uses += 1
        else:
            stats.failed_uses += 1
        
        # Update average response time
        if response_time is not None:
            if stats.average_response_time is None:
                stats.average_response_time = response_time
            else:
                # Simple moving average
                stats.average_response_time = (
                    stats.average_response_time * 0.9 + response_time * 0.1
                )
    
    def get_fallback_stats(self) -> Dict[str, Dict[str, FallbackStats]]:
        """
        Get statistics on fallback usage
        
        Returns:
            Dictionary mapping primary module names to fallback statistics
        """
        return {
            primary: {
                fallback: FallbackStats(
                    module_name=stats.module_name,
                    fallback_module=stats.fallback_module,
                    total_uses=stats.total_uses,
                    successful_uses=stats.successful_uses,
                    failed_uses=stats.failed_uses,
                    last_used=stats.last_used,
                    average_response_time=stats.average_response_time
                )
                for fallback, stats in fallbacks.items()
            }
            for primary, fallbacks in self._fallback_stats.items()
        }


# Global classifier instance
_global_classifier: Optional[DegradedModeClassifier] = None


def get_degraded_classifier() -> DegradedModeClassifier:
    """Get global degraded mode classifier instance"""
    global _global_classifier
    if _global_classifier is None:
        _global_classifier = DegradedModeClassifier()
    return _global_classifier

