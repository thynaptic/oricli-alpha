"""
Sandbox Service - Secure Code Execution Sandboxes

Provides secure, isolated environments for code execution using Firecracker
microVMs (with Docker fallback).
"""

from mavaia_core.services.sandbox.base import (
    SandboxService,
    SandboxExecutionError,
)
from mavaia_core.services.sandbox.docker_sandbox import DockerSandbox
from mavaia_core.services.sandbox.firecracker_sandbox import (
    FirecrackerSandbox,
    check_firecracker_available,
)
from mavaia_core.services.sandbox.pool_manager import SandboxPoolManager
from mavaia_core.services.sandbox.resource_limits import (
    ResourceLimits,
    ResourceUsage,
)
from mavaia_core.services.sandbox.command_validator import (
    CommandValidator,
    CommandValidationError,
)

__all__ = [
    "SandboxService",
    "SandboxExecutionError",
    "DockerSandbox",
    "FirecrackerSandbox",
    "check_firecracker_available",
    "SandboxPoolManager",
    "ResourceLimits",
    "ResourceUsage",
    "CommandValidator",
    "CommandValidationError",
]

