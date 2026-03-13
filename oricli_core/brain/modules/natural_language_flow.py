from __future__ import annotations
"""
Natural Language Flow Module - Natural sentence variation, flow, and structure
Handles sentence length variation, natural structure patterns, flow transitions, and rhythm
"""

from typing import Dict, Any, List, Optional
import json
import re
import random
from pathlib import Path
import logging

from oricli_core.brain.base_module import BaseBrainModule, ModuleMetadata
from oricli_core.exceptions import InvalidParameterError

logger = logging.getLogger(__name__)


class NaturalLanguageFlowModule(BaseBrainModule):
    """Natural language flow for human-like sentence variation and structure"""

    def __init__(self):
        super().__init__()
        self.config = None
        self.sentence_patterns = {}
        self.flow_transitions = {}
        self._load_config()

    @property
    def metadata(self) -> ModuleMetadata:
        return ModuleMetadata(
            name="natural_language_flow",
            version="1.0.0",
            description="Natural language flow: sentence variation, structure, flow transitions, rhythm",
            operations=[
                "vary_sentence_structure",
                "add_flow_transitions",
                "naturalize_rhythm",
                "mix_sentence_lengths",
                "create_natural_flow",
            ],
            dependencies=[],
            model_required=False,
        )

    def initialize(self) -> bool:
        """Initialize the module"""
        return True

    def _load_config(self):
        """Load natural language flow configuration"""
        config_path = Path(__file__).parent / "natural_language_flow_config.json"
        try:
            if config_path.exists():
                with open(config_path, "r", encoding="utf-8") as f:
                    self.config = json.load(f)
                    self.sentence_patterns = self.config.get("sentence_patterns", {})
                    self.flow_transitions = self.config.get("flow_transitions", {})
            else:
                # Default config
                self.sentence_patterns = {
                    "simple": [
                        "{subject} {verb} {object}.",
                        "{subject} is {predicate}.",
                    ],
                    "compound": [
                        "{clause1}, and {clause2}.",
                        "{clause1}, but {clause2}.",
                    ],
                    "complex": [
                        "{clause1}, {subordinator} {clause2}.",
                        "When {clause}, {result}.",
                    ],
                }
                self.flow_transitions = {
                    "continuation": ["and", "also", "plus", "additionally"],
                    "contrast": ["but", "however", "though", "although"],
                    "cause": ["because", "since", "as", "due to"],
                    "result": ["so", "therefore", "thus", "as a result"],
                }
        except Exception as e:
            logger.warning(
                "Failed to load natural_language_flow config; using empty defaults",
                exc_info=True,
                extra={"module_name": "natural_language_flow", "error_type": type(e).__name__},
            )
            self.sentence_patterns = {}
            self.flow_transitions = {}

    def execute(self, operation: str, params: Dict[str, Any]) -> Dict[str, Any]:
        """Execute a natural language flow operation"""
        if operation == "vary_sentence_structure":
            text = params.get("text", "")
            if text is None:
                text = ""
            if not isinstance(text, str):
                raise InvalidParameterError(
                    parameter="text",
                    value=str(type(text).__name__),
                    reason="text must be a string",
                )
            return self.vary_sentence_structure(text)
        elif operation == "add_flow_transitions":
            text = params.get("text", "")
            context = params.get("context", "")
            if text is None:
                text = ""
            if context is None:
                context = ""
            if not isinstance(text, str):
                raise InvalidParameterError(
                    parameter="text",
                    value=str(type(text).__name__),
                    reason="text must be a string",
                )
            if not isinstance(context, str):
                raise InvalidParameterError(
                    parameter="context",
                    value=str(type(context).__name__),
                    reason="context must be a string",
                )
            return self.add_flow_transitions(text, context)
        elif operation == "naturalize_rhythm":
            text = params.get("text", "")
            if text is None:
                text = ""
            if not isinstance(text, str):
                raise InvalidParameterError(
                    parameter="text",
                    value=str(type(text).__name__),
                    reason="text must be a string",
                )
            return self.naturalize_rhythm(text)
        elif operation == "mix_sentence_lengths":
            sentences = params.get("sentences", [])
            if sentences is None:
                sentences = []
            if not isinstance(sentences, list):
                raise InvalidParameterError(
                    parameter="sentences",
                    value=str(type(sentences).__name__),
                    reason="sentences must be a list",
                )
            return self.mix_sentence_lengths(sentences)
        elif operation == "create_natural_flow":
            text = params.get("text", "")
            previous_text = params.get("previous_text", "")
            if text is None:
                text = ""
            if previous_text is None:
                previous_text = ""
            if not isinstance(text, str):
                raise InvalidParameterError(
                    parameter="text",
                    value=str(type(text).__name__),
                    reason="text must be a string",
                )
            if not isinstance(previous_text, str):
                raise InvalidParameterError(
                    parameter="previous_text",
                    value=str(type(previous_text).__name__),
                    reason="previous_text must be a string",
                )
            return self.create_natural_flow(text, previous_text)
        else:
            raise InvalidParameterError(
                parameter="operation",
                value=operation,
                reason="Unknown operation for natural_language_flow",
            )

    def vary_sentence_structure(self, text: str) -> Dict[str, Any]:
        """Vary sentence structure for natural flow"""
        if not text:
            return {"varied_text": text, "changes": []}

        sentences = re.split(r"[.!?]+", text)
        sentences = [s.strip() for s in sentences if s.strip()]

        if not sentences:
            return {"varied_text": text, "changes": []}

        varied_sentences = []
        changes = []

        for i, sentence in enumerate(sentences):
            original = sentence

            # Vary structure based on position and length
            if len(sentence.split()) > 15 and i % 3 == 0:
                # Break long sentences occasionally
                parts = sentence.split(",")
                if len(parts) > 1:
                    # Split into two sentences
                    first = parts[0].strip()
                    rest = ", ".join(parts[1:]).strip()
                    varied_sentences.append(first + ".")
                    varied_sentences.append(rest.capitalize() + ".")
                    changes.append(f"Split long sentence at position {i}")
                    continue

            # Add variety with different openings
            if i > 0 and sentence.lower().startswith(("the ", "it ", "this ")):
                # Sometimes start with different words
                if random.random() < 0.3:
                    words = sentence.split()
                    if len(words) > 2:
                        # Rearrange to start with different element
                        varied = (
                            words[1].capitalize()
                            + " "
                            + words[0].lower()
                            + " "
                            + " ".join(words[2:])
                        )
                        sentence = varied
                        changes.append(f"Varied opening at position {i}")

            varied_sentences.append(sentence)

        varied_text = ". ".join(varied_sentences)
        if varied_text and not varied_text.endswith((".", "!", "?")):
            varied_text += "."

        return {
            "varied_text": varied_text,
            "changes": changes,
            "sentence_count": len(varied_sentences),
        }

    def add_flow_transitions(self, text: str, context: str = "") -> Dict[str, Any]:
        """Add natural flow transitions between sentences"""
        if not text:
            return {"text_with_transitions": text, "transitions_added": []}

        sentences = re.split(r"[.!?]+", text)
        sentences = [s.strip() for s in sentences if s.strip()]

        if len(sentences) <= 1:
            return {"text_with_transitions": text, "transitions_added": []}

        transitions_added = []
        result_sentences = [sentences[0]]

        for i in range(1, len(sentences)):
            prev_sentence = sentences[i - 1].lower()
            curr_sentence = sentences[i]

            # Determine if transition needed
            needs_transition = True

            # Check if already has a transition word
            transition_words = [
                "and",
                "but",
                "however",
                "also",
                "so",
                "because",
                "since",
                "therefore",
            ]
            if any(
                curr_sentence.lower().startswith(word + " ")
                for word in transition_words
            ):
                needs_transition = False

            # Add appropriate transition
            if needs_transition and random.random() < 0.4:  # 40% chance
                # Choose transition type based on relationship
                if "but" in prev_sentence or "however" in prev_sentence:
                    transition = random.choice(
                        self.flow_transitions.get(
                            "contrast", ["However,", "But", "Though"]
                        )
                    )
                elif any(
                    word in prev_sentence for word in ["because", "since", "due to"]
                ):
                    transition = random.choice(
                        self.flow_transitions.get(
                            "result", ["So", "Therefore,", "As a result,"]
                        )
                    )
                else:
                    transition = random.choice(
                        self.flow_transitions.get(
                            "continuation", ["Also,", "Plus,", "Additionally,"]
                        )
                    )

                # Add transition
                curr_sentence = transition + " " + curr_sentence.lower()
                transitions_added.append(f"Added '{transition}' at position {i}")

            result_sentences.append(curr_sentence)

        text_with_transitions = ". ".join(result_sentences)
        if text_with_transitions and not text_with_transitions.endswith(
            (".", "!", "?")
        ):
            text_with_transitions += "."

        return {
            "text_with_transitions": text_with_transitions,
            "transitions_added": transitions_added,
        }

    def naturalize_rhythm(self, text: str) -> Dict[str, Any]:
        """Naturalize rhythm by mixing sentence lengths and structures"""
        if not text:
            return {"naturalized_text": text, "changes": []}

        sentences = re.split(r"[.!?]+", text)
        sentences = [s.strip() for s in sentences if s.strip()]

        if len(sentences) <= 1:
            return {"naturalized_text": text, "changes": []}

        naturalized = []
        changes = []

        # Analyze sentence lengths
        lengths = [len(s.split()) for s in sentences]
        avg_length = sum(lengths) / len(lengths) if lengths else 0

        for i, sentence in enumerate(sentences):
            word_count = len(sentence.split())

            # Vary rhythm
            if word_count > avg_length * 1.5 and i % 2 == 0:
                # Occasionally shorten very long sentences
                if "," in sentence:
                    # Break at comma
                    parts = sentence.split(",", 1)
                    naturalized.append(parts[0].strip() + ".")
                    naturalized.append(parts[1].strip().capitalize() + ".")
                    changes.append(f"Shortened sentence at position {i}")
                    continue
            elif word_count < 5 and i > 0:
                # Very short sentence - might combine with previous if appropriate
                if random.random() < 0.2:  # 20% chance
                    prev = naturalized[-1] if naturalized else ""
                    if prev and not prev.endswith((".", "!", "?")):
                        naturalized[-1] = prev + ", " + sentence.lower()
                        changes.append(f"Combined short sentence at position {i}")
                        continue

            naturalized.append(sentence)

        naturalized_text = ". ".join(naturalized)
        if naturalized_text and not naturalized_text.endswith((".", "!", "?")):
            naturalized_text += "."

        return {
            "naturalized_text": naturalized_text,
            "changes": changes,
            "original_sentence_count": len(sentences),
            "naturalized_sentence_count": len(naturalized),
        }

    def mix_sentence_lengths(self, sentences: List[str]) -> Dict[str, Any]:
        """Mix sentence lengths for natural variation"""
        if not sentences:
            return {"mixed_sentences": [], "variation_score": 0.0}

        # Analyze current lengths
        lengths = [len(s.split()) for s in sentences]

        if not lengths:
            return {"mixed_sentences": sentences, "variation_score": 0.0}

        min_length = min(lengths)
        max_length = max(lengths)
        avg_length = sum(lengths) / len(lengths)

        # Calculate variation (coefficient of variation)
        if avg_length > 0:
            variance = sum((l - avg_length) ** 2 for l in lengths) / len(lengths)
            std_dev = variance**0.5
            variation_score = std_dev / avg_length if avg_length > 0 else 0.0
        else:
            variation_score = 0.0

        # If variation is low, suggest mixing
        mixed = sentences.copy()
        changes = []

        if variation_score < 0.3:  # Low variation
            # Introduce more variation
            for i in range(len(mixed)):
                if i % 3 == 0 and len(mixed[i].split()) > 10:
                    # Occasionally break long sentences
                    if "," in mixed[i]:
                        parts = mixed[i].split(",", 1)
                        mixed[i] = parts[0].strip() + "."
                        mixed.insert(i + 1, parts[1].strip().capitalize() + ".")
                        changes.append(f"Broke sentence at index {i}")

        return {
            "mixed_sentences": mixed,
            "variation_score": variation_score,
            "changes": changes,
            "length_range": {"min": min_length, "max": max_length, "avg": avg_length},
        }

    def create_natural_flow(self, text: str, previous_text: str = "") -> Dict[str, Any]:
        """Create natural flow from previous text to current text"""
        if not text:
            return {"flowing_text": text, "transition_added": False}

        flowing_text = text

        # If there's previous text, add transition if needed
        if previous_text:
            prev_lower = previous_text.lower().strip()
            text_lower = text.lower().strip()

            # Check if transition needed
            needs_transition = True

            # Check if text already starts with transition
            transition_starters = [
                "and",
                "but",
                "so",
                "however",
                "also",
                "plus",
                "well",
                "actually",
            ]
            if any(text_lower.startswith(word + " ") for word in transition_starters):
                needs_transition = False

            # Check if previous text ended with question (might need different transition)
            if prev_lower.endswith("?"):
                # Responding to question - use acknowledgment
                if needs_transition and random.random() < 0.5:
                    acknowledgments = ["Well,", "So,", "Right,", "I see,", "Okay,"]
                    flowing_text = random.choice(acknowledgments) + " " + text.lower()
                    return {
                        "flowing_text": flowing_text,
                        "transition_added": True,
                        "transition_type": "acknowledgment",
                    }

            # Add continuation transition
            if needs_transition and random.random() < 0.3:
                continuations = ["And", "Also,", "Plus,", "Well,", "So,"]
                flowing_text = random.choice(continuations) + " " + text.lower()
                return {
                    "flowing_text": flowing_text,
                    "transition_added": True,
                    "transition_type": "continuation",
                }

        return {"flowing_text": flowing_text, "transition_added": False}

    def validate_params(self, operation: str, params: Dict[str, Any]) -> bool:
        """Validate parameters for operations"""
        if operation == "vary_sentence_structure":
            return "text" in params
        elif operation == "add_flow_transitions":
            return "text" in params
        elif operation == "naturalize_rhythm":
            return "text" in params
        elif operation == "mix_sentence_lengths":
            return "sentences" in params
        elif operation == "create_natural_flow":
            return "text" in params
        return True
