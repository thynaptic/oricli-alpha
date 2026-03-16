from __future__ import annotations
"""Neural text trainer module.

Thin wrapper around `neural_text_generator.train_model` to expose named training
operations.
"""

from typing import Any, Dict
import sys

from oricli_core.brain.base_module import BaseBrainModule, ModuleMetadata
from oricli_core.exceptions import InvalidParameterError


class NeuralTextTrainerModule(BaseBrainModule):
    """Trains neural text generation models (character, word, transformer)."""

    def __init__(self):
        self._module_registry = None

    @property
    def metadata(self) -> ModuleMetadata:
        return ModuleMetadata(
            name="neural_text_trainer",
            version="1.0.0",
            description="Trains neural text generation models (character, word, transformer)",
            operations=[
                "train_model",
                "train_character_model",
                "train_word_model",
                "train_transformer_model",
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
                print("[NeuralTextTrainerModule] ModuleRegistry not available", file=sys.stderr)
                self._module_registry = None

    def _get_neural_text_generator(self):
        self._init_module_registry()
        if not self._module_registry:
            return None
        return self._module_registry.get_module("neural_text_generator")

    def execute(self, operation: str, params: Dict[str, Any]) -> Dict[str, Any]:
        ntg = self._get_neural_text_generator()
        if not ntg:
            return {"success": False, "error": "neural_text_generator module unavailable"}

        try:
            if operation == "train_model":
                return ntg.execute("train_model", params)

            if operation == "train_character_model":
                return ntg.execute("train_model", {**params, "model_type": "character"})

            if operation == "train_word_model":
                return ntg.execute("train_model", {**params, "model_type": "word"})

            if operation == "train_transformer_model":
                return ntg.execute("train_model", {**params, "model_type": "transformer"})
        except KeyboardInterrupt:
            model_type = params.get("model_type", "both")
            snapshot_result = {"success": False, "error": "Snapshot not attempted"}
            try:
                snapshot_result = ntg.execute("save_model", {"model_type": model_type})
            except Exception as e:
                snapshot_result = {"success": False, "error": str(e)}

            return {
                "success": False,
                "error": "Training interrupted by user",
                "interrupted": True,
                "snapshot": snapshot_result,
            }

        raise InvalidParameterError(
            parameter="operation",
            value=str(operation),
            reason="Unknown operation for neural_text_trainer",
        )
