"""
Persistent Memory Service - Unified persistent memory service for reasoning-aware memory system
Converted from Swift PersistentMemoryService.swift
"""

from typing import Any, Dict, List, Optional
import sys
import math
from pathlib import Path

from mavaia_core.brain.base_module import BaseBrainModule, ModuleMetadata
from mavaia_core.brain.registry import ModuleRegistry
try:
    from models.memory_models import MemoryEntry, MemoryType
except ImportError:
    # Models not available - define minimal types
    MemoryEntry = None
    MemoryType = None


class PersistentMemoryServiceModule(BaseBrainModule):
    """Unified persistent memory service for reasoning-aware memory system"""

    def __init__(self):
        self.embeddings = None
        self.memory_graph = None
        self._modules_loaded = False
        self._default_embedding_dimensions = 768
        # In-memory storage (in production, would use database)
        self._memory_store: Dict[str, MemoryEntry] = {}

    @property
    def metadata(self) -> ModuleMetadata:
        return ModuleMetadata(
            name="persistent_memory_service",
            version="1.0.0",
            description="Unified persistent memory service for reasoning-aware memory system",
            operations=[
                "store_memory",
                "recall_memories",
                "update_memory",
                "delete_memory",
                "search_memories",
                "get_memory_by_id",
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
            self.embeddings = ModuleRegistry.get_module("embeddings")
            self.memory_graph = ModuleRegistry.get_module("memory_graph")
            self._modules_loaded = True
        except Exception:
            # Modules not available - will use fallback methods
            pass

    def execute(self, operation: str, params: Dict[str, Any]) -> Dict[str, Any]:
        """Execute an operation"""
        self._ensure_modules_loaded()

        if operation == "store_memory":
            return self._store_memory(params)
        elif operation == "recall_memories":
            return self._recall_memories(params)
        elif operation == "update_memory":
            return self._update_memory(params)
        elif operation == "delete_memory":
            return self._delete_memory(params)
        elif operation == "search_memories":
            return self._search_memories(params)
        elif operation == "get_memory_by_id":
            return self._get_memory_by_id(params)
        else:
            raise ValueError(f"Unknown operation: {operation}")

    def _store_memory(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """Store a new memory entry"""
        import uuid
        import time

        content = params.get("content", "")
        memory_type = params.get("type", MemoryType.CONVERSATION.value)
        metadata = params.get("metadata", {})
        importance = params.get("importance")
        conversation_id = params.get("conversation_id")
        message_id = params.get("message_id")
        tags = params.get("tags", [])
        keywords = params.get("keywords", [])
        emotional_tone = params.get("emotional_tone")

        # Calculate importance if not provided
        if importance is None:
            importance = self._calculate_importance(content, memory_type, metadata)

        # Extract keywords if not provided
        if not keywords:
            keywords = self._extract_keywords(content)

        # Create memory entry
        entry = MemoryEntry(
            id=str(uuid.uuid4()),
            type=memory_type,
            content=content,
            importance=importance,
            conversation_id=conversation_id,
            message_id=message_id,
            tags=tags,
            keywords=keywords,
            emotional_tone=emotional_tone,
        )

        # Generate embedding for semantic search
        embedding = self._generate_embedding(content)
        if embedding:
            entry.set_embedding(embedding)

        # Update cleanup priority
        entry.update_cleanup_priority()

        # Store in memory (in production, would save to database)
        self._memory_store[entry.id] = entry

        return {
            "success": True,
            "memory": {
                "id": entry.id,
                "type": entry.type,
                "content": entry.content,
                "importance": entry.importance,
            },
        }

    def _recall_memories(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """Recall memories matching a query"""
        query = params.get("query", "").strip()
        limit = params.get("limit", 10)
        min_score = params.get("min_score", 0.3)

        if not query:
            return {
                "success": True,
                "memories": [],
            }

        # Generate query embedding
        query_embedding = self._generate_embedding(query)
        query_lower = query.lower()
        query_words = [w for w in query_lower.split() if len(w) > 2]

        # Score and filter memories
        scored = []
        for memory in self._memory_store.values():
            score = 0.0

            # Semantic similarity (if embedding exists)
            if query_embedding and memory.get_embedding():
                similarity = self._cosine_similarity(query_embedding, memory.get_embedding())
                score += similarity * 0.5  # 50% weight for semantic similarity

            # Keyword matching
            content_lower = memory.content.lower()
            summary_lower = (memory.summary or "").lower()
            all_text = f"{content_lower} {summary_lower} {' '.join(memory.keywords)}"

            # Exact phrase match
            if query_lower in all_text:
                score += 0.3

            # Individual word matches
            if query_words:
                word_matches = sum(1 for word in query_words if word in all_text)
                score += (word_matches / len(query_words)) * 0.2

            # Recency boost
            import time
            days_since_access = (time.time() - memory.last_accessed) / (60 * 60 * 24)
            recency_boost = max(0.0, 1.0 - (days_since_access / 30.0)) * 0.1

            # Importance boost
            importance_boost = memory.importance * 0.1

            final_score = score + recency_boost + importance_boost

            if final_score >= min_score:
                scored.append((memory, final_score))
                # Mark as accessed
                memory.mark_accessed()

        # Sort by score and limit
        scored.sort(key=lambda x: x[1], reverse=True)
        scored = scored[:limit]

        return {
            "success": True,
            "memories": [
                {
                    "id": entry.id,
                    "type": entry.type,
                    "content": entry.content,
                    "summary": entry.summary,
                    "importance": entry.importance,
                    "score": score,
                }
                for entry, score in scored
            ],
        }

    def _update_memory(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """Update an existing memory"""
        memory_id = params.get("memory_id")
        content = params.get("content")
        summary = params.get("summary")
        importance = params.get("importance")
        tags = params.get("tags")
        keywords = params.get("keywords")
        emotional_tone = params.get("emotional_tone")

        if memory_id not in self._memory_store:
            return {
                "success": False,
                "error": "Memory not found",
            }

        entry = self._memory_store[memory_id]

        if content is not None:
            entry.content = content
            # Regenerate embedding for updated content
            embedding = self._generate_embedding(content)
            if embedding:
                entry.set_embedding(embedding)

        if summary is not None:
            entry.summary = summary

        if importance is not None:
            entry.importance = max(0.0, min(1.0, importance))

        if tags is not None:
            entry.tags = tags

        if keywords is not None:
            entry.keywords = keywords

        if emotional_tone is not None:
            entry.emotional_tone = emotional_tone

        entry.update_cleanup_priority()

        return {
            "success": True,
            "memory": {
                "id": entry.id,
                "type": entry.type,
                "content": entry.content,
            },
        }

    def _delete_memory(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """Delete a memory"""
        memory_id = params.get("memory_id")

        if memory_id not in self._memory_store:
            return {
                "success": False,
                "error": "Memory not found",
            }

        del self._memory_store[memory_id]

        return {
            "success": True,
        }

    def _search_memories(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """Search memories (alias for recall_memories)"""
        return self._recall_memories(params)

    def _get_memory_by_id(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """Get memory by ID"""
        memory_id = params.get("memory_id")

        if memory_id not in self._memory_store:
            return {
                "success": False,
                "error": "Memory not found",
            }

        entry = self._memory_store[memory_id]
        entry.mark_accessed()

        return {
            "success": True,
            "memory": {
                "id": entry.id,
                "type": entry.type,
                "content": entry.content,
                "summary": entry.summary,
                "importance": entry.importance,
                "tags": entry.tags,
                "keywords": entry.keywords,
            },
        }

    def _generate_embedding(self, text: str) -> Optional[List[float]]:
        """Generate embedding for text"""
        if self.embeddings:
            try:
                result = self.embeddings.execute("generate", {
                    "text": text,
                })
                return result.get("embedding")
            except:
                pass

        # Fallback: return None (no embedding)
        return None

    def _cosine_similarity(self, vec1: List[float], vec2: List[float]) -> float:
        """Calculate cosine similarity between two vectors"""
        if len(vec1) != len(vec2):
            return 0.0

        dot_product = sum(a * b for a, b in zip(vec1, vec2))
        magnitude1 = math.sqrt(sum(a * a for a in vec1))
        magnitude2 = math.sqrt(sum(b * b for b in vec2))

        if magnitude1 == 0 or magnitude2 == 0:
            return 0.0

        return dot_product / (magnitude1 * magnitude2)

    def _calculate_importance(self, content: str, memory_type: str, metadata: Dict[str, Any]) -> float:
        """Calculate importance score for memory"""
        # Simple heuristic: longer content = more important
        base_score = min(1.0, len(content) / 500.0)

        # Type-based importance
        type_scores = {
            MemoryType.PREFERENCE.value: 0.9,
            MemoryType.FACT.value: 0.7,
            MemoryType.CONVERSATION.value: 0.5,
            MemoryType.MESSAGE.value: 0.3,
        }
        type_score = type_scores.get(memory_type, 0.5)

        return (base_score + type_score) / 2.0

    def _extract_keywords(self, content: str) -> List[str]:
        """Extract keywords from content"""
        # Simple keyword extraction: take important words
        words = content.lower().split()
        # Filter out common stop words
        stop_words = {"the", "a", "an", "and", "or", "but", "in", "on", "at", "to", "for", "of", "with", "by"}
        keywords = [w for w in words if len(w) > 3 and w not in stop_words]
        return keywords[:10]  # Limit to 10 keywords

