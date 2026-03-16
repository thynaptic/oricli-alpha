from __future__ import annotations
"""
Step Safety Filter
Safety-aware step filtering that evaluates each reasoning step for safety issues
Converted from Swift StepSafetyFilter.swift
"""

from typing import Any, Dict, List, Optional
import time
import logging

from oricli_core.brain.base_module import BaseBrainModule, ModuleMetadata
from oricli_core.brain.registry import ModuleRegistry
from oricli_core.exceptions import InvalidParameterError

# Lazy imports to avoid timeout during module discovery
CoTStep = None
ToTThoughtNode = None
MCTSNode = None

logger = logging.getLogger(__name__)

def _lazy_import_safety_models():
    """Lazy import safety models only when needed"""
    global CoTStep, ToTThoughtNode, MCTSNode
    if CoTStep is None:
        try:
            from cot_models import CoTStep as CS
            from tot_models import ToTThoughtNode as TTTN
            from mcts_models import MCTSNode as MN
            CoTStep = CS
            ToTThoughtNode = TTTN
            MCTSNode = MN
        except ImportError:
            pass


class StepSafetyCheck:
    """Step safety check result"""

    def __init__(self, step_id: str, timestamp: float, flags: List[str], blocked: bool):
        self.step_id = step_id
        self.timestamp = timestamp
        self.flags = flags
        self.blocked = blocked


class StepSafetyResult:
    """Step safety filtering result"""

    def __init__(
        self,
        step_id: str,
        is_safe: bool,
        safety_flags: List[str],
        confidence: float,
    ):
        self.step_id = step_id
        self.is_safe = is_safe
        self.safety_flags = safety_flags
        self.confidence = confidence

    def to_dict(self) -> Dict[str, Any]:
        return {
            "step_id": self.step_id,
            "is_safe": self.is_safe,
            "safety_flags": self.safety_flags,
            "confidence": self.confidence,
        }


class DriftCheck:
    """Drift detection result"""

    def __init__(self, has_drift: bool, severity: float, drift_reason: Optional[str]):
        self.has_drift = has_drift
        self.severity = severity
        self.drift_reason = drift_reason


class StepSafetyFilterModule(BaseBrainModule):
    """Safety-aware step filtering service"""

    def __init__(self):
        super().__init__()
        self.safety_framework = None
        self.step_history: Dict[str, List[StepSafetyCheck]] = {}
        self.max_history_size = 10
        self._modules_loaded = False

    @property
    def metadata(self) -> ModuleMetadata:
        return ModuleMetadata(
            name="step_safety_filter",
            version="1.0.0",
            description="Safety-aware step filtering that evaluates each reasoning step for safety issues",
            operations=[
                "filter_step",
                "filter_tot_node",
                "filter_mcts_node",
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
            self.safety_framework = ModuleRegistry.get_module("safety_framework", auto_discover=True, wait_timeout=1.0)

            self._modules_loaded = True
        except Exception as e:
            logger.debug(
                "Failed to load optional dependency modules for step_safety_filter",
                exc_info=True,
                extra={"module_name": "step_safety_filter", "error_type": type(e).__name__},
            )

    def execute(self, operation: str, params: Dict[str, Any]) -> Dict[str, Any]:
        """Execute an operation"""
        _lazy_import_safety_models()
        self._ensure_modules_loaded()

        if operation == "filter_step":
            return self._filter_step(params)
        elif operation == "filter_tot_node":
            return self._filter_tot_node(params)
        elif operation == "filter_mcts_node":
            return self._filter_mcts_node(params)
        else:
            raise InvalidParameterError(
                parameter="operation",
                value=operation,
                reason="Unknown operation for step_safety_filter",
            )

    def _filter_step(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """Filter a reasoning step for safety issues"""
        step_data = params.get("step", {})
        previous_steps_data = params.get("previous_steps", [])
        session_id = params.get("session_id", "default")

        step = CoTStep.from_dict(step_data) if isinstance(step_data, dict) else step_data
        previous_steps = [
            CoTStep.from_dict(s) if isinstance(s, dict) else s
            for s in previous_steps_data
        ]

        safety_flags: List[str] = []
        should_block = False

        # Check 1: Drift detection
        drift_check = self._detect_drift(step, previous_steps, session_id)
        if drift_check.has_drift:
            safety_flags.append(f"drift_detected:{drift_check.drift_reason or 'Unknown drift'}")
            if drift_check.severity > 0.7:
                should_block = True

        # Check 2: Emotional ambiguity detection
        emotional_check = self._detect_emotional_ambiguity(step)
        if emotional_check.get("has_ambiguity", False):
            safety_flags.append(f"emotional_ambiguity:{emotional_check.get('ambiguity_reason', 'Unknown ambiguity')}")
            if emotional_check.get("severity", 0.0) > 0.8:
                should_block = True

        # Check 3: Factual error detection
        factual_check = self._detect_factual_errors(step)
        if factual_check.get("has_errors", False):
            safety_flags.append(f"factual_error:{factual_check.get('error_reason', 'Unknown error')}")
            should_block = True  # Always block factual errors

        # Check 4: Safety framework integration
        safety_check = self._check_with_safety_framework(step)
        if not safety_check.get("is_safe", True):
            safety_flags.append(f"safety_framework_violation:{safety_check.get('violation_reason', 'Safety violation')}")
            should_block = True

        # Store check result in history
        check_result = StepSafetyCheck(
            step_id=step.id if hasattr(step, "id") else step_data.get("id", ""),
            timestamp=time.time(),
            flags=safety_flags,
            blocked=should_block,
        )

        history = self.step_history.get(session_id, [])
        history.append(check_result)
        if len(history) > self.max_history_size:
            history.pop(0)
        self.step_history[session_id] = history

        result = StepSafetyResult(
            step_id=step.id if hasattr(step, "id") else step_data.get("id", ""),
            is_safe=not should_block,
            safety_flags=safety_flags,
            confidence=self._calculate_safety_confidence(safety_flags, should_block),
        )

        return {
            "success": True,
            "result": result.to_dict(),
        }

    def _filter_tot_node(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """Filter a ToT node"""
        node_data = params.get("node", {})
        previous_nodes_data = params.get("previous_nodes", [])
        session_id = params.get("session_id", "default")

        # Convert to CoT step
        step_data = {
            "id": node_data.get("id", ""),
            "prompt": node_data.get("thought", ""),
            "reasoning": node_data.get("thought", ""),
            "intermediate_state": node_data.get("state", {}),
            "confidence": node_data.get("evaluation_score", 0.5),
        }

        previous_steps = [
            {
                "id": n.get("id", ""),
                "prompt": n.get("thought", ""),
                "reasoning": n.get("thought", ""),
                "intermediate_state": n.get("state", {}),
                "confidence": n.get("evaluation_score", 0.5),
            }
            for n in previous_nodes_data
        ]

        return self._filter_step({
            "step": step_data,
            "previous_steps": previous_steps,
            "session_id": session_id,
        })

    def _filter_mcts_node(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """Filter an MCTS node"""
        node_data = params.get("node", {})
        previous_nodes_data = params.get("previous_nodes", [])
        session_id = params.get("session_id", "default")

        # Extract ToT node from MCTS node
        tot_node = node_data.get("tot_node", node_data)
        previous_tot_nodes = [n.get("tot_node", n) for n in previous_nodes_data]

        return self._filter_tot_node({
            "node": tot_node,
            "previous_nodes": previous_tot_nodes,
            "session_id": session_id,
        })

    def _detect_drift(
        self,
        step,
        previous_steps: List,
        session_id: str,
    ) -> DriftCheck:
        """Detect drift in reasoning"""
        if not previous_steps:
            return DriftCheck(has_drift=False, severity=0.0, drift_reason=None)

        step_text = (step.reasoning if hasattr(step, "reasoning") and step.reasoning else step.prompt if hasattr(step, "prompt") else "").lower()

        # Simple drift detection: check if step text is very different from previous steps
        previous_texts = [
            (s.reasoning if hasattr(s, "reasoning") and s.reasoning else s.prompt if hasattr(s, "prompt") else "").lower()
            for s in previous_steps
        ]

        # Calculate similarity (simple word overlap)
        step_words = set(step_text.split())
        previous_words = set()
        for pt in previous_texts:
            previous_words.update(pt.split())

        if not previous_words:
            return DriftCheck(has_drift=False, severity=0.0, drift_reason=None)

        overlap = len(step_words & previous_words) / max(len(step_words), 1)
        similarity = overlap

        if similarity < 0.3:  # Low similarity indicates drift
            severity = 1.0 - similarity
            return DriftCheck(
                has_drift=True,
                severity=severity,
                drift_reason="Low similarity with previous steps",
            )

        return DriftCheck(has_drift=False, severity=0.0, drift_reason=None)

    def _detect_emotional_ambiguity(self, step) -> Dict[str, Any]:
        """Detect emotional ambiguity in step"""
        step_text = (step.reasoning if hasattr(step, "reasoning") and step.reasoning else step.prompt if hasattr(step, "prompt") else "").lower()

        # Simple heuristic: check for conflicting emotional words
        positive_words = ["good", "great", "excellent", "happy", "positive", "success"]
        negative_words = ["bad", "terrible", "awful", "sad", "negative", "failure"]

        has_positive = any(word in step_text for word in positive_words)
        has_negative = any(word in step_text for word in negative_words)

        if has_positive and has_negative:
            return {
                "has_ambiguity": True,
                "severity": 0.7,
                "ambiguity_reason": "Conflicting emotional signals",
            }

        return {"has_ambiguity": False, "severity": 0.0, "ambiguity_reason": None}

    def _detect_factual_errors(self, step) -> Dict[str, Any]:
        """Detect factual errors in step"""
        step_text = (step.reasoning if hasattr(step, "reasoning") and step.reasoning else step.prompt if hasattr(step, "prompt") else "").lower()

        # Simple heuristic: check for obviously false statements
        false_patterns = [
            "the earth is flat",
            "2 + 2 = 5",
            "water is not h2o",
        ]

        for pattern in false_patterns:
            if pattern in step_text:
                return {
                    "has_errors": True,
                    "error_reason": f"Contains false statement: {pattern}",
                }

        return {"has_errors": False, "error_reason": None}

    def _check_with_safety_framework(self, step) -> Dict[str, Any]:
        """Check step with safety framework"""
        if not self.safety_framework:
            return {"is_safe": True, "violation_reason": None}

        step_text = (step.reasoning if hasattr(step, "reasoning") and step.reasoning else step.prompt if hasattr(step, "prompt") else "")

        try:
            result = self.safety_framework.execute(
                "check_content",
                {"content": step_text}
            )
            is_safe = result.get("result", {}).get("is_safe", True)
            violation_reason = result.get("result", {}).get("violation_reason")
            return {
                "is_safe": is_safe,
                "violation_reason": violation_reason,
            }
        except Exception:
            return {"is_safe": True, "violation_reason": None}

    def _calculate_safety_confidence(self, flags: List[str], should_block: bool) -> float:
        """Calculate safety confidence"""
        if should_block:
            return 0.0

        if not flags:
            return 1.0

        # Reduce confidence based on number of flags
        base_confidence = 1.0
        penalty = len(flags) * 0.1
        return max(0.0, base_confidence - penalty)
