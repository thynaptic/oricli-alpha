from __future__ import annotations
"""
Chain-of-Thought Data Models

Data structures for Chain-of-Thought reasoning process.
Ported from Swift ChainOfThoughtModels.swift
"""

import uuid
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any


@dataclass
class CoTStep:
    """Represents a single step in a chain-of-thought reasoning process"""

    prompt: str
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    reasoning: str | None = None
    intermediate_state: dict[str, str] | None = None
    confidence: float | None = None
    timestamp: datetime = field(default_factory=datetime.now)

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary for serialization"""
        return {
            "id": self.id,
            "prompt": self.prompt,
            "reasoning": self.reasoning,
            "intermediate_state": self.intermediate_state,
            "confidence": self.confidence,
            "timestamp": self.timestamp.isoformat(),
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "CoTStep":
        """Create from dictionary"""
        return cls(
            id=data.get("id", str(uuid.uuid4())),
            prompt=data["prompt"],
            reasoning=data.get("reasoning"),
            intermediate_state=data.get("intermediate_state"),
            confidence=data.get("confidence"),
            timestamp=datetime.fromisoformat(data["timestamp"])
            if "timestamp" in data and data["timestamp"]
            else datetime.now(),
        )


@dataclass
class CoTResult:
    """Complete result from a chain-of-thought reasoning process"""

    steps: list[CoTStep]
    final_answer: str
    total_reasoning: str
    confidence: float
    model_used: str
    total_latency: float

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary for serialization"""
        return {
            "steps": [step.to_dict() for step in self.steps],
            "final_answer": self.final_answer,
            "conclusion": self.final_answer,  # Alias for test compatibility
            "reasoning": self.total_reasoning,  # Alias for test compatibility
            "total_reasoning": self.total_reasoning,
            "confidence": self.confidence,
            "model_used": self.model_used,
            "total_latency": self.total_latency,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "CoTResult":
        """Create from dictionary"""
        return cls(
            steps=[CoTStep.from_dict(s) for s in data["steps"]],
            final_answer=data["final_answer"],
            total_reasoning=data["total_reasoning"],
            confidence=data["confidence"],
            model_used=data["model_used"],
            total_latency=data["total_latency"],
        )


@dataclass
class CoTConfiguration:
    """Configuration for chain-of-thought processing"""

    max_steps: int = 5
    min_complexity_score: float = 0.6
    adaptive_timeout: bool = True
    enable_prompt_chaining: bool = True
    reasoning_depth: str = "medium"  # "shallow", "medium", "deep"

    @classmethod
    def default(cls) -> "CoTConfiguration":
        """Return default configuration"""
        return cls()

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary"""
        return {
            "max_steps": self.max_steps,
            "min_complexity_score": self.min_complexity_score,
            "adaptive_timeout": self.adaptive_timeout,
            "enable_prompt_chaining": self.enable_prompt_chaining,
            "reasoning_depth": self.reasoning_depth,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "CoTConfiguration":
        """Create from dictionary"""
        return cls(
            max_steps=data.get("max_steps", 5),
            min_complexity_score=data.get("min_complexity_score", 0.6),
            adaptive_timeout=data.get("adaptive_timeout", True),
            enable_prompt_chaining=data.get("enable_prompt_chaining", True),
            reasoning_depth=data.get("reasoning_depth", "medium"),
        )


@dataclass
class ComplexityFactor:
    """A factor contributing to complexity score"""

    name: str
    contribution: float
    description: str

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary"""
        return {
            "name": self.name,
            "contribution": self.contribution,
            "description": self.description,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "ComplexityFactor":
        """Create from dictionary"""
        return cls(
            name=data["name"],
            contribution=data["contribution"],
            description=data["description"],
        )


@dataclass
class CoTComplexityScore:
    """Result from Chain-of-Thought complexity detection analysis"""

    score: float  # 0.0 to 1.0
    factors: list[ComplexityFactor]
    requires_cot: bool
    estimated_timeout_multiplier: float

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary"""
        return {
            "score": self.score,
            "complexity": self.score,  # Alias for test compatibility
            "factors": [f.to_dict() for f in self.factors],
            "requires_cot": self.requires_cot,
            "estimated_timeout_multiplier": self.estimated_timeout_multiplier,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "CoTComplexityScore":
        """Create from dictionary"""
        factors = [ComplexityFactor.from_dict(f) for f in data.get("factors", [])]
        return cls(
            score=data.get("score", 0.5),
            factors=factors,
            requires_cot=data.get("requires_cot", False),
            estimated_timeout_multiplier=data.get("estimated_timeout_multiplier", 1.0),
        )


# Reflection types

@dataclass
class ReflectionResult:
    """Result from reflection analysis"""

    should_reflect: bool
    corrections: list["Correction"]
    improved_steps: list[CoTStep] | None
    reflection_depth: int

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary"""
        return {
            "should_reflect": self.should_reflect,
            "corrections": [c.to_dict() for c in self.corrections],
            "improved_steps": (
                [s.to_dict() for s in self.improved_steps]
                if self.improved_steps
                else None
            ),
            "reflection_depth": self.reflection_depth,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "ReflectionResult":
        """Create from dictionary"""
        corrections = [Correction.from_dict(c) for c in data.get("corrections", [])]
        improved_steps = (
            [CoTStep.from_dict(s) for s in data["improved_steps"]]
            if data.get("improved_steps")
            else None
        )
        return cls(
            should_reflect=data.get("should_reflect", False),
            corrections=corrections,
            improved_steps=improved_steps,
            reflection_depth=data.get("reflection_depth", 0),
        )


@dataclass
class Correction:
    """A correction suggestion for a reasoning step"""

    step_index: int
    issue: str
    suggestion: str | None = None

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary"""
        return {
            "step_index": self.step_index,
            "issue": self.issue,
            "suggestion": self.suggestion,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "Correction":
        """Create from dictionary"""
        return cls(
            step_index=data["step_index"],
            issue=data["issue"],
            suggestion=data.get("suggestion"),
        )


@dataclass
class ReflectionIssue:
    """An issue identified during reflection"""

    step_index: int
    description: str
    suggestion: str | None = None

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary"""
        return {
            "step_index": self.step_index,
            "description": self.description,
            "suggestion": self.suggestion,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "ReflectionIssue":
        """Create from dictionary"""
        return cls(
            step_index=data["step_index"],
            description=data["description"],
            suggestion=data.get("suggestion"),
        )


@dataclass
class CoTStageResult:
    """Result from a CoT reasoning stage (decomposition, reasoning, or synthesis)"""

    stage_name: str  # "decomposition", "reasoning", or "synthesis"
    output: Any  # Stage-specific output (dict, list, str)
    execution_time: float
    success: bool
    error: str | None = None
    metadata: dict[str, Any] | None = None

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary for serialization"""
        return {
            "stage_name": self.stage_name,
            "output": self.output,
            "execution_time": self.execution_time,
            "success": self.success,
            "error": self.error,
            "metadata": self.metadata or {},
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "CoTStageResult":
        """Create from dictionary"""
        return cls(
            stage_name=data["stage_name"],
            output=data["output"],
            execution_time=data["execution_time"],
            success=data["success"],
            error=data.get("error"),
            metadata=data.get("metadata"),
        )

