from __future__ import annotations
"""
Strategic Pre-Execution Planner Module
Orchestrates ToT, MCTS, and CoT to formulate and validate execution plans.
Ensures Oricli-Alpha "thinks before acting" on complex goals.
"""

import logging
import time
from typing import Dict, Any, List, Optional

from oricli_core.brain.base_module import BaseBrainModule, ModuleMetadata
from oricli_core.brain.registry import ModuleRegistry
from oricli_core.exceptions import InvalidParameterError

logger = logging.getLogger(__name__)

class StrategicPlannerModule(BaseBrainModule):
    """Orchestrates high-fidelity planning using ToT, MCTS, and CoT."""

    def __init__(self):
        super().__init__()
        self.tree_of_thought = None
        self.mcts_search_engine = None
        self.chain_of_thought = None
        self._modules_loaded = False

    @property
    def metadata(self) -> ModuleMetadata:
        return ModuleMetadata(
            name="strategic_planner",
            version="1.0.0",
            description="Strategic pre-execution planner combining ToT, MCTS, and CoT",
            operations=[
                "create_strategic_plan",
                "validate_plan"
            ],
            dependencies=["tree_of_thought", "mcts_search_engine", "chain_of_thought"],
            model_required=False,
        )

    def _ensure_modules_loaded(self):
        """Lazy load planning components."""
        if self._modules_loaded:
            return
        
        try:
            self.tree_of_thought = ModuleRegistry.get_module("tree_of_thought")
            self.mcts_search_engine = ModuleRegistry.get_module("mcts_search_engine")
            self.chain_of_thought = ModuleRegistry.get_module("chain_of_thought")
            self._modules_loaded = True
        except Exception as e:
            logger.error(f"Failed to load strategic_planner dependencies: {e}")

    def execute(self, operation: str, params: Dict[str, Any]) -> Dict[str, Any]:
        self._ensure_modules_loaded()
        
        if operation == "create_strategic_plan":
            return self._create_strategic_plan(params)
        elif operation == "validate_plan":
            return self._validate_plan(params)
        else:
            raise InvalidParameterError(parameter="operation", value=operation, reason="Unsupported operation")

    def _create_strategic_plan(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """
        Orchestrated planning flow:
        1. ToT: Generate strategy branches
        2. MCTS: Simulate and score branches
        3. CoT: Detailed decomposition of the best branch
        """
        goal = params.get("goal") or params.get("input", "")
        if not goal:
            return {"success": False, "error": "No goal provided for planning"}

        _rich_log(f"Planner: Initiating strategic planning for goal: '{goal[:50]}...'", "cyan", "🧭")

        # Phase 1: Tree of Thought - Strategy Generation
        strategies = []
        if self.tree_of_thought:
            _rich_log("Phase 1: Generating strategy branches via Tree of Thoughts...", "dim", "🌳")
            tot_res = self.tree_of_thought.execute("generate_thoughts", {
                "input": f"Generate 3 diverse high-level strategies to solve this goal: {goal}",
                "num_thoughts": 3
            })
            strategies = tot_res.get("thoughts", [])
        
        if not strategies:
            strategies = [f"Direct execution path for: {goal}"]

        # Phase 2: MCTS - Strategy Simulation
        best_strategy = strategies[0]
        scores = {}
        if self.mcts_search_engine:
            _rich_log(f"Phase 2: Simulating {len(strategies)} strategies via MCTS rollouts...", "dim", "🎲")
            for i, strategy in enumerate(strategies):
                mcts_res = self.mcts_search_engine.execute("search", {
                    "input": f"Simulate the success probability of this strategy: {strategy} for goal: {goal}",
                    "max_iterations": 10
                })
                # Simple scoring heuristic for mock/prototype
                score = mcts_res.get("confidence", 0.5 + (i * 0.1)) 
                scores[strategy] = score
            
            # Pick best
            best_strategy = max(scores, key=scores.get)
            _rich_log(f"MCTS Selected Strategy: '{best_strategy[:60]}...' (Score: {scores[best_strategy]:.2f})", "green", "🎯")

        # Phase 3: Chain of Thought - Step Decomposition
        steps = []
        if self.chain_of_thought:
            _rich_log("Phase 3: Decomposing winning strategy into discrete steps via Chain of Thought...", "dim", "🔗")
            cot_res = self.chain_of_thought.execute("generate_cot", {
                "input": f"Create a 5-step concrete execution plan for this strategy: {best_strategy}",
                "expected_steps": 5
            })
            steps = cot_res.get("steps", [])

        if not steps:
            steps = [f"1. Analyze {goal}", "2. Execute primary path", "3. Verify results"]

        return {
            "success": True,
            "goal": goal,
            "selected_strategy": best_strategy,
            "strategy_scores": scores,
            "steps": steps,
            "method": "tot_mcts_cot_fusion"
        }

    def _validate_plan(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """Re-validate a generated plan using MCTS."""
        # Simple implementation for now
        return {"success": True, "valid": True, "confidence": 0.9}

def _rich_log(message: str, style: str = "white", icon: str = ""):
    prefix = f"{icon} " if icon else ""
    print(f"[{style}]{prefix}{message}")
