from __future__ import annotations
"""
Response Naturalizer Module - Post-processing layer for human-like touches
Handles sentence structure randomization, natural pronoun usage, contraction application, and overall naturalization
"""

from typing import Dict, Any, List, Optional
import json
import re
import random
from pathlib import Path
import logging

from mavaia_core.brain.base_module import BaseBrainModule, ModuleMetadata
from mavaia_core.exceptions import InvalidParameterError

logger = logging.getLogger(__name__)


class ResponseNaturalizerModule(BaseBrainModule):
    """Post-processing layer to add human-like naturalization"""

    def __init__(self):
        super().__init__()
        self.config = None
        self.contraction_rules = {}
        self.pronoun_patterns = {}
        self.naturalization_rules = {}
        self._load_config()

    @property
    def metadata(self) -> ModuleMetadata:
        return ModuleMetadata(
            name="response_naturalizer",
            version="1.0.0",
            description="Response naturalizer: post-processing for human-like touches, contractions, pronouns, variation",
            operations=[
                "naturalize_response",
                "apply_contractions",
                "naturalize_pronouns",
                "add_human_touches",
                "complete_naturalization",
                "add_uncertainty_markers",
                "adjust_formality",
                "add_conversational_repair",
            ],
            dependencies=[],
            model_required=False,
        )

    def initialize(self) -> bool:
        """Initialize the module"""
        return True

    def _load_config(self):
        """Load response naturalizer configuration"""
        config_path = Path(__file__).parent / "response_naturalizer_config.json"
        try:
            if config_path.exists():
                with open(config_path, "r", encoding="utf-8") as f:
                    self.config = json.load(f)
                    self.contraction_rules = self.config.get("contraction_rules", {})
                    self.pronoun_patterns = self.config.get("pronoun_patterns", {})
                    self.naturalization_rules = self.config.get(
                        "naturalization_rules", {}
                    )
            else:
                # Default config
                self.contraction_rules = {
                    "formal": {"enabled": False},
                    "neutral": {"enabled": True, "probability": 0.6},
                    "informal": {"enabled": True, "probability": 0.9},
                }
                self.pronoun_patterns = {
                    "use_you": True,
                    "use_we": True,
                    "natural_references": True,
                }
        except Exception as e:
            logger.warning(
                "Failed to load response_naturalizer config; using defaults",
                exc_info=True,
                extra={"module_name": "response_naturalizer", "error_type": type(e).__name__},
            )
            self.contraction_rules = {}
            self.pronoun_patterns = {}
            self.naturalization_rules = {}

    def execute(self, operation: str, params: Dict[str, Any]) -> Dict[str, Any]:
        """Execute a response naturalizer operation"""
        if operation == "naturalize_response":
            response = params.get("response", "")
            formality = params.get("formality", "neutral")
            context = params.get("context", {})
            return self.naturalize_response(response, formality, context)
        elif operation == "apply_contractions":
            text = params.get("text", "")
            formality = params.get("formality", "neutral")
            return self.apply_contractions(text, formality)
        elif operation == "naturalize_pronouns":
            text = params.get("text", "")
            context = params.get("context", {})
            return self.naturalize_pronouns(text, context)
        elif operation == "add_human_touches":
            text = params.get("text", "")
            formality = params.get("formality", "neutral")
            return self.add_human_touches(text, formality)
        elif operation == "complete_naturalization":
            response = params.get("response", "")
            formality = params.get("formality", "neutral")
            context = params.get("context", {})
            previous_responses = params.get("previous_responses", [])
            return self.complete_naturalization(
                response, formality, context, previous_responses
            )
        elif operation == "add_uncertainty_markers":
            text = params.get("text", "")
            confidence = params.get("confidence", 0.7)
            return self.add_uncertainty_markers(text, confidence)
        elif operation == "adjust_formality":
            text = params.get("text", "")
            target_formality = params.get("target_formality", "neutral")
            current_formality = params.get("current_formality", "neutral")
            return self.adjust_formality(text, target_formality, current_formality)
        elif operation == "add_conversational_repair":
            text = params.get("text", "")
            return self.add_conversational_repair(text)
        else:
            raise InvalidParameterError(
                parameter="operation",
                value=operation,
                reason="Unknown operation for response_naturalizer",
            )

    def naturalize_response(
        self, response: str, formality: str = "neutral", context: Dict[str, Any] = None
    ) -> Dict[str, Any]:
        """Naturalize a response with all human-like touches"""
        if context is None:
            context = {}

        if not response:
            return {"naturalized_response": response, "changes_applied": []}

        naturalized = response
        changes = []

        # Apply contractions
        contraction_result = self.apply_contractions(naturalized, formality)
        if contraction_result.get("changes"):
            naturalized = contraction_result["contracted_text"]
            changes.extend(["contractions"])

        # Naturalize pronouns
        pronoun_result = self.naturalize_pronouns(naturalized, context)
        if pronoun_result.get("changes"):
            naturalized = pronoun_result["pronoun_text"]
            changes.extend(["pronouns"])

        # Add human touches
        human_result = self.add_human_touches(naturalized, formality)
        if human_result.get("touches_added"):
            naturalized = human_result["touched_text"]
            changes.extend(["human_touches"])

        # Add uncertainty markers if confidence is provided
        if context.get("confidence") is not None:
            uncertainty_result = self.add_uncertainty_markers(
                naturalized, context.get("confidence", 0.7)
            )
            if uncertainty_result.get("markers_added"):
                naturalized = uncertainty_result["text"]
                changes.extend(["uncertainty_markers"])

        # Add conversational repair occasionally
        if random.random() < 0.1:  # 10% chance
            repair_result = self.add_conversational_repair(naturalized)
            if repair_result.get("repairs_added"):
                naturalized = repair_result["text"]
                changes.extend(["conversational_repair"])

        return {
            "naturalized_response": naturalized,
            "changes_applied": changes,
            "original_length": len(response),
            "naturalized_length": len(naturalized),
        }

    def apply_contractions(
        self, text: str, formality: str = "neutral"
    ) -> Dict[str, Any]:
        """Apply contractions based on formality"""
        if not text:
            return {"contracted_text": text, "changes": []}

        # Get contraction rules for formality level
        rules = self.contraction_rules.get(
            formality, self.contraction_rules.get("neutral", {})
        )

        if not rules.get("enabled", True):
            return {"contracted_text": text, "changes": []}

        contracted = text
        changes = []
        probability = rules.get("probability", 0.6)

        # Common contractions
        contractions = {
            "I am": "I'm",
            "you are": "you're",
            "we are": "we're",
            "they are": "they're",
            "it is": "it's",
            "that is": "that's",
            "there is": "there's",
            "here is": "here's",
            "cannot": "can't",
            "do not": "don't",
            "does not": "doesn't",
            "did not": "didn't",
            "will not": "won't",
            "would not": "wouldn't",
            "should not": "shouldn't",
            "could not": "couldn't",
            "have not": "haven't",
            "has not": "hasn't",
            "had not": "hadn't",
            "I have": "I've",
            "you have": "you've",
            "we have": "we've",
            "they have": "they've",
            "I will": "I'll",
            "you will": "you'll",
            "we will": "we'll",
            "they will": "they'll",
            "I would": "I'd",
            "you would": "you'd",
            "we would": "we'd",
            "they would": "they'd",
        }

        for formal, contracted_form in contractions.items():
            if formal in contracted and random.random() < probability:
                # Replace (case-insensitive)
                pattern = re.compile(re.escape(formal), re.IGNORECASE)
                if pattern.search(contracted):
                    contracted = pattern.sub(contracted_form, contracted, count=1)
                    changes.append(f"{formal} -> {contracted_form}")

        return {
            "contracted_text": contracted,
            "changes": changes,
            "contractions_applied": len(changes),
        }

    def naturalize_pronouns(
        self, text: str, context: Dict[str, Any] = None
    ) -> Dict[str, Any]:
        """Naturalize pronoun usage"""
        if context is None:
            context = {}

        if not text:
            return {"pronoun_text": text, "changes": []}

        pronoun_text = text
        changes = []

        # Replace "I" with "we" occasionally in collaborative contexts
        if context.get("collaborative", False) and "I" in pronoun_text:
            if random.random() < 0.3:  # 30% chance
                # Replace first "I" with "we"
                pronoun_text = pronoun_text.replace("I ", "we ", 1)
                changes.append("I -> we")

        # Add "you" references naturally when talking about user
        if "the user" in pronoun_text.lower() or "user" in pronoun_text.lower():
            if random.random() < 0.5:
                pronoun_text = re.sub(
                    r"\bthe user\b", "you", pronoun_text, flags=re.IGNORECASE, count=1
                )
                pronoun_text = re.sub(
                    r"\buser\b", "you", pronoun_text, flags=re.IGNORECASE, count=1
                )
                changes.append("user references -> you")

        return {"pronoun_text": pronoun_text, "changes": changes}

    def add_human_touches(
        self, text: str, formality: str = "neutral"
    ) -> Dict[str, Any]:
        """Add human-like touches to text"""
        if not text:
            return {"touched_text": text, "touches_added": []}

        touched_text = text
        touches_added = []

        # Add natural openings occasionally
        if formality != "formal" and random.random() < 0.3:
            natural_openings = ["Well,", "So,", "Actually,", "You know,", "I mean,"]
            if not any(
                touched_text.startswith(opening) for opening in natural_openings
            ):
                opening = random.choice(natural_openings)
                touched_text = opening + " " + touched_text.lower()
                touched_text = touched_text[0].upper() + touched_text[1:]
                touches_added.append(f"Added opening: {opening}")

        # Fix overly formal language
        formal_replacements = {
            "utilize": "use",
            "facilitate": "help",
            "implement": "do",
            "indicate": "show",
            "demonstrate": "show",
            "approximately": "about",
            "subsequent": "next",
            "prior to": "before",
        }

        for formal_word, casual_word in formal_replacements.items():
            if formal_word in touched_text.lower() and formality != "formal":
                touched_text = re.sub(
                    r"\b" + re.escape(formal_word) + r"\b",
                    casual_word,
                    touched_text,
                    flags=re.IGNORECASE,
                    count=1,
                )
                touches_added.append(f"{formal_word} -> {casual_word}")

        return {"touched_text": touched_text, "touches_added": touches_added}

    def complete_naturalization(
        self,
        response: str,
        formality: str = "neutral",
        context: Dict[str, Any] = None,
        previous_responses: List[str] = None,
    ) -> Dict[str, Any]:
        """Complete naturalization pipeline"""
        if context is None:
            context = {}
        if previous_responses is None:
            previous_responses = []

        if not response:
            return {"naturalized": response, "changes": []}

        # Apply all naturalization steps
        naturalized = response
        all_changes = []

        # 1. Apply contractions
        contraction_result = self.apply_contractions(naturalized, formality)
        naturalized = contraction_result.get("contracted_text", naturalized)
        all_changes.extend(contraction_result.get("changes", []))

        # 2. Naturalize pronouns
        pronoun_result = self.naturalize_pronouns(naturalized, context)
        naturalized = pronoun_result.get("pronoun_text", naturalized)
        all_changes.extend(pronoun_result.get("changes", []))

        # 3. Add human touches
        human_result = self.add_human_touches(naturalized, formality)
        naturalized = human_result.get("touched_text", naturalized)
        all_changes.extend(human_result.get("touches_added", []))

        # 4. Avoid repetition with previous responses
        if previous_responses:
            # Simple check - in full implementation would use language_variety module
            for prev_response in previous_responses[-2:]:
                # Check for exact phrase repetition
                prev_words = set(prev_response.lower().split())
                curr_words = set(naturalized.lower().split())
                if len(curr_words & prev_words) > 5:
                    # Some repetition detected - could add variation
                    pass

        return {
            "naturalized": naturalized,
            "changes": all_changes,
            "naturalization_score": min(
                1.0, len(all_changes) / 5.0
            ),  # Score based on changes
        }

    def validate_params(self, operation: str, params: Dict[str, Any]) -> bool:
        """Validate parameters for operations"""
        if operation == "naturalize_response" or operation == "complete_naturalization":
            return "response" in params
        elif operation == "apply_contractions":
            return "text" in params
        elif operation == "naturalize_pronouns":
            return "text" in params
        elif operation == "add_human_touches":
            return "text" in params
        return True
