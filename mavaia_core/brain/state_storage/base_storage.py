from __future__ import annotations
"""
Base Storage Interface

Abstract storage interface for state persistence.
All storage implementations must inherit from this class.
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Any, Dict, List, Optional, Tuple
from pathlib import Path
from datetime import datetime


@dataclass
class StorageConfig:
    """Configuration for storage backends"""
    
    storage_type: str = "file"  # file, memory, database
    storage_path: Optional[Path] = None
    compression: bool = False
    encryption: bool = False
    max_size_mb: Optional[int] = None
    backup_enabled: bool = True
    backup_interval_hours: int = 24


class BaseStorage(ABC):
    """
    Abstract base class for state storage implementations
    
    Provides unified interface for state persistence across different backends.
    """
    
    def __init__(self, config: StorageConfig):
        """
        Initialize storage backend
        
        Args:
            config: Storage configuration
        """
        self.config = config
        self._initialized = False
    
    @abstractmethod
    def initialize(self) -> bool:
        """
        Initialize the storage backend
        
        Returns:
            True if initialization succeeded, False otherwise
        """
        pass
    
    @abstractmethod
    def save(
        self,
        state_type: str,
        state_id: str,
        state_data: Dict[str, Any],
        metadata: Optional[Dict[str, Any]] = None
    ) -> bool:
        """
        Save state data
        
        Args:
            state_type: Type of state (e.g., "conversation", "task")
            state_id: Unique identifier for this state
            state_data: State data to save
            metadata: Optional metadata (timestamps, version, etc.)
        
        Returns:
            True if save succeeded, False otherwise
        """
        pass
    
    @abstractmethod
    def load(
        self,
        state_type: str,
        state_id: str
    ) -> Optional[Dict[str, Any]]:
        """
        Load state data
        
        Args:
            state_type: Type of state
            state_id: Unique identifier for this state
        
        Returns:
            State data dictionary or None if not found
        """
        pass
    
    @abstractmethod
    def delete(
        self,
        state_type: str,
        state_id: str
    ) -> bool:
        """
        Delete state data
        
        Args:
            state_type: Type of state
            state_id: Unique identifier for this state
        
        Returns:
            True if deletion succeeded, False otherwise
        """
        pass
    
    @abstractmethod
    def list_states(
        self,
        state_type: Optional[str] = None,
        limit: Optional[int] = None
    ) -> List[Dict[str, Any]]:
        """
        List all states, optionally filtered by type
        
        Args:
            state_type: Optional filter by state type
            limit: Optional limit on number of results
        
        Returns:
            List of state metadata dictionaries
        """
        pass
    
    @abstractmethod
    def exists(
        self,
        state_type: str,
        state_id: str
    ) -> bool:
        """
        Check if state exists
        
        Args:
            state_type: Type of state
            state_id: Unique identifier for this state
        
        Returns:
            True if state exists, False otherwise
        """
        pass
    
    @abstractmethod
    def cleanup(self) -> None:
        """
        Cleanup resources and close connections
        """
        pass
    
    def _add_metadata(
        self,
        state_data: Dict[str, Any],
        metadata: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Add metadata to state data
        
        Args:
            state_data: Original state data
            metadata: Additional metadata
        
        Returns:
            State data with metadata added
        """
        enriched = state_data.copy()
        
        # Add standard metadata
        enriched["_metadata"] = {
            "saved_at": datetime.now().isoformat(),
            "version": metadata.get("version", 1) if metadata else 1,
            **(metadata or {})
        }
        
        return enriched
    
    def _extract_metadata(
        self,
        state_data: Dict[str, Any]
    ) -> Tuple[Dict[str, Any], Dict[str, Any]]:
        """
        Extract metadata from state data
        
        Args:
            state_data: State data with metadata
        
        Returns:
            Tuple of (state_data, metadata)
        """
        metadata = state_data.pop("_metadata", {})
        return state_data, metadata

