"""
File-Based Storage Implementation

Simple file-based storage using JSON files.
Suitable for single-instance deployments and development.
"""

import json
import gzip
from pathlib import Path
from typing import Any, Dict, List, Optional
from datetime import datetime

from mavaia_core.brain.state_storage.base_storage import BaseStorage, StorageConfig


class FileStorage(BaseStorage):
    """
    File-based storage implementation
    
    Stores state as JSON files in a directory structure:
    {storage_path}/{state_type}/{state_id}.json
    """
    
    def __init__(self, config: StorageConfig):
        """
        Initialize file storage
        
        Args:
            config: Storage configuration with storage_path set
        """
        super().__init__(config)
        if config.storage_path is None:
            # Default to state_storage directory
            self.storage_path = Path(__file__).parent.parent / "state_storage"
        else:
            self.storage_path = Path(config.storage_path)
        
        self.storage_path.mkdir(parents=True, exist_ok=True)
        self.compression = config.compression
    
    def initialize(self) -> bool:
        """Initialize file storage backend"""
        try:
            self.storage_path.mkdir(parents=True, exist_ok=True)
            self._initialized = True
            return True
        except Exception as e:
            print(f"[FileStorage] Initialization failed: {e}")
            return False
    
    def _get_file_path(
        self,
        state_type: str,
        state_id: str
    ) -> Path:
        """
        Get file path for a state
        
        Args:
            state_type: Type of state
            state_id: Unique identifier
        
        Returns:
            Path to state file
        """
        state_dir = self.storage_path / state_type
        state_dir.mkdir(parents=True, exist_ok=True)
        
        ext = ".json.gz" if self.compression else ".json"
        return state_dir / f"{state_id}{ext}"
    
    def save(
        self,
        state_type: str,
        state_id: str,
        state_data: Dict[str, Any],
        metadata: Optional[Dict[str, Any]] = None
    ) -> bool:
        """Save state data to file"""
        try:
            file_path = self._get_file_path(state_type, state_id)
            enriched_data = self._add_metadata(state_data, metadata)
            
            json_data = json.dumps(enriched_data, indent=2, default=str)
            
            if self.compression:
                with gzip.open(file_path, "wt", encoding="utf-8") as f:
                    f.write(json_data)
            else:
                with open(file_path, "w", encoding="utf-8") as f:
                    f.write(json_data)
            
            return True
        except Exception as e:
            print(f"[FileStorage] Failed to save {state_type}:{state_id}: {e}")
            return False
    
    def load(
        self,
        state_type: str,
        state_id: str
    ) -> Optional[Dict[str, Any]]:
        """Load state data from file"""
        try:
            file_path = self._get_file_path(state_type, state_id)
            
            if not file_path.exists():
                return None
            
            if self.compression:
                with gzip.open(file_path, "rt", encoding="utf-8") as f:
                    data = json.load(f)
            else:
                with open(file_path, "r", encoding="utf-8") as f:
                    data = json.load(f)
            
            state_data, metadata = self._extract_metadata(data)
            return state_data
        except Exception as e:
            print(f"[FileStorage] Failed to load {state_type}:{state_id}: {e}")
            return None
    
    def delete(
        self,
        state_type: str,
        state_id: str
    ) -> bool:
        """Delete state file"""
        try:
            file_path = self._get_file_path(state_type, state_id)
            
            if file_path.exists():
                file_path.unlink()
                return True
            return False
        except Exception as e:
            print(f"[FileStorage] Failed to delete {state_type}:{state_id}: {e}")
            return False
    
    def list_states(
        self,
        state_type: Optional[str] = None,
        limit: Optional[int] = None
    ) -> List[Dict[str, Any]]:
        """List all states"""
        states = []
        
        try:
            if state_type:
                search_dirs = [self.storage_path / state_type]
            else:
                search_dirs = [d for d in self.storage_path.iterdir() if d.is_dir()]
            
            for state_dir in search_dirs:
                if not state_dir.is_dir():
                    continue
                
                pattern = "*.json.gz" if self.compression else "*.json"
                for state_file in state_dir.glob(pattern):
                    state_id = state_file.stem.replace(".json", "")
                    states.append({
                        "state_type": state_dir.name,
                        "state_id": state_id,
                        "file_path": str(state_file),
                        "size": state_file.stat().st_size,
                        "modified": datetime.fromtimestamp(
                            state_file.stat().st_mtime
                        ).isoformat()
                    })
            
            # Sort by modified time (newest first)
            states.sort(key=lambda x: x["modified"], reverse=True)
            
            if limit:
                states = states[:limit]
            
            return states
        except Exception as e:
            print(f"[FileStorage] Failed to list states: {e}")
            return []
    
    def exists(
        self,
        state_type: str,
        state_id: str
    ) -> bool:
        """Check if state file exists"""
        file_path = self._get_file_path(state_type, state_id)
        return file_path.exists()
    
    def cleanup(self) -> None:
        """Cleanup file storage resources"""
        # File storage doesn't need cleanup
        pass

