"""
Self-Chaining Executor Service
Service for executing discovered reasoning structures
Converted from Swift SelfChainingExecutor.swift
"""

from typing import Any, Dict, List, Optional
import sys
import time
from pathlib import Path

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent))

from mavaia_core.brain.base_module import BaseBrainModule, ModuleMetadata

# Optional imports - models package may not be available
try:
    from models.reasoning_models import (
        ReasoningStructure,
        ExecutionContext,
        ReasoningResult,
        ModuleExecutionResult,
        ExecutionPlan,
        ExecutionStep,
        ExecutionType,
    )
except ImportError:
    # Models not available - define minimal types
    ReasoningStructure = None
    ExecutionContext = None
    ReasoningResult = None
    ModuleExecutionResult = None
    ExecutionPlan = None
    ExecutionStep = None
    ExecutionType = None


class SelfChainingExecutorModule(BaseBrainModule):
    """Service for executing discovered reasoning structures"""

    def __init__(self):
        self.python_brain_service = None
        self.module_registry = None
        self._modules_loaded = False

    @property
    def metadata(self) -> ModuleMetadata:
        return ModuleMetadata(
            name="self_chaining_executor",
            version="1.0.0",
            description="Service for executing discovered reasoning structures",
            operations=[
                "execute_structure",
                "execute_chain",
                "validate_chain_step",
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

            self.python_brain_service = ModuleRegistry.get_module("python_brain_service")
            self.module_registry = ModuleRegistry.get_module("self_chaining_module_registry")

            self._modules_loaded = True
        except Exception as e:
            print(f"Error loading modules: {e}")

    def execute(self, operation: str, params: Dict[str, Any]) -> Dict[str, Any]:
        """Execute an operation"""
        self._ensure_modules_loaded()

        if operation == "execute_structure":
            return self._execute_structure(params)
        elif operation == "execute_chain":
            return self._execute_chain(params)
        elif operation == "validate_chain_step":
            return self._validate_chain_step(params)
        else:
            raise ValueError(f"Unknown operation: {operation}")

    def _execute_structure(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """Execute a discovered reasoning structure"""
        structure_data = params.get("structure", {})
        context_data = params.get("context", {})

        # Reconstruct structure
        structure = self._reconstruct_structure(structure_data)
        context = ExecutionContext(
            query=context_data.get("query", ""),
            conversation_history=context_data.get("conversation_history"),
            additional_context=context_data.get("additional_context"),
        )

        start_time = time.time()

        module_results = {}
        accumulated_context = context.query
        execution_errors = []

        # Build dependency graph
        dependency_graph = self._build_dependency_graph(structure.modules)

        # Execute according to execution plan
        if structure.execution_plan.steps:
            # Use explicit execution plan
            self._execute_by_plan(
                plan=structure.execution_plan,
                modules=structure.modules,
                dependency_graph=dependency_graph,
                context=context,
                accumulated_context=accumulated_context,
                module_results=module_results,
                execution_errors=execution_errors,
            )
        else:
            # Fallback: execute based on dependencies
            self._execute_by_dependencies(
                modules=structure.modules,
                dependency_graph=dependency_graph,
                context=context,
                accumulated_context=accumulated_context,
                module_results=module_results,
                execution_errors=execution_errors,
            )

        # Aggregate final results
        final_response = self._aggregate_results(
            module_results=module_results,
            accumulated_context=accumulated_context,
            query=context.query,
        )

        execution_time = time.time() - start_time
        success = len(execution_errors) == 0

        result = ReasoningResult(
            structure_id=structure.id,
            query=context.query,
            final_response=final_response,
            module_results=module_results,
            execution_time=execution_time,
            success=success,
            error="; ".join(execution_errors) if execution_errors else None,
        )

        return {
            "success": True,
            "result": {
                "structure_id": result.structure_id,
                "query": result.query,
                "final_response": result.final_response,
                "module_results": {
                    k: {
                        "module_id": v.module_id,
                        "output": v.output,
                        "execution_time": v.execution_time,
                        "success": v.success,
                        "error": v.error,
                    }
                    for k, v in result.module_results.items()
                },
                "execution_time": result.execution_time,
                "success": result.success,
                "error": result.error,
            },
        }

    def _execute_chain(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """Execute chain (alias for execute_structure)"""
        return self._execute_structure(params)

    def _validate_chain_step(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """Validate a chain step"""
        step_data = params.get("step", {})
        module_id = step_data.get("module_id", "")

        # Check if module exists
        if self.module_registry:
            validation_result = self.module_registry.execute(
                "validate_module_ids",
                {"module_ids": [module_id]}
            )
            is_valid = validation_result.get("result", {}).get("invalid_ids", []) == []
        else:
            is_valid = True

        return {
            "success": True,
            "result": {
                "is_valid": is_valid,
                "module_id": module_id,
            },
        }

    def _reconstruct_structure(self, structure_data: Dict) -> ReasoningStructure:
        """Reconstruct ReasoningStructure from dictionary"""
        from models.reasoning_models import (
            ReasoningModuleStep,
            ExecutionPlan,
            ExecutionStep,
            ReasoningMetadata,
        )

        modules = [
            ReasoningModuleStep(
                module_id=m.get("module_id", ""),
                module_name=m.get("module_name", ""),
                parameters=m.get("parameters", {}),
                dependencies=m.get("dependencies", []),
                execution_type=m.get("execution_type", "sequential"),
            )
            for m in structure_data.get("modules", [])
        ]

        execution_plan = ExecutionPlan(
            steps=[
                ExecutionStep(
                    step=s.get("step", 0),
                    modules=s.get("modules", []),
                    type=s.get("type", "sequential"),
                    depends_on=s.get("depends_on"),
                )
                for s in structure_data.get("execution_plan", {}).get("steps", [])
            ],
            parallel_groups=structure_data.get("execution_plan", {}).get("parallel_groups", []),
        )

        metadata = ReasoningMetadata(
            discovered_at=structure_data.get("metadata", {}).get("discovered_at", 0.0),
            confidence=structure_data.get("metadata", {}).get("confidence", 0.5),
            reasoning_type=structure_data.get("metadata", {}).get("reasoning_type", ""),
            estimated_complexity=structure_data.get("metadata", {}).get("estimated_complexity", 0.5),
        )

        return ReasoningStructure(
            id=structure_data.get("id", ""),
            query=structure_data.get("query", ""),
            modules=modules,
            execution_plan=execution_plan,
            metadata=metadata,
        )

    def _build_dependency_graph(self, modules: List) -> Dict[str, List[str]]:
        """Build dependency graph from modules"""
        graph = {}
        for module in modules:
            graph[module.module_id] = module.dependencies
        return graph

    def _execute_by_plan(
        self,
        plan: ExecutionPlan,
        modules: List,
        dependency_graph: Dict[str, List[str]],
        context: ExecutionContext,
        accumulated_context: str,
        module_results: Dict[str, ModuleExecutionResult],
        execution_errors: List[str],
    ):
        """Execute modules according to execution plan"""
        # Sort steps by step number
        sorted_steps = sorted(plan.steps, key=lambda s: s.step)

        # Track completed steps
        completed_steps = set()

        for step in sorted_steps:
            # Check dependencies
            if step.depends_on:
                all_dependencies_met = all(dep in completed_steps for dep in step.depends_on)
                if not all_dependencies_met:
                    continue

            # Execute modules in this step
            if step.type == ExecutionType.PARALLEL:
                # Execute modules in parallel (simplified - sequential for now)
                self._execute_modules_sequential(
                    module_ids=step.modules,
                    modules=modules,
                    context=context,
                    accumulated_context=accumulated_context,
                    module_results=module_results,
                    execution_errors=execution_errors,
                )
            else:
                # Execute modules sequentially
                self._execute_modules_sequential(
                    module_ids=step.modules,
                    modules=modules,
                    context=context,
                    accumulated_context=accumulated_context,
                    module_results=module_results,
                    execution_errors=execution_errors,
                )

            completed_steps.add(step.step)

        # Execute parallel groups if any
        for group in plan.parallel_groups:
            self._execute_modules_sequential(
                module_ids=group,
                modules=modules,
                context=context,
                accumulated_context=accumulated_context,
                module_results=module_results,
                execution_errors=execution_errors,
            )

    def _execute_by_dependencies(
        self,
        modules: List,
        dependency_graph: Dict[str, List[str]],
        context: ExecutionContext,
        accumulated_context: str,
        module_results: Dict[str, ModuleExecutionResult],
        execution_errors: List[str],
    ):
        """Execute modules based on dependencies (topological sort)"""
        executed = set()
        in_progress = set()

        def execute_module(module_id: str):
            if module_id in executed or module_id in in_progress:
                return

            in_progress.add(module_id)

            # Execute dependencies first
            if module_id in dependency_graph:
                for dep_id in dependency_graph[module_id]:
                    execute_module(dep_id)

            # Execute this module
            module = next((m for m in modules if m.module_id == module_id), None)
            if not module:
                execution_errors.append(f"Module {module_id} not found")
                in_progress.remove(module_id)
                return

            result = self._execute_single_module(module, context, accumulated_context)
            module_results[module_id] = result
            accumulated_context += f"\n\n{module.module_name} output: {result.output}"

            in_progress.remove(module_id)
            executed.add(module_id)

        # Execute all modules
        for module in modules:
            execute_module(module.module_id)

    def _execute_modules_sequential(
        self,
        module_ids: List[str],
        modules: List,
        context: ExecutionContext,
        accumulated_context: str,
        module_results: Dict[str, ModuleExecutionResult],
        execution_errors: List[str],
    ):
        """Execute modules sequentially"""
        for module_id in module_ids:
            module = next((m for m in modules if m.module_id == module_id), None)
            if not module:
                execution_errors.append(f"Module {module_id} not found")
                continue

            result = self._execute_single_module(module, context, accumulated_context)
            module_results[module_id] = result
            accumulated_context += f"\n\n{module.module_name} output: {result.output}"

    def _execute_single_module(
        self,
        module,
        context: ExecutionContext,
        accumulated_context: str,
    ) -> ModuleExecutionResult:
        """Execute a single module"""
        start_time = time.time()

        try:
            if self.python_brain_service:
                # Execute via Python brain service
                result = self.python_brain_service.execute(
                    "execute_operation",
                    {
                        "module": module.module_name,
                        "operation": "execute",
                        "params": {
                            **module.parameters,
                            "query": context.query,
                            "context": accumulated_context,
                        },
                    }
                )

                output = result.get("result", {}).get("output", "")
                success = result.get("success", False)
                error = None if success else result.get("error", "Unknown error")
            else:
                # Fallback: return empty result
                output = ""
                success = False
                error = "Python brain service not available"

            execution_time = time.time() - start_time

            return ModuleExecutionResult(
                module_id=module.module_id,
                output=output,
                execution_time=execution_time,
                success=success,
                error=error,
            )
        except Exception as e:
            execution_time = time.time() - start_time
            return ModuleExecutionResult(
                module_id=module.module_id,
                output="",
                execution_time=execution_time,
                success=False,
                error=str(e),
            )

    def _aggregate_results(
        self,
        module_results: Dict[str, ModuleExecutionResult],
        accumulated_context: str,
        query: str,
    ) -> str:
        """Aggregate results from all modules into final response"""
        if not module_results:
            return "No results generated"

        # Combine all module outputs
        outputs = [result.output for result in module_results.values() if result.success]
        return "\n\n".join(outputs) if outputs else "Execution completed with errors"

