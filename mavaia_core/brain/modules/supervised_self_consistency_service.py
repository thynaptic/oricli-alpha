"""
Supervised Self-Consistency Service
Main orchestrator for supervised self-consistency pipeline
Converted from Swift SupervisedSelfConsistencyService.swift
"""

from typing import Any, Dict, List, Optional
import time
import logging
from dataclasses import dataclass

from mavaia_core.brain.base_module import BaseBrainModule, ModuleMetadata
from mavaia_core.brain.registry import ModuleRegistry
from mavaia_core.exceptions import InvalidParameterError

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

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class _FallbackComplexityScore:
    overall: float
    factors: Dict[str, float]
    reasoning: bool
    threshold: float

    @property
    def should_trigger(self) -> bool:
        return bool(self.reasoning) and float(self.overall) >= float(self.threshold)


@dataclass(frozen=True)
class _FallbackCandidateResponse:
    id: str
    text: str
    metadata: Dict[str, Any]

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "_FallbackCandidateResponse":
        if not isinstance(data, dict):
            data = {}
        candidate_id = data.get("id")
        candidate_text = data.get("text")
        if not isinstance(candidate_id, str) or not candidate_id:
            candidate_id = "unknown"
        if not isinstance(candidate_text, str):
            candidate_text = ""
        metadata = data.get("metadata", {})
        if not isinstance(metadata, dict):
            metadata = {}
        return cls(id=candidate_id, text=candidate_text, metadata=metadata)

    def to_dict(self) -> Dict[str, Any]:
        return {"id": self.id, "text": self.text, "metadata": dict(self.metadata)}


@dataclass(frozen=True)
class _FallbackSupervisionScore:
    candidate_id: str
    overall: float
    correctness: float
    reasoning_quality: float
    consistency: float

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "_FallbackSupervisionScore":
        if not isinstance(data, dict):
            data = {}
        candidate_id = data.get("candidate_id") or data.get("id") or ""
        if not isinstance(candidate_id, str):
            candidate_id = str(candidate_id)

        overall = data.get("combined_score", data.get("overall", data.get("model_score", 0.5)))
        correctness = data.get("correctness_score", data.get("correctness", 0.5))
        reasoning_quality = data.get("reasoning_quality_score", data.get("reasoning_quality", 0.5))
        consistency = data.get("consistency_score", data.get("consistency", 0.5))

        def clamp01(v: Any, default: float) -> float:
            try:
                f = float(v)
            except (TypeError, ValueError):
                return default
            if f < 0.0:
                return 0.0
            if f > 1.0:
                return 1.0
            return f

        return cls(
            candidate_id=candidate_id,
            overall=clamp01(overall, 0.5),
            correctness=clamp01(correctness, 0.5),
            reasoning_quality=clamp01(reasoning_quality, 0.5),
            consistency=clamp01(consistency, 0.5),
        )

    def to_dict(self) -> Dict[str, Any]:
        return {
            "candidate_id": self.candidate_id,
            "overall": self.overall,
            "correctness": self.correctness,
            "reasoning_quality": self.reasoning_quality,
            "consistency": self.consistency,
        }


@dataclass(frozen=True)
class _FallbackSupervisedResponse:
    response: str
    selected_candidate: _FallbackCandidateResponse
    structures_generated: int
    responses_per_structure: int
    total_candidates: int
    supervision_scores: List[_FallbackSupervisionScore]
    selection_metadata: Dict[str, Any]
    execution_time: float

    def to_dict(self) -> Dict[str, Any]:
        return {
            "response": self.response,
            "selected_candidate": self.selected_candidate.to_dict(),
            "structures_generated": self.structures_generated,
            "responses_per_structure": self.responses_per_structure,
            "total_candidates": self.total_candidates,
            "supervision_scores": [s.to_dict() for s in self.supervision_scores],
            "selection_metadata": dict(self.selection_metadata),
            "execution_time": self.execution_time,
        }


class SupervisedSelfConsistencyServiceModule(BaseBrainModule):
    """Main orchestrator for supervised self-consistency pipeline"""

    def __init__(self):
        super().__init__()
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
            # Load dependent modules
            self.complexity_analyzer = (
                ModuleRegistry.get_module("query_complexity_analyzer")
                or ModuleRegistry.get_module("query_complexity")
            )
            self.multi_structure_discovery = ModuleRegistry.get_module(
                "multi_structure_discovery_service"
            )
            self.multi_response_generator = ModuleRegistry.get_module(
                "multi_response_generator_service"
            )
            self.supervision_service = ModuleRegistry.get_module("supervision_service")
            self.response_selection = ModuleRegistry.get_module("response_selection_service")

            self._modules_loaded = True
        except Exception as e:
            logger.debug(
                "Error loading modules for supervised_self_consistency_service",
                exc_info=True,
                extra={"module_name": "supervised_self_consistency_service", "error_type": type(e).__name__},
            )

    def execute(self, operation: str, params: Dict[str, Any]) -> Dict[str, Any]:
        """Execute an operation"""
        self._ensure_modules_loaded()

        match operation:
            case "execute_supervised_self_consistency":
                return self._execute_supervised_self_consistency(params)
            case "supervise_candidates":
                return self._supervise_candidates(params)
            case "select_best_response":
                return self._select_best_response(params)
            case _:
                raise InvalidParameterError(
                    parameter="operation",
                    value=operation,
                    reason="Unknown operation for supervised_self_consistency_service",
                )

    def _execute_supervised_self_consistency(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """Execute supervised self-consistency pipeline"""
        query = params.get("query", "")
        context = params.get("context")
        conversation_history = params.get("conversation_history")
        self_chaining_metadata = params.get("self_chaining_metadata")

        if not isinstance(query, str) or not query.strip():
            raise InvalidParameterError("query", str(query), "query must be a non-empty string")
        if context is not None and not isinstance(context, str):
            raise InvalidParameterError(
                "context",
                str(type(context).__name__),
                "context must be a string when provided",
            )
        if conversation_history is not None and not isinstance(conversation_history, list):
            raise InvalidParameterError(
                "conversation_history",
                str(type(conversation_history).__name__),
                "conversation_history must be a list when provided",
            )
        if self_chaining_metadata is not None and not isinstance(self_chaining_metadata, dict):
            raise InvalidParameterError(
                "self_chaining_metadata",
                str(type(self_chaining_metadata).__name__),
                "self_chaining_metadata must be a dict when provided",
            )

        start_time = time.time()

        # Step 1: Check complexity
        if not self.complexity_analyzer:
            return {"success": False, "error": "Complexity analyzer not available"}

        try:
            complexity_result = self.complexity_analyzer.execute(
                "analyze_complexity",
                {
                    "query": query,
                    "context": context,
                    "self_chaining_metadata": self_chaining_metadata,
                },
            )
        except Exception as e:
            logger.debug(
                "Complexity analysis failed",
                exc_info=True,
                extra={"module_name": "supervised_self_consistency_service", "error_type": type(e).__name__},
            )
            return {"success": False, "error": "Complexity analysis failed"}

        score_cls = ComplexityScore or _FallbackComplexityScore
        try:
            complexity_score = score_cls(
                overall=float(complexity_result.get("overall", 0.0)),
                factors=complexity_result.get("factors", {}) if isinstance(complexity_result.get("factors", {}), dict) else {},
                reasoning=bool(complexity_result.get("reasoning", False)),
                threshold=float(complexity_result.get("threshold", 0.6)),
            )
        except Exception:
            complexity_score = _FallbackComplexityScore(overall=0.0, factors={}, reasoning=False, threshold=0.6)

        if not complexity_score.should_trigger:
            return {
                "success": False,
                "error": "Query complexity does not meet threshold for supervised self-consistency",
                "should_trigger": False,
                "complexity": {
                    "overall": complexity_score.overall,
                    "threshold": complexity_score.threshold,
                    "reasoning": complexity_score.reasoning,
                    "factors": complexity_score.factors,
                },
            }

        # Step 2: Determine structure count
        structure_count = self.multi_structure_discovery.execute(
            "determine_structure_count",
            {"complexity": complexity_score.overall}
        ) if self.multi_structure_discovery else 3

        # Step 3: Discover multiple structures
        if not self.multi_structure_discovery:
            return {"success": False, "error": "Multi-structure discovery service not available"}

        try:
            structures_result = self.multi_structure_discovery.execute(
                "discover_multiple_structures",
                {
                    "query": query,
                    "context": context,
                    "count": structure_count,
                },
            )
        except Exception as e:
            logger.debug(
                "Structure discovery failed",
                exc_info=True,
                extra={"module_name": "supervised_self_consistency_service", "error_type": type(e).__name__},
            )
            return {"success": False, "error": "Failed to discover reasoning structures"}

        structures = structures_result.get("structures", [])
        if not structures:
            return {"success": False, "error": "Failed to discover any reasoning structures"}

        # Step 4: Generate multiple responses per structure
        if not self.multi_response_generator:
            return {"success": False, "error": "Multi-response generator service not available"}

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
            return {"success": False, "error": "Failed to generate any candidate responses"}

        # Step 5: Supervise all candidates
        if not self.supervision_service:
            return {"success": False, "error": "Supervision service not available"}

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
        selected_result: Dict[str, Any] = {}
        selected_candidate_id = None
        if self.response_selection:
            try:
                selected_result = self.response_selection.execute(
                    "select_best_response",
                    {
                        "candidates": all_candidates,
                        "scores": supervision_scores,
                    },
                )
                selected_candidate_id = selected_result.get("selected_candidate_id")
            except Exception as e:
                logger.debug(
                    "Response selection service failed; falling back to local selection",
                    exc_info=True,
                    extra={"module_name": "supervised_self_consistency_service", "error_type": type(e).__name__},
                )

        if not selected_candidate_id:
            score_map: Dict[str, float] = {}
            if isinstance(supervision_scores, list):
                for s in supervision_scores:
                    if not isinstance(s, dict):
                        continue
                    cid = s.get("candidate_id") or s.get("id")
                    if not isinstance(cid, str) or not cid:
                        continue
                    try:
                        score_map[cid] = float(
                            s.get("combined_score", s.get("overall", s.get("model_score", 0.0)))
                        )
                    except (TypeError, ValueError):
                        score_map[cid] = 0.0

            best_id = None
            best_score = float("-inf")
            for c in all_candidates:
                if not isinstance(c, dict):
                    continue
                cid = c.get("id")
                if not isinstance(cid, str) or not cid:
                    continue
                sc = score_map.get(cid, 0.0)
                if sc > best_score:
                    best_score = sc
                    best_id = cid

            selected_candidate_id = best_id
            if not selected_candidate_id and all_candidates and isinstance(all_candidates[0], dict):
                selected_candidate_id = all_candidates[0].get("id")

            selected_result = {
                "selected_candidate_id": selected_candidate_id,
                "response": next(
                    (
                        c.get("text", "")
                        for c in all_candidates
                        if isinstance(c, dict) and c.get("id") == selected_candidate_id
                    ),
                    "",
                ),
                "metadata": {"selection_method": "local_score_fallback"},
            }
        selected_candidate = next(
            (c for c in all_candidates if c.get("id") == selected_candidate_id),
            None
        )

        if not selected_candidate:
            return {"success": False, "error": "Selected candidate not found"}

        execution_time = time.time() - start_time

        # Build response
        resp_cls = SupervisedResponse or _FallbackSupervisedResponse
        cand_cls = CandidateResponse or _FallbackCandidateResponse
        score_cls2 = SupervisionScore or _FallbackSupervisionScore
        supervised_response = resp_cls(
            response=selected_result.get("response", ""),
            selected_candidate=cand_cls.from_dict(selected_candidate),
            structures_generated=len(structures),
            responses_per_structure=len(all_candidates) // len(structures) if structures else 0,
            total_candidates=len(all_candidates),
            supervision_scores=[
                score_cls2.from_dict(s) for s in supervision_scores if isinstance(s, dict)
            ],
            selection_metadata=selected_result.get("metadata", {}) if isinstance(selected_result.get("metadata", {}), dict) else {},
            execution_time=float(execution_time),
        )

        return {
            "success": True,
            "result": supervised_response.to_dict(),
        }

    def _supervise_candidates(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """Supervise candidates (delegates to supervision service)"""
        if not self.supervision_service:
            return {"success": False, "error": "Supervision service not available"}

        return self.supervision_service.execute("supervise_candidates", params)

    def _select_best_response(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """Select best response (delegates to response selection service)"""
        if not self.response_selection:
            return {"success": False, "error": "Response selection service not available"}

        return self.response_selection.execute("select_best_response", params)

