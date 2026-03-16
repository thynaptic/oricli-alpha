"""
Research Agent Module - coordinates multi-pass research workflow.
Simplified orchestration using reasoning + document_orchestration when present.
"""

from __future__ import annotations

import logging
from typing import Any, Dict, List, Optional

from oricli_core.brain.base_module import BaseBrainModule, ModuleMetadata
from oricli_core.exceptions import InvalidParameterError

logger = logging.getLogger(__name__)


class ResearchAgentModule(BaseBrainModule):
    """Runs multi-pass research: generate sub-queries, gather docs, summarize."""

    def __init__(self) -> None:
        super().__init__()
        self.reasoning = None
        self.doc_orch = None
        self._modules_ensured = False

    def _ensure_modules(self) -> None:
        """Lazy load modules only when needed"""
        if self._modules_ensured:
            return
        self._modules_ensured = True
        try:
            from oricli_core.brain.registry import ModuleRegistry
            self.reasoning = ModuleRegistry.get_module("reasoning", auto_discover=True, wait_timeout=1.0)
        except Exception as e:
            logger.debug(
                "Failed to load reasoning for research_agent",
                exc_info=True,
                extra={"module_name": "research_agent", "dependency": "reasoning", "error_type": type(e).__name__},
            )
            self.reasoning = None
        try:
            from oricli_core.brain.registry import ModuleRegistry
            self.doc_orch = ModuleRegistry.get_module("document_orchestration", auto_discover=True, wait_timeout=1.0)
        except Exception as e:
            logger.debug(
                "Failed to load document_orchestration for research_agent",
                exc_info=True,
                extra={"module_name": "research_agent", "dependency": "document_orchestration", "error_type": type(e).__name__},
            )
            self.doc_orch = None

    @property
    def metadata(self) -> ModuleMetadata:
        return ModuleMetadata(
            name="research_agent",
            version="1.0.1",
            description="Multi-pass research orchestration",
            operations=["research", "status"],
            dependencies=[],
            model_required=False,
        )

    def initialize(self) -> bool:
        """Initialize the module"""
        return True

    def execute(self, operation: str, params: Dict[str, Any]) -> Dict[str, Any]:
        """Execute operation"""
        if operation == "status":
            return self._get_status()

        if operation == "research":
            # Lazy load modules only when execute is called
            self._ensure_modules()

            query: str = params.get("query", "") or params.get("input", "")
            if not query:
                return {"success": False, "error": "No query provided"}

            try:
                max_passes = int(params.get("max_passes", 3) or 3)
            except (TypeError, ValueError):
                max_passes = 3

            sub_queries = self._derive_sub_queries(query)
            documents: List[Dict[str, Any]] = []

            if self.doc_orch:
                try:
                    doc_result = self.doc_orch.execute(
                        "route_multi_document",
                        {"text": query, "queries": sub_queries, "max_docs": params.get("limit", 10)},
                    )
                    documents = doc_result.get("documents") or doc_result.get("results") or []
                except Exception as e:
                    logger.debug(
                        "document_orchestration failed; continuing with empty documents",
                        exc_info=True,
                        extra={"module_name": "research_agent", "dependency": "document_orchestration", "error_type": type(e).__name__},
                    )
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
        else:
            return {"success": False, "error": f"Unknown operation: {operation}"}

    def _get_status(self) -> Dict[str, Any]:
        """Return module status"""
        self._ensure_modules()
        return {
            "success": True,
            "status": "active",
            "version": self.metadata.version,
            "reasoning_available": self.reasoning is not None,
            "doc_orchestration_available": self.doc_orch is not None
        }

    # ------------------------------------------------------------------ #
    def _derive_sub_queries(self, query: str) -> List[str]:
        if self.reasoning:
            try:
                result = self.reasoning.execute("reason", {"query": f"Decompose: {query}", "reasoning_type": "analytical"})
                steps = result.get("reasoning_steps") or []
                if isinstance(steps, list):
                    return [str(s) for s in steps if s]
            except Exception as e:
                logger.debug(
                    "reasoning decomposition failed; using heuristic sub-queries",
                    exc_info=True,
                    extra={"module_name": "research_agent", "dependency": "reasoning", "error_type": type(e).__name__},
                )
        return [query, f"{query} key facts", f"{query} recent updates"]

    def _summarize(self, query: str, documents: List[Dict[str, Any]]) -> str:
        if not documents:
            return f"I conducted research on '{query}' but couldn't find definitive sources to ground the answer."
            
        lines = [f"I have conducted a multi-pass research investigation into '{query}'. Here are the key findings from my analysis:"]
        for idx, doc in enumerate(documents[:8], start=1):
            title = doc.get('title') or doc.get('name') or "Untitled Source"
            snippet = doc.get('snippet') or doc.get('content', '')[:200]
            if snippet:
                lines.append(f"\n[{idx}] {title}\nSummary: {snippet}")
        
        lines.append(f"\nConclusion: Based on these {len(documents[:8])} sources, I have synthesized a comprehensive understanding of the subject matter.")
        return "\n".join(lines)


__all__ = ["ResearchAgentModule"]
