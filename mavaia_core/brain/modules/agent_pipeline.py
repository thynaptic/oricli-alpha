"""
Agent Pipeline Module - orchestrates search -> ranking -> synthesis -> answer formatting.
Acts as a thin router for Swift to call a single module.operation.
"""

from __future__ import annotations

from typing import Any, Dict, List, Tuple

from mavaia_core.brain.base_module import BaseBrainModule, ModuleMetadata
from module_registry import ModuleRegistry


class AgentPipelineModule(BaseBrainModule):
    """Runs the canonical agent pipeline for Q&A."""

    def __init__(self) -> None:
        self.search = None
        self.ranking = None
        self.synthesis = None
        self.answer = None
        self._ensure_modules()

    def _ensure_modules(self) -> None:
        self.search = ModuleRegistry.get_module("search_agent")
        self.ranking = ModuleRegistry.get_module("ranking_agent")
        self.synthesis = ModuleRegistry.get_module("synthesis_agent")
        self.answer = ModuleRegistry.get_module("answer_agent")

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
            raise ValueError(f"Unsupported operation: {operation}")

        query: str = params.get("query", "") or ""
        limit: int = int(params.get("limit", 10) or 10)
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
        return result.get("rankedDocuments") or documents

    def _run_synthesis(self, query: str, documents: List[Dict[str, Any]]) -> str:
        if not self.synthesis:
            return ""
        result = self.synthesis.execute("synthesize", {"query": query, "documents": documents})
        if result.get("success"):
            return result.get("answer", "") or ""
        return ""

    def _run_answer(self, query: str, answer: str, documents: List[Dict[str, Any]]) -> str:
        if not self.answer:
            return answer
        result = self.answer.execute("format_answer", {"query": query, "answer": answer, "documents": documents})
        if result.get("success"):
            return result.get("answer", answer)
        return answer


__all__ = ["AgentPipelineModule"]

