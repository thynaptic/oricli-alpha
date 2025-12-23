"""
Natural Transitions Module - Smooth topic transitions
Handles natural topic shifting, smooth conversation flow, handling interruptions, and topic bridging
"""

from typing import Dict, Any, List, Optional
import json
import random
from pathlib import Path
import logging

from mavaia_core.brain.base_module import BaseBrainModule, ModuleMetadata
from mavaia_core.exceptions import InvalidParameterError

logger = logging.getLogger(__name__)


class NaturalTransitionsModule(BaseBrainModule):
    """Natural topic transitions and conversation flow"""

    def __init__(self):
        super().__init__()
        self.config = None
        self.transition_phrases = {}
        self.topic_shift_patterns = {}
        self.bridging_patterns = {}
        self._load_config()

    @property
    def metadata(self) -> ModuleMetadata:
        return ModuleMetadata(
            name="natural_transitions",
            version="1.0.0",
            description="Natural transitions: topic shifting, smooth flow, handling interruptions, topic bridging",
            operations=[
                "create_transition",
                "detect_topic_shift",
                "bridge_topics",
                "handle_interruption",
                "smooth_flow",
            ],
            dependencies=[],
            model_required=False,
        )

    def initialize(self) -> bool:
        """Initialize the module"""
        return True

    def _load_config(self):
        """Load natural transitions configuration"""
        config_path = Path(__file__).parent / "natural_transitions_config.json"
        try:
            if config_path.exists():
                with open(config_path, "r", encoding="utf-8") as f:
                    self.config = json.load(f)
                    self.transition_phrases = self.config.get("transition_phrases", {})
                    self.topic_shift_patterns = self.config.get(
                        "topic_shift_patterns", {}
                    )
                    self.bridging_patterns = self.config.get("bridging_patterns", {})
            else:
                # Default config
                self.transition_phrases = {
                    "smooth": [
                        "Speaking of which,",
                        "That reminds me,",
                        "On that note,",
                    ],
                    "explicit": [
                        "By the way,",
                        "Changing topics a bit,",
                        "On another note,",
                    ],
                    "natural": [
                        "Oh,",
                        "Actually,",
                        "You know what,",
                        "Wait, I just thought of something,",
                    ],
                }
                self.bridging_patterns = {
                    "connection": [
                        "That connects to",
                        "That relates to",
                        "That's similar to",
                    ],
                    "contrast": [
                        "On the other hand,",
                        "In contrast,",
                        "But thinking about",
                    ],
                    "continuation": ["And also,", "Plus,", "Additionally,"],
                }
        except Exception as e:
            logger.warning(
                "Failed to load natural_transitions config; using empty defaults",
                exc_info=True,
                extra={"module_name": "natural_transitions", "error_type": type(e).__name__},
            )
            self.transition_phrases = {}
            self.topic_shift_patterns = {}
            self.bridging_patterns = {}

    def execute(self, operation: str, params: Dict[str, Any]) -> Dict[str, Any]:
        """Execute a natural transitions operation"""
        if operation == "create_transition":
            from_topic = params.get("from_topic", "")
            to_topic = params.get("to_topic", "")
            transition_type = params.get("transition_type", "smooth")
            if from_topic is None:
                from_topic = ""
            if to_topic is None:
                to_topic = ""
            if transition_type is None:
                transition_type = "smooth"
            if not isinstance(from_topic, str):
                raise InvalidParameterError("from_topic", str(type(from_topic).__name__), "from_topic must be a string")
            if not isinstance(to_topic, str):
                raise InvalidParameterError("to_topic", str(type(to_topic).__name__), "to_topic must be a string")
            if not isinstance(transition_type, str):
                raise InvalidParameterError(
                    "transition_type", str(type(transition_type).__name__), "transition_type must be a string"
                )
            return self.create_transition(from_topic, to_topic, transition_type)
        elif operation == "detect_topic_shift":
            current_text = params.get("current_text", "")
            previous_texts = params.get("previous_texts", [])
            if current_text is None:
                current_text = ""
            if previous_texts is None:
                previous_texts = []
            if not isinstance(current_text, str):
                raise InvalidParameterError(
                    "current_text", str(type(current_text).__name__), "current_text must be a string"
                )
            if not isinstance(previous_texts, list):
                raise InvalidParameterError(
                    "previous_texts", str(type(previous_texts).__name__), "previous_texts must be a list"
                )
            return self.detect_topic_shift(current_text, previous_texts)
        elif operation == "bridge_topics":
            topic1 = params.get("topic1", "")
            topic2 = params.get("topic2", "")
            if topic1 is None:
                topic1 = ""
            if topic2 is None:
                topic2 = ""
            if not isinstance(topic1, str):
                raise InvalidParameterError("topic1", str(type(topic1).__name__), "topic1 must be a string")
            if not isinstance(topic2, str):
                raise InvalidParameterError("topic2", str(type(topic2).__name__), "topic2 must be a string")
            return self.bridge_topics(topic1, topic2)
        elif operation == "handle_interruption":
            previous_text = params.get("previous_text", "")
            interruption_text = params.get("interruption_text", "")
            if previous_text is None:
                previous_text = ""
            if interruption_text is None:
                interruption_text = ""
            if not isinstance(previous_text, str):
                raise InvalidParameterError(
                    "previous_text", str(type(previous_text).__name__), "previous_text must be a string"
                )
            if not isinstance(interruption_text, str):
                raise InvalidParameterError(
                    "interruption_text", str(type(interruption_text).__name__), "interruption_text must be a string"
                )
            return self.handle_interruption(previous_text, interruption_text)
        elif operation == "smooth_flow":
            text = params.get("text", "")
            previous_text = params.get("previous_text", "")
            if text is None:
                text = ""
            if previous_text is None:
                previous_text = ""
            if not isinstance(text, str):
                raise InvalidParameterError("text", str(type(text).__name__), "text must be a string")
            if not isinstance(previous_text, str):
                raise InvalidParameterError(
                    "previous_text", str(type(previous_text).__name__), "previous_text must be a string"
                )
            return self.smooth_flow(text, previous_text)
        else:
            raise InvalidParameterError(
                parameter="operation",
                value=operation,
                reason="Unknown operation for natural_transitions",
            )

    def create_transition(
        self, from_topic: str, to_topic: str, transition_type: str = "smooth"
    ) -> Dict[str, Any]:
        """Create natural transition between topics"""
        phrases = self.transition_phrases.get(
            transition_type, self.transition_phrases.get("smooth", [])
        )

        if not phrases:
            return {"transition_phrase": "", "transition_text": to_topic}

        phrase = random.choice(phrases)

        transition_text = phrase + " " + to_topic.lower()
        transition_text = transition_text[0].upper() + transition_text[1:]

        return {
            "transition_phrase": phrase,
            "transition_text": transition_text,
            "transition_type": transition_type,
        }

    def detect_topic_shift(
        self, current_text: str, previous_texts: List[str] = None
    ) -> Dict[str, Any]:
        """Detect if topic has shifted"""
        if previous_texts is None:
            previous_texts = []

        if not previous_texts:
            return {"topic_shifted": False, "shift_strength": 0.0}

        # Simple keyword overlap check
        current_words = set(current_text.lower().split())
        previous_words = set()
        for prev_text in previous_texts[-2:]:  # Last 2 turns
            previous_words.update(prev_text.lower().split())

        # Remove common words
        common_words = {
            "the",
            "a",
            "an",
            "and",
            "or",
            "but",
            "is",
            "are",
            "was",
            "were",
            "in",
            "on",
            "at",
            "to",
            "for",
        }
        current_words -= common_words
        previous_words -= common_words

        overlap = len(current_words & previous_words)
        total_unique = len(current_words | previous_words)

        overlap_ratio = overlap / total_unique if total_unique > 0 else 0.0

        topic_shifted = overlap_ratio < 0.3  # Less than 30% overlap suggests shift
        shift_strength = 1.0 - overlap_ratio

        return {
            "topic_shifted": topic_shifted,
            "shift_strength": shift_strength,
            "overlap_ratio": overlap_ratio,
            "overlap_words": list(current_words & previous_words),
        }

    def bridge_topics(self, topic1: str, topic2: str) -> Dict[str, Any]:
        """Bridge two topics naturally"""
        if not topic1 or not topic2:
            return {"bridged_text": topic2 if topic2 else topic1, "bridge_added": False}

        # Choose bridging pattern
        patterns = self.bridging_patterns.get("connection", [])
        if not patterns:
            patterns = ["That relates to", "Speaking of"]

        bridge = random.choice(patterns)
        bridged_text = bridge + " " + topic2.lower() + ", " + topic1.lower()
        bridged_text = bridged_text[0].upper() + bridged_text[1:]

        return {
            "bridged_text": bridged_text,
            "bridge_added": True,
            "bridge_phrase": bridge,
        }

    def handle_interruption(
        self, previous_text: str, interruption_text: str
    ) -> Dict[str, Any]:
        """Handle topic interruption naturally"""
        if not interruption_text:
            return {"handled_text": previous_text, "interruption_handled": False}

        # Check if interruption is significant
        if not previous_text or len(interruption_text.split()) < 3:
            return {
                "handled_text": interruption_text,
                "interruption_handled": False,
                "reason": "no_significant_interruption",
            }

        # Create natural transition to acknowledge interruption
        interruption_patterns = [
            "Oh, that's interesting!",
            "Wait, before we continue -",
            "Actually, that reminds me -",
            "You know what, let me address that first -",
        ]

        pattern = random.choice(interruption_patterns)
        handled_text = pattern + " " + interruption_text.lower()
        handled_text = handled_text[0].upper() + handled_text[1:]

        return {
            "handled_text": handled_text,
            "interruption_handled": True,
            "pattern_used": pattern,
        }

    def smooth_flow(self, text: str, previous_text: str = "") -> Dict[str, Any]:
        """Smooth flow from previous text to current text"""
        if not text:
            return {"smoothed_text": text, "transition_added": False}

        if not previous_text:
            return {"smoothed_text": text, "transition_added": False}

        # Check if transition needed
        smoothed_text = text

        # Detect abrupt change
        prev_words = set(previous_text.lower().split())
        curr_words = set(text.lower().split())
        common_words = {"the", "a", "an", "and", "or", "but", "is", "are"}
        prev_words -= common_words
        curr_words -= common_words

        overlap = len(prev_words & curr_words)
        overlap_ratio = (
            overlap / max(len(prev_words), len(curr_words))
            if max(len(prev_words), len(curr_words)) > 0
            else 0
        )

        # If low overlap, add transition
        if overlap_ratio < 0.2 and random.random() < 0.4:  # 40% chance
            smooth_transitions = self.transition_phrases.get(
                "smooth", ["Speaking of which,", "That reminds me,"]
            )
            if smooth_transitions:
                transition = random.choice(smooth_transitions)
                smoothed_text = transition + " " + text.lower()
                smoothed_text = smoothed_text[0].upper() + smoothed_text[1:]
                return {
                    "smoothed_text": smoothed_text,
                    "transition_added": True,
                    "transition_phrase": transition,
                }

        return {"smoothed_text": smoothed_text, "transition_added": False}

    def validate_params(self, operation: str, params: Dict[str, Any]) -> bool:
        """Validate parameters for operations"""
        if operation == "create_transition":
            return "to_topic" in params
        elif operation == "detect_topic_shift":
            return "current_text" in params
        elif operation == "bridge_topics":
            return "topic1" in params and "topic2" in params
        elif operation == "handle_interruption":
            return "interruption_text" in params
        elif operation == "smooth_flow":
            return "text" in params
        return True
