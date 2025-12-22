"""
Shell Sandbox Service
Safe shell command execution service with strict allowlist and validation
Converted from Swift ShellSandboxService.swift
"""

from typing import Any, Dict, List, Optional
import os
import subprocess
import stat
from pathlib import Path
from datetime import datetime
import logging

from mavaia_core.brain.base_module import BaseBrainModule, ModuleMetadata
from mavaia_core.exceptions import InvalidParameterError, ModuleOperationError

logger = logging.getLogger(__name__)


class SandboxProcessInfo:
    """Sandbox process information"""

    def __init__(self, pid: int, name: str, command: str):
        self.pid = pid
        self.name = name
        self.command = command

    def to_dict(self) -> Dict[str, Any]:
        return {
            "pid": self.pid,
            "name": self.name,
            "command": self.command,
        }


class FileMetadata:
    """File metadata"""

    def __init__(
        self,
        path: str,
        size: int,
        modification_date: Optional[float],
        is_directory: bool,
        permissions: Optional[str],
    ):
        self.path = path
        self.size = size
        self.modification_date = modification_date
        self.is_directory = is_directory
        self.permissions = permissions

    def to_dict(self) -> Dict[str, Any]:
        return {
            "path": self.path,
            "size": self.size,
            "modification_date": self.modification_date,
            "is_directory": self.is_directory,
            "permissions": self.permissions,
        }


class ShellSandboxServiceModule(BaseBrainModule):
    """Safe shell command execution service"""

    def __init__(self):
        super().__init__()
        # Allowed commands with their safe flags
        self.allowed_commands = {
            "ls", "pwd", "whoami", "date", "uname",
            "stat", "file", "ps", "df", "du",
        }

        # Dangerous patterns to block
        self.dangerous_patterns = [
            ">", ">>", "|", "&", ";", "&&", "||",
            "rm", "sudo", "chmod", "chown", "kill", "delete",
            "mv", "cp", "mkdir", "rmdir", "touch",
        ]

        # Allowed roots for filesystem reads (resolved path must be within one of these)
        self._allowed_roots: List[Path] = [
            Path.home(),
            Path("/workspace"),
            Path("/tmp"),
            Path("/var/tmp"),
        ]

    @property
    def metadata(self) -> ModuleMetadata:
        return ModuleMetadata(
            name="shell_sandbox_service",
            version="1.0.0",
            description="Safe shell command execution service with strict allowlist and validation",
            operations=[
                "list_folder",
                "list_running_processes",
                "read_file_metadata",
                "execute_safe_command",
            ],
            dependencies=[],
            model_required=False,
        )

    def initialize(self) -> bool:
        """Initialize the module"""
        return True

    def execute(self, operation: str, params: Dict[str, Any]) -> Dict[str, Any]:
        """Execute an operation"""
        match operation:
            case "list_folder":
                return self._list_folder(params)
            case "list_running_processes":
                return self._list_running_processes(params)
            case "read_file_metadata":
                return self._read_file_metadata(params)
            case "execute_safe_command":
                return self._execute_safe_command(params)
            case _:
                raise InvalidParameterError("operation", str(operation), "Unknown operation for shell_sandbox_service")

    def _list_folder(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """List folder contents"""
        path = params.get("path", "")
        if path is None:
            path = ""
        if not isinstance(path, str):
            raise InvalidParameterError("path", str(type(path).__name__), "path must be a string")

        # Validate path
        if not self._is_valid_path(path):
            return {
                "success": False,
                "error": f"Invalid path: {path}",
            }

        try:
            if not os.path.exists(path):
                return {
                    "success": False,
                    "error": f"Path not found: {path}",
                }

            if not os.path.isdir(path):
                return {
                    "success": False,
                    "error": f"Path is not a directory: {path}",
                }

            contents = os.listdir(path)
            return {
                "success": True,
                "result": {
                    "contents": contents,
                    "count": len(contents),
                },
            }
        except Exception as e:
            logger.debug(
                "list_folder failed",
                exc_info=True,
                extra={"module_name": "shell_sandbox_service", "operation": "list_folder", "error_type": type(e).__name__},
            )
            return {
                "success": False,
                "error": "Failed to list folder",
            }

    def _list_running_processes(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """List running processes"""
        filter_name = params.get("filter_name")
        max_results = params.get("max_results", 50)
        if filter_name is not None and not isinstance(filter_name, str):
            raise InvalidParameterError("filter_name", str(type(filter_name).__name__), "filter_name must be a string")
        try:
            max_results_int = int(max_results)
        except (TypeError, ValueError):
            raise InvalidParameterError("max_results", str(max_results), "max_results must be an integer")
        if max_results_int < 1:
            raise InvalidParameterError("max_results", str(max_results_int), "max_results must be >= 1")

        try:
            # Use ps command with safe flags only
            result = subprocess.run(
                ["ps", "-eo", "pid,comm,command"],
                capture_output=True,
                text=True,
                timeout=5,
            )

            if result.returncode != 0:
                return {
                    "success": False,
                    "error": "Failed to list processes",
                }

            processes: List[SandboxProcessInfo] = []
            lines = result.stdout.strip().split("\n")

            for i, line in enumerate(lines):
                if i == 0:
                    continue  # Skip header
                if len(processes) >= max_results_int:
                    break

                components = line.strip().split()
                if len(components) < 3:
                    continue

                try:
                    pid = int(components[0])
                    process_name = components[1]
                    command = " ".join(components[2:])

                    # Apply filter if provided
                    if filter_name and filter_name.lower() not in process_name.lower():
                        continue

                    processes.append(SandboxProcessInfo(pid=pid, name=process_name, command=command))
                except (ValueError, IndexError):
                    continue

            return {
                "success": True,
                "result": {
                    "processes": [p.to_dict() for p in processes],
                    "count": len(processes),
                },
            }
        except Exception as e:
            logger.debug(
                "list_running_processes failed",
                exc_info=True,
                extra={
                    "module_name": "shell_sandbox_service",
                    "operation": "list_running_processes",
                    "error_type": type(e).__name__,
                },
            )
            return {
                "success": False,
                "error": "Failed to list processes",
            }

    def _read_file_metadata(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """Read file metadata"""
        path = params.get("path", "")
        if path is None:
            path = ""
        if not isinstance(path, str):
            raise InvalidParameterError("path", str(type(path).__name__), "path must be a string")

        # Validate path
        if not self._is_valid_path(path):
            return {
                "success": False,
                "error": f"Invalid path: {path}",
            }

        try:
            if not os.path.exists(path):
                return {
                    "success": False,
                    "error": f"Path not found: {path}",
                }

            stat_info = os.stat(path)
            size = stat_info.st_size
            modification_date = stat_info.st_mtime
            is_directory = os.path.isdir(path)
            permissions = oct(stat_info.st_mode)[-3:]

            metadata = FileMetadata(
                path=path,
                size=size,
                modification_date=modification_date,
                is_directory=is_directory,
                permissions=permissions,
            )

            return {
                "success": True,
                "result": metadata.to_dict(),
            }
        except Exception as e:
            logger.debug(
                "read_file_metadata failed",
                exc_info=True,
                extra={"module_name": "shell_sandbox_service", "operation": "read_file_metadata", "error_type": type(e).__name__},
            )
            return {
                "success": False,
                "error": "Failed to read file metadata",
            }

    def _execute_safe_command(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """Execute a safe shell command"""
        command = params.get("command", "")
        arguments = params.get("arguments", [])
        if command is None:
            command = ""
        if arguments is None:
            arguments = []
        if not isinstance(command, str):
            raise InvalidParameterError("command", str(type(command).__name__), "command must be a string")
        if not isinstance(arguments, list):
            raise InvalidParameterError("arguments", str(type(arguments).__name__), "arguments must be a list")
        if not all(isinstance(a, str) for a in arguments):
            raise InvalidParameterError("arguments", "non-string", "all arguments must be strings")

        # Validate command
        if command not in self.allowed_commands:
            return {
                "success": False,
                "error": f"Command not allowed: {command}",
            }

        # Check for dangerous patterns in arguments
        all_args = " ".join(arguments)
        for pattern in self.dangerous_patterns:
            if pattern in all_args:
                return {
                    "success": False,
                    "error": f"Dangerous pattern detected: {pattern}",
                }

        try:
            result = subprocess.run(
                [command] + arguments,
                capture_output=True,
                text=True,
                timeout=10,
            )

            return {
                "success": result.returncode == 0,
                "result": {
                    "output": result.stdout,
                    "error": result.stderr,
                    "return_code": result.returncode,
                },
            }
        except subprocess.TimeoutExpired:
            return {
                "success": False,
                "error": "Command execution timed out",
            }
        except Exception as e:
            logger.debug(
                "execute_safe_command failed",
                exc_info=True,
                extra={"module_name": "shell_sandbox_service", "operation": "execute_safe_command", "error_type": type(e).__name__},
            )
            return {
                "success": False,
                "error": "Command execution failed",
            }

    def _is_valid_path(self, path: str) -> bool:
        """Validate path is safe"""
        if not path:
            return False

        if "\x00" in path:
            return False

        try:
            resolved = Path(path).expanduser().resolve()
        except Exception:
            return False

        # Reject traversal-like segments early (defense-in-depth)
        if ".." in Path(path).parts:
            return False

        # Resolved path must live under one of the allowed roots
        for root in self._allowed_roots:
            try:
                resolved.relative_to(root)
                return True
            except ValueError:
                continue

        return False

