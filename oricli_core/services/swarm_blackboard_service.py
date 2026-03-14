from __future__ import annotations

import json
import threading
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional


class SwarmBlackboardService:
    """Persist collaborative swarm sessions and shared blackboard state."""

    def __init__(self, sessions_dir: Optional[Path] = None) -> None:
        resolved_sessions_dir = sessions_dir or (Path(__file__).resolve().parent.parent / "data" / "swarm_sessions")
        self.sessions_dir = Path(resolved_sessions_dir)
        self.sessions_dir.mkdir(parents=True, exist_ok=True)
        self._write_lock = threading.Lock()

    def _session_path(self, session_id: str) -> Path:
        return self.sessions_dir / f"{session_id}.json"

    def _now(self) -> str:
        return datetime.now(timezone.utc).isoformat()

    def create_session(
        self,
        *,
        query: str,
        participants: List[Dict[str, Any]],
        shared_state: Optional[Dict[str, Any]] = None,
        message_log: Optional[List[Dict[str, Any]]] = None,
        metadata: Optional[Dict[str, Any]] = None,
        session_id: Optional[str] = None,
    ) -> Dict[str, Any]:
        resolved_session_id = session_id or str(uuid.uuid4())[:12]
        state = {
            "session_id": resolved_session_id,
            "query": query,
            "participants": participants,
            "shared_state": dict(shared_state or {}),
            "message_log": list(message_log or []),
            "contributions": [],
            "reviews": [],
            "rounds": [],
            "status": "active",
            "metadata": dict(metadata or {}),
            "created_at": self._now(),
            "updated_at": self._now(),
            "final_consensus": None,
        }
        self.save_session(state)
        return state

    def save_session(self, state: Dict[str, Any]) -> None:
        state = dict(state)
        state["updated_at"] = self._now()
        path = self._session_path(str(state["session_id"]))
        with self._write_lock:
            path.write_text(json.dumps(state, indent=2, default=str), encoding="utf-8")

    def load_session(self, session_id: str) -> Optional[Dict[str, Any]]:
        path = self._session_path(session_id)
        if not path.exists():
            return None
        return json.loads(path.read_text(encoding="utf-8"))

    def save_round(
        self,
        session_id: str,
        *,
        round_data: Dict[str, Any],
        shared_state: Dict[str, Any],
        message_log: List[Dict[str, Any]],
        contributions: List[Dict[str, Any]],
        reviews: List[Dict[str, Any]],
    ) -> Dict[str, Any]:
        state = self.load_session(session_id)
        if state is None:
            raise ValueError(f"Swarm session not found: {session_id}")
        state["rounds"].append(round_data)
        state["shared_state"] = dict(shared_state)
        state["message_log"] = list(message_log)
        state["contributions"] = list(contributions)
        state["reviews"] = list(reviews)
        self.save_session(state)
        return state

    def finalize_session(
        self,
        session_id: str,
        *,
        final_consensus: Dict[str, Any],
        shared_state: Dict[str, Any],
        message_log: List[Dict[str, Any]],
        contributions: List[Dict[str, Any]],
        reviews: List[Dict[str, Any]],
    ) -> Dict[str, Any]:
        state = self.load_session(session_id)
        if state is None:
            raise ValueError(f"Swarm session not found: {session_id}")
        state["status"] = "completed"
        state["final_consensus"] = dict(final_consensus)
        state["shared_state"] = dict(shared_state)
        state["message_log"] = list(message_log)
        state["contributions"] = list(contributions)
        state["reviews"] = list(reviews)
        self.save_session(state)
        return state


_SERVICE: Optional[SwarmBlackboardService] = None


def get_swarm_blackboard_service() -> SwarmBlackboardService:
    global _SERVICE
    if _SERVICE is None:
        _SERVICE = SwarmBlackboardService()
    return _SERVICE
