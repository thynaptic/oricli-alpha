"""
Emotional Ontology Module - Complex emotion taxonomy with transitions and relationships
Handles emotion detection, emotion-appropriate responses, and emotion state transitions
"""

from typing import Dict, Any, List, Optional, Tuple
import json
import re
from pathlib import Path
import logging

from mavaia_core.brain.base_module import BaseBrainModule, ModuleMetadata
from mavaia_core.exceptions import InvalidParameterError

logger = logging.getLogger(__name__)


class EmotionalOntologyModule(BaseBrainModule):
    """Complex emotional ontology with taxonomy and transitions"""

    def __init__(self):
        super().__init__()
        self.config = None
        self.emotion_taxonomy = {}
        self.emotion_transitions = {}
        self.emotion_detection_patterns = {}
        self._load_config()
        self._initialize_taxonomy()

    @property
    def metadata(self) -> ModuleMetadata:
        return ModuleMetadata(
            name="emotional_ontology",
            version="1.0.0",
            description="Complex emotional ontology: taxonomy, transitions, emotion detection",
            operations=[
                "detect_emotion",
                "transition_emotion",
                "select_emotion_response",
                "get_emotion_graph",
                "get_emotion_intensity",
                "get_emotion_valence_arousal",
            ],
            dependencies=[],
            model_required=False,
        )

    def initialize(self) -> bool:
        """Initialize the module"""
        return True

    def _load_config(self):
        """Load emotional ontology configuration"""
        config_path = Path(__file__).parent / "emotional_ontology.json"
        try:
            if config_path.exists():
                with open(config_path, "r", encoding="utf-8") as f:
                    self.config = json.load(f)
            else:
                # Will use defaults from _initialize_taxonomy
                self.config = {}
        except Exception as e:
            logger.warning(
                "Failed to load emotional_ontology config; using empty defaults",
                exc_info=True,
                extra={"module_name": "emotional_ontology", "error_type": type(e).__name__},
            )
            self.config = {}

    def _initialize_taxonomy(self):
        """Initialize emotion taxonomy with comprehensive emotion structure"""
        # Load from config if available, otherwise use defaults
        if self.config and "emotions" in self.config:
            self.emotion_taxonomy = self.config["emotions"]
        else:
            # Default comprehensive emotion taxonomy
            self.emotion_taxonomy = {
                "primary": {
                    "joy": {
                        "valence": 0.9,
                        "arousal": 0.7,
                        "intensity_range": [0.3, 1.0],
                        "sub_emotions": [
                            "happiness",
                            "elation",
                            "cheerfulness",
                            "contentment",
                            "satisfaction",
                            "pleasure",
                            "delight",
                            "excitement",
                            "enthusiasm",
                        ],
                        "markers": [
                            "happy",
                            "joy",
                            "glad",
                            "pleased",
                            "excited",
                            "thrilled",
                            "delighted",
                            "cheerful",
                            "great",
                            "wonderful",
                        ],
                    },
                    "sadness": {
                        "valence": -0.8,
                        "arousal": -0.3,
                        "intensity_range": [0.3, 1.0],
                        "sub_emotions": [
                            "sorrow",
                            "grief",
                            "melancholy",
                            "despair",
                            "loneliness",
                            "disappointment",
                            "dejection",
                            "unhappiness",
                        ],
                        "markers": [
                            "sad",
                            "unhappy",
                            "depressed",
                            "down",
                            "blue",
                            "melancholy",
                            "gloomy",
                            "disappointed",
                            "hurt",
                        ],
                    },
                    "anger": {
                        "valence": -0.7,
                        "arousal": 0.9,
                        "intensity_range": [0.4, 1.0],
                        "sub_emotions": [
                            "rage",
                            "fury",
                            "irritation",
                            "annoyance",
                            "resentment",
                            "indignation",
                            "frustration",
                            "hostility",
                        ],
                        "markers": [
                            "angry",
                            "mad",
                            "furious",
                            "irritated",
                            "annoyed",
                            "frustrated",
                            "upset",
                            "pissed",
                            "raging",
                        ],
                    },
                    "fear": {
                        "valence": -0.7,
                        "arousal": 0.8,
                        "intensity_range": [0.3, 1.0],
                        "sub_emotions": [
                            "terror",
                            "anxiety",
                            "worry",
                            "nervousness",
                            "apprehension",
                            "dread",
                            "panic",
                            "fright",
                        ],
                        "markers": [
                            "afraid",
                            "scared",
                            "frightened",
                            "worried",
                            "anxious",
                            "nervous",
                            "terrified",
                            "panicked",
                        ],
                    },
                    "surprise": {
                        "valence": 0.3,
                        "arousal": 0.9,
                        "intensity_range": [0.4, 1.0],
                        "sub_emotions": [
                            "amazement",
                            "astonishment",
                            "shock",
                            "bewilderment",
                            "wonder",
                            "awe",
                        ],
                        "markers": [
                            "surprised",
                            "shocked",
                            "amazed",
                            "astonished",
                            "wow",
                            "whoa",
                            "incredible",
                            "unbelievable",
                        ],
                    },
                    "disgust": {
                        "valence": -0.8,
                        "arousal": 0.2,
                        "intensity_range": [0.3, 1.0],
                        "sub_emotions": [
                            "revulsion",
                            "contempt",
                            "loathing",
                            "aversion",
                            "repugnance",
                        ],
                        "markers": [
                            "disgusted",
                            "grossed out",
                            "revolted",
                            "sickened",
                            "appalled",
                        ],
                    },
                },
                "secondary": {
                    "love": {
                        "valence": 0.95,
                        "arousal": 0.6,
                        "intensity_range": [0.4, 1.0],
                        "sub_emotions": [
                            "affection",
                            "adoration",
                            "fondness",
                            "devotion",
                            "passion",
                            "romance",
                        ],
                        "markers": [
                            "love",
                            "adore",
                            "cherish",
                            "care",
                            "fond",
                            "devoted",
                        ],
                    },
                    "guilt": {
                        "valence": -0.6,
                        "arousal": 0.4,
                        "intensity_range": [0.3, 1.0],
                        "sub_emotions": ["remorse", "regret", "shame", "self-reproach"],
                        "markers": [
                            "guilty",
                            "ashamed",
                            "regretful",
                            "sorry",
                            "remorseful",
                        ],
                    },
                    "shame": {
                        "valence": -0.8,
                        "arousal": 0.3,
                        "intensity_range": [0.3, 1.0],
                        "sub_emotions": [
                            "embarrassment",
                            "humiliation",
                            "self-consciousness",
                        ],
                        "markers": [
                            "ashamed",
                            "embarrassed",
                            "humiliated",
                            "self-conscious",
                        ],
                    },
                    "pride": {
                        "valence": 0.8,
                        "arousal": 0.5,
                        "intensity_range": [0.3, 1.0],
                        "sub_emotions": [
                            "triumph",
                            "accomplishment",
                            "self-respect",
                            "dignity",
                        ],
                        "markers": ["proud", "accomplished", "triumphant", "satisfied"],
                    },
                    "envy": {
                        "valence": -0.5,
                        "arousal": 0.5,
                        "intensity_range": [0.3, 0.9],
                        "sub_emotions": ["jealousy", "resentment", "covetousness"],
                        "markers": ["envious", "jealous", "resentful", "covetous"],
                    },
                    "hope": {
                        "valence": 0.7,
                        "arousal": 0.5,
                        "intensity_range": [0.3, 1.0],
                        "sub_emotions": ["optimism", "expectation", "anticipation"],
                        "markers": [
                            "hopeful",
                            "optimistic",
                            "expectant",
                            "anticipating",
                        ],
                    },
                    "relief": {
                        "valence": 0.7,
                        "arousal": -0.3,
                        "intensity_range": [0.3, 0.9],
                        "sub_emotions": ["reassurance", "comfort", "calm"],
                        "markers": ["relieved", "reassured", "comforted", "calm"],
                    },
                    "contempt": {
                        "valence": -0.7,
                        "arousal": 0.1,
                        "intensity_range": [0.3, 0.9],
                        "sub_emotions": ["scorn", "disdain", "derision"],
                        "markers": [
                            "contemptuous",
                            "scornful",
                            "disdainful",
                            "derisive",
                        ],
                    },
                },
            }

        # Initialize emotion transitions (how emotions can change)
        self._initialize_transitions()

        # Initialize detection patterns
        self._initialize_detection_patterns()

    def _initialize_transitions(self):
        """Initialize emotion transition probabilities"""
        self.emotion_transitions = {
            "joy": {
                "likely_transitions": ["excitement", "contentment", "pride"],
                "unlikely_transitions": ["sadness", "anger"],
                "neutral_transitions": ["surprise", "hope"],
            },
            "sadness": {
                "likely_transitions": ["melancholy", "loneliness", "disappointment"],
                "unlikely_transitions": ["joy", "excitement"],
                "neutral_transitions": ["hope", "relief", "acceptance"],
            },
            "anger": {
                "likely_transitions": ["frustration", "irritation", "resentment"],
                "unlikely_transitions": ["joy", "contentment"],
                "neutral_transitions": ["relief", "understanding", "calm"],
            },
            "fear": {
                "likely_transitions": ["anxiety", "worry", "nervousness"],
                "unlikely_transitions": ["joy", "confidence"],
                "neutral_transitions": ["relief", "calm", "understanding"],
            },
        }

    def _initialize_detection_patterns(self):
        """Initialize patterns for emotion detection"""
        # Patterns are loaded from emotion taxonomy markers
        self.emotion_detection_patterns = {}
        for category, emotions in self.emotion_taxonomy.items():
            for emotion_name, emotion_data in emotions.items():
                self.emotion_detection_patterns[emotion_name] = emotion_data.get(
                    "markers", []
                )

    def execute(self, operation: str, params: Dict[str, Any]) -> Dict[str, Any]:
        """Execute an emotional ontology operation"""
        if operation == "detect_emotion":
            text = params.get("text", "")
            context = params.get("context", "")
            if text is None:
                text = ""
            if context is None:
                context = ""
            if not isinstance(text, str):
                raise InvalidParameterError("text", str(type(text).__name__), "text must be a string")
            if not isinstance(context, str):
                raise InvalidParameterError("context", str(type(context).__name__), "context must be a string")
            return self.detect_emotion(text, context)
        elif operation == "transition_emotion":
            current_emotion = params.get("current_emotion", "")
            context = params.get("context", "")
            trigger = params.get("trigger", "")
            if current_emotion is None:
                current_emotion = ""
            if context is None:
                context = ""
            if trigger is None:
                trigger = ""
            if not isinstance(current_emotion, str):
                raise InvalidParameterError(
                    "current_emotion", str(type(current_emotion).__name__), "current_emotion must be a string"
                )
            if not isinstance(context, str):
                raise InvalidParameterError("context", str(type(context).__name__), "context must be a string")
            if not isinstance(trigger, str):
                raise InvalidParameterError("trigger", str(type(trigger).__name__), "trigger must be a string")
            return self.transition_emotion(current_emotion, context, trigger)
        elif operation == "select_emotion_response":
            detected_emotion = params.get("detected_emotion", "")
            emotion_intensity = params.get("intensity", 0.5)
            context = params.get("context", "")
            if detected_emotion is None:
                detected_emotion = ""
            if context is None:
                context = ""
            if not isinstance(detected_emotion, str):
                raise InvalidParameterError(
                    "detected_emotion", str(type(detected_emotion).__name__), "detected_emotion must be a string"
                )
            if not isinstance(context, str):
                raise InvalidParameterError("context", str(type(context).__name__), "context must be a string")
            try:
                intensity_float = float(emotion_intensity)
            except (TypeError, ValueError):
                raise InvalidParameterError("intensity", str(emotion_intensity), "intensity must be a number")
            return self.select_emotion_response(
                detected_emotion, intensity_float, context
            )
        elif operation == "get_emotion_graph":
            return self.get_emotion_graph()
        elif operation == "get_emotion_intensity":
            text = params.get("text", "")
            emotion = params.get("emotion", "")
            if text is None:
                text = ""
            if emotion is None:
                emotion = ""
            if not isinstance(text, str):
                raise InvalidParameterError("text", str(type(text).__name__), "text must be a string")
            if not isinstance(emotion, str):
                raise InvalidParameterError("emotion", str(type(emotion).__name__), "emotion must be a string")
            return self.get_emotion_intensity(text, emotion)
        elif operation == "get_emotion_valence_arousal":
            emotion = params.get("emotion", "")
            if emotion is None:
                emotion = ""
            if not isinstance(emotion, str):
                raise InvalidParameterError("emotion", str(type(emotion).__name__), "emotion must be a string")
            return self.get_emotion_valence_arousal(emotion)
        else:
            raise InvalidParameterError(
                parameter="operation",
                value=operation,
                reason="Unknown operation for emotional_ontology",
            )

    def detect_emotion(self, text: str, context: str = "") -> Dict[str, Any]:
        """Detect emotion(s) from text"""
        if not text:
            return {
                "primary_emotion": None,
                "emotions": [],
                "confidence": 0.0,
                "intensity": 0.0,
            }

        text_lower = text.lower()
        emotion_scores = {}

        # Score each emotion based on markers
        all_emotions = {}
        for category in ["primary", "secondary"]:
            if category in self.emotion_taxonomy:
                all_emotions.update(self.emotion_taxonomy[category])

        for emotion_name, emotion_data in all_emotions.items():
            markers = emotion_data.get("markers", [])
            score = 0.0
            matches = []

            for marker in markers:
                if marker in text_lower:
                    score += 1.0
                    matches.append(marker)

            # Normalize score
            if markers:
                score = min(1.0, score / len(markers))

            if score > 0:
                emotion_scores[emotion_name] = {
                    "score": score,
                    "matches": matches,
                    "valence": emotion_data.get("valence", 0.0),
                    "arousal": emotion_data.get("arousal", 0.0),
                }

        # Determine primary emotion
        primary_emotion = None
        max_score = 0.0

        if emotion_scores:
            primary_emotion = max(emotion_scores.items(), key=lambda x: x[1]["score"])[
                0
            ]
            max_score = emotion_scores[primary_emotion]["score"]

        # Calculate intensity (simple heuristic based on language intensity)
        intensity_indicators = [
            "very",
            "extremely",
            "incredibly",
            "absolutely",
            "totally",
            "completely",
        ]
        intensity_multiplier = 1.0
        for indicator in intensity_indicators:
            if indicator in text_lower:
                intensity_multiplier += 0.2

        intensity = min(1.0, max_score * intensity_multiplier)

        # Get all detected emotions sorted by score
        detected_emotions = sorted(
            [(name, data["score"]) for name, data in emotion_scores.items()],
            key=lambda x: x[1],
            reverse=True,
        )

        return {
            "primary_emotion": primary_emotion,
            "emotions": [name for name, score in detected_emotions if score > 0.2],
            "confidence": max_score,
            "intensity": intensity,
            "emotion_scores": {
                name: data["score"] for name, data in emotion_scores.items()
            },
            "valence": (
                emotion_scores[primary_emotion]["valence"] if primary_emotion else 0.0
            ),
            "arousal": (
                emotion_scores[primary_emotion]["arousal"] if primary_emotion else 0.0
            ),
        }

    def transition_emotion(
        self, current_emotion: str, context: str = "", trigger: str = ""
    ) -> Dict[str, Any]:
        """Predict emotion transition from current state"""
        if not current_emotion or current_emotion not in self.emotion_transitions:
            return {
                "current_emotion": current_emotion,
                "likely_transitions": [],
                "transition_probability": 0.0,
            }

        transitions = self.emotion_transitions.get(current_emotion, {})
        likely = transitions.get("likely_transitions", [])
        unlikely = transitions.get("unlikely_transitions", [])

        # If trigger provided, check if it suggests a transition
        transition_probability = 0.5  # Default

        if trigger:
            trigger_lower = trigger.lower()
            # Positive triggers might lead to positive transitions
            if any(
                word in trigger_lower for word in ["good", "great", "happy", "excited"]
            ):
                transition_probability = 0.7
            # Negative triggers might lead to negative transitions
            elif any(
                word in trigger_lower for word in ["bad", "sad", "angry", "worried"]
            ):
                transition_probability = 0.6

        return {
            "current_emotion": current_emotion,
            "likely_transitions": likely,
            "unlikely_transitions": unlikely,
            "transition_probability": transition_probability,
            "suggested_next": likely[0] if likely else None,
        }

    def select_emotion_response(
        self, detected_emotion: str, emotion_intensity: float = 0.5, context: str = ""
    ) -> Dict[str, Any]:
        """Select emotion-appropriate response strategy"""
        if not detected_emotion:
            return {
                "response_strategy": "neutral",
                "tone": "neutral",
                "should_show_empathy": False,
                "should_be_supportive": False,
            }

        # Get emotion data
        emotion_data = None
        for category in ["primary", "secondary"]:
            if (
                category in self.emotion_taxonomy
                and detected_emotion in self.emotion_taxonomy[category]
            ):
                emotion_data = self.emotion_taxonomy[category][detected_emotion]
                break

        if not emotion_data:
            return {
                "response_strategy": "neutral",
                "tone": "neutral",
                "should_show_empathy": False,
            }

        valence = emotion_data.get("valence", 0.0)
        arousal = emotion_data.get("arousal", 0.0)

        # Determine response strategy
        response_strategy = "neutral"
        tone = "neutral"
        should_show_empathy = False
        should_be_supportive = False

        # Negative emotions require empathy and support
        if valence < -0.5:
            response_strategy = "supportive_empathic"
            tone = "warm_caring"
            should_show_empathy = True
            should_be_supportive = True
        # Positive emotions can be celebratory
        elif valence > 0.7:
            response_strategy = "positive_engaging"
            tone = "enthusiastic_friendly"
            should_show_empathy = False
        # High arousal emotions need calming
        elif arousal > 0.7:
            response_strategy = "calming_reassuring"
            tone = "calm_reassuring"
            should_show_empathy = True

        # Adjust for intensity
        if emotion_intensity > 0.7:
            if valence < 0:
                tone = "very_caring"
            else:
                tone = "very_enthusiastic"

        return {
            "response_strategy": response_strategy,
            "tone": tone,
            "should_show_empathy": should_show_empathy,
            "should_be_supportive": should_be_supportive,
            "detected_emotion": detected_emotion,
            "emotion_intensity": emotion_intensity,
            "valence": valence,
            "arousal": arousal,
        }

    def get_emotion_graph(self) -> Dict[str, Any]:
        """Get full emotion taxonomy graph"""
        return {
            "taxonomy": self.emotion_taxonomy,
            "transitions": self.emotion_transitions,
            "total_emotions": sum(
                len(emotions) for emotions in self.emotion_taxonomy.values()
            ),
            "primary_count": len(self.emotion_taxonomy.get("primary", {})),
            "secondary_count": len(self.emotion_taxonomy.get("secondary", {})),
        }

    def get_emotion_intensity(self, text: str, emotion: str = "") -> Dict[str, Any]:
        """Get intensity of a specific emotion in text"""
        if not text:
            return {"emotion": emotion, "intensity": 0.0, "confidence": 0.0}

        # If emotion specified, check for that emotion
        if emotion:
            emotion_data = None
            for category in ["primary", "secondary"]:
                if (
                    category in self.emotion_taxonomy
                    and emotion in self.emotion_taxonomy[category]
                ):
                    emotion_data = self.emotion_taxonomy[category][emotion]
                    break

            if emotion_data:
                markers = emotion_data.get("markers", [])
                text_lower = text.lower()
                matches = sum(1 for marker in markers if marker in text_lower)
                intensity = min(1.0, matches / max(1, len(markers)))

                # Check for intensity amplifiers
                intensity_amplifiers = [
                    "very",
                    "extremely",
                    "incredibly",
                    "absolutely",
                    "totally",
                ]
                for amplifier in intensity_amplifiers:
                    if amplifier in text_lower:
                        intensity = min(1.0, intensity + 0.2)

                return {
                    "emotion": emotion,
                    "intensity": intensity,
                    "confidence": 0.8 if matches > 0 else 0.0,
                }

        # Otherwise, detect all emotions and return intensities
        detection_result = self.detect_emotion(text)
        return {
            "primary_emotion": detection_result.get("primary_emotion"),
            "intensity": detection_result.get("intensity", 0.0),
            "confidence": detection_result.get("confidence", 0.0),
            "all_emotions": detection_result.get("emotion_scores", {}),
        }

    def get_emotion_valence_arousal(self, emotion: str) -> Dict[str, Any]:
        """Get valence and arousal values for an emotion"""
        emotion_data = None
        category = None

        for cat in ["primary", "secondary"]:
            if cat in self.emotion_taxonomy and emotion in self.emotion_taxonomy[cat]:
                emotion_data = self.emotion_taxonomy[cat][emotion]
                category = cat
                break

        if not emotion_data:
            return {"emotion": emotion, "found": False, "valence": 0.0, "arousal": 0.0}

        return {
            "emotion": emotion,
            "category": category,
            "found": True,
            "valence": emotion_data.get("valence", 0.0),
            "arousal": emotion_data.get("arousal", 0.0),
            "intensity_range": emotion_data.get("intensity_range", [0.0, 1.0]),
            "sub_emotions": emotion_data.get("sub_emotions", []),
        }

    def validate_params(self, operation: str, params: Dict[str, Any]) -> bool:
        """Validate parameters for operations"""
        if operation == "detect_emotion":
            return "text" in params
        elif operation == "transition_emotion":
            return "current_emotion" in params
        elif operation == "select_emotion_response":
            return "detected_emotion" in params
        elif operation == "get_emotion_intensity":
            return "text" in params
        elif operation == "get_emotion_valence_arousal":
            return "emotion" in params
        return True
