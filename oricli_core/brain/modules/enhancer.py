from __future__ import annotations
"""Enhancer module.

Delegates to `cognitive_generator` response enhancement utilities.
"""

from typing import Any, Dict
import sys

from oricli_core.brain.base_module import BaseBrainModule, ModuleMetadata
from oricli_core.exceptions import InvalidParameterError


class EnhancerModule(BaseBrainModule):
    """Enhances responses with human-like qualities and personality."""

    def __init__(self):
        self._module_registry = None

    @property
    def metadata(self) -> ModuleMetadata:
        return ModuleMetadata(
            name="enhancer",
            version="1.0.0",
            description="Enhances responses with human-like qualities and personality",
            operations=[
                "apply_human_like_enhancements",
                "generate_personality_aware_fallback",
                "expand_response_for_detailed_mode",
                "enhance_for_consistency",
                "generate_conversational_response",
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
                print("[EnhancerModule] ModuleRegistry not available", file=sys.stderr)
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

        if operation == "apply_human_like_enhancements":
            text = params.get("text") or params.get("response") or ""
            input_text = params.get("input") or params.get("query") or ""
            context = params.get("context") or ""
            voice_context = params.get("voice_context") or {}
            social_context = params.get("social_context")
            confidence = float(params.get("confidence", 0.5) or 0.5)
            enhanced = cg._apply_human_like_enhancements(
                str(text),
                str(input_text),
                str(context),
                voice_context if isinstance(voice_context, dict) else {},
                social_context if isinstance(social_context, dict) else None,
                confidence,
            )
            return {"success": True, "text": enhanced}

        if operation == "generate_personality_aware_fallback":
            input_text = params.get("input") or params.get("query") or ""
            context = params.get("context") or ""
            persona = self._persona_from_params(params)
            return {"success": True, "text": cg._generate_personality_aware_fallback(str(input_text), persona, str(context))}

        if operation == "expand_response_for_detailed_mode":
            base_response = params.get("base_response") or params.get("text") or params.get("response") or ""
            input_text = params.get("input") or params.get("query") or ""
            thoughts = params.get("thoughts") or []
            context = params.get("context") or ""
            voice_context = params.get("voice_context") or {}
            expanded = cg._expand_response_for_detailed_mode(
                str(base_response),
                str(input_text),
                thoughts if isinstance(thoughts, list) else [],
                str(context),
                voice_context if isinstance(voice_context, dict) else {},
            )
            return {"success": True, "text": expanded}

        if operation == "enhance_for_consistency":
            response = params.get("response") or params.get("text") or ""
            persona = self._persona_from_params(params)
            previous_numbers = params.get("previous_numbers") or params.get("numbers") or []
            previous_topics = params.get("previous_topics") or params.get("topics") or []
            previous_personality_markers = params.get("previous_personality_markers") or params.get("personality_markers") or []
            input_text = params.get("input") or params.get("query") or ""
            got_mentioned = bool(params.get("got_mentioned", False))
            enhanced = cg._enhance_for_consistency(
                str(response),
                persona,
                previous_numbers if isinstance(previous_numbers, list) else [],
                previous_topics if isinstance(previous_topics, list) else [],
                previous_personality_markers if isinstance(previous_personality_markers, list) else [],
                str(input_text),
                got_mentioned,
            )
            return {"success": True, "text": enhanced}

        if operation == "generate_conversational_response":
            input_text = params.get("input") or params.get("query") or ""
            voice_context = params.get("voice_context") or {}
            context = params.get("context") or ""
            conversation_history = params.get("conversation_history")
            selected_thoughts = params.get("selected_thoughts")
            max_tokens = params.get("max_tokens")
            text = cg._generate_conversational_response(
                str(input_text),
                voice_context if isinstance(voice_context, dict) else {},
                str(context),
                conversation_history if isinstance(conversation_history, list) else None,
                selected_thoughts if isinstance(selected_thoughts, list) else None,
                int(max_tokens) if max_tokens is not None else None,
            )
            return {"success": True, "text": text}

        raise InvalidParameterError(
            parameter="operation",
            value=str(operation),
            reason="Unknown operation for enhancer",
        )
