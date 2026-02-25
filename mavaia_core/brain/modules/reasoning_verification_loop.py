from __future__ import annotations
"""
Reasoning Verification Loop
Verification loop that validates reasoning steps before they proceed
Converted from Swift ReasoningVerificationLoop.swift
"""

from typing import Any, Dict, List, Optional
import logging

from mavaia_core.brain.base_module import BaseBrainModule, ModuleMetadata
from mavaia_core.brain.registry import ModuleRegistry
from mavaia_core.brain.modules.cot_models import CoTStep
from mavaia_core.exceptions import InvalidParameterError

logger = logging.getLogger(__name__)


class StepVerificationResult:
    """Step verification result"""

    class VerificationType:
        NEURAL = "neural"
        SYMBOLIC = "symbolic"
        SYMBOLIC_OVERLAY = "symbolic_overlay"
        MAX_ATTEMPTS_REACHED = "max_attempts_reached"

    def __init__(
        self,
        is_valid: bool,
        confidence: float,
        verification_type: str,
        errors: List[str],
        warnings: List[str],
    ):
        self.is_valid = is_valid
        self.confidence = confidence
        self.verification_type = verification_type
        self.errors = errors
        self.warnings = warnings

    def to_dict(self) -> Dict[str, Any]:
        return {
            "is_valid": self.is_valid,
            "confidence": self.confidence,
            "verification_type": self.verification_type,
            "errors": self.errors,
            "warnings": self.warnings,
        }


class ReasoningVerificationLoopModule(BaseBrainModule):
    """Verification loop that validates reasoning steps"""

    def __init__(self):
        super().__init__()
        self.symbolic_validator = None
        self.symbolic_overlay = None
        self.python_brain = None
        self.verification_attempts: Dict[str, int] = {}
        self.max_verification_attempts = 3
        self._modules_loaded = False

    @property
    def metadata(self) -> ModuleMetadata:
        return ModuleMetadata(
            name="reasoning_verification_loop",
            version="1.0.0",
            description="Verification loop that validates reasoning steps before they proceed",
            operations=[
                "verify_step",
                "validate_reasoning",
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
            self.symbolic_validator = ModuleRegistry.get_module("symbolic_step_validator")
            self.symbolic_overlay = ModuleRegistry.get_module("symbolic_overlay_service")
            self.python_brain = ModuleRegistry.get_module("python_brain_service")

            self._modules_loaded = True
        except Exception as e:
            logger.debug(
                "Failed to load optional verification dependencies",
                exc_info=True,
                extra={"module_name": "reasoning_verification_loop", "error_type": type(e).__name__},
            )

    def execute(self, operation: str, params: Dict[str, Any]) -> Dict[str, Any]:
        """Execute an operation"""
        self._ensure_modules_loaded()

        if operation == "verify_step":
            return self._verify_step(params)
        elif operation == "validate_reasoning":
            return self._validate_reasoning(params)
        else:
            raise InvalidParameterError(
                parameter="operation",
                value=operation,
                reason="Unknown operation for reasoning_verification_loop",
            )

    def _verify_step(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """Verify a reasoning step with adaptive verification"""
        step_data = params.get("step", {})
        previous_steps_data = params.get("previous_steps", [])
        complexity = params.get("complexity", 0.5)
        confidence = params.get("confidence", 0.5)

        step = CoTStep.from_dict(step_data) if isinstance(step_data, dict) else step_data
        previous_steps = [
            CoTStep.from_dict(s) if isinstance(s, dict) else s
            for s in previous_steps_data
        ]

        step_id = step.id if hasattr(step, "id") else step_data.get("id", "")

        # Check verification attempt count
        attempt_count = self.verification_attempts.get(step_id, 0)
        if attempt_count >= self.max_verification_attempts:
            result = StepVerificationResult(
                is_valid=True,
                confidence=0.5,
                verification_type=StepVerificationResult.VerificationType.MAX_ATTEMPTS_REACHED,
                errors=[],
                warnings=["Max verification attempts reached"],
            )
            return {
                "success": True,
                "result": result.to_dict(),
            }

        self.verification_attempts[step_id] = attempt_count + 1

        # Determine verification strategy
        verification_strategy = self._determine_verification_strategy(complexity, confidence)

        all_errors: List[str] = []
        all_warnings: List[str] = []
        is_valid = True
        verification_type = StepVerificationResult.VerificationType.NEURAL

        # Step 1: Symbolic verification
        if verification_strategy.get("use_symbolic", False):
            try:
                if self.symbolic_validator:
                    symbolic_result = self.symbolic_validator.execute(
                        "validate_step",
                        {
                            "step": step_data,
                            "previous_steps": previous_steps_data,
                        }
                    )
                    symbolic_validation = symbolic_result.get("result", {})
                    if not symbolic_validation.get("is_valid", True):
                        is_valid = False
                        all_errors.extend(symbolic_validation.get("errors", []))
                        verification_type = StepVerificationResult.VerificationType.SYMBOLIC
                    all_warnings.extend(symbolic_validation.get("warnings", []))
            except Exception as e:
                logger.debug(
                    "Symbolic verification failed; continuing without symbolic validation",
                    exc_info=True,
                    extra={"module_name": "reasoning_verification_loop", "error_type": type(e).__name__},
                )
                all_warnings.append("Symbolic verification unavailable")

        # Step 2: Neural validation
        if verification_strategy.get("use_neural", True):
            neural_validation = self._validate_neurally(step, previous_steps, confidence)
            if not neural_validation.get("is_valid", True):
                is_valid = False
                all_errors.extend(neural_validation.get("errors", []))
                verification_type = StepVerificationResult.VerificationType.NEURAL
            all_warnings.extend(neural_validation.get("warnings", []))

        # Step 3: Consistency check
        if previous_steps:
            consistency_check = self._check_step_consistency(step, previous_steps)
            if not consistency_check.get("is_consistent", True):
                is_valid = False
                all_errors.append(f"Inconsistent with previous steps: {consistency_check.get('error', 'Unknown')}")

        # Step 4: Symbolic overlay veto check
        if verification_strategy.get("use_symbolic_overlay", False):
            try:
                if self.symbolic_overlay:
                    veto_result = self.symbolic_overlay.execute(
                        "should_veto_step",
                        {
                            "step": step_data,
                            "previous_steps": previous_steps_data,
                        }
                    )
                    veto_decision = veto_result.get("result", {})
                    if veto_decision.get("should_veto", False):
                        is_valid = False
                        reason = veto_decision.get("reason", "Unknown")
                        all_errors.append(f"Step vetoed by symbolic overlay: {reason}")
                        verification_type = StepVerificationResult.VerificationType.SYMBOLIC_OVERLAY
            except Exception:
                all_warnings.append("Symbolic overlay check unavailable")

        # Calculate final confidence
        final_confidence = self._calculate_verification_confidence(
            is_valid, all_errors, all_warnings, confidence, verification_type
        )

        # Clean up verification attempts if step passed
        if is_valid:
            self.verification_attempts.pop(step_id, None)

        result = StepVerificationResult(
            is_valid=is_valid,
            confidence=final_confidence,
            verification_type=verification_type,
            errors=all_errors,
            warnings=all_warnings,
        )

        return {
            "success": True,
            "result": result.to_dict(),
        }

    def _validate_reasoning(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """Validate reasoning (alias for verify_step)"""
        return self._verify_step(params)

    def _determine_verification_strategy(self, complexity: float, confidence: float) -> Dict[str, bool]:
        """Determine verification strategy based on complexity and confidence"""
        # High complexity or low confidence -> use symbolic verification
        use_symbolic = complexity > 0.7 or confidence < 0.6
        # Always use neural validation
        use_neural = True
        # Use symbolic overlay for high complexity
        use_symbolic_overlay = complexity > 0.8

        return {
            "use_symbolic": use_symbolic,
            "use_neural": use_neural,
            "use_symbolic_overlay": use_symbolic_overlay,
        }

    def _validate_neurally(
        self,
        step,
        previous_steps: List,
        confidence: float,
    ) -> Dict[str, Any]:
        """Neural validation (confidence-based checks)"""
        errors: List[str] = []
        warnings: List[str] = []

        step_text = (step.reasoning if hasattr(step, "reasoning") and step.reasoning else step.prompt if hasattr(step, "prompt") else "")

        # Low confidence -> warning
        if confidence < 0.5:
            warnings.append("Low confidence in step")

        # Check for empty reasoning
        if not step_text.strip():
            errors.append("Empty reasoning step")

        return {
            "is_valid": len(errors) == 0,
            "errors": errors,
            "warnings": warnings,
        }

    def _check_step_consistency(self, step, previous_steps: List) -> Dict[str, Any]:
        """Check step consistency with previous steps"""
        if not previous_steps:
            return {"is_consistent": True, "error": None}

        step_text = (step.reasoning if hasattr(step, "reasoning") and step.reasoning else step.prompt if hasattr(step, "prompt") else "").lower()

        # Simple consistency check: check for contradictory keywords
        previous_texts = [
            (s.reasoning if hasattr(s, "reasoning") and s.reasoning else s.prompt if hasattr(s, "prompt") else "").lower()
            for s in previous_steps
        ]

        # Check for contradictions (simple heuristic)
        contradictions = [
            ("yes", "no"),
            ("true", "false"),
            ("correct", "incorrect"),
        ]

        for prev_text in previous_texts:
            for pos, neg in contradictions:
                if pos in prev_text and neg in step_text:
                    return {
                        "is_consistent": False,
                        "error": f"Contradiction detected: {pos} vs {neg}",
                    }
                if neg in prev_text and pos in step_text:
                    return {
                        "is_consistent": False,
                        "error": f"Contradiction detected: {neg} vs {pos}",
                    }

        return {"is_consistent": True, "error": None}

    def _calculate_verification_confidence(
        self,
        is_valid: bool,
        errors: List[str],
        warnings: List[str],
        base_confidence: float,
        verification_type: str,
    ) -> float:
        """Calculate verification confidence"""
        if not is_valid:
            return 0.0

        # Reduce confidence based on errors and warnings
        penalty = len(errors) * 0.2 + len(warnings) * 0.1
        confidence = base_confidence - penalty

        # Adjust based on verification type
        if verification_type == StepVerificationResult.VerificationType.SYMBOLIC:
            confidence += 0.1  # Symbolic verification is more reliable
        elif verification_type == StepVerificationResult.VerificationType.SYMBOLIC_OVERLAY:
            confidence += 0.15  # Symbolic overlay is most reliable

        return max(0.0, min(1.0, confidence))
