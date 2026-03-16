from __future__ import annotations
"""
Local Model Service - Provides local model management and health checks
Replaces external API calls with local Python service that uses cognitive generator
"""

from typing import List, Dict, Any, Optional
import logging

from oricli_core.brain.base_module import BaseBrainModule, ModuleMetadata
from oricli_core.brain.registry import ModuleRegistry
from oricli_core.exceptions import InvalidParameterError

logger = logging.getLogger(__name__)


class LocalModelService(BaseBrainModule):
    """Local model service that replaces external API calls"""

    def __init__(self):
        super().__init__()
        self.cognitive_generator = None
        self._modules_loaded = False

    @property
    def metadata(self) -> ModuleMetadata:
        return ModuleMetadata(
            name="local_model_service",
            version="1.0.0",
            description="Local model service that provides model listing, health checks, and warmup",
            operations=[
                "list_available_models",
                "check_model_health",
                "warmup_model",
                "check_service_running",
                "generate_response",
            ],
            dependencies=[],
            model_required=False,
        )

    def initialize(self) -> bool:
        """Initialize the module - lazy load dependent modules"""
        return True

    def _ensure_modules_loaded(self):
        """Lazy load dependent modules"""
        if self._modules_loaded:
            return

        try:
            # Load cognitive generator for text generation
            try:
                self.cognitive_generator = ModuleRegistry.get_module(
                    "cognitive_generator"
                )
            except Exception as e:
                logger.debug(
                    "Failed to load cognitive_generator dependency",
                    exc_info=True,
                    extra={"module_name": "local_model_service", "error_type": type(e).__name__},
                )

            self._modules_loaded = True
        except Exception as e:
            # Modules not available - will use fallback methods
            logger.debug(
                "Failed to initialize local_model_service dependencies",
                exc_info=True,
                extra={"module_name": "local_model_service", "error_type": type(e).__name__},
            )

    def execute(self, operation: str, params: Dict[str, Any]) -> Dict[str, Any]:
        """Execute a local model service operation"""
        self._ensure_modules_loaded()

        if operation == "list_available_models":
            return self.list_available_models()
        elif operation == "check_model_health":
            model_name = params.get("model_name", "")
            return self.check_model_health(model_name)
        elif operation == "warmup_model":
            model_name = params.get("model_name", "")
            return self.warmup_model(model_name)
        elif operation == "check_service_running":
            return self.check_service_running()
        elif operation == "generate_response":
            return self.generate_response(
                model=params.get("model", ""),
                prompt=params.get("prompt", ""),
                context=params.get("context", ""),
            )
        else:
            raise InvalidParameterError(
                parameter="operation",
                value=operation,
                reason="Unknown operation for local_model_service",
            )

    def list_available_models(self) -> Dict[str, Any]:
        """List all locally available models"""
        # Cognitive generator doesn't use specific models - it's model-agnostic
        # Return empty list to indicate no model dependencies
        return {"success": True, "models": []}

    def check_model_health(self, model_name: str) -> Dict[str, Any]:
        """Check if the cognitive generator service is healthy and ready"""
        # Model name is ignored - we don't use specific models
        # Just check if cognitive generator is available

        # Check if cognitive generator is available
        if not self.cognitive_generator:
            return {
                "success": False,
                "healthy": False,
                "error": "Cognitive generator not available",
            }

        # Cognitive generator is available - service is healthy
        return {"success": True, "healthy": True}

    def warmup_model(self, model_name: str) -> Dict[str, Any]:
        """Warm up the cognitive generator service"""
        # Model name is ignored - we don't use specific models
        # Just warmup the cognitive generator

        # Check if cognitive generator is available
        if not self.cognitive_generator:
            return {"success": False, "error": "Cognitive generator not available"}

        # Perform a lightweight test generation to warm up the service
        try:
            # Use a simple test prompt
            test_result = self.cognitive_generator.execute(
                "generate_response",
                {
                    "input": "test",
                    "context": "This is a warmup test.",
                    "persona": "oricli",
                },
            )

            if test_result.get("success", False):
                return {"success": True, "ready": True}
            else:
                return {"success": False, "error": "Warmup test failed"}
        except Exception as e:
            return {"success": False, "error": f"Warmup failed: {str(e)}"}

    def check_service_running(self) -> Dict[str, Any]:
        """Check if the local model service is running"""
        # Check if cognitive generator is available
        if not self.cognitive_generator:
            return {
                "success": False,
                "running": False,
                "error": "Cognitive generator not available",
            }

        # Try to initialize cognitive generator
        try:
            if self.cognitive_generator.initialize():
                return {"success": True, "running": True}
            else:
                return {
                    "success": False,
                    "running": False,
                    "error": "Failed to initialize cognitive generator",
                }
        except Exception as e:
            return {
                "success": False,
                "running": False,
                "error": f"Service check failed: {str(e)}",
            }

    def generate_response(
        self, model: str, prompt: str, context: str = ""
    ) -> Dict[str, Any]:
        """Generate a response using the cognitive generator"""
        # Model parameter is ignored - cognitive generator doesn't use specific models

        if not self.cognitive_generator:
            return {
                "success": False,
                "text": "",
                "error": "Cognitive generator not available",
            }

        try:
            result = self.cognitive_generator.execute(
                "generate_response",
                {"input": prompt, "context": context, "persona": "oricli"},
            )

            if result.get("success", False):
                return {"success": True, "text": result.get("text", "")}
            else:
                return {
                    "success": False,
                    "text": "",
                    "error": result.get("error", "Generation failed"),
                }
        except Exception as e:
            return {
                "success": False,
                "text": "",
                "error": f"Generation error: {str(e)}",
            }
