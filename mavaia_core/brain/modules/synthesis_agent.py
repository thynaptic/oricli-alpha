"""
Synthesis Agent Module - answer generation from ranked documents.
Uses cognitive_generator if available; falls back to stitched summary.
"""

from __future__ import annotations

import logging
from typing import Any, Dict, List

from mavaia_core.brain.base_module import BaseBrainModule, ModuleMetadata
from mavaia_core.brain.registry import ModuleRegistry
from mavaia_core.exceptions import InvalidParameterError

logger = logging.getLogger(__name__)


class SynthesisAgentModule(BaseBrainModule):
    """Generates an answer from ranked documents."""

    def __init__(self) -> None:
        self.cog = None
        self._modules_ensured = False

    def _ensure_modules(self) -> None:
        """Lazy load modules only when needed"""
        if self._modules_ensured:
            return
        self._modules_ensured = True
        try:
            self.cog = ModuleRegistry.get_module("cognitive_generator", auto_discover=True, wait_timeout=1.0)
        except Exception as e:
            logger.debug(
                "Failed to load cognitive_generator for synthesis_agent",
                exc_info=True,
                extra={"module_name": "synthesis_agent", "error_type": type(e).__name__},
            )
            self.cog = None

    @property
    def metadata(self) -> ModuleMetadata:
        return ModuleMetadata(
            name="synthesis_agent",
            version="1.0.0",
            description="Generates answers from ranked documents",
            # Keep `process_synthesis` as a compatibility alias (older pipeline modules may call it).
            operations=["synthesize", "process_synthesis"],
            dependencies=[],
            model_required=False,
        )

    def execute(self, operation: str, params: Dict[str, Any]) -> Dict[str, Any]:
        if operation not in {"synthesize", "process_synthesis"}:
            raise InvalidParameterError(
                parameter="operation",
                value=operation,
                reason="Unsupported operation for synthesis_agent",
            )

        # Lazy load modules only when execute is called
        self._ensure_modules()

        query: str = params.get("query", "") or ""
        documents: List[Dict[str, Any]] = params.get("documents") or []

        if self.cog:
            try:
                result = self.cog.execute(
                    "generate_response",
                    {
                        "input": query,
                        "context": self._build_context(documents),
                        "persona": params.get("persona", "mavaia"),
                    },
                )
                text = result.get("response") or result.get("result") or ""
                if isinstance(text, dict):
                    text = text.get("response", "") or ""
                return {"success": True, "synthesis": text, "answer": text, "documents": documents}
            except Exception as e:
                logger.debug(
                    "cognitive_generator synthesis failed; using fallback synthesis",
                    exc_info=True,
                    extra={"module_name": "synthesis_agent", "error_type": type(e).__name__},
                )

        answer = self._fallback_synthesis(query, documents)
        return {"success": True, "synthesis": answer, "answer": answer, "documents": documents}

    # ------------------------------------------------------------------ #
    def _build_context(self, documents: List[Dict[str, Any]]) -> str:
        parts = []
        for idx, doc in enumerate(documents[:5], start=1):
            title = doc.get("title", "")
            snippet = doc.get("snippet") or (doc.get("content", "")[:200])
            url = doc.get("url")
            parts.append(f"{idx}. {title}\n{snippet}")
            if url:
                parts.append(f"Source: {url}")
        return "\n\n".join(parts)

    def _fallback_synthesis(self, query: str, documents: List[Dict[str, Any]]) -> str:
        if not documents:
            return f"No supporting documents found for '{query}'."
        lines = [f"Answer for '{query}':"]
        for idx, doc in enumerate(documents[:3], start=1):
            lines.append(f"{idx}. {doc.get('title','')}: {doc.get('snippet') or doc.get('content','')[:160]}")
        return "\n".join(lines)


__all__ = ["SynthesisAgentModule"]

