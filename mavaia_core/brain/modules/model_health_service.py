"""
Model Health Service - Service to verify models are actually online and communicating
Converted from Swift ModelHealthService.swift
"""

from typing import Any, Dict, List, Optional
import sys
import time
from pathlib import Path

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent))

from mavaia_core.brain.base_module import BaseBrainModule, ModuleMetadata


class ModelHealthServiceModule(BaseBrainModule):
    """Service to verify models are actually online and communicating"""

    def __init__(self):
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
            from module_registry import ModuleRegistry

            self.cognitive_generator = ModuleRegistry.get_module("cognitive_generator")
            self.model_warmup = ModuleRegistry.get_module("model_warmup_service")

            self._modules_loaded = True
        except Exception as e:
            # Modules not available - will use fallback methods
            pass

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
            raise ValueError(f"Unknown operation: {operation}")

    def _check_health(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """Check if a model is currently healthy and online"""
        model = params.get("model", "default")

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
            return {
                "success": False,
                "is_communicating": False,
                "response_time": response_time,
                "error": str(e),
            }

