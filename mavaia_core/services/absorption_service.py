import json
import threading
import time
from pathlib import Path
from typing import Dict, Any, Optional

class AbsorptionService:
    """
    Manages the thread-safe recording of synthetic lessons for JIT learning.
    """
    _instance = None
    _lock = threading.Lock()
    
    def __new__(cls):
        with cls._lock:
            if cls._instance is None:
                cls._instance = super(AbsorptionService, cls).__new__(cls)
                cls._instance._initialized = False
            return cls._instance

    def __init__(self):
        if self._initialized:
            return
        self.buffer_path = Path(__file__).resolve().parent.parent / "data" / "jit_absorption.jsonl"
        self.buffer_path.parent.mkdir(parents=True, exist_ok=True)
        self._write_lock = threading.Lock()
        self._initialized = True

    def record_lesson(self, prompt: str, response: str, metadata: Optional[Dict[str, Any]] = None):
        """
        Append a verified prompt-response pair to the absorption buffer.
        """
        entry = {
            "prompt": prompt,
            "response": response,
            "timestamp": time.time(),
            "metadata": metadata or {}
        }
        
        try:
            with self._write_lock:
                with open(self.buffer_path, "a", encoding="utf-8") as f:
                    f.write(json.dumps(entry) + "\n")
            return True
        except Exception as e:
            # Service should be non-blocking and silent in production to avoid crashing the main brain
            print(f"[AbsorptionService] Error recording lesson: {e}")
            return False

    def get_buffer_count(self) -> int:
        """Return the number of lessons currently in the buffer."""
        if not self.buffer_path.exists():
            return 0
        try:
            with open(self.buffer_path, "r", encoding="utf-8") as f:
                return sum(1 for _ in f)
        except Exception:
            return 0

    def clear_buffer(self):
        """Clear the buffer after successful training."""
        with self._write_lock:
            if self.buffer_path.exists():
                self.buffer_path.unlink()
            self.buffer_path.touch()
