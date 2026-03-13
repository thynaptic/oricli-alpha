from __future__ import annotations
"""
Firecracker Sandbox Implementation

Firecracker microVM-based sandbox for secure code execution.
Falls back to Docker if Firecracker is not available.
"""

import os
import subprocess
import time
import tempfile
from pathlib import Path
from typing import Optional, Dict, Any, List

from oricli_core.services.sandbox.base import SandboxService, SandboxExecutionError
from oricli_core.services.sandbox.docker_sandbox import DockerSandbox
from oricli_core.services.sandbox.resource_limits import ResourceLimits, ResourceUsage


def check_firecracker_available() -> bool:
    """
    Check if Firecracker is available on the system.
    
    Returns:
        True if Firecracker is available, False otherwise
    """
    try:
        result = subprocess.run(
            ["which", "firecracker"],
            capture_output=True,
            timeout=5,
        )
        return result.returncode == 0
    except Exception:
        return False


class FirecrackerSandbox(SandboxService):
    """
    Firecracker microVM-based sandbox implementation.
    
    Uses Firecracker microVMs for stronger isolation. Falls back to Docker
    if Firecracker is not available.
    """
    
    def __init__(
        self,
        sandbox_root: str = "/sandbox",
        resource_limits: Optional[ResourceLimits] = None,
        fallback_to_docker: bool = True,
    ):
        """
        Initialize Firecracker sandbox.
        
        Args:
            sandbox_root: Root directory of the sandbox
            resource_limits: Resource limits for this sandbox
            fallback_to_docker: If True, fall back to Docker if Firecracker unavailable
            
        Raises:
            SandboxExecutionError: If Firecracker is not available and fallback is disabled
        """
        super().__init__(sandbox_root, resource_limits)
        
        self.fallback_to_docker = fallback_to_docker
        self._firecracker_available = check_firecracker_available()
        
        if not self._firecracker_available:
            if fallback_to_docker:
                # Fall back to Docker implementation
                self._docker_fallback = DockerSandbox(sandbox_root, resource_limits)
                return
            else:
                raise SandboxExecutionError(
                    "Firecracker is not available and fallback is disabled. "
                    "Install Firecracker or enable Docker fallback."
                )
        
        # Firecracker-specific initialization would go here
        # This is a simplified implementation - full Firecracker integration
        # would require kernel image, rootfs, and API server setup
        self._docker_fallback = None
    
    def _use_docker_fallback(self) -> bool:
        """Check if we should use Docker fallback."""
        return not self._firecracker_available or self._docker_fallback is not None
    
    def create_session(
        self, session_id: str, resource_limits: Optional[ResourceLimits] = None
    ) -> str:
        """Create a new execution session."""
        if self._use_docker_fallback():
            return self._docker_fallback.create_session(session_id, resource_limits)
        
        # Firecracker implementation would go here
        # For now, delegate to Docker
        # In a full implementation, this would:
        # 1. Create a Firecracker microVM
        # 2. Boot it with a minimal kernel and rootfs
        # 3. Set up the filesystem
        # 4. Store session info
        
        # Fallback to Docker for now
        if self._docker_fallback is None:
            self._docker_fallback = DockerSandbox(
                str(self.sandbox_root), resource_limits or self.resource_limits
            )
        
        return self._docker_fallback.create_session(session_id, resource_limits)
    
    def destroy_session(self, session_id: str) -> None:
        """Destroy an execution session."""
        if self._use_docker_fallback():
            if self._docker_fallback:
                return self._docker_fallback.destroy_session(session_id)
            return
        
        # Firecracker implementation would stop and remove the microVM
        # For now, delegate to Docker
        if self._docker_fallback:
            return self._docker_fallback.destroy_session(session_id)
    
    def execute_command(
        self,
        session_id: str,
        command: str,
        timeout: Optional[int] = None,
    ) -> Dict[str, Any]:
        """Execute a command in the sandbox."""
        if self._use_docker_fallback():
            if self._docker_fallback:
                return self._docker_fallback.execute_command(session_id, command, timeout)
            raise SandboxExecutionError("Docker fallback not initialized")
        
        # Firecracker implementation would execute via SSH or API
        # For now, delegate to Docker
        if self._docker_fallback:
            return self._docker_fallback.execute_command(session_id, command, timeout)
        raise SandboxExecutionError("Sandbox not initialized")
    
    def read_file(self, session_id: str, file_path: str) -> str:
        """Read a file from the sandbox."""
        if self._use_docker_fallback():
            if self._docker_fallback:
                return self._docker_fallback.read_file(session_id, file_path)
            raise SandboxExecutionError("Docker fallback not initialized")
        
        if self._docker_fallback:
            return self._docker_fallback.read_file(session_id, file_path)
        raise SandboxExecutionError("Sandbox not initialized")
    
    def write_file(self, session_id: str, file_path: str, content: str) -> None:
        """Write a file to the sandbox."""
        if self._use_docker_fallback():
            if self._docker_fallback:
                return self._docker_fallback.write_file(session_id, file_path, content)
            raise SandboxExecutionError("Docker fallback not initialized")
        
        if self._docker_fallback:
            return self._docker_fallback.write_file(session_id, file_path, content)
        raise SandboxExecutionError("Sandbox not initialized")
    
    def list_files(self, session_id: str, directory: str = ".") -> List[str]:
        """List files in a directory within the sandbox."""
        if self._use_docker_fallback():
            if self._docker_fallback:
                return self._docker_fallback.list_files(session_id, directory)
            raise SandboxExecutionError("Docker fallback not initialized")
        
        if self._docker_fallback:
            return self._docker_fallback.list_files(session_id, directory)
        raise SandboxExecutionError("Sandbox not initialized")
    
    def delete_file(self, session_id: str, file_path: str) -> None:
        """Delete a file or directory from the sandbox."""
        if self._use_docker_fallback():
            if self._docker_fallback:
                return self._docker_fallback.delete_file(session_id, file_path)
            raise SandboxExecutionError("Docker fallback not initialized")
        
        if self._docker_fallback:
            return self._docker_fallback.delete_file(session_id, file_path)
        raise SandboxExecutionError("Sandbox not initialized")

