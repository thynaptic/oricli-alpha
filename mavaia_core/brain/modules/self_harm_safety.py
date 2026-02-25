from __future__ import annotations
"""
Self-Harm Safety Service - Comprehensive self-harm and suicidal ideation detection
Provides tiered severity assessment and escalation protocols
"""

from typing import Any, Dict, List, Optional
import logging
import time

from mavaia_core.brain.base_module import BaseBrainModule, ModuleMetadata
from mavaia_core.exceptions import InvalidParameterError
from mavaia_core.brain.modules.safety_framework import (
    SafetyServicePriority,
    SafetyCheckType,
    SafetyCheckContext,
    SafetyCheckResult,
    SafetySeverity,
)

logger = logging.getLogger(__name__)

class SelfHarmSeverity:
    """Self-harm severity levels"""
    NONE = "none"
    LOW = "low"
    MODERATE = "moderate"
    HIGH = "high"
    CRITICAL = "critical"


class SelfHarmSafetyModule(BaseBrainModule):
    """Comprehensive self-harm safety detection service"""

    def __init__(self):
        super().__init__()
        self.service_id = "self_harm_safety"
        self.service_name = "Self-Harm Safety"
        self.priority = SafetyServicePriority.CRITICAL
        self.check_type = SafetyCheckType.BOTH
        self.conversation_history: List[str] = []
        self.max_history_size = 10

    @property
    def metadata(self) -> ModuleMetadata:
        return ModuleMetadata(
            name="self_harm_safety",
            version="1.0.0",
            description=(
                "Comprehensive self-harm detection: suicidal ideation, self-harm patterns, "
                "tiered severity assessment, crisis resources, escalation protocols"
            ),
            operations=["check_input", "check_response", "detect_self_harm"],
            dependencies=[],
            model_required=False,
        )

    def initialize(self) -> bool:
        """Initialize the module"""
        return True

    def execute(self, operation: str, params: Dict[str, Any]) -> Dict[str, Any]:
        """Execute a self-harm safety operation"""
        if operation == "check_input":
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
        elif operation == "detect_self_harm":
            text = params.get("text", "")
            context_dict = params.get("context", {})
            context = self._dict_to_context(context_dict) if context_dict else None
            detection = self.detect_self_harm(text, context)
            return detection
        else:
            raise InvalidParameterError(
                parameter="operation",
                value=operation,
                reason="Unknown operation for self_harm_safety",
            )

    def check_input(self, input_text: str, context: SafetyCheckContext) -> SafetyCheckResult:
        """Check input for self-harm content"""
        detection = self.detect_self_harm(input_text, context)

        if not detection["detected"]:
            return SafetyCheckResult.none(self.service_id, self.service_name)

        severity = self._map_severity(detection["severity"])

        if detection.get("requires_escalation", False):
            crisis_response = self.generate_crisis_response(
                detection["severity"], detection.get("crisis_resources", [])
            )

            return SafetyCheckResult.escalation(
                service_id=self.service_id,
                service_name=self.service_name,
                replacement_response=crisis_response,
                severity=severity,
                confidence=detection.get("confidence", 0.0),
                detected_patterns=detection.get("detected_patterns", []),
                response_guidance=detection.get("response_guidance", ""),
                metadata={
                    "selfHarmSeverity": detection["severity"],
                    "requiresEscalation": str(detection.get("requires_escalation", False)),
                    "timestamp": time.time(),
                },
            )

        return SafetyCheckResult.guidance(
            service_id=self.service_id,
            service_name=self.service_name,
            response_guidance=detection.get("response_guidance", ""),
            severity=severity,
            confidence=detection.get("confidence", 0.0),
            detected_patterns=detection.get("detected_patterns", []),
            metadata={
                "selfHarmSeverity": detection["severity"],
                "requiresEscalation": str(detection.get("requires_escalation", False)),
                "timestamp": time.time(),
            },
        )

    def check_response(self, response: str, context: SafetyCheckContext) -> SafetyCheckResult:
        """Check response for harmful content"""
        return self.check_input(response, context)

    def detect_self_harm(
        self, message: str, context: Optional[SafetyCheckContext] = None
    ) -> Dict[str, Any]:
        """Detect self-harm and suicidal ideation"""
        trimmed = message.strip()
        if not trimmed:
            return {
                "detected": False,
                "severity": SelfHarmSeverity.NONE,
                "detected_patterns": [],
                "confidence": 0.0,
                "requires_escalation": False,
                "response_guidance": "",
                "crisis_resources": [],
            }

        normalized = message.lower()
        detected_patterns: List[str] = []
        severity_score = 0.0

        # Update conversation history
        self.conversation_history.append(message)
        if len(self.conversation_history) > self.max_history_size:
            self.conversation_history.pop(0)

        # Explicit self-harm patterns (CRITICAL/HIGH)
        explicit_patterns = [
            ("how to kill myself", 1.0, "explicit_method"),
            ("how to end my life", 1.0, "explicit_method"),
            ("how to commit suicide", 1.0, "explicit_method"),
            ("plan to kill myself", 1.0, "explicit_plan"),
            ("going to kill myself", 1.0, "explicit_plan"),
            ("will kill myself", 1.0, "explicit_intent"),
            ("kill myself", 0.95, "suicidal_ideation"),
            ("end my life", 0.95, "suicidal_ideation"),
            ("commit suicide", 0.95, "suicidal_ideation"),
            ("take my own life", 0.95, "suicidal_ideation"),
            ("hurt myself", 0.85, "self_harm"),
            ("cut myself", 0.85, "self_harm"),
            ("self harm", 0.8, "self_harm"),
            ("suicide", 0.9, "suicidal_ideation"),
            ("kill myself tonight", 0.98, "immediate_danger"),
            ("end my life today", 0.98, "immediate_danger"),
        ]

        for pattern, severity, signal in explicit_patterns:
            if pattern in normalized:
                detected_patterns.append(signal)
                severity_score = max(severity_score, severity)

        # Suicidal ideation patterns (HIGH/MODERATE)
        ideation_patterns = [
            ("want to die", 0.9, "suicidal_ideation"),
            ("wish i was dead", 0.9, "suicidal_ideation"),
            ("better off dead", 0.85, "suicidal_ideation"),
            ("no point living", 0.85, "hopelessness"),
            ("no reason to live", 0.85, "hopelessness"),
            ("nothing to live for", 0.8, "hopelessness"),
            ("don't want to live", 0.9, "suicidal_ideation"),
            ("tired of living", 0.8, "suicidal_ideation"),
            ("can't go on", 0.8, "hopelessness"),
            ("give up on life", 0.85, "hopelessness"),
        ]

        for pattern, severity, signal in ideation_patterns:
            if pattern in normalized:
                detected_patterns.append(signal)
                severity_score = max(severity_score, severity)

        # Indirect expressions (MODERATE/LOW)
        indirect_patterns = [
            ("no one would miss me", 0.7, "worthlessness"),
            ("i'm a burden", 0.7, "burden"),
            ("i'm worthless", 0.6, "worthlessness"),
            ("i'm hopeless", 0.7, "hopelessness"),
            ("there's no hope", 0.7, "hopelessness"),
            ("nothing matters", 0.6, "hopelessness"),
            ("what's the point", 0.6, "hopelessness"),
            ("life is pointless", 0.7, "hopelessness"),
        ]

        for pattern, severity, signal in indirect_patterns:
            if pattern in normalized:
                detected_patterns.append(signal)
                severity_score = max(severity_score, severity)

        # Goodbye messages (HIGH/MODERATE)
        goodbye_patterns = [
            ("goodbye forever", 0.9, "goodbye_message"),
            ("this is my last message", 0.85, "goodbye_message"),
            ("won't be here", 0.8, "goodbye_message"),
            ("you won't hear from me", 0.85, "goodbye_message"),
            ("final message", 0.85, "goodbye_message"),
        ]

        for pattern, severity, signal in goodbye_patterns:
            if pattern in normalized:
                detected_patterns.append(signal)
                severity_score = max(severity_score, severity)

        # Contextual analysis
        context_severity_boost = 0.0
        if context and context.conversation_history:
            context_text = " ".join(context.conversation_history).lower()
            previous_concerns = sum(
                1 for pattern, _, _ in explicit_patterns if pattern in context_text
            )
            if previous_concerns > 0:
                context_severity_boost = min(0.2, previous_concerns * 0.1)

        severity_score = min(1.0, severity_score + context_severity_boost)

        # Determine severity level
        if severity_score >= 0.95:
            severity = SelfHarmSeverity.CRITICAL
        elif severity_score >= 0.8:
            severity = SelfHarmSeverity.HIGH
        elif severity_score >= 0.6:
            severity = SelfHarmSeverity.MODERATE
        elif severity_score >= 0.3:
            severity = SelfHarmSeverity.LOW
        else:
            severity = SelfHarmSeverity.NONE

        confidence = min(1.0, len(detected_patterns) * 0.15 + severity_score * 0.7)
        requires_escalation = severity in (SelfHarmSeverity.CRITICAL, SelfHarmSeverity.HIGH)

        crisis_resources = self.get_crisis_resources()
        response_guidance = self.generate_response_guidance(
            severity, detected_patterns, crisis_resources
        )

        return {
            "detected": severity != SelfHarmSeverity.NONE,
            "severity": severity,
            "detected_patterns": list(set(detected_patterns)),
            "confidence": confidence,
            "requires_escalation": requires_escalation,
            "response_guidance": response_guidance,
            "crisis_resources": crisis_resources,
        }

    def generate_crisis_response(
        self, severity: str, crisis_resources: List[Dict[str, Any]]
    ) -> str:
        """Generate crisis response with resources"""
        if severity == SelfHarmSeverity.CRITICAL:
            return (
                "I’m really concerned about your safety. If you are in immediate danger, call your local emergency number now.\n\n"
                "If you’re in the U.S., you can call or text 988 (Suicide & Crisis Lifeline).\n"
                "You can also text HOME to 741741 (Crisis Text Line).\n\n"
                "You’re not alone. If you want, tell me where you are (country/region) and whether you feel safe right now."
            )
        elif severity == SelfHarmSeverity.HIGH:
            return (
                "I’m concerned about you. Support is available.\n\n"
                "If you’re in the U.S., you can call or text 988 (Suicide & Crisis Lifeline).\n"
                "You can also text HOME to 741741 (Crisis Text Line).\n\n"
                "If you’re outside the U.S., tell me your country/region and I’ll share local crisis resources. Are you safe right now?"
            )
        else:
            return (
                "I’m sorry you’re going through a difficult time. If you feel at risk of harming yourself, please reach out for support.\n\n"
                "If you’re in the U.S., you can call or text 988.\n"
                "You can also text HOME to 741741.\n\n"
                "If you share your country/region, I can help find local resources. If you’d like, tell me what’s been going on."
            )

    def generate_response_guidance(
        self, severity: str, detected_patterns: List[str], crisis_resources: List[Dict[str, Any]]
    ) -> str:
        """Generate guidance for response"""
        if severity == SelfHarmSeverity.CRITICAL:
            return (
                "CRITICAL: User expressing immediate self-harm intent. "
                "Provide crisis resources and empathetic support. "
                "Do not provide methods or encourage harmful behavior."
            )
        elif severity == SelfHarmSeverity.HIGH:
            return (
                "HIGH: User expressing self-harm ideation. "
                "Provide support and crisis resources. "
                "Be empathetic and non-judgmental."
            )
        else:
            return (
                "User expressing distress. "
                "Provide supportive response and resources if appropriate."
            )

    def get_crisis_resources(self) -> List[Dict[str, Any]]:
        """Get crisis resource information"""
        return [
            {
                "name": "National Suicide Prevention Lifeline",
                "phone_number": "988",
                "text_number": None,
                "website": "https://988lifeline.org",
                "description": "24/7 free and confidential support",
                "is_emergency": True,
            },
            {
                "name": "Crisis Text Line",
                "phone_number": None,
                "text_number": "741741",
                "website": "https://www.crisistextline.org",
                "description": "Free 24/7 crisis support via text",
                "is_emergency": True,
            },
        ]

    def _map_severity(self, self_harm_severity: str) -> SafetySeverity:
        """Map SelfHarmSeverity to SafetySeverity"""
        mapping = {
            SelfHarmSeverity.NONE: SafetySeverity.NONE,
            SelfHarmSeverity.LOW: SafetySeverity.LOW,
            SelfHarmSeverity.MODERATE: SafetySeverity.MODERATE,
            SelfHarmSeverity.HIGH: SafetySeverity.HIGH,
            SelfHarmSeverity.CRITICAL: SafetySeverity.CRITICAL,
        }
        return mapping.get(self_harm_severity, SafetySeverity.NONE)

    def _dict_to_context(self, context_dict: Dict[str, Any]) -> SafetyCheckContext:
        """Convert dictionary to SafetyCheckContext"""
        return SafetyCheckContext(
            conversation_history=context_dict.get("conversation_history", []),
            conversation_id=context_dict.get("conversation_id"),
            message_id=context_dict.get("message_id"),
            metadata=context_dict.get("metadata", {}),
            timestamp=context_dict.get("timestamp", time.time()),
        )

