from __future__ import annotations
"""
Advanced Threat Safety Service - Advanced threat detection
Detects prompt injection, routing hijacks, API leakage, safety blind spots, etc.
"""

from typing import Any, Dict, List, Optional
import time
import logging

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

class AdvancedThreatType:
    """Types of advanced threats"""
    PROMPT_INJECTION = "promptInjection"
    ROUTING_HIJACK = "routingHijack"
    API_LEAKAGE = "apiLeakage"
    SAFETY_BLIND_SPOT = "safetyBlindSpot"
    DUAL_USE_EXPLOITATION = "dualUseExploitation"
    CHAIN_OF_THOUGHT_EXTRACTION = "chainOfThoughtExtraction"
    SANDBOX_ESCAPE = "sandboxEscape"
    INFERENCE_DRIFT = "inferenceDrift"


class AdvancedThreatSafetyModule(BaseBrainModule):
    """Advanced threat safety service"""

    def __init__(self):
        super().__init__()
        self.service_id = "advanced_threat_safety"
        self.service_name = "Advanced Threat Safety"
        self.priority = SafetyServicePriority.CRITICAL
        self.check_type = SafetyCheckType.BOTH

    @property
    def metadata(self) -> ModuleMetadata:
        return ModuleMetadata(
            name="advanced_threat_safety",
            version="1.0.0",
            description=(
                "Advanced threat detection: prompt injection, routing hijacks, "
                "API leakage, safety blind spots, dual-use exploitation, "
                "chain-of-thought extraction, sandbox escapes, inference drift"
            ),
            operations=["check_input", "check_response", "detect_advanced_threats"],
            dependencies=[],
            model_required=False,
        )

    def initialize(self) -> bool:
        """Initialize the module"""
        return True

    def execute(self, operation: str, params: Dict[str, Any]) -> Dict[str, Any]:
        """Execute an advanced threat safety operation"""
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
        elif operation == "detect_advanced_threats":
            text = params.get("text", "")
            context_dict = params.get("context", {})
            context = self._dict_to_context(context_dict) if context_dict else None
            is_response = params.get("is_response", False)
            detection = self.detect_advanced_threats(text, context, is_response)
            return detection
        else:
            raise InvalidParameterError(
                parameter="operation",
                value=operation,
                reason="Unknown operation for advanced_threat_safety",
            )

    def check_input(self, input_text: str, context: SafetyCheckContext) -> SafetyCheckResult:
        """Check input for advanced threats"""
        detection = self.detect_advanced_threats(input_text, context, is_response=False)

        if not detection["detected"] or not detection.get("threat_type"):
            return SafetyCheckResult.none(self.service_id, self.service_name)

        blocked_response = self.generate_blocked_response(
            detection["threat_type"], input_text
        )

        return SafetyCheckResult.hard_stop(
            service_id=self.service_id,
            service_name=self.service_name,
            replacement_response=blocked_response,
            confidence=detection.get("confidence", 0.0),
            detected_patterns=detection.get("detected_patterns", []),
            metadata={
                "threatType": detection["threat_type"],
                "severity": detection.get("severity", "none"),
                "timestamp": time.time(),
            },
        )

    def check_response(self, response: str, context: SafetyCheckContext) -> SafetyCheckResult:
        """Check response for advanced threats"""
        detection = self.detect_advanced_threats(response, context, is_response=True)

        if not detection["detected"] or not detection.get("threat_type"):
            return SafetyCheckResult.none(self.service_id, self.service_name)

        user_input = context.conversation_history[-1] if context.conversation_history else ""
        blocked_response = self.generate_blocked_response(detection["threat_type"], user_input)

        return SafetyCheckResult.hard_stop(
            service_id=self.service_id,
            service_name=self.service_name,
            replacement_response=blocked_response,
            confidence=detection.get("confidence", 0.0),
            detected_patterns=detection.get("detected_patterns", []),
            metadata={
                "threatType": detection["threat_type"],
                "severity": detection.get("severity", "none"),
                "checkType": "postCheck",
                "timestamp": time.time(),
            },
        )

    def detect_advanced_threats(
        self,
        text: str,
        context: Optional[SafetyCheckContext] = None,
        is_response: bool = False,
    ) -> Dict[str, Any]:
        """Detect advanced threats in text"""
        trimmed = text.strip()
        if not trimmed:
            return {
                "detected": False,
                "threat_type": None,
                "detected_patterns": [],
                "confidence": 0.0,
                "severity": SafetySeverity.NONE.value,
            }

        normalized = text.lower()
        detected_patterns: List[str] = []
        highest_confidence = 0.0
        detected_type = None
        max_severity = SafetySeverity.NONE

        # Prompt injection detection
        injection_result = self.detect_prompt_injection(normalized)
        if injection_result:
            detected_patterns.extend(injection_result["patterns"])
            if injection_result["confidence"] > highest_confidence:
                highest_confidence = injection_result["confidence"]
                detected_type = AdvancedThreatType.PROMPT_INJECTION
                max_severity = injection_result["severity"]

        # Routing hijack detection
        if context:
            hijack_result = self.detect_routing_hijack(normalized, context)
            if hijack_result:
                detected_patterns.extend(hijack_result["patterns"])
                if hijack_result["confidence"] > highest_confidence:
                    highest_confidence = hijack_result["confidence"]
                    detected_type = AdvancedThreatType.ROUTING_HIJACK
                    max_severity = hijack_result["severity"]

        # API leakage detection (for responses)
        if is_response:
            api_result = self.detect_api_leakage(normalized)
            if api_result:
                detected_patterns.extend(api_result["patterns"])
                if api_result["confidence"] > highest_confidence:
                    highest_confidence = api_result["confidence"]
                    detected_type = AdvancedThreatType.API_LEAKAGE
                    max_severity = api_result["severity"]

        # Chain-of-thought extraction (for responses)
        if is_response:
            cot_result = self.detect_chain_of_thought_extraction(normalized)
            if cot_result:
                detected_patterns.extend(cot_result["patterns"])
                if cot_result["confidence"] > highest_confidence:
                    highest_confidence = cot_result["confidence"]
                    detected_type = AdvancedThreatType.CHAIN_OF_THOUGHT_EXTRACTION
                    max_severity = cot_result["severity"]

        detected = highest_confidence >= 0.6

        return {
            "detected": detected,
            "threat_type": detected_type if detected else None,
            "detected_patterns": list(set(detected_patterns)),
            "confidence": highest_confidence,
            "severity": max_severity.value,
        }

    def detect_prompt_injection(self, text: str) -> Optional[Dict[str, Any]]:
        """Detect prompt injection patterns"""
        patterns = [
            ("ignore previous", 0.9, "instruction_override"),
            ("forget all", 0.9, "instruction_override"),
            ("new instructions", 0.85, "instruction_override"),
            ("override", 0.9, "instruction_override"),
            ("you are now", 0.9, "jailbreak"),
            ("pretend to be", 0.9, "jailbreak"),
        ]

        detected = []
        max_confidence = 0.0

        for pattern, confidence, signal in patterns:
            if pattern in text:
                detected.append(signal)
                max_confidence = max(max_confidence, confidence)

        if detected:
            return {
                "patterns": detected,
                "confidence": max_confidence,
                "severity": SafetySeverity.HIGH if max_confidence >= 0.9 else SafetySeverity.MODERATE,
            }

        return None

    def detect_routing_hijack(self, text: str, context: SafetyCheckContext) -> Optional[Dict[str, Any]]:
        """Detect routing hijack attempts"""
        # Check for attempts to manipulate module routing
        routing_patterns = [
            ("use module", 0.7, "routing_manipulation"),
            ("call module", 0.7, "routing_manipulation"),
            ("execute module", 0.8, "routing_manipulation"),
            ("bypass module", 0.9, "routing_hijack"),
            ("skip module", 0.85, "routing_hijack"),
        ]

        detected = []
        max_confidence = 0.0

        for pattern, confidence, signal in routing_patterns:
            if pattern in text:
                detected.append(signal)
                max_confidence = max(max_confidence, confidence)

        if detected:
            return {
                "patterns": detected,
                "confidence": max_confidence,
                "severity": SafetySeverity.HIGH if max_confidence >= 0.9 else SafetySeverity.MODERATE,
            }

        return None

    def detect_api_leakage(self, text: str) -> Optional[Dict[str, Any]]:
        """Detect API/key leakage in response"""
        api_patterns = [
            ("api key", 0.95, "api_leakage"),
            ("api_key", 0.95, "api_leakage"),
            ("secret key", 0.95, "api_leakage"),
            ("secret_key", 0.95, "api_leakage"),
            ("access token", 0.95, "api_leakage"),
            ("bearer token", 0.95, "api_leakage"),
            ("private key", 0.9, "api_leakage"),
        ]

        detected = []
        max_confidence = 0.0

        for pattern, confidence, signal in api_patterns:
            if pattern in text:
                detected.append(signal)
                max_confidence = max(max_confidence, confidence)

        if detected:
            return {
                "patterns": detected,
                "confidence": max_confidence,
                "severity": SafetySeverity.CRITICAL,
            }

        return None

    def detect_chain_of_thought_extraction(self, text: str) -> Optional[Dict[str, Any]]:
        """Detect chain-of-thought extraction attempts"""
        cot_patterns = [
            ("show your reasoning", 0.85, "cot_extraction"),
            ("show your thinking", 0.85, "cot_extraction"),
            ("reveal your process", 0.85, "cot_extraction"),
            ("internal reasoning", 0.9, "cot_extraction"),
            ("internal thoughts", 0.9, "cot_extraction"),
        ]

        detected = []
        max_confidence = 0.0

        for pattern, confidence, signal in cot_patterns:
            if pattern in text:
                detected.append(signal)
                max_confidence = max(max_confidence, confidence)

        if detected:
            return {
                "patterns": detected,
                "confidence": max_confidence,
                "severity": SafetySeverity.MODERATE,
            }

        return None

    def generate_blocked_response(self, threat_type: str, user_input: str) -> str:
        """Generate blocked response for threat type"""
        responses = {
            AdvancedThreatType.PROMPT_INJECTION: (
                "Request blocked due to suspected prompt-injection attempt. "
                "Please restate your request without instructions to ignore or override prior rules."
            ),
            AdvancedThreatType.ROUTING_HIJACK: (
                "Request blocked due to suspected routing-manipulation attempt. "
                "Please describe the goal rather than instructing internal routing or module selection."
            ),
            AdvancedThreatType.API_LEAKAGE: (
                "Response blocked to prevent disclosure of sensitive credentials or secrets. "
                "If you need help configuring access, provide non-secret configuration details."
            ),
            AdvancedThreatType.CHAIN_OF_THOUGHT_EXTRACTION: (
                "Request blocked: internal reasoning traces are not provided. "
                "I can provide a concise explanation and the final answer instead."
            ),
        }

        return responses.get(
            threat_type,
            "Request blocked due to a detected safety risk. Please rephrase your request.",
        )

    def _dict_to_context(self, context_dict: Dict[str, Any]) -> SafetyCheckContext:
        """Convert dictionary to SafetyCheckContext"""
        return SafetyCheckContext(
            conversation_history=context_dict.get("conversation_history", []),
            conversation_id=context_dict.get("conversation_id"),
            message_id=context_dict.get("message_id"),
            metadata=context_dict.get("metadata", {}),
            timestamp=context_dict.get("timestamp", time.time()),
        )

