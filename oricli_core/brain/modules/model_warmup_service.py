from __future__ import annotations
"""
Model Warmup Service - Service to warm up all AI models before OricliAlpha becomes available
Converted from Swift ModelWarmupService.swift
"""

from typing import Any, Dict, List, Optional, Set
import time
import logging

from oricli_core.brain.base_module import BaseBrainModule, ModuleMetadata
from oricli_core.brain.registry import ModuleRegistry
from oricli_core.exceptions import InvalidParameterError

logger = logging.getLogger(__name__)


class ModelWarmupServiceModule(BaseBrainModule):
    """Service to warm up all AI models before OricliAlpha becomes available"""

    def __init__(self):
        super().__init__()
        self.cognitive_generator = None
        self._modules_loaded = False
        self._is_warming_up = False
        self._is_ready = False
        self._warmup_progress = ""
        self._ready_models: Set[str] = set()
        self._failed_models: Set[str] = set()
        self._total_models = 0
        self._completed_models = 0
        self._warmup_cache_timeout = 24 * 60 * 60  # 24 hours

    @property
    def metadata(self) -> ModuleMetadata:
        return ModuleMetadata(
            name="model_warmup_service",
            version="1.0.0",
            description="Service to warm up all AI models before OricliAlpha becomes available",
            operations=[
                "warmup_models",
                "preload_models",
                "check_readiness",
            ],
            dependencies=[],
            model_required=False,
        )

    def initialize(self) -> bool:
        """Initialize the module"""
        return True

    def _ensure_modules_loaded(self):
        """Lazy load dependent modules"""
        if self._modules_loaded:
            return

        try:
            self.cognitive_generator = ModuleRegistry.get_module("cognitive_generator")

            self._modules_loaded = True
        except Exception as e:
            # Modules not available - will use fallback methods
            logger.debug(
                "Failed to load model_warmup_service dependencies",
                exc_info=True,
                extra={"module_name": "model_warmup_service", "error_type": type(e).__name__},
            )

    def execute(self, operation: str, params: Dict[str, Any]) -> Dict[str, Any]:
        """Execute an operation"""
        self._ensure_modules_loaded()

        if operation == "warmup_models":
            return self._warmup_models(params)
        elif operation == "preload_models":
            return self._preload_models(params)
        elif operation == "check_readiness":
            return self._check_readiness(params)
        else:
            raise InvalidParameterError(
                parameter="operation",
                value=operation,
                reason="Unknown operation for model_warmup_service",
            )

    def _warmup_models(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """Warmup all models"""
        if self._is_warming_up or self._is_ready:
            return {
                "success": True,
                "is_ready": self._is_ready,
                "ready_models": list(self._ready_models),
            }

        self._is_warming_up = True
        self._is_ready = False
        self._ready_models.clear()
        self._failed_models.clear()
        self._completed_models = 0

        # Common modules to warmup
        common_modules = [
            "linguistic_priors",
            "social_priors",
            "emotional_ontology",
            "conversational_memory",
            "pattern_library",
        ]

        self._total_models = len(common_modules) + 1  # +1 for cognitive_generator

        # Warmup common modules
        for module_name in common_modules:
            try:
                self._warmup_local_model(module_name)
                self._ready_models.add(module_name)
                self._completed_models += 1
            except Exception as e:
                logger.debug(
                    "Model warmup failed",
                    exc_info=True,
                    extra={
                        "module_name": "model_warmup_service",
                        "target_module": str(module_name),
                        "error_type": type(e).__name__,
                    },
                )
                self._failed_models.add(module_name)
                self._completed_models += 1

        # Warmup cognitive generator
        if self.cognitive_generator:
            try:
                # Simple ping to warmup
                self.cognitive_generator.execute("generate_response", {
                    "input": "test",
                    "context": "warmup",
                })
                self._ready_models.add("cognitive_generator")
                self._completed_models += 1
            except Exception as e:
                logger.debug(
                    "cognitive_generator warmup failed",
                    exc_info=True,
                    extra={"module_name": "model_warmup_service", "error_type": type(e).__name__},
                )
                self._failed_models.add("cognitive_generator")
                self._completed_models += 1

        self._is_warming_up = False
        self._is_ready = len(self._ready_models) > 0

        return {
            "success": True,
            "is_ready": self._is_ready,
            "ready_models": list(self._ready_models),
            "failed_models": list(self._failed_models),
            "total_models": self._total_models,
            "completed_models": self._completed_models,
        }

    def _preload_models(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """Preload models (alias for warmup_models)"""
        return self._warmup_models(params)

    def _check_readiness(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """Check if models are ready"""
        return {
            "success": True,
            "is_ready": self._is_ready,
            "is_warming_up": self._is_warming_up,
            "ready_models": list(self._ready_models),
            "failed_models": list(self._failed_models),
        }

    def _warmup_local_model(self, model: str) -> None:
        """Warmup a local model"""
        try:
            module = ModuleRegistry.get_module(model)
            if module:
                # Simple ping to initialize
                module.initialize()
        except Exception as e:
            logger.debug(
                "Local module warmup failed",
                exc_info=True,
                extra={
                    "module_name": "model_warmup_service",
                    "target_module": str(model),
                    "error_type": type(e).__name__,
                },
            )

