from __future__ import annotations
"""
System Identifier - Cognitive System Naming Scheme

Implements the standardized naming scheme for cognitive systems as defined in
TR-2025-01-Cognitive-System-Naming-Scheme.

Format: {system_name}-{quantifier}{architecture_type}
For cognitive systems: {system_name}-{module_count}c
With sub-naming: {system_name}-{module_count}c-{subname}

The module count is dynamically discovered via ModuleRegistry.discover_modules().
"""

import os
from typing import Optional
from mavaia_core.brain.modules.module_registry import ModuleRegistry

# Global subname storage (can be set via set_system_subname())
_system_subname: Optional[str] = None


def get_system_identifier() -> str:
    """
    Get the standardized system identifier for Mavaia.
    
    Discovers modules via ModuleRegistry and constructs the identifier
    following the naming scheme: mavaia-{module_count}c
    
    Returns:
        System identifier string (e.g., "mavaia-137c")
    """
    # Ensure modules are discovered
    ModuleRegistry.discover_modules(verbose=False)
    
    # Count registered modules
    module_count = len(ModuleRegistry.list_modules())
    
    # Construct identifier: mavaia-{count}c
    return f"mavaia-{module_count}c"


def get_system_identifier_with_subname(subname: str) -> str:
    """
    Get the system identifier with a sub-name qualifier.
    
    Format: mavaia-{module_count}c-{subname}
    Examples: "mavaia-137c-alpha", "mavaia-137c-Pro", "mavaia-137c-Flash"
    
    Args:
        subname: Sub-name qualifier (e.g., "alpha", "Pro", "Flash")
    
    Returns:
        System identifier string with subname (e.g., "mavaia-137c-alpha")
    
    Raises:
        ValueError: If subname is empty or contains invalid characters
    """
    if not subname or not subname.strip():
        raise ValueError("Subname cannot be empty")
    
    # Validate subname (alphanumeric, hyphens, underscores allowed)
    subname_clean = subname.strip()
    if not all(c.isalnum() or c in ('-', '_') for c in subname_clean):
        raise ValueError(
            "Subname can only contain alphanumeric characters, hyphens, and underscores"
        )
    
    base_id = get_system_identifier()
    return f"{base_id}-{subname_clean}"


def set_system_subname(subname: Optional[str]) -> None:
    """
    Set the default system subname for this session.
    
    This affects the SYSTEM_ID_FULL constant. Set to None to clear.
    
    Args:
        subname: Sub-name qualifier (e.g., "alpha", "Pro", "Flash") or None to clear
    """
    global _system_subname
    if subname is None:
        _system_subname = None
    else:
        if not subname.strip():
            raise ValueError("Subname cannot be empty")
        subname_clean = subname.strip()
        if not all(c.isalnum() or c in ('-', '_') for c in subname_clean):
            raise ValueError(
                "Subname can only contain alphanumeric characters, hyphens, and underscores"
            )
        _system_subname = subname_clean


def get_system_subname() -> Optional[str]:
    """
    Get the currently set system subname.
    
    Returns:
        Current subname or None if not set
    """
    return _system_subname


# System identifier constant (base, without subname)
# Format: {system_name}-{cognitive_module_count}c
# Discovered via ModuleRegistry.discover_modules()
SYSTEM_ID: str = get_system_identifier()

# System identifier with subname (if set)
# Format: {system_name}-{cognitive_module_count}c-{subname}
# Can be set via set_system_subname() or MAVAIA_SYSTEM_SUBNAME environment variable
def get_system_id_full() -> str:
    """
    Get the full system identifier with subname if available.
    
    Checks for subname in this order:
    1. Subname set via set_system_subname()
    2. MAVAIA_SYSTEM_SUBNAME environment variable
    3. Falls back to base SYSTEM_ID if no subname is set
    
    Returns:
        System identifier with subname if set, otherwise base SYSTEM_ID
    """
    subname = _system_subname or os.getenv("MAVAIA_SYSTEM_SUBNAME")
    if subname:
        return get_system_identifier_with_subname(subname)
    return SYSTEM_ID


# For backward compatibility and convenience, provide as a callable
# Note: This is a function, not a constant, to allow dynamic updates
SYSTEM_ID_FULL = get_system_id_full

# Model identifiers (for API compatibility)
# These remain as service-level identifiers, not system architecture identifiers
MODEL_COGNITIVE: str = "mavaia-cognitive"
MODEL_EMBEDDINGS: str = "mavaia-embeddings"

