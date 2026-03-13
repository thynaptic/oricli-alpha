from __future__ import annotations
"""
Test Categories

Different types of tests for comprehensive evaluation:
- Module tests: Test individual module operations
- API tests: Test HTTP API endpoints
- Client tests: Test Python client interface
- System tests: Test core system components
- Reasoning tests: Test reasoning quality
- Safety tests: Test safety and edge cases
"""

# Imports are lazy to avoid triggering module discovery on import
# Import these classes only when actually needed

__all__ = [
    "ModuleTestRunner",
    "APITestRunner",
    "ClientTestRunner",
    "SystemTestRunner",
    "ReasoningTestRunner",
    "SafetyTestRunner",
    "LiveBenchTestRunner",
]

# Cache for imported classes
_imported_classes = {}

def __getattr__(name: str):
    """Lazy import of test executor classes"""
    if name not in __all__:
        raise AttributeError(f"module '{__name__}' has no attribute '{name}'")
    
    if name not in _imported_classes:
        if name == "ModuleTestRunner":
            from oricli_core.evaluation.categories.module_tests import ModuleTestRunner
            _imported_classes[name] = ModuleTestRunner
        elif name == "APITestRunner":
            from oricli_core.evaluation.categories.api_tests import APITestRunner
            _imported_classes[name] = APITestRunner
        elif name == "ClientTestRunner":
            from oricli_core.evaluation.categories.client_tests import ClientTestRunner
            _imported_classes[name] = ClientTestRunner
        elif name == "SystemTestRunner":
            from oricli_core.evaluation.categories.system_tests import SystemTestRunner
            _imported_classes[name] = SystemTestRunner
        elif name == "ReasoningTestRunner":
            from oricli_core.evaluation.categories.reasoning_tests import ReasoningTestRunner
            _imported_classes[name] = ReasoningTestRunner
        elif name == "SafetyTestRunner":
            from oricli_core.evaluation.categories.safety_tests import SafetyTestRunner
            _imported_classes[name] = SafetyTestRunner
        elif name == "LiveBenchTestRunner":
            from oricli_core.evaluation.categories.livebench_tests import LiveBenchTestRunner
            _imported_classes[name] = LiveBenchTestRunner
    
    return _imported_classes[name]

