"""
Cognitive Reasoning Orchestrator
Orchestrates all cognitive reasoning features into a unified flow
Converted from Swift CognitiveReasoningOrchestrator.swift
"""

from typing import Any, Dict, Optional
import sys
import time
from pathlib import Path

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent))

from mavaia_core.brain.base_module import BaseBrainModule, ModuleMetadata


class CognitiveReasoningOrchestratorModule(BaseBrainModule):
    """Orchestrates all cognitive reasoning features into a unified flow"""

    def __init__(self):
        self.cot_service = None
        self.tot_service = None
        self.mcts_service = None
        self.adaptive_depth = None
        self.model_cascade = None
        self.self_verification = None
        self.long_horizon_planner = None
        self.python_brain = None
        self._modules_loaded = False

    @property
    def metadata(self) -> ModuleMetadata:
        return ModuleMetadata(
            name="cognitive_reasoning_orchestrator",
            version="1.0.0",
            description="Orchestrates all cognitive reasoning features into a unified flow",
            operations=[
                "execute_cognitive_reasoning",
                "select_reasoning_method",
                "orchestrate_reasoning",
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

            self.cot_service = ModuleRegistry.get_module("chain_of_thought")
            self.tot_service = ModuleRegistry.get_module("tree_of_thought")
            self.mcts_service = ModuleRegistry.get_module("mcts_service")
            self.adaptive_depth = ModuleRegistry.get_module("adaptive_depth_controller")
            self.model_cascade = ModuleRegistry.get_module("model_cascade_service")
            self.self_verification = ModuleRegistry.get_module("self_verification_service")
            self.long_horizon_planner = ModuleRegistry.get_module("long_horizon_planner")
            self.python_brain = ModuleRegistry.get_module("python_brain_service")

            self._modules_loaded = True
        except Exception as e:
            print(f"Error loading modules: {e}")

    def execute(self, operation: str, params: Dict[str, Any]) -> Dict[str, Any]:
        """Execute an operation"""
        self._ensure_modules_loaded()

        if operation == "execute_cognitive_reasoning":
            return self._execute_cognitive_reasoning(params)
        elif operation == "select_reasoning_method":
            return self._select_reasoning_method(params)
        elif operation == "orchestrate_reasoning":
            return self._orchestrate_reasoning(params)
        else:
            raise ValueError(f"Unknown operation: {operation}")

    def _execute_cognitive_reasoning(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """Execute cognitive reasoning with all features integrated"""
        query = params.get("query", "")
        context = params.get("context")
        session_id = params.get("session_id")

        # Step 1: Determine adaptive depth
        if not self.adaptive_depth:
            raise ValueError("Adaptive depth controller not available")

        depth_result = self.adaptive_depth.execute(
            "determine_depth",
            {
                "query": query,
                "context": context,
                "reasoning_method": "cot",
            }
        )

        depth_config = depth_result.get("result", {})
        complexity = depth_config.get("complexity", 0.5)

        # Step 2: Select reasoning method based on complexity
        reasoning_method = self._select_reasoning_method_internal(complexity)

        # Step 3: Execute reasoning with adaptive depth
        reasoning_result = None
        final_model = "cognitive_generator"

        if reasoning_method == "cot" and self.cot_service:
            cot_config = {
                "max_steps": depth_config.get("depth", 5),
                "min_complexity_score": 0.4,
                "adaptive_timeout": True,
                "enable_prompt_chaining": True,
                "reasoning_depth": "deep" if depth_config.get("depth", 0) > 3 else "medium",
            }

            cot_result = self.cot_service.execute(
                "execute_cot",
                {
                    "query": query,
                    "context": context,
                    "configuration": cot_config,
                    "session_id": session_id,
                }
            )

            reasoning_result = {"type": "cot", "result": cot_result}
            final_model = cot_result.get("result", {}).get("model_used", "cognitive_generator")

        elif reasoning_method == "tot" and self.tot_service:
            tot_config = {
                "max_depth": depth_config.get("depth", 3),
                "base_thoughts_per_step": 3,
                "pruning_top_k": {0: 3, 1: 3, 2: 2, 3: 2, 4: 1},
                "min_score_threshold": 0.3,
                "evaluation_weights": {"llm": 0.4, "semantic": 0.3, "heuristic": 0.3},
                "search_strategy": "best_first",
                "max_search_time": 60.0,
                "enable_early_termination": True,
            }

            tot_result = self.tot_service.execute(
                "execute_tot",
                {
                    "query": query,
                    "context": context,
                    "configuration": tot_config,
                    "session_id": session_id,
                }
            )

            reasoning_result = {"type": "tot", "result": tot_result}
            final_model = tot_result.get("result", {}).get("model_used", "cognitive_generator")

        elif reasoning_method == "mcts" and self.mcts_service:
            mcts_config_result = self.adaptive_depth.execute(
                "get_mcts_configuration",
                {"complexity": complexity}
            ) if self.adaptive_depth else {"result": {}}

            mcts_config = mcts_config_result.get("result", {})

            mcts_result = self.mcts_service.execute(
                "execute_mcts",
                {
                    "query": query,
                    "context": context,
                    "configuration": mcts_config,
                    "session_id": session_id,
                }
            )

            reasoning_result = {"type": "mcts", "result": mcts_result}
            final_model = mcts_result.get("result", {}).get("model_used", "cognitive_generator")

        else:
            # Fallback to CoT
            if self.cot_service:
                cot_result = self.cot_service.execute(
                    "execute_cot",
                    {
                        "query": query,
                        "context": context,
                        "configuration": {"max_steps": depth_config.get("depth", 5)},
                        "session_id": session_id,
                    }
                )
                reasoning_result = {"type": "cot", "result": cot_result}
                final_model = cot_result.get("result", {}).get("model_used", "cognitive_generator")

        if not reasoning_result:
            raise ValueError("Failed to execute reasoning")

        # Extract answer and confidence
        result_data = reasoning_result["result"].get("result", {})
        final_answer = result_data.get("final_answer", "")
        final_confidence = result_data.get("confidence", 0.5)

        # Step 4: Check if model cascading is needed
        cascade_used = False
        if self.model_cascade:
            should_cascade_result = self.model_cascade.execute(
                "should_trigger_cascade",
                {
                    "confidence": final_confidence,
                    "verification_failed": False,
                    "complexity": complexity,
                }
            )

            should_cascade = should_cascade_result.get("result", False)

            if should_cascade and final_confidence < 0.7:
                try:
                    cascade_result = self.model_cascade.execute(
                        "cascade",
                        {
                            "query": query,
                            "context": context,
                            "initial_model": final_model,
                            "session_id": session_id,
                        }
                    )

                    cascade_data = cascade_result.get("result", {})
                    if cascade_data.get("final_confidence", 0) > final_confidence:
                        final_answer = cascade_data.get("final_answer", final_answer)
                        final_confidence = cascade_data.get("final_confidence", final_confidence)
                        cascade_used = True
                except Exception as e:
                    print(f"Model cascading failed: {e}")

        # Step 5: Self-verification
        verification_result_data = {}
        if self.self_verification:
            try:
                verification_result = self.self_verification.execute(
                    "verify_answer",
                    {
                        "query": query,
                        "original_answer": final_answer,
                        "original_method": reasoning_method,
                        "original_confidence": final_confidence,
                        "context": context,
                    }
                )

                verification_result_data = verification_result.get("result", {})
                verified_confidence = verification_result_data.get("verified_confidence", final_confidence)

                if verified_confidence > final_confidence:
                    final_answer = verification_result_data.get("verified_answer", final_answer)
                    final_confidence = verified_confidence
            except Exception as e:
                print(f"Self-verification failed: {e}")

        return {
            "success": True,
            "result": {
                "answer": final_answer,
                "confidence": final_confidence,
                "reasoning_method": reasoning_method,
                "reasoning_result": reasoning_result,
                "depth_config": depth_config,
                "cascade_used": cascade_used,
                "verification_result": verification_result_data,
            },
        }

    def _select_reasoning_method(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """Select reasoning method based on complexity"""
        complexity = params.get("complexity", 0.5)
        method = self._select_reasoning_method_internal(complexity)
        return {"success": True, "result": method}

    def _select_reasoning_method_internal(self, complexity: float) -> str:
        """Internal method to select reasoning method"""
        if complexity > 0.8:
            return "mcts"  # High complexity -> MCTS
        elif complexity > 0.6:
            return "tot"  # Medium-high complexity -> ToT
        elif complexity > 0.4:
            return "cot"  # Medium complexity -> CoT
        else:
            return "cot"  # Low complexity -> CoT (simplest)

    def _orchestrate_reasoning(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """Orchestrate reasoning (alias for execute_cognitive_reasoning)"""
        return self._execute_cognitive_reasoning(params)

