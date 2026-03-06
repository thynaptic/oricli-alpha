"""
Synthesis Agent Module - answer generation from ranked documents.
Uses cognitive_generator if available; falls back to stitched summary.
"""

from __future__ import annotations

import logging
from typing import Any, Dict, List, Optional

from mavaia_core.brain.base_module import BaseBrainModule, ModuleMetadata
from mavaia_core.brain.registry import ModuleRegistry
from mavaia_core.exceptions import InvalidParameterError

logger = logging.getLogger(__name__)


class SynthesisAgentModule(BaseBrainModule):
    """Generates an answer from ranked documents."""

    def __init__(self) -> None:
        super().__init__()
        self.cog = None
        self.engine = None
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
            
        try:
            self.engine = ModuleRegistry.get_module("text_generation_engine", auto_discover=True, wait_timeout=1.0)
        except Exception:
            self.engine = None

    @property
    def metadata(self) -> ModuleMetadata:
        return ModuleMetadata(
            name="synthesis_agent",
            version="1.0.1",
            description="Generates answers from ranked documents using neural grounding",
            # Keep `process_synthesis` as a compatibility alias (older pipeline modules may call it).
            operations=["synthesize", "process_synthesis", "status"],
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

        if operation not in {"synthesize", "process_synthesis"}:
            return {"success": False, "error": f"Unknown operation: {operation}"}

        # Lazy load modules only when execute is called
        self._ensure_modules()

        query: str = params.get("query", "") or params.get("input", "")
        documents: List[Dict[str, Any]] = params.get("documents") or []
        context = self._build_context(documents)

        # Prefer the raw engine to avoid recursion if called FROM CognitiveGenerator
        if self.engine:
            try:
                prompt = (
                    f"Instructions: Synthesize a detailed answer to the question using the context provided.\n"
                    f"Question: {query}\n"
                    f"Context:\n{context}\n"
                    f"Synthesis:"
                )
                result = self.engine.execute(
                    "generate_with_neural",
                    {
                        "prompt": prompt,
                        "temperature": 0.7,
                        "max_length": 1024,
                    },
                )
                text = result.get("text") or ""
                if text:
                    return {
                        "success": True, 
                        "synthesis": text, 
                        "answer": text, 
                        "documents": documents,
                        "metadata": {"method": "neural_engine"}
                    }
            except Exception as e:
                logger.debug(f"Engine synthesis failed: {e}")

        if self.cog:
            try:
                result = self.cog.execute(
                    "generate_response",
                    {
                        "input": query,
                        "context": context,
                        "persona": params.get("persona", "mavaia"),
                    },
                )
                text = result.get("response") or result.get("result") or ""
                if isinstance(text, dict):
                    text = text.get("response", "") or ""
                return {
                    "success": True, 
                    "synthesis": text, 
                    "answer": text, 
                    "documents": documents,
                    "metadata": {"method": "cognitive_generator"}
                }
            except Exception:
                pass

        answer = self._fallback_synthesis(query, documents)
        return {
            "success": True, 
            "synthesis": answer, 
            "answer": answer, 
            "documents": documents,
            "metadata": {"method": "fallback"}
        }

    def _get_status(self) -> Dict[str, Any]:
        """Return module status"""
        self._ensure_modules()
        return {
            "success": True,
            "status": "active",
            "version": self.metadata.version,
            "cognitive_generator_available": self.cog is not None,
            "neural_engine_available": self.engine is not None
        }

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
