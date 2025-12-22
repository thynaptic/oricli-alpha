"""
Tool Calling Plan Service - Service for creating, validating, and executing tool calling plans
Mirrors Swift ToolCallingPlanService.swift functionality
"""

from typing import Any, Dict, List, Optional
import json
import re
import time
import asyncio
import logging

from mavaia_core.brain.base_module import BaseBrainModule, ModuleMetadata
from mavaia_core.brain.modules.tool_calling_models import Tool, ToolResult
from mavaia_core.brain.modules.tool_calling_plan_models import (
    ToolCallingPlan,
    PlanStep,
    PlanValidationResult,
    PlanExecutionResult,
    PlanAdaptation,
)
from mavaia_core.brain.modules.tool_execution_service import tool_execution_service
from mavaia_core.exceptions import InvalidParameterError

logger = logging.getLogger(__name__)


class ToolCallingPlanServiceModule(BaseBrainModule):
    """Service for creating, validating, and executing tool calling plans"""

    def __init__(self):
        super().__init__()

    @property
    def metadata(self) -> ModuleMetadata:
        return ModuleMetadata(
            name="tool_calling_plan_service",
            version="1.0.0",
            description=(
                "Plan-based tool calling: creates structured plans, validates them, "
                "executes with dependency handling, adaptive failure handling"
            ),
            operations=[
                "should_create_plan",
                "create_plan",
                "validate_plan",
                "execute_plan",
            ],
            dependencies=[],
            model_required=False,
        )

    def initialize(self) -> bool:
        """Initialize the module"""
        return True

    def execute(self, operation: str, params: Dict[str, Any]) -> Dict[str, Any]:
        """Execute a plan service operation"""
        if operation == "should_create_plan":
            query = params.get("query", "")
            available_tools = params.get("available_tools", [])
            should_plan = self.should_create_plan(query, available_tools)
            return {"should_plan": should_plan}
        elif operation == "create_plan":
            query = params.get("query", "")
            tools = params.get("tools", [])
            conversation_history = params.get("conversation_history")
            plan = self.create_plan(query, tools, conversation_history)
            return plan.to_dict()
        elif operation == "validate_plan":
            plan_dict = params.get("plan", {})
            tools = params.get("tools", [])
            plan = self._dict_to_plan(plan_dict)
            validation = self.validate_plan(plan, tools)
            return validation.to_dict()
        elif operation == "execute_plan":
            plan_dict = params.get("plan", {})
            tools = params.get("tools", [])
            system_prompt = params.get("system_prompt")
            conversation_history = params.get("conversation_history")
            plan = self._dict_to_plan(plan_dict)
            result = asyncio.run(self.execute_plan(plan, tools, system_prompt, conversation_history))
            return result.to_dict()
        else:
            raise InvalidParameterError(
                parameter="operation",
                value=operation,
                reason="Unknown operation for tool_calling_plan_service",
            )

    def should_create_plan(self, query: str, available_tools: List[Dict[str, Any]]) -> bool:
        """Determine if planning is needed for a query"""
        query_lower = query.lower()
        
        # Check for multiple action keywords
        action_keywords = ["and", "then", "after", "before", "first", "next", "finally", "also", "additionally"]
        action_count = sum(1 for keyword in action_keywords if keyword in query_lower)
        
        # Check for sequential indicators
        sequential_indicators = ["step", "steps", "sequence", "order", "process", "pipeline"]
        has_sequential = any(indicator in query_lower for indicator in sequential_indicators)
        
        # Check for multiple tool mentions
        tool_names = [tool.get("name", "").lower() for tool in available_tools]
        mentioned_tools = sum(1 for tool_name in tool_names if tool_name in query_lower)
        
        # Plan if multiple actions, sequential process, multiple tools, or long complex query
        should_plan = (
            action_count >= 2
            or has_sequential
            or mentioned_tools >= 2
            or (len(query) > 100 and len(query.split(",.;")) >= 3)
        )
        
        return should_plan

    def create_plan(
        self,
        query: str,
        tools: List[Dict[str, Any]],
        conversation_history: Optional[List[Dict[str, Any]]] = None,
    ) -> ToolCallingPlan:
        """Create a structured plan from a query"""
        # For now, create a simple plan
        # In a full implementation, this would use an LLM to generate the plan
        
        steps: List[PlanStep] = []
        
        # Simple heuristic: if query mentions tools, create steps for them
        query_lower = query.lower()
        for i, tool in enumerate(tools):
            tool_name = tool.get("name", "")
            if tool_name.lower() in query_lower:
                step = PlanStep(
                    id=f"step_{i+1}",
                    order=i+1,
                    tool_name=tool_name,
                    arguments={},
                    description=f"Execute {tool_name}",
                    estimated_time=2.0,
                )
                steps.append(step)
        
        # If no steps created, create a default step
        if not steps:
            # This would normally be generated by an LLM
            # For now, return an empty plan
            logger.debug(
                "No explicit tool mentions found; returning empty plan",
                extra={"module_name": "tool_calling_plan_service"},
            )
        
        estimated_total_time = sum(step.estimated_time for step in steps)
        
        return ToolCallingPlan(
            query=query,
            steps=steps,
            estimated_total_time=estimated_total_time,
        )

    def validate_plan(self, plan: ToolCallingPlan, tools: List[Dict[str, Any]]) -> PlanValidationResult:
        """Validate a plan before execution"""
        issues: List[str] = []
        warnings: List[str] = []
        suggested_improvements: List[str] = []
        
        # Check all tools exist
        tool_names = {tool.get("name", "") for tool in tools}
        for step in plan.steps:
            if step.tool_name not in tool_names:
                issues.append(f"Step '{step.id}' references unknown tool '{step.tool_name}'")
        
        # Check for circular dependencies
        if self._has_circular_dependencies(plan):
            issues.append("Plan contains circular dependencies")
        
        # Check step IDs are unique
        step_ids = [step.id for step in plan.steps]
        if len(step_ids) != len(set(step_ids)):
            issues.append("Duplicate step IDs found")
        
        # Check dependencies reference valid steps
        valid_step_ids = set(step_ids)
        for step in plan.steps:
            for dep_id in step.depends_on:
                if dep_id not in valid_step_ids:
                    issues.append(f"Step '{step.id}' depends on non-existent step '{dep_id}'")
        
        # Check estimated times are reasonable
        for step in plan.steps:
            if step.estimated_time < 0:
                warnings.append(f"Step '{step.id}' has negative estimated time")
            elif step.estimated_time > 300:
                warnings.append(f"Step '{step.id}' has very long estimated time ({step.estimated_time}s)")
        
        # Check if plan is empty
        if not plan.steps:
            issues.append("Plan has no steps")
        
        is_valid = len(issues) == 0
        
        return PlanValidationResult(
            is_valid=is_valid,
            issues=issues,
            warnings=warnings,
            suggested_improvements=suggested_improvements,
        )

    async def execute_plan(
        self,
        plan: ToolCallingPlan,
        tools: List[Dict[str, Any]],
        system_prompt: Optional[str] = None,
        conversation_history: Optional[List[Dict[str, Any]]] = None,
    ) -> PlanExecutionResult:
        """Execute a plan with adaptive failure handling"""
        start_time = time.time()
        completed_steps: List[str] = []
        failed_steps: List[str] = []
        skipped_steps: List[str] = []
        adaptations: List[PlanAdaptation] = []
        step_results: Dict[str, ToolResult] = {}
        
        # Sort steps by order and dependencies
        sorted_steps = self._sort_steps_by_dependencies(plan.steps)
        
        # Execute steps in order
        for step in sorted_steps:
            # Check if dependencies are met
            dependencies_met = all(dep_id in completed_steps for dep_id in step.depends_on)
            
            if not dependencies_met:
                missing_deps = [dep_id for dep_id in step.depends_on if dep_id not in completed_steps]
                skipped_steps.append(step.id)
                continue
            
            # Execute step
            try:
                from mavaia_core.brain.modules.tool_calling_models import ToolCall, ToolCallFunction
                tool_call = ToolCall(
                    function=ToolCallFunction(name=step.tool_name, arguments=step.arguments)
                )
                result = await tool_execution_service.execute_tool(step.tool_name, step.arguments)
                step_results[step.id] = result
                
                if result.success:
                    completed_steps.append(step.id)
                else:
                    if step.fallback_strategy:
                        adaptation = PlanAdaptation(
                            step_id=step.id,
                            reason=result.error or "Step execution failed",
                            original_action=step.description,
                            adapted_action=step.fallback_strategy,
                        )
                        adaptations.append(adaptation)
                    
                    if step.is_optional:
                        skipped_steps.append(step.id)
                    else:
                        failed_steps.append(step.id)
            except Exception as e:
                if step.is_optional:
                    skipped_steps.append(step.id)
                else:
                    failed_steps.append(step.id)
        
        # Generate final response
        final_response = self._generate_final_response(
            plan, completed_steps, failed_steps, skipped_steps, step_results
        )
        
        total_time = time.time() - start_time
        
        return PlanExecutionResult(
            plan_id=plan.id,
            completed_steps=completed_steps,
            failed_steps=failed_steps,
            skipped_steps=skipped_steps,
            final_response=final_response,
            total_time=total_time,
            adaptations=adaptations,
            step_results=step_results,
        )

    def _has_circular_dependencies(self, plan: ToolCallingPlan) -> bool:
        """Check for circular dependencies using DFS"""
        visited = set()
        rec_stack = set()
        
        def has_cycle(step_id: str) -> bool:
            visited.add(step_id)
            rec_stack.add(step_id)
            
            step = next((s for s in plan.steps if s.id == step_id), None)
            if step:
                for dep_id in step.depends_on:
                    if dep_id not in visited:
                        if has_cycle(dep_id):
                            return True
                    elif dep_id in rec_stack:
                        return True
            
            rec_stack.remove(step_id)
            return False
        
        for step in plan.steps:
            if step.id not in visited:
                if has_cycle(step.id):
                    return True
        
        return False

    def _sort_steps_by_dependencies(self, steps: List[PlanStep]) -> List[PlanStep]:
        """Topological sort of steps by dependencies"""
        sorted_steps: List[PlanStep] = []
        visited = set()
        temp_mark = set()
        
        def visit(step: PlanStep):
            if step.id in temp_mark:
                return
            if step.id in visited:
                return
            
            temp_mark.add(step.id)
            
            # Visit dependencies first
            for dep_id in step.depends_on:
                dep_step = next((s for s in steps if s.id == dep_id), None)
                if dep_step:
                    visit(dep_step)
            
            temp_mark.remove(step.id)
            visited.add(step.id)
            sorted_steps.append(step)
        
        for step in sorted(steps, key=lambda s: s.order):
            if step.id not in visited:
                visit(step)
        
        return sorted_steps

    def _generate_final_response(
        self,
        plan: ToolCallingPlan,
        completed_steps: List[str],
        failed_steps: List[str],
        skipped_steps: List[str],
        step_results: Dict[str, ToolResult],
    ) -> str:
        """Generate final response from plan execution"""
        summary = f"Plan execution summary:\n"
        summary += f"- Completed: {len(completed_steps)} steps\n"
        if failed_steps:
            summary += f"- Failed: {len(failed_steps)} steps\n"
        if skipped_steps:
            summary += f"- Skipped: {len(skipped_steps)} steps\n"
        summary += "\n"
        
        # Collect results from completed steps
        results_text = ""
        for step_id in completed_steps:
            if step_id in step_results:
                result = step_results[step_id]
                step = next((s for s in plan.steps if s.id == step_id), None)
                if step:
                    results_text += f"{step.description}: {result.content}\n"
        
        return summary + results_text

    def _dict_to_plan(self, plan_dict: Dict[str, Any]) -> ToolCallingPlan:
        """Convert dictionary to ToolCallingPlan"""
        steps = [
            PlanStep(
                id=step_dict.get("id", ""),
                order=step_dict.get("order", 0),
                tool_name=step_dict.get("toolName", ""),
                arguments=step_dict.get("arguments", {}),
                description=step_dict.get("description", ""),
                estimated_time=step_dict.get("estimatedTime", 2.0),
                depends_on=step_dict.get("dependsOn", []),
                is_optional=step_dict.get("isOptional", False),
                fallback_strategy=step_dict.get("fallbackStrategy"),
            )
            for step_dict in plan_dict.get("steps", [])
        ]
        
        return ToolCallingPlan(
            id=plan_dict.get("id", ""),
            query=plan_dict.get("query", ""),
            steps=steps,
            estimated_total_time=plan_dict.get("estimatedTotalTime", 0.0),
            dependencies=plan_dict.get("dependencies", {}),
            can_execute_in_parallel=plan_dict.get("canExecuteInParallel", False),
            created_at=plan_dict.get("createdAt", time.time()),
        )

