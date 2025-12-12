"""
In-Memory Storage Implementation

Fast in-memory storage for temporary state.
Data is lost on process restart.
"""

from typing import Any, Dict, List, Optional
from datetime import datetime
import threading

from mavaia_core.brain.state_storage.base_storage import BaseStorage, StorageConfig


class MemoryStorage(BaseStorage):
    """
    In-memory storage implementation
    
    Stores state in memory using dictionaries.
    Fast but ephemeral - data is lost on restart.
    """
    
    def __init__(self, config: StorageConfig):
        """
        Initialize memory storage
        
        Args:
            config: Storage configuration
        """
        super().__init__(config)
        self._storage: Dict[str, Dict[str, Dict[str, Any]]] = {}
        self._lock = threading.RLock()
        self._max_size = config.max_size_mb * 1024 * 1024 if config.max_size_mb else None
    
    def initialize(self) -> bool:
        """Initialize memory storage backend"""
        self._storage = {}
        self._initialized = True
        return True
    
    def _get_key(self, state_type: str, state_id: str) -> str:
        """Get storage key"""
        return f"{state_type}:{state_id}"
    
    def save(
        self,
        state_type: str,
        state_id: str,
        state_data: Dict[str, Any],
        metadata: Optional[Dict[str, Any]] = None
    ) -> bool:
        """Save state data to memory"""
        try:
            with self._lock:
                if state_type not in self._storage:
                    self._storage[state_type] = {}
                
                enriched_data = self._add_metadata(state_data, metadata)
                self._storage[state_type][state_id] = enriched_data
                
                # Check size limits
                if self._max_size:
                    self._enforce_size_limit()
                
                return True
        except Exception as e:
            print(f"[MemoryStorage] Failed to save {state_type}:{state_id}: {e}")
            return False
    
    def load(
        self,
        state_type: str,
        state_id: str
    ) -> Optional[Dict[str, Any]]:
        """Load state data from memory"""
        try:
            with self._lock:
                if state_type not in self._storage:
                    return None
                
                if state_id not in self._storage[state_type]:
                    return None
                
                data = self._storage[state_type][state_id].copy()
                state_data, metadata = self._extract_metadata(data)
                return state_data
        except Exception as e:
            print(f"[MemoryStorage] Failed to load {state_type}:{state_id}: {e}")
            return None
    
    def delete(
        self,
        state_type: str,
        state_id: str
    ) -> bool:
        """Delete state from memory"""
        try:
            with self._lock:
                if state_type in self._storage:
                    if state_id in self._storage[state_type]:
                        del self._storage[state_type][state_id]
                        return True
                return False
        except Exception as e:
            print(f"[MemoryStorage] Failed to delete {state_type}:{state_id}: {e}")
            return False
    
    def list_states(
        self,
        state_type: Optional[str] = None,
        limit: Optional[int] = None
    ) -> List[Dict[str, Any]]:
        """List all states in memory"""
        states = []
        
        try:
            with self._lock:
                types_to_search = [state_type] if state_type else list(self._storage.keys())
                
                for st_type in types_to_search:
                    if st_type not in self._storage:
                        continue
                    
                    for state_id, state_data in self._storage[st_type].items():
                        metadata = state_data.get("_metadata", {})
                        states.append({
                            "state_type": st_type,
                            "state_id": state_id,
                            "saved_at": metadata.get("saved_at", datetime.now().isoformat()),
                            "version": metadata.get("version", 1)
                        })
                
                # Sort by saved_at (newest first)
                states.sort(key=lambda x: x.get("saved_at", ""), reverse=True)
                
                if limit:
                    states = states[:limit]
                
                return states
        except Exception as e:
            print(f"[MemoryStorage] Failed to list states: {e}")
            return []
    
    def exists(
        self,
        state_type: str,
        state_id: str
    ) -> bool:
        """Check if state exists in memory"""
        with self._lock:
            return (
                state_type in self._storage and
                state_id in self._storage[state_type]
            )
    
    def cleanup(self) -> None:
        """Cleanup memory storage resources"""
        with self._lock:
            self._storage.clear()
    
    def _enforce_size_limit(self) -> None:
        """Enforce size limit by removing oldest states"""
        # Simple implementation: remove oldest states if over limit
        # In production, use more sophisticated LRU cache
        total_size = sum(
            len(str(v)) for state_type in self._storage.values()
            for v in state_type.values()
        )
        
        if self._max_size and total_size > self._max_size:
            # Remove oldest 10% of states
            all_states = []
            for state_type, states in self._storage.items():
                for state_id, state_data in states.items():
                    metadata = state_data.get("_metadata", {})
                    all_states.append((state_type, state_id, metadata.get("saved_at", "")))
            
            all_states.sort(key=lambda x: x[2])  # Sort by saved_at
            to_remove = int(len(all_states) * 0.1)  # Remove 10%
            
            for state_type, state_id, _ in all_states[:to_remove]:
                if state_type in self._storage and state_id in self._storage[state_type]:
                    del self._storage[state_type][state_id]

