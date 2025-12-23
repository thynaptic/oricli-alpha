"""
Conversational Defaults Module - Default responses and behaviors for common scenarios
Handles context-appropriate defaults, personality-aware defaults, and fallback responses
"""

from typing import Dict, Any, List, Optional
import json
import random
from pathlib import Path
import logging

from mavaia_core.brain.base_module import BaseBrainModule, ModuleMetadata
from mavaia_core.exceptions import InvalidParameterError

logger = logging.getLogger(__name__)


class ConversationalDefaultsModule(BaseBrainModule):
    """Default responses and behaviors for conversational scenarios"""

    def __init__(self):
        super().__init__()
        self.config = None
        self.defaults = {}
        self.personality_defaults = {}
        self._load_config()

    @property
    def metadata(self) -> ModuleMetadata:
        return ModuleMetadata(
            name="conversational_defaults",
            version="1.0.0",
            description="Conversational defaults: default responses, context-appropriate defaults, personality-aware defaults",
            operations=[
                "get_default_response",
                "generate_fallback",
                "adapt_default",
                "get_scenario_default",
                "get_personality_default",
            ],
            dependencies=[],
            model_required=False,
        )

    def initialize(self) -> bool:
        """Initialize the module"""
        return True

    def _load_config(self):
        """Load conversational defaults configuration"""
        config_path = Path(__file__).parent / "conversational_defaults.json"
        try:
            if config_path.exists():
                with open(config_path, "r", encoding="utf-8") as f:
                    self.config = json.load(f)
                    self.defaults = self.config.get("defaults", {})
                    self.personality_defaults = self.config.get(
                        "personality_defaults", {}
                    )
            else:
                # Default config
                self.defaults = {
                    "greeting": [
                        "Hello! How can I help you?",
                        "Hi there! What's on your mind?",
                        "Hey! What can I do for you?",
                    ],
                    "acknowledgment": ["I see.", "Got it.", "Understood.", "Okay."],
                    "clarification": [
                        "Could you clarify that?",
                        "I'm not sure I understand.",
                        "Can you tell me more?",
                    ],
                    "apology": [
                        "I'm sorry about that.",
                        "My apologies.",
                        "Sorry for the confusion.",
                    ],
                    "confirmation": [
                        "Yes, that's right.",
                        "Exactly.",
                        "Correct.",
                        "That's correct.",
                    ],
                    "thanks": [
                        "You're welcome!",
                        "Happy to help!",
                        "Anytime!",
                        "No problem!",
                    ],
                }
                self.personality_defaults = {}
        except Exception as e:
            logger.warning(
                "Failed to load conversational_defaults config; using empty defaults",
                exc_info=True,
                extra={"module_name": "conversational_defaults", "error_type": type(e).__name__},
            )
            self.defaults = {}
            self.personality_defaults = {}

    def execute(self, operation: str, params: Dict[str, Any]) -> Dict[str, Any]:
        """Execute a conversational defaults operation"""
        if operation == "get_default_response":
            scenario = params.get("scenario", "")
            context = params.get("context", {})
            personality = params.get("personality", "")
            if scenario is None:
                scenario = ""
            if context is None:
                context = {}
            if personality is None:
                personality = ""
            if not isinstance(scenario, str):
                raise InvalidParameterError("scenario", str(type(scenario).__name__), "scenario must be a string")
            if not isinstance(context, dict):
                raise InvalidParameterError("context", str(type(context).__name__), "context must be a dict")
            if not isinstance(personality, str):
                raise InvalidParameterError(
                    "personality", str(type(personality).__name__), "personality must be a string"
                )
            return self.get_default_response(scenario, context, personality)
        elif operation == "generate_fallback":
            context = params.get("context", "")
            personality = params.get("personality", "")
            previous_attempt = params.get("previous_attempt", "")
            if context is None:
                context = ""
            if personality is None:
                personality = ""
            if previous_attempt is None:
                previous_attempt = ""
            if not isinstance(context, str):
                raise InvalidParameterError("context", str(type(context).__name__), "context must be a string")
            if not isinstance(personality, str):
                raise InvalidParameterError(
                    "personality", str(type(personality).__name__), "personality must be a string"
                )
            if not isinstance(previous_attempt, str):
                raise InvalidParameterError(
                    "previous_attempt", str(type(previous_attempt).__name__), "previous_attempt must be a string"
                )
            return self.generate_fallback(context, personality, previous_attempt)
        elif operation == "adapt_default":
            default = params.get("default", "")
            target_context = params.get("target_context", {})
            personality = params.get("personality", "")
            if default is None:
                default = ""
            if target_context is None:
                target_context = {}
            if personality is None:
                personality = ""
            if not isinstance(default, str):
                raise InvalidParameterError("default", str(type(default).__name__), "default must be a string")
            if not isinstance(target_context, dict):
                raise InvalidParameterError(
                    "target_context", str(type(target_context).__name__), "target_context must be a dict"
                )
            if not isinstance(personality, str):
                raise InvalidParameterError(
                    "personality", str(type(personality).__name__), "personality must be a string"
                )
            return self.adapt_default(default, target_context, personality)
        elif operation == "get_scenario_default":
            scenario = params.get("scenario", "")
            if scenario is None:
                scenario = ""
            if not isinstance(scenario, str):
                raise InvalidParameterError("scenario", str(type(scenario).__name__), "scenario must be a string")
            return self.get_scenario_default(scenario)
        elif operation == "get_personality_default":
            personality = params.get("personality", "")
            scenario = params.get("scenario", "")
            if personality is None:
                personality = ""
            if scenario is None:
                scenario = ""
            if not isinstance(personality, str):
                raise InvalidParameterError(
                    "personality", str(type(personality).__name__), "personality must be a string"
                )
            if not isinstance(scenario, str):
                raise InvalidParameterError("scenario", str(type(scenario).__name__), "scenario must be a string")
            return self.get_personality_default(personality, scenario)
        else:
            raise InvalidParameterError(
                parameter="operation",
                value=str(operation),
                reason="Unknown operation for conversational_defaults",
            )

    def get_default_response(
        self, scenario: str, context: Dict[str, Any] = None, personality: str = ""
    ) -> Dict[str, Any]:
        """Get default response for a scenario"""
        if context is None:
            context = {}

        # Try personality-specific default first
        if personality:
            personality_result = self.get_personality_default(personality, scenario)
            if personality_result.get("response"):
                return {
                    "response": personality_result["response"],
                    "scenario": scenario,
                    "source": "personality",
                    "personality": personality,
                }

        # Try scenario-specific default
        if scenario in self.defaults:
            responses = self.defaults[scenario]
            selected = random.choice(responses) if responses else ""

            # Adapt based on context
            if context:
                adapted = self.adapt_default(selected, context, personality)
                selected = adapted.get("adapted_response", selected)

            return {
                "response": selected,
                "scenario": scenario,
                "source": "default",
                "variations_available": len(responses),
            }

        # Fallback to generic response
        fallback = self.generate_fallback(context, personality)
        return {
            "response": fallback.get(
                "response", "I'm here to help. What would you like to know?"
            ),
            "scenario": scenario,
            "source": "fallback",
        }

    def generate_fallback(
        self, context: str = "", personality: str = "", previous_attempt: str = ""
    ) -> Dict[str, Any]:
        """Generate fallback response when other methods fail"""
        # Analyze context to determine appropriate fallback
        context_lower = context.lower() if context else ""

        # Determine fallback type
        if "error" in context_lower or "failed" in context_lower:
            fallback_response = "I apologize, but I'm having trouble with that. Could you try rephrasing your question?"
        elif "confused" in context_lower or "don't understand" in context_lower:
            fallback_response = "I'm not entirely sure I understand. Could you help me by rephrasing that?"
        elif "greeting" in context_lower or any(
            word in context_lower for word in ["hi", "hello", "hey"]
        ):
            fallback_response = "Hello! How can I help you today?"
        elif previous_attempt:
            # If we've tried before, acknowledge and ask for clarification
            fallback_response = "I'm having difficulty with that. Could you provide more details or try a different approach?"
        else:
            # Generic helpful fallback
            fallback_responses = [
                "I'm here to help. What would you like to know?",
                "How can I assist you?",
                "What's on your mind?",
                "I'm listening. What can I do for you?",
            ]
            fallback_response = random.choice(fallback_responses)

        # Adapt to personality if specified
        if personality:
            adapted = self.adapt_default(fallback_response, {}, personality)
            fallback_response = adapted.get("adapted_response", fallback_response)

        return {
            "response": fallback_response,
            "type": "fallback",
            "context_aware": bool(context),
            "personality_adapted": bool(personality),
        }

    def adapt_default(
        self, default: str, target_context: Dict[str, Any], personality: str = ""
    ) -> Dict[str, Any]:
        """Adapt a default response to target context and personality"""
        adapted = default
        modifications = []

        # Adapt to formality
        formality = target_context.get("formality_level", "neutral")
        if formality == "formal":
            # Make more formal
            adapted = adapted.replace("I'm", "I am")
            adapted = adapted.replace("you're", "you are")
            adapted = adapted.replace("can't", "cannot")
            adapted = adapted.replace("don't", "do not")
            if not adapted.startswith(("I ", "Thank", "Please")):
                adapted = "I " + adapted.lower()
            modifications.append("formal")
        elif formality == "informal":
            # Make more casual
            adapted = adapted.replace("I am", "I'm")
            adapted = adapted.replace("you are", "you're")
            adapted = adapted.replace("cannot", "can't")
            adapted = adapted.replace("do not", "don't")
            modifications.append("informal")

        # Adapt to emotional context
        emotional_context = target_context.get("emotional_context", "")
        if emotional_context == "negative":
            # Add empathy
            if "I'm sorry" not in adapted and "I understand" not in adapted:
                adapted = "I understand. " + adapted
            modifications.append("empathetic")
        elif emotional_context == "positive":
            # Add enthusiasm
            if "great" not in adapted.lower() and "wonderful" not in adapted.lower():
                adapted = "Great! " + adapted
            modifications.append("enthusiastic")

        # Personality-specific adaptations (simplified)
        if personality:
            personality_lower = personality.lower()
            if "casual" in personality_lower or "gen z" in personality_lower:
                # Add casual markers
                adapted = adapted.replace(".", "!")
                modifications.append("casual_tone")
            elif (
                "professional" in personality_lower or "executive" in personality_lower
            ):
                # Keep formal
                if "formal" not in modifications:
                    modifications.append("professional")

        return {
            "original_response": default,
            "adapted_response": adapted,
            "modifications": modifications,
            "context_applied": bool(target_context),
            "personality_applied": bool(personality),
        }

    def get_scenario_default(self, scenario: str) -> Dict[str, Any]:
        """Get default response for a specific scenario"""
        if scenario in self.defaults:
            responses = self.defaults[scenario]
            return {
                "scenario": scenario,
                "responses": responses,
                "count": len(responses),
                "default": random.choice(responses) if responses else None,
            }
        else:
            return {
                "scenario": scenario,
                "responses": [],
                "count": 0,
                "default": None,
                "error": "Scenario not found",
            }

    def get_personality_default(
        self, personality: str, scenario: str = ""
    ) -> Dict[str, Any]:
        """Get personality-specific default"""
        personality_key = personality.lower().replace(" ", "_")

        if personality_key in self.personality_defaults:
            personality_defaults = self.personality_defaults[personality_key]

            if scenario and scenario in personality_defaults:
                responses = personality_defaults[scenario]
                return {
                    "personality": personality,
                    "scenario": scenario,
                    "response": random.choice(responses) if responses else None,
                    "variations": responses,
                    "found": True,
                }
            elif not scenario:
                # Return all scenarios for this personality
                return {
                    "personality": personality,
                    "scenarios": list(personality_defaults.keys()),
                    "found": True,
                }

        return {
            "personality": personality,
            "scenario": scenario,
            "response": None,
            "found": False,
        }

    def validate_params(self, operation: str, params: Dict[str, Any]) -> bool:
        """Validate parameters for operations"""
        if operation == "get_default_response":
            return "scenario" in params
        elif operation == "adapt_default":
            return "default" in params and "target_context" in params
        elif operation == "get_personality_default":
            return "personality" in params
        return True
