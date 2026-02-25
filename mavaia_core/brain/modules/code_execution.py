from __future__ import annotations
"""
Code Execution Module

Secure code execution in isolated sandboxes with allowlist-based validation.
Supports Bash, Python, and Node.js execution.
"""

import uuid
import time
import ast
import re
from typing import Dict, Any, Optional, List
from pathlib import Path
import logging

from mavaia_core.brain.base_module import BaseBrainModule, ModuleMetadata
from mavaia_core.exceptions import (
    InvalidParameterError,
    ModuleInitializationError,
    ModuleOperationError,
)

# Lazy imports to avoid timeout during module discovery
SandboxService = None
DockerSandbox = None
FirecrackerSandbox = None
SandboxPoolManager = None
ResourceLimits = None
CommandValidator = None
CommandValidationError = None
SandboxExecutionError = None
_SANDBOX_IMPORT_FAILURE_LOGGED = False

logger = logging.getLogger(__name__)

def _lazy_import_sandbox():
    """Lazy import sandbox services only when needed"""
    global SandboxService, DockerSandbox, FirecrackerSandbox, SandboxPoolManager
    global ResourceLimits, CommandValidator, CommandValidationError, SandboxExecutionError
    global _SANDBOX_IMPORT_FAILURE_LOGGED
    if SandboxService is None:
        try:
            from mavaia_core.services.sandbox import (
                SandboxService as SS,
                DockerSandbox as DS,
                FirecrackerSandbox as FS,
                SandboxPoolManager as SPM,
                ResourceLimits as RL,
                CommandValidator as CV,
                CommandValidationError as CVE,
                SandboxExecutionError as SEE,
            )
            SandboxService = SS
            DockerSandbox = DS
            FirecrackerSandbox = FS
            SandboxPoolManager = SPM
            ResourceLimits = RL
            CommandValidator = CV
            CommandValidationError = CVE
            SandboxExecutionError = SEE
        except ImportError:
            if not _SANDBOX_IMPORT_FAILURE_LOGGED:
                _SANDBOX_IMPORT_FAILURE_LOGGED = True
                logger.debug(
                    "Sandbox services not available",
                    exc_info=True,
                    extra={"module_name": "code_execution"},
                )


class CodeExecutionModule(BaseBrainModule):
    """
    Secure code execution module with sandbox isolation.
    
    Provides safe execution of Bash, Python, and Node.js code in isolated
    sandboxes with strict allowlist-based validation.
    """
    
    def __init__(self):
        """Initialize code execution module."""
        super().__init__()
        self._sessions: Dict[str, Dict[str, Any]] = {}
        self._sandbox_service: Optional[Any] = None
        self._pool_manager: Optional[Any] = None
        self._command_validator = None
        self._default_resource_limits = None
        self._session_timeout = 3600  # 1 hour
        self._docker_available = None  # Will be checked lazily
        self._initialization_error = None  # Store any initialization errors
    
    @property
    def metadata(self) -> ModuleMetadata:
        """Return module metadata."""
        return ModuleMetadata(
            name="code_execution",
            version="1.0.0",
            description="Secure code execution in isolated sandboxes with allowlist validation",
            operations=[
                "execute_command",
                "execute_python",
                "execute_node",
                "read_file",
                "write_file",
                "list_files",
                "delete_file",
                "create_session",
                "destroy_session",
            ],
            dependencies=[
                "docker>=6.0.0",  # Must be installed in virtual environment: pip install docker
                "psutil>=5.9.0"
            ],
            enabled=True,
            model_required=False,
        )
    
    def initialize(self) -> bool:
        """
        Initialize the module and set up sandbox service.
        
        Returns True even if Docker is not available - actual initialization
        happens lazily when operations are executed.
        
        IMPORTANT: Docker daemon must be running when operations are executed.
        The Docker Python client must be installed in your virtual environment.
        """
        # Lazy initialization - don't create sandboxes at import time
        # They'll be initialized when first needed
        # Don't check Docker availability here to avoid blocking discovery
        # Docker will be checked when execute() is called
        return True
    
    def _check_docker_availability(self) -> bool:
        """
        Check if Docker is available without initializing sandboxes.
        
        IMPORTANT: Docker daemon must be running on the system.
        The Docker Python client must be installed in your virtual environment.
        """
        if self._docker_available is not None:
            return self._docker_available
        
        # First check if docker Python package is available
        try:
            import docker
        except ImportError:
            self._docker_available = False
            self._initialization_error = (
                "Docker Python client not installed in virtual environment. "
                "Install with: pip install docker"
            )
            return False
        
        # Check if sandbox services are available
        _lazy_import_sandbox()
        if SandboxService is None:
            self._docker_available = False
            self._initialization_error = "Sandbox services not available"
            return False
        
        # Try to check Docker daemon availability
        try:
            # Use docker.from_env() which respects DOCKER_HOST environment variable
            # and will use the Docker socket from the environment
            client = docker.from_env()
            client.ping()  # Quick check if Docker daemon is running and accessible
            client.close()
            self._docker_available = True
            return True
        except docker.errors.DockerException as e:
            # Docker daemon not running or not accessible
            self._docker_available = False
            error_msg = str(e)
            if "Connection" in error_msg or "No such file" in error_msg or "FileNotFoundError" in error_msg:
                self._initialization_error = (
                    "Docker daemon is not running or not accessible.\n"
                    "To fix:\n"
                    "1. Ensure Docker Desktop (or Docker daemon) is running on your system\n"
                    "2. Make sure you're in your virtual environment: source venv/bin/activate\n"
                    "3. Verify Docker is accessible: docker ps\n"
                    "4. The Docker Python client is installed in your venv, but the Docker daemon must be running separately"
                )
            else:
                self._initialization_error = f"Docker connection failed: {e}"
            return False
        except Exception as e:
            # Other errors
            self._docker_available = False
            error_msg = str(e)
            self._initialization_error = (
                f"Docker availability check failed: {e}\n"
                "Ensure:\n"
                "1. Docker daemon is running (start Docker Desktop or docker service)\n"
                "2. You're in your virtual environment: source venv/bin/activate\n"
                "3. Docker Python client is installed: pip install docker"
            )
            return False
    
    def _ensure_initialized(self):
        """Ensure sandbox service is initialized"""
        # Check Docker availability first
        if not self._check_docker_availability():
            raise ModuleInitializationError(
                module_name=self.metadata.name,
                reason=self._initialization_error or "Docker is not available",
            )
        
        _lazy_import_sandbox()
        if SandboxService is None:
            raise ModuleInitializationError(
                module_name=self.metadata.name,
                reason="Sandbox services not available",
            )
        
        if self._command_validator is None:
            self._command_validator = CommandValidator()
        if self._default_resource_limits is None:
            self._default_resource_limits = ResourceLimits()
        
        if self._sandbox_service is None or self._pool_manager is None:
            try:
                # Try Firecracker first, fallback to Docker
                try:
                    self._sandbox_service = FirecrackerSandbox(
                        sandbox_root="/sandbox",
                        resource_limits=self._default_resource_limits,
                        fallback_to_docker=True,
                    )
                except Exception:
                    # Fallback to Docker
                    self._sandbox_service = DockerSandbox(
                        sandbox_root="/sandbox",
                        resource_limits=self._default_resource_limits,
                    )
                
                # Initialize pool manager
                self._pool_manager = SandboxPoolManager(
                    sandbox_service=self._sandbox_service,
                    pool_size=5,
                    max_pool_size=20,
                    session_timeout=self._session_timeout,
                )
            except Exception as e:
                # Store error but don't print during discovery
                # Error will be raised when module is actually used
                self._initialization_error = f"Failed to initialize sandbox service: {e}"
                logger.debug(
                    "Sandbox initialization failed",
                    exc_info=True,
                    extra={"module_name": "code_execution", "error_type": type(e).__name__},
                )
                raise ModuleInitializationError(
                    module_name=self.metadata.name,
                    reason="Failed to initialize sandbox service",
                ) from e
    
    def cleanup(self) -> None:
        """Clean up resources."""
        # Clean up all sessions
        for session_id in list(self._sessions.keys()):
            try:
                self._destroy_session_internal(session_id)
            except Exception:
                pass
        
        # Shutdown pool manager
        if self._pool_manager:
            try:
                self._pool_manager.shutdown()
            except Exception:
                pass
    
    def execute(self, operation: str, params: Dict[str, Any]) -> Dict[str, Any]:
        """
        Execute a code execution operation.
        
        IMPORTANT: Docker daemon must be running on your system.
        The Docker Python client must be installed in your virtual environment.
        
        Setup:
        1. Activate your virtual environment: source venv/bin/activate
        2. Install Docker Python client: pip install docker
        3. Start Docker Desktop (or Docker daemon) on your system
        4. Verify Docker is accessible: docker ps
        """
        # Lazy initialize on first use
        try:
            self._ensure_initialized()
        except ModuleInitializationError as e:
            # Provide clear error message when Docker is not available
            error_msg = str(e)
            if "Docker" in error_msg or "docker" in error_msg or "daemon" in error_msg.lower():
                raise ModuleOperationError(
                    self.metadata.name,
                    operation,
                    f"{error_msg}\n\n"
                    "Docker Setup Instructions:\n"
                    "1. Activate your virtual environment: source venv/bin/activate\n"
                    "2. Install Docker Python client (if not installed): pip install docker\n"
                    "3. Start Docker Desktop or Docker daemon on your system\n"
                    "4. Verify Docker is accessible: docker ps\n"
                    "5. The Docker Python client connects to the Docker daemon - both must be available"
                )
            raise
        
        if not self._sandbox_service:
            raise ModuleOperationError(
                self.metadata.name,
                operation,
                "Sandbox service not initialized",
            )
        
        try:
            if operation == "execute_command":
                return self._execute_command(params)
            elif operation == "execute_python":
                return self._execute_python(params)
            elif operation == "execute_node":
                return self._execute_node(params)
            elif operation == "read_file":
                return self._read_file(params)
            elif operation == "write_file":
                return self._write_file(params)
            elif operation == "list_files":
                return self._list_files(params)
            elif operation == "delete_file":
                return self._delete_file(params)
            elif operation == "create_session":
                return self._create_session(params)
            elif operation == "destroy_session":
                return self._destroy_session(params)
            else:
                raise InvalidParameterError(
                    "operation",
                    str(operation),
                    "Unknown operation for code_execution",
                )
        except (CommandValidationError, SandboxExecutionError) as e:
            raise ModuleOperationError(
                self.metadata.name,
                operation,
                str(e),
            )
        except (InvalidParameterError, ModuleInitializationError, ModuleOperationError):
            raise
        except Exception as e:
            logger.debug(
                "code_execution operation failed",
                exc_info=True,
                extra={"module_name": "code_execution", "operation": str(operation), "error_type": type(e).__name__},
            )
            raise ModuleOperationError(
                self.metadata.name,
                operation,
                "Unexpected error during code execution operation",
            )
    
    def _get_or_create_session(self, session_id: Optional[str] = None) -> str:
        """Get existing session or create a new one."""
        if session_id and session_id in self._sessions:
            return session_id
        
        # Create new session
        new_session_id = session_id or str(uuid.uuid4())
        
        # Get session from pool or create new one
        if self._pool_manager:
            pool_session_id = self._pool_manager.get_session()
        else:
            pool_session_id = new_session_id
            self._sandbox_service.create_session(pool_session_id)
        
        self._sessions[new_session_id] = {
            "pool_session_id": pool_session_id,
            "created_at": time.time(),
            "last_used": time.time(),
        }
        
        return new_session_id
    
    def _execute_command(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """Execute a bash command."""
        command = params.get("command", "")
        session_id = params.get("session_id")
        resource_limits = self._parse_resource_limits(params.get("resource_limits"))
        
        if not command:
            raise InvalidParameterError("command", "", "Command cannot be empty")
        
        # Validate command against allowlist
        is_valid, error_msg = self._command_validator.validate_bash_command(command)
        if not is_valid:
            raise CommandValidationError(f"Command validation failed: {error_msg}")
        
        # Get or create session
        session_id = self._get_or_create_session(session_id)
        session_info = self._sessions[session_id]
        pool_session_id = session_info["pool_session_id"]
        session_info["last_used"] = time.time()
        
        # Execute command
        timeout = resource_limits.timeout_seconds if resource_limits else None
        result = self._sandbox_service.execute_command(
            pool_session_id,
            command,
            timeout=timeout,
        )
        
        return {
            "session_id": session_id,
            "success": result["exit_code"] == 0,
            "stdout": result["stdout"],
            "stderr": result["stderr"],
            "exit_code": result["exit_code"],
            "execution_time": result["execution_time"],
            "resource_usage": result["resource_usage"].to_dict(),
        }
    
    def _execute_python(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """Execute Python code."""
        code = params.get("code", "")
        session_id = params.get("session_id")
        resource_limits = self._parse_resource_limits(params.get("resource_limits"))
        
        if not code:
            raise InvalidParameterError("code", "", "Code cannot be empty")
        
        # Validate Python code for dangerous imports/operations
        self._validate_python_code(code)
        
        # Get or create session
        session_id = self._get_or_create_session(session_id)
        session_info = self._sessions[session_id]
        pool_session_id = session_info["pool_session_id"]
        session_info["last_used"] = time.time()
        
        # Write code to temporary file
        script_path = f"/tmp/script_{uuid.uuid4().hex[:8]}.py"
        self._sandbox_service.write_file(pool_session_id, script_path, code)
        
        try:
            # Execute Python script
            command = f"python3 {script_path}"
            timeout = resource_limits.timeout_seconds if resource_limits else None
            result = self._sandbox_service.execute_command(
                pool_session_id,
                command,
                timeout=timeout,
            )
            
            return {
                "session_id": session_id,
                "success": result["exit_code"] == 0,
                "stdout": result["stdout"],
                "stderr": result["stderr"],
                "exit_code": result["exit_code"],
                "execution_time": result["execution_time"],
                "resource_usage": result["resource_usage"].to_dict(),
            }
        finally:
            # Clean up script file
            try:
                self._sandbox_service.delete_file(pool_session_id, script_path)
            except Exception:
                pass
    
    def _execute_node(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """Execute Node.js code."""
        code = params.get("code", "")
        session_id = params.get("session_id")
        resource_limits = self._parse_resource_limits(params.get("resource_limits"))
        
        if not code:
            raise InvalidParameterError("code", "", "Code cannot be empty")
        
        # Validate Node.js code for dangerous requires/operations
        self._validate_node_code(code)
        
        # Get or create session
        session_id = self._get_or_create_session(session_id)
        session_info = self._sessions[session_id]
        pool_session_id = session_info["pool_session_id"]
        session_info["last_used"] = time.time()
        
        # Write code to temporary file
        script_path = f"/tmp/script_{uuid.uuid4().hex[:8]}.js"
        self._sandbox_service.write_file(pool_session_id, script_path, code)
        
        try:
            # Execute Node.js script
            command = f"node {script_path}"
            timeout = resource_limits.timeout_seconds if resource_limits else None
            result = self._sandbox_service.execute_command(
                pool_session_id,
                command,
                timeout=timeout,
            )
            
            return {
                "session_id": session_id,
                "success": result["exit_code"] == 0,
                "stdout": result["stdout"],
                "stderr": result["stderr"],
                "exit_code": result["exit_code"],
                "execution_time": result["execution_time"],
                "resource_usage": result["resource_usage"].to_dict(),
            }
        finally:
            # Clean up script file
            try:
                self._sandbox_service.delete_file(pool_session_id, script_path)
            except Exception:
                pass
    
    def _validate_python_code(self, code: str) -> None:
        """Validate Python code for dangerous imports and operations."""
        try:
            tree = ast.parse(code)
            
            for node in ast.walk(tree):
                # Check for imports
                if isinstance(node, (ast.Import, ast.ImportFrom)):
                    module_name = node.module if isinstance(node, ast.ImportFrom) else ""
                    if isinstance(node, ast.Import):
                        for alias in node.names:
                            module_name = alias.name
                            is_valid, error_msg = self._command_validator.validate_python_import(
                                module_name
                            )
                            if not is_valid:
                                raise CommandValidationError(
                                    f"Python import validation failed: {error_msg}"
                                )
                    else:
                        is_valid, error_msg = self._command_validator.validate_python_import(
                            module_name
                        )
                        if not is_valid:
                            raise CommandValidationError(
                                f"Python import validation failed: {error_msg}"
                            )
                
                # Check for eval, exec, compile calls
                if isinstance(node, ast.Call):
                    if isinstance(node.func, ast.Name):
                        if node.func.id in ("eval", "exec", "compile", "__import__"):
                            raise CommandValidationError(
                                f"Dangerous Python operation: {node.func.id}"
                            )
        except SyntaxError as e:
            raise CommandValidationError(f"Invalid Python syntax: {str(e)}")
        except CommandValidationError:
            raise
        except Exception as e:
            # If AST parsing fails for other reasons, do basic string checks
            dangerous_patterns = [
                r"__import__\s*\(",
                r"eval\s*\(",
                r"exec\s*\(",
                r"compile\s*\(",
            ]
            for pattern in dangerous_patterns:
                if re.search(pattern, code):
                    raise CommandValidationError(
                        f"Dangerous Python pattern detected: {pattern}"
                    )
    
    def _validate_node_code(self, code: str) -> None:
        """Validate Node.js code for dangerous requires and operations."""
        # Basic regex-based validation (could be enhanced with proper JS parser)
        # Check for require() statements
        require_pattern = r"require\s*\(\s*['\"]([^'\"]+)['\"]"
        matches = re.findall(require_pattern, code)
        
        for module_name in matches:
            is_valid, error_msg = self._command_validator.validate_node_require(module_name)
            if not is_valid:
                raise CommandValidationError(
                    f"Node.js require validation failed: {error_msg}"
                )
        
        # Check for dangerous functions
        dangerous_patterns = [
            r"eval\s*\(",
            r"Function\s*\(",
            r"child_process",
            r"vm\.",
        ]
        for pattern in dangerous_patterns:
            if re.search(pattern, code):
                raise CommandValidationError(
                    f"Dangerous Node.js pattern detected: {pattern}"
                )
    
    def _read_file(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """Read a file from the sandbox."""
        file_path = params.get("file_path", "")
        session_id = params.get("session_id")
        
        if not file_path:
            raise InvalidParameterError("file_path", "", "File path cannot be empty")
        
        # Validate path
        is_valid, error_msg = self._command_validator.validate_path(file_path)
        if not is_valid:
            raise CommandValidationError(f"Path validation failed: {error_msg}")
        
        # Get or create session
        session_id = self._get_or_create_session(session_id)
        session_info = self._sessions[session_id]
        pool_session_id = session_info["pool_session_id"]
        session_info["last_used"] = time.time()
        
        # Read file
        content = self._sandbox_service.read_file(pool_session_id, file_path)
        
        return {
            "session_id": session_id,
            "success": True,
            "file_content": content,
            "file_path": file_path,
        }
    
    def _write_file(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """Write a file to the sandbox."""
        file_path = params.get("file_path", "")
        content = params.get("content", "")
        session_id = params.get("session_id")
        
        if not file_path:
            raise InvalidParameterError("file_path", "", "File path cannot be empty")
        
        # Validate path
        is_valid, error_msg = self._command_validator.validate_path(file_path)
        if not is_valid:
            raise CommandValidationError(f"Path validation failed: {error_msg}")
        
        # Get or create session
        session_id = self._get_or_create_session(session_id)
        session_info = self._sessions[session_id]
        pool_session_id = session_info["pool_session_id"]
        session_info["last_used"] = time.time()
        
        # Write file
        self._sandbox_service.write_file(pool_session_id, file_path, content)
        
        return {
            "session_id": session_id,
            "success": True,
            "file_path": file_path,
        }
    
    def _list_files(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """List files in a directory."""
        directory = params.get("directory", ".")
        session_id = params.get("session_id")
        
        # Validate path
        is_valid, error_msg = self._command_validator.validate_path(directory)
        if not is_valid:
            raise CommandValidationError(f"Path validation failed: {error_msg}")
        
        # Get or create session
        session_id = self._get_or_create_session(session_id)
        session_info = self._sessions[session_id]
        pool_session_id = session_info["pool_session_id"]
        session_info["last_used"] = time.time()
        
        # List files
        files = self._sandbox_service.list_files(pool_session_id, directory)
        
        return {
            "session_id": session_id,
            "success": True,
            "files": files,
            "directory": directory,
        }
    
    def _delete_file(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """Delete a file from the sandbox."""
        file_path = params.get("file_path", "")
        session_id = params.get("session_id")
        
        if not file_path:
            raise InvalidParameterError("file_path", "", "File path cannot be empty")
        
        # Validate path
        is_valid, error_msg = self._command_validator.validate_path(file_path)
        if not is_valid:
            raise CommandValidationError(f"Path validation failed: {error_msg}")
        
        # Get or create session
        session_id = self._get_or_create_session(session_id)
        session_info = self._sessions[session_id]
        pool_session_id = session_info["pool_session_id"]
        session_info["last_used"] = time.time()
        
        # Delete file
        self._sandbox_service.delete_file(pool_session_id, file_path)
        
        return {
            "session_id": session_id,
            "success": True,
            "file_path": file_path,
        }
    
    def _create_session(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """Create a new execution session."""
        session_id = params.get("session_id") or str(uuid.uuid4())
        resource_limits = self._parse_resource_limits(params.get("resource_limits"))
        
        if session_id in self._sessions:
            raise InvalidParameterError(
                "session_id", session_id, "Session already exists"
            )
        
        # Get session from pool or create new one
        if self._pool_manager:
            pool_session_id = self._pool_manager.get_session()
        else:
            pool_session_id = session_id
            self._sandbox_service.create_session(pool_session_id, resource_limits)
        
        self._sessions[session_id] = {
            "pool_session_id": pool_session_id,
            "created_at": time.time(),
            "last_used": time.time(),
        }
        
        return {
            "session_id": session_id,
            "success": True,
        }
    
    def _destroy_session(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """Destroy an execution session."""
        session_id = params.get("session_id")
        
        if not session_id:
            raise InvalidParameterError("session_id", "", "Session ID is required")
        
        self._destroy_session_internal(session_id)
        
        return {
            "session_id": session_id,
            "success": True,
        }
    
    def _destroy_session_internal(self, session_id: str) -> None:
        """Internal method to destroy a session."""
        if session_id not in self._sessions:
            return
        
        session_info = self._sessions[session_id]
        pool_session_id = session_info["pool_session_id"]
        
        # Return to pool or destroy
        if self._pool_manager:
            self._pool_manager.return_session(pool_session_id, reuse=True)
        else:
            self._sandbox_service.destroy_session(pool_session_id)
        
        del self._sessions[session_id]
    
    def _parse_resource_limits(self, limits_dict: Optional[Dict[str, Any]]) -> Optional[ResourceLimits]:
        """Parse resource limits from dictionary."""
        if not limits_dict:
            return None
        
        try:
            return ResourceLimits.from_dict(limits_dict)
        except Exception:
            return None

