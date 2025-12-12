"""
Query Agent Module - Perplexity Multi-Agent Pipeline

Normalizes user input, extracts keywords, and formulates precise search queries.
Part of the Perplexity Multi-Agent Pipeline implementation.
"""

import re
from typing import Any, Dict, List, Optional, Set
from pathlib import Path
import sys

from mavaia_core.brain.base_module import BaseBrainModule, ModuleMetadata


class QueryAgent(BaseBrainModule):
    """
    Query Agent for normalizing queries and extracting search-relevant information.
    
    Responsibilities:
    - Normalize and clean user input
    - Extract keywords and entities
    - Formulate multiple search query variations
    - Analyze query intent and complexity
    """

    def __init__(self):
        """Initialize the Query Agent"""
        self._query_complexity = None
        self._intent_categorizer = None
        self._world_knowledge = None
        self._stop_words = {
            "a", "an", "and", "are", "as", "at", "be", "by", "for", "from",
            "has", "he", "in", "is", "it", "its", "of", "on", "that", "the",
            "to", "was", "will", "with", "the", "this", "but", "they", "have",
            "had", "what", "said", "each", "which", "their", "time", "if",
            "up", "out", "many", "then", "them", "these", "so", "some", "her",
            "would", "make", "like", "into", "him", "has", "two", "more",
            "very", "after", "words", "long", "than", "first", "been", "call",
            "who", "oil", "sit", "now", "find", "down", "day", "did", "get",
            "come", "made", "may", "part"
        }

    @property
    def metadata(self) -> ModuleMetadata:
        return ModuleMetadata(
            name="query_agent",
            version="1.0.0",
            description=(
                "Query Agent: Normalizes user input, extracts keywords, "
                "and formulates precise search queries for the Multi-Agent Pipeline"
            ),
            operations=[
                "normalize_query",
                "extract_keywords",
                "formulate_search_queries",
                "analyze_query_intent",
                "process_query",
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
                self._query_complexity = ModuleRegistry.get_module("query_complexity")
            except Exception:
                pass

            try:
                self._intent_categorizer = ModuleRegistry.get_module("intent_categorizer")
            except Exception:
                pass

            try:
                self._world_knowledge = ModuleRegistry.get_module("world_knowledge")
            except Exception:
                pass

            return True
        except Exception:
            return True  # Can work without dependencies

    def execute(self, operation: str, params: Dict[str, Any]) -> Dict[str, Any]:
        """
        Execute Query Agent operations.

        Supported operations:
        - normalize_query: Clean and normalize user input
        - extract_keywords: Extract relevant keywords and entities
        - formulate_search_queries: Generate multiple search query variations
        - analyze_query_intent: Determine query type and complexity
        - process_query: Full query processing pipeline
        """
        match operation:
            case "normalize_query":
                query = params.get("query", "")
                return self.normalize_query(query)
            case "extract_keywords":
                query = params.get("query", "")
                return self.extract_keywords(query)
            case "formulate_search_queries":
                query = params.get("query", "")
                max_variations = params.get("max_variations", 5)
                return self.formulate_search_queries(query, max_variations)
            case "analyze_query_intent":
                query = params.get("query", "")
                return self.analyze_query_intent(query)
            case "process_query":
                query = params.get("query", "")
                return self.process_query(query)
            case _:
                raise ValueError(f"Unknown operation: {operation}")

    def normalize_query(self, query: str) -> Dict[str, Any]:
        """
        Clean and normalize user input.

        Args:
            query: Raw user query string

        Returns:
            Dictionary with normalized query and metadata
        """
        if not query or not isinstance(query, str):
            return {
                "normalized": "",
                "original": query,
                "length": 0,
                "word_count": 0,
            }

        # Store original
        original = query.strip()

        # Remove extra whitespace
        normalized = re.sub(r'\s+', ' ', original).strip()

        # Remove special characters but keep punctuation that might be meaningful
        # Keep: letters, numbers, spaces, basic punctuation
        normalized = re.sub(r'[^\w\s\?\.\!\,\-]', ' ', normalized)

        # Normalize case (keep first letter capitalized for proper nouns)
        normalized = normalized.strip()

        # Remove leading/trailing punctuation
        normalized = normalized.strip('.,!?;:')

        word_count = len(normalized.split()) if normalized else 0

        return {
            "normalized": normalized,
            "original": original,
            "length": len(normalized),
            "word_count": word_count,
            "changes": original != normalized,
        }

    def extract_keywords(self, query: str) -> Dict[str, Any]:
        """
        Extract relevant keywords and entities from query.

        Args:
            query: Query string to analyze

        Returns:
            Dictionary with extracted keywords, entities, and metadata
        """
        if not query:
            return {
                "keywords": [],
                "entities": [],
                "key_phrases": [],
                "count": 0,
            }

        # Normalize first
        normalized_result = self.normalize_query(query)
        normalized = normalized_result.get("normalized", query).lower()

        # Extract words (remove stop words)
        words = re.findall(r'\b\w+\b', normalized)
        keywords = [
            word for word in words
            if word not in self._stop_words and len(word) > 2
        ]

        # Extract potential entities (capitalized words, longer phrases)
        # Check with world_knowledge if available
        entities = []
        if self._world_knowledge:
            try:
                entity_result = self._world_knowledge.execute(
                    "find_entities",
                    {"text": query}
                )
                found_entities = entity_result.get("entities", [])
                entities = [
                    e.get("entity", "") for e in found_entities
                    if e.get("entity")
                ]
            except Exception:
                pass

        # Extract key phrases (2-3 word combinations)
        key_phrases = []
        words_list = normalized.split()
        for i in range(len(words_list) - 1):
            # 2-word phrases
            phrase = f"{words_list[i]} {words_list[i+1]}"
            if not any(sw in phrase for sw in self._stop_words):
                key_phrases.append(phrase)
            # 3-word phrases
            if i < len(words_list) - 2:
                phrase = f"{words_list[i]} {words_list[i+1]} {words_list[i+2]}"
                if not any(sw in phrase for sw in self._stop_words):
                    key_phrases.append(phrase)

        # Remove duplicates while preserving order
        seen = set()
        unique_keywords = []
        for kw in keywords:
            if kw not in seen:
                seen.add(kw)
                unique_keywords.append(kw)

        seen_phrases = set()
        unique_phrases = []
        for phrase in key_phrases:
            if phrase not in seen_phrases:
                seen_phrases.add(phrase)
                unique_phrases.append(phrase)

        return {
            "keywords": unique_keywords,
            "entities": entities,
            "key_phrases": unique_phrases[:10],  # Limit phrases
            "count": len(unique_keywords),
            "entity_count": len(entities),
            "phrase_count": len(unique_phrases),
        }

    def formulate_search_queries(
        self, query: str, max_variations: int = 5
    ) -> Dict[str, Any]:
        """
        Generate multiple search query variations.

        Args:
            query: Original query string
            max_variations: Maximum number of query variations to generate

        Returns:
            Dictionary with query variations and metadata
        """
        if not query:
            return {
                "queries": [],
                "original": query,
                "count": 0,
            }

        # Normalize
        normalized_result = self.normalize_query(query)
        normalized = normalized_result.get("normalized", query)

        # Extract keywords
        keywords_result = self.extract_keywords(query)
        keywords = keywords_result.get("keywords", [])
        key_phrases = keywords_result.get("key_phrases", [])

        queries = []

        # 1. Original normalized query
        queries.append({
            "query": normalized,
            "type": "original",
            "priority": 1,
        })

        # 2. Keyword-only query
        if keywords:
            keyword_query = " ".join(keywords[:5])
            queries.append({
                "query": keyword_query,
                "type": "keywords",
                "priority": 2,
            })

        # 3. Key phrase queries
        for phrase in key_phrases[:3]:
            queries.append({
                "query": phrase,
                "type": "phrase",
                "priority": 3,
            })

        # 4. Expanded query (add synonyms/related terms if available)
        # For now, create variations by removing less important words
        words = normalized.split()
        if len(words) > 3:
            # Remove articles and common words
            important_words = [
                w for w in words
                if w.lower() not in ["the", "a", "an", "is", "are", "was", "were"]
            ]
            if important_words:
                queries.append({
                    "query": " ".join(important_words),
                    "type": "expanded",
                    "priority": 4,
                })

        # 5. Question-form query (if not already a question)
        if not normalized.endswith("?"):
            queries.append({
                "query": f"{normalized}?",
                "type": "question",
                "priority": 5,
            })

        # Limit to max_variations
        queries = queries[:max_variations]

        return {
            "queries": queries,
            "original": query,
            "normalized": normalized,
            "count": len(queries),
        }

    def analyze_query_intent(self, query: str) -> Dict[str, Any]:
        """
        Determine query type and complexity.

        Args:
            query: Query string to analyze

        Returns:
            Dictionary with intent analysis and complexity metrics
        """
        if not query:
            return {
                "intent": "unknown",
                "complexity": 0.0,
                "query_type": "unknown",
                "requires_reasoning": False,
            }

        # Normalize
        normalized_result = self.normalize_query(query)
        normalized = normalized_result.get("normalized", query).lower()

        # Analyze complexity
        complexity_score = 0.0
        complexity_factors = {}
        if self._query_complexity:
            try:
                complexity_result = self._query_complexity.execute(
                    "analyze_complexity",
                    {"query": query}
                )
                complexity_score = complexity_result.get("overall", 0.0)
                complexity_factors = complexity_result.get("factors", {})
            except Exception:
                # Fallback: simple heuristics
                word_count = len(normalized.split())
                complexity_score = min(1.0, word_count / 20.0)
                complexity_factors = {"length": complexity_score}

        # Analyze intent
        intent = "information_request"
        query_type = "factual"

        # Check for question words
        question_words = ["what", "who", "where", "when", "why", "how", "which"]
        is_question = any(normalized.startswith(qw) for qw in question_words) or normalized.endswith("?")

        if is_question:
            if normalized.startswith("why"):
                intent = "explanation_request"
                query_type = "analytical"
            elif normalized.startswith("how"):
                intent = "process_request"
                query_type = "procedural"
            elif normalized.startswith("what"):
                intent = "definition_request"
                query_type = "factual"
            else:
                intent = "information_request"
                query_type = "factual"

        # Check for reasoning keywords
        reasoning_keywords = [
            "analyze", "compare", "explain", "evaluate", "assess",
            "reason", "why", "because", "therefore", "conclusion"
        ]
        requires_reasoning = any(kw in normalized for kw in reasoning_keywords)

        if requires_reasoning:
            query_type = "analytical"
            intent = "reasoning_request"

        # Use intent categorizer if available
        intent_category = None
        if self._intent_categorizer:
            try:
                intent_result = self._intent_categorizer.execute(
                    "categorize",
                    {"intent": query}
                )
                intent_category = intent_result.get("category", "casual_conversation")
            except Exception:
                pass

        return {
            "intent": intent,
            "intent_category": intent_category,
            "query_type": query_type,
            "complexity": complexity_score,
            "complexity_factors": complexity_factors,
            "requires_reasoning": requires_reasoning,
            "is_question": is_question,
            "word_count": len(normalized.split()),
        }

    def process_query(self, query: str) -> Dict[str, Any]:
        """
        Full query processing pipeline.

        Args:
            query: Raw user query

        Returns:
            Dictionary with complete query analysis
        """
        if not query:
            return {
                "success": False,
                "error": "Empty query",
            }

        # Step 1: Normalize
        normalized_result = self.normalize_query(query)

        # Step 2: Extract keywords
        keywords_result = self.extract_keywords(query)

        # Step 3: Formulate search queries
        queries_result = self.formulate_search_queries(query)

        # Step 4: Analyze intent
        intent_result = self.analyze_query_intent(query)

        return {
            "success": True,
            "normalized": normalized_result,
            "keywords": keywords_result,
            "search_queries": queries_result,
            "intent": intent_result,
            "metadata": {
                "original_query": query,
                "processed_at": self._get_timestamp(),
            },
        }

    def _get_timestamp(self) -> str:
        """Get current timestamp as ISO string"""
        from datetime import datetime
        return datetime.now().isoformat()

    def validate_params(self, operation: str, params: Dict[str, Any]) -> bool:
        """Validate parameters for operations"""
        match operation:
            case "normalize_query" | "extract_keywords" | "analyze_query_intent" | "process_query":
                return "query" in params or isinstance(params.get("query"), str)
            case "formulate_search_queries":
                return "query" in params or isinstance(params.get("query"), str)
            case _:
                return True

