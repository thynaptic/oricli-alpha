from __future__ import annotations
"""
Model Health Service - Service to verify models are actually online and communicating
Converted from Swift ModelHealthService.swift
"""

from typing import Any, Dict, List, Optional
import time
import logging

from oricli_core.brain.base_module import BaseBrainModule, ModuleMetadata
from oricli_core.brain.registry import ModuleRegistry
from oricli_core.exceptions import InvalidParameterError

logger = logging.getLogger(__name__)


class ModelHealthServiceModule(BaseBrainModule):
    """Service to verify models are actually online and communicating"""

    def __init__(self):
        super().__init__()
        self.cognitive_generator = None
        self.model_warmup = None
        self._modules_loaded = False
        self._model_health_status: Dict[str, Dict[str, Any]] = {}
        self._health_check_interval = 30.0  # 30 seconds
        self._verification_timeout = 10.0  # 10 seconds
        self._health_cache_ttl = 300.0  # 5 minutes
        self._max_consecutive_failures = 3

    @property
    def metadata(self) -> ModuleMetadata:
        return ModuleMetadata(
            name="model_health_service",
            version="1.0.0",
            description="Service to verify models are actually online and communicating",
            operations=[
                "check_health",
                "monitor_models",
                "get_health_status",
                "verify_model_communicating",
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
            self.model_warmup = ModuleRegistry.get_module("model_warmup_service")

            self._modules_loaded = True
        except Exception as e:
            # Modules not available - will use fallback methods
            logger.debug(
                "Failed to load model_health_service dependencies",
                exc_info=True,
                extra={"module_name": "model_health_service", "error_type": type(e).__name__},
            )

    def execute(self, operation: str, params: Dict[str, Any]) -> Dict[str, Any]:
        """Execute an operation"""
        self._ensure_modules_loaded()

        if operation == "check_health":
            return self._check_health(params)
        elif operation == "monitor_models":
            return self._monitor_models(params)
        elif operation == "get_health_status":
            return self._get_health_status(params)
        elif operation == "verify_model_communicating":
            return self._verify_model_communicating(params)
        else:
            raise InvalidParameterError(
                parameter="operation",
                value=operation,
                reason="Unknown operation for model_health_service",
            )

    def _check_health(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """Check if a model is currently healthy and online"""
        model = params.get("model", "default")
        if not isinstance(model, str) or not model.strip():
            raise InvalidParameterError(
                parameter="model",
                value=str(model),
                reason="model must be a non-empty string",
            )

        # Check cache first
        if model in self._model_health_status:
            status = self._model_health_status[model]
            last_checked = status.get("last_checked", 0)
            if time.time() - last_checked < self._health_cache_ttl:
                if status.get("is_online", False):
                    return {
                        "success": True,
                        "is_healthy": True,
                        "status": "online",
                    }

        # Verify model is communicating
        verified = self._verify_model_communicating({"model": model})

        # Update cache
        self._model_health_status[model] = {
            "is_online": verified.get("is_communicating", False),
            "last_checked": time.time(),
            "response_time": verified.get("response_time", 0.0),
        }

        return {
            "success": True,
            "is_healthy": verified.get("is_communicating", False),
            "status": "online" if verified.get("is_communicating", False) else "offline",
        }

    def _monitor_models(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """Monitor models (background monitoring)"""
        models = params.get("models", ["default"])
        if models is None:
            models = ["default"]
        if not isinstance(models, list) or any(not isinstance(m, str) for m in models):
            raise InvalidParameterError(
                parameter="models",
                value=str(type(models).__name__),
                reason="models must be a list of strings",
            )

        results = {}
        for model in models:
            health = self._check_health({"model": model})
            results[model] = health

        return {
            "success": True,
            "models": results,
        }

    def _get_health_status(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """Get current health status for a model"""
        model = params.get("model", "default")
        if not isinstance(model, str) or not model.strip():
            raise InvalidParameterError(
                parameter="model",
                value=str(model),
                reason="model must be a non-empty string",
            )

        status = self._model_health_status.get(model, {})
        return {
            "success": True,
            "status": status.get("is_online", False) and "online" or "offline",
            "last_checked": status.get("last_checked", 0),
            "response_time": status.get("response_time", 0.0),
            "consecutive_failures": status.get("consecutive_failures", 0),
        }

    def _verify_model_communicating(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """Verify model is actually communicating"""
        import time

        model = params.get("model", "default")
        if not isinstance(model, str) or not model.strip():
            raise InvalidParameterError(
                parameter="model",
                value=str(model),
                reason="model must be a non-empty string",
            )
        start_time = time.time()

        if not self.cognitive_generator:
            return {
                "success": False,
                "is_communicating": False,
                "response_time": 0.0,
            }

        try:
            # Simple test prompt
            result = self.cognitive_generator.execute("generate_response", {
                "input": "test",
                "context": "Health check",
            })

            response_time = time.time() - start_time

            return {
                "success": True,
                "is_communicating": True,
                "response_time": response_time,
            }
        except Exception as e:
            response_time = time.time() - start_time
            logger.debug(
                "Model communication check failed",
                exc_info=True,
                extra={
                    "module_name": "model_health_service",
                    "target_model": str(model),
                    "error_type": type(e).__name__,
                },
            )
            return {
                "success": False,
                "is_communicating": False,
                "response_time": response_time,
                "error": "Model communication check failed",
            }

