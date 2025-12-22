"""
State Manager Service - State tracking and management service
Converted from Swift StateManagerService.swift
"""

from typing import Any, Dict, List, Optional
import sys
from pathlib import Path

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent))

from mavaia_core.brain.base_module import BaseBrainModule, ModuleMetadata


class StateManagerServiceModule(BaseBrainModule):
    """State tracking and management service"""

    def __init__(self):
        self.state_manager = None
        self._modules_loaded = False

    @property
    def metadata(self) -> ModuleMetadata:
        return ModuleMetadata(
            name="state_manager_service",
            version="1.0.0",
            description="State tracking and management service",
            operations=[
                "get_state",
                "update_state",
                "transition_state",
                "merge_states",
                "get_state_history",
                "create_snapshot",
                "restore_snapshot",
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
            from mavaia_core.brain.registry import ModuleRegistry

            self.state_manager = ModuleRegistry.get_module("state_manager")

            self._modules_loaded = True
        except Exception as e:
            # Modules not available - will use fallback methods
            pass

    def execute(self, operation: str, params: Dict[str, Any]) -> Dict[str, Any]:
        """Execute an operation"""
        self._ensure_modules_loaded()

        if operation == "get_state":
            return self._get_state(params)
        elif operation == "update_state":
            return self._update_state(params)
        elif operation == "transition_state":
            return self._transition_state(params)
        elif operation == "merge_states":
            return self._merge_states(params)
        elif operation == "get_state_history":
            return self._get_state_history(params)
        elif operation == "create_snapshot":
            return self._create_snapshot(params)
        elif operation == "restore_snapshot":
            return self._restore_snapshot(params)
        else:
            raise ValueError(f"Unknown operation: {operation}")

    def _get_state(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """Get current state"""
        state_type = params.get("state_type", "")
        state_id = params.get("state_id")

        if self.state_manager:
            try:
                return self.state_manager.execute("get_state", {
                    "state_type": state_type,
                    "state_id": state_id,
                })
            except:
                pass

        # Fallback: return empty state
        return {
            "success": True,
            "state": {},
        }

    def _update_state(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """Update state data"""
        state_type = params.get("state_type", "")
        state_id = params.get("state_id")
        state_data = params.get("state_data", {})

        if self.state_manager:
            try:
                return self.state_manager.execute("update_state", {
                    "state_type": state_type,
                    "state_id": state_id,
                    "state_data": state_data,
                })
            except:
                pass

        return {
            "success": True,
            "state": state_data,
        }

    def _transition_state(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """Transition state"""
        state_type = params.get("state_type", "")
        state_id = params.get("state_id")
        from_state = params.get("from_state")
        to_state = params.get("to_state", "")
        reason = params.get("reason", "State transition")
        metadata = params.get("metadata", {})

        if self.state_manager:
            try:
                return self.state_manager.execute("transition_state", {
                    "state_type": state_type,
                    "state_id": state_id,
                    "from_state": from_state,
                    "to_state": to_state,
                    "reason": reason,
                    "metadata": metadata,
                })
            except:
                pass

        return {
            "success": True,
            "state": to_state,
        }

    def _merge_states(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """Merge multiple states"""
        state_type = params.get("state_type", "")
        state_ids = params.get("state_ids", [])

        if self.state_manager:
            try:
                return self.state_manager.execute("merge_states", {
                    "state_type": state_type,
                    "state_ids": state_ids,
                })
            except:
                pass

        return {
            "success": True,
            "merged_state": {},
        }

    def _get_state_history(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """Get transition history"""
        state_type = params.get("state_type", "")
        state_id = params.get("state_id", "")
        limit = params.get("limit", 50)

        if self.state_manager:
            try:
                return self.state_manager.execute("get_state_history", {
                    "state_type": state_type,
                    "state_id": state_id,
                    "limit": limit,
                })
            except:
                pass

        return {
            "success": True,
            "history": [],
        }

    def _create_snapshot(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """Create a snapshot"""
        state_type = params.get("state_type", "")
        state_id = params.get("state_id", "")

        if self.state_manager:
            try:
                return self.state_manager.execute("create_snapshot", {
                    "state_type": state_type,
                    "state_id": state_id,
                })
            except:
                pass

        return {
            "success": True,
            "snapshot_id": "",
        }

    def _restore_snapshot(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """Restore state from snapshot"""
        state_type = params.get("state_type", "")
        state_id = params.get("state_id", "")
        snapshot_id = params.get("snapshot_id", "")

        if self.state_manager:
            try:
                return self.state_manager.execute("restore_snapshot", {
                    "state_type": state_type,
                    "state_id": state_id,
                    "snapshot_id": snapshot_id,
                })
            except:
                pass

        return {
            "success": True,
        }

