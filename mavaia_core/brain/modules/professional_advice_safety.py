from __future__ import annotations
"""
Professional Advice Safety Service - Hard-stop service
Prevents providing professional advice (legal, medical, financial, etc.)
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
)

logger = logging.getLogger(__name__)

class ProfessionalAdviceType:
    """Types of professional advice"""
    LEGAL = "legal"
    MEDICAL = "medical"
    FINANCIAL = "financial"
    THERAPY = "therapy"
    ENGINEERING = "engineering"
    ACCOUNTING = "accounting"


class ProfessionalAdviceSafetyModule(BaseBrainModule):
    """Hard-stop professional advice safety service"""

    def __init__(self):
        super().__init__()
        self.service_id = "professional_advice_safety"
        self.service_name = "Professional Advice Safety"
        self.priority = SafetyServicePriority.CRITICAL
        self.check_type = SafetyCheckType.PRE_CHECK  # Only pre-check

    @property
    def metadata(self) -> ModuleMetadata:
        return ModuleMetadata(
            name="professional_advice_safety",
            version="1.0.0",
            description=(
                "Hard-stop professional advice safety: prevents legal, medical, "
                "financial, therapy, engineering, and accounting advice"
            ),
            operations=["check_input", "detect_professional_advice"],
            dependencies=[],
            model_required=False,
        )

    def initialize(self) -> bool:
        """Initialize the module"""
        return True

    def execute(self, operation: str, params: Dict[str, Any]) -> Dict[str, Any]:
        """Execute a professional advice safety operation"""
        if operation == "check_input":
            input_text = params.get("input", "")
            context_dict = params.get("context", {})
            context = self._dict_to_context(context_dict)
            result = self.check_input(input_text, context)
            return result.to_dict()
        elif operation == "detect_professional_advice":
            text = params.get("text", "")
            detection = self.detect_professional_advice_request(text)
            return detection
        else:
            raise InvalidParameterError(
                parameter="operation",
                value=operation,
                reason="Unknown operation for professional_advice_safety",
            )

    def check_input(self, input_text: str, context: SafetyCheckContext) -> SafetyCheckResult:
        """Check input for professional advice requests"""
        # Check for dangerous topics first
        dangerous_result = self.detect_dangerous_topics(input_text)
        if dangerous_result:
            return dangerous_result

        detection = self.detect_professional_advice_request(input_text)

        if not detection["detected"] or not detection.get("advice_type"):
            return SafetyCheckResult.none(self.service_id, self.service_name)

        blocked_response = self.generate_blocked_response(detection["advice_type"])

        return SafetyCheckResult.hard_stop(
            service_id=self.service_id,
            service_name=self.service_name,
            replacement_response=blocked_response,
            confidence=detection.get("confidence", 0.0),
            detected_patterns=detection.get("detected_patterns", []),
            metadata={
                "adviceType": detection["advice_type"],
                "timestamp": time.time(),
            },
        )

    def detect_dangerous_topics(self, input_text: str) -> Optional[SafetyCheckResult]:
        """Detect dangerous/illegal topics"""
        normalized = input_text.lower()

        dangerous_patterns = [
            ("avoid police", 0.95),
            ("evade police", 0.95),
            ("police surveillance", 0.95),
            ("avoid surveillance", 0.95),
            ("evade surveillance", 0.95),
            ("bypass police", 0.95),
            ("avoid detection", 0.9),
            ("evade detection", 0.9),
            ("disable security", 0.95),
            ("disable security system", 0.95),
            ("tool that could disable", 0.95),
            ("tool to disable", 0.95),
            ("bypass security", 0.95),
            ("disable alarm", 0.9),
            ("bypass alarm", 0.9),
        ]

        for pattern, confidence in dangerous_patterns:
            if pattern in normalized:
                blocked_response = (
                    "Request blocked: it appears to seek assistance with evasion, surveillance, or disabling security. "
                    "I can help with legal, safety-focused alternatives (e.g., personal privacy best practices) instead."
                )

                return SafetyCheckResult.hard_stop(
                    service_id=self.service_id,
                    service_name=self.service_name,
                    replacement_response=blocked_response,
                    confidence=confidence,
                    detected_patterns=[pattern],
                    metadata={"dangerousTopic": pattern, "timestamp": time.time()},
                )

        return None

    def detect_professional_advice_request(self, text: str) -> Dict[str, Any]:
        """Detect professional advice request"""
        trimmed = text.strip()
        if not trimmed:
            return {
                "detected": False,
                "advice_type": None,
                "detected_patterns": [],
                "confidence": 0.0,
            }

        normalized = trimmed.lower()
        detected_patterns: List[str] = []
        highest_confidence = 0.0
        detected_type = None

        # Legal advice patterns
        legal_patterns = [
            ("legal advice", 0.95, "legal_request"),
            ("should i sue", 0.9, "legal_request"),
            ("can i sue", 0.9, "legal_request"),
            ("lawsuit", 0.85, "legal_request"),
            ("legal action", 0.85, "legal_request"),
            ("attorney", 0.8, "legal_request"),
            ("lawyer", 0.8, "legal_request"),
            ("legal counsel", 0.85, "legal_request"),
            ("is this legal", 0.85, "legal_request"),
            ("legal implications", 0.85, "legal_request"),
        ]

        for pattern, confidence, signal in legal_patterns:
            if pattern in normalized:
                detected_patterns.append(signal)
                highest_confidence = max(highest_confidence, confidence)
                detected_type = ProfessionalAdviceType.LEGAL

        # Medical advice patterns
        medical_patterns = [
            ("medical advice", 0.95, "medical_request"),
            ("diagnose", 0.9, "medical_request"),
            ("symptoms", 0.85, "medical_request"),
            ("treatment for", 0.9, "medical_request"),
            ("medicine for", 0.85, "medical_request"),
            ("drug for", 0.85, "medical_request"),
            ("prescription", 0.85, "medical_request"),
            ("should i see a doctor", 0.8, "medical_request"),
            ("is this normal", 0.7, "medical_request"),
            ("health condition", 0.8, "medical_request"),
        ]

        for pattern, confidence, signal in medical_patterns:
            if pattern in normalized:
                detected_patterns.append(signal)
                highest_confidence = max(highest_confidence, confidence)
                detected_type = ProfessionalAdviceType.MEDICAL

        # Financial advice patterns
        financial_patterns = [
            ("financial advice", 0.95, "financial_request"),
            ("investment advice", 0.9, "financial_request"),
            ("should i invest", 0.85, "financial_request"),
            ("stock advice", 0.9, "financial_request"),
            ("trading advice", 0.9, "financial_request"),
            ("crypto advice", 0.85, "financial_request"),
            ("bitcoin", 0.8, "financial_request"),
            ("tax advice", 0.9, "financial_request"),
            ("accounting advice", 0.9, "financial_request"),
        ]

        for pattern, confidence, signal in financial_patterns:
            if pattern in normalized:
                detected_patterns.append(signal)
                highest_confidence = max(highest_confidence, confidence)
                detected_type = ProfessionalAdviceType.FINANCIAL

        # Therapy/clinical psychology patterns
        therapy_patterns = [
            ("therapy advice", 0.9, "therapy_request"),
            ("clinical psychology", 0.9, "therapy_request"),
            ("diagnose my", 0.85, "therapy_request"),
            ("mental health diagnosis", 0.9, "therapy_request"),
            ("psychological evaluation", 0.9, "therapy_request"),
        ]

        for pattern, confidence, signal in therapy_patterns:
            if pattern in normalized:
                detected_patterns.append(signal)
                highest_confidence = max(highest_confidence, confidence)
                detected_type = ProfessionalAdviceType.THERAPY

        # Engineering patterns
        engineering_patterns = [
            ("engineering advice", 0.9, "engineering_request"),
            ("structural advice", 0.9, "engineering_request"),
            ("building design", 0.85, "engineering_request"),
            ("structural integrity", 0.9, "engineering_request"),
        ]

        for pattern, confidence, signal in engineering_patterns:
            if pattern in normalized:
                detected_patterns.append(signal)
                highest_confidence = max(highest_confidence, confidence)
                detected_type = ProfessionalAdviceType.ENGINEERING

        detected = highest_confidence >= 0.7

        return {
            "detected": detected,
            "advice_type": detected_type if detected else None,
            "detected_patterns": list(set(detected_patterns)),
            "confidence": highest_confidence,
        }

    def generate_blocked_response(self, advice_type: str) -> str:
        """Generate blocked response for advice type"""
        responses = {
            ProfessionalAdviceType.LEGAL: (
                "I can’t provide legal advice. For legal guidance, please consult a qualified attorney. "
                "If you share your jurisdiction and the general situation (no sensitive details), I can help explain common concepts."
            ),
            ProfessionalAdviceType.MEDICAL: (
                "I can’t provide medical advice. Please consult a licensed healthcare professional. "
                "If you describe symptoms at a high level, I can share general information and questions to ask a clinician."
            ),
            ProfessionalAdviceType.FINANCIAL: (
                "I can’t provide personalized financial advice. For tailored guidance, consult a licensed financial professional. "
                "I can help explain general financial concepts and risk trade-offs."
            ),
            ProfessionalAdviceType.THERAPY: (
                "I can’t provide therapy or clinical psychological treatment. "
                "If you’re in distress, consider contacting a licensed professional. "
                "I can offer general coping resources and help you find appropriate support options."
            ),
            ProfessionalAdviceType.ENGINEERING: (
                "I can’t provide professional engineering advice for safety-critical decisions. "
                "For structural/building questions, consult a licensed engineer. "
                "I can help with general principles and non-safety-critical explanations."
            ),
        }

        return responses.get(
            advice_type,
            "I can’t provide professional advice on that topic. Please consult a qualified professional. "
            "I can help with general information and terminology if you’d like.",
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

