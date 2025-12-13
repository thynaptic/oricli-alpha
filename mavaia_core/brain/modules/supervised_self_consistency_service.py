"""
Supervised Self-Consistency Service
Main orchestrator for supervised self-consistency pipeline
Converted from Swift SupervisedSelfConsistencyService.swift
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
    from models.supervised_self_consistency_models import (
        SupervisedResponse,
        CandidateResponse,
        SupervisionScore,
        ComplexityScore,
    )
except ImportError:
    # Models not available - define minimal types
    SupervisedResponse = None
    CandidateResponse = None
    SupervisionScore = None
    ComplexityScore = None


class SupervisedSelfConsistencyServiceModule(BaseBrainModule):
    """Main orchestrator for supervised self-consistency pipeline"""

    def __init__(self):
        self.complexity_analyzer = None
        self.multi_structure_discovery = None
        self.multi_response_generator = None
        self.supervision_service = None
        self.response_selection = None
        self._modules_loaded = False

    @property
    def metadata(self) -> ModuleMetadata:
        return ModuleMetadata(
            name="supervised_self_consistency_service",
            version="1.0.0",
            description="Main orchestrator for supervised self-consistency pipeline",
            operations=[
                "execute_supervised_self_consistency",
                "supervise_candidates",
                "select_best_response",
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

            # Load dependent modules
            self.complexity_analyzer = ModuleRegistry.get_module("query_complexity_analyzer")
            self.multi_structure_discovery = ModuleRegistry.get_module("multi_structure_discovery_service")
            self.multi_response_generator = ModuleRegistry.get_module("multi_response_generator_service")
            self.supervision_service = ModuleRegistry.get_module("supervision_service")
            self.response_selection = ModuleRegistry.get_module("response_selection_service")

            self._modules_loaded = True
        except Exception as e:
            print(f"Error loading modules: {e}")

    def execute(self, operation: str, params: Dict[str, Any]) -> Dict[str, Any]:
        """Execute an operation"""
        self._ensure_modules_loaded()

        if operation == "execute_supervised_self_consistency":
            return self._execute_supervised_self_consistency(params)
        elif operation == "supervise_candidates":
            return self._supervise_candidates(params)
        elif operation == "select_best_response":
            return self._select_best_response(params)
        else:
            raise ValueError(f"Unknown operation: {operation}")

    def _execute_supervised_self_consistency(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """Execute supervised self-consistency pipeline"""
        query = params.get("query", "")
        context = params.get("context")
        conversation_history = params.get("conversation_history")
        self_chaining_metadata = params.get("self_chaining_metadata")

        start_time = time.time()

        # Step 1: Check complexity
        if not self.complexity_analyzer:
            raise ValueError("Complexity analyzer not available")

        complexity_result = self.complexity_analyzer.execute(
            "analyze_complexity",
            {
                "query": query,
                "context": context,
                "self_chaining_metadata": self_chaining_metadata,
            }
        )

        complexity_score = ComplexityScore(
            overall=complexity_result.get("overall", 0.0),
            factors=complexity_result.get("factors", {}),
            reasoning=complexity_result.get("reasoning", False),
            threshold=complexity_result.get("threshold", 0.6),
        )

        if not complexity_score.should_trigger:
            raise ValueError(
                f"Query complexity ({complexity_score.overall:.2f}) does not meet threshold (0.6) "
                "for supervised self-consistency"
            )

        # Step 2: Determine structure count
        structure_count = self.multi_structure_discovery.execute(
            "determine_structure_count",
            {"complexity": complexity_score.overall}
        ) if self.multi_structure_discovery else 3

        # Step 3: Discover multiple structures
        if not self.multi_structure_discovery:
            raise ValueError("Multi-structure discovery service not available")

        structures_result = self.multi_structure_discovery.execute(
            "discover_multiple_structures",
            {
                "query": query,
                "context": context,
                "count": structure_count,
            }
        )

        structures = structures_result.get("structures", [])
        if not structures:
            raise ValueError("Failed to discover any reasoning structures")

        # Step 4: Generate multiple responses per structure
        all_candidates = []

        for structure in structures:
            structure_id = structure.get("id")
            response_count = self.multi_response_generator.execute(
                "determine_response_count",
                {"structure": structure}
            ) if self.multi_response_generator else 2

            candidates_result = self.multi_response_generator.execute(
                "generate_multiple_responses",
                {
                    "structure": structure,
                    "query": query,
                    "context": context,
                    "count": response_count,
                    "conversation_history": conversation_history,
                }
            ) if self.multi_response_generator else {"candidates": []}

            candidates = candidates_result.get("candidates", [])
            all_candidates.extend(candidates)

        if not all_candidates:
            raise ValueError("Failed to generate any candidate responses")

        # Step 5: Supervise all candidates
        if not self.supervision_service:
            raise ValueError("Supervision service not available")

        supervision_result = self.supervision_service.execute(
            "supervise_candidates",
            {
                "candidates": all_candidates,
                "query": query,
                "context": context,
            }
        )

        supervision_scores = supervision_result.get("scores", [])

        # Step 6: Select best response
        if not self.response_selection:
            raise ValueError("Response selection service not available")

        selected_result = self.response_selection.execute(
            "select_best_response",
            {
                "candidates": all_candidates,
                "scores": supervision_scores,
            }
        )

        selected_candidate_id = selected_result.get("selected_candidate_id")
        selected_candidate = next(
            (c for c in all_candidates if c.get("id") == selected_candidate_id),
            None
        )

        if not selected_candidate:
            raise ValueError(f"Selected candidate {selected_candidate_id} not found")

        execution_time = time.time() - start_time

        # Build response
        supervised_response = SupervisedResponse(
            response=selected_result.get("response", ""),
            selected_candidate=CandidateResponse.from_dict(selected_candidate),
            structures_generated=len(structures),
            responses_per_structure=len(all_candidates) // len(structures) if structures else 0,
            total_candidates=len(all_candidates),
            supervision_scores=[
                SupervisionScore.from_dict(s) for s in supervision_scores
            ],
            selection_metadata=selected_result.get("metadata", {}),
            execution_time=execution_time,
        )

        return {
            "success": True,
            "result": supervised_response.to_dict(),
        }

    def _supervise_candidates(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """Supervise candidates (delegates to supervision service)"""
        if not self.supervision_service:
            raise ValueError("Supervision service not available")

        return self.supervision_service.execute("supervise_candidates", params)

    def _select_best_response(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """Select best response (delegates to response selection service)"""
        if not self.response_selection:
            raise ValueError("Response selection service not available")

        return self.response_selection.execute("select_best_response", params)

