"""
Tool Calling Plan Models - Data structures for plan-based tool calling
Mirrors Swift ToolCallingPlan.swift functionality
"""

from typing import Any, Dict, List, Optional
from dataclasses import dataclass, field
import time
import uuid
from tool_calling_models import ToolResult


# MARK: - Tool Calling Plan

@dataclass
class PlanStep:
    """A step in a tool calling plan"""
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    order: int = 0
    tool_name: str = ""
    arguments: Dict[str, Any] = field(default_factory=dict)
    description: str = ""
    estimated_time: float = 2.0
    depends_on: List[str] = field(default_factory=list)  # IDs of steps that must complete first
    is_optional: bool = False
    fallback_strategy: Optional[str] = None
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for JSON serialization"""
        result: Dict[str, Any] = {
            "id": self.id,
            "order": self.order,
            "toolName": self.tool_name,
            "arguments": self.arguments,
            "description": self.description,
            "estimatedTime": self.estimated_time,
            "dependsOn": self.depends_on,
            "isOptional": self.is_optional,
        }
        if self.fallback_strategy:
            result["fallbackStrategy"] = self.fallback_strategy
        return result


@dataclass
class ToolCallingPlan:
    """A structured plan for tool calling"""
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    query: str = ""
    steps: List[PlanStep] = field(default_factory=list)
    estimated_total_time: float = 0.0
    dependencies: Dict[str, List[str]] = field(default_factory=dict)  # stepId -> [dependentStepIds]
    can_execute_in_parallel: bool = False
    created_at: float = field(default_factory=time.time)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for JSON serialization"""
        return {
            "id": self.id,
            "query": self.query,
            "steps": [step.to_dict() for step in self.steps],
            "estimatedTotalTime": self.estimated_total_time,
            "dependencies": self.dependencies,
            "canExecuteInParallel": self.can_execute_in_parallel,
            "createdAt": self.created_at,
        }


# MARK: - Plan Validation Result

@dataclass
class PlanValidationResult:
    """Result of plan validation"""
    is_valid: bool
    issues: List[str] = field(default_factory=list)
    warnings: List[str] = field(default_factory=list)
    suggested_improvements: List[str] = field(default_factory=list)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for JSON serialization"""
        return {
            "isValid": self.is_valid,
            "issues": self.issues,
            "warnings": self.warnings,
            "suggestedImprovements": self.suggested_improvements,
        }


# MARK: - Plan Execution Result

@dataclass
class PlanAdaptation:
    """Plan adaptation when a step fails"""
    step_id: str
    reason: str
    original_action: str
    adapted_action: str
    timestamp: float = field(default_factory=time.time)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for JSON serialization"""
        return {
            "stepId": self.step_id,
            "reason": self.reason,
            "originalAction": self.original_action,
            "adaptedAction": self.adapted_action,
            "timestamp": self.timestamp,
        }


@dataclass
class PlanExecutionResult:
    """Result of plan execution"""
    plan_id: str
    completed_steps: List[str] = field(default_factory=list)
    failed_steps: List[str] = field(default_factory=list)
    skipped_steps: List[str] = field(default_factory=list)
    final_response: str = ""
    total_time: float = 0.0
    adaptations: List[PlanAdaptation] = field(default_factory=list)
    step_results: Dict[str, ToolResult] = field(default_factory=dict)  # stepId -> result
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for JSON serialization"""
        return {
            "planId": self.plan_id,
            "completedSteps": self.completed_steps,
            "failedSteps": self.failed_steps,
            "skippedSteps": self.skipped_steps,
            "finalResponse": self.final_response,
            "totalTime": self.total_time,
            "adaptations": [a.to_dict() for a in self.adaptations],
            "stepResults": {k: v.to_dict() for k, v in self.step_results.items()},
        }

