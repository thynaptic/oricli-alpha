"""
Ranking Agent Module - multi-stage ranking shim.
Approximates Swift DocumentRanker using lightweight heuristics.
"""

from __future__ import annotations

import logging
from typing import Any, Dict, List

from mavaia_core.brain.base_module import BaseBrainModule, ModuleMetadata
from mavaia_core.exceptions import InvalidParameterError

logger = logging.getLogger(__name__)


class RankingAgentModule(BaseBrainModule):
    """Ranks documents by combined relevance heuristics."""

    def __init__(self) -> None:
        super().__init__()

    @property
    def metadata(self) -> ModuleMetadata:
        return ModuleMetadata(
            name="ranking_agent",
            version="1.0.0",
            description="Heuristic ranking for RetrievedDocument-style inputs",
            operations=["rank"],
            dependencies=[],
            model_required=False,
        )

    def execute(self, operation: str, params: Dict[str, Any]) -> Dict[str, Any]:
        if operation != "rank":
            raise InvalidParameterError(
                parameter="operation",
                value=operation,
                reason="Unsupported operation for ranking_agent",
            )

        documents: List[Dict[str, Any]] = params.get("documents") or []
        query: str = params.get("query", "") or ""
        ranked = self._rank_documents(documents, query=query)
        # Provide both camelCase and snake_case for downstream compatibility.
        return {
            "success": True,
            "rankedDocuments": ranked,
            "ranked_documents": ranked,
            "count": len(ranked),
        }

    # ------------------------------------------------------------------ #
    # Helpers
    # ------------------------------------------------------------------ #
    def _rank_documents(self, documents: List[Dict[str, Any]], query: str) -> List[Dict[str, Any]]:
        if not documents:
            return []

        query_lower = query.lower()
        ranked: List[Dict[str, Any]] = []
        for doc in documents:
            score = float(doc.get("relevanceScore", 0.0))
            title = (doc.get("title") or "").lower()
            snippet = (doc.get("snippet") or "").lower()
            content = (doc.get("content") or "").lower()

            if query_lower and query_lower in title:
                score += 0.2
            if query_lower and query_lower in snippet:
                score += 0.1
            if query_lower and query_lower in content:
                score += 0.05

            quality_keywords = {"research", "study", "analysis", "evidence", "data", "source"}
            quality_hits = sum(1 for kw in quality_keywords if kw in content)
            score += 0.05 * quality_hits

            enriched = dict(doc)
            enriched["relevanceScore"] = score
            metadata = dict(enriched.get("metadata") or {})
            metadata["combinedScore"] = score
            enriched["metadata"] = metadata
            ranked.append(enriched)

        ranked.sort(key=lambda d: d.get("relevanceScore", 0.0), reverse=True)
        return ranked


__all__ = ["RankingAgentModule"]

