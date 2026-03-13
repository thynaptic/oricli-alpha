from __future__ import annotations
"""
OricliAlpha Core Evaluation Framework

MMLU-style test suite for comprehensive evaluation of all brain modules
and system components.
"""

# Lazy imports to avoid import-time execution and module discovery
# Import these classes only when actually needed

__all__ = [
    "TestRunner",
    "TestReporter",
    "TestResults",
    "TestDataManager",
]

def __getattr__(name: str):
    """Lazy import of evaluation classes"""
    if name == "TestRunner":
        from oricli_core.evaluation.test_runner import TestRunner
        return TestRunner
    elif name == "TestReporter":
        from oricli_core.evaluation.test_reporter import TestReporter
        return TestReporter
    elif name == "TestResults":
        from oricli_core.evaluation.test_results import TestResults
        return TestResults
    elif name == "TestDataManager":
        from oricli_core.evaluation.test_data_manager import TestDataManager
        return TestDataManager
    raise AttributeError(f"module '{__name__}' has no attribute '{name}'")

