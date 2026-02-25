from __future__ import annotations
"""
Mavaia Core API - OpenAI-compatible API and embedded server
"""

# Lazy imports to avoid dependency issues at module level
def create_app(*args, **kwargs):
    """Create FastAPI application (lazy import)"""
    from mavaia_core.api.server import create_app as _create_app
    return _create_app(*args, **kwargs)


def run_server(*args, **kwargs):
    """Run the embedded HTTP server (lazy import)"""
    from mavaia_core.api.server import run_server as _run_server
    return _run_server(*args, **kwargs)


__all__ = ["create_app", "run_server"]

