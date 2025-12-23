"""
Reranker Agent Module - Perplexity Multi-Agent Pipeline

Scores and ranks retrieved documents by relevance using multiple signals.
Part of the Perplexity Multi-Agent Pipeline.
"""

from __future__ import annotations

import logging
from typing import Any, Dict, List, Optional, Tuple
import re

from mavaia_core.brain.base_module import BaseBrainModule, ModuleMetadata
from mavaia_core.exceptions import InvalidParameterError

logger = logging.getLogger(__name__)


class RerankerAgent(BaseBrainModule):
    """
    Reranker Agent for scoring and ranking documents by relevance.
    
    Responsibilities:
    - Multi-factor relevance scoring
    - Semantic similarity calculation
    - Keyword matching
    - Result diversification
    - Top-k selection
    """

    def __init__(self):
        """Initialize the Reranker Agent"""
        super().__init__()
        self._embeddings = None
        self._phrase_embeddings = None
        self._world_knowledge = None
        self._query_agent = None

    @property
    def metadata(self) -> ModuleMetadata:
        return ModuleMetadata(
            name="reranker_agent",
            version="1.0.0",
            description=(
                "Reranker Agent: Scores and ranks documents by relevance "
                "for the Multi-Agent Pipeline"
            ),
            operations=[
                "rerank_documents",
                "calculate_relevance",
                "select_top_k",
                "diversify_results",
                "process_reranking",
            ],
            dependencies=[],
            enabled=True,
            model_required=False,
        )

    def initialize(self) -> bool:
        """Initialize dependent modules"""
        try:
            from mavaia_core.brain.registry import ModuleRegistry

            # Lazy load optional dependencies
            try:
                self._embeddings = ModuleRegistry.get_module("embeddings")
            except Exception as e:
                logger.debug(
                    "Failed to load dependency embeddings",
                    exc_info=True,
                    extra={"module_name": "reranker_agent", "dependency": "embeddings", "error_type": type(e).__name__},
                )

            try:
                self._phrase_embeddings = ModuleRegistry.get_module("phrase_embeddings")
            except Exception as e:
                logger.debug(
                    "Failed to load dependency phrase_embeddings",
                    exc_info=True,
                    extra={"module_name": "reranker_agent", "dependency": "phrase_embeddings", "error_type": type(e).__name__},
                )

            try:
                self._world_knowledge = ModuleRegistry.get_module("world_knowledge")
            except Exception as e:
                logger.debug(
                    "Failed to load dependency world_knowledge",
                    exc_info=True,
                    extra={"module_name": "reranker_agent", "dependency": "world_knowledge", "error_type": type(e).__name__},
                )

            try:
                self._query_agent = ModuleRegistry.get_module("query_agent")
            except Exception as e:
                logger.debug(
                    "Failed to load dependency query_agent",
                    exc_info=True,
                    extra={"module_name": "reranker_agent", "dependency": "query_agent", "error_type": type(e).__name__},
                )

            return True
        except Exception as e:
            logger.debug(
                "ModuleRegistry not available; reranker_agent will run without dependencies",
                exc_info=True,
                extra={"module_name": "reranker_agent", "error_type": type(e).__name__},
            )
            return True  # Can work without dependencies

    def execute(self, operation: str, params: Dict[str, Any]) -> Dict[str, Any]:
        """
        Execute Reranker Agent operations.

        Supported operations:
        - rerank_documents: Score documents using multiple signals
        - calculate_relevance: Multi-factor relevance scoring
        - select_top_k: Select top-k most relevant documents
        - diversify_results: Ensure result diversity
        - process_reranking: Full reranking pipeline
        """
        match operation:
            case "rerank_documents":
                documents = params.get("documents", [])
                query = params.get("query", "")
                return self.rerank_documents(documents, query)
            case "calculate_relevance":
                document = params.get("document", {})
                query = params.get("query", "")
                return self.calculate_relevance(document, query)
            case "select_top_k":
                documents = params.get("documents", [])
                k = params.get("k", 10)
                return self.select_top_k(documents, k)
            case "diversify_results":
                documents = params.get("documents", [])
                max_similar = params.get("max_similar", 0.8)
                return self.diversify_results(documents, max_similar)
            case "process_reranking":
                documents = params.get("documents", [])
                query = params.get("query", "")
                top_k = params.get("top_k", 10)
                return self.process_reranking(documents, query, top_k)
            case _:
                raise InvalidParameterError(
                    parameter="operation",
                    value=operation,
                    reason="Unknown operation for reranker_agent",
                )

    def rerank_documents(
        self, documents: List[Dict[str, Any]], query: str
    ) -> Dict[str, Any]:
        """
        Score documents using multiple signals.

        Args:
            documents: List of candidate documents
            query: Original query

        Returns:
            Dictionary with reranked documents and scores
        """
        if not documents:
            return {
                "documents": [],
                "count": 0,
            }

        if not query:
            # Return documents with existing relevance scores
            return {
                "documents": documents,
                "count": len(documents),
            }

        # Calculate relevance for each document
        scored_documents = []
        for doc in documents:
            relevance_result = self.calculate_relevance(doc, query)
            relevance_score = relevance_result.get("relevance", 0.0)
            factors = relevance_result.get("factors", {})

            # Update document with new scores
            doc_copy = doc.copy()
            doc_copy["relevance"] = relevance_score
            doc_copy["relevance_factors"] = factors
            scored_documents.append(doc_copy)

        # Sort by relevance
        scored_documents.sort(key=lambda x: x.get("relevance", 0.0), reverse=True)

        return {
            "documents": scored_documents,
            "count": len(scored_documents),
            "query": query,
        }

    def calculate_relevance(
        self, document: Dict[str, Any], query: str
    ) -> Dict[str, Any]:
        """
        Multi-factor relevance scoring.

        Args:
            document: Document to score
            query: Query string

        Returns:
            Dictionary with relevance score and factor breakdown
        """
        if not document or not query:
            return {
                "relevance": 0.0,
                "factors": {},
            }

        content = str(document.get("content", "")).lower()
        query_lower = query.lower()

        factors = {}

        # Factor 1: Semantic similarity (if embeddings available)
        semantic_score = 0.0
        if self._embeddings:
            try:
                # Get embeddings for query and document
                query_embed_result = self._embeddings.execute(
                    "generate",
                    {"text": query}
                )
                doc_embed_result = self._embeddings.execute(
                    "generate",
                    {"text": content[:500]}  # Limit content length
                )

                query_embed = query_embed_result.get("embedding", [])
                doc_embed = doc_embed_result.get("embedding", [])

                if query_embed and doc_embed:
                    # Calculate cosine similarity
                    similarity_result = self._embeddings.execute(
                        "similarity",
                        {
                            "text1": query,
                            "text2": content[:500],
                        }
                    )
                    semantic_score = similarity_result.get("similarity", 0.0)
            except Exception as e:
                logger.debug(
                    "Embedding-based similarity failed; continuing with lexical signals",
                    exc_info=True,
                    extra={"module_name": "reranker_agent", "dependency": "embeddings", "error_type": type(e).__name__},
                )

        factors["semantic_similarity"] = semantic_score

        # Factor 2: Keyword matching
        query_words = set(re.findall(r'\b\w+\b', query_lower))
        content_words = set(re.findall(r'\b\w+\b', content))

        # Exact keyword matches
        keyword_matches = len(query_words & content_words)
        keyword_score = min(1.0, keyword_matches / max(len(query_words), 1))
        factors["keyword_match"] = keyword_score

        # Factor 3: Phrase matching
        query_phrases = self._extract_phrases(query)
        content_phrases = self._extract_phrases(content)
        phrase_matches = sum(1 for qp in query_phrases if qp in content)
        phrase_score = min(1.0, phrase_matches / max(len(query_phrases), 1))
        factors["phrase_match"] = phrase_score

        # Factor 4: Existing relevance (if provided)
        existing_relevance = document.get("relevance", 0.0)
        factors["existing_relevance"] = existing_relevance

        # Factor 5: Document length (prefer medium-length documents)
        content_length = len(content)
        if 100 <= content_length <= 2000:
            length_score = 1.0
        elif content_length < 100:
            length_score = 0.5
        else:
            length_score = 0.8  # Slightly penalize very long documents
        factors["length_score"] = length_score

        # Factor 6: Source authority (if available)
        source = document.get("source", "")
        source_score = 1.0
        if source == "knowledge_base":
            source_score = 1.0
        elif source == "memory":
            source_score = 0.8
        else:
            source_score = 0.7
        factors["source_authority"] = source_score

        # Weighted combination
        weights = {
            "semantic_similarity": 0.4,
            "keyword_match": 0.25,
            "phrase_match": 0.15,
            "existing_relevance": 0.1,
            "length_score": 0.05,
            "source_authority": 0.05,
        }

        relevance = sum(
            factors.get(factor, 0.0) * weight
            for factor, weight in weights.items()
        )

        # Normalize to [0, 1]
        relevance = max(0.0, min(1.0, relevance))

        return {
            "relevance": relevance,
            "factors": factors,
            "weights": weights,
        }

    def _extract_phrases(self, text: str, min_length: int = 2, max_length: int = 4) -> List[str]:
        """Extract phrases (n-grams) from text"""
        words = re.findall(r'\b\w+\b', text.lower())
        phrases = []
        
        for n in range(min_length, max_length + 1):
            for i in range(len(words) - n + 1):
                phrase = ' '.join(words[i:i+n])
                phrases.append(phrase)
        
        return phrases

    def select_top_k(
        self, documents: List[Dict[str, Any]], k: int = 10
    ) -> Dict[str, Any]:
        """
        Select top-k most relevant documents.

        Args:
            documents: List of scored documents
            k: Number of documents to select

        Returns:
            Dictionary with top-k documents
        """
        if not documents:
            return {
                "documents": [],
                "count": 0,
                "k": k,
            }

        # Sort by relevance (should already be sorted, but ensure)
        sorted_docs = sorted(
            documents,
            key=lambda x: x.get("relevance", 0.0),
            reverse=True
        )

        top_k = sorted_docs[:k]

        return {
            "documents": top_k,
            "count": len(top_k),
            "k": k,
            "total_available": len(documents),
        }

    def diversify_results(
        self, documents: List[Dict[str, Any]], max_similar: float = 0.8
    ) -> Dict[str, Any]:
        """
        Ensure result diversity by removing highly similar documents.

        Args:
            documents: List of documents (should be sorted by relevance)
            max_similar: Maximum similarity threshold for diversity

        Returns:
            Dictionary with diversified documents
        """
        if not documents or len(documents) <= 1:
            return {
                "documents": documents,
                "count": len(documents),
                "removed": 0,
            }

        diversified = [documents[0]]  # Always include top result
        removed = []

        for doc in documents[1:]:
            is_similar = False

            # Check similarity with already selected documents
            for selected_doc in diversified:
                similarity = self._calculate_document_similarity(doc, selected_doc)
                if similarity > max_similar:
                    is_similar = True
                    break

            if not is_similar:
                diversified.append(doc)
            else:
                removed.append(doc)

        return {
            "documents": diversified,
            "count": len(diversified),
            "removed": len(removed),
            "removed_documents": removed,
        }

    def _calculate_document_similarity(
        self, doc1: Dict[str, Any], doc2: Dict[str, Any]
    ) -> float:
        """Calculate similarity between two documents"""
        content1 = str(doc1.get("content", "")).lower()
        content2 = str(doc2.get("content", "")).lower()

        # Use embeddings if available
        if self._embeddings:
            try:
                similarity_result = self._embeddings.execute(
                    "similarity",
                    {
                        "text1": content1[:500],
                        "text2": content2[:500],
                    }
                )
                return similarity_result.get("similarity", 0.0)
            except Exception as e:
                logger.debug(
                    "Embedding similarity failed; using lexical similarity",
                    exc_info=True,
                    extra={"module_name": "reranker_agent", "dependency": "embeddings", "error_type": type(e).__name__},
                )

        # Fallback: Jaccard similarity on words
        words1 = set(re.findall(r'\b\w+\b', content1))
        words2 = set(re.findall(r'\b\w+\b', content2))

        if not words1 or not words2:
            return 0.0

        intersection = len(words1 & words2)
        union = len(words1 | words2)

        return intersection / union if union > 0 else 0.0

    def process_reranking(
        self, documents: List[Dict[str, Any]], query: str, top_k: int = 10
    ) -> Dict[str, Any]:
        """
        Full reranking pipeline: score, rank, diversify, select top-k.

        Args:
            documents: List of candidate documents
            query: Original query
            top_k: Number of top documents to return

        Returns:
            Dictionary with final reranked documents
        """
        if not documents:
            return {
                "success": False,
                "error": "No documents provided",
            }

        if not query:
            # Just return top-k by existing relevance
            top_k_result = self.select_top_k(documents, top_k)
            return {
                "success": True,
                "documents": top_k_result.get("documents", []),
                "count": top_k_result.get("count", 0),
                "query": query,
            }

        # Step 1: Rerank documents
        rerank_result = self.rerank_documents(documents, query)
        reranked_docs = rerank_result.get("documents", [])

        # Step 2: Diversify results
        diversify_result = self.diversify_results(reranked_docs, max_similar=0.85)
        diversified_docs = diversify_result.get("documents", [])

        # Step 3: Select top-k
        top_k_result = self.select_top_k(diversified_docs, top_k)
        final_docs = top_k_result.get("documents", [])

        return {
            "success": True,
            "query": query,
            "documents": final_docs,
            "count": len(final_docs),
            "metadata": {
                "original_count": len(documents),
                "reranked_count": len(reranked_docs),
                "diversified_count": len(diversified_docs),
                "final_count": len(final_docs),
                "removed_for_diversity": diversify_result.get("removed", 0),
            },
        }

    def validate_params(self, operation: str, params: Dict[str, Any]) -> bool:
        """Validate parameters for operations"""
        match operation:
            case "rerank_documents" | "process_reranking":
                return "documents" in params and "query" in params
            case "calculate_relevance":
                return "document" in params and "query" in params
            case "select_top_k":
                return "documents" in params
            case "diversify_results":
                return "documents" in params
            case _:
                return True

