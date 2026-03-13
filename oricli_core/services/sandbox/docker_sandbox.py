from __future__ import annotations
"""
Docker Sandbox Implementation

Docker container-based sandbox for secure code execution.
Uses docker-py to manage isolated containers.
"""

import os
import time
import tempfile
import shutil
from pathlib import Path
from typing import Optional, Dict, Any, List

try:
    import docker
    DOCKER_AVAILABLE = True
except ImportError:
    DOCKER_AVAILABLE = False
    docker = None

from oricli_core.services.sandbox.base import SandboxService, SandboxExecutionError
from oricli_core.services.sandbox.resource_limits import ResourceLimits, ResourceUsage


class DockerSandbox(SandboxService):
    """
    Docker container-based sandbox implementation.
    
    Uses Docker containers for isolation. Each session gets its own container
    or shares containers from a pool.
    """
    
    # Base image with common tools (Bash, Python, Node.js)
    BASE_IMAGE = "python:3.11-slim"
    
    def __init__(
        self,
        sandbox_root: str = "/sandbox",
        resource_limits: Optional[ResourceLimits] = None,
        docker_client: Optional[Any] = None,
    ):
        """
        Initialize Docker sandbox.
        
        Args:
            sandbox_root: Root directory of the sandbox
            resource_limits: Resource limits for this sandbox
            docker_client: Optional Docker client (creates new one if not provided)
            
        Raises:
            SandboxExecutionError: If Docker is not available
        """
        if not DOCKER_AVAILABLE:
            raise SandboxExecutionError(
                "Docker SDK not available. Install with: pip install docker"
            )
        
        super().__init__(sandbox_root, resource_limits)
        
        try:
            self.docker_client = docker_client or docker.from_env()
            # Test connection
            self.docker_client.ping()
        except Exception as e:
            raise SandboxExecutionError(f"Failed to connect to Docker: {str(e)}")
        
        # Ensure base image exists
        self._ensure_base_image()
    
    def _ensure_base_image(self) -> None:
        """Ensure base Docker image is available."""
        try:
            self.docker_client.images.get(self.BASE_IMAGE)
        except docker.errors.ImageNotFound:
            # Pull the image
            try:
                self.docker_client.images.pull(self.BASE_IMAGE)
            except Exception as e:
                raise SandboxExecutionError(
                    f"Failed to pull base image {self.BASE_IMAGE}: {str(e)}"
                )
    
    def create_session(
        self, session_id: str, resource_limits: Optional[ResourceLimits] = None
    ) -> str:
        """Create a new execution session with a Docker container."""
        if session_id in self._sessions:
            raise SandboxExecutionError(f"Session {session_id} already exists")
        
        limits = resource_limits or self.resource_limits
        
        try:
            # Create container with resource limits
            container = self.docker_client.containers.create(
                image=self.BASE_IMAGE,
                command="sleep infinity",  # Keep container alive
                name=f"oricli-sandbox-{session_id}",
                working_dir=str(self.sandbox_root),
                mem_limit=f"{limits.memory_mb}m",
                cpu_quota=int(limits.cpu_cores * 100000),  # Docker CPU quota
                cpu_period=100000,  # 100ms period
                network_disabled=True,  # No network access
                read_only=False,  # Allow writes within container
                volumes={},  # No host mounts (isolated)
                detach=True,
                stdin_open=True,
                tty=False,
            )
            
            # Start container
            container.start()
            
            # Install Node.js if not present (for Node.js execution support)
            # This is done once per container
            exec_result = container.exec_run(
                "bash -c 'command -v node >/dev/null 2>&1 || (apt-get update -qq && apt-get install -y -qq nodejs npm >/dev/null 2>&1)'",
                user="root",
            )
            
            # Store session info
            self._sessions[session_id] = {
                "container_id": container.id,
                "container": container,
                "created_at": time.time(),
                "resource_limits": limits,
            }
            
            return session_id
        except Exception as e:
            raise SandboxExecutionError(f"Failed to create session: {str(e)}")
    
    def destroy_session(self, session_id: str) -> None:
        """Destroy an execution session and remove its container."""
        if session_id not in self._sessions:
            return
        
        session_info = self._sessions[session_id]
        container = session_info.get("container")
        
        try:
            if container:
                try:
                    container.stop(timeout=5)
                except Exception:
                    pass
                try:
                    container.remove(force=True)
                except Exception:
                    pass
        except Exception as e:
            # Log but don't raise - cleanup should be best-effort
            print(f"Warning: Failed to remove container for session {session_id}: {e}")
        
        del self._sessions[session_id]
    
    def execute_command(
        self,
        session_id: str,
        command: str,
        timeout: Optional[int] = None,
    ) -> Dict[str, Any]:
        """Execute a command in the Docker container."""
        if session_id not in self._sessions:
            raise SandboxExecutionError(f"Session {session_id} does not exist")
        
        session_info = self._sessions[session_id]
        container = session_info["container"]
        limits = session_info["resource_limits"]
        
        exec_timeout = timeout or limits.timeout_seconds
        
        start_time = time.time()
        
        try:
            # Execute command in container
            exec_result = container.exec_run(
                f"bash -c {command!r}",
                workdir=str(self.sandbox_root),
                user="nobody",  # Non-root user for security
                timeout=exec_timeout,
            )
            
            execution_time = time.time() - start_time
            
            # Extract output
            stdout = exec_result.output.decode("utf-8", errors="replace") if exec_result.output else ""
            exit_code = exec_result.exit_code or 0
            
            # For simplicity, assume stderr goes to stdout in exec_run
            # In production, you'd want to separate stdout/stderr
            stderr = ""
            if exit_code != 0:
                stderr = stdout  # Treat non-zero exit as stderr
            
            # Create resource usage (simplified - Docker doesn't easily expose per-exec stats)
            resource_usage = ResourceUsage(
                cpu_percent=0.0,  # Would need cgroups to measure accurately
                memory_mb=0.0,  # Would need cgroups to measure accurately
                disk_mb=0.0,
                execution_time=execution_time,
            )
            
            return {
                "stdout": stdout,
                "stderr": stderr,
                "exit_code": exit_code,
                "execution_time": execution_time,
                "resource_usage": resource_usage,
            }
        except docker.errors.ContainerError as e:
            execution_time = time.time() - start_time
            return {
                "stdout": "",
                "stderr": str(e),
                "exit_code": e.exit_status or 1,
                "execution_time": execution_time,
                "resource_usage": ResourceUsage(execution_time=execution_time),
            }
        except Exception as e:
            raise SandboxExecutionError(f"Command execution failed: {str(e)}")
    
    def read_file(self, session_id: str, file_path: str) -> str:
        """Read a file from the Docker container."""
        if session_id not in self._sessions:
            raise SandboxExecutionError(f"Session {session_id} does not exist")
        
        session_info = self._sessions[session_id]
        container = session_info["container"]
        
        # Ensure path is within sandbox
        full_path = self.sandbox_root / file_path.lstrip("/")
        
        try:
            # Use docker exec to read file
            exec_result = container.exec_run(
                f"cat {full_path!r}",
                workdir=str(self.sandbox_root),
                user="nobody",
            )
            
            if exec_result.exit_code != 0:
                raise SandboxExecutionError(f"Failed to read file: {file_path}")
            
            return exec_result.output.decode("utf-8", errors="replace")
        except Exception as e:
            raise SandboxExecutionError(f"Failed to read file {file_path}: {str(e)}")
    
    def write_file(self, session_id: str, file_path: str, content: str) -> None:
        """Write a file to the Docker container."""
        if session_id not in self._sessions:
            raise SandboxExecutionError(f"Session {session_id} does not exist")
        
        session_info = self._sessions[session_id]
        container = session_info["container"]
        
        # Ensure path is within sandbox
        full_path = self.sandbox_root / file_path.lstrip("/")
        dir_path = full_path.parent
        
        try:
            # Create directory if needed
            if str(dir_path) != str(self.sandbox_root):
                container.exec_run(
                    f"mkdir -p {dir_path!r}",
                    workdir=str(self.sandbox_root),
                    user="nobody",
                )
            
            # Write file using echo (safe for simple content)
            # For complex content with special chars, use base64 or a temp file
            import base64
            content_b64 = base64.b64encode(content.encode("utf-8")).decode("ascii")
            exec_result = container.exec_run(
                f"bash -c 'echo {content_b64!r} | base64 -d > {full_path!r}'",
                workdir=str(self.sandbox_root),
                user="nobody",
            )
            
            if exec_result.exit_code != 0:
                raise SandboxExecutionError(f"Failed to write file: {file_path}")
        except Exception as e:
            raise SandboxExecutionError(f"Failed to write file {file_path}: {str(e)}")
    
    def list_files(self, session_id: str, directory: str = ".") -> List[str]:
        """List files in a directory within the Docker container."""
        if session_id not in self._sessions:
            raise SandboxExecutionError(f"Session {session_id} does not exist")
        
        session_info = self._sessions[session_id]
        container = session_info["container"]
        
        # Ensure path is within sandbox
        full_path = self.sandbox_root / directory.lstrip("/")
        
        try:
            exec_result = container.exec_run(
                f"ls -1 {full_path!r}",
                workdir=str(self.sandbox_root),
                user="nobody",
            )
            
            if exec_result.exit_code != 0:
                raise SandboxExecutionError(f"Failed to list directory: {directory}")
            
            output = exec_result.output.decode("utf-8", errors="replace").strip()
            if not output:
                return []
            
            return [line for line in output.split("\n") if line.strip()]
        except Exception as e:
            raise SandboxExecutionError(f"Failed to list directory {directory}: {str(e)}")
    
    def delete_file(self, session_id: str, file_path: str) -> None:
        """Delete a file or directory from the Docker container."""
        if session_id not in self._sessions:
            raise SandboxExecutionError(f"Session {session_id} does not exist")
        
        session_info = self._sessions[session_id]
        container = session_info["container"]
        
        # Ensure path is within sandbox (and not the root itself)
        full_path = self.sandbox_root / file_path.lstrip("/")
        if full_path == self.sandbox_root:
            raise SandboxExecutionError("Cannot delete sandbox root")
        
        try:
            exec_result = container.exec_run(
                f"rm -rf {full_path!r}",
                workdir=str(self.sandbox_root),
                user="nobody",
            )
            
            if exec_result.exit_code != 0:
                raise SandboxExecutionError(f"Failed to delete: {file_path}")
        except Exception as e:
            raise SandboxExecutionError(f"Failed to delete {file_path}: {str(e)}")

