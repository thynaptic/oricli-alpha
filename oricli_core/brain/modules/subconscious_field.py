from __future__ import annotations
"""
Subconscious Field Module - Persistent Neural Influence Layer
Maintains a vectorized 'subconscious' state that influences generation.
"""

import json
import time
import logging
from pathlib import Path
from typing import List, Dict, Any, Optional

from oricli_core.brain.base_module import BaseBrainModule, ModuleMetadata
from oricli_core.brain.registry import ModuleRegistry
from oricli_core.exceptions import InvalidParameterError

logger = logging.getLogger(__name__)

try:
    import numpy as np
    NUMPY_AVAILABLE = True
except ImportError:
    NUMPY_AVAILABLE = False

class SubconsciousFieldModule(BaseBrainModule):
    """
    Subconscious Field - An active vector buffer that biases cognition.
    """

    def __init__(self):
        super().__init__()
        self.buffer_size = 100
        self.vibration_dim = 384 # Standard for small embeddings
        self._buffer: List[Dict[str, Any]] = []
        self._mental_state_vector: Optional[List[float]] = None
        self._last_update = 0
        self.state_path = Path(__file__).resolve().parent.parent / "data" / "subconscious_state.json"
        self.embeddings = None
        self._load_state()

    @property
    def metadata(self) -> ModuleMetadata:
        return ModuleMetadata(
            name="subconscious_field",
            version="1.0.0",
            description="Maintains a persistent mental state to bias cognition",
            operations=[
                "vibrate",
                "get_mental_state",
                "clear_field",
                "sync_to_memory"
            ],
            dependencies=["numpy", "embeddings"],
            model_required=False,
        )

    def initialize(self) -> bool:
        """Initialize the field."""
        return True

    def _ensure_embeddings(self):
        if not self.embeddings:
            try:
                self.embeddings = ModuleRegistry.get_module("embeddings")
            except Exception:
                pass

    def _load_state(self):
        """Load persistent subconscious state from disk."""
        if self.state_path.exists():
            try:
                data = json.loads(self.state_path.read_text())
                self._buffer = data.get("buffer", [])
                self._mental_state_vector = data.get("mental_state")
                self._last_update = data.get("last_update", 0)
            except Exception as e:
                logger.warning(f"Failed to load subconscious state: {e}")

    def _save_state(self):
        """Save subconscious state to disk."""
        try:
            self.state_path.parent.mkdir(parents=True, exist_ok=True)
            data = {
                "buffer": self._buffer,
                "mental_state": self._mental_state_vector,
                "last_update": time.time()
            }
            self.state_path.write_text(json.dumps(data))
        except Exception as e:
            logger.warning(f"Failed to save subconscious state: {e}")

    def execute(self, operation: str, params: Dict[str, Any]) -> Dict[str, Any]:
        """Execute a subconscious operation."""
        if operation == "vibrate":
            return self._vibrate(params)
        elif operation == "get_mental_state":
            return self._get_mental_state()
        elif operation == "clear_field":
            self._buffer = []
            self._mental_state_vector = None
            self._save_state()
            return {"success": True}
        else:
            raise InvalidParameterError(parameter="operation", value=operation, reason="Unknown operation")

    def _vibrate(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """
        Add a new 'vibration' (embedding) to the field.
        Input can be raw text or a vector.
        """
        text = params.get("text")
        vector = params.get("vector")
        weight = params.get("weight", 1.0)
        
        if not vector and text:
            self._ensure_embeddings()
            if self.embeddings:
                res = self.embeddings.execute("generate", {"text": text})
                vector = res.get("embedding")
                self.vibration_dim = res.get("dimension", self.vibration_dim)
        
        if not vector:
            return {"success": False, "error": "No vector provided or generated"}

        vibration = {
            "vector": vector,
            "weight": weight,
            "timestamp": time.time(),
            "source": params.get("source", "cognition")
        }

        # Update circular buffer
        self._buffer.append(vibration)
        if len(self._buffer) > self.buffer_size:
            self._buffer.pop(0)

        # Update mental state
        self._recalculate_mental_state()
        self._save_state()

        return {"success": True, "vibration_count": len(self._buffer)}

    def _recalculate_mental_state(self):
        """Aggregate buffer into a single bias vector."""
        if not self._buffer:
            self._mental_state_vector = None
            return

        if NUMPY_AVAILABLE:
            vectors = np.array([v["vector"] for v in self._buffer])
            weights = np.array([v["weight"] for v in self._buffer])
            
            # Simple weighted average
            avg_vector = np.average(vectors, axis=0, weights=weights)
            self._mental_state_vector = avg_vector.tolist()
        else:
            # Fallback manual average
            dim = len(self._buffer[0]["vector"])
            avg_vector = [0.0] * dim
            total_weight = sum(v["weight"] for v in self._buffer)
            
            if abs(total_weight) < 1e-9:
                # If weights cancel out, use simple average
                total_weight = len(self._buffer)
                for v in self._buffer:
                    for i in range(dim):
                        avg_vector[i] += v["vector"][i] * (1.0 / total_weight)
            else:
                for v in self._buffer:
                    for i in range(dim):
                        avg_vector[i] += v["vector"][i] * (v["weight"] / total_weight)
            
            self._mental_state_vector = avg_vector

    def _get_mental_state(self) -> Dict[str, Any]:
        """Return the current aggregated mental state vector."""
        return {
            "success": True,
            "mental_state": self._mental_state_vector,
            "dimension": self.vibration_dim,
            "vibration_count": len(self._buffer)
        }
