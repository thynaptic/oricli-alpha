from __future__ import annotations
"""
Emotional Inference Module - Detect emotional intent, modulate warmth, and tune empathy
Claude-level emotional understanding: sensing tone, detecting emotional intent,
adjusting warmth/distance
"""

from pathlib import Path
from typing import Any, Dict, List, Optional
from datetime import datetime, timedelta
import json
import random
import re
import logging

from oricli_core.brain.base_module import BaseBrainModule, ModuleMetadata
from oricli_core.exceptions import InvalidParameterError

logger = logging.getLogger(__name__)


class EmotionalInferenceModule(BaseBrainModule):
    """Infer emotional intent and modulate response warmth and empathy"""

    def __init__(self):
        super().__init__()
        self.config = None
        self.emotion_patterns = {}
        self.warmth_modulators = {}
        self.empathy_tuners = {}
        self.affective_states: Dict[str, Dict[str, Any]] = {}
        self.mood_history: Dict[str, List[Dict[str, Any]]] = {}
        self.emotional_graph: Dict[str, List[str]] = {}
        self._load_config()
        self._initialize_emotional_graph()

    @property
    def metadata(self) -> ModuleMetadata:
        return ModuleMetadata(
            name="emotional_inference",
            version="2.0.0",
            description=(
                "Emotional inference: intent scoring, warmth modulation, empathy tuning, "
                "affective state tracking, mood curves, sentiment carryover, decay, "
                "tone compensation, emotional steering graphs"
            ),
            operations=[
                "score_emotional_intent",
                "calculate_warmth_level",
                "tune_empathy",
                "infer_emotion",
                "modulate_response_warmth",
                "track_affective_state",
                "calculate_mood_curve",
                "apply_sentiment_carryover",
                "apply_emotional_decay",
                "compensate_tone",
                "navigate_emotional_graph",
            ],
            dependencies=[],
            model_required=False,
        )

    def initialize(self) -> bool:
        """Initialize the module"""
        return True

    def _load_config(self):
        """Load emotional inference configuration"""
        config_path = Path(__file__).parent / "emotional_inference_config.json"
        try:
            if config_path.exists():
                with open(config_path, "r", encoding="utf-8") as f:
                    self.config = json.load(f)
                    self.emotion_patterns = self.config.get("emotion_patterns", {})
                    self.warmth_modulators = self.config.get("warmth_modulators", {})
                    self.empathy_tuners = self.config.get("empathy_tuners", {})
            else:
                # Default config
                self.emotion_patterns = {
                    "positive": [
                        "happy",
                        "excited",
                        "great",
                        "awesome",
                        "wonderful",
                        "amazing",
                        "love",
                        "enjoy",
                    ],
                    "negative": [
                        "sad",
                        "angry",
                        "frustrated",
                        "worried",
                        "stressed",
                        "tired",
                        "upset",
                        "disappointed",
                    ],
                    "neutral": ["okay", "fine", "alright", "normal", "regular"],
                    "seeking_help": [
                        "help",
                        "need",
                        "problem",
                        "issue",
                        "stuck",
                        "confused",
                        "don't understand",
                    ],
                    "sharing": [
                        "wanted to tell",
                        "thought you'd like",
                        "check this out",
                        "look at this",
                    ],
                }
                self.warmth_modulators = {
                    "high_warmth": [
                        "I'm here for you",
                        "I understand",
                        "That sounds",
                        "I hear you",
                    ],
                    "medium_warmth": [
                        "I see",
                        "Got it",
                        "That makes sense",
                        "I get that",
                    ],
                    "low_warmth": ["Understood", "Noted", "Acknowledged"],
                }
                self.empathy_tuners = {
                    "high_empathy": [
                        "That must be",
                        "I can imagine",
                        "That sounds really",
                        "I'm sorry you're",
                    ],
                    "medium_empathy": ["That's", "I understand", "That can be"],
                    "low_empathy": ["I see", "Okay", "Right"],
                }
        except Exception as e:
            logger.warning(
                "Failed to load emotional_inference config; using empty defaults",
                exc_info=True,
                extra={"module_name": "emotional_inference", "error_type": type(e).__name__},
            )
            self.emotion_patterns = {}
            self.warmth_modulators = {}
            self.empathy_tuners = {}

    def execute(self, operation: str, params: Dict[str, Any]) -> Dict[str, Any]:
        """Execute an emotional inference operation"""
        if operation == "score_emotional_intent":
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
            return self.score_emotional_intent(text, context)
        elif operation == "calculate_warmth_level":
            emotion_score = params.get("emotion_score", {})
            if emotion_score is None:
                emotion_score = {}
            if not isinstance(emotion_score, dict):
                raise InvalidParameterError(
                    "emotion_score", str(type(emotion_score).__name__), "emotion_score must be a dict"
                )
            return self.calculate_warmth_level(emotion_score)
        elif operation == "tune_empathy":
            text = params.get("text", "")
            emotion_score = params.get("emotion_score", {})
            if text is None:
                text = ""
            if emotion_score is None:
                emotion_score = {}
            if not isinstance(text, str):
                raise InvalidParameterError("text", str(type(text).__name__), "text must be a string")
            if not isinstance(emotion_score, dict):
                raise InvalidParameterError(
                    "emotion_score", str(type(emotion_score).__name__), "emotion_score must be a dict"
                )
            return self.tune_empathy(text, emotion_score)
        elif operation == "infer_emotion":
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
            return self.infer_emotion(text, context)
        elif operation == "modulate_response_warmth":
            response = params.get("response", "")
            emotion_score = params.get("emotion_score", {})
            if response is None:
                response = ""
            if emotion_score is None:
                emotion_score = {}
            if not isinstance(response, str):
                raise InvalidParameterError("response", str(type(response).__name__), "response must be a string")
            if not isinstance(emotion_score, dict):
                raise InvalidParameterError(
                    "emotion_score", str(type(emotion_score).__name__), "emotion_score must be a dict"
                )
            return self.modulate_response_warmth(response, emotion_score)
        elif operation == "track_affective_state":
            user_id = params.get("user_id", "default")
            text = params.get("text", "")
            context = params.get("context", "")
            if user_id is None:
                user_id = "default"
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
            return self.track_affective_state(user_id, text, context)
        elif operation == "calculate_mood_curve":
            user_id = params.get("user_id", "default")
            time_window = params.get("time_window", 24)
            if user_id is None:
                user_id = "default"
            if not isinstance(user_id, str):
                raise InvalidParameterError("user_id", str(type(user_id).__name__), "user_id must be a string")
            try:
                time_window_int = int(time_window)
            except (TypeError, ValueError):
                raise InvalidParameterError("time_window", str(time_window), "time_window must be an integer")
            if time_window_int < 1:
                raise InvalidParameterError("time_window", str(time_window_int), "time_window must be >= 1")
            return self.calculate_mood_curve(user_id, time_window)
        elif operation == "apply_sentiment_carryover":
            current_sentiment = params.get("current_sentiment", 0.0)
            previous_sentiment = params.get("previous_sentiment", 0.0)
            carryover_factor = params.get("carryover_factor", 0.3)
            try:
                float(current_sentiment)
                float(previous_sentiment)
                float(carryover_factor)
            except (TypeError, ValueError):
                raise InvalidParameterError(
                    "carryover_factor",
                    str(carryover_factor),
                    "current_sentiment, previous_sentiment, and carryover_factor must be numbers",
                )
            return self.apply_sentiment_carryover(
                current_sentiment, previous_sentiment, carryover_factor
            )
        elif operation == "apply_emotional_decay":
            user_id = params.get("user_id", "default")
            time_elapsed = params.get("time_elapsed", 1.0)
            decay_rate = params.get("decay_rate", 0.1)
            if user_id is None:
                user_id = "default"
            if not isinstance(user_id, str):
                raise InvalidParameterError("user_id", str(type(user_id).__name__), "user_id must be a string")
            try:
                float(time_elapsed)
                float(decay_rate)
            except (TypeError, ValueError):
                raise InvalidParameterError(
                    "time_elapsed",
                    str(time_elapsed),
                    "time_elapsed and decay_rate must be numbers",
                )
            return self.apply_emotional_decay(user_id, time_elapsed, decay_rate)
        elif operation == "compensate_tone":
            text = params.get("text", "")
            detected_emotion = params.get("detected_emotion", {})
            if text is None:
                text = ""
            if detected_emotion is None:
                detected_emotion = {}
            if not isinstance(text, str):
                raise InvalidParameterError("text", str(type(text).__name__), "text must be a string")
            if not isinstance(detected_emotion, dict):
                raise InvalidParameterError(
                    "detected_emotion", str(type(detected_emotion).__name__), "detected_emotion must be a dict"
                )
            return self.compensate_tone(text, detected_emotion)
        elif operation == "navigate_emotional_graph":
            current_state = params.get("current_state", "neutral")
            target_state = params.get("target_state")
            if current_state is None:
                current_state = "neutral"
            if not isinstance(current_state, str):
                raise InvalidParameterError(
                    "current_state", str(type(current_state).__name__), "current_state must be a string"
                )
            if target_state is not None and not isinstance(target_state, str):
                raise InvalidParameterError(
                    "target_state", str(type(target_state).__name__), "target_state must be a string when provided"
                )
            return self.navigate_emotional_graph(current_state, target_state)
        else:
            raise InvalidParameterError(
                parameter="operation",
                value=operation,
                reason="Unknown operation for emotional_inference",
            )

    def score_emotional_intent(self, text: str, context: str = "") -> Dict[str, Any]:
        """Score emotional intent from user input (detect tone, sentiment, emotional state)"""
        if not text:
            return {
                "emotion": "neutral",
                "intensity": 0.0,
                "sentiment": 0.0,
                "tone": "neutral",
                "confidence": 0.0,
            }

        text_lower = text.lower()
        combined_text = (text + " " + context).lower()

        # Score different emotional dimensions
        positive_score = 0.0
        negative_score = 0.0
        seeking_help_score = 0.0
        sharing_score = 0.0

        # Check for positive emotions
        positive_patterns = self.emotion_patterns.get("positive", [])
        for pattern in positive_patterns:
            if pattern in text_lower:
                positive_score += 0.2
            if pattern in combined_text:
                positive_score += 0.1

        # Check for negative emotions
        negative_patterns = self.emotion_patterns.get("negative", [])
        for pattern in negative_patterns:
            if pattern in text_lower:
                negative_score += 0.2
            if pattern in combined_text:
                negative_score += 0.1

        # Check for help-seeking
        help_patterns = self.emotion_patterns.get("seeking_help", [])
        for pattern in help_patterns:
            if pattern in text_lower:
                seeking_help_score += 0.3

        # Check for sharing
        sharing_patterns = self.emotion_patterns.get("sharing", [])
        for pattern in sharing_patterns:
            if pattern in text_lower:
                sharing_score += 0.2

        # Detect tone from punctuation and capitalization
        tone_indicators = {
            "excited": text.count("!") > 1 or text.isupper(),
            "questioning": text.count("?") > 0,
            "emphatic": text.count("!") > 0,
            "casual": any(
                word in text_lower for word in ["hey", "hi", "sup", "yo", "lol", "haha"]
            ),
        }

        # Determine primary emotion
        scores = {
            "positive": min(positive_score, 1.0),
            "negative": min(negative_score, 1.0),
            "seeking_help": min(seeking_help_score, 1.0),
            "sharing": min(sharing_score, 1.0),
        }

        primary_emotion = max(scores, key=scores.get)
        intensity = scores[primary_emotion]

        # Determine tone
        excited, questioning, emphatic, casual = (
            tone_indicators["excited"],
            tone_indicators["questioning"],
            tone_indicators["emphatic"],
            tone_indicators["casual"],
        )
        if excited:
            tone = "excited"
        elif questioning:
            tone = "questioning"
        elif emphatic:
            tone = "emphatic"
        elif casual:
            tone = "casual"
        else:
            tone = "neutral"

        # Calculate sentiment (-1.0 to 1.0)
        sentiment = positive_score - negative_score
        sentiment = max(-1.0, min(1.0, sentiment))

        # Confidence based on how clear the signals are
        confidence = intensity if intensity > 0.3 else 0.3

        return {
            "emotion": primary_emotion,
            "intensity": intensity,
            "sentiment": sentiment,
            "tone": tone,
            "confidence": confidence,
            "scores": scores,
        }

    def calculate_warmth_level(self, emotion_score: Dict[str, Any]) -> Dict[str, Any]:
        """Calculate appropriate warmth level based on detected emotion"""
        if not emotion_score:
            return {"warmth_level": "medium", "warmth_score": 0.5}

        emotion = emotion_score.get("emotion", "neutral")
        intensity = emotion_score.get("intensity", 0.0)
        sentiment = emotion_score.get("sentiment", 0.0)

        # Determine warmth level
        if emotion == "negative" and intensity > 0.5:
            warmth_level = "high"
            warmth_score = 0.8
        elif emotion == "seeking_help" and intensity > 0.4:
            warmth_level = "high"
            warmth_score = 0.75
        elif emotion == "positive" and intensity > 0.6:
            warmth_level = "medium_high"
            warmth_score = 0.65
        elif sentiment < -0.3:
            warmth_level = "high"
            warmth_score = 0.7
        elif sentiment > 0.5:
            warmth_level = "medium_high"
            warmth_score = 0.6
        elif emotion == "sharing":
            warmth_level = "medium"
            warmth_score = 0.5
        else:
            warmth_level = "medium"
            warmth_score = 0.5


        return {
            "warmth_level": warmth_level,
            "warmth_score": warmth_score,
            "recommended_modulators": self.warmth_modulators.get(
                warmth_level, self.warmth_modulators.get("medium_warmth", [])
            ),
        }

    def tune_empathy(self, text: str, emotion_score: Dict[str, Any]) -> Dict[str, Any]:
        """Tune conversational empathy based on emotional context"""
        if not text or not emotion_score:
            return {"text": text, "empathy_tuned": False}

        emotion = emotion_score.get("emotion", "neutral")
        intensity = emotion_score.get("intensity", 0.0)
        sentiment = emotion_score.get("sentiment", 0.0)

        # Determine empathy level needed
        if emotion == "negative" and intensity > 0.5:
            empathy_level = "high"
        elif emotion == "seeking_help" and intensity > 0.4:
            empathy_level = "high"
        elif sentiment < -0.3:
            empathy_level = "high"
        elif emotion == "positive" and intensity > 0.6:
            empathy_level = "medium"
        else:
            empathy_level = "medium"

        # Get empathy phrases
        empathy_phrases = self.empathy_tuners.get(
            f"{empathy_level}_empathy", self.empathy_tuners.get("medium_empathy", [])
        )

        # Check if text already has empathy markers
        has_empathy = any(phrase.lower() in text.lower() for phrase in empathy_phrases)

        tuned_text = text
        empathy_added = False

        # Add empathy marker if needed and not present
        if empathy_level == "high" and not has_empathy:
            # Add empathy phrase at the start
            empathy_phrase = empathy_phrases[0] if empathy_phrases else "I understand"
            tuned_text = f"{empathy_phrase} {tuned_text.lower()}"
            tuned_text = tuned_text[0].upper() + tuned_text[1:]
            empathy_added = True

        return {
            "text": tuned_text,
            "empathy_tuned": empathy_added,
            "empathy_level": empathy_level,
            "emotion_context": emotion,
        }

    def infer_emotion(self, text: str, context: str = "") -> Dict[str, Any]:
        """Complete emotional inference pipeline"""
        emotion_score = self.score_emotional_intent(text, context)
        warmth_result = self.calculate_warmth_level(emotion_score)

        return {
            "emotion_score": emotion_score,
            "warmth": warmth_result,
            "recommended_approach": self._recommend_approach(
                emotion_score, warmth_result
            ),
        }

    def modulate_response_warmth(
        self, response: str, emotion_score: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Modulate response warmth based on detected emotion"""
        if not response or not emotion_score:
            return {"response": response, "warmth_modulated": False}

        warmth_result = self.calculate_warmth_level(emotion_score)
        warmth_level = warmth_result.get("warmth_level", "medium")
        modulators = warmth_result.get("recommended_modulators", [])

        modulated_response = response
        warmth_added = False

        # Add warmth modulators if needed
        if warmth_level in ["high", "medium_high"] and modulators:
            # Check if response already has warmth
            has_warmth = any(
                modulator.lower() in modulated_response.lower()
                for modulator in modulators
            )

            if not has_warmth and random.random() < 0.4:  # 40% chance
                # Add warmth phrase at the start
                warmth_phrase = random.choice(modulators)
                modulated_response = f"{warmth_phrase} {modulated_response.lower()}"
                modulated_response = (
                    modulated_response[0].upper() + modulated_response[1:]
                )
                warmth_added = True

        return {
            "response": modulated_response,
            "warmth_modulated": warmth_added,
            "warmth_level": warmth_level,
            "warmth_score": warmth_result.get("warmth_score", 0.5),
        }

    def _recommend_approach(
        self, emotion_score: Dict[str, Any], warmth_result: Dict[str, Any]
    ) -> str:
        """Recommend conversational approach based on emotion and warmth"""
        emotion = emotion_score.get("emotion", "neutral")
        intensity = emotion_score.get("intensity", 0.0)
        warmth_level = warmth_result.get("warmth_level", "medium")

        if emotion == "negative" and intensity > 0.6:
            return "supportive_empathetic"
        elif emotion == "seeking_help" and intensity > 0.5:
            return "helpful_encouraging"
        elif emotion == "positive" and intensity > 0.6:
            return "enthusiastic_matching"
        elif warmth_level == "high":
            return "warm_supportive"
        else:
            return "balanced_conversational"

    def _initialize_emotional_graph(self) -> None:
        """Initialize emotional state transition graph"""
        self.emotional_graph = {
            "neutral": ["positive", "negative", "excited", "calm"],
            "positive": ["excited", "happy", "neutral", "calm"],
            "negative": ["sad", "angry", "anxious", "neutral"],
            "excited": ["positive", "happy", "neutral"],
            "sad": ["negative", "neutral", "calm"],
            "angry": ["negative", "frustrated", "neutral"],
            "anxious": ["negative", "worried", "calm", "neutral"],
            "happy": ["positive", "excited", "neutral"],
            "calm": ["neutral", "positive", "relaxed"],
            "frustrated": ["negative", "angry", "neutral"],
            "worried": ["anxious", "negative", "neutral"],
            "relaxed": ["calm", "positive", "neutral"],
        }

    def track_affective_state(
        self, user_id: str, text: str, context: str = ""
    ) -> Dict[str, Any]:
        """Track multi-dimensional affective state (valence, arousal, dominance)"""
        emotion_score = self.score_emotional_intent(text, context)

        # Calculate valence (-1.0 to 1.0)
        sentiment = emotion_score.get("sentiment", 0.0)
        valence = sentiment

        # Calculate arousal (0.0 to 1.0) based on intensity and tone
        intensity = emotion_score.get("intensity", 0.0)
        tone = emotion_score.get("tone", "neutral")
        arousal = intensity
        if tone in ["excited", "emphatic"]:
            arousal = min(1.0, arousal + 0.2)

        # Calculate dominance (0.0 to 1.0) based on emotion type
        emotion = emotion_score.get("emotion", "neutral")
        dominance_map = {
            "positive": 0.7,
            "negative": 0.3,
            "seeking_help": 0.2,
            "sharing": 0.6,
            "neutral": 0.5,
        }
        dominance = dominance_map.get(emotion, 0.5)

        # Update affective state
        if user_id not in self.affective_states:
            self.affective_states[user_id] = {
                "valence": 0.0,
                "arousal": 0.5,
                "dominance": 0.5,
                "history": [],
            }

        current_state = self.affective_states[user_id]
        current_state["valence"] = valence
        current_state["arousal"] = arousal
        current_state["dominance"] = dominance
        current_state["last_updated"] = datetime.now().isoformat()

        # Add to history
        history_entry = {
            "valence": valence,
            "arousal": arousal,
            "dominance": dominance,
            "timestamp": datetime.now().isoformat(),
            "emotion": emotion,
            "intensity": intensity,
        }
        current_state["history"].append(history_entry)
        if len(current_state["history"]) > 100:
            current_state["history"] = current_state["history"][-100:]

        # Update mood history
        if user_id not in self.mood_history:
            self.mood_history[user_id] = []
        self.mood_history[user_id].append(
            {
                "mood": emotion,
                "valence": valence,
                "timestamp": datetime.now().isoformat(),
            }
        )
        if len(self.mood_history[user_id]) > 200:
            self.mood_history[user_id] = self.mood_history[user_id][-200:]

        return {
            "user_id": user_id,
            "affective_state": {
                "valence": valence,
                "arousal": arousal,
                "dominance": dominance,
            },
            "emotion": emotion,
            "intensity": intensity,
            "timestamp": datetime.now().isoformat(),
        }

    def calculate_mood_curve(
        self, user_id: str, time_window: int = 24
    ) -> Dict[str, Any]:
        """Calculate mood curve over time window (hours)"""
        if user_id not in self.mood_history:
            return {
                "user_id": user_id,
                "mood_curve": [],
                "trend": "stable",
                "average_valence": 0.0,
            }

        history = self.mood_history[user_id]
        if not history:
            return {
                "user_id": user_id,
                "mood_curve": [],
                "trend": "stable",
                "average_valence": 0.0,
            }

        # Filter by time window
        cutoff_time = datetime.now() - timedelta(hours=time_window)
        recent_history = [
            h
            for h in history
            if datetime.fromisoformat(h["timestamp"]) > cutoff_time
        ]

        if not recent_history:
            return {
                "user_id": user_id,
                "mood_curve": [],
                "trend": "stable",
                "average_valence": 0.0,
            }

        # Calculate trend
        valences = [h["valence"] for h in recent_history]
        average_valence = sum(valences) / len(valences)

        # Simple trend calculation
        if len(valences) >= 2:
            first_half = valences[: len(valences) // 2]
            second_half = valences[len(valences) // 2 :]
            first_avg = sum(first_half) / len(first_half)
            second_avg = sum(second_half) / len(second_half)

            if second_avg > first_avg + 0.1:
                trend = "improving"
            elif second_avg < first_avg - 0.1:
                trend = "declining"
            else:
                trend = "stable"
        else:
            trend = "stable"

        return {
            "user_id": user_id,
            "mood_curve": recent_history,
            "trend": trend,
            "average_valence": average_valence,
            "data_points": len(recent_history),
        }

    def apply_sentiment_carryover(
        self,
        current_sentiment: float,
        previous_sentiment: float,
        carryover_factor: float = 0.3,
    ) -> Dict[str, Any]:
        """Apply sentiment carryover from previous state"""
        # Weighted combination of current and previous sentiment
        adjusted_sentiment = (
            current_sentiment * (1.0 - carryover_factor)
            + previous_sentiment * carryover_factor
        )

        # Clamp to valid range
        adjusted_sentiment = max(-1.0, min(1.0, adjusted_sentiment))

        return {
            "original_sentiment": current_sentiment,
            "previous_sentiment": previous_sentiment,
            "adjusted_sentiment": adjusted_sentiment,
            "carryover_factor": carryover_factor,
            "carryover_applied": True,
        }

    def apply_emotional_decay(
        self, user_id: str, time_elapsed: float, decay_rate: float = 0.1
    ) -> Dict[str, Any]:
        """Apply exponential decay to emotional intensity over time"""
        if user_id not in self.affective_states:
            return {
                "user_id": user_id,
                "decay_applied": False,
                "new_state": None,
            }

        state = self.affective_states[user_id]

        # Apply exponential decay: new = old * e^(-decay_rate * time)
        import math

        decay_factor = math.exp(-decay_rate * time_elapsed)

        original_arousal = state.get("arousal", 0.5)
        original_intensity = state.get("intensity", 0.0)

        new_arousal = original_arousal * decay_factor + 0.5 * (1 - decay_factor)
        new_intensity = original_intensity * decay_factor

        state["arousal"] = new_arousal
        state["intensity"] = new_intensity
        state["last_decay"] = datetime.now().isoformat()

        return {
            "user_id": user_id,
            "decay_applied": True,
            "original_arousal": original_arousal,
            "new_arousal": new_arousal,
            "original_intensity": original_intensity,
            "new_intensity": new_intensity,
            "decay_factor": decay_factor,
            "time_elapsed": time_elapsed,
        }

    def compensate_tone(
        self, text: str, detected_emotion: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Compensate tone based on detected emotion"""
        if not text or not detected_emotion:
            return {"text": text, "tone_compensated": False}

        emotion = detected_emotion.get("emotion", "neutral")
        sentiment = detected_emotion.get("sentiment", 0.0)
        intensity = detected_emotion.get("intensity", 0.0)

        compensated_text = text
        compensation_applied = False

        # Apply tone compensation based on emotion
        if sentiment < -0.5 and intensity > 0.6:
            # Very negative - soften tone
            if not any(
                word in text.lower()
                for word in ["understand", "sorry", "here", "support"]
            ):
                compensated_text = f"I understand. {text}"
                compensation_applied = True
        elif sentiment > 0.5 and intensity > 0.6:
            # Very positive - match enthusiasm
            if not any(
                word in text.lower()
                for word in ["great", "wonderful", "excited", "amazing"]
            ):
                compensated_text = f"That's great! {text}"
                compensation_applied = True
        elif emotion == "seeking_help" and intensity > 0.4:
            # Help-seeking - be supportive
            if not any(
                word in text.lower()
                for word in ["help", "support", "assist", "here"]
            ):
                compensated_text = f"I'm here to help. {text}"
                compensation_applied = True

        return {
            "original_text": text,
            "compensated_text": compensated_text,
            "tone_compensated": compensation_applied,
            "compensation_type": emotion,
        }

    def navigate_emotional_graph(
        self, current_state: str, target_state: Optional[str] = None
    ) -> Dict[str, Any]:
        """Navigate emotional state transitions using graph"""
        if current_state not in self.emotional_graph:
            return {
                "current_state": current_state,
                "possible_transitions": [],
                "path_to_target": [],
                "error": "Unknown state",
            }

        possible_transitions = self.emotional_graph[current_state]

        path_to_target = []
        if target_state:
            # Find path from current to target
            path_to_target = self._find_emotional_path(
                current_state, target_state
            )

        return {
            "current_state": current_state,
            "possible_transitions": possible_transitions,
            "path_to_target": path_to_target,
            "target_state": target_state,
        }

    def _find_emotional_path(
        self, start: str, target: str, max_depth: int = 3
    ) -> List[str]:
        """Find shortest path between emotional states using BFS"""
        if start == target:
            return [start]

        queue: List[tuple[str, List[str]]] = [(start, [start])]
        visited = {start}

        depth = 0
        while queue and depth < max_depth:
            depth += 1
            current, path = queue.pop(0)

            if current not in self.emotional_graph:
                continue

            for next_state in self.emotional_graph[current]:
                if next_state == target:
                    return path + [target]

                if next_state not in visited:
                    visited.add(next_state)
                    queue.append((next_state, path + [next_state]))

        return []

    def validate_params(self, operation: str, params: Dict[str, Any]) -> bool:
        """Validate parameters for operations"""
        if operation == 'score_emotional_intent' or operation == 'infer_emotion':
            return "text" in params
        elif operation == 'calculate_warmth_level' or operation == 'tune_empathy' or operation == 'modulate_response_warmth':
            return "emotion_score" in params or "text" in params
        elif operation == "track_affective_state":
            return "text" in params
        elif operation == 'calculate_mood_curve' or operation == 'apply_emotional_decay':
            return "user_id" in params
        elif operation == "apply_sentiment_carryover":
            return "current_sentiment" in params and "previous_sentiment" in params
        elif operation == "compensate_tone":
            return "text" in params and "detected_emotion" in params
        elif operation == "navigate_emotional_graph":
            return "current_state" in params
        else:
            return True


# Module export
def create_module():
    return EmotionalInferenceModule()
