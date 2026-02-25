from __future__ import annotations
"""
Language Variety Module - Natural language variation
Handles avoiding repetition, natural synonym usage, varied expression patterns, and natural fillers
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


class LanguageVarietyModule(BaseBrainModule):
    """Natural language variety to avoid repetition"""

    def __init__(self):
        super().__init__()
        self.config = None
        self.synonyms = {}
        self.variation_patterns = {}
        self.discourse_fillers = {}
        self.recent_words = []
        self._load_config()

    @property
    def metadata(self) -> ModuleMetadata:
        return ModuleMetadata(
            name="language_variety",
            version="1.0.0",
            description="Language variety: avoid repetition, synonym usage, varied expressions, natural fillers",
            operations=[
                "avoid_repetition",
                "use_synonyms",
                "add_variety",
                "insert_discourse_fillers",
                "vary_expressions",
            ],
            dependencies=[],
            model_required=False,
        )

    def initialize(self) -> bool:
        """Initialize the module"""
        return True

    def _load_config(self):
        """Load language variety configuration"""
        config_path = Path(__file__).parent / "language_variety_config.json"
        try:
            if config_path.exists():
                with open(config_path, "r", encoding="utf-8") as f:
                    self.config = json.load(f)
                    self.synonyms = self.config.get("synonyms", {})
                    self.variation_patterns = self.config.get("variation_patterns", {})
                    self.discourse_fillers = self.config.get("discourse_fillers", {})
            else:
                # Default config
                self.synonyms = {
                    "good": [
                        "great",
                        "nice",
                        "excellent",
                        "wonderful",
                        "awesome",
                        "fantastic",
                    ],
                    "bad": ["not great", "tough", "difficult", "challenging", "rough"],
                    "think": ["believe", "feel", "suppose", "guess", "imagine"],
                    "know": ["understand", "see", "get", "realize", "recognize"],
                    "help": ["assist", "support", "aid", "guide"],
                    "say": ["mention", "tell", "explain", "describe", "share"],
                }
                self.discourse_fillers = {
                    "natural": [
                        "well",
                        "you know",
                        "I mean",
                        "like",
                        "sort of",
                        "kind of",
                    ],
                    "formal": ["essentially", "basically", "essentially", "in essence"],
                    "casual": ["ya know", "I guess", "I suppose", "pretty much"],
                }
        except Exception as e:
            logger.warning(
                "Failed to load language_variety config; using empty defaults",
                exc_info=True,
                extra={"module_name": "language_variety", "error_type": type(e).__name__},
            )
            self.synonyms = {}
            self.variation_patterns = {}
            self.discourse_fillers = {}

    def execute(self, operation: str, params: Dict[str, Any]) -> Dict[str, Any]:
        """Execute a language variety operation"""
        if operation == "avoid_repetition":
            text = params.get("text", "")
            previous_texts = params.get("previous_texts", [])
            if text is None:
                text = ""
            if previous_texts is None:
                previous_texts = []
            if not isinstance(text, str):
                raise InvalidParameterError("text", str(type(text).__name__), "text must be a string")
            if not isinstance(previous_texts, list):
                raise InvalidParameterError(
                    "previous_texts", str(type(previous_texts).__name__), "previous_texts must be a list"
                )
            return self.avoid_repetition(text, previous_texts)
        elif operation == "use_synonyms":
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
            return self.use_synonyms(text, formality)
        elif operation == "add_variety":
            text = params.get("text", "")
            if text is None:
                text = ""
            if not isinstance(text, str):
                raise InvalidParameterError("text", str(type(text).__name__), "text must be a string")
            return self.add_variety(text)
        elif operation == "insert_discourse_fillers":
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
            return self.insert_discourse_fillers(text, formality)
        elif operation == "vary_expressions":
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
            return self.vary_expressions(text, context)
        else:
            raise InvalidParameterError(
                parameter="operation",
                value=operation,
                reason="Unknown operation for language_variety",
            )

    def avoid_repetition(
        self, text: str, previous_texts: List[str] = None
    ) -> Dict[str, Any]:
        """Avoid repeating words/phrases from recent conversation"""
        if previous_texts is None:
            previous_texts = []

        if not text:
            return {"varied_text": text, "changes": []}

        # Get words from previous texts
        previous_words = set()
        for prev_text in previous_texts[-3:]:  # Last 3 turns
            if prev_text:
                previous_words.update(prev_text.lower().split())

        # Find repeated words in current text
        current_words = text.lower().split()
        repeated_words = []

        for word in current_words:
            clean_word = re.sub(r"[^\w]", "", word)
            if (
                clean_word in previous_words and len(clean_word) > 3
            ):  # Only significant words
                repeated_words.append(clean_word)

        # Replace repeated words with synonyms
        varied_text = text
        changes = []

        for repeated_word in set(repeated_words):
            if repeated_word in self.synonyms:
                synonyms = self.synonyms[repeated_word]
                replacement = random.choice(synonyms)
                # Replace word (case-insensitive)
                pattern = re.compile(
                    r"\b" + re.escape(repeated_word) + r"\b", re.IGNORECASE
                )
                varied_text = pattern.sub(
                    replacement, varied_text, count=1
                )  # Replace first occurrence
                changes.append(f"Replaced '{repeated_word}' with '{replacement}'")

        return {
            "varied_text": varied_text,
            "changes": changes,
            "repeated_words_found": len(set(repeated_words)),
        }

    def use_synonyms(self, text: str, formality: str = "neutral") -> Dict[str, Any]:
        """Use synonyms to add variety"""
        if not text:
            return {"synonym_text": text, "replacements": []}

        synonym_text = text
        replacements = []

        # Replace common words with synonyms occasionally
        for word, synonyms_list in self.synonyms.items():
            if word in text.lower():
                # Only replace occasionally (30% chance)
                if random.random() < 0.3:
                    synonym = random.choice(synonyms_list)
                    pattern = re.compile(r"\b" + re.escape(word) + r"\b", re.IGNORECASE)
                    synonym_text = pattern.sub(synonym, synonym_text, count=1)
                    replacements.append({"original": word, "replacement": synonym})

        return {"synonym_text": synonym_text, "replacements": replacements}

    def add_variety(self, text: str) -> Dict[str, Any]:
        """Add variety to expression patterns"""
        if not text:
            return {"varied_text": text, "changes": []}

        varied_text = text
        changes = []

        # Vary common patterns
        patterns = {
            r"\bI think\b": ["I believe", "I feel", "I suppose", "It seems to me"],
            r"\bthat is\b": ["that's", "which is", "i.e."],
            r"\bfor example\b": ["for instance", "like", "such as"],
            r"\bin addition\b": ["also", "plus", "furthermore", "moreover"],
            r"\bhowever\b": ["but", "though", "although", "on the other hand"],
        }

        for pattern, replacements in patterns.items():
            if re.search(pattern, varied_text, re.IGNORECASE):
                replacement = random.choice(replacements)
                varied_text = re.sub(
                    pattern, replacement, varied_text, flags=re.IGNORECASE, count=1
                )
                changes.append(f"Varied expression pattern")

        return {"varied_text": varied_text, "changes": changes}

    def insert_discourse_fillers(
        self, text: str, formality: str = "neutral"
    ) -> Dict[str, Any]:
        """Insert natural discourse fillers"""
        if not text:
            return {"text_with_fillers": text, "fillers_added": []}

        # Choose fillers based on formality
        filler_list = self.discourse_fillers.get(
            formality, self.discourse_fillers.get("natural", [])
        )

        if not filler_list:
            return {"text_with_fillers": text, "fillers_added": []}

        sentences = re.split(r"[.!?]+", text)
        sentences = [s.strip() for s in sentences if s.strip()]

        if not sentences:
            return {"text_with_fillers": text, "fillers_added": []}

        text_with_fillers = ""
        fillers_added = []

        for i, sentence in enumerate(sentences):
            # Occasionally add filler at start (20% chance, not first sentence)
            if i > 0 and random.random() < 0.2:
                filler = random.choice(filler_list)
                sentence = filler.capitalize() + ", " + sentence.lower()
                fillers_added.append(f"Added '{filler}' to sentence {i+1}")

            text_with_fillers += sentence + ". "

        text_with_fillers = text_with_fillers.strip()

        return {"text_with_fillers": text_with_fillers, "fillers_added": fillers_added}

    def vary_expressions(self, text: str, context: str = "") -> Dict[str, Any]:
        """Vary expressions to avoid monotony"""
        if not text:
            return {"varied_text": text, "variations_applied": []}

        varied_text = text
        variations_applied = []

        # Combine multiple variety techniques
        # 1. Use synonyms
        synonym_result = self.use_synonyms(varied_text)
        if synonym_result.get("replacements"):
            varied_text = synonym_result["synonym_text"]
            variations_applied.extend(["synonym_replacement"])

        # 2. Add expression variety
        variety_result = self.add_variety(varied_text)
        if variety_result.get("changes"):
            varied_text = variety_result["varied_text"]
            variations_applied.extend(["expression_variety"])

        return {"varied_text": varied_text, "variations_applied": variations_applied}

    def validate_params(self, operation: str, params: Dict[str, Any]) -> bool:
        """Validate parameters for operations"""
        if operation == "use_synonyms":
            return "text" in params
        elif operation == "add_variety":
            return "text" in params
        elif operation == "insert_discourse_fillers":
            return "text" in params
        elif operation == "vary_expressions":
            return "text" in params
        return True
