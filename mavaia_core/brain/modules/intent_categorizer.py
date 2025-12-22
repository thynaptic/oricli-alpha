"""
Intent Categorizer - Intent categorization system for personality response generation
Converted from Swift IntentCategorizer.swift
"""

from typing import Any, Dict, List, Optional
from enum import Enum
import sys
from pathlib import Path

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent))

from mavaia_core.brain.base_module import BaseBrainModule, ModuleMetadata


class IntentCategory(str, Enum):
    """Intent categories"""
    GREETING = "greeting"
    SHARING_NEWS = "sharingNews"
    ASKING_FOR_HELP = "askingForHelp"
    EXPRESSING_EMOTION = "expressingEmotion"
    EMOTIONAL_DISTRESS = "emotionalDistress"
    MENTAL_HEALTH_SUPPORT = "mentalHealthSupport"
    REQUESTING_INFORMATION = "requestingInformation"
    CASUAL_CONVERSATION = "casualConversation"
    OTHER = "other"


class IntentCategorizerModule(BaseBrainModule):
    """Intent categorization system for personality response generation"""

    def __init__(self):
        self.intent_correction = None
        self._modules_loaded = False

    @property
    def metadata(self) -> ModuleMetadata:
        return ModuleMetadata(
            name="intent_categorizer",
            version="1.0.0",
            description="Intent categorization system for personality response generation",
            operations=[
                "categorize_intent",
                "detect_intent",
                "categorize_with_normalization",
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
            from mavaia_core.brain.registry import ModuleRegistry

            self.intent_correction = ModuleRegistry.get_module("intent_correction")

            self._modules_loaded = True
        except Exception as e:
            # Modules not available - will use fallback methods
            pass

    def execute(self, operation: str, params: Dict[str, Any]) -> Dict[str, Any]:
        """Execute an operation"""
        self._ensure_modules_loaded()

        if operation == "categorize_intent":
            return self._categorize_intent(params)
        elif operation == "detect_intent":
            return self._detect_intent(params)
        elif operation == "categorize_with_normalization":
            return self._categorize_with_normalization(params)
        else:
            raise ValueError(f"Unknown operation: {operation}")

    def _categorize_intent(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """Categorize an intent string"""
        intent = params.get("intent", "")
        user_message = params.get("user_message")

        # Try normalization first if available
        normalized_intent = intent
        if self.intent_correction:
            try:
                result = self.intent_correction.execute("normalize_intent", {
                    "text": intent,
                    "context": user_message or "",
                })
                normalized_intent = result.get("normalized", intent)
            except:
                pass

        # Categorize
        classification = self._categorize_with_normalized(normalized_intent, intent, user_message)

        return {
            "success": True,
            "category": classification["category"],
            "subcategory": classification.get("subcategory"),
            "confidence": classification["confidence"],
        }

    def _detect_intent(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """Detect intent (alias for categorize_intent)"""
        return self._categorize_intent(params)

    def _categorize_with_normalization(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """Categorize with normalization"""
        return self._categorize_intent(params)

    def _categorize_with_normalized(
        self, normalized_intent: str, original_intent: str, user_message: Optional[str]
    ) -> Dict[str, Any]:
        """Categorize with normalized intent"""
        normalized_lower = normalized_intent.lower()
        message_lower = (user_message or "").lower()

        # Check for greeting
        if (
            "greeting" in normalized_lower
            or "greet" in normalized_lower
            or normalized_lower == "greet"
            or "social" in normalized_lower
            or any(word in message_lower for word in ["hello", "hi", "hey"])
        ):
            return {
                "category": IntentCategory.GREETING.value,
                "confidence": 0.9,
            }

        # Check for sharing news
        if any(
            word in normalized_lower
            for word in ["sharing", "surprising", "excitement", "unexpected", "news", "guess what", "happened"]
        ) or "you'll never guess" in message_lower:
            return {
                "category": IntentCategory.SHARING_NEWS.value,
                "confidence": 0.9,
            }

        # Check for asking for help
        if (
            any(word in normalized_lower for word in ["help", "assist", "support", "need help", "can you help"])
            or any(word in message_lower for word in ["help", "can you", "assist"])
        ):
            return {
                "category": IntentCategory.ASKING_FOR_HELP.value,
                "confidence": 0.85,
            }

        # Check for emotional distress (high severity)
        if any(
            word in normalized_lower
            for word in ["overwhelmed", "hopeless", "can't go on", "no point", "nothing matters", "give up"]
        ) or any(word in message_lower for word in ["overwhelmed", "hopeless", "can't go on", "no point"]):
            return {
                "category": IntentCategory.EMOTIONAL_DISTRESS.value,
                "subcategory": "high",
                "confidence": 0.9,
            }

        # Check for expressing emotion
        if any(word in normalized_lower for word in ["happy", "excited", "great", "amazing", "wonderful", "positive"]):
            return {
                "category": IntentCategory.EXPRESSING_EMOTION.value,
                "subcategory": "positive",
                "confidence": 0.8,
            }

        if any(word in normalized_lower for word in ["sad", "frustrated", "angry", "upset", "disappointed", "negative"]):
            return {
                "category": IntentCategory.EXPRESSING_EMOTION.value,
                "subcategory": "negative",
                "confidence": 0.8,
            }

        # Default to casual conversation
        return {
            "category": IntentCategory.CASUAL_CONVERSATION.value,
            "confidence": 0.5,
        }

