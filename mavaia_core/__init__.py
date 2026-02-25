from __future__ import annotations
"""
Mavaia Core - Modular AI Core Package
Provides unified interface for all Mavaia capabilities
"""

__version__ = "1.0.0"

# Lazy imports to avoid import-time execution and expensive import chains
# Import these classes only when actually needed

__all__ = [
    "MavaiaClient",
    "MavaiaError",
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
    """Lazy import of mavaia_core classes and functions"""
    if name == "MavaiaClient":
        from mavaia_core.client import MavaiaClient
        return MavaiaClient
    elif name in [
        "MavaiaError", "ModuleError", "ModuleNotFoundError", "ModuleInitializationError",
        "ModuleOperationError", "InvalidParameterError", "APIError", "AuthenticationError",
        "ValidationError", "ClientError", "ClientInitializationError", "RegistryError",
        "ModuleDiscoveryError"
    ]:
        from mavaia_core.exceptions import (
            MavaiaError, ModuleError, ModuleNotFoundError, ModuleInitializationError,
            ModuleOperationError, InvalidParameterError, APIError, AuthenticationError,
            ValidationError, ClientError, ClientInitializationError, RegistryError,
            ModuleDiscoveryError
        )
        return globals().get(name) or locals().get(name)
    elif name in [
        "SYSTEM_ID", "SYSTEM_ID_FULL", "MODEL_COGNITIVE", "MODEL_EMBEDDINGS",
        "get_system_identifier_with_subname", "set_system_subname", "get_system_subname"
    ]:
        from mavaia_core.system_identifier import (
            SYSTEM_ID, SYSTEM_ID_FULL, MODEL_COGNITIVE, MODEL_EMBEDDINGS,
            get_system_identifier_with_subname, set_system_subname, get_system_subname
        )
        return globals().get(name) or locals().get(name)
    raise AttributeError(f"module '{__name__}' has no attribute '{name}'")

