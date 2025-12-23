"""
Creative Writing Module - Narrative structures, creative patterns, and storytelling
Handles creative writing generation, narrative structures, creative language patterns
No LLM dependencies - uses templates, patterns, and structured generation
"""

from pathlib import Path
from typing import Any, Dict, List
import random
import re

from mavaia_core.brain.base_module import BaseBrainModule, ModuleMetadata
from mavaia_core.exceptions import InvalidParameterError


class CreativeWritingModule(BaseBrainModule):
    """Generate creative writing using narrative structures and patterns"""

    def __init__(self):
        super().__init__()
        self.narrative_structures = {
            "three_act": ["setup", "confrontation", "resolution"],
            "hero_journey": [
                "ordinary_world",
                "call_to_adventure",
                "refusal",
                "mentor",
                "crossing_threshold",
                "tests_allies_enemies",
                "approach",
                "ordeal",
                "reward",
                "road_back",
                "resurrection",
                "return",
            ],
            "fairy_tale": [
                "once_upon_a_time",
                "introduction",
                "problem",
                "journey",
                "obstacle",
                "solution",
                "resolution",
                "moral",
            ],
            "mystery": [
                "crime",
                "investigation",
                "clues",
                "red_herrings",
                "revelation",
                "resolution",
            ],
        }
        self.creative_patterns = {
            "metaphor": ["like", "as", "resembles", "mirrors"],
            "alliteration": ["repeated", "sound", "pattern"],
            "personification": ["whispered", "danced", "sang", "wept"],
            "imagery": ["vivid", "sensory", "descriptive"],
        }

    @property
    def metadata(self) -> ModuleMetadata:
        return ModuleMetadata(
            name="creative_writing",
            version="1.0.0",
            description=(
                "Creative writing: narrative structures, creative patterns, "
                "storytelling, imaginative generation"
            ),
            operations=[
                "generate_story",
                "create_narrative",
                "apply_structure",
                "add_creative_elements",
                "generate_character",
                "create_setting",
                "build_plot",
                "write_poem",
            ],
            dependencies=[],
            model_required=False,
        )

    def initialize(self) -> bool:
        """Initialize the module"""
        return True

    def execute(self, operation: str, params: Dict[str, Any]) -> Dict[str, Any]:
        """Execute a creative writing operation"""
        match operation:
            case "generate_story":
                theme = params.get("theme", "")
                structure = params.get("structure", "three_act")
                length = params.get("length", "short")
                if theme is None:
                    theme = ""
                if structure is None:
                    structure = "three_act"
                if length is None:
                    length = "short"
                if not isinstance(theme, str):
                    raise InvalidParameterError("theme", str(type(theme).__name__), "theme must be a string")
                if not isinstance(structure, str):
                    raise InvalidParameterError("structure", str(type(structure).__name__), "structure must be a string")
                if not isinstance(length, str):
                    raise InvalidParameterError("length", str(type(length).__name__), "length must be a string")
                return self.generate_story(theme, structure, length)
            case "create_narrative":
                elements = params.get("elements", {})
                style = params.get("style", "descriptive")
                if elements is None:
                    elements = {}
                if style is None:
                    style = "descriptive"
                if not isinstance(elements, dict):
                    raise InvalidParameterError("elements", str(type(elements).__name__), "elements must be a dict")
                if not isinstance(style, str):
                    raise InvalidParameterError("style", str(type(style).__name__), "style must be a string")
                return self.create_narrative(elements, style)
            case "apply_structure":
                content = params.get("content", "")
                structure_type = params.get("structure_type", "three_act")
                if content is None:
                    content = ""
                if structure_type is None:
                    structure_type = "three_act"
                if not isinstance(content, str):
                    raise InvalidParameterError("content", str(type(content).__name__), "content must be a string")
                if not isinstance(structure_type, str):
                    raise InvalidParameterError(
                        "structure_type", str(type(structure_type).__name__), "structure_type must be a string"
                    )
                return self.apply_structure(content, structure_type)
            case "add_creative_elements":
                text = params.get("text", "")
                elements = params.get("elements", ["metaphor", "imagery"])
                if text is None:
                    text = ""
                if elements is None:
                    elements = ["metaphor", "imagery"]
                if not isinstance(text, str):
                    raise InvalidParameterError("text", str(type(text).__name__), "text must be a string")
                if not isinstance(elements, list) or not all(isinstance(e, str) for e in elements):
                    raise InvalidParameterError("elements", str(type(elements).__name__), "elements must be a list[str]")
                return self.add_creative_elements(text, elements)
            case "generate_character":
                traits = params.get("traits", [])
                role = params.get("role", "protagonist")
                if traits is None:
                    traits = []
                if role is None:
                    role = "protagonist"
                if not isinstance(traits, list) or not all(isinstance(t, str) for t in traits):
                    raise InvalidParameterError("traits", str(type(traits).__name__), "traits must be a list[str]")
                if not isinstance(role, str):
                    raise InvalidParameterError("role", str(type(role).__name__), "role must be a string")
                return self.generate_character(traits, role)
            case "create_setting":
                location = params.get("location", "")
                mood = params.get("mood", "neutral")
                if location is None:
                    location = ""
                if mood is None:
                    mood = "neutral"
                if not isinstance(location, str):
                    raise InvalidParameterError("location", str(type(location).__name__), "location must be a string")
                if not isinstance(mood, str):
                    raise InvalidParameterError("mood", str(type(mood).__name__), "mood must be a string")
                return self.create_setting(location, mood)
            case "build_plot":
                conflict = params.get("conflict", "")
                resolution = params.get("resolution", "")
                if conflict is None:
                    conflict = ""
                if resolution is None:
                    resolution = ""
                if not isinstance(conflict, str):
                    raise InvalidParameterError("conflict", str(type(conflict).__name__), "conflict must be a string")
                if not isinstance(resolution, str):
                    raise InvalidParameterError(
                        "resolution", str(type(resolution).__name__), "resolution must be a string"
                    )
                return self.build_plot(conflict, resolution)
            case "write_poem":
                theme = params.get("theme", "")
                form = params.get("form", "free_verse")
                if theme is None:
                    theme = ""
                if form is None:
                    form = "free_verse"
                if not isinstance(theme, str):
                    raise InvalidParameterError("theme", str(type(theme).__name__), "theme must be a string")
                if not isinstance(form, str):
                    raise InvalidParameterError("form", str(type(form).__name__), "form must be a string")
                return self.write_poem(theme, form)
            case _:
                raise InvalidParameterError("operation", str(operation), "Unknown operation for creative_writing")

    def generate_story(
        self, theme: str, structure: str = "three_act", length: str = "short"
    ) -> Dict[str, Any]:
        """Generate a story with specified structure"""
        if not theme:
            theme = "adventure"

        structure_steps = self.narrative_structures.get(structure, [])
        if not structure_steps:
            structure_steps = self.narrative_structures["three_act"]

        story_parts = []
        for step in structure_steps:
            part = self._generate_story_part(step, theme, structure)
            story_parts.append({"stage": step, "content": part})

        # Combine into full story
        full_story = self._combine_story_parts(story_parts, length)

        return {
            "story": full_story,
            "theme": theme,
            "structure": structure,
            "length": length,
            "parts": story_parts,
        }

    def create_narrative(
        self, elements: Dict[str, Any], style: str = "descriptive"
    ) -> Dict[str, Any]:
        """Create a narrative from elements"""
        character = elements.get("character", "a person")
        setting = elements.get("setting", "a place")
        conflict = elements.get("conflict", "a challenge")
        resolution = elements.get("resolution", "a solution")

        narrative = self._build_narrative(character, setting, conflict, resolution, style)

        return {
            "narrative": narrative,
            "elements": elements,
            "style": style,
        }

    def apply_structure(
        self, content: str, structure_type: str = "three_act"
    ) -> Dict[str, Any]:
        """Apply narrative structure to existing content"""
        if not content:
            return {"structured_content": "", "error": "No content provided"}

        structure_steps = self.narrative_structures.get(structure_type, [])
        if not structure_steps:
            return {"structured_content": content, "error": "Unknown structure"}

        # Split content into parts (simplified)
        content_parts = self._split_content(content, len(structure_steps))

        structured = []
        for i, step in enumerate(structure_steps):
            part_content = (
                content_parts[i] if i < len(content_parts) else ""
            )
            structured.append(
                {
                    "stage": step,
                    "content": part_content,
                    "label": step.replace("_", " ").title(),
                }
            )

        return {
            "structured_content": structured,
            "structure_type": structure_type,
            "original_length": len(content),
        }

    def add_creative_elements(
        self, text: str, elements: List[str] = None
    ) -> Dict[str, Any]:
        """Add creative elements to text"""
        if not text:
            return {"enhanced_text": "", "error": "No text provided"}

        if elements is None:
            elements = ["metaphor", "imagery"]

        enhanced = text

        # Add metaphors
        if "metaphor" in elements:
            enhanced = self._add_metaphors(enhanced)

        # Add imagery
        if "imagery" in elements:
            enhanced = self._add_imagery(enhanced)

        # Add personification
        if "personification" in elements:
            enhanced = self._add_personification(enhanced)

        # Add alliteration
        if "alliteration" in elements:
            enhanced = self._add_alliteration(enhanced)

        return {
            "enhanced_text": enhanced,
            "original_text": text,
            "elements_added": elements,
        }

    def generate_character(
        self, traits: List[str] = None, role: str = "protagonist"
    ) -> Dict[str, Any]:
        """Generate a character description"""
        if traits is None:
            traits = []

        character = {
            "name": self._generate_name(),
            "role": role,
            "traits": traits or self._generate_traits(role),
            "description": self._generate_character_description(traits, role),
            "motivation": self._generate_motivation(role),
        }

        return {"character": character}

    def create_setting(
        self, location: str = "", mood: str = "neutral"
    ) -> Dict[str, Any]:
        """Create a setting description"""
        if not location:
            location = self._generate_location()

        setting = {
            "location": location,
            "mood": mood,
            "description": self._generate_setting_description(location, mood),
            "sensory_details": self._generate_sensory_details(mood),
            "atmosphere": self._generate_atmosphere(mood),
        }

        return {"setting": setting}

    def build_plot(
        self, conflict: str = "", resolution: str = ""
    ) -> Dict[str, Any]:
        """Build a plot from conflict and resolution"""
        if not conflict:
            conflict = self._generate_conflict()
        if not resolution:
            resolution = self._generate_resolution(conflict)

        plot = {
            "conflict": conflict,
            "rising_action": self._generate_rising_action(conflict),
            "climax": self._generate_climax(conflict, resolution),
            "resolution": resolution,
            "plot_points": self._generate_plot_points(conflict, resolution),
        }

        return {"plot": plot}

    def write_poem(self, theme: str = "", form: str = "free_verse") -> Dict[str, Any]:
        """Write a poem on a theme"""
        if not theme:
            theme = "nature"

        match form:
            case "haiku":
                poem = self._write_haiku(theme)
            case "limerick":
                poem = self._write_limerick(theme)
            case "sonnet":
                poem = self._write_sonnet(theme)
            case _:  # free_verse
                poem = self._write_free_verse(theme)

        return {
            "poem": poem,
            "theme": theme,
            "form": form,
            "lines": len(poem.split("\n")),
        }

    def _generate_story_part(
        self, stage: str, theme: str, structure: str
    ) -> str:
        """Generate content for a story stage"""
        templates = {
            "setup": f"In the beginning, {theme} was introduced.",
            "confrontation": f"The challenge of {theme} emerged.",
            "resolution": f"Finally, {theme} was resolved.",
            "once_upon_a_time": f"Once upon a time, there was {theme}.",
            "problem": f"But then, a problem arose with {theme}.",
            "journey": f"A journey began to address {theme}.",
            "obstacle": f"An obstacle appeared related to {theme}.",
            "solution": f"A solution was found for {theme}.",
            "moral": f"The lesson learned about {theme}.",
        }

        return templates.get(stage, f"The story progressed with {theme}.")

    def _combine_story_parts(
        self, parts: List[Dict[str, Any]], length: str
    ) -> str:
        """Combine story parts into full story"""
        story_lines = []
        for part in parts:
            content = part.get("content", "")
            if content:
                story_lines.append(content)

        story = " ".join(story_lines)

        # Adjust length
        match length:
            case "short":
                # Keep first 3 parts
                story_lines = story_lines[:3]
            case "long":
                # Expand each part
                story_lines = [line + " " + self._expand_line(line) for line in story_lines]
            case _:  # medium
                pass

        return " ".join(story_lines)

    def _build_narrative(
        self,
        character: str,
        setting: str,
        conflict: str,
        resolution: str,
        style: str,
    ) -> str:
        """Build narrative from elements"""
        narrative_parts = [
            f"In {setting},",
            f"{character} faced {conflict}.",
            f"Through determination, {resolution}.",
        ]

        if style == "descriptive":
            narrative_parts = [
                f"In the vivid setting of {setting},",
                f"{character} encountered the challenge of {conflict}.",
                f"With courage and wisdom, {resolution} was achieved.",
            ]

        return " ".join(narrative_parts)

    def _split_content(self, content: str, num_parts: int) -> List[str]:
        """Split content into parts"""
        sentences = re.split(r"[.!?]+", content)
        sentences = [s.strip() for s in sentences if s.strip()]

        if not sentences:
            return [content]

        # Distribute sentences across parts
        part_size = max(1, len(sentences) // num_parts)
        parts = []
        for i in range(0, len(sentences), part_size):
            part = ". ".join(sentences[i : i + part_size])
            if part:
                parts.append(part + ".")

        # Ensure we have enough parts
        while len(parts) < num_parts:
            parts.append("")

        return parts[:num_parts]

    def _add_metaphors(self, text: str) -> str:
        """Add metaphors to text"""
        # Simple metaphor insertion
        metaphors = [
            "like a river flowing",
            "as bright as the sun",
            "like a storm approaching",
            "as quiet as the night",
        ]
        if len(text.split()) > 5:
            # Insert metaphor after first sentence
            sentences = re.split(r"[.!?]+", text)
            if len(sentences) > 1:
                sentences[0] += f", {random.choice(metaphors)}"
                text = ". ".join(sentences)
        return text

    def _add_imagery(self, text: str) -> str:
        """Add imagery to text"""
        # Add sensory details
        imagery_words = ["vivid", "bright", "colorful", "textured", "aromatic"]
        words = text.split()
        if len(words) > 3:
            # Insert imagery word
            insert_pos = len(words) // 2
            words.insert(insert_pos, random.choice(imagery_words))
            text = " ".join(words)
        return text

    def _add_personification(self, text: str) -> str:
        """Add personification to text"""
        # Simple personification patterns
        personification = {
            "wind": "whispered",
            "tree": "danced",
            "river": "sang",
            "cloud": "wept",
        }
        for word, action in personification.items():
            if word in text.lower():
                text = text.replace(word, f"{word} {action}")
                break
        return text

    def _add_alliteration(self, text: str) -> str:
        """Add alliteration to text"""
        # Simple alliteration: find words starting with same letter
        words = text.split()
        if len(words) > 2:
            # Try to create alliteration
            first_letter = words[0][0].lower() if words[0] else ""
            if first_letter:
                alliterative_words = [
                    w for w in words[1:3] if w.lower().startswith(first_letter)
                ]
                if alliterative_words:
                    # Already has alliteration
                    pass
        return text

    def _generate_name(self) -> str:
        """Generate a character name"""
        first_names = ["Alex", "Jordan", "Sam", "Taylor", "Casey"]
        last_names = ["Smith", "Johnson", "Williams", "Brown", "Davis"]
        return f"{random.choice(first_names)} {random.choice(last_names)}"

    def _generate_traits(self, role: str) -> List[str]:
        """Generate character traits based on role"""
        trait_sets = {
            "protagonist": ["brave", "determined", "curious", "kind"],
            "antagonist": ["cunning", "ambitious", "ruthless", "clever"],
            "mentor": ["wise", "patient", "experienced", "helpful"],
            "sidekick": ["loyal", "humorous", "supportive", "optimistic"],
        }
        return trait_sets.get(role, ["unique", "interesting", "complex"])

    def _generate_character_description(
        self, traits: List[str], role: str
    ) -> str:
        """Generate character description"""
        trait_str = ", ".join(traits[:3]) if traits else "unique"
        return f"A {role} characterized by {trait_str}."

    def _generate_motivation(self, role: str) -> str:
        """Generate character motivation"""
        motivations = {
            "protagonist": "to overcome challenges and achieve their goal",
            "antagonist": "to achieve their own goals, regardless of obstacles",
            "mentor": "to guide and teach others",
            "sidekick": "to support and help their friend",
        }
        return motivations.get(role, "to fulfill their purpose")

    def _generate_location(self) -> str:
        """Generate a location"""
        locations = [
            "a mysterious forest",
            "a bustling city",
            "a quiet village",
            "a distant planet",
            "an ancient castle",
        ]
        return random.choice(locations)

    def _generate_setting_description(
        self, location: str, mood: str
    ) -> str:
        """Generate setting description"""
        mood_descriptors = {
            "dark": "ominous and shadowy",
            "bright": "vibrant and cheerful",
            "mysterious": "enigmatic and intriguing",
            "peaceful": "serene and tranquil",
            "neutral": "balanced and calm",
        }
        descriptor = mood_descriptors.get(mood, "interesting")
        return f"{location} with a {descriptor} atmosphere."

    def _generate_sensory_details(self, mood: str) -> Dict[str, str]:
        """Generate sensory details"""
        sensory_sets = {
            "dark": {
                "sight": "dim shadows",
                "sound": "echoing whispers",
                "smell": "damp earth",
            },
            "bright": {
                "sight": "vibrant colors",
                "sound": "melodious birdsong",
                "smell": "fresh flowers",
            },
            "mysterious": {
                "sight": "shifting mists",
                "sound": "distant murmurs",
                "smell": "ancient scents",
            },
            "peaceful": {
                "sight": "gentle light",
                "sound": "soft rustling",
                "smell": "clean air",
            },
        }
        return sensory_sets.get(mood, {"sight": "various sights", "sound": "sounds", "smell": "scents"})

    def _generate_atmosphere(self, mood: str) -> str:
        """Generate atmosphere description"""
        atmospheres = {
            "dark": "A sense of foreboding fills the air.",
            "bright": "A feeling of joy and energy permeates the space.",
            "mysterious": "An aura of mystery surrounds everything.",
            "peaceful": "A calm tranquility envelops the scene.",
            "neutral": "A balanced atmosphere prevails.",
        }
        return atmospheres.get(mood, "An interesting atmosphere.")

    def _generate_conflict(self) -> str:
        """Generate a conflict"""
        conflicts = [
            "a great challenge",
            "an impossible task",
            "a dangerous enemy",
            "a moral dilemma",
            "a personal struggle",
        ]
        return random.choice(conflicts)

    def _generate_resolution(self, conflict: str) -> str:
        """Generate resolution for conflict"""
        return f"a solution was found for {conflict}"

    def _generate_rising_action(self, conflict: str) -> str:
        """Generate rising action"""
        return f"Tensions increased as {conflict} became more pressing."

    def _generate_climax(self, conflict: str, resolution: str) -> str:
        """Generate climax"""
        return f"The moment of truth arrived when {conflict} reached its peak, leading to {resolution}."

    def _generate_plot_points(
        self, conflict: str, resolution: str
    ) -> List[str]:
        """Generate plot points"""
        return [
            f"Introduction of {conflict}",
            "Development of the situation",
            f"Resolution through {resolution}",
        ]

    def _write_haiku(self, theme: str) -> str:
        """Write a haiku (5-7-5 syllables)"""
        # Simplified haiku - actual syllable counting would be more complex
        lines = [
            f"{theme} in the air",
            f"Moments pass like gentle breeze",
            f"Nature's quiet song",
        ]
        return "\n".join(lines)

    def _write_limerick(self, theme: str) -> str:
        """Write a limerick"""
        lines = [
            f"There once was a theme called {theme}",
            "That sparked creativity's dream",
            "With words and with rhyme",
            "It passed through all time",
            "And became part of life's grand scheme",
        ]
        return "\n".join(lines)

    def _write_sonnet(self, theme: str) -> str:
        """Write a sonnet (14 lines, simplified)"""
        lines = [
            f"About {theme} I now write",
            "With words that flow and take flight",
            "Through verses fourteen",
            "A story is seen",
            "Of {theme} in morning light",
            "And {theme} in the dark of night",
            "A tale that feels just right",
            "With rhythm and rhyme",
            "That stands the test of time",
            "And brings the theme to light",
            "So {theme} shall be told",
            "In words both new and old",
            "A story to unfold",
            f"About {theme}, brave and bold",
        ]
        return "\n".join(lines)

    def _write_free_verse(self, theme: str) -> str:
        """Write free verse poem"""
        lines = [
            f"{theme}",
            "flows like water",
            "through the mind",
            "creating images",
            "and emotions",
            "that resonate",
            "with the soul",
        ]
        return "\n".join(lines)

    def _expand_line(self, line: str) -> str:
        """Expand a line with more detail"""
        expansions = [
            "with great detail",
            "in vivid description",
            "through rich imagery",
        ]
        return random.choice(expansions)

    def validate_params(self, operation: str, params: Dict[str, Any]) -> bool:
        """Validate parameters for operations"""
        match operation:
            case "generate_story" | "write_poem":
                return True  # Optional theme
            case "create_narrative":
                return "elements" in params
            case "apply_structure":
                return "content" in params
            case "add_creative_elements":
                return "text" in params
            case "generate_character" | "create_setting" | "build_plot":
                return True  # All parameters optional
            case _:
                return True

