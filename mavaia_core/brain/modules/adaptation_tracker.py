"""
Adaptation Tracker Module - Analyze communication patterns and calculate adaptation factors
Tracks user communication style over time and suggests personality adjustments
"""

from typing import Dict, Any, List, Optional
import json
import re
import sys
from pathlib import Path
from collections import Counter

# Add parent directory to path for imports

from mavaia_core.brain.base_module import BaseBrainModule, ModuleMetadata


class AdaptationTrackerModule(BaseBrainModule):
    """Track and analyze user communication patterns for personality adaptation"""

    def __init__(self):
        self.config = None
        self._load_config()

        # Formal word patterns
        self.formal_words = {
            "please",
            "thank",
            "appreciate",
            "request",
            "would",
            "could",
            "should",
            "respectfully",
            "sincerely",
            "regards",
            "indeed",
            "furthermore",
            "moreover",
        }

        # Casual word patterns
        self.casual_words = {
            "yeah",
            "yep",
            "nah",
            "dude",
            "bro",
            "sup",
            "yo",
            "hey",
            "cool",
            "awesome",
            "nice",
            "sure",
            "ok",
            "okay",
            "yeah",
            "yea",
        }

        # Slang word patterns
        self.slang_words = {
            "yeet",
            "fr",
            "frfr",
            "no cap",
            "cap",
            "bet",
            "lowkey",
            "highkey",
            "deadass",
            "spill",
            "tea",
            "sis",
            "cuz",
            "sus",
            "slay",
            "vibe",
            "vibes",
            "mood",
            "facts",
            "facts only",
            "periodt",
            "period",
            "stan",
        }

        # Emotional tone keywords
        self.tone_keywords = {
            "playful": [
                "lol",
                "haha",
                "funny",
                "joke",
                "hilarious",
                "laugh",
                "lmao",
                "lmfao",
            ],
            "warm": [
                "love",
                "care",
                "feel",
                "warm",
                "comfort",
                "support",
                "appreciate",
                "grateful",
            ],
            "assertive": [
                "need",
                "must",
                "should",
                "definitely",
                "absolutely",
                "sure",
                "certain",
            ],
            "protective": [
                "worried",
                "concern",
                "care",
                "protect",
                "safe",
                "help",
                "worry",
            ],
        }

    @property
    def metadata(self) -> ModuleMetadata:
        return ModuleMetadata(
            name="adaptation_tracker",
            version="1.0.0",
            description="Track user communication patterns and calculate adaptation factors",
            operations=[
                "analyze_communication_patterns",
                "calculate_adaptation_factors",
                "suggest_personality_adjustments",
                "track_phrase_usage",
            ],
            dependencies=[],
            model_required=False,
        )

    def initialize(self) -> bool:
        """Initialize the module"""
        return True

    def _load_config(self):
        """Load adaptation tracker configuration"""
        config_path = Path(__file__).parent / "adaptation_tracker_config.json"
        try:
            if config_path.exists():
                with open(config_path, "r", encoding="utf-8") as f:
                    self.config = json.load(f)
            else:
                self.config = {
                    "fast_adaptation_window": 15,
                    "fast_adaptation_alpha": 0.4,
                    "gradual_adaptation_alpha": 0.15,
                }
        except Exception as e:
            print(
                f"[AdaptationTrackerModule] Failed to load config: {e}", file=sys.stderr
            )
            self.config = {}

    def execute(self, operation: str, params: Dict[str, Any]) -> Dict[str, Any]:
        """Execute an adaptation tracker operation"""
        if operation == "analyze_communication_patterns":
            conversation_history = params.get("conversation_history", [])
            return self.analyze_communication_patterns(conversation_history)
        elif operation == "calculate_adaptation_factors":
            user_profile = params.get("user_profile", {})
            recent_conversations = params.get("recent_conversations", [])
            return self.calculate_adaptation_factors(user_profile, recent_conversations)
        elif operation == "suggest_personality_adjustments":
            base_config = params.get("base_config", {})
            user_profile = params.get("user_profile", {})
            return self.suggest_personality_adjustments(base_config, user_profile)
        elif operation == "track_phrase_usage":
            messages = params.get("messages", [])
            return self.track_phrase_usage(messages)
        else:
            raise ValueError(f"Unknown operation: {operation}")

    def analyze_communication_patterns(
        self, conversation_history: List[str]
    ) -> Dict[str, Any]:
        """Extract user communication metrics from conversation history"""
        if not conversation_history:
            return {
                "formality_level": 0.5,
                "slang_usage": 0.0,
                "cultural_reference_comfort": 0.0,
                "average_energy": 0.5,
                "preferred_emotional_tone": None,
                "response_length_preference": 20.0,
            }

        # Analyze all messages
        formality_samples = []
        slang_samples = []
        energy_samples = []
        length_samples = []
        tone_scores = {"playful": 0, "warm": 0, "assertive": 0, "protective": 0}
        cultural_count = 0

        for message in conversation_history:
            words = message.lower().split()
            word_count = len(words)
            length_samples.append(word_count)

            # Formality
            formal_count = sum(1 for word in words if word in self.formal_words)
            casual_count = sum(1 for word in words if word in self.casual_words)
            if formal_count + casual_count > 0:
                formality = formal_count / (formal_count + casual_count)
            else:
                formality = 0.5  # Neutral
            formality_samples.append(formality)

            # Slang usage
            slang_count = sum(
                1 for word in words if any(slang in word for slang in self.slang_words)
            )
            slang_usage = min(1.0, slang_count / max(1.0, word_count * 0.3))
            slang_samples.append(slang_usage)

            # Energy (punctuation, caps, length)
            exclamation = message.count("!")
            question = message.count("?")
            caps = sum(1 for c in message if c.isupper())
            energy = min(
                1.0,
                (exclamation * 0.3 + question * 0.2 + caps * 0.1 + word_count * 0.01),
            )
            energy_samples.append(energy)

            # Emotional tone
            message_lower = message.lower()
            for tone, keywords in self.tone_keywords.items():
                tone_scores[tone] += sum(
                    1 for keyword in keywords if keyword in message_lower
                )

            # Cultural references
            cultural_indicators = [
                "meme",
                "viral",
                "trend",
                "tiktok",
                "instagram",
                "twitter",
                "youtube",
            ]
            if any(indicator in message_lower for indicator in cultural_indicators):
                cultural_count += 1

        # Calculate averages
        avg_formality = (
            sum(formality_samples) / len(formality_samples)
            if formality_samples
            else 0.5
        )
        avg_slang = sum(slang_samples) / len(slang_samples) if slang_samples else 0.0
        avg_energy = (
            sum(energy_samples) / len(energy_samples) if energy_samples else 0.5
        )
        avg_length = (
            sum(length_samples) / len(length_samples) if length_samples else 20.0
        )
        cultural_comfort = min(
            1.0, cultural_count / max(1.0, len(conversation_history) * 0.3)
        )

        # Determine preferred tone
        preferred_tone = None
        if max(tone_scores.values()) > 0:
            preferred_tone = max(tone_scores.items(), key=lambda x: x[1])[0]

        return {
            "formality_level": avg_formality,
            "slang_usage": avg_slang,
            "cultural_reference_comfort": cultural_comfort,
            "average_energy": avg_energy,
            "preferred_emotional_tone": preferred_tone,
            "response_length_preference": avg_length,
        }

    def calculate_adaptation_factors(
        self, user_profile: Dict[str, Any], recent_conversations: List[str]
    ) -> Dict[str, Any]:
        """Compute adaptation adjustments based on user profile and recent conversations"""
        # Analyze recent conversations
        recent_metrics = self.analyze_communication_patterns(recent_conversations)

        # Get current profile values
        current_formality = user_profile.get("formality_level", 0.5)
        current_slang = user_profile.get("slang_usage", 0.0)
        current_energy = user_profile.get("average_energy", 0.5)
        conversation_count = user_profile.get("conversation_count", 0)

        # Calculate adaptation factors (how much to adjust)
        # Fast adaptation for recent conversations
        alpha_fast = 0.4
        formality_factor = (
            current_formality * (1 - alpha_fast)
            + recent_metrics["formality_level"] * alpha_fast
        )
        slang_factor = (
            current_slang * (1 - alpha_fast)
            + recent_metrics["slang_usage"] * alpha_fast
        )
        energy_factor = (
            current_energy * (1 - alpha_fast)
            + recent_metrics["average_energy"] * alpha_fast
        )

        # Determine adaptation strength based on conversation count
        adaptation_strength = min(0.5, 0.1 + (conversation_count / 100) * 0.4)

        return {
            "formality_adjustment": formality_factor - current_formality,
            "slang_adjustment": slang_factor - current_slang,
            "energy_adjustment": energy_factor - current_energy,
            "adaptation_strength": adaptation_strength,
            "suggested_formality": formality_factor,
            "suggested_slang": slang_factor,
            "suggested_energy": energy_factor,
            "preferred_tone": recent_metrics.get("preferred_emotional_tone"),
        }

    def suggest_personality_adjustments(
        self, base_config: Dict[str, Any], user_profile: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Generate adapted personality configuration"""
        formality = user_profile.get("formality_level", 0.5)
        slang = user_profile.get("slang_usage", 0.0)
        cultural = user_profile.get("cultural_reference_comfort", 0.0)
        energy = user_profile.get("average_energy", 0.5)
        conversation_count = user_profile.get("conversation_count", 0)

        # Determine adaptation strength
        if conversation_count < 5:
            adaptation_strength = 0.1
        elif conversation_count < 20:
            adaptation_strength = 0.2
        else:
            adaptation_strength = 0.5

        # Get base values
        base_formality = base_config.get("formality_baseline", 0.5)
        base_slang = base_config.get("slang_comfort_level", 0.0)
        base_cultural = base_config.get("cultural_reference_comfort", 0.0)
        base_energy = base_config.get("energy_matching_intensity", 0.5)

        # Blend base and adapted
        adapted_formality = (
            base_formality * (1 - adaptation_strength) + formality * adaptation_strength
        )
        adapted_slang = (
            base_slang * (1 - adaptation_strength) + slang * adaptation_strength
        )
        adapted_cultural = (
            base_cultural * (1 - adaptation_strength) + cultural * adaptation_strength
        )
        adapted_energy = (
            base_energy * (1 - adaptation_strength) + energy * adaptation_strength
        )

        # Clamp values
        adapted_formality = max(0.0, min(1.0, adapted_formality))
        adapted_slang = max(0.0, min(1.0, adapted_slang))
        adapted_cultural = max(0.0, min(1.0, adapted_cultural))
        adapted_energy = max(0.0, min(1.0, adapted_energy))

        # Create adapted config (copy base and modify)
        adapted_config = base_config.copy()
        adapted_config["formality_baseline"] = adapted_formality
        adapted_config["slang_comfort_level"] = adapted_slang
        adapted_config["cultural_reference_comfort"] = adapted_cultural
        adapted_config["energy_matching_intensity"] = adapted_energy

        return {
            "adapted_config": adapted_config,
            "adaptation_strength": adaptation_strength,
            "changes": {
                "formality": adapted_formality - base_formality,
                "slang": adapted_slang - base_slang,
                "cultural": adapted_cultural - base_cultural,
                "energy": adapted_energy - base_energy,
            },
        }

    def track_phrase_usage(self, messages: List[str]) -> Dict[str, Any]:
        """Identify frequently used phrases/styles"""
        if not messages:
            return {"common_phrases": [], "style_patterns": {}}

        # Extract phrases (2-6 word sequences)
        all_phrases = []
        for message in messages:
            words = message.split()
            for i in range(len(words) - 1):
                for j in range(i + 2, min(i + 7, len(words) + 1)):
                    phrase = " ".join(words[i:j])
                    if len(phrase) > 5:  # Minimum length
                        all_phrases.append(phrase.lower())

        # Count phrase frequency
        phrase_counts = Counter(all_phrases)
        common_phrases = [
            phrase for phrase, count in phrase_counts.most_common(10) if count >= 2
        ]

        # Analyze style patterns
        style_patterns = {
            "uses_contractions": sum(
                1
                for msg in messages
                if any(
                    c in msg.lower() for c in ["'t", "'re", "'ll", "'ve", "'d", "n't"]
                )
            ),
            "uses_emoji": sum(
                1 for msg in messages if any(ord(char) > 127 for char in msg)
            ),
            "uses_caps": sum(
                1
                for msg in messages
                if msg.isupper() or any(c.isupper() for c in msg.split()[:3])
            ),
            "short_messages": sum(1 for msg in messages if len(msg.split()) < 5),
            "long_messages": sum(1 for msg in messages if len(msg.split()) > 20),
        }

        return {
            "common_phrases": common_phrases,
            "style_patterns": style_patterns,
            "total_messages": len(messages),
        }
