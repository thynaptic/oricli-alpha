from __future__ import annotations
"""
Sandbox Pool Manager

Manages a pool of pre-warmed sandbox containers for improved performance.
"""

import time
import threading
from typing import Dict, Optional, List
from collections import deque

from oricli_core.services.sandbox.base import SandboxService, SandboxExecutionError
from oricli_core.services.sandbox.resource_limits import ResourceLimits


class SandboxPoolManager:
    """
    Manages a pool of pre-warmed sandbox containers.
    
    Maintains a pool of ready-to-use containers to avoid cold-start overhead.
    """
    
    def __init__(
        self,
        sandbox_service: SandboxService,
        pool_size: int = 5,
        max_pool_size: int = 20,
        session_timeout: int = 3600,  # 1 hour
    ):
        """
        Initialize pool manager.
        
        Args:
            sandbox_service: SandboxService instance to use
            pool_size: Target number of containers to keep warm
            max_pool_size: Maximum number of containers in pool
            session_timeout: Session timeout in seconds (for cleanup)
        """
        self.sandbox_service = sandbox_service
        self.pool_size = pool_size
        self.max_pool_size = max_pool_size
        self.session_timeout = session_timeout
        
        # Pool of available session IDs
        self._available_sessions: deque = deque()
        self._session_to_service: Dict[str, SandboxService] = {}
        self._session_created_at: Dict[str, float] = {}
        self._active_sessions: set = set()
        self._lock = threading.Lock()
        
        # Start background thread for pool maintenance
        self._running = True
        self._maintenance_thread = threading.Thread(
            target=self._maintenance_loop, daemon=True
        )
        self._maintenance_thread.start()
    
    def _maintenance_loop(self) -> None:
        """Background thread for pool maintenance."""
        while self._running:
            try:
                self._cleanup_expired_sessions()
                self._replenish_pool()
            except Exception as e:
                # Log error but continue
                print(f"Pool maintenance error: {e}")
            
            time.sleep(60)  # Run maintenance every minute
    
    def _cleanup_expired_sessions(self) -> None:
        """Clean up expired sessions."""
        current_time = time.time()
        expired_sessions = []
        
        with self._lock:
            for session_id in list(self._available_sessions):
                if session_id in self._session_created_at:
                    age = current_time - self._session_created_at[session_id]
                    if age > self.session_timeout:
                        expired_sessions.append(session_id)
            
            for session_id in expired_sessions:
                self._remove_from_pool(session_id)
    
    def _replenish_pool(self) -> None:
        """Replenish pool if below target size."""
        with self._lock:
            current_size = len(self._available_sessions)
            if current_size < self.pool_size and current_size < self.max_pool_size:
                # Create new session to add to pool
                try:
                    session_id = self._create_pool_session()
                    if session_id:
                        self._available_sessions.append(session_id)
                except Exception as e:
                    # Log but don't raise - pool replenishment is best-effort
                    print(f"Failed to replenish pool: {e}")
    
    def _create_pool_session(self) -> Optional[str]:
        """Create a new session for the pool."""
        session_id = f"pool-{int(time.time() * 1000000)}"
        try:
            self.sandbox_service.create_session(session_id)
            self._session_to_service[session_id] = self.sandbox_service
            self._session_created_at[session_id] = time.time()
            return session_id
        except Exception:
            return None
    
    def _remove_from_pool(self, session_id: str) -> None:
        """Remove a session from the pool."""
        try:
            if session_id in self._session_to_service:
                service = self._session_to_service[session_id]
                service.destroy_session(session_id)
            self._session_to_service.pop(session_id, None)
            self._session_created_at.pop(session_id, None)
            # Remove from deque if present
            if session_id in self._available_sessions:
                self._available_sessions.remove(session_id)
        except Exception:
            pass
    
    def get_session(self) -> str:
        """
        Get a session from the pool (or create a new one).
        
        Returns:
            Session ID
        """
        with self._lock:
            # Try to get from pool
            if self._available_sessions:
                session_id = self._available_sessions.popleft()
                self._active_sessions.add(session_id)
                return session_id
            
            # Pool is empty, create new session
            session_id = f"session-{int(time.time() * 1000000)}"
            try:
                self.sandbox_service.create_session(session_id)
                self._session_to_service[session_id] = self.sandbox_service
                self._session_created_at[session_id] = time.time()
                self._active_sessions.add(session_id)
                return session_id
            except Exception as e:
                raise SandboxExecutionError(f"Failed to create session: {str(e)}")
    
    def return_session(self, session_id: str, reuse: bool = True) -> None:
        """
        Return a session to the pool or destroy it.
        
        Args:
            session_id: Session ID to return
            reuse: If True, add back to pool; if False, destroy session
        """
        with self._lock:
            if session_id in self._active_sessions:
                self._active_sessions.remove(session_id)
            
            if reuse and session_id in self._session_to_service:
                # Check pool size
                if len(self._available_sessions) < self.max_pool_size:
                    # Reset session if needed (clean up any files, etc.)
                    # For now, just add back to pool
                    self._available_sessions.append(session_id)
                else:
                    # Pool is full, destroy session
                    self._remove_from_pool(session_id)
            else:
                # Don't reuse, destroy session
                self._remove_from_pool(session_id)
    
    def destroy_session(self, session_id: str) -> None:
        """
        Destroy a session immediately (remove from pool if present).
        
        Args:
            session_id: Session ID to destroy
        """
        with self._lock:
            self._active_sessions.discard(session_id)
            self._remove_from_pool(session_id)
    
    def shutdown(self) -> None:
        """Shutdown pool manager and clean up all sessions."""
        self._running = False
        
        with self._lock:
            # Destroy all sessions
            all_sessions = (
                list(self._available_sessions) + list(self._active_sessions)
            )
            for session_id in all_sessions:
                self._remove_from_pool(session_id)
        
        # Wait for maintenance thread
        if self._maintenance_thread.is_alive():
            self._maintenance_thread.join(timeout=5)
    
    def get_pool_stats(self) -> Dict[str, int]:
        """
        Get pool statistics.
        
        Returns:
            Dictionary with pool statistics
        """
        with self._lock:
            return {
                "available": len(self._available_sessions),
                "active": len(self._active_sessions),
                "total": len(self._session_to_service),
            }

