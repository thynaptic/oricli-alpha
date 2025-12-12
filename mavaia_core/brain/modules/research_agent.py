"""
Research Agent Module - coordinates multi-pass research workflow.
Simplified orchestration using reasoning + document_orchestration when present.
"""

from __future__ import annotations

from typing import Any, Dict, List

from mavaia_core.brain.base_module import BaseBrainModule, ModuleMetadata


class ResearchAgentModule(BaseBrainModule):
    """Runs multi-pass research: generate sub-queries, gather docs, summarize."""

    def __init__(self) -> None:
        self.reasoning = None
        self.doc_orch = None
        self._modules_ensured = False

    def _ensure_modules(self) -> None:
        """Lazy load modules only when needed"""
        if self._modules_ensured:
            return
        self._modules_ensured = True
        try:
            from mavaia_core.brain.registry import ModuleRegistry
            self.reasoning = ModuleRegistry.get_module("reasoning", auto_discover=True, wait_timeout=1.0)
        except Exception:
            self.reasoning = None
        try:
            from mavaia_core.brain.registry import ModuleRegistry
            self.doc_orch = ModuleRegistry.get_module("document_orchestration", auto_discover=True, wait_timeout=1.0)
        except Exception:
            self.doc_orch = None

    @property
    def metadata(self) -> ModuleMetadata:
        return ModuleMetadata(
            name="research_agent",
            version="1.0.0",
            description="Multi-pass research orchestration",
            operations=["research"],
            dependencies=[],
            model_required=False,
        )

    def execute(self, operation: str, params: Dict[str, Any]) -> Dict[str, Any]:
        if operation != "research":
            raise ValueError(f"Unsupported operation: {operation}")

        # Lazy load modules only when execute is called
        self._ensure_modules()

        query: str = params.get("query", "") or ""
        max_passes = int(params.get("max_passes", 3) or 3)

        sub_queries = self._derive_sub_queries(query)
        documents: List[Dict[str, Any]] = []

        if self.doc_orch:
            try:
                doc_result = self.doc_orch.execute(
                    "route_multi_document",
                    {"text": query, "queries": sub_queries, "max_docs": params.get("limit", 10)},
                )
                documents = doc_result.get("documents") or doc_result.get("results") or []
            except Exception:
                documents = []

        summary = self._summarize(query, documents)

        return {
            "success": True,
            "query": query,
            "subQueries": sub_queries[: max_passes * 2],
            "documents": documents,
            "summary": summary,
            "sources": [d.get("url") for d in documents if d.get("url")] if isinstance(documents, list) else [],
        }

    # ------------------------------------------------------------------ #
    def _derive_sub_queries(self, query: str) -> List[str]:
        if self.reasoning:
            try:
                result = self.reasoning.execute("reason", {"query": f"Decompose: {query}", "reasoning_type": "analytical"})
                steps = result.get("reasoning_steps") or []
                if isinstance(steps, list):
                    return [str(s) for s in steps if s]
            except Exception:
                pass
        return [query, f"{query} key facts", f"{query} recent updates"]

    def _summarize(self, query: str, documents: List[Dict[str, Any]]) -> str:
        lines = [f"Research summary for '{query}':"]
        for idx, doc in enumerate(documents[:5], start=1):
            lines.append(f"{idx}. {doc.get('title','')}: {doc.get('snippet') or doc.get('content','')[:160]}")
        return "\n".join(lines)


__all__ = ["ResearchAgentModule"]

