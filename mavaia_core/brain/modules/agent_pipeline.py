"""
Agent Pipeline Module - orchestrates search -> ranking -> synthesis -> answer formatting.
Acts as a thin router for Swift to call a single module.operation.
"""

from __future__ import annotations

import logging
from typing import Any, Dict, List, Tuple

from mavaia_core.brain.base_module import BaseBrainModule, ModuleMetadata
from mavaia_core.brain.registry import ModuleRegistry
from mavaia_core.exceptions import InvalidParameterError

logger = logging.getLogger(__name__)


class AgentPipelineModule(BaseBrainModule):
    """Runs the canonical agent pipeline for Q&A."""

    def __init__(self) -> None:
        super().__init__()
        self.search = None
        self.ranking = None
        self.synthesis = None
        self.answer = None
        self._ensure_modules()

    def _ensure_modules(self) -> None:
        try:
            self.search = ModuleRegistry.get_module("search_agent", auto_discover=True, wait_timeout=1.0)
        except Exception as e:
            logger.debug(
                "Failed to load search_agent",
                exc_info=True,
                extra={"module_name": "agent_pipeline", "dependency": "search_agent", "error_type": type(e).__name__},
            )
            self.search = None
        try:
            self.ranking = ModuleRegistry.get_module("ranking_agent", auto_discover=True, wait_timeout=1.0)
        except Exception as e:
            logger.debug(
                "Failed to load ranking_agent",
                exc_info=True,
                extra={"module_name": "agent_pipeline", "dependency": "ranking_agent", "error_type": type(e).__name__},
            )
            self.ranking = None
        try:
            self.synthesis = ModuleRegistry.get_module("synthesis_agent", auto_discover=True, wait_timeout=1.0)
        except Exception as e:
            logger.debug(
                "Failed to load synthesis_agent",
                exc_info=True,
                extra={"module_name": "agent_pipeline", "dependency": "synthesis_agent", "error_type": type(e).__name__},
            )
            self.synthesis = None
        try:
            self.answer = ModuleRegistry.get_module("answer_agent", auto_discover=True, wait_timeout=1.0)
        except Exception as e:
            logger.debug(
                "Failed to load answer_agent",
                exc_info=True,
                extra={"module_name": "agent_pipeline", "dependency": "answer_agent", "error_type": type(e).__name__},
            )
            self.answer = None

    @property
    def metadata(self) -> ModuleMetadata:
        return ModuleMetadata(
            name="agent_pipeline",
            version="1.0.0",
            description="End-to-end Q&A pipeline (search->rank->synthesize->answer)",
            operations=["run_pipeline"],
            dependencies=[],
            model_required=False,
        )

    def execute(self, operation: str, params: Dict[str, Any]) -> Dict[str, Any]:
        if operation != "run_pipeline":
            raise InvalidParameterError(
                parameter="operation",
                value=operation,
                reason="Unsupported operation for agent_pipeline",
            )

        query: str = params.get("query", "") or ""
        try:
            limit: int = int(params.get("limit", 10) or 10)
        except (TypeError, ValueError):
            limit = 10
        sources = params.get("sources") or ["web", "memory"]

        documents = self._run_search(query, limit=limit * 2, sources=sources)
        ranked = self._run_ranking(query, documents)
        answer = self._run_synthesis(query, ranked)
        formatted = self._run_answer(query, answer, ranked)

        return {
            "success": True,
            "query": query,
            "documents": ranked,
            "answer": formatted,
        }

    # ------------------------------------------------------------------ #
    def _run_search(self, query: str, limit: int, sources: List[str]) -> List[Dict[str, Any]]:
        if not self.search:
            return []
        result = self.search.execute("search", {"query": query, "limit": limit, "sources": sources})
        return result.get("documents") or []

    def _run_ranking(self, query: str, documents: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        if not self.ranking or not documents:
            return documents
        result = self.ranking.execute("rank", {"query": query, "documents": documents})
        return result.get("rankedDocuments") or result.get("ranked_documents") or documents

    def _run_synthesis(self, query: str, documents: List[Dict[str, Any]]) -> str:
        if not self.synthesis:
            return ""
        result = self.synthesis.execute("synthesize", {"query": query, "documents": documents})
        if result.get("success"):
            return result.get("answer") or result.get("synthesis") or ""
        return ""

    def _run_answer(self, query: str, answer: str, documents: List[Dict[str, Any]]) -> str:
        if not self.answer:
            return answer
        result = self.answer.execute("format_answer", {"query": query, "answer": answer, "documents": documents})
        if result.get("success"):
            return result.get("answer", answer)
        return answer


__all__ = ["AgentPipelineModule"]

