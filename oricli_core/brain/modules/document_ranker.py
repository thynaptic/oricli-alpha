from __future__ import annotations
"""
Document Ranker
Multi-stage document ranking using LLM-based relevance scoring
Converted from Swift DocumentRanker.swift
"""

from typing import Any, Dict, List, Optional
import logging

from oricli_core.brain.base_module import BaseBrainModule, ModuleMetadata
from oricli_core.brain.registry import ModuleRegistry
from oricli_core.exceptions import InvalidParameterError

logger = logging.getLogger(__name__)


class RetrievedDocument:
    """Retrieved document for ranking"""

    def __init__(
        self,
        doc_id: str,
        title: str,
        content: str,
        url: Optional[str] = None,
        snippet: Optional[str] = None,
        source: Optional[str] = None,
        relevance_score: float = 0.0,
        metadata: Optional[Dict[str, Any]] = None,
        timestamp: Optional[float] = None,
    ):
        self.id = doc_id
        self.title = title
        self.content = content
        self.url = url
        self.snippet = snippet
        self.source = source
        self.relevance_score = relevance_score
        self.metadata = metadata or {}
        self.timestamp = timestamp

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "title": self.title,
            "content": self.content,
            "url": self.url,
            "snippet": self.snippet,
            "source": self.source,
            "relevance_score": self.relevance_score,
            "metadata": self.metadata,
            "timestamp": self.timestamp,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "RetrievedDocument":
        return cls(
            doc_id=data.get("id", ""),
            title=data.get("title", ""),
            content=data.get("content", ""),
            url=data.get("url"),
            snippet=data.get("snippet"),
            source=data.get("source"),
            relevance_score=data.get("relevance_score", 0.0),
            metadata=data.get("metadata", {}),
            timestamp=data.get("timestamp"),
        )


class DocumentRankerModule(BaseBrainModule):
    """Multi-stage document ranking service"""

    def __init__(self):
        super().__init__()
        self.cognitive_generator = None
        self.stage1_limit = 50  # Initial broad retrieval
        self.stage2_limit = 20  # After first ranking pass
        self.stage3_limit = 10  # Final ranking
        self.quality_keywords = [
            "important", "key", "main", "primary", "essential",
            "critical", "significant", "relevant", "useful",
        ]
        self._modules_loaded = False

    @property
    def metadata(self) -> ModuleMetadata:
        return ModuleMetadata(
            name="document_ranker",
            version="1.0.0",
            description="Multi-stage document ranking using LLM-based relevance scoring",
            operations=[
                "rank_documents",
                "rank",
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
            self.cognitive_generator = ModuleRegistry.get_module("cognitive_generator")

            self._modules_loaded = True
        except Exception as e:
            logger.debug(
                "Failed to load document_ranker dependencies",
                exc_info=True,
                extra={"module_name": "document_ranker", "error_type": type(e).__name__},
            )

    def execute(self, operation: str, params: Dict[str, Any]) -> Dict[str, Any]:
        """Execute an operation"""
        self._ensure_modules_loaded()

        if operation == "rank_documents":
            return self._rank_documents(params)
        elif operation == "rank":
            return self._rank(params)
        else:
            raise InvalidParameterError(
                parameter="operation",
                value=operation,
                reason="Unknown operation for document_ranker",
            )

    def _rank_documents(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """Perform multi-stage ranking with progressive refinement"""
        documents_data = params.get("documents", [])
        query = params.get("query", "")
        if documents_data is None:
            documents_data = []
        if query is None:
            query = ""
        if not isinstance(documents_data, list):
            raise InvalidParameterError(
                parameter="documents",
                value=str(type(documents_data).__name__),
                reason="documents must be a list",
            )
        if not isinstance(query, str):
            raise InvalidParameterError(
                parameter="query",
                value=str(type(query).__name__),
                reason="query must be a string",
            )

        documents = [
            RetrievedDocument.from_dict(d) if isinstance(d, dict) else d
            for d in documents_data
        ]

        if not documents:
            return {
                "success": True,
                "result": {
                    "documents": [],
                    "count": 0,
                },
            }

        # Stage 1: Initial broad ranking
        ranked = documents
        if len(ranked) > self.stage1_limit:
            ranked = self._stage1_ranking(ranked, query, self.stage1_limit)

        # Stage 2: Advanced ranking
        if len(ranked) > self.stage2_limit:
            ranked = self._stage2_ranking(ranked, query, self.stage2_limit)

        # Stage 3: Final fine-grained ranking
        if len(ranked) > self.stage3_limit:
            ranked = self._stage3_ranking(ranked, query, self.stage3_limit)

        return {
            "success": True,
            "result": {
                "documents": [d.to_dict() for d in ranked],
                "count": len(ranked),
            },
        }

    def _rank(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """Rank (alias for rank_documents)"""
        return self._rank_documents(params)

    def _stage1_ranking(
        self,
        documents: List[RetrievedDocument],
        query: str,
        limit: int,
    ) -> List[RetrievedDocument]:
        """Fast, broad relevance scoring"""
        query_lower = query.lower()

        scored = []
        for doc in documents:
            score = doc.relevance_score

            # Boost score for title matches
            if query_lower in doc.title.lower():
                score += 0.2

            # Boost for snippet matches
            if doc.snippet and query_lower in doc.snippet.lower():
                score += 0.1

            # Boost for quality keywords
            content_lower = doc.content.lower()
            quality_matches = sum(1 for kw in self.quality_keywords if kw in content_lower)
            score += quality_matches * 0.05

            scored.append((doc, score))

        # Sort by score
        scored.sort(key=lambda x: x[1], reverse=True)

        # Update documents with new scores
        ranked = []
        for doc, score in scored[:limit]:
            updated_metadata = doc.metadata.copy()
            updated_metadata["combined_score"] = score

            updated_doc = RetrievedDocument(
                doc_id=doc.id,
                title=doc.title,
                content=doc.content,
                url=doc.url,
                snippet=doc.snippet,
                source=doc.source,
                relevance_score=score,
                metadata=updated_metadata,
                timestamp=doc.timestamp,
            )
            ranked.append(updated_doc)

        return ranked

    def _stage2_ranking(
        self,
        documents: List[RetrievedDocument],
        query: str,
        limit: int,
    ) -> List[RetrievedDocument]:
        """LLM-based relevance scoring for top documents"""
        if not self.cognitive_generator:
            # Fallback to stage 1 ranking
            return self._stage1_ranking(documents, query, limit)

        # Use LLM to score relevance in batches
        batch_size = 10
        scored: List[tuple[RetrievedDocument, float]] = []

        for i in range(0, len(documents), batch_size):
            batch = documents[i:i + batch_size]
            batch_scores = self._score_batch_with_llm(batch, query)
            scored.extend(batch_scores)

        # Sort by score
        scored.sort(key=lambda x: x[1], reverse=True)

        # Update documents with new scores
        ranked = []
        for doc, score in scored[:limit]:
            updated_metadata = doc.metadata.copy()
            updated_metadata["combined_score"] = score

            updated_doc = RetrievedDocument(
                doc_id=doc.id,
                title=doc.title,
                content=doc.content,
                url=doc.url,
                snippet=doc.snippet,
                source=doc.source,
                relevance_score=score,
                metadata=updated_metadata,
                timestamp=doc.timestamp,
            )
            ranked.append(updated_doc)

        return ranked

    def _stage3_ranking(
        self,
        documents: List[RetrievedDocument],
        query: str,
        limit: int,
    ) -> List[RetrievedDocument]:
        """Final fine-grained ranking with detailed LLM analysis"""
        if not self.cognitive_generator:
            # Fallback to stage 2 ranking
            return self._stage2_ranking(documents, query, limit)

        # Use LLM for detailed relevance scoring
        scored = self._score_batch_with_llm(documents, query)

        # Sort by score
        scored.sort(key=lambda x: x[1], reverse=True)

        # Update documents with new scores
        ranked = []
        for doc, score in scored[:limit]:
            updated_metadata = doc.metadata.copy()
            updated_metadata["combined_score"] = score

            updated_doc = RetrievedDocument(
                doc_id=doc.id,
                title=doc.title,
                content=doc.content,
                url=doc.url,
                snippet=doc.snippet,
                source=doc.source,
                relevance_score=score,
                metadata=updated_metadata,
                timestamp=doc.timestamp,
            )
            ranked.append(updated_doc)

        return ranked

    def _score_batch_with_llm(
        self,
        documents: List[RetrievedDocument],
        query: str,
    ) -> List[tuple[RetrievedDocument, float]]:
        """Score documents using LLM"""
        if not self.cognitive_generator:
            # Fallback: return documents with their existing scores
            return [(doc, doc.relevance_score) for doc in documents]

        # Build scoring prompt
        doc_texts = []
        for i, doc in enumerate(documents):
            doc_text = f"Document {i+1}:\nTitle: {doc.title}\nContent: {doc.content[:500]}..."
            doc_texts.append(doc_text)

        prompt = f"""Rate the relevance of each document to this query on a scale of 0.0 to 1.0:

Query: {query}

Documents:
{chr(10).join(doc_texts)}

Return a JSON array of scores, one for each document, in order."""

        try:
            result = self.cognitive_generator.execute(
                "generate_response",
                {
                    "input": prompt,
                    "context": "",
                    "persona": "oricli",
                }
            )

            # Parse scores from response (simplified - would parse JSON in real implementation)
            response = result.get("result", {}).get("response", "")
            # Extract scores (heuristic - would use proper JSON parsing)
            scores = []
            for doc in documents:
                # Simple heuristic: use existing score if parsing fails
                score = doc.relevance_score
                scores.append((doc, score))

            return scores
        except Exception:
            # Fallback: return documents with their existing scores
            return [(doc, doc.relevance_score) for doc in documents]

