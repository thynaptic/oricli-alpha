from __future__ import annotations
"""
Uncertainty Expression Module - Natural uncertainty handling
Handles expressing uncertainty appropriately, using hedging language, natural corrections, and confidence modulation
"""

from typing import Dict, Any, List, Optional
import json
import random
from pathlib import Path
import logging

from oricli_core.brain.base_module import BaseBrainModule, ModuleMetadata
from oricli_core.exceptions import InvalidParameterError

logger = logging.getLogger(__name__)


class UncertaintyExpressionModule(BaseBrainModule):
    """Natural uncertainty expression and hedging"""

    def __init__(self):
        super().__init__()
        self.config = None
        self.hedging_phrases = {}
        self.uncertainty_markers = {}
        self.correction_patterns = {}
        self._load_config()

    @property
    def metadata(self) -> ModuleMetadata:
        return ModuleMetadata(
            name="uncertainty_expression",
            version="1.0.0",
            description="Uncertainty expression: hedging language, natural corrections, confidence modulation",
            operations=[
                "add_hedging",
                "express_uncertainty",
                "natural_correction",
                "modulate_confidence",
                "add_qualifiers",
            ],
            dependencies=[],
            model_required=False,
        )

    def initialize(self) -> bool:
        """Initialize the module"""
        return True

    def _load_config(self):
        """Load uncertainty expression configuration"""
        config_path = Path(__file__).parent / "uncertainty_expression_config.json"
        try:
            if config_path.exists():
                with open(config_path, "r", encoding="utf-8") as f:
                    self.config = json.load(f)
                    self.hedging_phrases = self.config.get("hedging_phrases", {})
                    self.uncertainty_markers = self.config.get(
                        "uncertainty_markers", {}
                    )
                    self.correction_patterns = self.config.get(
                        "correction_patterns", {}
                    )
            else:
                # Default config
                self.hedging_phrases = {
                    "high_confidence": ["I'm fairly sure", "I believe", "I think"],
                    "medium_confidence": [
                        "I think",
                        "I believe",
                        "It seems",
                        "It appears",
                    ],
                    "low_confidence": [
                        "I'm not entirely sure",
                        "I'm not certain",
                        "It might be",
                        "Perhaps",
                    ],
                }
                self.uncertainty_markers = {
                    "mild": ["maybe", "perhaps", "possibly", "might", "could"],
                    "moderate": ["I think", "I believe", "probably", "likely"],
                    "strong": ["I'm not sure", "uncertain", "unclear", "hard to say"],
                }
        except Exception as e:
            logger.warning(
                "Failed to load uncertainty_expression config; using empty defaults",
                exc_info=True,
                extra={"module_name": "uncertainty_expression", "error_type": type(e).__name__},
            )
            self.hedging_phrases = {}
            self.uncertainty_markers = {}
            self.correction_patterns = {}

    def execute(self, operation: str, params: Dict[str, Any]) -> Dict[str, Any]:
        """Execute an uncertainty expression operation"""
        if operation == "add_hedging":
            text = params.get("text", "")
            confidence_level = params.get("confidence_level", "medium")
            if text is None:
                text = ""
            if confidence_level is None:
                confidence_level = "medium"
            if not isinstance(text, str):
                raise InvalidParameterError("text", str(type(text).__name__), "text must be a string")
            if not isinstance(confidence_level, str):
                raise InvalidParameterError(
                    "confidence_level", str(type(confidence_level).__name__), "confidence_level must be a string"
                )
            return self.add_hedging(text, confidence_level)
        elif operation == "express_uncertainty":
            text = params.get("text", "")
            uncertainty_level = params.get("uncertainty_level", "moderate")
            if text is None:
                text = ""
            if uncertainty_level is None:
                uncertainty_level = "moderate"
            if not isinstance(text, str):
                raise InvalidParameterError("text", str(type(text).__name__), "text must be a string")
            if not isinstance(uncertainty_level, str):
                raise InvalidParameterError(
                    "uncertainty_level", str(type(uncertainty_level).__name__), "uncertainty_level must be a string"
                )
            return self.express_uncertainty(text, uncertainty_level)
        elif operation == "natural_correction":
            original_text = params.get("original_text", "")
            corrected_text = params.get("corrected_text", "")
            if original_text is None:
                original_text = ""
            if corrected_text is None:
                corrected_text = ""
            if not isinstance(original_text, str):
                raise InvalidParameterError(
                    "original_text", str(type(original_text).__name__), "original_text must be a string"
                )
            if not isinstance(corrected_text, str):
                raise InvalidParameterError(
                    "corrected_text", str(type(corrected_text).__name__), "corrected_text must be a string"
                )
            return self.natural_correction(original_text, corrected_text)
        elif operation == "modulate_confidence":
            text = params.get("text", "")
            confidence = params.get("confidence", 0.5)
            if text is None:
                text = ""
            if not isinstance(text, str):
                raise InvalidParameterError("text", str(type(text).__name__), "text must be a string")
            try:
                float(confidence)
            except (TypeError, ValueError):
                raise InvalidParameterError("confidence", str(confidence), "confidence must be a number")
            return self.modulate_confidence(text, confidence)
        elif operation == "add_qualifiers":
            text = params.get("text", "")
            formality = params.get("formality", "neutral")
            if text is None:
                text = ""
            if formality is None:
                formality = "neutral"
            if not isinstance(text, str):
                raise InvalidParameterError("text", str(type(text).__name__), "text must be a string")
            if not isinstance(formality, str):
                raise InvalidParameterError("formality", str(type(formality).__name__), "formality must be a string")
            return self.add_qualifiers(text, formality)
        else:
            raise InvalidParameterError(
                parameter="operation",
                value=operation,
                reason="Unknown operation for uncertainty_expression",
            )

    def add_hedging(
        self, text: str, confidence_level: str = "medium"
    ) -> Dict[str, Any]:
        """Add hedging language based on confidence level"""
        if not text:
            return {"hedged_text": text, "hedging_added": False}

        # Get appropriate hedging phrases
        phrases = self.hedging_phrases.get(
            confidence_level, self.hedging_phrases.get("medium", [])
        )

        if not phrases:
            return {"hedged_text": text, "hedging_added": False}

        # Check if text already has hedging
        has_hedging = any(
            phrase.lower() in text.lower()
            for phrase_group in self.hedging_phrases.values()
            for phrase in phrase_group
        )

        if has_hedging:
            return {
                "hedged_text": text,
                "hedging_added": False,
                "reason": "already_hedged",
            }

        # Add hedging phrase at start (30% chance)
        if random.random() < 0.3:
            phrase = random.choice(phrases)
            hedged_text = phrase + ", " + text.lower()
            hedged_text = hedged_text[0].upper() + hedged_text[1:]
            return {
                "hedged_text": hedged_text,
                "hedging_added": True,
                "hedging_phrase": phrase,
            }

        return {"hedged_text": text, "hedging_added": False}

    def express_uncertainty(
        self, text: str, uncertainty_level: str = "moderate"
    ) -> Dict[str, Any]:
        """Express uncertainty naturally"""
        if not text:
            return {"uncertain_text": text, "uncertainty_added": False}

        markers = self.uncertainty_markers.get(
            uncertainty_level, self.uncertainty_markers.get("moderate", [])
        )

        if not markers:
            return {"uncertain_text": text, "uncertainty_added": False}

        # Check if already has uncertainty markers
        text_lower = text.lower()
        has_uncertainty = any(
            marker in text_lower
            for marker_group in self.uncertainty_markers.values()
            for marker in marker_group
        )

        if has_uncertainty:
            return {
                "uncertain_text": text,
                "uncertainty_added": False,
                "reason": "already_uncertain",
            }

        # Add uncertainty marker (40% chance)
        if random.random() < 0.4:
            marker = random.choice(markers)

            # Insert marker appropriately
            if uncertainty_level == "mild":
                # Insert mid-sentence sometimes
                words = text.split()
                if len(words) > 5 and random.random() < 0.5:
                    insert_pos = len(words) // 2
                    words.insert(insert_pos, marker)
                    uncertain_text = " ".join(words)
                else:
                    uncertain_text = marker.capitalize() + " " + text.lower()
            else:
                uncertain_text = marker.capitalize() + " " + text.lower()

            return {
                "uncertain_text": uncertain_text,
                "uncertainty_added": True,
                "marker": marker,
            }

        return {"uncertain_text": text, "uncertainty_added": False}

    def natural_correction(
        self, original_text: str, corrected_text: str
    ) -> Dict[str, Any]:
        """Generate natural correction/reconsideration"""
        if not original_text or not corrected_text:
            return {"correction_text": corrected_text, "correction_added": False}

        correction_patterns = self.correction_patterns.get(
            "patterns",
            [
                "Actually,",
                "Wait, let me reconsider.",
                "On second thought,",
                "Actually, I think",
                "Let me correct that -",
                "Actually, it might be",
                "I should clarify -",
            ],
        )

        pattern = random.choice(correction_patterns)
        correction_text = pattern + " " + corrected_text.lower()
        correction_text = correction_text[0].upper() + correction_text[1:]

        return {
            "correction_text": correction_text,
            "correction_added": True,
            "pattern_used": pattern,
        }

    def modulate_confidence(self, text: str, confidence: float) -> Dict[str, Any]:
        """Modulate confidence level in text"""
        if not text:
            return {"modulated_text": text, "confidence_level": confidence}

        # Map confidence to level
        if confidence >= 0.8:
            level = "high_confidence"
        elif confidence >= 0.5:
            level = "medium_confidence"
        else:
            level = "low_confidence"

        # Add appropriate hedging
        hedged_result = self.add_hedging(text, level)
        modulated_text = hedged_result.get("hedged_text", text)

        # Also add qualifiers for lower confidence
        if confidence < 0.6:
            qualifier_result = self.add_qualifiers(modulated_text, "neutral")
            modulated_text = qualifier_result.get("qualified_text", modulated_text)

        return {
            "modulated_text": modulated_text,
            "confidence_level": level,
            "confidence_score": confidence,
            "hedging_applied": hedged_result.get("hedging_added", False),
        }

    def add_qualifiers(self, text: str, formality: str = "neutral") -> Dict[str, Any]:
        """Add qualifiers to soften statements"""
        if not text:
            return {"qualified_text": text, "qualifiers_added": []}

        qualifiers = {
            "neutral": [
                "sort of",
                "kind of",
                "pretty much",
                "basically",
                "essentially",
            ],
            "formal": ["essentially", "primarily", "fundamentally", "largely"],
            "casual": ["kinda", "sorta", "pretty much", "basically"],
        }

        qualifier_list = qualifiers.get(formality, qualifiers["neutral"])

        qualified_text = text
        qualifiers_added = []

        # Add qualifiers occasionally (20% chance)
        if random.random() < 0.2:
            qualifier = random.choice(qualifier_list)
            # Insert before key verbs/adjectives
            words = qualified_text.split()
            if len(words) > 3:
                # Insert before last verb/adjective if found
                verb_positions = []
                common_verbs = [
                    "is",
                    "are",
                    "was",
                    "were",
                    "has",
                    "have",
                    "do",
                    "does",
                    "think",
                    "know",
                ]
                for i, word in enumerate(words):
                    if word.lower() in common_verbs:
                        verb_positions.append(i)

                if verb_positions:
                    insert_pos = verb_positions[-1]
                    words.insert(insert_pos, qualifier)
                    qualified_text = " ".join(words)
                    qualifiers_added.append(qualifier)

        return {"qualified_text": qualified_text, "qualifiers_added": qualifiers_added}

    def validate_params(self, operation: str, params: Dict[str, Any]) -> bool:
        """Validate parameters for operations"""
        if operation == "add_hedging":
            return "text" in params
        elif operation == "express_uncertainty":
            return "text" in params
        elif operation == "natural_correction":
            return "original_text" in params and "corrected_text" in params
        elif operation == "modulate_confidence":
            return "text" in params and "confidence" in params
        elif operation == "add_qualifiers":
            return "text" in params
        return True
