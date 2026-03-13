from __future__ import annotations
"""
Sandbox Service - Secure Code Execution Sandboxes

Provides secure, isolated environments for code execution using Firecracker
microVMs (with Docker fallback).
"""

from oricli_core.services.sandbox.base import (
    SandboxService,
    SandboxExecutionError,
)

# Docker support is optional (some environments cannot install the `docker`
# Python package, or do not run Docker at all). Keep imports resilient so that
# the sandbox package can still be imported for Firecracker-only setups.
try:
    from oricli_core.services.sandbox.docker_sandbox import DockerSandbox
    _DOCKER_SANDBOX_AVAILABLE = True
except ImportError:
    DockerSandbox = None  # type: ignore[assignment]
    _DOCKER_SANDBOX_AVAILABLE = False
from oricli_core.services.sandbox.firecracker_sandbox import (
    FirecrackerSandbox,
    check_firecracker_available,
)
from oricli_core.services.sandbox.pool_manager import SandboxPoolManager
from oricli_core.services.sandbox.resource_limits import (
    ResourceLimits,
    ResourceUsage,
)
from oricli_core.services.sandbox.command_validator import (
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

