from __future__ import annotations
"""
Oricli-Alpha Core - Modular AI Core Package
Provides unified interface for all Oricli-Alpha capabilities
"""

__version__ = "1.0.0"

# Lazy imports to avoid import-time execution and expensive import chains
# Import these classes only when actually needed

__all__ = [
    "Oricli-AlphaClient",
    "Oricli-AlphaError",
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
    if name == "Oricli-AlphaClient":
        from oricli_core.client import Oricli-AlphaClient
        return Oricli-AlphaClient
    elif name in [
        "Oricli-AlphaError", "ModuleError", "ModuleNotFoundError", "ModuleInitializationError",
        "ModuleOperationError", "InvalidParameterError", "APIError", "AuthenticationError",
        "ValidationError", "ClientError", "ClientInitializationError", "RegistryError",
        "ModuleDiscoveryError"
    ]:
        from oricli_core.exceptions import (
            Oricli-AlphaError, ModuleError, ModuleNotFoundError, ModuleInitializationError,
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

