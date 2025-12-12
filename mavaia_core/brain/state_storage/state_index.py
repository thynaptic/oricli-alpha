"""
State Indexing and Querying System

Provides efficient querying and indexing of stored state.
"""

from typing import Any, Dict, List, Optional, Callable
from datetime import datetime
from pathlib import Path

from mavaia_core.brain.state_storage.base_storage import BaseStorage


class StateIndex:
    """
    State indexing and querying system
    
    Provides efficient querying capabilities over stored state.
    """
    
    def __init__(self, storage: BaseStorage):
        """
        Initialize state index
        
        Args:
            storage: Storage backend to index
        """
        self.storage = storage
        self._index: Dict[str, Dict[str, Any]] = {}
        self._initialized = False
    
    def initialize(self) -> bool:
        """Initialize and build index"""
        try:
            self._build_index()
            self._initialized = True
            return True
        except Exception as e:
            print(f"[StateIndex] Initialization failed: {e}")
            return False
    
    def _build_index(self) -> None:
        """Build index from all stored states"""
        self._index = {}
        
        states = self.storage.list_states()
        for state_info in states:
            state_type = state_info["state_type"]
            state_id = state_info["state_id"]
            
            if state_type not in self._index:
                self._index[state_type] = {}
            
            self._index[state_type][state_id] = {
                "saved_at": state_info.get("saved_at"),
                "version": state_info.get("version", 1)
            }
    
    def query(
        self,
        state_type: Optional[str] = None,
        filter_func: Optional[Callable[[Dict[str, Any]], bool]] = None,
        limit: Optional[int] = None
    ) -> List[Dict[str, Any]]:
        """
        Query states using filter function
        
        Args:
            state_type: Optional filter by state type
            filter_func: Optional filter function (state_data) -> bool
            limit: Optional limit on results
        
        Returns:
            List of matching states
        """
        results = []
        
        types_to_search = [state_type] if state_type else list(self._index.keys())
        
        for st_type in types_to_search:
            if st_type not in self._index:
                continue
            
            for state_id in self._index[st_type].keys():
                state_data = self.storage.load(st_type, state_id)
                
                if state_data is None:
                    continue
                
                # Apply filter if provided
                if filter_func and not filter_func(state_data):
                    continue
                
                results.append({
                    "state_type": st_type,
                    "state_id": state_id,
                    "state_data": state_data
                })
        
        if limit:
            results = results[:limit]
        
        return results
    
    def search(
        self,
        state_type: Optional[str] = None,
        search_term: Optional[str] = None,
        limit: Optional[int] = None
    ) -> List[Dict[str, Any]]:
        """
        Search states by text content
        
        Args:
            state_type: Optional filter by state type
            search_term: Text to search for
            limit: Optional limit on results
        
        Returns:
            List of matching states
        """
        if not search_term:
            return self.query(state_type=state_type, limit=limit)
        
        search_lower = search_term.lower()
        
        def search_filter(state_data: Dict[str, Any]) -> bool:
            """Filter function for text search"""
            state_str = str(state_data).lower()
            return search_lower in state_str
        
        return self.query(state_type=state_type, filter_func=search_filter, limit=limit)
    
    def get_by_type(self, state_type: str) -> List[Dict[str, Any]]:
        """
        Get all states of a specific type
        
        Args:
            state_type: Type of state to retrieve
        
        Returns:
            List of states
        """
        return self.query(state_type=state_type)
    
    def refresh(self) -> None:
        """Refresh index from storage"""
        self._build_index()
    
    def get_stats(self) -> Dict[str, Any]:
        """
        Get index statistics
        
        Returns:
            Dictionary with statistics
        """
        total_states = sum(len(states) for states in self._index.values())
        
        return {
            "total_states": total_states,
            "state_types": list(self._index.keys()),
            "states_by_type": {
                st_type: len(states)
                for st_type, states in self._index.items()
            }
        }

