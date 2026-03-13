"""
Analysis Agent Module - deep analysis of retrieved information.
Uses ReasoningModule when available; falls back to heuristic summary.
"""

from __future__ import annotations

import logging
from typing import Any, Dict, List

from oricli_core.brain.base_module import BaseBrainModule, ModuleMetadata
from oricli_core.exceptions import InvalidParameterError

logger = logging.getLogger(__name__)


class AnalysisAgentModule(BaseBrainModule):
    """Performs analysis over documents leveraging reasoning module."""

    def __init__(self) -> None:
        super().__init__()
        self.reasoning = None
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
                "Failed to load reasoning for analysis_agent",
                exc_info=True,
                extra={"module_name": "analysis_agent", "dependency": "reasoning", "error_type": type(e).__name__},
            )
            self.reasoning = None

    @property
    def metadata(self) -> ModuleMetadata:
        return ModuleMetadata(
            name="analysis_agent",
            version="1.0.0",
            description="Document analysis via reasoning module",
            operations=["analyze"],
            dependencies=[],
            model_required=False,
        )

    def execute(self, operation: str, params: Dict[str, Any]) -> Dict[str, Any]:
        # Lazy load modules only when execute is called
        self._ensure_modules()
        
        if operation != "analyze":
            raise InvalidParameterError(
                parameter="operation",
                value=operation,
                reason="Unsupported operation for analysis_agent",
            )

        query: str = params.get("query", "") or ""
        documents: List[Dict[str, Any]] = params.get("documents") or []

        if self.reasoning:
            try:
                result = self.reasoning.execute(
                    "reason",
                    {"query": query, "context": [doc.get("snippet") or doc.get("content", "") for doc in documents]},
                )
                return {"success": True, "analysis": result.get("reasoning", ""), "metadata": result}
            except Exception as e:
                logger.debug(
                    "Reasoning failed in analysis_agent; using heuristic analysis",
                    exc_info=True,
                    extra={"module_name": "analysis_agent", "dependency": "reasoning", "error_type": type(e).__name__},
                )

        # Fallback heuristic summary
        summary_parts = []
        for doc in documents[:5]:
            title = doc.get("title", "")
            snippet = doc.get("snippet") or (doc.get("content", "")[:120])
            summary_parts.append(f"- {title}: {snippet}")

        analysis = "Key findings:\n" + "\n".join(summary_parts)
        return {"success": True, "analysis": analysis, "metadata": {"reasoning_type": "heuristic"}}


__all__ = ["AnalysisAgentModule"]

