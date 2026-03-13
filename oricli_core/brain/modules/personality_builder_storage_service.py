from __future__ import annotations
"""
Personality Builder Storage Service
Storage service for personality builder plugins and templates
Converted from Swift PersonalityBuilderStorageService.swift

DEPRECATED: This module is deprecated. Use universal_voice_engine instead.
The personality-based system has been replaced with a universal voice that adapts contextually.
"""

from typing import Any, Dict, List, Optional
import json
import os
import time
from pathlib import Path
import logging
from datetime import datetime

from oricli_core.brain.base_module import BaseBrainModule, ModuleMetadata
from oricli_core.exceptions import InvalidParameterError

logger = logging.getLogger(__name__)

# Optional imports - models package may not be available
try:
    from models.personality_builder_models import (
        PersonalityPlugin,
        PersonalityPluginList,
        PersonalityTemplate,
        PersonalityBuilderData,
    )
except ImportError:
    # Models not available - define minimal types
    PersonalityPlugin = None
    PersonalityPluginList = None
    PersonalityTemplate = None
    PersonalityBuilderData = None


class PersonalityBuilderStorageServiceModule(BaseBrainModule):
    """Storage service for personality builder plugins and templates"""

    def __init__(self):
        super().__init__()
        self.plugins: List[Dict[str, Any]] = []
        self.plugins_file_name = "personality_plugins.json"
        self.templates_file_name = "personality_templates.json"
        self._plugins_loaded = False

    @property
    def metadata(self) -> ModuleMetadata:
        import warnings
        warnings.warn(
            "personality_builder_storage_service module is deprecated. Use universal_voice_engine instead.",
            DeprecationWarning,
            stacklevel=2
        )
        return ModuleMetadata(
            name="personality_builder_storage_service",
            version="1.0.0",
            description="[DEPRECATED] Storage service for personality builder plugins and templates. Use universal_voice_engine instead.",
            operations=[
                "load_plugins",
                "save_plugins",
                "store_personality",
                "load_personality",
                "list_personalities",
                "delete_personality",
                "load_templates",
                "save_templates",
            ],
            dependencies=[],
            model_required=False,
        )

    def initialize(self) -> bool:
        """Initialize the module"""
        self._load_plugins()
        return True

    def _get_plugins_path(self) -> Path:
        """Get path to plugins file"""
        # Use current directory or app support directory
        base_dir = Path.home() / "Library" / "Application Support" / "OricliAlphaStandalone" / "PersonalityPlugins"
        base_dir.mkdir(parents=True, exist_ok=True)
        return base_dir / self.plugins_file_name

    def _get_templates_path(self) -> Path:
        """Get path to templates file"""
        base_dir = Path.home() / "Library" / "Application Support" / "OricliAlphaStandalone" / "PersonalityPlugins"
        base_dir.mkdir(parents=True, exist_ok=True)
        return base_dir / self.templates_file_name

    def execute(self, operation: str, params: Dict[str, Any]) -> Dict[str, Any]:
        """Execute an operation"""
        if operation == "load_plugins":
            return self._load_plugins()
        elif operation == "save_plugins":
            return self._save_plugins()
        elif operation == "store_personality":
            return self._store_personality(params)
        elif operation == "load_personality":
            return self._load_personality(params)
        elif operation == "list_personalities":
            return self._list_personalities()
        elif operation == "delete_personality":
            return self._delete_personality(params)
        elif operation == "load_templates":
            return self._load_templates()
        elif operation == "save_templates":
            return self._save_templates(params)
        else:
            raise InvalidParameterError(
                parameter="operation",
                value=operation,
                reason="Unknown operation for personality_builder_storage_service",
            )

    def _load_plugins(self) -> Dict[str, Any]:
        """Load all personality plugins from disk"""
        plugins_path = self._get_plugins_path()

        if not plugins_path.exists():
            self.plugins = []
            self._plugins_loaded = True
            return {
                "success": True,
                "result": {"plugins": [], "count": 0},
            }

        try:
            with open(plugins_path, "r", encoding="utf-8") as f:
                data = json.load(f)
                if PersonalityPluginList is not None:
                    plugin_list = PersonalityPluginList.from_dict(data)
                    self.plugins = [p.to_dict() for p in plugin_list.plugins]
                else:
                    # Fallback for missing models package
                    self.plugins = data.get("plugins", []) if isinstance(data, dict) else []
                self._plugins_loaded = True
                return {
                    "success": True,
                    "result": {
                        "plugins": self.plugins,
                        "count": len(self.plugins),
                    },
                }
        except Exception as e:
            logger.debug(
                "Failed to load plugins; returning empty list",
                exc_info=True,
                extra={"module_name": "personality_builder_storage_service", "error_type": type(e).__name__},
            )
            self.plugins = []
            self._plugins_loaded = True
            return {
                "success": False,
                "error": "Failed to load plugins",
                "result": {"plugins": [], "count": 0},
            }

    def _save_plugins(self) -> Dict[str, Any]:
        """Save all personality plugins to disk"""
        try:
            plugins_path = self._get_plugins_path()
            plugins_path.parent.mkdir(parents=True, exist_ok=True)
            if PersonalityPluginList is not None and PersonalityPlugin is not None:
                plugin_list = PersonalityPluginList(
                    plugins=[PersonalityPlugin.from_dict(p) for p in self.plugins],
                    last_updated=time.time(),
                )
                payload = plugin_list.to_dict()
            else:
                payload = {"plugins": self.plugins, "last_updated": time.time()}

            with open(plugins_path, "w", encoding="utf-8") as f:
                json.dump(payload, f, indent=2, ensure_ascii=False)

            return {
                "success": True,
                "result": {"saved": True, "count": len(self.plugins)},
            }
        except Exception as e:
            logger.debug(
                "Failed to save plugins",
                exc_info=True,
                extra={"module_name": "personality_builder_storage_service", "error_type": type(e).__name__},
            )
            return {
                "success": False,
                "error": "Failed to save plugins",
            }

    def _store_personality(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """Store a personality plugin"""
        plugin_data = params.get("plugin", {})
        if plugin_data is None:
            plugin_data = {}
        if not isinstance(plugin_data, dict):
            raise InvalidParameterError("plugin", str(type(plugin_data).__name__), "plugin must be a dict")

        plugin_id = plugin_data.get("id") or plugin_data.get("builder_data", {}).get("id")
        if PersonalityPlugin is not None:
            plugin = PersonalityPlugin.from_dict(plugin_data)
            plugin_id = plugin.id
            plugin_dict = plugin.to_dict()
        else:
            plugin = None
            plugin_dict = plugin_data
            if not plugin_id:
                raise InvalidParameterError("plugin.id", str(plugin_id), "plugin must include an id")

        # Check if plugin already exists
        existing_idx = next(
            (i for i, p in enumerate(self.plugins) if p.get("id") == plugin_id),
            None
        )

        if existing_idx is not None:
            self.plugins[existing_idx] = plugin_dict
        else:
            self.plugins.append(plugin_dict)

        # Save to disk
        save_result = self._save_plugins()

        return {
            "success": save_result.get("success", True),
            "result": {
                "plugin_id": plugin_id,
                "stored": True,
            },
        }

    def _load_personality(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """Load a personality plugin by ID"""
        personality_id = params.get("personality_id")
        if personality_id is None or not isinstance(personality_id, str) or not personality_id.strip():
            raise InvalidParameterError("personality_id", str(personality_id), "personality_id must be a non-empty string")

        if not self._plugins_loaded:
            self._load_plugins()

        plugin = next(
            (p for p in self.plugins if p.get("builder_data", {}).get("id") == personality_id),
            None
        )

        if not plugin:
            return {
                "success": False,
                "error": f"Personality {personality_id} not found",
            }

        return {
            "success": True,
            "result": {"plugin": plugin},
        }

    def _list_personalities(self) -> Dict[str, Any]:
        """List all personality plugins"""
        if not self._plugins_loaded:
            self._load_plugins()

        return {
            "success": True,
            "result": {
                "plugins": self.plugins,
                "count": len(self.plugins),
            },
        }

    def _delete_personality(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """Delete a personality plugin"""
        personality_id = params.get("personality_id")

        if not self._plugins_loaded:
            self._load_plugins()

        original_count = len(self.plugins)
        self.plugins = [
            p for p in self.plugins
            if p.get("builder_data", {}).get("id") != personality_id
        ]

        if len(self.plugins) < original_count:
            self._save_plugins()
            return {
                "success": True,
                "result": {"deleted": True},
            }
        else:
            return {
                "success": False,
                "error": f"Personality {personality_id} not found",
            }

    def _load_templates(self) -> Dict[str, Any]:
        """Load personality templates"""
        templates_path = self._get_templates_path()

        if not templates_path.exists():
            return {
                "success": True,
                "result": {"templates": [], "count": 0},
            }

        try:
            with open(templates_path, "r", encoding="utf-8") as f:
                data = json.load(f)
                templates = [PersonalityTemplate.from_dict(t) for t in data.get("templates", [])]
                return {
                    "success": True,
                    "result": {
                        "templates": [t.to_dict() for t in templates],
                        "count": len(templates),
                    },
                }
        except Exception as e:
            return {
                "success": False,
                "error": str(e),
                "result": {"templates": [], "count": 0},
            }

    def _save_templates(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """Save personality templates"""
        templates_data = params.get("templates", [])
        templates = [PersonalityTemplate.from_dict(t) for t in templates_data]

        try:
            templates_path = self._get_templates_path()
            templates_path.parent.mkdir(parents=True, exist_ok=True)

            with open(templates_path, "w", encoding="utf-8") as f:
                json.dump(
                    {"templates": [t.to_dict() for t in templates]},
                    f,
                    indent=2,
                    ensure_ascii=False,
                )

            return {
                "success": True,
                "result": {"saved": True, "count": len(templates)},
            }
        except Exception as e:
            return {
                "success": False,
                "error": str(e),
            }

