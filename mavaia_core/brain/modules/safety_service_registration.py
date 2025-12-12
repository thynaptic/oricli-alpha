"""
Safety Service Registration
Auto-registration service for all safety services
Converted from Swift SafetyServiceRegistration.swift
"""

from typing import Any, Dict
import sys
from pathlib import Path

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent))

from mavaia_core.brain.base_module import BaseBrainModule, ModuleMetadata


class SafetyServiceRegistrationModule(BaseBrainModule):
    """Auto-registration service for all safety services"""

    def __init__(self):
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
            from module_registry import ModuleRegistry

            self.safety_framework = ModuleRegistry.get_module("safety_framework")

            self._modules_loaded = True
        except Exception as e:
            print(f"Error loading modules: {e}")

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
            raise ValueError(f"Unknown operation: {operation}")

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
            "mental_health_safety",
            "default_deny_safety",  # Always runs last (fail-safe)
        ]

        registered_count = 0
        for service_name in services_to_register:
            try:
                result = self.safety_framework.execute(
                    "register_service",
                    {"service_name": service_name}
                )
                if result.get("success"):
                    registered_count += 1
            except Exception as e:
                print(f"Error registering {service_name}: {e}")

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

