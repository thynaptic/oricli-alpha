"""
Shell Sandbox Service
Safe shell command execution service with strict allowlist and validation
Converted from Swift ShellSandboxService.swift
"""

from typing import Any, Dict, List, Optional
import sys
import os
import subprocess
import stat
from pathlib import Path
from datetime import datetime

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent))

from mavaia_core.brain.base_module import BaseBrainModule, ModuleMetadata


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


class ShellSandboxError(Exception):
    """Shell sandbox error"""
    pass


class ShellSandboxServiceModule(BaseBrainModule):
    """Safe shell command execution service"""

    def __init__(self):
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
        if operation == "list_folder":
            return self._list_folder(params)
        elif operation == "list_running_processes":
            return self._list_running_processes(params)
        elif operation == "read_file_metadata":
            return self._read_file_metadata(params)
        elif operation == "execute_safe_command":
            return self._execute_safe_command(params)
        else:
            raise ValueError(f"Unknown operation: {operation}")

    def _list_folder(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """List folder contents"""
        path = params.get("path", "")

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
            return {
                "success": False,
                "error": str(e),
            }

    def _list_running_processes(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """List running processes"""
        filter_name = params.get("filter_name")
        max_results = params.get("max_results", 50)

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
                if len(processes) >= max_results:
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
            return {
                "success": False,
                "error": str(e),
            }

    def _read_file_metadata(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """Read file metadata"""
        path = params.get("path", "")

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
            return {
                "success": False,
                "error": str(e),
            }

    def _execute_safe_command(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """Execute a safe shell command"""
        command = params.get("command", "")
        arguments = params.get("arguments", [])

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
            return {
                "success": False,
                "error": str(e),
            }

    def _is_valid_path(self, path: str) -> bool:
        """Validate path is safe"""
        if not path:
            return False

        # Block absolute paths outside user directory (simplified)
        # In real implementation, would have more sophisticated validation
        if path.startswith("/") and not path.startswith(os.path.expanduser("~")):
            # Allow some system paths for read-only operations
            allowed_system_paths = ["/tmp", "/var/tmp"]
            if not any(path.startswith(p) for p in allowed_system_paths):
                return False

        return True

