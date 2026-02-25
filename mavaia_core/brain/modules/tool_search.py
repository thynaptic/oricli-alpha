from __future__ import annotations
"""
Tool Search Module

Implements tool search functionality for Claude Tool Search Tool feature.
Supports both regex and BM25 search variants for discovering tools dynamically.
"""

import re
from typing import Any, Dict, List, Optional, Tuple
from collections import defaultdict
import math
import logging

from mavaia_core.brain.base_module import BaseBrainModule, ModuleMetadata
from mavaia_core.exceptions import (
    InvalidParameterError,
    ModuleInitializationError,
    ModuleOperationError,
)

# Lazy import to avoid timeout during module discovery
ToolRegistry = None
_TOOL_REGISTRY_IMPORT_FAILURE_LOGGED = False

logger = logging.getLogger(__name__)

def _lazy_import_tool_registry():
    """Lazy import ToolRegistry only when needed"""
    global ToolRegistry, _TOOL_REGISTRY_IMPORT_FAILURE_LOGGED
    if ToolRegistry is None:
        try:
            from mavaia_core.services.tool_registry import ToolRegistry as TR
            ToolRegistry = TR
        except ImportError:
            if not _TOOL_REGISTRY_IMPORT_FAILURE_LOGGED:
                _TOOL_REGISTRY_IMPORT_FAILURE_LOGGED = True
                logger.debug(
                    "ToolRegistry not available; tool_search disabled until installed",
                    exc_info=True,
                    extra={"module_name": "tool_search"},
                )


class ToolSearchModule(BaseBrainModule):
    """
    Tool Search Module for discovering tools dynamically.
    
    Supports regex and BM25 search to find tools based on queries.
    Searches through tool names, descriptions, and parameter descriptions.
    """
    
    def __init__(self):
        """Initialize tool search module."""
        super().__init__()
        self._tool_registry: Optional[ToolRegistry] = None
        self._bm25_index: Optional[Dict[str, Any]] = None
        self._bm25_k1 = 1.5  # BM25 k1 parameter (term frequency saturation)
        self._bm25_b = 0.75   # BM25 b parameter (length normalization)
    
    def _ensure_tool_registry(self):
        """Lazy load tool registry only when needed"""
        _lazy_import_tool_registry()
        if ToolRegistry is None:
            raise ModuleInitializationError(
                module_name=self.metadata.name,
                reason="ToolRegistry not available",
            )
        if self._tool_registry is None:
            self._tool_registry = ToolRegistry()
    
    @property
    def metadata(self) -> ModuleMetadata:
        """Return module metadata."""
        return ModuleMetadata(
            name="tool_search",
            version="1.0.0",
            description="Tool search for dynamic tool discovery using regex and BM25",
            operations=[
                "search_regex",
                "search_bm25",
            ],
            dependencies=[],
            enabled=True,
            model_required=False,
        )
    
    def initialize(self) -> bool:
        """Initialize the module."""
        return True
    
    def execute(self, operation: str, params: Dict[str, Any]) -> Dict[str, Any]:
        """Execute a tool search operation."""
        try:
            if operation == "search_regex":
                return self._search_regex(params)
            elif operation == "search_bm25":
                return self._search_bm25(params)
            else:
                raise InvalidParameterError("operation", str(operation), "Unknown operation for tool_search")
        except (InvalidParameterError, ModuleInitializationError) as e:
            raise ModuleOperationError(
                self.metadata.name,
                operation,
                str(e),
            )
        except Exception as e:
            logger.debug(
                "tool_search operation failed",
                exc_info=True,
                extra={"module_name": "tool_search", "operation": str(operation), "error_type": type(e).__name__},
            )
            raise ModuleOperationError(
                self.metadata.name,
                operation,
                "Unexpected error during tool search",
            )
    
    def _tokenize(self, text: str) -> List[str]:
        """
        Tokenize text into words.
        
        Args:
            text: Text to tokenize
            
        Returns:
            List of lowercase tokens
        """
        if not text:
            return []
        # Simple tokenization: split on non-word characters, lowercase
        tokens = re.findall(r'\b\w+\b', text.lower())
        return tokens
    
    def _build_tool_text(self, tool_def: Dict[str, Any]) -> str:
        """
        Build searchable text from tool definition.
        
        Args:
            tool_def: Tool definition dictionary
            
        Returns:
            Combined searchable text
        """
        parts = []
        
        # Add tool name (weighted more heavily)
        name = tool_def.get("name", "")
        parts.append(name)
        parts.append(name)  # Duplicate for higher weight
        
        # Add description
        description = tool_def.get("description", "")
        parts.append(description)
        
        # Add parameter names and descriptions
        parameters = tool_def.get("parameters", {})
        if isinstance(parameters, dict):
            for param_name, param_def in parameters.items():
                parts.append(param_name)
                if isinstance(param_def, dict):
                    param_desc = param_def.get("description", "")
                    if param_desc:
                        parts.append(param_desc)
        
        return " ".join(parts)
    
    def _build_bm25_index(self) -> Dict[str, Any]:
        """
        Build BM25 index from all tools.
        
        Returns:
            BM25 index dictionary with term frequencies and document lengths
        """
        self._ensure_tool_registry()
        tools = self._tool_registry.list_tools()
        
        # Build document corpus
        documents = []
        tool_names = []
        
        for tool_def in tools:
            tool_text = self._build_tool_text(tool_def)
            tokens = self._tokenize(tool_text)
            documents.append(tokens)
            tool_names.append(tool_def["name"])
        
        if not documents:
            return {
                "documents": [],
                "tool_names": [],
                "term_freq": {},
                "doc_freq": {},
                "doc_lengths": [],
                "avg_doc_length": 0.0,
            }
        
        # Calculate term frequencies and document frequencies
        term_freq = defaultdict(lambda: defaultdict(int))  # term -> doc_idx -> count
        doc_freq = defaultdict(int)  # term -> number of docs containing term
        doc_lengths = []
        
        for doc_idx, doc_tokens in enumerate(documents):
            doc_length = len(doc_tokens)
            doc_lengths.append(doc_length)
            
            # Count term frequencies in this document
            term_counts = defaultdict(int)
            for token in doc_tokens:
                term_counts[token] += 1
            
            for term, count in term_counts.items():
                term_freq[term][doc_idx] = count
                if count > 0:
                    doc_freq[term] += 1
        
        avg_doc_length = sum(doc_lengths) / len(doc_lengths) if doc_lengths else 0.0
        
        return {
            "documents": documents,
            "tool_names": tool_names,
            "term_freq": dict(term_freq),
            "doc_freq": dict(doc_freq),
            "doc_lengths": doc_lengths,
            "avg_doc_length": avg_doc_length,
        }
    
    def _calculate_bm25_score(
        self,
        query_terms: List[str],
        doc_idx: int,
        index: Dict[str, Any],
    ) -> float:
        """
        Calculate BM25 score for a document given query terms.
        
        Args:
            query_terms: List of query terms
            doc_idx: Document index
            index: BM25 index
            
        Returns:
            BM25 score
        """
        score = 0.0
        term_freq = index["term_freq"]
        doc_freq = index["doc_freq"]
        doc_lengths = index["doc_lengths"]
        avg_doc_length = index["avg_doc_length"]
        num_docs = len(index["documents"])
        
        if doc_idx >= len(doc_lengths):
            return 0.0
        
        doc_length = doc_lengths[doc_idx]
        
        # Count query term frequencies in document
        query_term_counts = defaultdict(int)
        for term in query_terms:
            query_term_counts[term] += 1
        
        for term, query_freq in query_term_counts.items():
            if term not in term_freq or doc_idx not in term_freq[term]:
                continue
            
            tf = term_freq[term][doc_idx]  # Term frequency in document
            df = doc_freq.get(term, 0)  # Document frequency
            
            if df == 0:
                continue
            
            # IDF component
            idf = math.log((num_docs - df + 0.5) / (df + 0.5) + 1.0)
            
            # Term frequency component with length normalization
            numerator = tf * (self._bm25_k1 + 1)
            denominator = tf + self._bm25_k1 * (
                1 - self._bm25_b + self._bm25_b * (doc_length / avg_doc_length)
            )
            
            # BM25 score component
            score += idf * (numerator / denominator) * query_freq
        
        return score
    
    def _search_regex(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """
        Search tools using regex pattern.
        
        Args:
            query: Regex pattern to search for
            limit: Optional limit on number of results (default: 10)
            search_deferred_only: If True, only search deferred tools (default: False)
            
        Returns:
            Dictionary with matching tool references
        """
        query = params.get("query")
        if query is None:
            raise InvalidParameterError("query", None, "query parameter is required")
        if not isinstance(query, str) or not query.strip():
            raise InvalidParameterError("query", str(query), "query must be a non-empty string")
        
        limit = params.get("limit", 10)
        try:
            limit_int = int(limit)
        except (TypeError, ValueError):
            raise InvalidParameterError("limit", str(limit), "limit must be an integer")
        if limit_int < 1:
            raise InvalidParameterError("limit", str(limit_int), "limit must be >= 1")
        
        search_deferred_only = params.get("search_deferred_only", False)
        if not isinstance(search_deferred_only, bool):
            raise InvalidParameterError(
                "search_deferred_only", str(search_deferred_only), "search_deferred_only must be a boolean"
            )
        
        # Compile regex pattern
        try:
            pattern = re.compile(query, re.IGNORECASE)
        except re.error as e:
            raise InvalidParameterError(
                "query",
                query,
                f"Invalid regex pattern: {str(e)}"
            )
        
        # Get tools to search
        self._ensure_tool_registry()
        if search_deferred_only:
            tools = self._tool_registry.list_deferred_tools()
        else:
            tools = self._tool_registry.list_tools()
        
        # Search through tools
        matches = []
        for tool_def in tools:
            tool_name = tool_def.get("name", "")
            tool_text = self._build_tool_text(tool_def)
            
            # Check if pattern matches
            if pattern.search(tool_name) or pattern.search(tool_text):
                matches.append({
                    "type": "tool_reference",
                    "name": tool_name,
                })
        
        # Limit results
        matches = matches[:limit_int]
        
        return {
            "success": True,
            "matches": matches,
            "count": len(matches),
            "query": query,
        }
    
    def _search_bm25(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """
        Search tools using BM25 ranking.
        
        Args:
            query: Search query string
            limit: Optional limit on number of results (default: 10)
            search_deferred_only: If True, only search deferred tools (default: False)
            
        Returns:
            Dictionary with matching tool references ranked by BM25 score
        """
        query = params.get("query")
        if query is None:
            raise InvalidParameterError("query", None, "query parameter is required")
        if not isinstance(query, str) or not query.strip():
            raise InvalidParameterError("query", str(query), "query must be a non-empty string")
        
        limit = params.get("limit", 10)
        try:
            limit_int = int(limit)
        except (TypeError, ValueError):
            raise InvalidParameterError("limit", str(limit), "limit must be an integer")
        if limit_int < 1:
            raise InvalidParameterError("limit", str(limit_int), "limit must be >= 1")
        
        search_deferred_only = params.get("search_deferred_only", False)
        if not isinstance(search_deferred_only, bool):
            raise InvalidParameterError(
                "search_deferred_only", str(search_deferred_only), "search_deferred_only must be a boolean"
            )
        
        # Tokenize query
        query_terms = self._tokenize(query)
        if not query_terms:
            return {
                "success": True,
                "matches": [],
                "count": 0,
                "query": query,
            }
        
        # Get tools to search
        self._ensure_tool_registry()
        if search_deferred_only:
            tools = self._tool_registry.list_deferred_tools()
        else:
            tools = self._tool_registry.list_tools()
        
        if not tools:
            return {
                "success": True,
                "matches": [],
                "count": 0,
                "query": query,
            }
        
        # Build BM25 index for current tool set
        # Filter index to only include tools we're searching
        tool_name_set = {t["name"] for t in tools}
        
        # Build index only for tools we're searching
        documents = []
        tool_names = []
        for tool_def in tools:
            tool_text = self._build_tool_text(tool_def)
            tokens = self._tokenize(tool_text)
            documents.append(tokens)
            tool_names.append(tool_def["name"])
        
        if not documents:
            return {
                "success": True,
                "matches": [],
                "count": 0,
                "query": query,
            }
        
        # Build index
        term_freq = defaultdict(lambda: defaultdict(int))
        doc_freq = defaultdict(int)
        doc_lengths = []
        
        for doc_idx, doc_tokens in enumerate(documents):
            doc_length = len(doc_tokens)
            doc_lengths.append(doc_length)
            
            term_counts = defaultdict(int)
            for token in doc_tokens:
                term_counts[token] += 1
            
            for term, count in term_counts.items():
                term_freq[term][doc_idx] = count
                if count > 0:
                    doc_freq[term] += 1
        
        avg_doc_length = sum(doc_lengths) / len(doc_lengths) if doc_lengths else 0.0
        
        index = {
            "documents": documents,
            "tool_names": tool_names,
            "term_freq": dict(term_freq),
            "doc_freq": dict(doc_freq),
            "doc_lengths": doc_lengths,
            "avg_doc_length": avg_doc_length,
        }
        
        # Calculate BM25 scores for each document
        scores = []
        for doc_idx in range(len(documents)):
            score = self._calculate_bm25_score(query_terms, doc_idx, index)
            scores.append((score, doc_idx))
        
        # Sort by score (descending)
        scores.sort(reverse=True, key=lambda x: x[0])
        
        # Build results
        matches = []
        for score, doc_idx in scores:
            if score > 0:  # Only include documents with positive scores
                tool_name = tool_names[doc_idx]
                matches.append({
                    "type": "tool_reference",
                    "name": tool_name,
                })
        
        # Limit results
        matches = matches[:limit_int]
        
        return {
            "success": True,
            "matches": matches,
            "count": len(matches),
            "query": query,
        }

