"""
State Manager Module - Comprehensive state tracking and management
Tracks conversation state, task state, user context state, and session state
with persistence, transitions, and intelligent merging
"""

from pathlib import Path
from typing import Any, Dict, List, Optional
from dataclasses import dataclass, asdict
from datetime import datetime, timedelta
import json
import sys
import uuid

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent))

from mavaia_core.brain.base_module import BaseBrainModule, ModuleMetadata


@dataclass
class StateTransition:
    """Represents a state transition with metadata"""

    from_state: str
    to_state: str
    timestamp: str
    reason: str
    metadata: Dict[str, Any]


@dataclass
class StateSnapshot:
    """Represents a state snapshot at a point in time"""

    state_id: str
    state_type: str
    state_data: Dict[str, Any]
    timestamp: str
    version: int


class StateManagerModule(BaseBrainModule):
    """Manage state tracking, persistence, transitions, and queries"""

    def __init__(self):
        self.state_storage_path = Path(__file__).parent.parent / "state_storage"
        self.state_storage_path.mkdir(parents=True, exist_ok=True)
        self.state_cache: Dict[str, Dict[str, Any]] = {}
        self.transition_history: Dict[str, List[StateTransition]] = {}
        self.snapshots: Dict[str, List[StateSnapshot]] = {}

    @property
    def metadata(self) -> ModuleMetadata:
        return ModuleMetadata(
            name="state_manager",
            version="1.0.0",
            description=(
                "State tracking and management: conversation state, task state, "
                "user context state, session state with persistence and transitions"
            ),
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
        """Initialize the module and load persisted state"""
        try:
            self._load_persisted_state()
            return True
        except Exception as e:
            print(
                f"[StateManagerModule] Failed to load persisted state: {e}",
                file=sys.stderr,
            )
            return True  # Continue even if loading fails

    def execute(self, operation: str, params: Dict[str, Any]) -> Dict[str, Any]:
        """Execute a state management operation"""
        match operation:
            case "get_state":
                state_type = params.get("state_type", "conversation")
                state_id = params.get("state_id")
                return self.get_state(state_type, state_id)

            case "update_state":
                state_type = params.get("state_type", "conversation")
                state_id = params.get("state_id")
                state_data = params.get("state_data", {})
                return self.update_state(state_type, state_id, state_data)

            case "transition_state":
                state_type = params.get("state_type", "conversation")
                state_id = params.get("state_id")
                from_state = params.get("from_state")
                to_state = params.get("to_state")
                reason = params.get("reason", "State transition")
                metadata = params.get("metadata", {})
                return self.transition_state(
                    state_type, state_id, from_state, to_state, reason, metadata
                )

            case "merge_states":
                state_type = params.get("state_type", "conversation")
                state_ids = params.get("state_ids", [])
                return self.merge_states(state_type, state_ids)

            case "get_state_history":
                state_type = params.get("state_type", "conversation")
                state_id = params.get("state_id")
                limit = params.get("limit", 50)
                return self.get_state_history(state_type, state_id, limit)

            case "create_snapshot":
                state_type = params.get("state_type", "conversation")
                state_id = params.get("state_id")
                return self.create_snapshot(state_type, state_id)

            case "restore_snapshot":
                state_type = params.get("state_type", "conversation")
                state_id = params.get("state_id")
                snapshot_id = params.get("snapshot_id")
                return self.restore_snapshot(state_type, state_id, snapshot_id)

            case _:
                raise ValueError(f"Unknown operation: {operation}")

    def get_state(
        self, state_type: str, state_id: Optional[str] = None
    ) -> Dict[str, Any]:
        """Get current state for a state type and optional state ID"""
        if state_id:
            cache_key = f"{state_type}:{state_id}"
            if cache_key in self.state_cache:
                return {
                    "state_type": state_type,
                    "state_id": state_id,
                    "state_data": self.state_cache[cache_key],
                    "found": True,
                }
            # Try to load from persistence
            persisted = self._load_state_from_file(state_type, state_id)
            if persisted:
                self.state_cache[cache_key] = persisted
                return {
                    "state_type": state_type,
                    "state_id": state_id,
                    "state_data": persisted,
                    "found": True,
                }
            return {
                "state_type": state_type,
                "state_id": state_id,
                "state_data": {},
                "found": False,
            }
        else:
            # Return all states of this type
            states = {}
            for key, value in self.state_cache.items():
                if key.startswith(f"{state_type}:"):
                    state_id_from_key = key.split(":", 1)[1]
                    states[state_id_from_key] = value
            return {
                "state_type": state_type,
                "states": states,
                "count": len(states),
            }

    def update_state(
        self,
        state_type: str,
        state_id: Optional[str],
        state_data: Dict[str, Any],
    ) -> Dict[str, Any]:
        """Update state data for a state type and ID"""
        if not state_id:
            state_id = str(uuid.uuid4())

        cache_key = f"{state_type}:{state_id}"

        # Merge with existing state if it exists
        if cache_key in self.state_cache:
            existing = self.state_cache[cache_key]
            existing.update(state_data)
            state_data = existing
        else:
            # Initialize with defaults
            state_data.setdefault("created_at", datetime.now().isoformat())
            state_data.setdefault("version", 1)

        state_data["updated_at"] = datetime.now().isoformat()
        state_data["version"] = state_data.get("version", 0) + 1

        self.state_cache[cache_key] = state_data
        self._persist_state(state_type, state_id, state_data)

        return {
            "state_type": state_type,
            "state_id": state_id,
            "state_data": state_data,
            "updated": True,
        }

    def transition_state(
        self,
        state_type: str,
        state_id: Optional[str],
        from_state: Optional[str],
        to_state: str,
        reason: str = "State transition",
        metadata: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """Transition state from one value to another"""
        if not state_id:
            state_id = str(uuid.uuid4())

        if metadata is None:
            metadata = {}

        cache_key = f"{state_type}:{state_id}"
        current_state = self.state_cache.get(cache_key, {})

        # Get current state value if from_state not provided
        if from_state is None:
            from_state = current_state.get("current_state", "initial")

        # Create transition record
        transition = StateTransition(
            from_state=from_state,
            to_state=to_state,
            timestamp=datetime.now().isoformat(),
            reason=reason,
            metadata=metadata,
        )

        # Store transition history
        if cache_key not in self.transition_history:
            self.transition_history[cache_key] = []
        self.transition_history[cache_key].append(transition)

        # Update state
        current_state["current_state"] = to_state
        current_state["last_transition"] = asdict(transition)
        current_state["updated_at"] = datetime.now().isoformat()

        self.state_cache[cache_key] = current_state
        self._persist_state(state_type, state_id, current_state)
        self._persist_transitions(state_type, state_id)

        return {
            "state_type": state_type,
            "state_id": state_id,
            "transition": asdict(transition),
            "current_state": to_state,
            "success": True,
        }

    def merge_states(
        self, state_type: str, state_ids: List[str]
    ) -> Dict[str, Any]:
        """Merge multiple states into one"""
        if not state_ids:
            return {"error": "No state IDs provided", "merged": False}

        merged_state: Dict[str, Any] = {
            "merged_from": state_ids,
            "merged_at": datetime.now().isoformat(),
            "version": 1,
        }

        # Merge all states
        for state_id in state_ids:
            cache_key = f"{state_type}:{state_id}"
            if cache_key in self.state_cache:
                state_data = self.state_cache[cache_key]
                # Merge intelligently (prefer newer values, combine lists, etc.)
                for key, value in state_data.items():
                    if key in ["created_at", "updated_at", "version"]:
                        continue
                    if key not in merged_state:
                        merged_state[key] = value
                    elif isinstance(value, list) and isinstance(
                        merged_state.get(key), list
                    ):
                        # Combine lists
                        merged_state[key] = list(
                            set(merged_state[key] + value)
                        )
                    elif isinstance(value, dict) and isinstance(
                        merged_state.get(key), dict
                    ):
                        # Merge dicts
                        merged_state[key].update(value)
                    else:
                        # Prefer newer value (based on updated_at if available)
                        existing_updated = merged_state.get("updated_at", "")
                        new_updated = state_data.get("updated_at", "")
                        if new_updated > existing_updated:
                            merged_state[key] = value

        # Create new merged state ID
        merged_id = str(uuid.uuid4())
        cache_key = f"{state_type}:{merged_id}"
        self.state_cache[cache_key] = merged_state
        self._persist_state(state_type, merged_id, merged_state)

        return {
            "state_type": state_type,
            "merged_id": merged_id,
            "merged_state": merged_state,
            "merged_from": state_ids,
            "success": True,
        }

    def get_state_history(
        self, state_type: str, state_id: str, limit: int = 50
    ) -> Dict[str, Any]:
        """Get transition history for a state"""
        cache_key = f"{state_type}:{state_id}"
        transitions = self.transition_history.get(cache_key, [])

        # Load from persistence if not in cache
        if not transitions:
            transitions = self._load_transitions_from_file(state_type, state_id)
            if transitions:
                self.transition_history[cache_key] = transitions

        # Sort by timestamp (newest first) and limit
        transitions_sorted = sorted(
            transitions, key=lambda t: t.timestamp, reverse=True
        )[:limit]

        return {
            "state_type": state_type,
            "state_id": state_id,
            "transitions": [asdict(t) for t in transitions_sorted],
            "count": len(transitions_sorted),
        }

    def create_snapshot(
        self, state_type: str, state_id: str
    ) -> Dict[str, Any]:
        """Create a snapshot of current state"""
        cache_key = f"{state_type}:{state_id}"
        state_data = self.state_cache.get(cache_key, {})

        if not state_data:
            # Try to load from persistence
            state_data = self._load_state_from_file(state_type, state_id)
            if not state_data:
                return {
                    "error": "State not found",
                    "snapshot_id": None,
                    "success": False,
                }

        snapshot = StateSnapshot(
            state_id=state_id,
            state_type=state_type,
            state_data=state_data.copy(),
            timestamp=datetime.now().isoformat(),
            version=state_data.get("version", 1),
        )

        # Store snapshot
        if cache_key not in self.snapshots:
            self.snapshots[cache_key] = []
        self.snapshots[cache_key].append(snapshot)

        # Persist snapshot
        self._persist_snapshot(state_type, state_id, snapshot)

        return {
            "state_type": state_type,
            "state_id": state_id,
            "snapshot_id": snapshot.state_id,
            "snapshot": asdict(snapshot),
            "success": True,
        }

    def restore_snapshot(
        self, state_type: str, state_id: str, snapshot_id: str
    ) -> Dict[str, Any]:
        """Restore state from a snapshot"""
        cache_key = f"{state_type}:{state_id}"

        # Find snapshot
        snapshots = self.snapshots.get(cache_key, [])
        if not snapshots:
            snapshots = self._load_snapshots_from_file(state_type, state_id)
            if snapshots:
                self.snapshots[cache_key] = snapshots

        snapshot = next(
            (s for s in snapshots if s.state_id == snapshot_id), None
        )

        if not snapshot:
            return {
                "error": "Snapshot not found",
                "restored": False,
            }

        # Restore state
        self.state_cache[cache_key] = snapshot.state_data.copy()
        self._persist_state(state_type, state_id, snapshot.state_data)

        return {
            "state_type": state_type,
            "state_id": state_id,
            "snapshot_id": snapshot_id,
            "restored_state": snapshot.state_data,
            "restored": True,
        }

    def _persist_state(
        self, state_type: str, state_id: str, state_data: Dict[str, Any]
    ) -> None:
        """Persist state to file"""
        try:
            state_dir = self.state_storage_path / state_type
            state_dir.mkdir(parents=True, exist_ok=True)
            state_file = state_dir / f"{state_id}.json"

            with open(state_file, "w", encoding="utf-8") as f:
                json.dump(state_data, f, indent=2, ensure_ascii=False)
        except Exception as e:
            print(
                f"[StateManagerModule] Failed to persist state: {e}",
                file=sys.stderr,
            )

    def _load_state_from_file(
        self, state_type: str, state_id: str
    ) -> Optional[Dict[str, Any]]:
        """Load state from file"""
        try:
            state_file = (
                self.state_storage_path / state_type / f"{state_id}.json"
            )
            if state_file.exists():
                with open(state_file, "r", encoding="utf-8") as f:
                    return json.load(f)
        except Exception as e:
            print(
                f"[StateManagerModule] Failed to load state: {e}",
                file=sys.stderr,
            )
        return None

    def _load_persisted_state(self) -> None:
        """Load all persisted states into cache"""
        try:
            if not self.state_storage_path.exists():
                return

            for state_type_dir in self.state_storage_path.iterdir():
                if not state_type_dir.is_dir():
                    continue

                state_type = state_type_dir.name
                for state_file in state_type_dir.glob("*.json"):
                    state_id = state_file.stem
                    cache_key = f"{state_type}:{state_id}"
                    state_data = self._load_state_from_file(state_type, state_id)
                    if state_data:
                        self.state_cache[cache_key] = state_data
        except Exception as e:
            print(
                f"[StateManagerModule] Failed to load persisted state: {e}",
                file=sys.stderr,
            )

    def _persist_transitions(
        self, state_type: str, state_id: str
    ) -> None:
        """Persist transition history to file"""
        try:
            cache_key = f"{state_type}:{state_id}"
            transitions = self.transition_history.get(cache_key, [])

            transitions_dir = self.state_storage_path / "transitions" / state_type
            transitions_dir.mkdir(parents=True, exist_ok=True)
            transitions_file = transitions_dir / f"{state_id}.json"

            transitions_data = [asdict(t) for t in transitions]

            with open(transitions_file, "w", encoding="utf-8") as f:
                json.dump(transitions_data, f, indent=2, ensure_ascii=False)
        except Exception as e:
            print(
                f"[StateManagerModule] Failed to persist transitions: {e}",
                file=sys.stderr,
            )

    def _load_transitions_from_file(
        self, state_type: str, state_id: str
    ) -> List[StateTransition]:
        """Load transition history from file"""
        try:
            transitions_file = (
                self.state_storage_path
                / "transitions"
                / state_type
                / f"{state_id}.json"
            )
            if transitions_file.exists():
                with open(transitions_file, "r", encoding="utf-8") as f:
                    transitions_data = json.load(f)
                    return [
                        StateTransition(**t) for t in transitions_data
                    ]
        except Exception as e:
            print(
                f"[StateManagerModule] Failed to load transitions: {e}",
                file=sys.stderr,
            )
        return []

    def _persist_snapshot(
        self, state_type: str, state_id: str, snapshot: StateSnapshot
    ) -> None:
        """Persist snapshot to file"""
        try:
            snapshots_dir = (
                self.state_storage_path / "snapshots" / state_type
            )
            snapshots_dir.mkdir(parents=True, exist_ok=True)
            snapshots_file = snapshots_dir / f"{state_id}.json"

            # Load existing snapshots
            snapshots = []
            if snapshots_file.exists():
                with open(snapshots_file, "r", encoding="utf-8") as f:
                    snapshots_data = json.load(f)
                    snapshots = [StateSnapshot(**s) for s in snapshots_data]

            # Add new snapshot
            snapshots.append(snapshot)

            # Persist all snapshots
            snapshots_data = [asdict(s) for s in snapshots]
            with open(snapshots_file, "w", encoding="utf-8") as f:
                json.dump(snapshots_data, f, indent=2, ensure_ascii=False)
        except Exception as e:
            print(
                f"[StateManagerModule] Failed to persist snapshot: {e}",
                file=sys.stderr,
            )

    def _load_snapshots_from_file(
        self, state_type: str, state_id: str
    ) -> List[StateSnapshot]:
        """Load snapshots from file"""
        try:
            snapshots_file = (
                self.state_storage_path
                / "snapshots"
                / state_type
                / f"{state_id}.json"
            )
            if snapshots_file.exists():
                with open(snapshots_file, "r", encoding="utf-8") as f:
                    snapshots_data = json.load(f)
                    return [StateSnapshot(**s) for s in snapshots_data]
        except Exception as e:
            print(
                f"[StateManagerModule] Failed to load snapshots: {e}",
                file=sys.stderr,
            )
        return []

    def validate_params(self, operation: str, params: Dict[str, Any]) -> bool:
        """Validate parameters for operations"""
        match operation:
            case "get_state" | "create_snapshot":
                return "state_type" in params
            case "update_state" | "transition_state":
                return "state_type" in params and "state_data" in params or "to_state" in params
            case "merge_states":
                return "state_type" in params and "state_ids" in params
            case "get_state_history" | "restore_snapshot":
                return (
                    "state_type" in params
                    and "state_id" in params
                )
            case _:
                return True


# Module export
def create_module():
    return StateManagerModule()

