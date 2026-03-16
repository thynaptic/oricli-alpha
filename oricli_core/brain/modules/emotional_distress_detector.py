from __future__ import annotations
"""
Emotional Distress Detector - Personality-agnostic emotional distress detection service
Converted from Swift EmotionalDistressDetector.swift
"""

from typing import Any, Dict, List, Optional
from enum import Enum
import time
import logging

from oricli_core.brain.base_module import BaseBrainModule, ModuleMetadata
from oricli_core.brain.registry import ModuleRegistry
from oricli_core.exceptions import InvalidParameterError

logger = logging.getLogger(__name__)


class DistressSeverity(str, Enum):
    """Emotional distress severity levels"""
    LOW = "low"
    MODERATE = "moderate"
    HIGH = "high"
    NONE = "none"


class EmotionalDistressDetectorModule(BaseBrainModule):
    """Personality-agnostic emotional distress detector"""

    def __init__(self):
        super().__init__()
        self.emotional_inference = None
        self._modules_loaded = False
        self._conversation_history: List[str] = []
        self._max_history_size = 10

    @property
    def metadata(self) -> ModuleMetadata:
        return ModuleMetadata(
            name="emotional_distress_detector",
            version="1.0.0",
            description="Personality-agnostic emotional distress detection service",
            operations=[
                "detect_distress",
                "assess_risk",
                "track_affective_state",
                "calculate_mood_curve",
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
            self.emotional_inference = ModuleRegistry.get_module("emotional_inference")

            self._modules_loaded = True
        except Exception as e:
            # Modules not available - will use fallback methods
            logger.debug(
                "Failed to load emotional_inference dependency for emotional_distress_detector",
                exc_info=True,
                extra={"module_name": "emotional_distress_detector", "error_type": type(e).__name__},
            )

    def execute(self, operation: str, params: Dict[str, Any]) -> Dict[str, Any]:
        """Execute an operation"""
        self._ensure_modules_loaded()

        if operation == "detect_distress":
            return self._detect_distress(params)
        elif operation == "assess_risk":
            return self._assess_risk(params)
        elif operation == "track_affective_state":
            return self._track_affective_state(params)
        elif operation == "calculate_mood_curve":
            return self._calculate_mood_curve(params)
        else:
            raise InvalidParameterError(
                parameter="operation",
                value=operation,
                reason="Unknown operation for emotional_distress_detector",
            )

    def _detect_distress(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """Detect emotional distress signals in user message"""
        message_raw = params.get("message", "")
        message = str(message_raw).strip()
        conversation_context = params.get("conversation_context", [])
        if conversation_context is None:
            conversation_context = []
        if not isinstance(conversation_context, list):
            raise InvalidParameterError(
                parameter="conversation_context",
                value=str(type(conversation_context).__name__),
                reason="conversation_context must be a list",
            )

        if not message:
            return {
                "success": True,
                "severity": DistressSeverity.NONE.value,
                "detected_signals": [],
                "confidence": 0.0,
                "emotional_keywords": [],
            }

        normalized_message = message.lower()
        detected_signals = []
        emotional_keywords = []
        severity_score = 0.0

        # Update conversation history
        self._conversation_history.append(message)
        if len(self._conversation_history) > self._max_history_size:
            self._conversation_history.pop(0)

        # Distress markers
        distress_markers = [
            # High severity
            ("overwhelmed", 0.8, "overwhelmed"),
            ("hopeless", 0.9, "hopeless"),
            ("can't go on", 0.9, "can't continue"),
            ("end it all", 1.0, "suicidal ideation"),
            ("kill myself", 1.0, "suicidal ideation"),
            ("want to die", 1.0, "suicidal ideation"),
            ("no point", 0.8, "hopelessness"),
            ("nothing matters", 0.8, "hopelessness"),
            ("give up", 0.7, "defeat"),
            # Moderate severity
            ("anxious", 0.6, "anxiety"),
            ("stressed", 0.6, "stress"),
            ("depressed", 0.7, "depression"),
            ("sad", 0.5, "sadness"),
            ("tired", 0.4, "fatigue"),
            ("exhausted", 0.5, "exhaustion"),
            ("can't sleep", 0.5, "sleep issues"),
            ("worried", 0.5, "worry"),
            ("scared", 0.6, "fear"),
            ("afraid", 0.6, "fear"),
            ("panic", 0.7, "panic"),
            ("breakdown", 0.7, "emotional breakdown"),
            ("crying", 0.6, "emotional distress"),
            ("can't cope", 0.7, "coping difficulty"),
            ("struggling", 0.6, "struggle"),
            ("drowning", 0.7, "overwhelmed"),
        ]

        for pattern, score, signal in distress_markers:
            if pattern in normalized_message:
                detected_signals.append(signal)
                emotional_keywords.append(pattern)
                severity_score = max(severity_score, score)

        # Determine severity
        if severity_score >= 0.8:
            severity = DistressSeverity.HIGH.value
        elif severity_score >= 0.5:
            severity = DistressSeverity.MODERATE.value
        elif severity_score > 0.0:
            severity = DistressSeverity.LOW.value
        else:
            severity = DistressSeverity.NONE.value

        return {
            "success": True,
            "severity": severity,
            "detected_signals": detected_signals,
            "confidence": severity_score,
            "emotional_keywords": emotional_keywords,
            "timestamp": time.time(),
        }

    def _assess_risk(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """Assess risk level"""
        detection = self._detect_distress(params)

        severity = detection.get("severity", DistressSeverity.NONE.value)
        risk_level = "none"
        if severity == DistressSeverity.HIGH.value:
            risk_level = "high"
        elif severity == DistressSeverity.MODERATE.value:
            risk_level = "moderate"
        elif severity == DistressSeverity.LOW.value:
            risk_level = "low"

        return {
            "success": True,
            "risk_level": risk_level,
            "severity": severity,
            "recommendations": self._get_recommendations(severity),
        }

    def _track_affective_state(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """Track affective state"""
        user_id = params.get("user_id", "")
        text = params.get("text", "")
        context = params.get("context", "")
        if user_id is None:
            user_id = ""
        if text is None:
            text = ""
        if context is None:
            context = ""
        if not isinstance(user_id, str):
            raise InvalidParameterError("user_id", str(type(user_id).__name__), "user_id must be a string")
        if not isinstance(text, str):
            raise InvalidParameterError("text", str(type(text).__name__), "text must be a string")
        if not isinstance(context, str):
            raise InvalidParameterError("context", str(type(context).__name__), "context must be a string")

        if self.emotional_inference:
            try:
                return self.emotional_inference.execute("track_affective_state", {
                    "user_id": user_id,
                    "text": text,
                    "context": context,
                })
            except Exception as e:
                logger.debug(
                    "emotional_inference track_affective_state failed; using detect_distress fallback",
                    exc_info=True,
                    extra={"module_name": "emotional_distress_detector", "error_type": type(e).__name__},
                )

        # Fallback: use detect_distress
        return self._detect_distress({
            "message": text,
            "conversation_context": [context] if context else [],
        })

    def _calculate_mood_curve(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """Calculate mood curve"""
        user_id = params.get("user_id", "")
        time_window = params.get("time_window", 24)
        if user_id is None:
            user_id = ""
        if not isinstance(user_id, str):
            raise InvalidParameterError("user_id", str(type(user_id).__name__), "user_id must be a string")
        try:
            time_window_int = int(time_window)
        except (TypeError, ValueError):
            raise InvalidParameterError("time_window", str(time_window), "time_window must be an integer")
        if time_window_int < 1:
            raise InvalidParameterError("time_window", str(time_window_int), "time_window must be >= 1")

        if self.emotional_inference:
            try:
                return self.emotional_inference.execute("calculate_mood_curve", {
                    "user_id": user_id,
                    "time_window": time_window_int,
                })
            except Exception as e:
                logger.debug(
                    "emotional_inference calculate_mood_curve failed; using empty curve fallback",
                    exc_info=True,
                    extra={"module_name": "emotional_distress_detector", "error_type": type(e).__name__},
                )

        # Fallback: return empty curve
        return {
            "success": True,
            "mood_curve": [],
            "average_mood": 0.5,
        }

    def _get_recommendations(self, severity: str) -> List[str]:
        """Get recommendations based on severity"""
        if severity == DistressSeverity.HIGH.value:
            return [
                "Consider immediate professional help",
                "Contact crisis support: 988",
                "Reach out to trusted friends or family",
            ]
        elif severity == DistressSeverity.MODERATE.value:
            return [
                "Consider speaking with a mental health professional",
                "Practice self-care activities",
                "Reach out to support network",
            ]
        elif severity == DistressSeverity.LOW.value:
            return [
                "Practice self-care",
                "Consider talking to someone you trust",
            ]
        else:
            return []

