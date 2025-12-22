"""
Cognitive Curriculum Testing Framework for Mavaia

A comprehensive testing framework that enables curriculum-based evaluation
of Mavaia's cognitive capabilities through progressive difficulty testing
and selective testing via interactive menu system.
"""

from mavaia_core.evaluation.curriculum.models import (
    TestConfiguration,
    OptionalConstraints,
    TestResult,
    ScoringRubric,
    MemoryContinuityMode,
    SafetyPosture,
    PassFailStatus,
)

__all__ = [
    "TestConfiguration",
    "OptionalConstraints",
    "TestResult",
    "ScoringRubric",
    "MemoryContinuityMode",
    "SafetyPosture",
    "PassFailStatus",
]

