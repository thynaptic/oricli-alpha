"""
AI Recall Service - Phase 1 recall layer with shared AI config + telemetry
Converted from Swift AIRecallService.swift
"""

from typing import Any, Dict, List, Optional
import time
import logging

from mavaia_core.brain.base_module import BaseBrainModule, ModuleMetadata
from mavaia_core.brain.registry import ModuleRegistry
from mavaia_core.exceptions import InvalidParameterError

logger = logging.getLogger(__name__)
try:
    from models.core_types import RecallSnippet, RecallObjectType, AIPayloadContext
except ImportError:
    # Models not available - define minimal types
    RecallSnippet = None
    RecallObjectType = None
    AIPayloadContext = None


class AIRecallServiceModule(BaseBrainModule):
    """AI-powered memory recall service"""

    def __init__(self):
        super().__init__()
        self.persistent_memory = None
        self.memory_graph = None
        self.embeddings = None
        self._modules_loaded = False

    @property
    def metadata(self) -> ModuleMetadata:
        return ModuleMetadata(
            name="ai_recall_service",
            version="1.0.0",
            description="AI-powered memory recall with shared AI config + telemetry",
            operations=[
                "recall_memories",
                "recall_with_context",
                "recall_by_type",
                "recall_recent",
            ],
            dependencies=[],
            model_required=False,
        )

    def initialize(self) -> bool:
        """Initialize the module"""
        return True

    def _ensure_modules_loaded(self):
        """Lazy load dependent modules"""
        if self._modules_loaded:
            return

        try:
            self.persistent_memory = ModuleRegistry.get_module("persistent_memory_service")
            self.memory_graph = ModuleRegistry.get_module("memory_graph")
            self.embeddings = ModuleRegistry.get_module("embeddings")

            self._modules_loaded = True
        except Exception as e:
            # Modules not available - will use fallback methods
            logger.debug(
                "Failed to load ai_recall_service dependencies",
                exc_info=True,
                extra={"module_name": "ai_recall_service", "error_type": type(e).__name__},
            )

    def execute(self, operation: str, params: Dict[str, Any]) -> Dict[str, Any]:
        """Execute an operation"""
        self._ensure_modules_loaded()

        if operation == "recall_memories":
            return self._recall_memories(params)
        elif operation == "recall_with_context":
            return self._recall_with_context(params)
        elif operation == "recall_by_type":
            return self._recall_by_type(params)
        elif operation == "recall_recent":
            return self._recall_recent(params)
        else:
            raise InvalidParameterError(
                parameter="operation",
                value=operation,
                reason="Unknown operation for ai_recall_service",
            )

    def _recall_memories(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """Recall memories matching a query"""
        query = params.get("query", "")
        limit = params.get("limit", 10)
        min_score = params.get("min_score", 0.3)
        use_graph = params.get("use_graph", True)
        if query is None:
            query = ""
        if not isinstance(query, str):
            raise InvalidParameterError("query", str(type(query).__name__), "query must be a string")
        try:
            limit_int = int(limit)
        except (TypeError, ValueError):
            raise InvalidParameterError("limit", str(limit), "limit must be an integer")
        if limit_int < 1:
            raise InvalidParameterError("limit", str(limit_int), "limit must be >= 1")
        try:
            min_score_float = float(min_score)
        except (TypeError, ValueError):
            raise InvalidParameterError("min_score", str(min_score), "min_score must be a number")
        if not isinstance(use_graph, bool):
            raise InvalidParameterError("use_graph", str(type(use_graph).__name__), "use_graph must be a boolean")

        if not self.persistent_memory:
            return {
                "success": False,
                "error": "Persistent memory service not available",
                "snippets": [],
            }

        try:
            # Use persistent memory service to recall
            result = self.persistent_memory.execute("recall_memories", {
                "query": query,
                "limit": limit_int,
                "min_score": min_score_float,
            })

            memories = result.get("memories", [])

            # Convert to RecallSnippet format
            snippets = []
            for memory in memories:
                object_type_value = memory.get("type", "unknown")
                if RecallObjectType is not None and hasattr(RecallObjectType, "UNKNOWN"):
                    object_type_value = memory.get("type", RecallObjectType.UNKNOWN.value)

                snippet = {
                    "id": memory.get("id", ""),
                    "object_id": memory.get("id", ""),
                    "object_type": object_type_value,
                    "title": memory.get("content", "")[:50],  # Use first 50 chars as title
                    "detail": memory.get("content", ""),
                    "score": memory.get("score", 0.0),
                    "last_updated": time.time(),
                    "last_viewed_at": time.time(),
                    "emotion": "",
                    "emotion_score": 0.0,
                    "emotion_intensity": 0.0,
                    "emotion_keywords": [],
                }
                snippets.append(snippet)

            return {
                "success": True,
                "snippets": snippets,
            }
        except Exception as e:
            logger.debug(
                "Recall failed in persistent_memory_service",
                exc_info=True,
                extra={"module_name": "ai_recall_service", "error_type": type(e).__name__},
            )
            return {
                "success": False,
                "error": "Recall failed",
                "snippets": [],
            }

    def _recall_with_context(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """Recall memories with additional context"""
        query = params.get("query", "")
        context = params.get("context", {})  # AIPayloadContext-like dict
        limit = params.get("limit", 10)
        if query is None:
            query = ""
        if context is None:
            context = {}
        if not isinstance(query, str):
            raise InvalidParameterError("query", str(type(query).__name__), "query must be a string")
        if not isinstance(context, dict):
            raise InvalidParameterError("context", str(type(context).__name__), "context must be a dict")
        try:
            limit_int = int(limit)
        except (TypeError, ValueError):
            raise InvalidParameterError("limit", str(limit), "limit must be an integer")
        if limit_int < 1:
            raise InvalidParameterError("limit", str(limit_int), "limit must be >= 1")

        # Use graph-based recall if available and requested
        if self.memory_graph and context.get("use_graph", True):
            try:
                result = self.memory_graph.execute("recall_with_context", {
                    "query": query,
                    "context": context,
                    "limit": limit_int,
                })
                return result
            except Exception as e:
                logger.debug(
                    "memory_graph recall_with_context failed; falling back to base recall",
                    exc_info=True,
                    extra={"module_name": "ai_recall_service", "error_type": type(e).__name__},
                )

        # Fall back to regular recall
        return self._recall_memories({
            "query": query,
            "limit": limit_int,
        })

    def _recall_by_type(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """Recall memories by type"""
        memory_type = params.get("type", "conversation")
        limit = params.get("limit", 10)

        if not self.persistent_memory:
            return {
                "success": False,
                "error": "Persistent memory service not available",
                "snippets": [],
            }

        # Search for memories of specific type
        # In full implementation, would filter by type
        return self._recall_memories({
            "query": f"type:{memory_type}",
            "limit": limit,
        })

    def _recall_recent(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """Recall recent memories"""
        limit = params.get("limit", 10)
        days = params.get("days", 7)

        if not self.persistent_memory:
            return {
                "success": False,
                "error": "Persistent memory service not available",
                "snippets": [],
            }

        # In full implementation, would filter by recency
        # For now, just return recent memories from store
        return self._recall_memories({
            "query": "",
            "limit": limit,
        })

