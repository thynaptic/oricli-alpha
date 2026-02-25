from __future__ import annotations
"""
Semantic Search Service - Semantic/vector-based search service for memory and document corpus
Converted from Swift SemanticSearchService.swift
"""

from typing import Any, Dict, List, Optional, Set
import math
import logging

from mavaia_core.brain.base_module import BaseBrainModule, ModuleMetadata
from mavaia_core.brain.registry import ModuleRegistry
from mavaia_core.exceptions import InvalidParameterError

logger = logging.getLogger(__name__)

# Optional imports - models package may not be available
try:
    from models.retrieval_models import DocumentSource, SemanticRetrievalResult
except ImportError:
    # Models not available - define minimal types
    DocumentSource = None
    SemanticRetrievalResult = None


class SemanticSearchServiceModule(BaseBrainModule):
    """Semantic/vector-based search service for memory and document corpus"""

    def __init__(self):
        super().__init__()
        self.memory_pipeline = None
        self.embeddings = None
        self._modules_loaded = False
        self._embedding_cache: Dict[str, List[float]] = {}
        self._cache_max_size = 100

        self._default_sources = ["memory"]

    @property
    def metadata(self) -> ModuleMetadata:
        return ModuleMetadata(
            name="semantic_search_service",
            version="1.0.0",
            description="Semantic/vector-based search service for memory and document corpus",
            operations=[
                "semantic_search",
                "search_with_embeddings",
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
            self.memory_pipeline = ModuleRegistry.get_module("memory_pipeline_service")
            self.embeddings = ModuleRegistry.get_module("embeddings")

            self._modules_loaded = True
        except Exception as e:
            # Modules not available - will use fallback methods
            logger.debug(
                "Failed to load semantic_search_service dependencies",
                exc_info=True,
                extra={"module_name": "semantic_search_service", "error_type": type(e).__name__},
            )

    def execute(self, operation: str, params: Dict[str, Any]) -> Dict[str, Any]:
        """Execute an operation"""
        self._ensure_modules_loaded()

        if operation == "semantic_search":
            return self._semantic_search(params)
        elif operation == "search_with_embeddings":
            return self._search_with_embeddings(params)
        else:
            raise InvalidParameterError(
                parameter="operation",
                value=operation,
                reason="Unknown operation for semantic_search_service",
            )

    def _semantic_search(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """Perform semantic search"""
        query = params.get("query", "")
        limit = params.get("limit", 10)
        sources = params.get("sources", self._default_sources)

        if not isinstance(query, str) or not query.strip():
            raise InvalidParameterError(
                parameter="query",
                value=str(query),
                reason="query must be a non-empty string",
            )
        try:
            limit_int = int(limit)
        except (TypeError, ValueError):
            raise InvalidParameterError("limit", str(limit), "limit must be an integer")
        if limit_int < 1:
            raise InvalidParameterError("limit", str(limit_int), "limit must be >= 1")

        # Generate query embedding
        query_embedding = self._generate_embedding(query)

        all_documents = []

        # Search memory if requested
        if "memory" in [str(s).lower() for s in (sources or [])] and self.memory_pipeline:
            try:
                memory_results = self.memory_pipeline.execute("recall_memories", {
                    "query": query,
                    "limit": limit_int * 2,
                    "use_graph": True,
                })

                memories = memory_results.get("memories", [])

                # Convert to documents with semantic scoring
                for memory in memories:
                    memory_content = memory.get("content", "")
                    memory_embedding = self._generate_embedding(memory_content)

                    # Compute cosine similarity
                    similarity = self._cosine_similarity(query_embedding, memory_embedding)

                    # Combine with existing relevance score
                    existing_score = memory.get("score", 0.0)
                    combined_score = (similarity * 0.7) + (existing_score * 0.3)

                    document = {
                        "id": memory.get("id", ""),
                        "title": memory.get("summary") or memory.get("type", ""),
                        "content": memory_content,
                        "url": None,
                        "snippet": memory.get("summary"),
                        "source": "memory",
                        "relevance_score": combined_score,
                        "metadata": {
                            "source_id": memory.get("id", ""),
                            "source_type": memory.get("type", ""),
                            "importance": memory.get("importance", 0.5),
                            "semantic_score": similarity,
                            "combined_score": combined_score,
                        },
                    }

                    all_documents.append(document)
            except Exception as e:
                logger.debug(
                    "Memory semantic search failed; continuing with empty results",
                    exc_info=True,
                    extra={"module_name": "semantic_search_service", "error_type": type(e).__name__},
                )

        # Sort by relevance score
        all_documents.sort(key=lambda d: d.get("relevance_score", 0.0), reverse=True)

        # Limit results
        limited_documents = all_documents[:limit_int]

        return {
            "success": True,
            "documents": limited_documents,
            "query": query,
            "source": sources[0] if isinstance(sources, list) and len(sources) == 1 else "hybrid",
            "embedding": query_embedding,
        }

    def _search_with_embeddings(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """Search with embeddings (alias for semantic_search)"""
        return self._semantic_search(params)

    def _generate_embedding(self, text: str) -> List[float]:
        """Generate embedding for text"""
        # Check cache first
        if text in self._embedding_cache:
            return self._embedding_cache[text]

        if self.embeddings:
            try:
                result = self.embeddings.execute("generate", {
                    "text": text,
                })
                embedding = result.get("embedding", [])
                if embedding:
                    # Cache result
                    self._cache_embedding(text, embedding)
                    return embedding
            except Exception as e:
                logger.debug(
                    "Embedding generation failed; using fallback embedding",
                    exc_info=True,
                    extra={"module_name": "semantic_search_service", "error_type": type(e).__name__},
                )

        # Fallback: return zero vector
        return [0.0] * 768

    def _cache_embedding(self, text: str, embedding: List[float]) -> None:
        """Cache embedding"""
        if len(self._embedding_cache) >= self._cache_max_size:
            # Remove oldest entry (simple FIFO)
            oldest_key = next(iter(self._embedding_cache))
            del self._embedding_cache[oldest_key]

        self._embedding_cache[text] = embedding

    def _cosine_similarity(self, vec1: List[float], vec2: List[float]) -> float:
        """Calculate cosine similarity"""
        if len(vec1) != len(vec2):
            return 0.0

        dot_product = sum(a * b for a, b in zip(vec1, vec2))
        magnitude1 = math.sqrt(sum(a * a for a in vec1))
        magnitude2 = math.sqrt(sum(b * b for b in vec2))

        if magnitude1 == 0 or magnitude2 == 0:
            return 0.0

        return dot_product / (magnitude1 * magnitude2)

