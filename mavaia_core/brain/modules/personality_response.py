"""
Personality Response Module - Generate personality-specific responses using example-based selection
Plug-and-play module that generates responses in each Mavaia personality's voice
No LLM dependencies - uses example-based selection and template generation

DEPRECATED: This module is deprecated. Use universal_voice_engine and text_generation_engine instead.
The personality-based system has been replaced with a universal voice that adapts contextually.
"""

from typing import Any
import json
import os
from pathlib import Path
import random

import logging

from mavaia_core.brain.base_module import BaseBrainModule, ModuleMetadata
from mavaia_core.exceptions import InvalidParameterError

logger = logging.getLogger(__name__)


class PersonalityResponseModule(BaseBrainModule):
    """Generate personality-specific responses using example-based selection and templates"""

    def __init__(self) -> None:
        super().__init__()
        self.config = None
        self._load_config()

    @property
    def metadata(self) -> ModuleMetadata:
        import warnings
        warnings.warn(
            "personality_response module is deprecated. Use universal_voice_engine and text_generation_engine instead.",
            DeprecationWarning,
            stacklevel=2
        )
        return ModuleMetadata(
            name="personality_response",
            version="2.0.0",
            description="[DEPRECATED] Generate personality-specific responses using example-based selection (no LLM dependencies). Use universal_voice_engine instead.",
            operations=["generate", "generate_variations"],
            dependencies=[],
            model_required=False,
        )

    def initialize(self) -> bool:
        """Initialize the module"""
        if not self.config:
            logger.warning(
                "PersonalityResponse config not loaded; continuing with defaults",
                extra={"module_name": "personality_response"},
            )
        return True

    def _load_config(self) -> None:
        """Load personality configuration from JSON"""
        config_path = Path(__file__).parent / "personality_config.json"
        try:
            with open(config_path, "r", encoding="utf-8") as f:
                self.config = json.load(f)
        except Exception as e:
            logger.warning(
                "Failed to load personality_response config; using empty defaults",
                exc_info=True,
                extra={"module_name": "personality_response", "error_type": type(e).__name__},
            )
            self.config = {}

    def execute(self, operation: str, params: dict[str, Any]) -> dict[str, Any]:
        """Execute a personality response operation"""
        # Auto-load config if not loaded
        if not self.config:
            self._load_config()

        match operation:
            case "generate":
                return self._generate_response(
                    intent=params.get("intent", ""),
                    personality=params.get("personality", ""),
                    context=params.get("context", ""),
                    emotional_tone=params.get("emotional_tone"),
                    user_message=params.get("user_message", ""),
                    num_variations=params.get("num_variations", 3),
                    adapted_personality_config=params.get("adapted_personality_config"),
                )
            case "generate_variations":
                return self._generate_variations(
                    intent=params.get("intent", ""),
                    personality=params.get("personality", ""),
                    count=params.get("count", 3),
                    context=params.get("context", ""),
                    emotional_tone=params.get("emotional_tone"),
                )
            case _:
                raise InvalidParameterError(
                    parameter="operation",
                    value=operation,
                    reason="Unknown operation for personality_response",
                )

    def _generate_response(
        self,
        intent: str,
        personality: str,
        context: str = "",
        emotional_tone: str | None = None,
        user_message: str = "",
        num_variations: int = 3,
        adapted_personality_config: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        """Generate personality-specific response(s)"""
        if not self.config:
            return {"error": "Personality configuration not loaded", "responses": []}

        # Use adapted config if provided, otherwise load from config
        if adapted_personality_config:
            personality_config = adapted_personality_config
        else:
            # Normalize personality name (handle both snake_case and display names)
            personality_key = self._normalize_personality_name(personality)

            if personality_key not in self.config.get("personalities", {}):
                return {
                    "error": f"Personality '{personality}' not found in config",
                    "responses": [],
                }

            # Get personality config
            personality_config = self.config["personalities"][personality_key]

        # Determine intent category for better example selection
        intent_category = self._categorize_intent(intent)

        # Get examples for this personality + intent category
        examples = personality_config.get("example_responses", {}).get(
            intent_category, []
        )

        # If no examples for this category, try to use a general response or fallback
        if not examples:
            # Try to find similar category examples
            examples = self._find_similar_examples(personality_config, intent_category)

        # Generate responses using example-based selection and templates
        responses = []

        # First, try example-based selection with contextual variations
        if examples:
            # Generate contextual variations from examples
            base_responses = (
                random.sample(examples, min(num_variations, len(examples)))
                if len(examples) >= num_variations
                else examples
            )
            responses = []
            for base_response in base_responses:
                # Generate contextual variation
                varied_response = self._generate_contextual_variation(
                    base_response,
                    intent_category,
                    personality_config,
                    context,
                    user_message,
                )
                responses.append(varied_response)

            # If we need more variations, repeat with different examples
            if len(responses) < num_variations:
                additional_needed = num_variations - len(responses)
                additional_examples = [
                    ex for ex in examples if ex not in base_responses
                ]
                if additional_examples:
                    additional_responses = random.sample(
                        additional_examples,
                        min(additional_needed, len(additional_examples)),
                    )
                    for base_response in additional_responses:
                        varied_response = self._generate_contextual_variation(
                            base_response,
                            intent_category,
                            personality_config,
                            context,
                            user_message,
                        )
                        responses.append(varied_response)

        # If no examples, try template-based generation
        if not responses:
            # Try template system first
            template_response = self._generate_from_template(
                intent_category=intent_category,
                personality_config=personality_config,
                context=context,
                user_message=user_message,
            )
            if template_response:
                responses = [template_response]
            else:
                # Fallback to neural grammar or simple fallback
                fallback_response = self._generate_fallback_with_neural_grammar(
                    personality_config=personality_config,
                    intent_category=intent_category,
                    personality_key=personality_key,
                )
            responses = (
                [fallback_response]
                if fallback_response
                else [
                    self._generate_fallback_response(
                        personality_config, intent_category
                    )
                ]
            )

        # CRITICAL: Filter out any instruction-style responses
        filtered_responses = []
        instruction_patterns = [
            "respond",
            "reply",
            "answer",
            "say",
            "tell",
            "ask",
            "provide",
            "give",
            "offer",
            "make",
            "create",
            "generate",
            "produce",
            "build",
            "construct",
            "form",
            "consider",
            "think about",
            "reflect on",
            "contemplate",
            "ponder",
            "understand",
            "comprehend",
            "grasp",
            "realize",
            "recognize",
            "match",
            "align",
            "adjust",
            "adapt",
            "modify",
            "change",
            "alter",
            "integrate",
            "combine",
            "merge",
            "blend",
            "synthesize",
            "tailor",
            "customize",
            "personalize",
            "adapt",
            "connect",
            "link",
            "relate",
            "associate",
            "correlate",
            "share",
            "communicate",
            "express",
            "convey",
            "transmit",
            "break down",
            "analyze",
            "examine",
            "investigate",
            "explore",
            "evaluate",
            "assess",
            "judge",
            "appraise",
            "rate",
            "be",
            "become",
            "act",
            "behave",
            "perform",
            "i should",
            "i need",
            "i must",
            "i will",
            "i can",
            "i want",
            "i ought",
            "should",
            "need to",
            "must",
            "will",
            "can",
            "ought to",
            "try to",
            "attempt to",
            "aim to",
            "strive to",
            "seek to",
            "make sure",
            "ensure",
            "guarantee",
            "verify",
            "confirm",
            "be sure",
            "be certain",
            "be careful",
            "be aware",
            "needed",
            "required",
            "necessary",
            "essential",
            "important",
            "focus on",
            "concentrate on",
            "pay attention to",
            "remember to",
            "don't forget",
            "keep in mind",
        ]

        for response in responses:
            response_lower = response.lower()
            is_instruction = any(
                marker in response_lower
                for marker in [
                    "i should",
                    "i need",
                    "i must",
                    "i will",
                    "i can",
                    "i want",
                ]
            ) or any(pattern in response_lower for pattern in instruction_patterns)
            if not is_instruction:
                filtered_responses.append(response)

        # If all responses were filtered, generate a safe fallback
        if not filtered_responses:
            # Generate a simple, actual response based on intent
            match intent_category:
                case "greeting":
                    filtered_responses = ["Hey! What's up?"]
                case "asking_for_help":
                    filtered_responses = ["I'm here to help! What do you need?"]
                case "sharing_news":
                    filtered_responses = ["That's interesting! Tell me more."]
                case _:
                    filtered_responses = ["Got it! What else is on your mind?"]

        # Return first response (Swift can request variations separately)
        return {
            "response": filtered_responses[0] if filtered_responses else "",
            "variations": filtered_responses[:num_variations],
            "personality": personality_key,
            "intent_category": intent_category,
            "method": "example_based",
        }

    def _generate_variations(
        self,
        intent: str,
        personality: str,
        count: int,
        context: str = "",
        emotional_tone: str | None = None,
    ) -> dict[str, Any]:
        """Generate multiple response variations"""
        result = self._generate_response(
            intent=intent,
            personality=personality,
            context=context,
            emotional_tone=emotional_tone,
            num_variations=count,
        )
        return {
            "variations": result.get("variations", []),
            "personality": result.get("personality", personality),
            "intent_category": result.get("intent_category", ""),
        }

    def _normalize_personality_name(self, personality: str) -> str:
        """Normalize personality name to config key format"""
        # Handle display names like "Gen Z Cousin" -> "gen_z_cousin"
        normalized = personality.lower().replace(" ", "_")

        # Map common variations
        personality_map = {
            "gen_z_cousin": "gen_z_cousin",
            "genzcousin": "gen_z_cousin",
            "big_sister": "big_sister",
            "bigsister": "big_sister",
            "adhd_buddy": "adhd_buddy",
            "adhdbuddy": "adhd_buddy",
            "calm_therapist": "calm_therapist",
            "calmtherapist": "calm_therapist",
            "corporate_executive": "corporate_executive",
            "corporateexecutive": "corporate_executive",
            "aggressively_motivational": "aggressively_motivational",
            "aggressivelymotivational": "aggressively_motivational",
            "stoic_mentor": "stoic_mentor",
            "stoicmentor": "stoic_mentor",
        }

        return personality_map.get(normalized, normalized)

    def _categorize_intent(self, intent: str) -> str:
        """Categorize intent string into a category"""
        intent_lower = intent.lower()

        # Check each category's keywords
        categories = self.config.get("intent_categories", {})
        for category, keywords in categories.items():
            if any(keyword in intent_lower for keyword in keywords):
                return category

        # Default category
        return "casual_conversation"

    def _find_similar_examples(
        self, personality_config: dict[str, Any], intent_category: str
    ) -> list[str]:
        """Find similar examples when exact category doesn't exist"""
        example_responses = personality_config.get("example_responses", {})

        # Try common fallback categories
        fallback_categories = ["casual_conversation", "greeting", "asking_for_help"]
        for category in fallback_categories:
            if category in example_responses:
                return example_responses[category]

        # Return any examples we can find
        for category, examples in example_responses.items():
            if examples:
                return examples

        return []

    def _generate_fallback_with_neural_grammar(
        self,
        personality_config: dict[str, Any],
        intent_category: str,
        personality_key: str,
    ) -> str | None:
        """Generate fallback response using neural grammar module"""
        try:
            # Try to import and use neural grammar module
            from mavaia_core.brain.registry import ModuleRegistry

            grammar_module = ModuleRegistry.get_module("neural_grammar")
            if grammar_module:
                # Generate a simple template
                description = personality_config.get("description", "")
                key_phrases = personality_config.get("key_phrases", [])
                opener = random.choice(key_phrases) if key_phrases else "Hey"

                templates = {
                    "greeting": f"{opener}! What's up?",
                    "sharing_news": f"{opener}! Tell me more!",
                    "discomfort": f"{opener}, you okay? Want to talk?",
                    "asking_for_help": f"{opener}! How can I help?",
                    "casual_conversation": f"{opener}! That's interesting.",
                }

                template = templates.get(
                    intent_category, f"{opener}! What's on your mind?"
                )

                # Use neural grammar to naturalize the template
                result = grammar_module.execute(
                    "naturalize_response",
                    {"text": template, "persona": personality_key, "context": ""},
                )

                if (text := result.get("text")) and result.get(
                    "confidence", 0.0
                ) >= 0.70:
                    return text
        except Exception as e:
            logger.debug(
                "Neural grammar fallback failed",
                exc_info=True,
                extra={"module_name": "personality_response", "error_type": type(e).__name__},
            )

        return None

    def _generate_contextual_variation(
        self,
        base_response: str,
        intent_category: str,
        personality_config: dict[str, Any],
        context: str,
        user_message: str,
    ) -> str:
        """Generate contextual variation of a base response"""
        if not base_response:
            return base_response

        # Extract key phrases from personality
        key_phrases = personality_config.get("key_phrases", [])
        
        # Get personality name to check if it's gen_z_cousin
        personality_name = personality_config.get("name", "").lower()
        is_gen_z = "gen_z" in personality_name or "genz" in personality_name

        # Simple template-based variation
        # Apply personality-specific modifications to the base response
        variation = base_response

        # Add personality-specific phrases occasionally
        if key_phrases and random.random() < 0.3:
            # Sometimes add a key phrase at the start
            opener = random.choice(key_phrases)
            if not variation.lower().startswith(opener.lower()):
                variation = f"{opener.capitalize()}! {variation}"

        # For gen_z_cousin, add casual markers and contractions
        if is_gen_z:
            # Add casual markers
            casual_markers = ["hey", "yeah", "like", "totally", "yoo", "cuz", "sis", "fr", "bet"]
            if random.random() < 0.4:  # 40% chance to add casual marker
                marker = random.choice(casual_markers)
                if marker not in variation.lower():
                    variation = f"{marker.capitalize()}, {variation}"
            
            # Ensure contractions are used
            import re
            # Replace formal phrases with contractions
            contraction_map = {
                r"\bit is\b": "it's",
                r"\bthat is\b": "that's",
                r"\bi am\b": "i'm",
                r"\byou are\b": "you're",
                r"\bwe are\b": "we're",
                r"\bthey are\b": "they're",
                r"\bis not\b": "isn't",
                r"\bare not\b": "aren't",
                r"\bdo not\b": "don't",
                r"\bwill not\b": "won't",
                r"\bcannot\b": "can't",
            }
            for pattern, replacement in contraction_map.items():
                variation = re.sub(pattern, replacement, variation, flags=re.IGNORECASE)

        # Context-aware modifications
        if context:
            # If context mentions something specific, try to reference it
            context_lower = context.lower()
            if "question" in context_lower or "?" in user_message:
                # For questions, ensure response acknowledges the question
                if "?" not in variation and "question" not in variation.lower():
                    # Don't modify if already appropriate
                    pass

        # Conversation state awareness
        # Check if this is a follow-up (context contains previous conversation)
        if "previous" in context.lower() or "earlier" in context.lower():
            # Add continuity markers occasionally
            continuity_markers = [
                "Speaking of which,",
                "That reminds me,",
                "On that note,",
                "Related to that,",
            ]
            if random.random() < 0.2 and not any(
                marker in variation for marker in continuity_markers
            ):
                variation = f"{random.choice(continuity_markers)} {variation.lower()}"

        return variation

    def _generate_from_template(
        self,
        intent_category: str,
        personality_config: dict[str, Any],
        context: str,
        user_message: str,
    ) -> str | None:
        """Generate response using template system with personality slot filling"""
        key_phrases = personality_config.get("key_phrases", [])
        opener = random.choice(key_phrases) if key_phrases else "Hey"
        description = personality_config.get("description", "")

        # Template system with personality-specific slot filling
        templates = {
            "greeting": [
                "{opener}! What's up?",
                "{opener}! How's it going?",
                "{opener}! What's on your mind?",
                "Hey! {opener}! What's good?",
                "{opener}! How can I help?",
            ],
            "asking_for_help": [
                "{opener}! What do you need?",
                "I got you! What's up?",
                "{opener}! Let's figure this out!",
                "For sure! What can I do?",
                "{opener}! I'm here to help!",
            ],
            "sharing_news": [
                "{opener}! Tell me more!",
                "Wait, what?! Tell me everything!",
                "{opener}! That's interesting!",
                "No way! What happened?!",
                "{opener}! I need details!",
            ],
            "discomfort": [
                "{opener}, you okay?",
                "Hey, what's going on?",
                "That sounds rough. Want to talk?",
                "{opener}, I'm here if you need me.",
                "That's heavy. What's on your mind?",
            ],
            "expressing_emotion_positive": [
                "That's awesome! I'm so happy for you!",
                "Yay! That's amazing!",
                "That's fantastic! Tell me more!",
                "Oh my gosh, that's wonderful!",
                "That's so great! I love it!",
            ],
            "expressing_emotion_negative": [
                "That sounds really hard. I'm here for you.",
                "Oh no, that's tough. Want to talk about it?",
                "I'm sorry you're going through that.",
                "That sounds rough. I'm listening.",
                "That's heavy. I'm here if you need me.",
            ],
            "requesting_information": [
                "Great question! Let me help you with that.",
                "Here's what I know...",
                "Let me break this down...",
                "Here's the info...",
                "I can help with that!",
            ],
            "casual_conversation": [
                "That's interesting! Tell me more.",
                "I'm listening. Go on.",
                "That's cool! Keep going.",
                "I hear you. Continue.",
                "That's awesome! I want to hear more.",
            ],
        }

        # Get template for this intent category
        category_templates = templates.get(
            intent_category, templates.get("casual_conversation", [])
        )
        if not category_templates:
            return None

        # Select a template
        template = random.choice(category_templates)

        # Fill slots with personality-specific content
        response = template.replace("{opener}", opener).replace(
            "{personality}", description
        )

        return response

    def _generate_fallback_response(
        self, personality_config: dict[str, Any], intent_category: str
    ) -> str:
        """Generate a simple fallback response when examples aren't available"""
        description = personality_config.get("description", "")
        key_phrases = personality_config.get("key_phrases", [])

        # Use a key phrase if available
        opener = random.choice(key_phrases) if key_phrases else "Hey"

        # Simple templates based on category
        templates = {
            "greeting": f"{opener}! What's up?",
            "sharing_news": f"{opener}! Tell me more!",
            "discomfort": f"{opener}, you okay? Want to talk?",
            "asking_for_help": f"{opener}! How can I help?",
            "casual_conversation": f"{opener}! That's interesting.",
        }

        return templates.get(intent_category, f"{opener}! What's on your mind?")

    def validate_params(self, operation: str, params: dict[str, Any]) -> bool:
        """Validate parameters for operations"""
        match operation:
            case "generate" | "generate_variations":
                return "intent" in params and "personality" in params
            case _:
                return True
