from __future__ import annotations
"""
Database Storage Implementation

SQLite-based storage for production use.
Supports transactions, indexing, and efficient queries.
"""

import json
import sqlite3
from pathlib import Path
from typing import Any, Dict, List, Optional
from datetime import datetime
import threading

from mavaia_core.brain.state_storage.base_storage import BaseStorage, StorageConfig


class DatabaseStorage(BaseStorage):
    """
    SQLite database storage implementation
    
    Stores state in SQLite database with proper indexing.
    Suitable for production deployments.
    """
    
    def __init__(self, config: StorageConfig):
        """
        Initialize database storage
        
        Args:
            config: Storage configuration with storage_path set
        """
        super().__init__(config)
        if config.storage_path is None:
            db_path = Path(__file__).parent.parent / "state_storage" / "states.db"
        else:
            db_path = Path(config.storage_path) / "states.db"
        
        self.db_path = db_path
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self._lock = threading.RLock()
        self._connection: Optional[sqlite3.Connection] = None
    
    def initialize(self) -> bool:
        """Initialize database storage backend"""
        try:
            self._connection = sqlite3.connect(
                str(self.db_path),
                check_same_thread=False
            )
            self._connection.row_factory = sqlite3.Row
            
            # Create tables
            self._connection.execute("""
                CREATE TABLE IF NOT EXISTS states (
                    state_type TEXT NOT NULL,
                    state_id TEXT NOT NULL,
                    state_data TEXT NOT NULL,
                    metadata TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    PRIMARY KEY (state_type, state_id)
                )
            """)
            
            # Create indexes
            self._connection.execute("""
                CREATE INDEX IF NOT EXISTS idx_state_type 
                ON states(state_type)
            """)
            
            self._connection.execute("""
                CREATE INDEX IF NOT EXISTS idx_updated_at 
                ON states(updated_at)
            """)
            
            self._connection.commit()
            self._initialized = True
            return True
        except Exception as e:
            print(f"[DatabaseStorage] Initialization failed: {e}")
            return False
    
    def _get_connection(self) -> sqlite3.Connection:
        """Get database connection"""
        if self._connection is None:
            self.initialize()
        return self._connection
    
    def save(
        self,
        state_type: str,
        state_id: str,
        state_data: Dict[str, Any],
        metadata: Optional[Dict[str, Any]] = None
    ) -> bool:
        """Save state data to database"""
        try:
            with self._lock:
                conn = self._get_connection()
                enriched_data = self._add_metadata(state_data, metadata)
                
                state_json = json.dumps(enriched_data, default=str)
                metadata_json = json.dumps(metadata or {}, default=str)
                
                conn.execute("""
                    INSERT OR REPLACE INTO states 
                    (state_type, state_id, state_data, metadata, updated_at)
                    VALUES (?, ?, ?, ?, ?)
                """, (state_type, state_id, state_json, metadata_json, datetime.now().isoformat()))
                
                conn.commit()
                return True
        except Exception as e:
            print(f"[DatabaseStorage] Failed to save {state_type}:{state_id}: {e}")
            return False
    
    def load(
        self,
        state_type: str,
        state_id: str
    ) -> Optional[Dict[str, Any]]:
        """Load state data from database"""
        try:
            with self._lock:
                conn = self._get_connection()
                
                row = conn.execute("""
                    SELECT state_data FROM states
                    WHERE state_type = ? AND state_id = ?
                """, (state_type, state_id)).fetchone()
                
                if row is None:
                    return None
                
                data = json.loads(row["state_data"])
                state_data, metadata = self._extract_metadata(data)
                return state_data
        except Exception as e:
            print(f"[DatabaseStorage] Failed to load {state_type}:{state_id}: {e}")
            return None
    
    def delete(
        self,
        state_type: str,
        state_id: str
    ) -> bool:
        """Delete state from database"""
        try:
            with self._lock:
                conn = self._get_connection()
                
                cursor = conn.execute("""
                    DELETE FROM states
                    WHERE state_type = ? AND state_id = ?
                """, (state_type, state_id))
                
                conn.commit()
                return cursor.rowcount > 0
        except Exception as e:
            print(f"[DatabaseStorage] Failed to delete {state_type}:{state_id}: {e}")
            return False
    
    def list_states(
        self,
        state_type: Optional[str] = None,
        limit: Optional[int] = None
    ) -> List[Dict[str, Any]]:
        """List all states from database"""
        states = []
        
        try:
            with self._lock:
                conn = self._get_connection()
                
                if state_type:
                    query = """
                        SELECT state_type, state_id, metadata, updated_at
                        FROM states
                        WHERE state_type = ?
                        ORDER BY updated_at DESC
                    """
                    params = (state_type,)
                else:
                    query = """
                        SELECT state_type, state_id, metadata, updated_at
                        FROM states
                        ORDER BY updated_at DESC
                    """
                    params = ()
                
                if limit:
                    query += f" LIMIT {limit}"
                
                rows = conn.execute(query, params).fetchall()
                
                for row in rows:
                    metadata = json.loads(row["metadata"] or "{}")
                    states.append({
                        "state_type": row["state_type"],
                        "state_id": row["state_id"],
                        "saved_at": row["updated_at"],
                        "version": metadata.get("version", 1)
                    })
                
                return states
        except Exception as e:
            print(f"[DatabaseStorage] Failed to list states: {e}")
            return []
    
    def exists(
        self,
        state_type: str,
        state_id: str
    ) -> bool:
        """Check if state exists in database"""
        try:
            with self._lock:
                conn = self._get_connection()
                
                row = conn.execute("""
                    SELECT 1 FROM states
                    WHERE state_type = ? AND state_id = ?
                    LIMIT 1
                """, (state_type, state_id)).fetchone()
                
                return row is not None
        except Exception as e:
            print(f"[DatabaseStorage] Failed to check existence: {e}")
            return False
    
    def cleanup(self) -> None:
        """Cleanup database storage resources"""
        with self._lock:
            if self._connection:
                self._connection.close()
                self._connection = None

