from __future__ import annotations
"""
State Storage Infrastructure

Centralized state persistence layer for brain modules.
Provides abstract storage interface with multiple backend implementations.
"""

from oricli_core.brain.state_storage.base_storage import BaseStorage, StorageConfig
from oricli_core.brain.state_storage.file_storage import FileStorage
from oricli_core.brain.state_storage.memory_storage import MemoryStorage
from oricli_core.brain.state_storage.db_storage import DatabaseStorage
from oricli_core.brain.state_storage.state_index import StateIndex

__all__ = [
    "BaseStorage",
    "StorageConfig",
    "FileStorage",
    "MemoryStorage",
    "DatabaseStorage",
    "StateIndex",
]

