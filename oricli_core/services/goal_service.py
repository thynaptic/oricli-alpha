import json
import threading
import time
import uuid
from pathlib import Path
from typing import Dict, Any, List, Optional
from datetime import datetime

class GoalService:
    """
    Manages the lifecycle of persistent, long-horizon global objectives.
    """
    _instance = None
    _lock = threading.Lock()
    
    def __new__(cls):
        with cls._lock:
            if cls._instance is None:
                cls._instance = super(GoalService, cls).__new__(cls)
                cls._instance._initialized = False
            return cls._instance

    def __init__(self):
        if self._initialized:
            return
        self.objectives_path = Path(__file__).resolve().parent.parent / "data" / "global_objectives.jsonl"
        self.plans_dir = Path(__file__).resolve().parent.parent / "data" / "persistent_plans"
        self.plans_dir.mkdir(parents=True, exist_ok=True)
        self._write_lock = threading.Lock()
        self._initialized = True

    def add_objective(self, goal: str, priority: int = 1, metadata: Optional[Dict[str, Any]] = None) -> str:
        """
        Register a new high-level objective.
        Returns the unique goal_id.
        """
        goal_id = str(uuid.uuid4())[:8]
        entry = {
            "id": goal_id,
            "goal": goal,
            "priority": priority,
            "status": "pending",
            "created_at": str(datetime.now()),
            "updated_at": str(datetime.now()),
            "progress": 0.0,
            "metadata": metadata or {}
        }
        
        with self._write_lock:
            with open(self.objectives_path, "a", encoding="utf-8") as f:
                f.write(json.dumps(entry) + "\n")
        
        return goal_id

    def list_objectives(self, status: Optional[str] = None) -> List[Dict[str, Any]]:
        """List all objectives, optionally filtering by status."""
        objectives = []
        if not self.objectives_path.exists():
            return []
            
        with open(self.objectives_path, "r", encoding="utf-8") as f:
            for line in f:
                obj = json.loads(line)
                if status is None or obj["status"] == status:
                    objectives.append(obj)
        return objectives

    def update_objective(self, goal_id: str, updates: Dict[str, Any]):
        """Update an existing objective's state."""
        objectives = self.list_objectives()
        found = False
        
        for obj in objectives:
            if obj["id"] == goal_id:
                obj.update(updates)
                obj["updated_at"] = str(datetime.now())
                found = True
                break
        
        if found:
            with self._write_lock:
                with open(self.objectives_path, "w", encoding="utf-8") as f:
                    for obj in objectives:
                        f.write(json.dumps(obj) + "\n")
        return found

    def save_plan_state(self, goal_id: str, plan_data: Dict[str, Any]):
        """Save the detailed execution state of a plan."""
        plan_path = self.plans_dir / f"{goal_id}_plan.json"
        with self._write_lock:
            plan_path.write_text(json.dumps(plan_data, indent=2))

    def load_plan_state(self, goal_id: str) -> Optional[Dict[str, Any]]:
        """Load the detailed execution state of a plan."""
        plan_path = self.plans_dir / f"{goal_id}_plan.json"
        if plan_path.exists():
            return json.loads(plan_path.read_text())
        return None
