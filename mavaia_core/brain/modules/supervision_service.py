"""
Supervision Service - Service to evaluate candidate responses using model-based supervision
Converted from Swift SupervisionService.swift
"""

from typing import Any, Dict, List, Optional
import json
import logging

from mavaia_core.brain.base_module import BaseBrainModule, ModuleMetadata
from mavaia_core.brain.registry import ModuleRegistry
from mavaia_core.exceptions import InvalidParameterError

logger = logging.getLogger(__name__)


class SupervisionServiceModule(BaseBrainModule):
    """Service to evaluate candidate responses using model-based supervision and internal scoring"""

    def __init__(self):
        super().__init__()
        self.cognitive_generator = None
        self.internal_scoring = None
        self._modules_loaded = False

    @property
    def metadata(self) -> ModuleMetadata:
        return ModuleMetadata(
            name="supervision_service",
            version="1.0.0",
            description="Service to evaluate candidate responses using model-based supervision",
            operations=[
                "supervise_reasoning",
                "validate_output",
                "supervise_candidates",
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
            self.cognitive_generator = ModuleRegistry.get_module("cognitive_generator")
            # Internal scoring would be a separate module if needed

            self._modules_loaded = True
        except Exception as e:
            logger.debug(
                "Failed to load dependent modules for supervision_service",
                exc_info=True,
                extra={"module_name": "supervision_service", "error_type": type(e).__name__},
            )

    def execute(self, operation: str, params: Dict[str, Any]) -> Dict[str, Any]:
        """Execute an operation"""
        self._ensure_modules_loaded()

        match operation:
            case "supervise_reasoning":
                return self._supervise_reasoning(params)
            case "validate_output":
                return self._validate_output(params)
            case "supervise_candidates":
                return self._supervise_candidates(params)
            case _:
                raise InvalidParameterError("operation", str(operation), "Unknown operation for supervision_service")

    def _extract_text(self, result: Any) -> str:
        """Best-effort extraction of text from common generator result shapes."""
        if isinstance(result, str):
            return result
        if isinstance(result, dict):
            if isinstance(result.get("text"), str):
                return result["text"]
            res = result.get("result")
            if isinstance(res, dict):
                if isinstance(res.get("text"), str):
                    return res["text"]
                if isinstance(res.get("response"), str):
                    return res["response"]
                if isinstance(res.get("summary"), str):
                    return res["summary"]
            if isinstance(res, str):
                return res
        return ""

    def _clamp01(self, value: Any, default: float) -> float:
        try:
            f = float(value)
        except (TypeError, ValueError):
            return default
        if f < 0.0:
            return 0.0
        if f > 1.0:
            return 1.0
        return f

    def _heuristic_scores(self, output: str, query: str, context: str) -> Dict[str, float]:
        """
        Produce deterministic scores without a model.

        This is intentionally conservative and based on simple signals (length, overlap, consistency cues).
        """
        out = (output or "").strip()
        q = (query or "").strip()
        if not out:
            return {"correctness": 0.0, "reasoning_quality": 0.0, "consistency": 0.0, "overall": 0.0}

        # Length-based quality proxy (avoid rewarding verbosity too much).
        length = len(out)
        length_score = 0.2
        if length >= 200:
            length_score = 0.7
        elif length >= 80:
            length_score = 0.5
        elif length >= 30:
            length_score = 0.35

        # Query overlap proxy (basic relevance).
        q_words = {w for w in q.lower().split() if len(w) > 3}
        out_words = {w for w in out.lower().split() if len(w) > 3}
        overlap = len(q_words & out_words)
        overlap_score = min(1.0, overlap / 6.0) if q_words else 0.5

        # Consistency proxy: penalize obvious contradictions/hedging.
        lower = out.lower()
        contradiction_penalty = 0.0
        if "contradict" in lower or "inconsistent" in lower:
            contradiction_penalty = 0.2
        if "i don't know" in lower or "not sure" in lower:
            contradiction_penalty = max(contradiction_penalty, 0.15)

        correctness = max(0.0, overlap_score - contradiction_penalty * 0.5)
        reasoning_quality = max(0.0, length_score - contradiction_penalty * 0.4)
        consistency = max(0.0, 0.8 - contradiction_penalty)
        overall = (correctness + reasoning_quality + consistency) / 3.0
        return {
            "correctness": self._clamp01(correctness, 0.0),
            "reasoning_quality": self._clamp01(reasoning_quality, 0.0),
            "consistency": self._clamp01(consistency, 0.0),
            "overall": self._clamp01(overall, 0.0),
        }

    def _supervise_reasoning(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """Supervise reasoning output"""
        output = params.get("output", "")
        query = params.get("query", "")
        context = params.get("context", "")
        if output is None:
            output = ""
        if query is None:
            query = ""
        if context is None:
            context = ""
        if not isinstance(output, str):
            raise InvalidParameterError("output", str(type(output).__name__), "output must be a string")
        if not isinstance(query, str):
            raise InvalidParameterError("query", str(type(query).__name__), "query must be a string")
        if not isinstance(context, str):
            raise InvalidParameterError("context", str(type(context).__name__), "context must be a string")

        if not self.cognitive_generator:
            scores = self._heuristic_scores(output=output, query=query, context=context)
            logger.debug(
                "cognitive_generator unavailable; using heuristic supervision",
                extra={"module_name": "supervision_service"},
            )
            return {"success": True, "is_valid": True, "scores": scores, "method": "heuristic"}

        try:
            # Build supervision prompt
            supervision_prompt = f"""
            Evaluate the following reasoning output for correctness and quality.
            
            Query: {query}
            Context: {context}
            Output: {output}
            
            Rate the output on:
            1. Correctness (0.0-1.0)
            2. Reasoning quality (0.0-1.0)
            3. Consistency (0.0-1.0)
            
            Respond with JSON: {{"correctness": 0.0, "reasoning_quality": 0.0, "consistency": 0.0, "overall": 0.0}}
            """

            result = self.cognitive_generator.execute("generate_response", {
                "input": supervision_prompt,
                "context": "You are a supervisor evaluating reasoning quality.",
            })

            response_text = self._extract_text(result)
            parsed: Dict[str, Any] = {}
            try:
                # Allow models to include extra text around JSON; extract first {...}.
                start = response_text.find("{")
                end = response_text.rfind("}")
                if start != -1 and end != -1 and end > start:
                    parsed = json.loads(response_text[start : end + 1])
            except Exception:
                parsed = {}

            if not parsed:
                # Fall back to deterministic heuristic scoring if parsing fails
                scores = self._heuristic_scores(output=output, query=query, context=context)
                return {"success": True, "is_valid": True, "scores": scores, "method": "heuristic_fallback"}

            scores = {
                "correctness": self._clamp01(parsed.get("correctness"), 0.5),
                "reasoning_quality": self._clamp01(parsed.get("reasoning_quality"), 0.5),
                "consistency": self._clamp01(parsed.get("consistency"), 0.5),
                "overall": self._clamp01(parsed.get("overall"), 0.5),
            }
            # If overall missing, derive it.
            if "overall" not in parsed:
                scores["overall"] = self._clamp01(
                    (scores["correctness"] + scores["reasoning_quality"] + scores["consistency"]) / 3.0,
                    0.5,
                )

            return {"success": True, "is_valid": True, "scores": scores, "method": "model"}
        except Exception as e:
            logger.debug(
                "supervise_reasoning failed; using heuristic scores",
                exc_info=True,
                extra={"module_name": "supervision_service", "error_type": type(e).__name__},
            )
            scores = self._heuristic_scores(output=output, query=query, context=context)
            return {
                "success": True,
                "is_valid": True,
                "scores": scores,
                "method": "heuristic_fallback",
            }

    def _validate_output(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """Validate output (alias for supervise_reasoning)"""
        return self._supervise_reasoning(params)

    def _supervise_candidates(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """Supervise multiple candidate responses"""
        candidates = params.get("candidates", [])
        query = params.get("query", "")
        context = params.get("context")
        if candidates is None:
            candidates = []
        if query is None:
            query = ""
        if context is None:
            context = ""
        if not isinstance(candidates, list):
            raise InvalidParameterError("candidates", str(type(candidates).__name__), "candidates must be a list")
        if not isinstance(query, str):
            raise InvalidParameterError("query", str(type(query).__name__), "query must be a string")
        if not isinstance(context, str):
            raise InvalidParameterError("context", str(type(context).__name__), "context must be a string")

        if not candidates:
            return {
                "success": False,
                "error": "No candidates provided",
                "scores": [],
            }

        scores = []
        for candidate in candidates:
            if not isinstance(candidate, dict):
                continue
            candidate_id = candidate.get("id", "")
            candidate_text = candidate.get("text", "")

            supervision = self._supervise_reasoning({
                "output": candidate_text,
                "query": query,
                "context": context,
            })

            scores.append({
                "candidate_id": candidate_id,
                "model_score": supervision.get("scores", {}).get("overall", 0.5),
                "consistency_score": supervision.get("scores", {}).get("consistency", 0.5),
                "correctness_score": supervision.get("scores", {}).get("correctness", 0.5),
                "reasoning_quality_score": supervision.get("scores", {}).get("reasoning_quality", 0.5),
                "combined_score": supervision.get("scores", {}).get("overall", 0.5),
            })

        return {
            "success": True,
            "scores": scores,
        }

