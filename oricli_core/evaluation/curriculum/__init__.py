from __future__ import annotations
"""
Cognitive Curriculum Testing Framework for Oricli-Alpha

A comprehensive testing framework that enables curriculum-based evaluation
of Oricli-Alpha's cognitive capabilities through progressive difficulty testing
and selective testing via interactive menu system.
"""

from oricli_core.evaluation.curriculum.models import (
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

