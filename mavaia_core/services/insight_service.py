import json
import threading
import time
from pathlib import Path
from typing import Dict, Any, List, Optional
from datetime import datetime

class InsightService:
    """
    Manages the recording and retrieval of novel insights generated during 
    the Synthetic Dream State.
    """
    _instance = None
    _lock = threading.Lock()
    
    def __new__(cls):
        with cls._lock:
            if cls._instance is None:
                cls._instance = super(InsightService, cls).__new__(cls)
                cls._instance._initialized = False
            return cls._instance

    def __init__(self):
        if self._initialized:
            return
        self.insights_path = Path(__file__).resolve().parent.parent / "data" / "synthetic_insights.jsonl"
        self.insights_path.parent.mkdir(parents=True, exist_ok=True)
        self._write_lock = threading.Lock()
        self._initialized = True

    def record_insight(self, connection: str, source_a: str, source_b: str, score: float, metadata: Optional[Dict[str, Any]] = None):
        """
        Record a novel correlation/insight found during dreaming.
        """
        entry = {
            "id": str(int(time.time() * 1000)),
            "insight": connection,
            "source_a": source_a,
            "source_b": source_b,
            "relevance_score": score,
            "dreamed_at": str(datetime.now()),
            "trained": False,
            "metadata": metadata or {}
        }
        
        with self._write_lock:
            with open(self.insights_path, "a", encoding="utf-8") as f:
                f.write(json.dumps(entry) + "\n")
        
        return entry["id"]

    def list_untrained_insights(self, min_score: float = 0.7) -> List[Dict[str, Any]]:
        """Retrieve high-quality insights that haven't been trained into the model yet."""
        insights = []
        if not self.insights_path.exists():
            return []
            
        with open(self.insights_path, "r", encoding="utf-8") as f:
            for line in f:
                try:
                    obj = json.loads(line)
                    if not obj.get("trained", False) and obj.get("relevance_score", 0) >= min_score:
                        insights.append(obj)
                except Exception:
                    continue
        return insights

    def mark_as_trained(self, insight_ids: List[str]):
        """Mark insights as processed after a training pass."""
        if not self.insights_path.exists():
            return
            
        all_insights = []
        with open(self.insights_path, "r", encoding="utf-8") as f:
            for line in f:
                try:
                    obj = json.loads(line)
                    if obj["id"] in insight_ids:
                        obj["trained"] = True
                    all_insights.append(obj)
                except Exception:
                    continue
                    
        with self._write_lock:
            with open(self.insights_path, "w", encoding="utf-8") as f:
                for obj in all_insights:
                    f.write(json.dumps(obj) + "\n")
