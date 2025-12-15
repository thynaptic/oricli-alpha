"""
Personality Adaptation Service - Service for tracking and adapting personality based on user communication patterns
Converted from Swift PersonalityAdaptationService.swift

DEPRECATED: This module is deprecated. Use universal_voice_engine instead.
The personality-based system has been replaced with a universal voice that adapts contextually.
"""

from typing import Any, Dict, List, Optional
import sys
import time
from pathlib import Path

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent))

from mavaia_core.brain.base_module import BaseBrainModule, ModuleMetadata


class PersonalityAdaptationServiceModule(BaseBrainModule):
    """Service for tracking and adapting personality based on user communication patterns"""

    def __init__(self):
        self._profiles: Dict[str, Dict[str, Any]] = {}
        self._fast_adaptation_alpha = 0.4
        self._gradual_adaptation_alpha = 0.15
        self._fast_adaptation_window = 15

    @property
    def metadata(self) -> ModuleMetadata:
        import warnings
        warnings.warn(
            "personality_adaptation_service module is deprecated. Use universal_voice_engine instead.",
            DeprecationWarning,
            stacklevel=2
        )
        return ModuleMetadata(
            name="personality_adaptation_service",
            version="1.0.0",
            description="[DEPRECATED] Service for tracking and adapting personality based on user communication patterns. Use universal_voice_engine instead.",
            operations=[
                "adapt_to_user",
                "update_personality",
                "get_profile",
                "update_profile",
            ],
            dependencies=[],
            model_required=False,
        )

    def initialize(self) -> bool:
        """Initialize the module"""
        return True

    def execute(self, operation: str, params: Dict[str, Any]) -> Dict[str, Any]:
        """Execute an operation"""
        if operation == "adapt_to_user":
            return self._adapt_to_user(params)
        elif operation == "update_personality":
            return self._update_personality(params)
        elif operation == "get_profile":
            return self._get_profile(params)
        elif operation == "update_profile":
            return self._update_profile(params)
        else:
            raise ValueError(f"Unknown operation: {operation}")

    def _adapt_to_user(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """Adapt personality to user"""
        personality_config = params.get("personality_config", {})
        user_profile = params.get("user_profile", {})
        conversation_context = params.get("conversation_context", [])

        # Get or create profile
        profile = self._get_profile_internal(user_profile.get("user_id", "default"))

        # Adapt configuration based on profile
        adapted_config = personality_config.copy()

        # Adjust formality based on user's formality level
        user_formality = profile.get("formality_level", 0.5)
        base_formality = personality_config.get("formality_baseline", 0.5)
        adapted_config["formality_baseline"] = (base_formality + user_formality) / 2.0

        # Adjust slang usage based on user's slang level
        user_slang = profile.get("slang_usage", 0.5)
        base_slang = personality_config.get("slang_comfort_level", 0.5)
        adapted_config["slang_comfort_level"] = (base_slang + user_slang) / 2.0

        return {
            "success": True,
            "adapted_config": adapted_config,
            "profile": profile,
        }

    def _update_personality(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """Update personality (alias for adapt_to_user)"""
        return self._adapt_to_user(params)

    def _get_profile(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """Get user profile"""
        user_id = params.get("user_id", "default")
        profile = self._get_profile_internal(user_id)

        return {
            "success": True,
            "profile": profile,
        }

    def _update_profile(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """Update profile with new message"""
        user_id = params.get("user_id", "default")
        user_message = params.get("user_message", "")
        conversation_history = params.get("conversation_history", [])

        profile = self._get_profile_internal(user_id)

        # Analyze message
        metrics = self._analyze_message(user_message)

        # Update fast adaptation samples
        profile.setdefault("recent_formality_samples", []).append(metrics["formality"])
        profile.setdefault("recent_slang_samples", []).append(metrics["slang_usage"])
        profile.setdefault("recent_energy_samples", []).append(metrics["energy"])

        # Keep window size limited
        for key in ["recent_formality_samples", "recent_slang_samples", "recent_energy_samples"]:
            samples = profile.get(key, [])
            if len(samples) > self._fast_adaptation_window:
                profile[key] = samples[-self._fast_adaptation_window:]

        # Update gradual adaptation (EMA)
        profile["formality_level"] = self._calculate_ema(
            [metrics["formality"]],
            profile.get("formality_level", 0.5),
            self._gradual_adaptation_alpha,
        )
        profile["slang_usage"] = self._calculate_ema(
            [metrics["slang_usage"]],
            profile.get("slang_usage", 0.5),
            self._gradual_adaptation_alpha,
        )
        profile["average_energy"] = self._calculate_ema(
            [metrics["energy"]],
            profile.get("average_energy", 0.5),
            self._gradual_adaptation_alpha,
        )

        profile["last_updated"] = time.time()
        profile["conversation_count"] = profile.get("conversation_count", 0) + 1

        self._profiles[user_id] = profile

        return {
            "success": True,
            "profile": profile,
        }

    def _get_profile_internal(self, user_id: str) -> Dict[str, Any]:
        """Get or create profile"""
        if user_id in self._profiles:
            return self._profiles[user_id]

        # Create new profile
        profile = {
            "user_id": user_id,
            "formality_level": 0.5,
            "slang_usage": 0.5,
            "average_energy": 0.5,
            "cultural_reference_comfort": 0.5,
            "response_length_preference": 50.0,
            "conversation_count": 0,
            "last_updated": time.time(),
            "recent_formality_samples": [],
            "recent_slang_samples": [],
            "recent_energy_samples": [],
        }

        self._profiles[user_id] = profile
        return profile

    def _analyze_message(self, message: str) -> Dict[str, float]:
        """Analyze message for communication patterns"""
        words = message.lower().split()
        word_count = len(words)

        # Simple heuristics
        formality = 0.5
        slang_usage = 0.0
        energy = 0.5

        # Check for formal language
        formal_words = ["please", "thank you", "would", "could", "should"]
        if any(word in formal_words for word in words):
            formality += 0.2

        # Check for slang
        slang_words = ["yeah", "yep", "nah", "gonna", "wanna", "dunno"]
        if any(word in slang_words for word in words):
            slang_usage += 0.3

        # Check for energy (exclamation marks, caps)
        if "!" in message or any(c.isupper() for c in message[:10]):
            energy += 0.2

        return {
            "formality": min(1.0, max(0.0, formality)),
            "slang_usage": min(1.0, max(0.0, slang_usage)),
            "energy": min(1.0, max(0.0, energy)),
        }

    def _calculate_ema(self, values: List[float], current: float, alpha: float) -> float:
        """Calculate exponential moving average"""
        if not values:
            return current

        result = current
        for value in values:
            result = alpha * value + (1 - alpha) * result

        return result

