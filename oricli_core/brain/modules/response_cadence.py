from __future__ import annotations
"""
Response Cadence Module - Prosody and rhythm control for natural speech-like flow
Handles sentence length variation, rhythm control, natural micro-pauses, and breathiness markers
"""

from pathlib import Path
from typing import Any, Dict, List
import json
import random
import re
import logging

from oricli_core.brain.base_module import BaseBrainModule, ModuleMetadata
from oricli_core.exceptions import InvalidParameterError

logger = logging.getLogger(__name__)


class ResponseCadenceModule(BaseBrainModule):
    """Control response cadence, prosody, and rhythm for natural flow"""

    def __init__(self):
        super().__init__()
        self.config = None
        self.rhythm_patterns = {}
        self.pause_patterns = {}
        self.breathiness_markers = {}
        self._load_config()

    @property
    def metadata(self) -> ModuleMetadata:
        return ModuleMetadata(
            name="response_cadence",
            version="1.0.0",
            description=(
                "Response cadence and prosody: sentence rhythm, pacing, "
                "micro-pauses, breathiness"
            ),
            operations=[
                "calculate_sentence_rhythm",
                "insert_natural_pauses",
                "apply_breathiness",
                "control_pacing",
                "apply_cadence",
            ],
            dependencies=[],
            model_required=False,
        )

    def initialize(self) -> bool:
        """Initialize the module"""
        return True

    def _load_config(self):
        """Load cadence configuration"""
        config_path = Path(__file__).parent / "response_cadence_config.json"
        try:
            if config_path.exists():
                with open(config_path, "r", encoding="utf-8") as f:
                    self.config = json.load(f)
                    self.rhythm_patterns = self.config.get("rhythm_patterns", {})
                    self.pause_patterns = self.config.get("pause_patterns", {})
                    self.breathiness_markers = self.config.get(
                        "breathiness_markers", {}
                    )
            else:
                # Default config
                self.rhythm_patterns = {
                    "short": {"min_words": 3, "max_words": 8},
                    "medium": {"min_words": 9, "max_words": 15},
                    "long": {"min_words": 16, "max_words": 25},
                }
                self.pause_patterns = {
                    "comma": ["after_conjunction", "before_clause", "in_lists"],
                    "period": ["sentence_end"],
                    "ellipsis": ["hesitation", "trailing_thought"],
                }
                self.breathiness_markers = {
                    "natural_breaks": [",", "—", "…"],
                    "phrasing_breaks": ["Well,", "So,", "You know,", "I mean,"],
                }
        except Exception as e:
            logger.warning(
                "Failed to load response_cadence config; using defaults",
                exc_info=True,
                extra={"module_name": "response_cadence", "error_type": type(e).__name__},
            )
            self.rhythm_patterns = {}
            self.pause_patterns = {}
            self.breathiness_markers = {}

    def execute(self, operation: str, params: Dict[str, Any]) -> Dict[str, Any]:
        """Execute a cadence operation"""
        if operation == "calculate_sentence_rhythm":
            text = params.get("text", "")
            return self.calculate_sentence_rhythm(text)
        elif operation == "insert_natural_pauses":
            text = params.get("text", "")
            return self.insert_natural_pauses(text)
        elif operation == "apply_breathiness":
            text = params.get("text", "")
            return self.apply_breathiness(text)
        elif operation == "control_pacing":
            text = params.get("text", "")
            content_type = params.get("content_type", "general")
            return self.control_pacing(text, content_type)
        elif operation == "apply_cadence":
            text = params.get("text", "")
            personality = params.get("personality", "oricli")
            return self.apply_cadence(text, personality)
        else:
            raise InvalidParameterError(
                parameter="operation",
                value=operation,
                reason="Unknown operation for response_cadence",
            )

    def calculate_sentence_rhythm(self, text: str) -> Dict[str, Any]:
        """Calculate and analyze sentence rhythm"""
        if not text:
            return {"text": text, "rhythm_score": 0.0, "pattern": "monotone"}

        # Split into sentences
        sentences = re.split(r"[.!?]+", text)
        sentences = [s.strip() for s in sentences if s.strip()]

        if not sentences:
            return {"text": text, "rhythm_score": 0.0, "pattern": "monotone"}

        # Calculate word counts per sentence
        word_counts = [len(s.split()) for s in sentences]

        # Calculate rhythm variation (coefficient of variation)
        avg_words = sum(word_counts) / len(word_counts) if word_counts else 0
        if avg_words > 0:
            variance = sum((wc - avg_words) ** 2 for wc in word_counts) / len(
                word_counts
            )
            std_dev = variance**0.5
            rhythm_score = std_dev / avg_words if avg_words > 0 else 0.0
        else:
            rhythm_score = 0.0

        # Determine rhythm pattern
        if rhythm_score < 0.2:
            pattern = "monotone"
        elif rhythm_score < 0.4:
            pattern = "slight_variation"
        elif rhythm_score < 0.6:
            pattern = "moderate_variation"
        else:
            pattern = "high_variation"

        # Classify sentence lengths
        length_distribution = {
            "short": len([wc for wc in word_counts if wc < 8]),
            "medium": len([wc for wc in word_counts if 8 <= wc < 16]),
            "long": len([wc for wc in word_counts if wc >= 16]),
        }

        return {
            "text": text,
            "rhythm_score": rhythm_score,
            "pattern": pattern,
            "sentence_count": len(sentences),
            "avg_words_per_sentence": avg_words,
            "word_counts": word_counts,
            "length_distribution": length_distribution,
        }

    def insert_natural_pauses(self, text: str) -> Dict[str, Any]:
        """Insert natural micro-pauses (commas, clause breaks)"""
        if not text:
            return {"text": text, "pauses_added": 0}

        paused_text = text
        pauses_added = 0

        # Find places to add natural pauses
        # 1. Before conjunctions in long sentences
        long_sentence_pattern = (
            r"(\w+\s+\w+\s+\w+\s+\w+\s+\w+\s+\w+\s+\w+\s+)(and|but|or|so)(\s+\w+)"
        )
        matches = list(re.finditer(long_sentence_pattern, paused_text, re.IGNORECASE))
        for match in reversed(matches):  # Reverse to maintain positions
            if random.random() < 0.4:  # 40% chance
                paused_text = (
                    paused_text[: match.end(1)] + ", " + match.group(2) + match.group(3)
                )
                pauses_added += 1

        # 2. Before relative clauses
        relative_clause_pattern = r"(\w+)(\s+)(which|that|who|where|when)(\s+\w+)"
        matches = list(re.finditer(relative_clause_pattern, paused_text, re.IGNORECASE))
        for match in reversed(matches):
            if random.random() < 0.3:  # 30% chance
                paused_text = (
                    paused_text[: match.end(1)]
                    + ","
                    + match.group(2)
                    + match.group(3)
                    + match.group(4)
                )
                pauses_added += 1

        # 3. After introductory phrases
        intro_phrases = [
            "Well",
            "So",
            "Actually",
            "You know",
            "I mean",
            "For example",
            "In fact",
        ]
        for phrase in intro_phrases:
            pattern = re.compile(r"\b" + re.escape(phrase) + r"\b", re.IGNORECASE)
            if (
                pattern.search(paused_text)
                and ","
                not in paused_text[
                    paused_text.find(phrase) : paused_text.find(phrase)
                    + len(phrase)
                    + 5
                ]
            ):
                paused_text = pattern.sub(phrase + ",", paused_text, count=1)
                pauses_added += 1
                break  # Only add one per text

        return {"text": paused_text, "pauses_added": pauses_added}

    def apply_breathiness(self, text: str) -> Dict[str, Any]:
        """Apply breathiness markers (natural phrasing breaks)"""
        if not text:
            return {"text": text, "breathiness_markers_added": 0}

        breathy_text = text
        markers_added = 0

        # Add natural phrasing breaks
        # 1. Add em-dash for natural breaks in thought
        if random.random() < 0.2:  # 20% chance
            # Find a good place (after a medium-length clause)
            sentences = re.split(r"[.!?]+", breathy_text)
            for i, sentence in enumerate(sentences):
                words = sentence.split()
                if 8 <= len(words) <= 15:  # Medium-length sentence
                    # Add em-dash before last few words occasionally
                    if random.random() < 0.3:
                        words_split = len(words) // 2
                        breathy_text = breathy_text.replace(
                            sentence,
                            " ".join(words[:words_split])
                            + " — "
                            + " ".join(words[words_split:]),
                        )
                        markers_added += 1
                        break

        # 2. Add ellipsis for trailing thoughts
        if random.random() < 0.15:  # 15% chance
            # Add ellipsis before last sentence occasionally
            sentences = re.split(r"[.!?]+", breathy_text)
            if len(sentences) > 1:
                last_sentence = sentences[-2].strip()
                if len(last_sentence.split()) < 10:  # Short sentence
                    breathy_text = breathy_text.replace(
                        last_sentence, last_sentence + "…"
                    )
                    markers_added += 1

        # 3. Add natural phrasing markers
        phrasing_markers = ["Well,", "So,", "You know,", "I mean,"]
        if random.random() < 0.25:  # 25% chance
            # Add at start of second sentence
            sentences = re.split(r"[.!?]+", breathy_text)
            if len(sentences) > 1:
                marker = random.choice(phrasing_markers)
                if not sentences[1].strip().startswith(marker):
                    sentences[1] = marker + " " + sentences[1].strip()
                    breathy_text = ". ".join(sentences) + "."
                    markers_added += 1

        return {"text": breathy_text, "breathiness_markers_added": markers_added}

    def control_pacing(
        self, text: str, content_type: str = "general"
    ) -> Dict[str, Any]:
        """Control pacing based on content type (fast for excitement, slower for reflection)"""
        if not text:
            return {"text": text, "pacing": "neutral"}

        paced_text = text

        # Determine target pacing based on content type
        pacing_rules = {
            "excitement": {
                "target_avg_words": 8,  # Shorter sentences
                "max_sentence_length": 12,
                "pause_probability": 0.2,  # Fewer pauses
            },
            "reflection": {
                "target_avg_words": 18,  # Longer sentences
                "max_sentence_length": 25,
                "pause_probability": 0.5,  # More pauses
            },
            "explanation": {
                "target_avg_words": 12,  # Medium sentences
                "max_sentence_length": 18,
                "pause_probability": 0.4,  # Moderate pauses
            },
            "general": {
                "target_avg_words": 12,
                "max_sentence_length": 20,
                "pause_probability": 0.3,
            },
        }

        rules = pacing_rules.get(content_type, pacing_rules["general"])

        # Split into sentences
        sentences = re.split(r"[.!?]+", paced_text)
        sentences = [s.strip() for s in sentences if s.strip()]

        if not sentences:
            return {"text": text, "pacing": content_type}

        # Adjust sentence lengths
        adjusted_sentences = []
        for sentence in sentences:
            words = sentence.split()
            word_count = len(words)

            # If sentence is too long for target pacing, break it
            if word_count > rules["max_sentence_length"]:
                # Break at comma or conjunction
                if "," in sentence:
                    parts = sentence.split(",", 1)
                    adjusted_sentences.append(parts[0].strip() + ".")
                    adjusted_sentences.append(parts[1].strip().capitalize() + ".")
                else:
                    # Break at midpoint
                    mid = len(words) // 2
                    adjusted_sentences.append(" ".join(words[:mid]) + ".")
                    adjusted_sentences.append(" ".join(words[mid:]).capitalize() + ".")
            else:
                adjusted_sentences.append(sentence)

        # Add pauses based on pacing rules
        if rules["pause_probability"] > 0.3:
            # Add more pauses for reflection
            for i, sentence in enumerate(adjusted_sentences):
                if random.random() < rules["pause_probability"] and "," not in sentence:
                    # Add pause before conjunction
                    if " and " in sentence or " but " in sentence:
                        sentence = sentence.replace(" and ", ", and ", 1)
                        sentence = sentence.replace(" but ", ", but ", 1)
                        adjusted_sentences[i] = sentence

        paced_text = ". ".join(adjusted_sentences) + "."

        return {
            "text": paced_text,
            "pacing": content_type,
            "target_avg_words": rules["target_avg_words"],
            "sentences_adjusted": len(adjusted_sentences) - len(sentences),
        }

    def apply_cadence(self, text: str, personality: str = "oricli") -> Dict[str, Any]:
        """Apply full cadence control based on personality"""
        if not text:
            return {"text": text, "cadence_applied": False}

        # Determine personality-specific cadence preferences
        personality_cadence = {
            "gen_z_cousin": {
                "rhythm": "high_variation",
                "pacing": "excitement",
                "breathiness": 0.4,
            },
            "calm_therapist": {
                "rhythm": "moderate_variation",
                "pacing": "reflection",
                "breathiness": 0.3,
            },
            "corporate_executive": {
                "rhythm": "slight_variation",
                "pacing": "explanation",
                "breathiness": 0.1,
            },
            "oricli": {
                "rhythm": "moderate_variation",
                "pacing": "general",
                "breathiness": 0.3,
            },
        }

        cadence_prefs = personality_cadence.get(
            personality.lower(), personality_cadence["oricli"]
        )

        cadenced_text = text

        # Apply rhythm
        rhythm_result = self.calculate_sentence_rhythm(cadenced_text)
        if rhythm_result["pattern"] != cadence_prefs["rhythm"]:
            # Adjust rhythm by varying sentence lengths
            # This is handled by natural_language_flow, so we'll just note it
            pass

        # Apply pacing
        pacing_result = self.control_pacing(cadenced_text, cadence_prefs["pacing"])
        cadenced_text = pacing_result["text"]

        # Apply breathiness
        if random.random() < cadence_prefs["breathiness"]:
            breathiness_result = self.apply_breathiness(cadenced_text)
            cadenced_text = breathiness_result["text"]

        # Insert natural pauses
        pause_result = self.insert_natural_pauses(cadenced_text)
        cadenced_text = pause_result["text"]

        return {
            "text": cadenced_text,
            "cadence_applied": True,
            "personality": personality,
            "rhythm_pattern": cadence_prefs["rhythm"],
            "pacing": cadence_prefs["pacing"],
        }

    def validate_params(
        self, operation: str, params: Dict[str, Any]
    ) -> bool:
        """Validate parameters for operations"""
        if operation in [
            "calculate_sentence_rhythm",
            "insert_natural_pauses",
            "apply_breathiness",
            "apply_cadence",
        ]:
            return "text" in params
        elif operation == "control_pacing":
            return "text" in params and "content_type" in params
        else:
            return True


# Module export
def create_module():
    return ResponseCadenceModule()
