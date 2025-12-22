"""
Mental Health Safety Service - Comprehensive depression and anxiety detection service
Converted from Swift MentalHealthSafetyService.swift
"""

from typing import Any, Dict, List, Optional
import logging
import time
from enum import Enum

from mavaia_core.brain.base_module import BaseBrainModule, ModuleMetadata
from mavaia_core.brain.registry import ModuleRegistry
from mavaia_core.exceptions import InvalidParameterError

logger = logging.getLogger(__name__)


class MentalHealthSeverity(str, Enum):
    """Mental health severity levels"""
    NONE = "none"
    LOW = "low"
    MODERATE = "moderate"
    HIGH = "high"


class MentalHealthSafetyServiceModule(BaseBrainModule):
    """Comprehensive mental health safety detection service"""

    def __init__(self):
        super().__init__()
        self.safety_framework = None
        self._modules_loaded = False
        self._conversation_history: List[str] = []
        self._max_history_size = 10
        self._previous_personality = None
        self._is_in_therapist_mode = False
        self._switch_timestamp: Optional[float] = None
        self._last_distress_timestamp: Optional[float] = None

    @property
    def metadata(self) -> ModuleMetadata:
        return ModuleMetadata(
            name="mental_health_safety_service",
            version="1.0.0",
            description="Comprehensive depression and anxiety detection service",
            operations=[
                "check_mental_health_risk",
                "suggest_resources",
                "detect_mental_health_distress",
                "check_stability",
            ],
            dependencies=[],
            model_required=False,
        )

    def initialize(self) -> bool:
        """Initialize the module"""
        return True

    def _ensure_modules_loaded(self):
        """Lazy load dependent modules"""
        if self._modules_loaded:
            return

        try:
            self.safety_framework = ModuleRegistry.get_module("safety_framework")

            self._modules_loaded = True
        except Exception as e:
            # Modules not available - will use fallback methods
            logger.debug(
                "Failed to load optional dependency modules for mental_health_safety_service",
                exc_info=True,
                extra={"module_name": "mental_health_safety_service", "error_type": type(e).__name__},
            )

    def execute(self, operation: str, params: Dict[str, Any]) -> Dict[str, Any]:
        """Execute an operation"""
        self._ensure_modules_loaded()

        if operation == "check_mental_health_risk":
            return self._check_mental_health_risk(params)
        elif operation == "suggest_resources":
            return self._suggest_resources(params)
        elif operation == "detect_mental_health_distress":
            return self._detect_mental_health_distress(params)
        elif operation == "check_stability":
            return self._check_stability(params)
        else:
            raise InvalidParameterError(
                parameter="operation",
                value=operation,
                reason="Unknown operation for mental_health_safety_service",
            )

    def _check_mental_health_risk(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """Check input for mental health risk"""
        input_text = params.get("input", "")
        conversation_context = params.get("conversation_context", [])

        detection = self._detect_mental_health_distress({
            "message": input_text,
            "conversation_context": conversation_context,
        })

        return {
            "success": True,
            "detected": detection.get("detected", False),
            "severity": detection.get("severity", MentalHealthSeverity.NONE.value),
            "confidence": detection.get("confidence", 0.0),
            "requires_personality_switch": detection.get("requires_personality_switch", False),
            "response_guidance": detection.get("response_guidance", ""),
            "detected_patterns": detection.get("detected_patterns", []),
        }

    def _suggest_resources(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """Suggest mental health resources"""
        severity = params.get("severity", MentalHealthSeverity.NONE.value)

        resources = []
        if severity == MentalHealthSeverity.HIGH:
            resources = [
                "National Suicide Prevention Lifeline: 988",
                "Crisis Text Line: Text HOME to 741741",
                "Emergency Services: 911",
            ]
        elif severity == MentalHealthSeverity.MODERATE:
            resources = [
                "National Alliance on Mental Illness (NAMI): nami.org",
                "Mental Health America: mhanational.org",
                "Consider speaking with a mental health professional",
            ]
        elif severity == MentalHealthSeverity.LOW:
            resources = [
                "Consider speaking with a trusted friend or family member",
                "Mental Health America: mhanational.org",
            ]

        return {
            "success": True,
            "resources": resources,
        }

    def _detect_mental_health_distress(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """Detect depression and anxiety in user message"""
        message = params.get("message", "").strip()
        conversation_context = params.get("conversation_context", [])

        if not message:
            return {
                "detected": False,
                "severity": MentalHealthSeverity.NONE.value,
                "detected_patterns": [],
                "confidence": 0.0,
                "requires_personality_switch": False,
                "response_guidance": "",
            }

        normalized_message = message.lower()
        detected_patterns = []
        severity_score = 0.0

        # Update conversation history
        self._conversation_history.append(message)
        if len(self._conversation_history) > self._max_history_size:
            self._conversation_history.pop(0)

        # Explicit depression patterns
        explicit_patterns = [
            ("i'm depressed", 0.85, "explicit_depression"),
            ("i am depressed", 0.85, "explicit_depression"),
            ("feeling depressed", 0.85, "explicit_depression"),
            ("have depression", 0.85, "explicit_depression"),
            ("suffering from depression", 0.9, "explicit_depression"),
        ]

        for pattern, score, signal in explicit_patterns:
            if pattern in normalized_message:
                detected_patterns.append(signal)
                severity_score = max(severity_score, score)

        # Anxiety patterns
        anxiety_patterns = [
            ("i'm anxious", 0.75, "explicit_anxiety"),
            ("feeling anxious", 0.75, "explicit_anxiety"),
            ("having anxiety", 0.75, "explicit_anxiety"),
            ("panic attack", 0.85, "panic_attack"),
        ]

        for pattern, score, signal in anxiety_patterns:
            if pattern in normalized_message:
                detected_patterns.append(signal)
                severity_score = max(severity_score, score)

        # Suicidal ideation patterns (HIGH severity)
        suicidal_patterns = [
            ("want to die", 0.95, "suicidal_ideation"),
            ("kill myself", 0.95, "suicidal_ideation"),
            ("end my life", 0.95, "suicidal_ideation"),
            ("not worth living", 0.9, "suicidal_ideation"),
        ]

        for pattern, score, signal in suicidal_patterns:
            if pattern in normalized_message:
                detected_patterns.append(signal)
                severity_score = max(severity_score, score)

        # Determine severity
        if severity_score >= 0.8:
            severity = MentalHealthSeverity.HIGH.value
        elif severity_score >= 0.5:
            severity = MentalHealthSeverity.MODERATE.value
        elif severity_score > 0.0:
            severity = MentalHealthSeverity.LOW.value
        else:
            severity = MentalHealthSeverity.NONE.value

        # Generate response guidance
        response_guidance = self._generate_response_guidance(severity, detected_patterns)

        # Determine if personality switch is needed
        requires_personality_switch = severity in [MentalHealthSeverity.MODERATE.value, MentalHealthSeverity.HIGH.value]

        if requires_personality_switch and not self._is_in_therapist_mode:
            self._is_in_therapist_mode = True
            self._switch_timestamp = time.time()
            self._last_distress_timestamp = time.time()

        return {
            "detected": severity != MentalHealthSeverity.NONE.value,
            "severity": severity,
            "detected_patterns": detected_patterns,
            "confidence": severity_score,
            "requires_personality_switch": requires_personality_switch,
            "response_guidance": response_guidance,
        }

    def _check_stability(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """Check if user is stable (for switching back from therapist mode)"""
        consecutive_calm = params.get("consecutive_calm_messages", 0)
        time_since_distress = params.get("time_since_distress", 0.0)

        # Consider stable if: 5+ calm messages AND 10+ minutes since distress
        is_stable = consecutive_calm >= 5 and time_since_distress >= 600  # 10 minutes

        if is_stable and self._is_in_therapist_mode:
            self._is_in_therapist_mode = False
            self._switch_timestamp = None

        return {
            "success": True,
            "is_stable": is_stable,
            "confidence": 0.8 if is_stable else 0.3,
            "indicators": [
                f"Consecutive calm messages: {consecutive_calm}",
                f"Time since distress: {time_since_distress:.0f}s",
            ],
            "consecutive_calm_messages": consecutive_calm,
            "time_since_distress": time_since_distress,
        }

    def _generate_response_guidance(self, severity: str, patterns: List[str]) -> str:
        """Generate response guidance based on severity"""
        if severity == MentalHealthSeverity.HIGH.value:
            return "High severity detected. Provide immediate support, suggest crisis resources, and switch to therapist personality mode."
        elif severity == MentalHealthSeverity.MODERATE.value:
            return "Moderate severity detected. Provide empathetic support, validate feelings, and consider suggesting professional help."
        elif severity == MentalHealthSeverity.LOW.value:
            return "Low severity detected. Provide gentle support and validation."
        else:
            return ""

