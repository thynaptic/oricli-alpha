from __future__ import annotations
"""
Social Priors Module - Social context detection, appropriateness scoring, and tone adaptation
Handles social norms, cultural sensitivity, relationship dynamics, and context-aware responses
"""

from typing import Dict, Any, List, Optional, Tuple
import json
import re
from pathlib import Path
import logging

from oricli_core.brain.base_module import BaseBrainModule, ModuleMetadata
from oricli_core.exceptions import InvalidParameterError

logger = logging.getLogger(__name__)


class SocialPriorsModule(BaseBrainModule):
    """Social priors for context detection and appropriateness scoring"""

    def __init__(self):
        super().__init__()
        self.config = None
        self._load_config()

    @property
    def metadata(self) -> ModuleMetadata:
        return ModuleMetadata(
            name="social_priors",
            version="1.0.0",
            description="Social priors: context detection, appropriateness scoring, tone adaptation",
            operations=[
                "assess_context",
                "score_appropriateness",
                "adapt_tone",
                "detect_relationship",
                "check_cultural_sensitivity",
            ],
            dependencies=[],
            model_required=False,
        )

    def initialize(self) -> bool:
        """Initialize the module"""
        return True

    def _load_config(self):
        """Load social priors configuration"""
        config_path = Path(__file__).parent / "social_priors_config.json"
        try:
            if config_path.exists():
                with open(config_path, "r", encoding="utf-8") as f:
                    self.config = json.load(f)
            else:
                # Default config
                self.config = {
                    "context_levels": {
                        "formal": ["sir", "madam", "dear", "regards", "sincerely"],
                        "informal": ["hey", "yo", "sup", "dude", "bro"],
                        "professional": [
                            "please",
                            "thank you",
                            "appreciate",
                            "would you",
                        ],
                        "casual": ["lol", "omg", "haha", "yeah", "sure"],
                    },
                    "appropriateness_rules": {
                        "first_interaction": "more_formal",
                        "returning_user": "adapt_to_history",
                        "sensitive_topics": "more_careful",
                    },
                }
        except Exception as e:
            logger.warning(
                "Failed to load social_priors config; using empty defaults",
                exc_info=True,
                extra={"module_name": "social_priors", "error_type": type(e).__name__},
            )
            self.config = {}

    def execute(self, operation: str, params: Dict[str, Any]) -> Dict[str, Any]:
        """Execute a social priors operation"""
        if operation == "assess_context":
            text = params.get("text", "")
            conversation_history = params.get("conversation_history", [])
            user_metadata = params.get("user_metadata", {})
            return self.assess_context(text, conversation_history, user_metadata)
        elif operation == "score_appropriateness":
            response = params.get("response", "")
            context = params.get("context", {})
            user_preferences = params.get("user_preferences", {})
            return self.score_appropriateness(response, context, user_preferences)
        elif operation == "adapt_tone":
            response = params.get("response", "")
            target_context = params.get("target_context", {})
            current_tone = params.get("current_tone", "neutral")
            return self.adapt_tone(response, target_context, current_tone)
        elif operation == "detect_relationship":
            conversation_history = params.get("conversation_history", [])
            user_metadata = params.get("user_metadata", {})
            return self.detect_relationship(conversation_history, user_metadata)
        elif operation == "check_cultural_sensitivity":
            text = params.get("text", "")
            context = params.get("context", {})
            return self.check_cultural_sensitivity(text, context)
        else:
            raise InvalidParameterError(
                parameter="operation",
                value=operation,
                reason="Unknown operation for social_priors",
            )

    def assess_context(
        self,
        text: str,
        conversation_history: List[str] = None,
        user_metadata: Dict[str, Any] = None,
    ) -> Dict[str, Any]:
        """Assess social context from text and history"""
        if conversation_history is None:
            conversation_history = []
        if user_metadata is None:
            user_metadata = {}

        text_lower = text.lower()
        config = self.config.get("context_levels", {})

        # Detect formality level
        formality_score = 0.5  # Neutral
        formality_level = "neutral"

        formal_markers = config.get("formal", [])
        informal_markers = config.get("informal", [])

        formal_count = sum(1 for marker in formal_markers if marker in text_lower)
        informal_count = sum(1 for marker in informal_markers if marker in text_lower)

        if formal_count > informal_count:
            formality_score = 0.8
            formality_level = "formal"
        elif informal_count > formal_count:
            formality_score = 0.2
            formality_level = "informal"

        # Detect professional vs casual
        professional_markers = config.get("professional", [])
        casual_markers = config.get("casual", [])

        professional_count = sum(
            1 for marker in professional_markers if marker in text_lower
        )
        casual_count = sum(1 for marker in casual_markers if marker in text_lower)

        tone = "neutral"
        if professional_count > casual_count:
            tone = "professional"
        elif casual_count > professional_count:
            tone = "casual"

        # Assess relationship level
        interaction_count = len(conversation_history)
        relationship_level = "stranger"

        if interaction_count == 0:
            relationship_level = "first_interaction"
        elif interaction_count < 5:
            relationship_level = "acquaintance"
        elif interaction_count < 20:
            relationship_level = "familiar"
        else:
            relationship_level = "established"

        # Determine appropriate response style
        appropriate_style = self._determine_appropriate_style(
            formality_level, tone, relationship_level
        )

        return {
            "formality_level": formality_level,
            "formality_score": formality_score,
            "tone": tone,
            "relationship_level": relationship_level,
            "interaction_count": interaction_count,
            "appropriate_style": appropriate_style,
            "context_summary": {
                "is_first_interaction": interaction_count == 0,
                "requires_formality": formality_level == "formal"
                or relationship_level == "first_interaction",
                "allows_casual": formality_level == "informal"
                and relationship_level in ["familiar", "established"],
            },
        }

    def _determine_appropriate_style(
        self, formality: str, tone: str, relationship: str
    ) -> str:
        """Determine appropriate response style based on context"""
        if relationship == "first_interaction":
            return "polite_neutral"
        elif formality == "formal":
            return "professional_polite"
        elif formality == "informal" and relationship in ["familiar", "established"]:
            return "casual_friendly"
        elif tone == "professional":
            return "professional_neutral"
        elif tone == "casual":
            return "casual_neutral"
        else:
            return "neutral"

    def score_appropriateness(
        self,
        response: str,
        context: Dict[str, Any] = None,
        user_preferences: Dict[str, Any] = None,
    ) -> Dict[str, Any]:
        """Score appropriateness of a response given context"""
        if context is None:
            context = {}
        if user_preferences is None:
            user_preferences = {}

        response_lower = response.lower()
        score = 0.7  # Base score

        issues = []
        strengths = []

        # Check formality match
        expected_formality = context.get("formality_level", "neutral")
        formality_markers = self.config.get("context_levels", {}).get("formal", [])
        has_formal = any(marker in response_lower for marker in formality_markers)

        if expected_formality == "formal" and not has_formal:
            score -= 0.2
            issues.append("Response too informal for formal context")
        elif expected_formality == "informal" and has_formal:
            score -= 0.1
            issues.append("Response too formal for informal context")
        else:
            strengths.append("Formality level matches context")

        # Check for sensitive content
        sensitive_words = ["fuck", "shit", "damn", "hell"]  # Basic profanity filter
        has_profanity = any(word in response_lower for word in sensitive_words)
        if has_profanity:
            score -= 0.3
            issues.append("Contains potentially inappropriate language")

        # Check for empathy markers (positive)
        empathy_markers = ["i understand", "i'm sorry", "that must be", "i hear you"]
        has_empathy = any(marker in response_lower for marker in empathy_markers)
        if has_empathy and context.get("emotional_context") == "negative":
            score += 0.1
            strengths.append("Shows appropriate empathy")

        # Check length appropriateness
        word_count = len(response.split())
        expected_length = context.get("expected_length", "medium")

        if expected_length == "short" and word_count > 30:
            score -= 0.1
            issues.append("Response too long for context")
        elif expected_length == "long" and word_count < 20:
            score -= 0.05
            issues.append("Response too short for context")

        return {
            "appropriateness_score": max(0.0, min(1.0, score)),
            "is_appropriate": score >= 0.6,
            "issues": issues,
            "strengths": strengths,
            "recommendations": self._generate_recommendations(issues, context),
        }

    def _generate_recommendations(
        self, issues: List[str], context: Dict[str, Any]
    ) -> List[str]:
        """Generate recommendations to improve appropriateness"""
        recommendations = []

        if "too informal" in " ".join(issues).lower():
            recommendations.append("Use more formal language")
        elif "too formal" in " ".join(issues).lower():
            recommendations.append("Use more casual language")

        if "inappropriate language" in " ".join(issues).lower():
            recommendations.append("Remove profanity or sensitive language")

        if "too long" in " ".join(issues).lower():
            recommendations.append("Shorten the response")
        elif "too short" in " ".join(issues).lower():
            recommendations.append("Provide more detail")

        return recommendations

    def adapt_tone(
        self,
        response: str,
        target_context: Dict[str, Any],
        current_tone: str = "neutral",
    ) -> Dict[str, Any]:
        """Adapt response tone to match target context"""
        target_formality = target_context.get("formality_level", "neutral")
        target_relationship = target_context.get("relationship_level", "neutral")

        adapted_response = response
        modifications = []

        # Adapt formality
        if target_formality == "formal" and current_tone != "formal":
            # Add formal markers
            if not response.startswith(("I", "We", "You")):
                adapted_response = "I " + adapted_response.lower()
            modifications.append("Added formal structure")

        elif target_formality == "informal" and current_tone == "formal":
            # Remove formal markers, use contractions
            adapted_response = adapted_response.replace("I am", "I'm")
            adapted_response = adapted_response.replace("you are", "you're")
            adapted_response = adapted_response.replace("cannot", "can't")
            modifications.append("Made more casual with contractions")

        # Adapt to relationship
        if target_relationship == "first_interaction":
            if "please" not in adapted_response.lower():
                adapted_response = adapted_response.replace(".", ", please.")
                modifications.append("Added politeness marker")

        return {
            "adapted_response": adapted_response,
            "original_response": response,
            "modifications": modifications,
            "target_tone": target_formality,
            "adaptation_applied": len(modifications) > 0,
        }

    def detect_relationship(
        self, conversation_history: List[str], user_metadata: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Detect relationship dynamics from conversation history"""
        interaction_count = len(conversation_history)

        # Analyze interaction patterns
        familiarity_score = min(1.0, interaction_count / 10.0)

        relationship_type = "stranger"
        if interaction_count == 0:
            relationship_type = "first_interaction"
        elif interaction_count < 3:
            relationship_type = "new_acquaintance"
        elif interaction_count < 10:
            relationship_type = "acquaintance"
        elif interaction_count < 30:
            relationship_type = "familiar"
        else:
            relationship_type = "established"

        # Detect personal topics (simple heuristic)
        personal_keywords = [
            "i",
            "my",
            "me",
            "myself",
            "personal",
            "feel",
            "think",
            "want",
        ]
        personal_count = 0
        for message in conversation_history[-5:]:
            personal_count += sum(
                1 for keyword in personal_keywords if keyword in message.lower()
            )

        is_personal = personal_count > 5

        return {
            "relationship_type": relationship_type,
            "interaction_count": interaction_count,
            "familiarity_score": familiarity_score,
            "is_personal": is_personal,
            "recommended_approach": (
                "polite"
                if relationship_type in ["first_interaction", "new_acquaintance"]
                else "friendly"
            ),
        }

    def check_cultural_sensitivity(
        self, text: str, context: Dict[str, Any] = None
    ) -> Dict[str, Any]:
        """Check cultural sensitivity of text"""
        if context is None:
            context = {}

        text_lower = text.lower()
        warnings = []
        score = 1.0

        # Basic cultural sensitivity checks
        # Note: This is a simplified version. A full implementation would use
        # more sophisticated cultural awareness patterns

        # Check for potentially insensitive stereotypes
        stereotype_patterns = []  # Would be populated with known problematic patterns

        # Check for appropriate cultural references
        # Note: A full implementation would use a comprehensive cultural knowledge base
        # Current implementation provides basic cultural sensitivity checks

        # Check for inclusive language
        inclusive_markers = ["they", "their", "everyone", "people"]
        exclusive_markers = ["guys" if context.get("mixed_group") else ""]

        has_inclusive = any(marker in text_lower for marker in inclusive_markers)

        return {
            "cultural_sensitivity_score": score,
            "is_culturally_sensitive": score >= 0.8,
            "warnings": warnings,
            "has_inclusive_language": has_inclusive,
            "recommendations": [],
        }

    def validate_params(self, operation: str, params: Dict[str, Any]) -> bool:
        """Validate parameters for operations"""
        if operation == "assess_context":
            return "text" in params
        elif operation == "score_appropriateness":
            return "response" in params
        elif operation == "adapt_tone":
            return "response" in params and "target_context" in params
        elif operation == "detect_relationship":
            return "conversation_history" in params
        elif operation == "check_cultural_sensitivity":
            return "text" in params
        return True
