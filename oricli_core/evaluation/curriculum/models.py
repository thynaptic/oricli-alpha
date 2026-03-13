from __future__ import annotations
"""
Data Models for Cognitive Curriculum Testing Framework

Pydantic models for test configuration, results, and constraints.
"""

from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from pathlib import Path
from typing import Any, Dict, List, Optional, Union

from pydantic import BaseModel, Field, field_validator


class MemoryContinuityMode(str, Enum):
    """Memory continuity tracking modes"""
    OFF = "off"
    SHORT_TERM = "short_term"
    LONG_TERM_BOUNDED = "long_term_bounded"


class SafetyPosture(str, Enum):
    """Safety layer posture modes"""
    NORMAL = "normal"
    SUPPORTIVE = "supportive"
    INTERVENTION = "intervention"
    HIGH_RISK_OVERRIDE = "high_risk_override"


class PassFailStatus(str, Enum):
    """Test pass/fail status"""
    PASS = "pass"
    FAIL = "fail"
    PARTIAL = "partial"


class OptionalConstraints(BaseModel):
    """Optional constraints for test execution"""
    
    time_bound: Optional[float] = Field(
        None,
        description="Maximum execution time in seconds",
        ge=0.0
    )
    token_bound: Optional[int] = Field(
        None,
        description="Maximum token usage",
        ge=0
    )
    memory_continuity: MemoryContinuityMode = Field(
        default=MemoryContinuityMode.OFF,
        description="Memory continuity tracking mode"
    )
    safety_posture: SafetyPosture = Field(
        default=SafetyPosture.NORMAL,
        description="Safety layer posture"
    )
    tool_usage_allowed: bool = Field(
        default=True,
        description="Whether tool usage is allowed"
    )
    bias_probes: bool = Field(
        default=False,
        description="Enable bias probing tests"
    )
    breakdown_explanation_required: bool = Field(
        default=False,
        description="Require step-by-step breakdown explanation"
    )
    mcts_depth: Optional[int] = Field(
        None,
        description="Monte Carlo Thought Search depth limit",
        ge=1
    )
    
    class Config:
        use_enum_values = True


class TestConfiguration(BaseModel):
    """Configuration for a curriculum test"""
    
    level: str = Field(
        ...,
        description="Education level: k5, middle_school, high_school, undergrad, grad, phd"
    )
    subject: str = Field(
        ...,
        description="Subject domain: math, language, science, logic, etc."
    )
    skill_type: str = Field(
        ...,
        description="Skill type: foundational, applied, abstract_reasoning, etc."
    )
    difficulty_style: str = Field(
        ...,
        description="Difficulty style: standard, accelerated, honors, ap, olympiad, research"
    )
    constraints: OptionalConstraints = Field(
        default_factory=OptionalConstraints,
        description="Optional execution constraints"
    )
    test_id: Optional[str] = Field(
        None,
        description="Specific test ID to run (if None, runs all matching tests)"
    )
    
    @field_validator("level")
    @classmethod
    def validate_level(cls, v: str) -> str:
        """Validate education level"""
        valid_levels = ["k5", "middle_school", "high_school", "undergrad", "grad", "phd"]
        if v not in valid_levels:
            raise ValueError(f"Invalid level: {v}. Must be one of {valid_levels}")
        return v
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary"""
        return {
            "level": self.level,
            "subject": self.subject,
            "skill_type": self.skill_type,
            "difficulty_style": self.difficulty_style,
            "constraints": self.constraints.model_dump(),
            "test_id": self.test_id,
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "TestConfiguration":
        """Create from dictionary"""
        constraints_data = data.get("constraints", {})
        constraints = OptionalConstraints(**constraints_data)
        return cls(
            level=data["level"],
            subject=data["subject"],
            skill_type=data["skill_type"],
            difficulty_style=data["difficulty_style"],
            constraints=constraints,
            test_id=data.get("test_id"),
        )


class ScoreBreakdown(BaseModel):
    """Detailed score breakdown"""
    
    accuracy: float = Field(0.0, ge=0.0, le=1.0, description="Accuracy score (0-1)")
    reasoning_depth: float = Field(0.0, ge=0.0, le=1.0, description="Reasoning depth score (0-1)")
    verbosity: float = Field(0.0, ge=0.0, le=1.0, description="Verbosity score (0-1)")
    structure: float = Field(0.0, ge=0.0, le=1.0, description="Structure score (0-1)")
    hallucination_penalty: float = Field(0.0, ge=-1.0, le=0.0, description="Hallucination penalty")
    safety_penalty: float = Field(0.0, ge=-1.0, le=0.0, description="Safety violation penalty")
    memory_penalty: float = Field(0.0, ge=-1.0, le=0.0, description="Memory corruption penalty")
    base_score: float = Field(0.0, description="Base score before penalties")
    final_score: float = Field(0.0, ge=0.0, le=1.0, description="Final score after penalties")


class TestResult(BaseModel):
    """Result of a curriculum test execution"""
    
    test_id: str = Field(..., description="Unique test identifier")
    test_config: TestConfiguration = Field(..., description="Test configuration")
    score: Union[float, str] = Field(..., description="Overall score (numeric or categorical)")
    score_breakdown: ScoreBreakdown = Field(..., description="Detailed score breakdown")
    reasoning_trace: Dict[str, Any] = Field(
        default_factory=dict,
        description="Structured reasoning trace from CoT/ToT/MCTS"
    )
    cognitive_weakness_map: Dict[str, Any] = Field(
        default_factory=dict,
        description="Map of cognitive weaknesses (what failed + why)"
    )
    cognitive_strength_map: Dict[str, Any] = Field(
        default_factory=dict,
        description="Map of cognitive strengths (what succeeded + why)"
    )
    safety_posture_summary: Dict[str, Any] = Field(
        default_factory=dict,
        description="Summary of how safety layer influenced behavior"
    )
    suggested_next_test: Optional[TestConfiguration] = Field(
        None,
        description="Suggested next test configuration"
    )
    pass_fail_status: PassFailStatus = Field(
        default=PassFailStatus.FAIL,
        description="Pass/fail status"
    )
    execution_time: float = Field(0.0, ge=0.0, description="Execution time in seconds")
    timestamp: str = Field(
        default_factory=lambda: datetime.utcnow().isoformat(),
        description="Test execution timestamp"
    )
    error_message: Optional[str] = Field(
        None,
        description="Error message if test failed"
    )
    error_type: Optional[str] = Field(
        None,
        description="Type of error if test failed"
    )
    
    class Config:
        use_enum_values = True
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary"""
        result = {
            "test_id": self.test_id,
            "test_config": self.test_config.to_dict(),
            "score": self.score,
            "score_breakdown": self.score_breakdown.model_dump(),
            "reasoning_trace": self.reasoning_trace,
            "cognitive_weakness_map": self.cognitive_weakness_map,
            "cognitive_strength_map": self.cognitive_strength_map,
            "safety_posture_summary": self.safety_posture_summary,
            "pass_fail_status": self.pass_fail_status,
            "execution_time": self.execution_time,
            "timestamp": self.timestamp,
            "error_message": self.error_message,
            "error_type": self.error_type,
        }
        if self.suggested_next_test:
            result["suggested_next_test"] = self.suggested_next_test.to_dict()
        return result


class ScoringRubric(BaseModel):
    """Scoring rubric configuration"""
    
    accuracy_weight: float = Field(0.47, ge=0.0, le=1.0, description="Weight for accuracy score")  # ~40% normalized
    reasoning_depth_weight: float = Field(0.29, ge=0.0, le=1.0, description="Weight for reasoning depth")  # ~25% normalized
    verbosity_weight: float = Field(0.12, ge=0.0, le=1.0, description="Weight for verbosity score")  # ~10% normalized
    structure_weight: float = Field(0.12, ge=0.0, le=1.0, description="Weight for structure score")  # ~10% normalized
    pass_threshold: float = Field(0.7, ge=0.0, le=1.0, description="Minimum score for pass")
    partial_pass_threshold: float = Field(0.5, ge=0.0, le=1.0, description="Minimum score for partial pass")
    hallucination_penalty_per_instance: float = Field(
        -0.3,
        ge=-1.0,
        le=0.0,
        description="Penalty per hallucination instance"
    )
    safety_violation_penalty_per_instance: float = Field(
        -0.5,
        ge=-1.0,
        le=0.0,
        description="Penalty per safety violation"
    )
    memory_corruption_penalty_per_instance: float = Field(
        -0.2,
        ge=-1.0,
        le=0.0,
        description="Penalty per memory corruption"
    )
    
    def validate_weights(self) -> bool:
        """Validate that weights sum to approximately 1.0"""
        total = (
            self.accuracy_weight +
            self.reasoning_depth_weight +
            self.verbosity_weight +
            self.structure_weight
        )
        return abs(total - 1.0) < 0.01
    
    def compute_score(
        self,
        accuracy: float,
        reasoning_depth: float,
        verbosity: float,
        structure: float,
        hallucination_count: int = 0,
        safety_violation_count: int = 0,
        memory_corruption_count: int = 0,
    ) -> ScoreBreakdown:
        """Compute score breakdown from component scores"""
        # Validate weights
        if not self.validate_weights():
            raise ValueError("Weights must sum to 1.0")
        
        # Compute base score
        base_score = (
            accuracy * self.accuracy_weight +
            reasoning_depth * self.reasoning_depth_weight +
            verbosity * self.verbosity_weight +
            structure * self.structure_weight
        )
        
        # Compute penalties
        hallucination_penalty = min(
            hallucination_count * self.hallucination_penalty_per_instance,
            -1.0
        )
        safety_penalty = min(
            safety_violation_count * self.safety_violation_penalty_per_instance,
            -1.0
        )
        memory_penalty = min(
            memory_corruption_count * self.memory_corruption_penalty_per_instance,
            -1.0
        )
        
        # Compute final score
        final_score = max(0.0, min(1.0, base_score + hallucination_penalty + safety_penalty + memory_penalty))
        
        return ScoreBreakdown(
            accuracy=accuracy,
            reasoning_depth=reasoning_depth,
            verbosity=verbosity,
            structure=structure,
            hallucination_penalty=hallucination_penalty,
            safety_penalty=safety_penalty,
            memory_penalty=memory_penalty,
            base_score=base_score,
            final_score=final_score,
        )
    
    def determine_pass_fail(
        self,
        score_breakdown: ScoreBreakdown,
        has_critical_safety_violation: bool = False,
        has_hallucinations: bool = False,
    ) -> PassFailStatus:
        """Determine pass/fail status from score breakdown"""
        if has_critical_safety_violation or has_hallucinations:
            return PassFailStatus.FAIL
        
        if score_breakdown.final_score >= self.pass_threshold:
            return PassFailStatus.PASS
        elif score_breakdown.final_score >= self.partial_pass_threshold:
            return PassFailStatus.PARTIAL
        else:
            return PassFailStatus.FAIL

