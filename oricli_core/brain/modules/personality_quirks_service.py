from __future__ import annotations
"""
Personality Quirks Service - Manages Oricli-Alpha's personality quirks, signature phrases, and response style
Converted from Swift PersonalityQuirksService.swift

DEPRECATED: This module is deprecated. Use universal_voice_engine instead.
The personality-based system has been replaced with a universal voice that adapts contextually.
"""

from typing import Any, Dict, List, Optional
import logging

from oricli_core.brain.base_module import BaseBrainModule, ModuleMetadata
from oricli_core.brain.registry import ModuleRegistry
from oricli_core.exceptions import InvalidParameterError

logger = logging.getLogger(__name__)
try:
    from models.personality_models import PersonalityConfiguration
except ImportError:
    # Models not available - define minimal types
    PersonalityConfiguration = None


class PersonalityQuirksServiceModule(BaseBrainModule):
    """Manages Oricli-Alpha's personality quirks, signature phrases, and response style"""

    def __init__(self):
        super().__init__()
        self.personality_adaptation = None
        self._modules_loaded = False

    @property
    def metadata(self) -> ModuleMetadata:
        import warnings
        warnings.warn(
            "personality_quirks_service module is deprecated. Use universal_voice_engine instead.",
            DeprecationWarning,
            stacklevel=2
        )
        return ModuleMetadata(
            name="personality_quirks_service",
            version="1.0.0",
            description="[DEPRECATED] Manages Oricli-Alpha's personality quirks, signature phrases, and response style. Use universal_voice_engine instead.",
            operations=[
                "apply_quirks",
                "adapt_personality",
                "build_instructions",
                "get_personality_tone",
            ],
            dependencies=[],
            model_required=False,
        )

    def initialize(self) -> bool:
        """Initialize the module"""
        return True

    def _ensure_modules_loaded(self):
        """Lazy load dependent modules"""
        if self._modules_loaded:
            return

        try:
            self.personality_adaptation = ModuleRegistry.get_module("personality_adaptation_service")

            self._modules_loaded = True
        except Exception as e:
            # Modules not available - will use fallback methods
            logger.debug(
                "Failed to load optional dependency module for personality_quirks_service",
                exc_info=True,
                extra={"module_name": "personality_quirks_service", "error_type": type(e).__name__},
            )

    def execute(self, operation: str, params: Dict[str, Any]) -> Dict[str, Any]:
        """Execute an operation"""
        self._ensure_modules_loaded()

        if operation == "apply_quirks":
            return self._apply_quirks(params)
        elif operation == "adapt_personality":
            return self._adapt_personality(params)
        elif operation == "build_instructions":
            return self._build_instructions(params)
        elif operation == "get_personality_tone":
            return self._get_personality_tone(params)
        else:
            raise InvalidParameterError(
                parameter="operation",
                value=operation,
                reason="Unknown operation for personality_quirks_service",
            )

    def _apply_quirks(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """Apply personality quirks to response"""
        response = params.get("response", "")
        personality_config = params.get("personality_config", {})
        tone_context = params.get("tone_context", {})

        # In full implementation, would apply personality-specific quirks
        # For now, return response as-is
        return {
            "success": True,
            "response": response,
            "quirks_applied": [],
        }

    def _adapt_personality(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """Adapt personality based on context"""
        personality_config = params.get("personality_config", {})
        user_profile = params.get("user_profile", {})
        conversation_context = params.get("conversation_context", [])

        if self.personality_adaptation:
            try:
                return self.personality_adaptation.execute("adapt_to_user", {
                    "personality_config": personality_config,
                    "user_profile": user_profile,
                    "conversation_context": conversation_context,
                })
            except Exception as e:
                logger.debug(
                    "personality_adaptation_service adapt_to_user failed; using unadapted config",
                    exc_info=True,
                    extra={"module_name": "personality_quirks_service", "error_type": type(e).__name__},
                )

        # Fallback: return config as-is
        return {
            "success": True,
            "adapted_config": personality_config,
        }

    def _build_instructions(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """Build personality instructions"""
        personality_config = params.get("personality_config", {})
        tone_context = params.get("tone_context", {})
        slang = params.get("slang")
        cultural = params.get("cultural")
        emotion = params.get("emotion")

        personality_id = personality_config.get("personality_id", "big_sister")
        emotional_response_style = personality_config.get("emotional_response_style", "supportive")
        sass_factor = personality_config.get("default_sass_factor", 0.3)

        # Build instruction sections
        sections = []

        # Core personality description
        sections.append(f"**{personality_id.upper()} PERSONALITY CORE:**")
        sections.append(f"- Emotional response style: {emotional_response_style}")
        sections.append(f"- Sass factor: {sass_factor:.2f}")

        # Add slang/cultural/emotion instructions if provided
        if slang:
            sections.append(f"- Slang usage: {slang.get('detected', False)}")
        if cultural:
            sections.append(f"- Cultural references: {cultural.get('detected', False)}")
        if emotion:
            sections.append(f"- Emotional state: {emotion.get('primary_emotion', 'neutral')}")

        instructions = "\n".join(sections)

        return {
            "success": True,
            "instructions": instructions,
        }

    def _get_personality_tone(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """Get personality tone context"""
        personality_config = params.get("personality_config", {})
        user_energy = params.get("user_energy", 0.5)

        energy_band = "moderate"
        if user_energy < 0.3:
            energy_band = "low"
        elif user_energy > 0.7:
            energy_band = "high"

        return {
            "success": True,
            "tone_context": {
                "energy_band": energy_band,
                "conversation_tempo": "balanced",
                "emotional_friction": "steady",
                "dominant_cue": "neutral",
                "sass_factor": personality_config.get("default_sass_factor", 0.3),
                "is_casual_chat": False,
                "user_energy": user_energy,
            },
        }

