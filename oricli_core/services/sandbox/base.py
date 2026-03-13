from __future__ import annotations
"""
Base Sandbox Service Interface

Abstract interface for sandbox implementations (Firecracker, Docker, etc.)
"""

from abc import ABC, abstractmethod
from typing import Optional, Dict, Any, List
from pathlib import Path

from oricli_core.services.sandbox.resource_limits import ResourceLimits, ResourceUsage


class SandboxExecutionError(Exception):
    """Raised when sandbox execution fails."""
    pass


class SandboxService(ABC):
    """
    Abstract base class for sandbox implementations.
    
    All sandbox implementations must inherit from this class and implement
    the required abstract methods.
    """
    
    def __init__(self, sandbox_root: str = "/sandbox", resource_limits: Optional[ResourceLimits] = None):
        """
        Initialize sandbox service.
        
        Args:
            sandbox_root: Root directory of the sandbox
            resource_limits: Resource limits for this sandbox
        """
        self.sandbox_root = Path(sandbox_root)
        self.resource_limits = resource_limits or ResourceLimits()
        self._sessions: Dict[str, Dict[str, Any]] = {}
    
    @abstractmethod
    def create_session(self, session_id: str, resource_limits: Optional[ResourceLimits] = None) -> str:
        """
        Create a new execution session.
        
        Args:
            session_id: Unique session identifier
            resource_limits: Optional resource limits for this session
            
        Returns:
            Session ID
            
        Raises:
            SandboxExecutionError: If session creation fails
        """
        pass
    
    @abstractmethod
    def destroy_session(self, session_id: str) -> None:
        """
        Destroy an execution session and clean up resources.
        
        Args:
            session_id: Session identifier to destroy
            
        Raises:
            SandboxExecutionError: If session destruction fails
        """
        pass
    
    @abstractmethod
    def execute_command(
        self,
        session_id: str,
        command: str,
        timeout: Optional[int] = None,
    ) -> Dict[str, Any]:
        """
        Execute a command in the sandbox.
        
        Args:
            session_id: Session identifier
            command: Command to execute
            timeout: Optional timeout override (in seconds)
            
        Returns:
            Dictionary with keys:
                - stdout: str - Standard output
                - stderr: str - Standard error
                - exit_code: int - Exit code
                - execution_time: float - Execution time in seconds
                - resource_usage: ResourceUsage - Resource usage information
                
        Raises:
            SandboxExecutionError: If execution fails
        """
        pass
    
    @abstractmethod
    def read_file(self, session_id: str, file_path: str) -> str:
        """
        Read a file from the sandbox.
        
        Args:
            session_id: Session identifier
            file_path: Path to file (relative to sandbox root)
            
        Returns:
            File contents as string
            
        Raises:
            SandboxExecutionError: If file read fails
        """
        pass
    
    @abstractmethod
    def write_file(self, session_id: str, file_path: str, content: str) -> None:
        """
        Write a file to the sandbox.
        
        Args:
            session_id: Session identifier
            file_path: Path to file (relative to sandbox root)
            content: File content to write
            
        Raises:
            SandboxExecutionError: If file write fails
        """
        pass
    
    @abstractmethod
    def list_files(self, session_id: str, directory: str = ".") -> List[str]:
        """
        List files in a directory within the sandbox.
        
        Args:
            session_id: Session identifier
            directory: Directory path (relative to sandbox root)
            
        Returns:
            List of file/directory names
            
        Raises:
            SandboxExecutionError: If listing fails
        """
        pass
    
    @abstractmethod
    def delete_file(self, session_id: str, file_path: str) -> None:
        """
        Delete a file or directory from the sandbox.
        
        Args:
            session_id: Session identifier
            file_path: Path to file/directory (relative to sandbox root)
            
        Raises:
            SandboxExecutionError: If deletion fails
        """
        pass
    
    def session_exists(self, session_id: str) -> bool:
        """
        Check if a session exists.
        
        Args:
            session_id: Session identifier
            
        Returns:
            True if session exists, False otherwise
        """
        return session_id in self._sessions
    
    def get_session_info(self, session_id: str) -> Dict[str, Any]:
        """
        Get information about a session.
        
        Args:
            session_id: Session identifier
            
        Returns:
            Session information dictionary
            
        Raises:
            SandboxExecutionError: If session doesn't exist
        """
        if session_id not in self._sessions:
            raise SandboxExecutionError(f"Session {session_id} does not exist")
        return self._sessions[session_id].copy()
    
    def list_sessions(self) -> List[str]:
        """
        List all active session IDs.
        
        Returns:
            List of session IDs
        """
        return list(self._sessions.keys())

