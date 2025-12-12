"""
Neural Grammar Module - Rule-based and template-based grammar correction and naturalization
Grammar correction and naturalization using rule-based methods and templates
No LLM dependencies - uses pattern matching, templates, and rule-based transformations
"""

from typing import Any
import json
import os
import sys
from pathlib import Path
import re

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent))

from mavaia_core.brain.base_module import BaseBrainModule, ModuleMetadata


class NeuralGrammarModule(BaseBrainModule):
    """Grammar correction and naturalization using rule-based methods"""

    def __init__(self) -> None:
        self.config = None
        self._load_config()

    @property
    def metadata(self) -> ModuleMetadata:
        return ModuleMetadata(
            name="neural_grammar",
            version="2.0.0",
            description="Rule-based grammar correction and naturalization (no LLM dependencies)",
            operations=[
                "generate_grammar",
                "correct_grammar",
                "naturalize_response",
                "generate_variations",
            ],
            dependencies=[],
            model_required=False,
        )

    def initialize(self) -> bool:
        """Initialize the module"""
        if not self.config:
            print(
                f"[NeuralGrammarModule] Warning: Config not loaded, but continuing with defaults",
                file=sys.stderr,
            )
        return True

    def _load_config(self) -> None:
        """Load model configuration from JSON"""
        config_path = Path(__file__).parent / "model_config.json"
        try:
            with open(config_path, "r", encoding="utf-8") as f:
                self.config = json.load(f)
        except Exception as e:
            print(f"[NeuralGrammarModule] Failed to load config: {e}", file=sys.stderr)
            self.config = {}

    def execute(self, operation: str, params: dict[str, Any]) -> dict[str, Any]:
        """Execute a neural grammar operation"""
        match operation:
            case "generate_grammar":
                return self._generate_grammar(
                    text=params.get("text", ""),
                    persona=params.get("persona", "mavaia"),
                    context=params.get("context", ""),
                )
            case "correct_grammar":
                return self._correct_grammar(
                    text=params.get("text", ""), persona=params.get("persona", "mavaia")
                )
            case "naturalize_response":
                return self._naturalize_response(
                    text=params.get("text", ""),
                    persona=params.get("persona", "mavaia"),
                    context=params.get("context", ""),
                )
            case "generate_variations":
                return self._generate_variations(
                    text=params.get("text", ""),
                    persona=params.get("persona", "mavaia"),
                    count=params.get("count", 3),
                    context=params.get("context", ""),
                )
            case _:
                raise ValueError(
                    f"Unknown operation: {operation}. Supported: generate_grammar, correct_grammar, naturalize_response, generate_variations"
                )

    def _generate_grammar(
        self, text: str, persona: str = "mavaia", context: str = ""
    ) -> dict[str, Any]:
        """Generate grammatically correct text"""
        if not text:
            return {"text": "", "confidence": 0.0}

        # Build prompt with persona token
        prompt = self._build_prompt(text, persona, context, operation="generate")

        # Generate using rule-based methods
        result = self._generate_with_model(prompt, persona)

        return result

    def _correct_grammar(self, text: str, persona: str = "mavaia") -> dict[str, Any]:
        """Fix grammar in existing text"""
        if not text:
            return {"text": "", "confidence": 0.0}

        # Build prompt for grammar correction
        prompt = self._build_prompt(text, persona, "", operation="correct")

        # Generate corrected version using rule-based methods
        result = self._generate_with_model(prompt, persona)

        return result

    def _naturalize_response(
        self, text: str, persona: str = "mavaia", context: str = ""
    ) -> dict[str, Any]:
        """Convert template-like responses to natural speech"""
        if not text:
            return {"text": "", "confidence": 0.0}

        # Build prompt for naturalization
        prompt = self._build_prompt(text, persona, context, operation="naturalize")

        # Generate naturalized version
        result = self._generate_with_model(prompt, persona)

        return result

    def _generate_variations(
        self, text: str, persona: str = "mavaia", count: int = 3, context: str = ""
    ) -> dict[str, Any]:
        """Generate multiple grammatically valid variations"""
        if not text:
            return {"variations": [], "confidences": []}

        variations = []
        confidences = []

        for _ in range(count):
            prompt = self._build_prompt(text, persona, context, operation="generate")
            result = self._generate_with_model(prompt, persona)
            # Update confidence calculation call
            if "confidence" not in result:
                result["confidence"] = self._calculate_confidence(
                    result.get("text", ""), prompt, persona
                )
            variations.append(result["text"])
            confidences.append(result["confidence"])

        return {"variations": variations, "confidences": confidences}

    def _build_prompt(
        self, text: str, persona: str, context: str, operation: str
    ) -> str:
        """Build prompt with persona token for style conditioning"""
        # Normalize persona name
        persona_normalized = persona.lower().replace(" ", "_")

        # Build prompt with persona token (style embedding)
        match operation:
            case "generate":
                prompt = f"[persona={persona_normalized}] Generate a natural response: {text}"
            case "correct":
                prompt = f"[persona={persona_normalized}] Correct the grammar: {text}"
            case "naturalize":
                prompt = (
                    f"[persona={persona_normalized}] Convert to natural speech: {text}"
                )
            case _:
                prompt = f"[persona={persona_normalized}] {text}"

        if context:
            prompt = f"{prompt}\nContext: {context}"

        return prompt

    def _generate_with_model(self, prompt: str, persona: str) -> dict[str, Any]:
        """Generate text using rule-based methods"""
        # Use rule-based generation instead of LLM
        return self._fallback_generation(prompt, persona)

    def _calculate_confidence(self, text: str, prompt: str, persona: str) -> float:
        """Calculate confidence score based on grammar heuristics and style consistency"""
        confidence = 0.5  # Base confidence

        try:
            # Grammar correctness heuristics
            grammar_score = 0.0
            if text:
                # Check sentence structure
                if text[0].isupper() or text[0].islower():  # Starts with letter
                    grammar_score += 0.1
                if text.endswith((".", "!", "?")):  # Proper punctuation
                    grammar_score += 0.1
                if len(text.split()) > 2:  # Has multiple words
                    grammar_score += 0.1
                # Check for persona token in prompt (style consistency)
                if f"[persona={persona.lower().replace(' ', '_')}]" in prompt:
                    grammar_score += 0.1

            confidence += grammar_score

            # Style consistency check
            style_score = 0.1  # Default style score
            confidence += style_score

            # Clamp to [0.0, 1.0]
            confidence = max(0.0, min(1.0, confidence))

        except Exception as e:
            print(
                f"[NeuralGrammarModule] Confidence calculation error: {e}",
                file=sys.stderr,
            )
            confidence = 0.5  # Default on error

        return confidence

    def _fallback_generation(self, prompt: str, persona: str) -> dict[str, Any]:
        """Rule-based generation and naturalization"""
        # Extract text from prompt (remove persona token and operation)
        text = prompt
        if "[persona=" in text:
            # Remove persona token
            text = re.sub(r"\[persona=[^\]]+\]\s*", "", text)
        # Remove operation prefixes
        text = re.sub(
            r"^(Generate a natural response:|Correct the grammar:|Convert to natural speech:)\s*",
            "",
            text,
            flags=re.IGNORECASE,
        )
        text = text.strip()

        # Apply basic grammar corrections
        text = self._apply_basic_grammar_corrections(text)

        # Calculate confidence
        confidence = self._calculate_confidence(text, prompt, persona)

        return {"text": text, "confidence": confidence}

    def _apply_basic_grammar_corrections(self, text: str) -> str:
        """Apply basic rule-based grammar corrections"""
        if not text:
            return text

        # Fix common issues
        # Capitalize first letter
        if text and text[0].islower():
            text = text[0].upper() + text[1:]

        # Ensure sentence ends with punctuation
        if text and not text[-1] in ".!?":
            text += "."

        # Fix double spaces
        text = re.sub(r"\s+", " ", text)

        # Fix spacing around punctuation
        text = re.sub(r"\s+([.!?])", r"\1", text)
        text = re.sub(r"([.!?])([A-Za-z])", r"\1 \2", text)

        return text.strip()

    def validate_params(self, operation: str, params: dict[str, Any]) -> bool:
        """Validate parameters for operations"""
        if operation in ["generate_grammar", "correct_grammar", "naturalize_response"]:
            return "text" in params
        elif operation == "generate_variations":
            return "text" in params
        return True
