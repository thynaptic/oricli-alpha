from __future__ import annotations
"""Neural text generator core.

Wraps `neural_text_generator.generate_text` behind a stable interface.
"""

from typing import Any, Dict
import sys

from mavaia_core.brain.base_module import BaseBrainModule, ModuleMetadata
from mavaia_core.exceptions import InvalidParameterError


class NeuralTextGeneratorCoreModule(BaseBrainModule):
    """Core text generation using trained neural models."""

    def __init__(self):
        self._module_registry = None

    @property
    def metadata(self) -> ModuleMetadata:
        return ModuleMetadata(
            name="neural_text_generator_core",
            version="1.0.0",
            description="Core text generation using trained neural models",
            operations=[
                "generate_text",
                "generate_with_character_model",
                "generate_with_word_model",
                "generate_with_transformer",
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
                from mavaia_core.brain.registry import ModuleRegistry

                self._module_registry = ModuleRegistry
            except ImportError:
                print("[NeuralTextGeneratorCoreModule] ModuleRegistry not available", file=sys.stderr)
                self._module_registry = None

    def _get_neural_text_generator(self):
        self._init_module_registry()
        if not self._module_registry:
            return None
        return self._module_registry.get_module("neural_text_generator")

    def _generate(self, ntg, params: Dict[str, Any], model_type: str | None = None) -> Dict[str, Any]:
        prompt = params.get("prompt")
        if not prompt:
            prompt = params.get("input") or params.get("text") or params.get("query") or ""
        gen_params = {**params, "prompt": str(prompt)}
        if model_type:
            gen_params["model_type"] = model_type
        return ntg.execute("generate_text", gen_params)

    def execute(self, operation: str, params: Dict[str, Any]) -> Dict[str, Any]:
        ntg = self._get_neural_text_generator()
        if not ntg:
            return {"success": False, "error": "neural_text_generator module unavailable"}

        if operation == "generate_text":
            return self._generate(ntg, params)

        if operation == "generate_with_character_model":
            return self._generate(ntg, params, model_type="character")

        if operation == "generate_with_word_model":
            return self._generate(ntg, params, model_type="word")

        if operation == "generate_with_transformer":
            return self._generate(ntg, params, model_type="transformer")

        raise InvalidParameterError(
            parameter="operation",
            value=str(operation),
            reason="Unknown operation for neural_text_generator_core",
        )
