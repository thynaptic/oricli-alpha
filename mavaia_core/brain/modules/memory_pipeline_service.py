from __future__ import annotations
"""
Memory Pipeline Service - Orchestrates three-layer memory pipeline
Converted from Swift MemoryPipelineService.swift
"""

from typing import Any, Dict, List, Optional
import logging

from mavaia_core.brain.base_module import BaseBrainModule, ModuleMetadata
from mavaia_core.exceptions import InvalidParameterError

logger = logging.getLogger(__name__)


class MemoryPipelineServiceModule(BaseBrainModule):
    """Orchestrates three-layer memory pipeline"""

    def __init__(self):
        super().__init__()
        self.persistent_memory = None
        self.memory_graph = None
        self._modules_loaded = False
        self._processing_threshold = 100
        self._memories_since_last_processing = 0

    @property
    def metadata(self) -> ModuleMetadata:
        return ModuleMetadata(
            name="memory_pipeline_service",
            version="1.0.0",
            description="Orchestrates three-layer memory pipeline: CoreData → Pandas → Neo4j",
            operations=[
                "store_memory",
                "recall_memories",
                "process_memories",
                "build_graph",
                "get_graph_stats",
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
            from mavaia_core.brain.registry import ModuleRegistry

            self.persistent_memory = ModuleRegistry.get_module("persistent_memory_service")
            self.memory_graph = ModuleRegistry.get_module("memory_graph")

            self._modules_loaded = True
        except Exception as e:
            # Modules not available - will use fallback methods
            logger.debug(
                "Failed to load one or more memory pipeline dependencies",
                exc_info=True,
                extra={"module_name": "memory_pipeline_service", "error_type": type(e).__name__},
            )

    def execute(self, operation: str, params: Dict[str, Any]) -> Dict[str, Any]:
        """Execute an operation"""
        self._ensure_modules_loaded()

        if operation == "store_memory":
            return self._store_memory(params)
        elif operation == "recall_memories":
            return self._recall_memories(params)
        elif operation == "process_memories":
            return self._process_memories(params)
        elif operation == "build_graph":
            return self._build_graph(params)
        elif operation == "get_graph_stats":
            return self._get_graph_stats(params)
        else:
            raise InvalidParameterError(
                parameter="operation",
                value=operation,
                reason="Unknown operation for memory_pipeline_service",
            )

    def _store_memory(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """Store a memory in the pipeline"""
        if not self.persistent_memory:
            return {
                "success": False,
                "error": "Persistent memory service not available",
                "memory_id": None,
            }

        try:
            result = self.persistent_memory.execute("store_memory", params)
            
            # Track for processing
            self._memories_since_last_processing += 1
            
            # Check if processing needed
            if self._memories_since_last_processing >= self._processing_threshold:
                # Trigger background processing (non-blocking)
                self._process_memories({"force": False})
                self._memories_since_last_processing = 0

            return result
        except Exception as e:
            return {
                "success": False,
                "error": str(e),
                "memory_id": None,
            }

    def _recall_memories(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """Recall memories with optional graph reasoning"""
        query = params.get("query", "")
        limit = params.get("limit", 10)
        use_graph = params.get("use_graph", True)

        if not self.persistent_memory:
            return {
                "success": False,
                "error": "Persistent memory service not available",
                "memories": [],
            }

        # Use graph-based recall if available and requested
        if self.memory_graph and use_graph:
            try:
                # Prefer standardized operation name if available.
                # memory_graph now supports `recall_memories`.
                result = self.memory_graph.execute(
                    "recall_memories",
                    {"query": query, "limit": limit, "use_graph": True},
                )
                # Normalize result shape
                if isinstance(result, dict) and "memories" in result:
                    return {"success": True, "memories": result.get("memories", [])}
                return result
            except Exception as e:
                logger.debug(
                    "Graph-based recall failed; falling back to persistent memory recall",
                    exc_info=True,
                    extra={"module_name": "memory_pipeline_service", "error_type": type(e).__name__},
                )

        # Fall back to persistent memory service
        return self.persistent_memory.execute("recall_memories", {
            "query": query,
            "limit": limit,
        })

    def _process_memories(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """Process memories (cleaning, clustering, etc.)"""
        force = params.get("force", False)

        # In full implementation, would process memories for clustering, cleaning, etc.
        # For now, just reset counter
        if force:
            self._memories_since_last_processing = 0

        return {
            "success": True,
            "processed_count": 0,
            "cleaned_count": 0,
            "clusters": [],
        }

    def _build_graph(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """Build memory graph"""
        if not self.memory_graph:
            return {
                "success": False,
                "error": "Memory graph service not available",
            }

        try:
            result = self.memory_graph.execute("build_graph", {})
            return result
        except Exception as e:
            return {
                "success": False,
                "error": str(e),
            }

    def _get_graph_stats(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """Get graph statistics"""
        if not self.memory_graph:
            return {
                "success": False,
                "error": "Memory graph service not available",
                "stats": {},
            }

        try:
            result = self.memory_graph.execute("get_stats", {})
            return result
        except Exception as e:
            return {
                "success": False,
                "error": str(e),
                "stats": {},
            }

