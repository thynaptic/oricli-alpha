"""
Personality Builder Service
Service for converting personality builder data to training configuration
Converted from Swift PersonalityBuilderService.swift

DEPRECATED: This module is deprecated. Use universal_voice_engine instead.
The personality-based system has been replaced with a universal voice that adapts contextually.
"""

from typing import Any, Dict, List, Optional
import logging

from mavaia_core.brain.base_module import BaseBrainModule, ModuleMetadata
from mavaia_core.exceptions import InvalidParameterError

logger = logging.getLogger(__name__)

# Optional imports - models package may not be available
try:
    from models.personality_builder_models import PersonalityBuilderData, ToneDescriptor, ResponseStyle
except ImportError:
    # Models not available - define minimal types
    PersonalityBuilderData = None
    ToneDescriptor = None
    ResponseStyle = None


class PersonalityBuilderServiceModule(BaseBrainModule):
    """Service for converting personality builder data to training configuration"""

    def __init__(self):
        super().__init__()

    @property
    def metadata(self) -> ModuleMetadata:
        import warnings
        warnings.warn(
            "personality_builder_service module is deprecated. Use universal_voice_engine instead.",
            DeprecationWarning,
            stacklevel=2
        )
        return ModuleMetadata(
            name="personality_builder_service",
            version="1.0.0",
            description="[DEPRECATED] Service for converting personality builder data to training configuration. Use universal_voice_engine instead.",
            operations=[
                "validate_personality",
                "build_personality",
                "generate_training_config",
                "generate_personality_metadata",
                "generate_dataset_content",
            ],
            dependencies=[],
            model_required=False,
        )

    def initialize(self) -> bool:
        """Initialize the module"""
        return True

    def execute(self, operation: str, params: Dict[str, Any]) -> Dict[str, Any]:
        """Execute an operation"""
        if operation == "validate_personality":
            return self._validate_personality(params)
        elif operation == "build_personality":
            return self._build_personality(params)
        elif operation == "generate_training_config":
            return self._generate_training_config(params)
        elif operation == "generate_personality_metadata":
            return self._generate_personality_metadata(params)
        elif operation == "generate_dataset_content":
            return self._generate_dataset_content(params)
        else:
            raise InvalidParameterError(
                parameter="operation",
                value=operation,
                reason="Unknown operation for personality_builder_service",
            )

    def _validate_personality(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """Validate personality builder data"""
        data_dict = params.get("data", {})
        data = PersonalityBuilderData.from_dict(data_dict)

        errors = []

        if not data.display_name.strip():
            errors.append("Display name is required")

        if not data.keywords:
            errors.append("At least one keyword is required")

        if not data.phrases:
            errors.append("At least one phrase is required")

        if not data.tone_descriptors:
            errors.append("At least one tone descriptor is required")

        return {
            "success": len(errors) == 0,
            "result": {
                "is_valid": len(errors) == 0,
                "errors": errors,
            },
        }

    def _build_personality(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """Build personality (alias for generate_training_config)"""
        return self._generate_training_config(params)

    def _generate_training_config(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """Convert builder data to LoRA training configuration"""
        data_dict = params.get("data", {})
        data = PersonalityBuilderData.from_dict(data_dict)

        # Map tone descriptors to training parameters
        formality_level = self._calculate_formality_level(data.tone_descriptors)
        empathy_level = self._calculate_empathy_level(data.tone_descriptors)
        energy_level = self._calculate_energy_level(data.tone_descriptors)

        # Map response style to max length
        max_length = self._map_response_style_to_max_length(data.response_style)

        # Build training configuration
        personality_id = data.display_name.lower().replace(" ", "_")

        config = {
            "component": "personality_response",
            "personality_id": personality_id,
            "display_name": data.display_name,
            "description": data.description,
            "model": {
                "base_model": "microsoft/DialoGPT-medium",
                "model_type": "causal_lm",
            },
            "dataset": {
                "name": f"personality_{personality_id}",
                "source": "generated",
                "keywords": data.keywords,
                "phrases": data.phrases,
                "preprocessing": {
                    "max_length": 512,
                    "truncation": True,
                },
            },
            "training": {
                "method": "lora",
                "lora_config": {
                    "r": 16,
                    "lora_alpha": 32,
                    "target_modules": ["q_proj", "v_proj"],
                    "qlora": False,
                },
                "hyperparameters": {
                    "num_epochs": 3,
                    "batch_size": 4,
                    "learning_rate": 2e-4,
                    "warmup_steps": 100,
                    "gradient_accumulation_steps": 4,
                },
            },
            "personality_params": {
                "formality_level": formality_level,
                "empathy_intensity": empathy_level,
                "energy_level": energy_level,
                "max_length": max_length,
                "tone_descriptors": [t.value for t in data.tone_descriptors],
                "response_style": data.response_style.value,
            },
            "output": {
                "local_path": f"models/mavaia_personality_{personality_id}",
                "hub_repo": None,
                "push_to_hub": False,
                "private": True,
            },
        }

        return {
            "success": True,
            "result": config,
        }

    def _generate_personality_metadata(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """Generate personality metadata for LoRA adapter"""
        data_dict = params.get("data", {})
        data = PersonalityBuilderData.from_dict(data_dict)

        import time

        metadata = {
            "personality_id": data.display_name.lower().replace(" ", "_"),
            "display_name": data.display_name,
            "description": data.description,
            "icon_name": data.icon_name,
            "keywords": data.keywords,
            "phrases": data.phrases,
            "tone_descriptors": [t.value for t in data.tone_descriptors],
            "response_style": data.response_style.value,
            "created_date": data.created_date,
            "version": data.version,
        }

        return {
            "success": True,
            "result": metadata,
        }

    def _generate_dataset_content(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """Generate dataset content from builder data"""
        data_dict = params.get("data", {})
        data = PersonalityBuilderData.from_dict(data_dict)

        examples = []

        # Generate examples from keywords
        for keyword in data.keywords:
            examples.append(f"User: Tell me about {keyword}")
            examples.append(f"Assistant: {keyword} is interesting because...")

        # Generate examples from phrases
        for phrase in data.phrases:
            examples.append(f"User: How would you respond?")
            examples.append(f"Assistant: {phrase}")

        # Generate examples combining keywords and phrases
        for keyword in data.keywords[:3]:  # Limit to first 3
            for phrase in data.phrases[:2]:  # Limit to first 2
                examples.append(f"User: {keyword}")
                examples.append(f"Assistant: {phrase}")

        return {
            "success": True,
            "result": {
                "examples": examples,
                "count": len(examples),
            },
        }

    def _calculate_formality_level(self, tone_descriptors: List[ToneDescriptor]) -> float:
        """Calculate formality level from tone descriptors"""
        formal_descriptors = {ToneDescriptor.PROFESSIONAL, ToneDescriptor.SERIOUS, ToneDescriptor.ANALYTICAL}
        informal_descriptors = {ToneDescriptor.CASUAL, ToneDescriptor.PLAYFUL, ToneDescriptor.HUMOROUS}

        formal_count = sum(1 for t in tone_descriptors if t in formal_descriptors)
        informal_count = sum(1 for t in tone_descriptors if t in informal_descriptors)

        if formal_count + informal_count == 0:
            return 0.5

        return formal_count / (formal_count + informal_count)

    def _calculate_empathy_level(self, tone_descriptors: List[ToneDescriptor]) -> float:
        """Calculate empathy level from tone descriptors"""
        empathetic_descriptors = {ToneDescriptor.EMPATHETIC, ToneDescriptor.SUPPORTIVE, ToneDescriptor.WARM}

        empathetic_count = sum(1 for t in tone_descriptors if t in empathetic_descriptors)
        total = len(tone_descriptors)

        if total == 0:
            return 0.5

        return empathetic_count / total

    def _calculate_energy_level(self, tone_descriptors: List[ToneDescriptor]) -> float:
        """Calculate energy level from tone descriptors"""
        high_energy_descriptors = {ToneDescriptor.ENERGETIC, ToneDescriptor.PLAYFUL, ToneDescriptor.CREATIVE}
        low_energy_descriptors = {ToneDescriptor.CALM, ToneDescriptor.SERIOUS}

        high_count = sum(1 for t in tone_descriptors if t in high_energy_descriptors)
        low_count = sum(1 for t in tone_descriptors if t in low_energy_descriptors)

        if high_count + low_count == 0:
            return 0.5

        return high_count / (high_count + low_count)

    def _map_response_style_to_max_length(self, response_style: ResponseStyle) -> int:
        """Map response style to max length"""
        mapping = {
            ResponseStyle.SHORT: 50,
            ResponseStyle.CONCISE: 100,
            ResponseStyle.BALANCED: 200,
            ResponseStyle.DETAILED: 400,
            ResponseStyle.VERBOSE: 600,
        }
        return mapping.get(response_style, 200)

