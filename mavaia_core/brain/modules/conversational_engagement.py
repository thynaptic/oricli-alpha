"""
Conversational Engagement Module - Proactive engagement and curiosity
Handles follow-up questions, natural curiosity, proactive topic exploration, and back-channeling
"""

from typing import Dict, Any, List, Optional
import json
import random
import logging
from pathlib import Path

from mavaia_core.brain.base_module import BaseBrainModule, ModuleMetadata
from mavaia_core.exceptions import InvalidParameterError

logger = logging.getLogger(__name__)


class ConversationalEngagementModule(BaseBrainModule):
    """Proactive conversational engagement and curiosity"""

    def __init__(self):
        super().__init__()
        self.config = None
        self.follow_up_patterns = {}
        self.curiosity_expressions = {}
        self.back_channeling = {}
        self._load_config()

    @property
    def metadata(self) -> ModuleMetadata:
        return ModuleMetadata(
            name="conversational_engagement",
            version="1.0.0",
            description="Conversational engagement: follow-up questions, curiosity, proactive exploration, back-channeling",
            operations=[
                "generate_follow_up",
                "express_curiosity",
                "add_back_channeling",
                "proactive_exploration",
                "should_engage",
            ],
            dependencies=[],
            model_required=False,
        )

    def initialize(self) -> bool:
        """Initialize the module"""
        return True

    def _load_config(self):
        """Load conversational engagement configuration"""
        config_path = Path(__file__).parent / "conversational_engagement_config.json"
        try:
            if config_path.exists():
                with open(config_path, "r", encoding="utf-8") as f:
                    self.config = json.load(f)
                    self.follow_up_patterns = self.config.get("follow_up_patterns", {})
                    self.curiosity_expressions = self.config.get(
                        "curiosity_expressions", {}
                    )
                    self.back_channeling = self.config.get("back_channeling", {})
            else:
                # Default config
                self.follow_up_patterns = {
                    "clarification": [
                        "What do you mean by that?",
                        "Could you elaborate?",
                        "Can you tell me more?",
                    ],
                    "deeper": [
                        "What made you think of that?",
                        "How did that come about?",
                        "What's the story behind that?",
                    ],
                    "related": [
                        "Have you considered...?",
                        "What about...?",
                        "Does that relate to...?",
                    ],
                }
                self.curiosity_expressions = {
                    "mild": ["That's interesting.", "I see.", "Hmm."],
                    "moderate": [
                        "That's really interesting!",
                        "I'd love to hear more.",
                        "Tell me more about that.",
                    ],
                    "high": [
                        "Wow, that's fascinating!",
                        "I'm really curious about that.",
                        "That sounds intriguing!",
                    ],
                }
                self.back_channeling = {
                    "acknowledgment": [
                        "I see",
                        "Right",
                        "Okay",
                        "Got it",
                        "Makes sense",
                    ],
                    "encouragement": [
                        "That's interesting",
                        "I hear you",
                        "Go on",
                        "Tell me more",
                    ],
                    "validation": [
                        "That makes sense",
                        "I understand",
                        "That's reasonable",
                        "I can see that",
                    ],
                }
        except Exception as e:
            logger.warning(
                "Failed to load conversational_engagement config; using empty defaults",
                exc_info=True,
                extra={"module_name": "conversational_engagement", "error_type": type(e).__name__},
            )
            self.follow_up_patterns = {}
            self.curiosity_expressions = {}
            self.back_channeling = {}

    def execute(self, operation: str, params: Dict[str, Any]) -> Dict[str, Any]:
        """Execute a conversational engagement operation"""
        match operation:
            case "generate_follow_up":
                context = params.get("context", "")
                topic = params.get("topic", "")
                conversation_history = params.get("conversation_history", [])
                if context is None:
                    context = ""
                if topic is None:
                    topic = ""
                if conversation_history is None:
                    conversation_history = []
                if not isinstance(context, str):
                    raise InvalidParameterError("context", str(type(context).__name__), "context must be a string")
                if not isinstance(topic, str):
                    raise InvalidParameterError("topic", str(type(topic).__name__), "topic must be a string")
                if not isinstance(conversation_history, list):
                    raise InvalidParameterError(
                        "conversation_history",
                        str(type(conversation_history).__name__),
                        "conversation_history must be a list",
                    )
                return self.generate_follow_up(context, topic, conversation_history)
            case "express_curiosity":
                topic = params.get("topic", "")
                intensity = params.get("intensity", "moderate")
                if topic is None:
                    topic = ""
                if intensity is None:
                    intensity = "moderate"
                if not isinstance(topic, str):
                    raise InvalidParameterError("topic", str(type(topic).__name__), "topic must be a string")
                if not isinstance(intensity, str):
                    raise InvalidParameterError(
                        "intensity", str(type(intensity).__name__), "intensity must be a string"
                    )
                return self.express_curiosity(topic, intensity)
            case "add_back_channeling":
                response = params.get("response", "")
                user_input = params.get("user_input", "")
                if response is None:
                    response = ""
                if user_input is None:
                    user_input = ""
                if not isinstance(response, str):
                    raise InvalidParameterError("response", str(type(response).__name__), "response must be a string")
                if not isinstance(user_input, str):
                    raise InvalidParameterError(
                        "user_input", str(type(user_input).__name__), "user_input must be a string"
                    )
                return self.add_back_channeling(response, user_input)
            case "proactive_exploration":
                topic = params.get("topic", "")
                current_response = params.get("current_response", "")
                if topic is None:
                    topic = ""
                if current_response is None:
                    current_response = ""
                if not isinstance(topic, str):
                    raise InvalidParameterError("topic", str(type(topic).__name__), "topic must be a string")
                if not isinstance(current_response, str):
                    raise InvalidParameterError(
                        "current_response",
                        str(type(current_response).__name__),
                        "current_response must be a string",
                    )
                return self.proactive_exploration(topic, current_response)
            case "should_engage":
                context = params.get("context", "")
                conversation_length = params.get("conversation_length", 0)
                if context is None:
                    context = ""
                if not isinstance(context, str):
                    raise InvalidParameterError("context", str(type(context).__name__), "context must be a string")
                try:
                    conversation_length_int = int(conversation_length)
                except (TypeError, ValueError):
                    raise InvalidParameterError(
                        "conversation_length", str(conversation_length), "conversation_length must be an integer"
                    )
                if conversation_length_int < 0:
                    raise InvalidParameterError(
                        "conversation_length", str(conversation_length_int), "conversation_length must be >= 0"
                    )
                return self.should_engage(context, conversation_length_int)
            case _:
                raise InvalidParameterError(
                    parameter="operation",
                    value=operation,
                    reason="Unknown operation for conversational_engagement",
                )

    def generate_follow_up(
        self, context: str, topic: str = "", conversation_history: List[str] = None
    ) -> Dict[str, Any]:
        """Generate natural follow-up questions"""
        if conversation_history is None:
            conversation_history = []

        follow_ups = []

        # Determine follow-up type based on context
        context_lower = context.lower()

        # Check for incomplete information
        if any(
            word in context_lower
            for word in ["maybe", "might", "could be", "not sure", "think"]
        ):
            # User seems uncertain - ask for clarification
            follow_ups.append(
                {
                    "question": random.choice(
                        self.follow_up_patterns.get("clarification", [])
                    ),
                    "type": "clarification",
                    "confidence": 0.8,
                }
            )

        # Check for interesting topic that could be explored
        if topic or any(len(s.split()) > 10 for s in conversation_history[-2:]):
            # Generate deeper exploration question
            follow_ups.append(
                {
                    "question": random.choice(
                        self.follow_up_patterns.get("deeper", [])
                    ),
                    "type": "deeper_exploration",
                    "confidence": 0.7,
                }
            )

        # Generate related question
        if topic:
            related_questions = [
                f"What about {topic}?",
                f"Does that relate to {topic}?",
                f"Have you thought about {topic}?",
            ]
            follow_ups.append(
                {
                    "question": random.choice(related_questions),
                    "type": "related_topic",
                    "confidence": 0.6,
                }
            )

        # Select best follow-up (highest confidence)
        selected = None
        if follow_ups:
            selected = max(follow_ups, key=lambda x: x["confidence"])

        return {
            "follow_up_question": selected["question"] if selected else None,
            "type": selected["type"] if selected else None,
            "all_options": follow_ups,
            "should_ask": selected is not None,
        }

    def express_curiosity(
        self, topic: str, intensity: str = "moderate"
    ) -> Dict[str, Any]:
        """Express curiosity about a topic"""
        expressions = self.curiosity_expressions.get(
            intensity, self.curiosity_expressions.get("moderate", [])
        )

        if not expressions:
            return {"expression": "", "intensity": intensity}

        expression = random.choice(expressions)

        # Add topic-specific curiosity if topic provided
        if topic:
            curiosity_patterns = {
                "mild": f"That's interesting about {topic}.",
                "moderate": f"I'd love to hear more about {topic}.",
                "high": f"I'm really curious about {topic}!",
            }
            if intensity in curiosity_patterns:
                expression = curiosity_patterns[intensity]

        return {"expression": expression, "intensity": intensity, "topic": topic}

    def add_back_channeling(
        self, response: str, user_input: str = ""
    ) -> Dict[str, Any]:
        """Add back-channeling to response"""
        if not response:
            return {"response_with_back_channeling": response, "added": False}

        # Determine if back-channeling is appropriate
        user_lower = user_input.lower() if user_input else ""

        # Check for emotional content that needs acknowledgment
        emotional_words = ["sad", "happy", "excited", "worried", "frustrated", "angry"]
        has_emotion = any(word in user_lower for word in emotional_words)

        # Check for sharing personal information
        personal_words = ["i", "my", "me", "myself", "feel", "think", "believe"]
        is_personal = (
            sum(1 for word in personal_words if word in user_lower.split()) > 2
        )

        back_channel = None

        if has_emotion:
            # Add empathetic acknowledgment
            back_channel = random.choice(
                self.back_channeling.get("validation", ["I see", "I understand"])
            )
        elif is_personal:
            # Add encouraging acknowledgment
            back_channel = random.choice(
                self.back_channeling.get(
                    "encouragement", ["That's interesting", "I hear you"]
                )
            )
        elif len(user_input.split()) > 15:
            # Long input - add acknowledgment
            back_channel = random.choice(
                self.back_channeling.get("acknowledgment", ["I see", "Right"])
            )

        if back_channel and random.random() < 0.6:  # 60% chance
            # Add to beginning of response
            if not response.lower().startswith(back_channel.lower()):
                response_with_back_channeling = back_channel + ", " + response.lower()
                response_with_back_channeling = (
                    response_with_back_channeling[0].upper()
                    + response_with_back_channeling[1:]
                )
                return {
                    "response_with_back_channeling": response_with_back_channeling,
                    "added": True,
                    "back_channel_type": (
                        "empathetic"
                        if has_emotion
                        else "encouraging" if is_personal else "acknowledgment"
                    ),
                }

        return {"response_with_back_channeling": response, "added": False}

    def proactive_exploration(
        self, topic: str, current_response: str = ""
    ) -> Dict[str, Any]:
        """Proactively explore a topic"""
        if not topic:
            return {"exploration_added": False, "exploration_text": ""}

        # Determine if proactive exploration is appropriate
        # Don't add if response is already long
        if len(current_response.split()) > 50:
            return {"exploration_added": False, "exploration_text": ""}

        # Add exploration based on probability
        if random.random() < 0.3:  # 30% chance
            exploration_patterns = [
                f"Have you thought about {topic}?",
                f"What's your take on {topic}?",
                f"I'm curious - what about {topic}?",
                f"On a related note, {topic} is interesting too.",
            ]

            exploration_text = random.choice(exploration_patterns)

            return {
                "exploration_added": True,
                "exploration_text": exploration_text,
                "topic": topic,
            }

        return {"exploration_added": False, "exploration_text": ""}

    def should_engage(
        self, context: str, conversation_length: int = 0
    ) -> Dict[str, Any]:
        """Determine if proactive engagement is appropriate"""
        # Engagement is more appropriate in longer conversations
        engagement_score = min(1.0, conversation_length / 5.0)

        # Boost engagement for questions
        context_lower = context.lower()
        if "?" in context:
            engagement_score += 0.2

        # Boost for emotional content
        emotional_words = [
            "feel",
            "feeling",
            "emotion",
            "happy",
            "sad",
            "excited",
            "worried",
        ]
        if any(word in context_lower for word in emotional_words):
            engagement_score += 0.3

        # Reduce for very short interactions
        if conversation_length < 2:
            engagement_score *= 0.5

        should_engage = engagement_score > 0.5

        engagement_type = None
        if should_engage:
            if "?" in context:
                engagement_type = "clarification"
            elif any(word in context_lower for word in emotional_words):
                engagement_type = "empathy"
            else:
                engagement_type = "exploration"

        return {
            "should_engage": should_engage,
            "engagement_score": engagement_score,
            "engagement_type": engagement_type,
            "recommended_action": engagement_type,
        }

    def validate_params(self, operation: str, params: Dict[str, Any]) -> bool:
        """Validate parameters for operations"""
        if operation == "express_curiosity":
            return True  # All params optional
        elif operation == "add_back_channeling":
            return "response" in params
        elif operation == "proactive_exploration":
            return "topic" in params
        return True
