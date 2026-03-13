from __future__ import annotations
"""Validator module.

Delegates to `cognitive_generator`'s internal verification and response-quality
checks so the rest of the system can call them as first-class module operations.
"""

from typing import Any, Dict
import sys

from oricli_core.brain.base_module import BaseBrainModule, ModuleMetadata
from oricli_core.exceptions import InvalidParameterError


class ValidatorModule(BaseBrainModule):
    """Validates response quality and correctness."""

    def __init__(self):
        self._module_registry = None

    @property
    def metadata(self) -> ModuleMetadata:
        return ModuleMetadata(
            name="validator",
            version="1.0.0",
            description="Validates response quality and correctness",
            operations=[
                "validate_response",
                "verify_web_content",
                "verify_output_matches_intent",
                "validate_and_filter_instructions",
                "validate_response_quality",
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
                print("[ValidatorModule] ModuleRegistry not available", file=sys.stderr)
                self._module_registry = None

    def _get_cognitive_generator(self):
        self._init_module_registry()
        if not self._module_registry:
            return None
        return self._module_registry.get_module("cognitive_generator")

    @staticmethod
    def _persona_from_params(params: Dict[str, Any]) -> str:
        persona = params.get("persona") or params.get("base_personality")
        if persona:
            return str(persona)
        voice_context = params.get("voice_context")
        if isinstance(voice_context, dict) and voice_context.get("base_personality"):
            return str(voice_context.get("base_personality"))
        return "oricli"

    def execute(self, operation: str, params: Dict[str, Any]) -> Dict[str, Any]:
        cg = self._get_cognitive_generator()
        if not cg:
            return {"success": False, "error": "cognitive_generator module unavailable"}

        if operation == "validate_response":
            text = params.get("text") or params.get("output") or params.get("response") or ""
            return {"success": True, "is_valid": bool(cg._validate_response(str(text)))}

        if operation == "verify_web_content":
            content = params.get("content") or params.get("text") or ""
            source_urls = params.get("source_urls") or params.get("urls") or []
            query = params.get("query") or params.get("input") or ""
            return {
                "success": True,
                "verification": cg._verify_web_content(
                    str(content),
                    source_urls if isinstance(source_urls, list) else [],
                    str(query),
                ),
            }

        if operation == "verify_output_matches_intent":
            output = params.get("output") or params.get("text") or params.get("response") or ""
            intent_info = params.get("intent_info") or {}
            input_text = params.get("input") or params.get("query") or ""
            return {
                "success": True,
                "verification": cg._verify_output_matches_intent(str(output), intent_info, str(input_text)),
            }

        if operation == "validate_and_filter_instructions":
            text = params.get("text") or params.get("output") or params.get("response") or ""
            input_text = params.get("input") or params.get("query") or ""
            context = params.get("context") or ""
            persona = self._persona_from_params(params)
            filtered = cg._validate_and_filter_instructions(str(text), str(input_text), persona, str(context))
            return {"success": True, "text": filtered}

        if operation == "validate_response_quality":
            text = params.get("text") or params.get("output") or params.get("response") or ""
            input_text = params.get("input") or params.get("query") or ""
            context = params.get("context") or ""
            persona = self._persona_from_params(params)
            return {
                "success": True,
                "quality": cg._validate_response_quality(str(text), str(input_text), persona, str(context)),
            }

        raise InvalidParameterError(
            parameter="operation",
            value=str(operation),
            reason="Unknown operation for validator",
        )
