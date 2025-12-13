"""
Personality Configuration Loader
Loads personality configurations from JSON files for extensible personality system
Converted from Swift PersonalityConfigurationLoader.swift
"""

from typing import Any, Dict, Optional
import sys
import json
import time
from pathlib import Path

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent))

from mavaia_core.brain.base_module import BaseBrainModule, ModuleMetadata

# Optional imports - models package may not be available
try:
    from models.personality_models import PersonalityConfiguration, PersonalityConfigurations
except ImportError:
    # Models not available - define minimal types
    PersonalityConfiguration = None
    PersonalityConfigurations = None


class PersonalityConfigurationLoaderModule(BaseBrainModule):
    """Loads personality configurations from JSON files"""

    def __init__(self):
        self.cached_configurations: Optional[Dict[str, Any]] = None
        self.last_load_time: float = 0.0
        self.cache_ttl = 300.0  # 5 minutes

    @property
    def metadata(self) -> ModuleMetadata:
        return ModuleMetadata(
            name="personality_configuration_loader",
            version="1.0.0",
            description="Loads personality configurations from JSON files for extensible personality system",
            operations=[
                "load_configurations",
                "get_configuration",
                "validate_configuration",
            ],
            dependencies=[],
            model_required=False,
        )

    def initialize(self) -> bool:
        """Initialize the module"""
        return True

    def execute(self, operation: str, params: Dict[str, Any]) -> Dict[str, Any]:
        """Execute an operation"""
        if operation == "load_configurations":
            return self._load_configurations()
        elif operation == "get_configuration":
            return self._get_configuration(params)
        elif operation == "validate_configuration":
            return self._validate_configuration(params)
        else:
            raise ValueError(f"Unknown operation: {operation}")

    def _load_configurations(self) -> Dict[str, Any]:
        """Load personality configurations from JSON file"""
        # Check cache first
        if (
            self.cached_configurations
            and time.time() - self.last_load_time < self.cache_ttl
        ):
            return {
                "success": True,
                "result": self.cached_configurations,
            }

        # Try to load from enhanced config file
        enhanced_config = self._load_enhanced_configurations()
        if enhanced_config:
            self.cached_configurations = enhanced_config
            self.last_load_time = time.time()
            return {
                "success": True,
                "result": enhanced_config,
            }

        # Fallback: Generate default configurations
        default_configs = self._generate_default_configurations()
        self.cached_configurations = default_configs
        self.last_load_time = time.time()
        return {
            "success": True,
            "result": default_configs,
        }

    def _load_enhanced_configurations(self) -> Optional[Dict[str, Any]]:
        """Load configurations from enhanced JSON file"""
        # Try to find the enhanced config file
        app_support = Path.home() / "Library" / "Application Support" / "MavaiaStandalone"
        config_path = app_support / "personality_config_enhanced.json"

        if config_path.exists():
            try:
                with open(config_path, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    return data
            except Exception:
                pass

        # Try in current directory
        local_config = Path("personality_config_enhanced.json")
        if local_config.exists():
            try:
                with open(local_config, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    return data
            except Exception:
                pass

        return None

    def _generate_default_configurations(self) -> Dict[str, Any]:
        """Generate default configurations for all personalities"""
        # Return empty dict - default configs are generated in PersonalityConfiguration.default()
        return {
            "personalities": {},
        }

    def _get_configuration(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """Get configuration for a specific personality"""
        personality_id = params.get("personality_id")

        # Load configurations
        configs_result = self._load_configurations()
        configs_data = configs_result.get("result", {})

        # Get configuration for personality
        personalities = configs_data.get("personalities", {})
        config_data = personalities.get(personality_id)

        if config_data:
            return {
                "success": True,
                "result": config_data,
            }
        else:
            # Return default configuration
            return {
                "success": True,
                "result": self._get_default_config(personality_id),
            }

    def _get_default_config(self, personality_id: Optional[str]) -> Dict[str, Any]:
        """Get default configuration for a personality"""
        # This matches the default() method in PersonalityConfiguration
        # Return a basic default config
        return {
            "personality_id": personality_id or "big_sister",
            "slang_comfort_level": 0.5,
            "cultural_reference_comfort": 0.5,
            "emotional_response_style": "supportive",
            "empathy_intensity": 0.7,
            "formality_baseline": 0.5,
            "sass_factor_range": {"min": 0.1, "max": 0.5},
            "mode_blending": ["warm", "supportive"],
            "default_sass_factor": 0.3,
            "energy_matching_intensity": 0.7,
            "slang_usage_threshold": 0.5,
            "cultural_reference_threshold": 0.5,
            "crisis_resource_enabled": True,
            "safe_completions_style": "supportive",
        }

    def _validate_configuration(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """Validate a personality configuration"""
        config_data = params.get("configuration", {})

        errors = []

        # Check required fields
        required_fields = [
            "personality_id",
            "slang_comfort_level",
            "cultural_reference_comfort",
            "emotional_response_style",
            "empathy_intensity",
            "formality_baseline",
        ]

        for field in required_fields:
            if field not in config_data:
                errors.append(f"Missing required field: {field}")

        # Validate ranges
        if "slang_comfort_level" in config_data:
            level = config_data["slang_comfort_level"]
            if not isinstance(level, (int, float)) or not (0.0 <= level <= 1.0):
                errors.append("slang_comfort_level must be between 0.0 and 1.0")

        if "empathy_intensity" in config_data:
            intensity = config_data["empathy_intensity"]
            if not isinstance(intensity, (int, float)) or not (0.0 <= intensity <= 1.0):
                errors.append("empathy_intensity must be between 0.0 and 1.0")

        return {
            "success": len(errors) == 0,
            "result": {
                "is_valid": len(errors) == 0,
                "errors": errors,
            },
        }

