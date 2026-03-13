"""
Memory Bridge Service Module

Brain-module wrapper around `oricli_core.services.memory_bridge_service.MemoryBridgeService`.

This makes the encrypted LMDB-backed store accessible through the existing
ModuleRegistry/orchestration system.
"""

from __future__ import annotations

import logging
from typing import Any, Optional

from oricli_core.brain.base_module import BaseBrainModule, ModuleMetadata
from oricli_core.exceptions import (
    InvalidParameterError,
    ModuleInitializationError,
    ModuleOperationError,
)
from oricli_core.services.memory_bridge_service import (
    MemoryBridgeConfig,
    MemoryBridgeService,
    MemoryCategory,
    MemoryBridgeError,
)

logger = logging.getLogger(__name__)


class MemoryBridgeServiceModule(BaseBrainModule):
    """Brain-module wrapper for the MemoryBridgeService (memory.oricli)."""

    def __init__(self):
        self._service: Optional[MemoryBridgeService] = None

    @property
    def metadata(self) -> ModuleMetadata:
        return ModuleMetadata(
            name="memory_bridge_service",
            version="1.0.0",
            description="Encrypted LMDB-backed memory store shared across runtimes (memory.oricli)",
            operations=[
                "health_check",
                "put",
                "get",
                "delete",
                "list_ids",
                "append_reflection_log",
                "read_reflection_log",
                "upsert_vector",
                "vector_search",
            ],
            dependencies=["lmdb", "cryptography"],
            model_required=False,
        )

    def initialize(self) -> bool:
        """Initialize the underlying MemoryBridgeService from environment configuration."""
        try:
            config = MemoryBridgeConfig.from_env()
            service = MemoryBridgeService(config)
            service.initialize()
            self._service = service
            logger.info(
                "MemoryBridgeServiceModule initialized",
                extra={
                    "lmdb_path": str(config.lmdb_path),
                    "map_size_mb": config.map_size_mb,
                    "enable_vector_index": config.enable_vector_index,
                },
            )
            return True
        except MemoryBridgeError as e:
            raise ModuleInitializationError(module_name=self.metadata.name, reason=str(e)) from e
        except Exception as e:
            raise ModuleInitializationError(module_name=self.metadata.name, reason=f"Unexpected error: {e}") from e

    def cleanup(self) -> None:
        """Close underlying service resources."""
        try:
            if self._service is not None:
                self._service.close()
        except Exception:
            # Cleanup should never raise.
            logger.warning(
                "MemoryBridgeServiceModule cleanup failed",
                exc_info=True,
                extra={"module_name": self.metadata.name},
            )

    def execute(self, operation: str, params: dict[str, Any]) -> dict[str, Any]:
        """Execute MemoryBridgeService operations through the module interface."""
        if self._service is None:
            # Lazy init to support environments that register modules before env is set.
            self.initialize()

        try:
            if operation == "health_check":
                return {"success": True, "result": self._service.health_check()}

            if operation == "put":
                category = _parse_category(params.get("category"))
                memory_id = _require_str(params.get("id"), "id")
                data = _require_dict(params.get("data"), "data")
                metadata = _optional_dict(params.get("metadata"), "metadata")
                self._service.put(category, memory_id, data, metadata=metadata)
                return {"success": True}

            if operation == "get":
                category = _parse_category(params.get("category"))
                memory_id = _require_str(params.get("id"), "id")
                obj = self._service.get(category, memory_id)
                return {"success": True, "result": obj}

            if operation == "delete":
                category = _parse_category(params.get("category"))
                memory_id = _require_str(params.get("id"), "id")
                deleted = self._service.delete(category, memory_id)
                return {"success": True, "deleted": deleted}

            if operation == "list_ids":
                category = _parse_category(params.get("category"))
                limit = params.get("limit")
                prefix = params.get("prefix")
                if limit is not None and not isinstance(limit, int):
                    raise InvalidParameterError(parameter="limit", value=str(limit), reason="Must be an integer")
                if prefix is not None and not isinstance(prefix, str):
                    raise InvalidParameterError(parameter="prefix", value=str(prefix), reason="Must be a string")
                ids = self._service.list_ids(category, limit=limit, prefix=prefix)
                return {"success": True, "result": ids}

            if operation == "append_reflection_log":
                log_id = _require_str(params.get("log_id"), "log_id")
                entry = _require_dict(params.get("entry"), "entry")
                timestamp = params.get("timestamp")
                if timestamp is not None and not isinstance(timestamp, (int, float)):
                    raise InvalidParameterError(
                        parameter="timestamp", value=str(timestamp), reason="Must be a number (unix seconds)"
                    )
                item_key = self._service.append_reflection_log(
                    log_id=log_id, entry=entry, timestamp=float(timestamp) if timestamp is not None else None
                )
                return {"success": True, "item_key": item_key}

            if operation == "read_reflection_log":
                log_id = _require_str(params.get("log_id"), "log_id")
                limit = params.get("limit", 100)
                if not isinstance(limit, int):
                    raise InvalidParameterError(parameter="limit", value=str(limit), reason="Must be an integer")
                items = self._service.read_reflection_log(log_id=log_id, limit=limit)
                return {"success": True, "result": items}

            if operation == "upsert_vector":
                vector_id = _require_str(params.get("id"), "id")
                vector = params.get("vector")
                if not isinstance(vector, list):
                    raise InvalidParameterError(parameter="vector", value=str(type(vector)), reason="Must be list[float]")
                metadata = _optional_dict(params.get("metadata"), "metadata")
                self._service.upsert_vector(vector_id, vector, metadata=metadata)
                return {"success": True}

            if operation == "vector_search":
                q = params.get("query_vector")
                if not isinstance(q, list):
                    raise InvalidParameterError(
                        parameter="query_vector", value=str(type(q)), reason="Must be list[float]"
                    )
                top_k = params.get("top_k", 10)
                min_score = params.get("min_score", 0.0)
                if not isinstance(top_k, int):
                    raise InvalidParameterError(parameter="top_k", value=str(top_k), reason="Must be an integer")
                if not isinstance(min_score, (int, float)):
                    raise InvalidParameterError(parameter="min_score", value=str(min_score), reason="Must be a number")
                results = self._service.vector_search(q, top_k=top_k, min_score=float(min_score))
                return {"success": True, "result": results}

            raise InvalidParameterError(parameter="operation", value=operation, reason="Unsupported operation")
        except InvalidParameterError:
            raise
        except MemoryBridgeError as e:
            raise ModuleOperationError(module_name=self.metadata.name, operation=operation, reason=str(e)) from e
        except Exception as e:
            raise ModuleOperationError(module_name=self.metadata.name, operation=operation, reason=f"Unexpected error: {e}") from e


def _parse_category(value: Any) -> MemoryCategory:
    if isinstance(value, MemoryCategory):
        return value
    if isinstance(value, str) and value.strip():
        try:
            return MemoryCategory(value.strip())
        except ValueError as e:
            raise InvalidParameterError(parameter="category", value=value, reason="Unknown category") from e
    raise InvalidParameterError(parameter="category", value=str(value), reason="Required")


def _require_str(value: Any, parameter: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise InvalidParameterError(parameter=parameter, value=str(value), reason="Required non-empty string")
    return value


def _require_dict(value: Any, parameter: str) -> dict[str, Any]:
    if not isinstance(value, dict):
        raise InvalidParameterError(parameter=parameter, value=str(type(value)), reason="Must be a dict/object")
    return value


def _optional_dict(value: Any, parameter: str) -> dict[str, Any] | None:
    if value is None:
        return None
    if not isinstance(value, dict):
        raise InvalidParameterError(parameter=parameter, value=str(type(value)), reason="Must be a dict/object")
    return value

