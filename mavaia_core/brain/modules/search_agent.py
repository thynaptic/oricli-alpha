"""
Search Agent Module - lightweight retrieval shim for Swift agents.
Produces normalized RetrievedDocument-style dictionaries compatible with Swift.
"""

from __future__ import annotations

import time
import uuid
from typing import Any, Dict, List

from mavaia_core.brain.base_module import BaseBrainModule, ModuleMetadata


class SearchAgentModule(BaseBrainModule):
    """Performs lightweight search orchestration."""

    def __init__(self) -> None:
        pass

    @property
    def metadata(self) -> ModuleMetadata:
        return ModuleMetadata(
            name="search_agent",
            version="1.0.0",
            description="Hybrid search shim returning RetrievedDocument-style results",
            operations=["search"],
            dependencies=[],
            model_required=False,
        )

    def execute(self, operation: str, params: Dict[str, Any]) -> Dict[str, Any]:
        if operation != "search":
            raise ValueError(f"Unsupported operation: {operation}")

        query: str = params.get("query", "") or ""
        limit: int = int(params.get("limit", 20) or 20)
        sources_param = params.get("sources") or ["web", "memory"]
        if isinstance(sources_param, str):
            sources = [sources_param]
        else:
            sources = list(sources_param)

        documents = self._build_synthetic_documents(query=query, limit=limit, sources=sources)

        return {
            "success": True,
            "documents": documents,
            "totalFound": len(documents),
            "sources": sources,
            "metadata": {
                "averageRelevanceScore": sum(d.get("relevanceScore", 0.0) for d in documents) / max(
                    len(documents), 1
                ),
                "retrievalTime": 0.01,
            },
        }

    # ------------------------------------------------------------------ #
    # Helpers
    # ------------------------------------------------------------------ #
    def _build_synthetic_documents(self, query: str, limit: int, sources: List[str]) -> List[Dict[str, Any]]:
        """Return lightweight synthetic docs so downstream steps always have context."""
        docs: List[Dict[str, Any]] = []
        ts = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
        for idx in range(max(1, min(limit, 5))):
            docs.append(
                {
                    "id": str(uuid.uuid4()),
                    "title": f"Synthetic result {idx + 1} for '{query}'",
                    "content": f"Auto-generated content for '{query}'.",
                    "url": None,
                    "snippet": f"Snippet {idx + 1} related to {query}",
                    "source": sources[idx % len(sources)] if sources else "memory",
                    "relevanceScore": 0.5 + (0.05 * idx),
                    "metadata": {
                        "sourceId": None,
                        "sourceType": None,
                        "importance": 0.5,
                        "tags": [],
                        "keywords": [query] if query else [],
                        "relationships": None,
                        "lexicalScore": 0.5,
                        "semanticScore": 0.5,
                        "combinedScore": 0.5 + (0.05 * idx),
                    },
                    "timestamp": ts,
                }
            )
        return docs


__all__ = ["SearchAgentModule"]

