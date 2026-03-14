from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Optional

from oricli_core.exceptions import InvalidParameterError


@dataclass(frozen=True)
class AgentProfile:
    """Declarative policy for a task-specific agent."""

    name: str
    description: str = ""
    allowed_modules: list[str] = field(default_factory=list)
    allowed_operations: dict[str, list[str]] = field(default_factory=dict)
    blocked_modules: list[str] = field(default_factory=list)
    blocked_operations: dict[str, list[str]] = field(default_factory=dict)
    system_instructions: str = ""
    model_preference: Optional[str] = None
    task_tags: list[str] = field(default_factory=list)
    skill_overlays: list[str] = field(default_factory=list)

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "AgentProfile":
        return cls(
            name=str(data.get("name", "")).strip(),
            description=str(data.get("description", "")).strip(),
            allowed_modules=[str(module).strip() for module in data.get("allowed_modules", []) if str(module).strip()],
            allowed_operations={
                str(module).strip(): [str(operation).strip() for operation in operations if str(operation).strip()]
                for module, operations in data.get("allowed_operations", {}).items()
                if str(module).strip()
            },
            blocked_modules=[str(module).strip() for module in data.get("blocked_modules", []) if str(module).strip()],
            blocked_operations={
                str(module).strip(): [str(operation).strip() for operation in operations if str(operation).strip()]
                for module, operations in data.get("blocked_operations", {}).items()
                if str(module).strip()
            },
            system_instructions=str(data.get("system_instructions", "")).strip(),
            model_preference=str(data.get("model_preference")).strip() if data.get("model_preference") else None,
            task_tags=[str(tag).strip() for tag in data.get("task_tags", []) if str(tag).strip()],
            skill_overlays=[str(skill).strip() for skill in data.get("skill_overlays", []) if str(skill).strip()],
        )

    def to_dict(self) -> dict[str, Any]:
        return {
            "name": self.name,
            "description": self.description,
            "allowed_modules": list(self.allowed_modules),
            "allowed_operations": {module: list(operations) for module, operations in self.allowed_operations.items()},
            "blocked_modules": list(self.blocked_modules),
            "blocked_operations": {module: list(operations) for module, operations in self.blocked_operations.items()},
            "system_instructions": self.system_instructions,
            "model_preference": self.model_preference,
            "task_tags": list(self.task_tags),
            "skill_overlays": list(self.skill_overlays),
        }


class AgentProfileService:
    """Loads, resolves, and enforces agent execution profiles."""

    def __init__(self, config_path: Optional[Path] = None) -> None:
        self.config_path = config_path or (Path(__file__).resolve().parent.parent / "data" / "agent_profiles.json")
        self.custom_config_path = self.config_path.parent / "custom_profiles.json"
        self._profiles: dict[str, AgentProfile] = {}
        self._custom_profiles: dict[str, AgentProfile] = {}
        self._task_type_profiles: dict[str, str] = {}
        self._agent_type_profiles: dict[str, str] = {}
        self.reload()

    def reload(self) -> None:
        """Reload both built-in and custom profiles from disk."""
        self._profiles = {}
        self._custom_profiles = {}
        
        # 1. Load Built-in Profiles
        if self.config_path.exists():
            with self.config_path.open("r", encoding="utf-8") as handle:
                data = json.load(handle)

            for raw_profile in data.get("profiles", []):
                profile = AgentProfile.from_dict(raw_profile)
                if profile.name:
                    self._profiles[profile.name] = profile

            self._task_type_profiles = {
                str(task_type).strip(): str(profile_name).strip()
                for task_type, profile_name in data.get("task_type_profiles", {}).items()
                if str(task_type).strip() and str(profile_name).strip()
            }
            self._agent_type_profiles = {
                str(agent_type).strip(): str(profile_name).strip()
                for agent_type, profile_name in data.get("agent_type_profiles", {}).items()
                if str(agent_type).strip() and str(profile_name).strip()
            }

        # 2. Load Custom Profiles
        if self.custom_config_path.exists():
            try:
                with self.custom_config_path.open("r", encoding="utf-8") as handle:
                    custom_data = json.load(handle)
                for raw_profile in custom_data.get("profiles", []):
                    profile = AgentProfile.from_dict(raw_profile)
                    if profile.name:
                        self._custom_profiles[profile.name] = profile
                        # Custom profiles can override built-in ones if names collide
                        self._profiles[profile.name] = profile
            except Exception as e:
                logger.error(f"Failed to load custom profiles: {e}")

    def _save_custom_profiles(self) -> None:
        """Persist custom profiles to disk."""
        data = {
            "profiles": [p.to_dict() for p in self._custom_profiles.values()]
        }
        try:
            with self.custom_config_path.open("w", encoding="utf-8") as handle:
                json.dump(data, handle, indent=2)
        except Exception as e:
            logger.error(f"Failed to save custom profiles: {e}")

    def create_profile(self, profile_data: dict[str, Any]) -> dict[str, Any]:
        """Create a new custom agent profile."""
        profile = AgentProfile.from_dict(profile_data)
        if not profile.name:
            raise ValueError("Profile name is required")
            
        self._custom_profiles[profile.name] = profile
        self._profiles[profile.name] = profile
        self._save_custom_profiles()
        return profile.to_dict()

    def update_profile(self, name: str, profile_data: dict[str, Any]) -> dict[str, Any]:
        """Update an existing custom agent profile."""
        if name not in self._custom_profiles:
            # Check if trying to override a built-in
            if name not in self._profiles:
                raise ValueError(f"Profile '{name}' not found")
        
        # Ensure name consistency
        profile_data["name"] = name
        profile = AgentProfile.from_dict(profile_data)
        
        self._custom_profiles[name] = profile
        self._profiles[name] = profile
        self._save_custom_profiles()
        return profile.to_dict()

    def delete_profile(self, name: str) -> bool:
        """Delete a custom agent profile."""
        if name in self._custom_profiles:
            del self._custom_profiles[name]
            self._save_custom_profiles()
            # Reload to properly restore built-in if it was overridden
            self.reload()
            return True
        return False

    def list_profiles(self) -> list[dict[str, Any]]:
        return [profile.to_dict() for profile in self._profiles.values()]

    def get_profile(self, name: str) -> Optional[AgentProfile]:
        return self._profiles.get(name)

    def resolve_profile(
        self,
        *,
        profile_name: Optional[str] = None,
        task_type: Optional[str] = None,
        agent_type: Optional[str] = None,
    ) -> Optional[AgentProfile]:
        resolved_name = profile_name
        if not resolved_name and task_type:
            resolved_name = self._task_type_profiles.get(task_type)
        if not resolved_name and agent_type:
            resolved_name = self._agent_type_profiles.get(agent_type)
        if not resolved_name:
            return None

        profile = self.get_profile(resolved_name)
        if profile is None:
            raise InvalidParameterError("agent_profile", resolved_name, "Profile not found")
        return profile

    def ensure_allowed(self, profile: Optional[AgentProfile], *, module_name: str, operation: str) -> None:
        if profile is None:
            return

        if module_name in profile.blocked_modules:
            raise InvalidParameterError(
                "agent_profile",
                profile.name,
                f"Module '{module_name}' is blocked by the selected profile",
            )

        blocked_operations = profile.blocked_operations.get(module_name, [])
        if operation in blocked_operations or "*" in blocked_operations:
            raise InvalidParameterError(
                "agent_profile",
                profile.name,
                f"Operation '{operation}' on module '{module_name}' is blocked by the selected profile",
            )

        if profile.allowed_modules and module_name not in profile.allowed_modules:
            raise InvalidParameterError(
                "agent_profile",
                profile.name,
                f"Module '{module_name}' is not permitted by the selected profile",
            )

        allowed_operations = profile.allowed_operations.get(module_name)
        if allowed_operations is not None and operation not in allowed_operations:
            raise InvalidParameterError(
                "agent_profile",
                profile.name,
                f"Operation '{operation}' on module '{module_name}' is not permitted by the selected profile",
            )


_SERVICE: Optional[AgentProfileService] = None


def get_agent_profile_service() -> AgentProfileService:
    global _SERVICE
    if _SERVICE is None:
        _SERVICE = AgentProfileService()
    return _SERVICE
