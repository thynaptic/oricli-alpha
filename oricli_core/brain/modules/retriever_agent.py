"""
Retriever Agent Module - Perplexity Multi-Agent Pipeline

Fetches candidate documents from various sources including knowledge base,
memory, and external sources. Part of the Perplexity Multi-Agent Pipeline.
"""

from __future__ import annotations

import logging
from typing import Any, Dict, List

from oricli_core.brain.base_module import BaseBrainModule, ModuleMetadata
from oricli_core.exceptions import InvalidParameterError

logger = logging.getLogger(__name__)


class RetrieverAgent(BaseBrainModule):
    """
    Retriever Agent for fetching candidate documents from multiple sources.
    
    Responsibilities:
    - Retrieve documents from knowledge base
    - Retrieve from memory graph
    - Multi-source retrieval coordination
    - Query expansion for better recall
    - Initial document filtering
    """

    def __init__(self):
        """Initialize the Retriever Agent"""
        super().__init__()
        self._world_knowledge = None
        self._memory_graph = None
        self._document_orchestration = None
        self._embeddings = None
        self._query_agent = None

    @property
    def metadata(self) -> ModuleMetadata:
        return ModuleMetadata(
            name="retriever_agent",
            version="1.0.0",
            description=(
                "Retriever Agent: Fetches candidate documents from various sources "
                "for the Multi-Agent Pipeline"
            ),
            operations=[
                "retrieve_documents",
                "retrieve_from_sources",
                "expand_query",
                "filter_candidates",
                "process_retrieval",
            ],
            dependencies=[],
            enabled=True,
            model_required=False,
        )

    def initialize(self) -> bool:
        """Initialize dependent modules"""
        try:
            from oricli_core.brain.registry import ModuleRegistry

            # Lazy load optional dependencies
            try:
                self._world_knowledge = ModuleRegistry.get_module("world_knowledge")
            except Exception as e:
                logger.debug(
                    "Failed to load dependency world_knowledge",
                    exc_info=True,
                    extra={"module_name": "retriever_agent", "dependency": "world_knowledge", "error_type": type(e).__name__},
                )

            try:
                self._memory_graph = ModuleRegistry.get_module("memory_graph")
            except Exception as e:
                logger.debug(
                    "Failed to load dependency memory_graph",
                    exc_info=True,
                    extra={"module_name": "retriever_agent", "dependency": "memory_graph", "error_type": type(e).__name__},
                )

            try:
                self._document_orchestration = ModuleRegistry.get_module("document_orchestration")
            except Exception as e:
                logger.debug(
                    "Failed to load dependency document_orchestration",
                    exc_info=True,
                    extra={"module_name": "retriever_agent", "dependency": "document_orchestration", "error_type": type(e).__name__},
                )

            try:
                self._embeddings = ModuleRegistry.get_module("embeddings")
            except Exception as e:
                logger.debug(
                    "Failed to load dependency embeddings",
                    exc_info=True,
                    extra={"module_name": "retriever_agent", "dependency": "embeddings", "error_type": type(e).__name__},
                )

            try:
                self._query_agent = ModuleRegistry.get_module("query_agent")
            except Exception as e:
                logger.debug(
                    "Failed to load dependency query_agent",
                    exc_info=True,
                    extra={"module_name": "retriever_agent", "dependency": "query_agent", "error_type": type(e).__name__},
                )

            return True
        except Exception as e:
            logger.debug(
                "ModuleRegistry not available; retriever_agent will run without dependencies",
                exc_info=True,
                extra={"module_name": "retriever_agent", "error_type": type(e).__name__},
            )
            return True  # Can work without dependencies

    def execute(self, operation: str, params: Dict[str, Any]) -> Dict[str, Any]:
        """
        Execute Retriever Agent operations.

        Supported operations:
        - retrieve_documents: Fetch documents from knowledge base
        - retrieve_from_sources: Multi-source retrieval
        - expand_query: Query expansion for better retrieval
        - filter_candidates: Initial filtering of retrieved documents
        - process_retrieval: Full retrieval pipeline
        """
        if operation == "retrieve_documents":
            query = params.get("query", "")
            try:
                limit = int(params.get("limit", 20) or 20)
            except (TypeError, ValueError):
                limit = 20
            return self.retrieve_documents(query, limit)
        elif operation == "retrieve_from_sources":
            query = params.get("query", "")
            sources = params.get("sources", ["knowledge_base", "memory"])
            try:
                limit = int(params.get("limit", 20) or 20)
            except (TypeError, ValueError):
                limit = 20
            return self.retrieve_from_sources(query, sources, limit)
        elif operation == "expand_query":
            query = params.get("query", "")
            return self.expand_query(query)
        elif operation == "filter_candidates":
            documents = params.get("documents", [])
            query = params.get("query", "")
            min_relevance = params.get("min_relevance", 0.3)
            return self.filter_candidates(documents, query, min_relevance)
        elif operation == "process_retrieval":
            query = params.get("query", "")
            try:
                limit = int(params.get("limit", 20) or 20)
            except (TypeError, ValueError):
                limit = 20
            return self.process_retrieval(query, limit)
        else:
            raise InvalidParameterError(
                parameter="operation",
                value=operation,
                reason="Unknown operation for retriever_agent",
            )

    def retrieve_documents(
        self, query: str, limit: int = 20
    ) -> Dict[str, Any]:
        """
        Fetch documents from knowledge base.

        Args:
            query: Search query
            limit: Maximum number of documents to retrieve

        Returns:
            Dictionary with retrieved documents and metadata
        """
        if not query:
            return {
                "documents": [],
                "count": 0,
                "sources": [],
            }

        documents = []
        sources_used = []

        # Retrieve from world_knowledge if available
        if self._world_knowledge:
            try:
                # Try semantic search first
                knowledge_result = self._world_knowledge.execute(
                    "query_knowledge",
                    {
                        "query": query,
                        "query_type": "semantic",
                        "limit": limit,
                    }
                )
                results = knowledge_result.get("results", [])
                
                for result in results:
                    fact = result.get("fact", "")
                    fact_id = result.get("fact_id") or result.get("key", "")
                    relevance = result.get("similarity") or result.get("relevance", 0.5)
                    entities = result.get("entities", [])
                    
                    if fact:
                        documents.append({
                            "id": fact_id or f"kb_{len(documents)}",
                            "content": fact,
                            "source": "knowledge_base",
                            "relevance": relevance,
                            "entities": entities,
                            "metadata": {
                                "type": "fact",
                                "source_type": "knowledge_base",
                            },
                        })
                
                if results:
                    sources_used.append("knowledge_base")
            except Exception as e:
                logger.debug(
                    "world_knowledge semantic query failed; attempting text query fallback",
                    exc_info=True,
                    extra={"module_name": "retriever_agent", "dependency": "world_knowledge", "error_type": type(e).__name__},
                )
                # Fallback: try text search
                try:
                    knowledge_result = self._world_knowledge.execute(
                        "query_knowledge",
                        {
                            "query": query,
                            "query_type": "text",
                            "limit": limit,
                        }
                    )
                    results = knowledge_result.get("results", [])
                    
                    for result in results:
                        fact = result.get("fact", "")
                        if fact:
                            documents.append({
                                "id": result.get("key", f"kb_{len(documents)}"),
                                "content": fact,
                                "source": "knowledge_base",
                                "relevance": 0.5,
                                "entities": result.get("entities", []),
                                "metadata": {
                                    "type": "fact",
                                    "source_type": "knowledge_base",
                                },
                            })
                    
                    if results:
                        sources_used.append("knowledge_base")
                except Exception as e2:
                    logger.debug(
                        "world_knowledge text query fallback failed",
                        exc_info=True,
                        extra={"module_name": "retriever_agent", "dependency": "world_knowledge", "error_type": type(e2).__name__},
                    )

        # Limit results
        documents = documents[:limit]

        return {
            "documents": documents,
            "count": len(documents),
            "sources": sources_used,
            "query": query,
        }

    def retrieve_from_sources(
        self, query: str, sources: List[str], limit: int = 20
    ) -> Dict[str, Any]:
        """
        Retrieve documents from multiple sources.

        Args:
            query: Search query
            sources: List of source types to query ("knowledge_base", "memory", "external")
            limit: Maximum number of documents per source

        Returns:
            Dictionary with documents from all sources
        """
        if not query:
            return {
                "documents": [],
                "count": 0,
                "sources_queried": sources,
            }

        all_documents = []
        sources_queried = []

        # Knowledge base retrieval
        if "knowledge_base" in sources:
            kb_result = self.retrieve_documents(query, limit)
            kb_docs = kb_result.get("documents", [])
            all_documents.extend(kb_docs)
            if kb_docs:
                sources_queried.append("knowledge_base")

        # Memory graph retrieval
        if "memory" in sources and self._memory_graph:
            try:
                # Search memory graph for relevant memories
                memory_result = self._memory_graph.execute(
                    "search_memories",
                    {
                        "query": query,
                        "limit": limit,
                    }
                )
                memories = memory_result.get("memories", [])
                
                for memory in memories:
                    content = memory.get("content", "") or memory.get("text", "")
                    if content:
                        all_documents.append({
                            "id": memory.get("id", f"memory_{len(all_documents)}"),
                            "content": content,
                            "source": "memory",
                            "relevance": memory.get("relevance", 0.5),
                            "metadata": {
                                "type": "memory",
                                "source_type": "memory_graph",
                                "timestamp": memory.get("timestamp"),
                            },
                        })
                
                if memories:
                    sources_queried.append("memory")
            except Exception as e:
                logger.debug(
                    "memory_graph recall_memories failed; attempting query fallback",
                    exc_info=True,
                    extra={"module_name": "retriever_agent", "dependency": "memory_graph", "error_type": type(e).__name__},
                )
                # Try alternative memory search
                try:
                    memory_result = self._memory_graph.execute(
                        "query",
                        {
                            "query": query,
                            "limit": limit,
                        }
                    )
                    memories = memory_result.get("results", []) or memory_result.get("memories", [])
                    
                    for memory in memories:
                        content = str(memory.get("content", "") or memory.get("text", ""))
                        if content:
                            all_documents.append({
                                "id": memory.get("id", f"memory_{len(all_documents)}"),
                                "content": content,
                                "source": "memory",
                                "relevance": 0.5,
                                "metadata": {
                                    "type": "memory",
                                    "source_type": "memory_graph",
                                },
                            })
                    
                    if memories:
                        sources_queried.append("memory")
                except Exception as e2:
                    logger.debug(
                        "memory_graph query fallback failed",
                        exc_info=True,
                        extra={"module_name": "retriever_agent", "dependency": "memory_graph", "error_type": type(e2).__name__},
                    )

        # External sources support
        # Note: External source integration (web search APIs, external databases) can be added as needed
        if "external" in sources:
            # External sources would be queried here when integration is configured
            pass

        # Sort by relevance if available
        all_documents.sort(key=lambda x: x.get("relevance", 0.0), reverse=True)

        # Limit total results
        all_documents = all_documents[:limit * len(sources)]

        return {
            "documents": all_documents,
            "count": len(all_documents),
            "sources_queried": sources_queried,
            "sources_requested": sources,
            "query": query,
        }

    def expand_query(self, query: str) -> Dict[str, Any]:
        """
        Expand query for better retrieval recall.

        Args:
            query: Original query

        Returns:
            Dictionary with expanded query variations
        """
        if not query:
            return {
                "original": query,
                "expanded": query,
                "variations": [],
            }

        # Use query_agent if available to get keyword variations
        variations = [query]  # Always include original
        
        if self._query_agent:
            try:
                query_result = self._query_agent.execute(
                    "formulate_search_queries",
                    {"query": query, "max_variations": 5}
                )
                query_variations = query_result.get("queries", [])
                variations.extend([q.get("query", "") for q in query_variations if q.get("query")])
            except Exception as e:
                logger.debug(
                    "query_agent formulate_search_queries failed",
                    exc_info=True,
                    extra={"module_name": "retriever_agent", "dependency": "query_agent", "error_type": type(e).__name__},
                )

        # Extract keywords for expansion
        keywords = []
        if self._query_agent:
            try:
                keywords_result = self._query_agent.execute(
                    "extract_keywords",
                    {"query": query}
                )
                keywords = keywords_result.get("keywords", [])
            except Exception as e:
                logger.debug(
                    "query_agent extract_keywords failed",
                    exc_info=True,
                    extra={"module_name": "retriever_agent", "dependency": "query_agent", "error_type": type(e).__name__},
                )

        # Create expanded query with synonyms/related terms
        # For now, use keyword combinations
        expanded = query
        if keywords:
            # Add important keywords if not already present
            important_keywords = [kw for kw in keywords[:3] if kw.lower() not in query.lower()]
            if important_keywords:
                expanded = f"{query} {' '.join(important_keywords)}"

        return {
            "original": query,
            "expanded": expanded,
            "variations": variations[:5],  # Limit variations
            "keywords": keywords,
        }

    def filter_candidates(
        self, documents: List[Dict[str, Any]], query: str, min_relevance: float = 0.3
    ) -> Dict[str, Any]:
        """
        Initial filtering of retrieved documents.

        Args:
            documents: List of candidate documents
            query: Original query
            min_relevance: Minimum relevance threshold

        Returns:
            Dictionary with filtered documents
        """
        if not documents:
            return {
                "documents": [],
                "count": 0,
                "filtered_count": 0,
            }

        if not query:
            # No filtering if no query
            return {
                "documents": documents,
                "count": len(documents),
                "filtered_count": 0,
            }

        query_lower = query.lower()
        query_words = set(query_lower.split())

        filtered = []
        filtered_out = []

        for doc in documents:
            content = str(doc.get("content", "")).lower()
            relevance = doc.get("relevance", 0.0)

            # Check relevance threshold
            if relevance < min_relevance:
                # Try to calculate basic relevance if not provided
                content_words = set(content.split())
                word_overlap = len(query_words & content_words)
                calculated_relevance = min(1.0, word_overlap / max(len(query_words), 1))
                
                if calculated_relevance < min_relevance:
                    filtered_out.append(doc)
                    continue

            # Check if document has minimum content
            if len(content.strip()) < 10:
                filtered_out.append(doc)
                continue

            # Update relevance if calculated
            if relevance < min_relevance:
                content_words = set(content.split())
                word_overlap = len(query_words & content_words)
                doc["relevance"] = min(1.0, word_overlap / max(len(query_words), 1))

            filtered.append(doc)

        # Sort by relevance
        filtered.sort(key=lambda x: x.get("relevance", 0.0), reverse=True)

        return {
            "documents": filtered,
            "count": len(filtered),
            "filtered_count": len(filtered_out),
            "min_relevance": min_relevance,
        }

    def process_retrieval(self, query: str, limit: int = 20) -> Dict[str, Any]:
        """
        Full retrieval pipeline: expand query, retrieve, filter.

        Args:
            query: Original query
            limit: Maximum number of documents to retrieve

        Returns:
            Dictionary with complete retrieval results
        """
        if not query:
            return {
                "success": False,
                "error": "Empty query",
            }

        # Step 1: Expand query
        expansion_result = self.expand_query(query)
        expanded_query = expansion_result.get("expanded", query)
        query_variations = expansion_result.get("variations", [query])

        # Step 2: Retrieve from multiple sources
        retrieval_result = self.retrieve_from_sources(
            expanded_query,
            sources=["knowledge_base", "memory"],
            limit=limit * 2,  # Retrieve more for filtering
        )

        # Step 3: Filter candidates
        documents = retrieval_result.get("documents", [])
        filter_result = self.filter_candidates(documents, query, min_relevance=0.3)

        filtered_documents = filter_result.get("documents", [])

        # Limit final results
        final_documents = filtered_documents[:limit]

        return {
            "success": True,
            "query": query,
            "expanded_query": expanded_query,
            "query_variations": query_variations,
            "documents": final_documents,
            "count": len(final_documents),
            "sources": retrieval_result.get("sources_queried", []),
            "metadata": {
                "retrieved_count": len(documents),
                "filtered_count": filter_result.get("filtered_count", 0),
                "final_count": len(final_documents),
            },
        }

    def validate_params(self, operation: str, params: Dict[str, Any]) -> bool:
        """Validate parameters for operations"""
        if operation == 'retrieve_documents' or operation == 'process_retrieval':
            return "query" in params
        elif operation == "retrieve_from_sources":
            return "query" in params and "sources" in params
        elif operation == "expand_query":
            return "query" in params
        elif operation == "filter_candidates":
            return "documents" in params and "query" in params
        else:
            return True

