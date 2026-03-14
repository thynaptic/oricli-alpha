from __future__ import annotations
"""
OricliAlpha Core - Modular AI Core Package
Provides unified interface for all OricliAlpha capabilities
"""

__version__ = "1.1.0"

# Lazy imports to avoid import-time execution and expensive import chains
# Import these classes only when actually needed

__all__ = [
    "OricliAlphaClient",
    "OricliAlphaError",
    "ModuleError",
    "ModuleNotFoundError",
    "ModuleInitializationError",
    "ModuleOperationError",
    "InvalidParameterError",
    "APIError",
    "AuthenticationError",
    "ValidationError",
    "ClientError",
    "ClientInitializationError",
    "RegistryError",
    "ModuleDiscoveryError",
    "SYSTEM_ID",
    "SYSTEM_ID_FULL",
    "MODEL_COGNITIVE",
    "MODEL_EMBEDDINGS",
    "get_system_identifier_with_subname",
    "set_system_subname",
    "get_system_subname",
]

def __getattr__(name: str):
    """Lazy import of oricli_core classes and functions"""
    if name == "OricliAlphaClient":
        from oricli_core.client import OricliAlphaClient
        return OricliAlphaClient
    elif name in [
        "OricliAlphaError", "ModuleError", "ModuleNotFoundError", "ModuleInitializationError",
        "ModuleOperationError", "InvalidParameterError", "APIError", "AuthenticationError",
        "ValidationError", "ClientError", "ClientInitializationError", "RegistryError",
        "ModuleDiscoveryError"
    ]:
        from oricli_core.exceptions import (
            OricliAlphaError, ModuleError, ModuleNotFoundError, ModuleInitializationError,
            ModuleOperationError, InvalidParameterError, APIError, AuthenticationError,
            ValidationError, ClientError, ClientInitializationError, RegistryError,
            ModuleDiscoveryError
        )
        return globals().get(name) or locals().get(name)
    elif name in [
        "SYSTEM_ID", "SYSTEM_ID_FULL", "MODEL_COGNITIVE", "MODEL_EMBEDDINGS",
        "get_system_identifier_with_subname", "set_system_subname", "get_system_subname"
    ]:
        from oricli_core.system_identifier import (
            SYSTEM_ID, SYSTEM_ID_FULL, MODEL_COGNITIVE, MODEL_EMBEDDINGS,
            get_system_identifier_with_subname, set_system_subname, get_system_subname
        )
        return globals().get(name) or locals().get(name)
    raise AttributeError(f"module '{__name__}' has no attribute '{name}'")

