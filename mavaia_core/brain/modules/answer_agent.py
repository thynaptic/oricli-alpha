"""
Answer Agent Module - final answer formatting and source attribution.
"""

from __future__ import annotations

from typing import Any, Dict, List

from mavaia_core.brain.base_module import BaseBrainModule, ModuleMetadata


class AnswerAgentModule(BaseBrainModule):
    """Formats answers and appends sources."""

    def __init__(self) -> None:
        self.cog = None
        self._modules_ensured = False

    def _ensure_modules(self) -> None:
        """Lazy load modules only when needed"""
        if self._modules_ensured:
            return
        self._modules_ensured = True
        try:
            from mavaia_core.brain.registry import ModuleRegistry
            self.cog = ModuleRegistry.get_module("cognitive_generator", auto_discover=True, wait_timeout=1.0)
        except Exception:
            self.cog = None

    @property
    def metadata(self) -> ModuleMetadata:
        return ModuleMetadata(
            name="answer_agent",
            version="1.0.0",
            description="Formats answers with citations and validation hints",
            operations=["format_answer"],
            dependencies=[],
            model_required=False,
        )

    def execute(self, operation: str, params: Dict[str, Any]) -> Dict[str, Any]:
        if operation != "format_answer":
            raise ValueError(f"Unsupported operation: {operation}")

        # Lazy load modules only when execute is called
        self._ensure_modules()

        raw_answer: str = params.get("answer", "") or ""
        query: str = params.get("query", "") or ""
        documents: List[Dict[str, Any]] = params.get("documents") or []

        if not raw_answer:
            return {"success": False, "error": "No answer provided"}

        if self.cog:
            prompt = self._build_prompt(query, raw_answer, documents)
            try:
                result = self.cog.execute(
                    "generate_response",
                    {"input": prompt, "context": "You are a formatting assistant.", "persona": "mavaia"},
                )
                formatted = result.get("response") or result.get("result") or raw_answer
                if isinstance(formatted, dict):
                    formatted = formatted.get("response", raw_answer)
                return {"success": True, "answer": formatted, "documents": documents}
            except Exception:
                pass

        return {"success": True, "answer": self._fallback(raw_answer, documents), "documents": documents}

    def _build_prompt(self, query: str, answer: str, documents: List[Dict[str, Any]]) -> str:
        prompt = f"Query: {query}\n\nAnswer to format:\n{answer}\n\n"
        if documents:
            prompt += "Sources:\n"
            for idx, doc in enumerate(documents[:5], start=1):
                title = doc.get("title", "Untitled")
                url = doc.get("url")
                prompt += f"{idx}. {title}"
                if url:
                    prompt += f" ({url})"
                prompt += "\n"
        prompt += "\nFormat clearly, cite sources, and flag uncertainty."
        return prompt

    def _fallback(self, answer: str, documents: List[Dict[str, Any]]) -> str:
        if not documents:
            return answer
        lines = [answer, "\nSources:"]
        for idx, doc in enumerate(documents[:5], start=1):
            title = doc.get("title", "Untitled")
            url = doc.get("url")
            ref = f"{idx}. {title}"
            if url:
                ref += f" ({url})"
            lines.append(ref)
        return "\n".join(lines)


__all__ = ["AnswerAgentModule"]

