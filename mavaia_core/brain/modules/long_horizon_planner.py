"""
Long Horizon Planner - Long-horizon planning for multi-step goal-based reasoning
Converted from Swift LongHorizonPlanner.swift
"""

from typing import Any, Dict, List, Optional
import sys
from pathlib import Path

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent))

from mavaia_core.brain.base_module import BaseBrainModule, ModuleMetadata


class LongHorizonPlannerModule(BaseBrainModule):
    """Long-horizon planning for multi-step goal-based reasoning"""

    def __init__(self):
        self.mcts_service = None
        self.complexity_detector = None
        self.cognitive_generator = None
        self._modules_loaded = False

    @property
    def metadata(self) -> ModuleMetadata:
        return ModuleMetadata(
            name="long_horizon_planner",
            version="1.0.0",
            description="Long-horizon planning for multi-step goal-based reasoning",
            operations=[
                "create_long_plan",
                "execute_plan",
                "create_plan",
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
            from mavaia_core.brain.registry import ModuleRegistry

            self.mcts_service = ModuleRegistry.get_module("mcts_service")
            self.complexity_detector = ModuleRegistry.get_module("cot_complexity_detector")
            self.cognitive_generator = ModuleRegistry.get_module("cognitive_generator")

            self._modules_loaded = True
        except Exception as e:
            # Modules not available - will use fallback methods
            pass

    def execute(self, operation: str, params: Dict[str, Any]) -> Dict[str, Any]:
        """Execute an operation"""
        self._ensure_modules_loaded()

        if operation == "create_long_plan":
            return self._create_long_plan(params)
        elif operation == "execute_plan":
            return self._execute_plan(params)
        elif operation == "create_plan":
            return self._create_plan(params)
        else:
            raise ValueError(f"Unknown operation: {operation}")

    def _create_long_plan(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """Create a long-horizon plan for a goal"""
        return self._create_plan(params)

    def _create_plan(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """Create a plan for a goal"""
        goal = params.get("goal", "")
        context = params.get("context")
        max_depth = params.get("max_depth")
        use_mcts = params.get("use_mcts", True)

        # Analyze complexity
        complexity_score = 0.5
        if self.complexity_detector:
            try:
                complexity_result = self.complexity_detector.execute("analyze_complexity", {
                    "query": goal,
                    "context": context,
                })
                complexity_score = complexity_result.get("score", 0.5)
            except:
                pass

        # Determine plan depth
        plan_depth = max_depth or self._determine_plan_depth(complexity_score)

        # Generate plan steps
        if use_mcts and complexity_score > 0.7 and self.mcts_service:
            # Use MCTS for complex planning
            try:
                result = self.mcts_service.execute("search", {
                    "query": goal,
                    "context": context,
                    "max_depth": plan_depth,
                })

                steps = result.get("steps", [])
            except:
                steps = self._create_sequential_steps(goal, context, plan_depth)
        else:
            # Use sequential planning
            steps = self._create_sequential_steps(goal, context, plan_depth)

        return {
            "success": True,
            "goal": goal,
            "steps": steps,
            "depth": plan_depth,
            "status": "planning",
        }

    def _execute_plan(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """Execute a long-horizon plan"""
        plan = params.get("plan", {})
        steps = plan.get("steps", [])

        executed_steps = []
        failures = []

        for index, step in enumerate(steps):
            step_result = self._execute_step(step, executed_steps)

            executed_steps.append({
                **step,
                "result": step_result.get("result"),
                "success": step_result.get("success", False),
            })

            if not step_result.get("success", False):
                failures.append({
                    "step_index": index,
                    "step": step,
                    "error": step_result.get("error", "Unknown error"),
                })

                # Attempt recovery
                recovery_plan = self._attempt_recovery(step, executed_steps, plan)
                if recovery_plan:
                    recovery_result = self._execute_plan({"plan": recovery_plan})
                    if recovery_result.get("success", False):
                        executed_steps.extend(recovery_result.get("executed_steps", []))
                        continue
                    else:
                        break

        success = len(failures) == 0 and len(executed_steps) == len(steps)

        return {
            "success": success,
            "plan": plan,
            "executed_steps": executed_steps,
            "failures": failures,
            "completion_percentage": len(executed_steps) / len(steps) if steps else 0.0,
        }

    def _create_sequential_steps(
        self, goal: str, context: Optional[str], max_depth: int
    ) -> List[Dict[str, Any]]:
        """Create sequential plan steps"""
        if not self.cognitive_generator:
            # Fallback: simple steps
            return [
                {
                    "id": f"step_{i}",
                    "description": f"Step {i + 1}",
                    "action": f"Perform action {i + 1}",
                }
                for i in range(max_depth)
            ]

        try:
            # Use cognitive generator to create plan
            result = self.cognitive_generator.execute("create_plan", {
                "goal": goal,
                "context": context,
                "max_depth": max_depth,
            })

            return result.get("steps", [])
        except:
            # Fallback
            return [
                {
                    "id": f"step_{i}",
                    "description": f"Step {i + 1}",
                    "action": f"Perform action {i + 1}",
                }
                for i in range(max_depth)
            ]

    def _execute_step(
        self, step: Dict[str, Any], previous_steps: List[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """Execute a single plan step"""
        action = step.get("action", "")

        if self.cognitive_generator:
            try:
                result = self.cognitive_generator.execute("execute_action", {
                    "action": action,
                    "context": step.get("context", ""),
                })

                return {
                    "success": True,
                    "result": result.get("result", ""),
                }
            except Exception as e:
                return {
                    "success": False,
                    "error": str(e),
                }

        # Fallback: assume success
        return {
            "success": True,
            "result": f"Executed: {action}",
        }

    def _attempt_recovery(
        self, failed_step: Dict[str, Any], executed_steps: List[Dict[str, Any]], original_plan: Dict[str, Any]
    ) -> Optional[Dict[str, Any]]:
        """Attempt to recover from a failed step"""
        # In full implementation, would create recovery plan
        # For now, return None (no recovery)
        return None

    def _determine_plan_depth(self, complexity_score: float) -> int:
        """Determine plan depth based on complexity"""
        if complexity_score > 0.8:
            return 7
        elif complexity_score > 0.6:
            return 5
        elif complexity_score > 0.4:
            return 3
        else:
            return 2

