"""
Safety Framework - Industry-grade safety framework orchestrator
Provides unified interface for all safety services with priority-based execution
Mirrors Swift SafetyFramework.swift functionality
"""

from typing import Any, Dict, List, Optional
import sys
import time
import hashlib
import json
from pathlib import Path
from dataclasses import dataclass, field
from enum import Enum

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent))

from mavaia_core.brain.base_module import BaseBrainModule, ModuleMetadata


# Safety Framework Types (mirroring Swift enums/structs)

class SafetyServicePriority(Enum):
    """Priority levels for safety service execution"""
    CRITICAL = 0  # Hard stops, must run first
    HIGH = 1      # Escalations, important checks
    MEDIUM = 2    # Guidance, moderate importance
    LOW = 3       # Optional checks, low priority


class SafetyCheckType(Enum):
    """When safety checks should run"""
    PRE_CHECK = "preCheck"    # Before response generation
    POST_CHECK = "postCheck"   # After response generation
    BOTH = "both"              # Both pre and post


class SafetyAction(Enum):
    """Safety action to take based on detection"""
    HARD_STOP = "hardStop"    # Block immediately, return replacement response
    ESCALATION = "escalation"  # Critical issue, override normal flow
    GUIDANCE = "guidance"      # Add guidance to context, continue
    ALLOW = "allow"            # No action needed


class SafetySeverity(Enum):
    """Safety severity levels"""
    NONE = "none"
    LOW = "low"
    MODERATE = "moderate"
    HIGH = "high"
    CRITICAL = "critical"


@dataclass
class SafetyCheckContext:
    """Context information for safety checks"""
    conversation_history: List[str] = field(default_factory=list)
    conversation_id: Optional[str] = None
    message_id: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)
    timestamp: float = field(default_factory=time.time)


@dataclass
class SafetyCheckResult:
    """Unified safety check result"""
    service_id: str
    service_name: str
    detected: bool
    action: SafetyAction
    severity: SafetySeverity
    confidence: float
    detected_patterns: List[str] = field(default_factory=list)
    response_guidance: Optional[str] = None
    replacement_response: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)
    timestamp: float = field(default_factory=time.time)

    @property
    def requires_immediate_action(self) -> bool:
        """Check if this result requires immediate action"""
        return self.action in (SafetyAction.HARD_STOP, SafetyAction.ESCALATION)

    @classmethod
    def none(cls, service_id: str, service_name: str) -> "SafetyCheckResult":
        """Create a result indicating no detection"""
        return cls(
            service_id=service_id,
            service_name=service_name,
            detected=False,
            action=SafetyAction.ALLOW,
            severity=SafetySeverity.NONE,
            confidence=0.0,
        )

    @classmethod
    def hard_stop(
        cls,
        service_id: str,
        service_name: str,
        replacement_response: str,
        confidence: float = 1.0,
        detected_patterns: List[str] = None,
        metadata: Dict[str, Any] = None,
    ) -> "SafetyCheckResult":
        """Create a hard stop result"""
        return cls(
            service_id=service_id,
            service_name=service_name,
            detected=True,
            action=SafetyAction.HARD_STOP,
            severity=SafetySeverity.CRITICAL,
            confidence=confidence,
            detected_patterns=detected_patterns or [],
            replacement_response=replacement_response,
            metadata=metadata or {},
        )

    @classmethod
    def escalation(
        cls,
        service_id: str,
        service_name: str,
        replacement_response: str,
        severity: SafetySeverity,
        confidence: float,
        detected_patterns: List[str],
        response_guidance: Optional[str] = None,
        metadata: Dict[str, Any] = None,
    ) -> "SafetyCheckResult":
        """Create an escalation result"""
        return cls(
            service_id=service_id,
            service_name=service_name,
            detected=True,
            action=SafetyAction.ESCALATION,
            severity=severity,
            confidence=confidence,
            detected_patterns=detected_patterns,
            response_guidance=response_guidance,
            replacement_response=replacement_response,
            metadata=metadata or {},
        )

    @classmethod
    def guidance(
        cls,
        service_id: str,
        service_name: str,
        response_guidance: str,
        severity: SafetySeverity,
        confidence: float,
        detected_patterns: List[str] = None,
        metadata: Dict[str, Any] = None,
    ) -> "SafetyCheckResult":
        """Create a guidance result"""
        return cls(
            service_id=service_id,
            service_name=service_name,
            detected=True,
            action=SafetyAction.GUIDANCE,
            severity=severity,
            confidence=confidence,
            detected_patterns=detected_patterns or [],
            response_guidance=response_guidance,
            metadata=metadata or {},
        )

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for JSON serialization"""
        return {
            "service_id": self.service_id,
            "service_name": self.service_name,
            "detected": self.detected,
            "action": self.action.value,
            "severity": self.severity.value,
            "confidence": self.confidence,
            "detected_patterns": self.detected_patterns,
            "response_guidance": self.response_guidance,
            "replacement_response": self.replacement_response,
            "metadata": self.metadata,
            "timestamp": self.timestamp,
        }


class SafetyService:
    """Base class for safety services (mirrors Swift SafetyService protocol)"""
    
    @property
    def service_id(self) -> str:
        """Unique identifier for the service"""
        raise NotImplementedError
    
    @property
    def service_name(self) -> str:
        """Human-readable service name"""
        raise NotImplementedError
    
    @property
    def priority(self) -> SafetyServicePriority:
        """Priority level (determines execution order)"""
        raise NotImplementedError
    
    @property
    def check_type(self) -> SafetyCheckType:
        """When this service should run"""
        raise NotImplementedError
    
    def check_input(self, input_text: str, context: SafetyCheckContext) -> SafetyCheckResult:
        """Check user input for safety issues"""
        raise NotImplementedError
    
    def check_response(self, response: str, context: SafetyCheckContext) -> SafetyCheckResult:
        """Check generated response for safety issues"""
        raise NotImplementedError


class SafetyFrameworkModule(BaseBrainModule):
    """Main safety framework orchestrator"""

    def __init__(self):
        self.services: Dict[str, SafetyService] = {}
        self.service_priorities: Dict[str, SafetyServicePriority] = {}
        self.service_health: Dict[str, Dict[str, Any]] = {}
        self.is_registration_complete = False
        self.framework_start_time = time.time()
        self.startup_delay = 3.0  # 3 seconds after framework creation
        
        # Required critical services
        self.required_critical_services = {
            "prompt_injection_safety",
            "professional_advice_safety",
            "advanced_threat_safety",
            "self_harm_safety",
        }
        
        # Circuit breaker configuration
        self.circuit_breaker_failure_threshold = 3
        self.circuit_breaker_time_window = 60.0  # 60 seconds
        self.circuit_breaker_failure_rate_threshold = 0.5  # 50%
        
        # Timeout configuration
        self.service_timeout = 5.0  # 5 seconds
        self.critical_service_timeout = 3.0  # 3 seconds

    @property
    def metadata(self) -> ModuleMetadata:
        return ModuleMetadata(
            name="safety_framework",
            version="1.0.0",
            description=(
                "Industry-grade safety framework: orchestrates safety services, "
                "priority-based execution, circuit breakers, health monitoring, "
                "pre/post checks, result aggregation"
            ),
            operations=[
                "register_service",
                "check_input",
                "check_response",
                "is_ready",
                "get_service_health",
                "get_registered_services",
            ],
            dependencies=[],
            model_required=False,
        )

    def initialize(self) -> bool:
        """Initialize the framework"""
        return True

    def execute(self, operation: str, params: Dict[str, Any]) -> Dict[str, Any]:
        """Execute a safety framework operation"""
        if operation == "register_service":
            service_data = params.get("service", {})
            return self.register_service(service_data)
        elif operation == "check_input":
            input_text = params.get("input", "")
            context_dict = params.get("context", {})
            context = self._dict_to_context(context_dict)
            result = self.check_input(input_text, context)
            return result.to_dict()
        elif operation == "check_response":
            response = params.get("response", "")
            context_dict = params.get("context", {})
            context = self._dict_to_context(context_dict)
            result = self.check_response(response, context)
            return result.to_dict()
        elif operation == "is_ready":
            return {"ready": self.is_ready()}
        elif operation == "get_service_health":
            service_id = params.get("service_id", "")
            return self.get_service_health(service_id) or {}
        elif operation == "get_registered_services":
            return {"services": list(self.services.keys())}
        else:
            raise ValueError(f"Unknown operation: {operation}")

    def register_service(self, service_data: Dict[str, Any]) -> Dict[str, Any]:
        """Register a safety service"""
        # Create a wrapper service from the data
        service_id = service_data.get("service_id", "")
        if not service_id:
            return {"success": False, "error": "service_id required"}

        # For now, we'll use a simple dict-based service wrapper
        # In production, services would be proper SafetyService instances
        service = DictSafetyService(service_data)
        self.services[service_id] = service
        self.service_priorities[service_id] = SafetyServicePriority(
            service_data.get("priority", 3)
        )

        # Check if all required services are registered
        self._check_registration_complete()

        return {
            "success": True,
            "service_id": service_id,
            "registered": True,
            "is_ready": self.is_ready(),
        }

    def check_input(self, input_text: str, context: SafetyCheckContext) -> SafetyCheckResult:
        """Run all pre-checks on user input"""
        if not self.services:
            return SafetyCheckResult.hard_stop(
                service_id="safety_framework",
                service_name="Safety Framework",
                replacement_response=(
                    "Safety services are not available right now. "
                    "I can’t process this request safely. Please try again in a moment."
                ),
                detected_patterns=["no_services_available"],
                metadata={"error": "no_services_registered"},
            )

        # Get services sorted by priority
        services_to_check = self._get_services_by_priority()

        results: List[SafetyCheckResult] = []

        # Execute checks in priority order
        for service in services_to_check:
            if service.check_type not in (SafetyCheckType.PRE_CHECK, SafetyCheckType.BOTH):
                continue

            service_id = service.service_id
            priority = self.service_priorities.get(service_id, SafetyServicePriority.LOW)
            timeout = (
                self.critical_service_timeout
                if priority == SafetyServicePriority.CRITICAL
                else self.service_timeout
            )

            # Check circuit breaker
            if self._is_service_disabled(service_id):
                continue

            if priority == SafetyServicePriority.CRITICAL and self._should_circuit_break(service_id):
                return SafetyCheckResult.hard_stop(
                    service_id="safety_framework",
                    service_name="Safety Framework",
                    replacement_response=(
                        "Critical safety services are currently unavailable. "
                        "I can’t process this request safely. Please try again in a moment."
                    ),
                    detected_patterns=["circuit_breaker_triggered"],
                    metadata={"failed_service": service_id, "priority": priority.value},
                )

            # Execute check with timeout
            try:
                start_time = time.time()
                result = self._execute_with_timeout(
                    lambda: service.check_input(input_text, context), timeout
                )
                duration = time.time() - start_time
                self._record_service_success(service_id, duration)
                results.append(result)

                # If critical action detected, return immediately
                if result.requires_immediate_action:
                    return result
            except TimeoutError:
                self._record_service_failure(service_id, "timeout")
                if priority == SafetyServicePriority.CRITICAL:
                    results.append(
                        SafetyCheckResult.guidance(
                            service_id=service_id,
                            service_name=service.service_name,
                            response_guidance="Critical safety service timed out. Proceeding with caution.",
                            severity=SafetySeverity.MODERATE,
                            confidence=0.6,
                            detected_patterns=["service_timeout"],
                            metadata={"timeout_seconds": timeout, "priority": priority.value},
                        )
                    )
            except Exception as e:
                self._record_service_failure(service_id, str(e))

        # Aggregate results
        return self._aggregate_results(results, "preCheck", context)

    def check_response(self, response: str, context: SafetyCheckContext) -> SafetyCheckResult:
        """Run all post-checks on generated response"""
        if not self.services:
            return SafetyCheckResult.hard_stop(
                service_id="safety_framework",
                service_name="Safety Framework",
                replacement_response=(
                    "Safety services are not available right now. "
                    "I can’t validate this response safely. Please try again in a moment."
                ),
                detected_patterns=["no_services_available"],
                metadata={"error": "no_services_registered", "checkType": "postCheck"},
            )

        services_to_check = self._get_services_by_priority()
        results: List[SafetyCheckResult] = []

        for service in services_to_check:
            if service.check_type not in (SafetyCheckType.POST_CHECK, SafetyCheckType.BOTH):
                continue

            service_id = service.service_id
            priority = self.service_priorities.get(service_id, SafetyServicePriority.LOW)
            timeout = (
                self.critical_service_timeout
                if priority == SafetyServicePriority.CRITICAL
                else self.service_timeout
            )

            if self._is_service_disabled(service_id):
                continue

            if priority == SafetyServicePriority.CRITICAL and self._should_circuit_break(service_id):
                return SafetyCheckResult.hard_stop(
                    service_id="safety_framework",
                    service_name="Safety Framework",
                    replacement_response=(
                        "Critical safety services are currently unavailable. "
                        "I can’t validate this response safely. Please try again in a moment."
                    ),
                    detected_patterns=["circuit_breaker_triggered"],
                    metadata={
                        "failed_service": service_id,
                        "priority": priority.value,
                        "checkType": "postCheck",
                    },
                )

            try:
                start_time = time.time()
                result = self._execute_with_timeout(
                    lambda: service.check_response(response, context), timeout
                )
                duration = time.time() - start_time
                self._record_service_success(service_id, duration)
                results.append(result)

                if result.requires_immediate_action:
                    return result
            except TimeoutError:
                self._record_service_failure(service_id, "timeout")
                if priority == SafetyServicePriority.CRITICAL:
                    results.append(
                        SafetyCheckResult.hard_stop(
                            service_id=service_id,
                            service_name=service.service_name,
                            replacement_response=(
                                "Safety validation timed out. "
                                "I can’t verify this response right now. Please try again."
                            ),
                            confidence=0.8,
                            detected_patterns=["service_timeout"],
                            metadata={
                                "timeout_seconds": timeout,
                                "priority": priority.value,
                                "checkType": "postCheck",
                            },
                        )
                    )
            except Exception as e:
                self._record_service_failure(service_id, str(e))

        return self._aggregate_results(results, "postCheck", context)

    def is_ready(self) -> bool:
        """Check if framework is ready (all required services registered)"""
        registered_ids = set(self.services.keys())
        all_required = self.required_critical_services.issubset(registered_ids)
        return all_required and self.is_registration_complete

    def get_service_health(self, service_id: str) -> Optional[Dict[str, Any]]:
        """Get service health metrics"""
        if service_id not in self.service_health:
            return None

        health = self.service_health[service_id]
        total_calls = health.get("total_calls", 0)
        total_failures = health.get("total_failures", 0)
        failure_rate = (
            total_failures / total_calls if total_calls > 0 else 0.0
        )

        return {
            "service_id": service_id,
            "total_calls": total_calls,
            "total_failures": total_failures,
            "failure_rate": failure_rate,
            "average_response_time": health.get("average_response_time", 0.0),
            "is_disabled": health.get("is_disabled", False),
            "failure_count": health.get("failure_count", 0),
        }

    def _get_services_by_priority(self) -> List[SafetyService]:
        """Get services sorted by priority"""
        services_with_priority = [
            (service, self.service_priorities.get(service.service_id, SafetyServicePriority.LOW))
            for service in self.services.values()
        ]
        services_with_priority.sort(key=lambda x: x[1].value)
        return [service for service, _ in services_with_priority]

    def _aggregate_results(
        self, results: List[SafetyCheckResult], check_type: str, context: SafetyCheckContext
    ) -> SafetyCheckResult:
        """Aggregate multiple safety check results"""
        if not results:
            return SafetyCheckResult.guidance(
                service_id="safety_framework",
                service_name="Safety Framework",
                response_guidance="All safety services returned no results. Proceeding with caution.",
                severity=SafetySeverity.MODERATE,
                confidence=0.5,
                detected_patterns=["no_results_from_services"],
                metadata={"checkType": check_type, "error": "no_results"},
            )

        # Sort by action priority (hard stop > escalation > guidance > allow)
        def get_action_priority(action: SafetyAction) -> int:
            priorities = {
                SafetyAction.HARD_STOP: 0,
                SafetyAction.ESCALATION: 1,
                SafetyAction.GUIDANCE: 2,
                SafetyAction.ALLOW: 3,
            }
            return priorities.get(action, 3)

        def get_severity_priority(severity: SafetySeverity) -> int:
            priorities = {
                SafetySeverity.CRITICAL: 0,
                SafetySeverity.HIGH: 1,
                SafetySeverity.MODERATE: 2,
                SafetySeverity.LOW: 3,
                SafetySeverity.NONE: 4,
            }
            return priorities.get(severity, 4)

        sorted_results = sorted(
            results,
            key=lambda r: (
                get_action_priority(r.action),
                get_severity_priority(r.severity),
            ),
        )

        top_result = sorted_results[0]

        # If no immediate action, combine guidance
        if not top_result.requires_immediate_action:
            all_guidance = [
                r.response_guidance
                for r in results
                if r.response_guidance
            ]
            combined_guidance = "\n\n".join(all_guidance) if all_guidance else None
            all_patterns = [p for r in results for p in r.detected_patterns]
            max_confidence = max((r.confidence for r in results), default=0.0)
            max_severity = max(
                results, key=lambda r: get_severity_priority(r.severity)
            ).severity

            if combined_guidance or all_patterns:
                return SafetyCheckResult.guidance(
                    service_id="safety_framework",
                    service_name="Safety Framework",
                    response_guidance=combined_guidance or "",
                    severity=max_severity,
                    confidence=max_confidence,
                    detected_patterns=list(set(all_patterns)),
                    metadata={"aggregated_from": [r.service_id for r in results]},
                )

        return top_result

    def _check_registration_complete(self):
        """Check if all required services are registered"""
        registered_ids = set(self.services.keys())
        all_required = self.required_critical_services.issubset(registered_ids)
        if all_required:
            self.is_registration_complete = True

    def _record_service_success(self, service_id: str, duration: float):
        """Record service success for health monitoring"""
        if service_id not in self.service_health:
            self.service_health[service_id] = {
                "total_calls": 0,
                "total_failures": 0,
                "failure_count": 0,
                "response_times": [],
                "is_disabled": False,
            }

        health = self.service_health[service_id]
        health["total_calls"] = health.get("total_calls", 0) + 1
        health.setdefault("response_times", []).append(duration)

        # Keep only recent response times
        if len(health["response_times"]) > 100:
            health["response_times"] = health["response_times"][-100:]

        # Calculate average
        if health["response_times"]:
            health["average_response_time"] = sum(health["response_times"]) / len(
                health["response_times"]
            )

        # Reset failure count on success
        health["failure_count"] = 0

    def _record_service_failure(self, service_id: str, error: str):
        """Record service failure for circuit breaker"""
        if service_id not in self.service_health:
            self.service_health[service_id] = {
                "total_calls": 0,
                "total_failures": 0,
                "failure_count": 0,
                "response_times": [],
                "is_disabled": False,
            }

        health = self.service_health[service_id]
        health["total_calls"] = health.get("total_calls", 0) + 1
        health["total_failures"] = health.get("total_failures", 0) + 1
        health["failure_count"] = health.get("failure_count", 0) + 1

        # Check if service should be disabled
        total_calls = health["total_calls"]
        total_failures = health["total_failures"]
        failure_rate = total_failures / total_calls if total_calls > 0 else 0.0

        if failure_rate >= self.circuit_breaker_failure_rate_threshold:
            health["is_disabled"] = True

    def _should_circuit_break(self, service_id: str) -> bool:
        """Check if circuit breaker should trigger"""
        if service_id not in self.service_health:
            return False

        health = self.service_health[service_id]
        failure_count = health.get("failure_count", 0)

        if failure_count >= self.circuit_breaker_failure_threshold:
            return True

        # Check overall failure rate
        total_calls = health.get("total_calls", 0)
        total_failures = health.get("total_failures", 0)
        failure_rate = total_failures / total_calls if total_calls > 0 else 0.0

        if failure_rate >= self.circuit_breaker_failure_rate_threshold and total_calls >= 10:
            return True

        return False

    def _is_service_disabled(self, service_id: str) -> bool:
        """Check if service is disabled"""
        return self.service_health.get(service_id, {}).get("is_disabled", False)

    def _execute_with_timeout(self, func, timeout: float):
        """Execute function with timeout"""
        import threading

        result_container = {"result": None, "exception": None, "done": False}

        def target():
            try:
                result_container["result"] = func()
            except Exception as e:
                result_container["exception"] = e
            finally:
                result_container["done"] = True

        thread = threading.Thread(target=target)
        thread.daemon = True
        thread.start()
        thread.join(timeout=timeout)

        if not result_container["done"]:
            raise TimeoutError(f"Operation timed out after {timeout}s")

        if result_container["exception"]:
            raise result_container["exception"]

        return result_container["result"]

    def _dict_to_context(self, context_dict: Dict[str, Any]) -> SafetyCheckContext:
        """Convert dictionary to SafetyCheckContext"""
        return SafetyCheckContext(
            conversation_history=context_dict.get("conversation_history", []),
            conversation_id=context_dict.get("conversation_id"),
            message_id=context_dict.get("message_id"),
            metadata=context_dict.get("metadata", {}),
            timestamp=context_dict.get("timestamp", time.time()),
        )


class DictSafetyService(SafetyService):
    """Wrapper to create SafetyService from dictionary data"""

    def __init__(self, service_data: Dict[str, Any]):
        self._service_id = service_data["service_id"]
        self._service_name = service_data.get("service_name", self._service_id)
        self._priority = SafetyServicePriority(service_data.get("priority", 3))
        self._check_type = SafetyCheckType(service_data.get("check_type", "both"))
        self._check_input_func = service_data.get("check_input")
        self._check_response_func = service_data.get("check_response")

    @property
    def service_id(self) -> str:
        return self._service_id

    @property
    def service_name(self) -> str:
        return self._service_name

    @property
    def priority(self) -> SafetyServicePriority:
        return self._priority

    @property
    def check_type(self) -> SafetyCheckType:
        return self._check_type

    def check_input(self, input_text: str, context: SafetyCheckContext) -> SafetyCheckResult:
        if self._check_input_func:
            result_dict = self._check_input_func(input_text, context.to_dict() if hasattr(context, 'to_dict') else context.__dict__)
            return self._dict_to_result(result_dict)
        return SafetyCheckResult.none(self._service_id, self._service_name)

    def check_response(self, response: str, context: SafetyCheckContext) -> SafetyCheckResult:
        if self._check_response_func:
            result_dict = self._check_response_func(response, context.to_dict() if hasattr(context, 'to_dict') else context.__dict__)
            return self._dict_to_result(result_dict)
        return SafetyCheckResult.none(self._service_id, self._service_name)

    def _dict_to_result(self, result_dict: Dict[str, Any]) -> SafetyCheckResult:
        """Convert dictionary to SafetyCheckResult"""
        return SafetyCheckResult(
            service_id=result_dict.get("service_id", self._service_id),
            service_name=result_dict.get("service_name", self._service_name),
            detected=result_dict.get("detected", False),
            action=SafetyAction(result_dict.get("action", "allow")),
            severity=SafetySeverity(result_dict.get("severity", "none")),
            confidence=result_dict.get("confidence", 0.0),
            detected_patterns=result_dict.get("detected_patterns", []),
            response_guidance=result_dict.get("response_guidance"),
            replacement_response=result_dict.get("replacement_response"),
            metadata=result_dict.get("metadata", {}),
        )

