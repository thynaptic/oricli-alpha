"""
Synthesis Agent Module - answer generation from ranked documents.
Uses cognitive_generator if available; falls back to stitched summary.
"""

from __future__ import annotations

from typing import Any, Dict, List

from mavaia_core.brain.base_module import BaseBrainModule, ModuleMetadata
from mavaia_core.brain.registry import ModuleRegistry


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
        except Exception:
            self.cog = None

    @property
    def metadata(self) -> ModuleMetadata:
        return ModuleMetadata(
            name="synthesis_agent",
            version="1.0.0",
            description="Generates answers from ranked documents",
            operations=["synthesize"],
            dependencies=[],
            model_required=False,
        )

    def execute(self, operation: str, params: Dict[str, Any]) -> Dict[str, Any]:
        if operation != "synthesize":
            raise ValueError(f"Unsupported operation: {operation}")

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
                return {"success": True, "answer": text, "documents": documents}
            except Exception as e:
                return {"success": False, "error": str(e)}

        answer = self._fallback_synthesis(query, documents)
        return {"success": True, "answer": answer, "documents": documents}

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

