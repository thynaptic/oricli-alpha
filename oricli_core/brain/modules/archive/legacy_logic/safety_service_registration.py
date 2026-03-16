from __future__ import annotations
"""
Safety Service Registration
Auto-registration service for all safety services
Converted from Swift SafetyServiceRegistration.swift
"""

from typing import Any, Dict
import logging

from oricli_core.brain.base_module import BaseBrainModule, ModuleMetadata
from oricli_core.brain.registry import ModuleRegistry
from oricli_core.exceptions import InvalidParameterError

logger = logging.getLogger(__name__)


class SafetyServiceRegistrationModule(BaseBrainModule):
    """Auto-registration service for all safety services"""

    def __init__(self):
        super().__init__()
        self.safety_framework = None
        self.is_registered = False
        self._modules_loaded = False

    @property
    def metadata(self) -> ModuleMetadata:
        return ModuleMetadata(
            name="safety_service_registration",
            version="1.0.0",
            description="Auto-registration service for all safety services",
            operations=[
                "register_all_safety_services",
                "register_safety_service",
                "get_safety_service",
                "reset",
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
            self.safety_framework = ModuleRegistry.get_module("safety_framework")

            self._modules_loaded = True
        except Exception as e:
            logger.debug(
                "Failed to load safety_framework for safety_service_registration",
                exc_info=True,
                extra={"module_name": "safety_service_registration", "error_type": type(e).__name__},
            )

    def execute(self, operation: str, params: Dict[str, Any]) -> Dict[str, Any]:
        """Execute an operation"""
        self._ensure_modules_loaded()

        if operation == "register_all_safety_services":
            return self._register_all_safety_services()
        elif operation == "register_safety_service":
            return self._register_safety_service(params)
        elif operation == "get_safety_service":
            return self._get_safety_service(params)
        elif operation == "reset":
            return self._reset()
        else:
            raise InvalidParameterError(
                parameter="operation",
                value=operation,
                reason="Unknown operation for safety_service_registration",
            )

    def _register_all_safety_services(self) -> Dict[str, Any]:
        """Register all built-in safety services"""
        if self.is_registered:
            return {
                "success": True,
                "result": {"message": "Safety services already registered"},
            }

        if not self.safety_framework:
            return {
                "success": False,
                "error": "Safety framework not available",
            }

        # Register services in priority order
        services_to_register = [
            "prompt_injection_safety",  # MUST be first
            "professional_advice_safety",
            "advanced_threat_safety",
            "self_harm_safety",
            "mental_health_safety_service",
            "step_safety_filter",  # Always runs last (fail-safe)
        ]

        registered_count = 0
        failed_services = []
        for service_name in services_to_register:
            try:
                result = self.safety_framework.execute(
                    "register_service",
                    {"service_name": service_name},
                )
                if result.get("success"):
                    registered_count += 1
                else:
                    failed_services.append(service_name)
            except Exception as e:
                failed_services.append(service_name)
                logger.debug(
                    "Error registering safety service",
                    exc_info=True,
                    extra={
                        "module_name": "safety_service_registration",
                        "service_name": service_name,
                        "error_type": type(e).__name__,
                    },
                )

        self.is_registered = True

        # Mark registration as complete
        try:
            self.safety_framework.execute("mark_registration_complete", {})
        except Exception:
            pass

        return {
            "success": True,
            "result": {
                "registered_count": registered_count,
                "services": services_to_register,
                "failed_services": failed_services,
            },
        }

    def _register_safety_service(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """Register a specific safety service"""
        service_name = params.get("service_name")

        if not service_name:
            return {
                "success": False,
                "error": "Service name is required",
            }

        if not self.safety_framework:
            return {
                "success": False,
                "error": "Safety framework not available",
            }

        result = self.safety_framework.execute(
            "register_service",
            {"service_name": service_name}
        )

        return result

    def _get_safety_service(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """Get a registered safety service"""
        service_name = params.get("service_name")

        if not service_name:
            return {
                "success": False,
                "error": "Service name is required",
            }

        if not self.safety_framework:
            return {
                "success": False,
                "error": "Safety framework not available",
            }

        result = self.safety_framework.execute(
            "get_service",
            {"service_name": service_name}
        )

        return result

    def _reset(self) -> Dict[str, Any]:
        """Reset registration state (for testing)"""
        self.is_registered = False
        return {
            "success": True,
            "result": {"message": "Registration state reset"},
        }

