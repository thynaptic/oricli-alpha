from __future__ import annotations
"""Context enricher module.

Delegates to `cognitive_generator` context enrichment helpers.
"""

from typing import Any, Dict
import sys

from oricli_core.brain.base_module import BaseBrainModule, ModuleMetadata
from oricli_core.exceptions import InvalidParameterError


class ContextEnricherModule(BaseBrainModule):
    """Enriches context with conversational components and consistency info."""

    def __init__(self):
        self._module_registry = None

    @property
    def metadata(self) -> ModuleMetadata:
        return ModuleMetadata(
            name="context_enricher",
            version="1.0.0",
            description="Enriches context with conversational components and consistency info",
            operations=[
                "enrich_context",
                "enrich_context_with_conversational_components",
                "extract_consistency_info",
            ],
            dependencies=[],
            model_required=False,
        )

    def initialize(self) -> bool:
        self._init_module_registry()
        return True

    def _init_module_registry(self) -> None:
        if self._module_registry is None:
            try:
                from oricli_core.brain.registry import ModuleRegistry

                self._module_registry = ModuleRegistry
            except ImportError:
                print("[ContextEnricherModule] ModuleRegistry not available", file=sys.stderr)
                self._module_registry = None

    def _get_cognitive_generator(self):
        self._init_module_registry()
        if not self._module_registry:
            return None
        return self._module_registry.get_module("cognitive_generator")

    def execute(self, operation: str, params: Dict[str, Any]) -> Dict[str, Any]:
        cg = self._get_cognitive_generator()
        if not cg:
            return {"success": False, "error": "cognitive_generator module unavailable"}

        if operation == "enrich_context":
            input_text = params.get("input") or params.get("query") or params.get("text") or ""
            context = params.get("context") or ""
            return {"success": True, "context": cg._enrich_context(str(input_text), str(context))}

        if operation == "enrich_context_with_conversational_components":
            input_text = params.get("input") or params.get("query") or params.get("text") or ""
            context = params.get("context") or ""
            voice_context = params.get("voice_context") or {}
            enriched = cg._enrich_context_with_conversational_components(
                str(input_text),
                str(context),
                voice_context if isinstance(voice_context, dict) else {},
            )
            return {"success": True, "context": enriched}

        if operation == "extract_consistency_info":
            history = params.get("history") or params.get("conversation_history")
            if not isinstance(history, list):
                history = []
            return {"success": True, "consistency": cg._extract_consistency_info(history)}

        raise InvalidParameterError(
            parameter="operation",
            value=str(operation),
            reason="Unknown operation for context_enricher",
        )
