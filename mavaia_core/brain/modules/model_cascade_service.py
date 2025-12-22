"""
Model Cascade Service
Model cascading service for sequential model usage
Converted from Swift ModelCascadeService.swift
"""

from typing import Any, Dict, List, Optional
import sys
import time
from pathlib import Path

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent))

from mavaia_core.brain.base_module import BaseBrainModule, ModuleMetadata


class CascadeAttempt:
    """Single cascade attempt result"""

    def __init__(
        self,
        model: str,
        answer: Optional[str],
        confidence: float,
        success: bool,
        error: Optional[str] = None,
    ):
        self.model = model
        self.answer = answer
        self.confidence = confidence
        self.success = success
        self.error = error

    def to_dict(self) -> Dict[str, Any]:
        return {
            "model": self.model,
            "answer": self.answer,
            "confidence": self.confidence,
            "success": self.success,
            "error": self.error,
        }


class CascadeResult:
    """Final cascade result"""

    def __init__(
        self,
        final_answer: str,
        final_model: str,
        final_confidence: float,
        attempts: List[CascadeAttempt],
        cascade_depth: int,
    ):
        self.final_answer = final_answer
        self.final_model = final_model
        self.final_confidence = final_confidence
        self.attempts = attempts
        self.cascade_depth = cascade_depth

    def to_dict(self) -> Dict[str, Any]:
        return {
            "final_answer": self.final_answer,
            "final_model": self.final_model,
            "final_confidence": self.final_confidence,
            "attempts": [a.to_dict() for a in self.attempts],
            "cascade_depth": self.cascade_depth,
        }


class ModelCascadeServiceModule(BaseBrainModule):
    """Model cascading service for sequential model usage"""

    def __init__(self):
        self.cognitive_generator = None
        self.cascade_depth: Dict[str, int] = {}
        self.max_cascade_depth = 3
        self._modules_loaded = False

    @property
    def metadata(self) -> ModuleMetadata:
        return ModuleMetadata(
            name="model_cascade_service",
            version="1.0.0",
            description="Model cascading service for sequential model usage",
            operations=[
                "cascade",
                "cascade_models",
                "fallback_chain",
                "should_trigger_cascade",
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

            self.cognitive_generator = ModuleRegistry.get_module("cognitive_generator")

            self._modules_loaded = True
        except Exception as e:
            print(f"Error loading modules: {e}")

    def execute(self, operation: str, params: Dict[str, Any]) -> Dict[str, Any]:
        """Execute an operation"""
        self._ensure_modules_loaded()

        if operation == "cascade":
            return self._cascade(params)
        elif operation == "cascade_models":
            return self._cascade_models(params)
        elif operation == "fallback_chain":
            return self._fallback_chain(params)
        elif operation == "should_trigger_cascade":
            return self._should_trigger_cascade(params)
        else:
            raise ValueError(f"Unknown operation: {operation}")

    def _cascade(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """Execute model cascade"""
        query = params.get("query", "")
        context = params.get("context")
        initial_model = params.get("initial_model", "cognitive_generator")
        session_id = params.get("session_id", "default")

        # Check cascade depth
        current_depth = self.cascade_depth.get(session_id, 0)
        if current_depth >= self.max_cascade_depth:
            return {
                "success": False,
                "error": "Max cascade depth reached",
            }

        self.cascade_depth[session_id] = current_depth + 1

        # Simplified cascade: retry with cognitive generator up to 3 times
        max_attempts = 3
        attempts: List[CascadeAttempt] = []
        final_answer: Optional[str] = None
        final_model: Optional[str] = None
        final_confidence = 0.0

        if not self.cognitive_generator:
            return {
                "success": False,
                "error": "Cognitive generator not available",
            }

        # Try up to maxAttempts times with cognitive generator
        for index in range(max_attempts):
            try:
                response_result = self.cognitive_generator.execute(
                    "generate_response",
                    {
                        "input": query,
                        "context": context or "",
                        "persona": "mavaia",
                    }
                )

                answer = response_result.get("result", {}).get("response", "")
                confidence = self._extract_confidence(answer)

                attempt = CascadeAttempt(
                    model="cognitive_generator",
                    answer=answer,
                    confidence=confidence,
                    success=True,
                    error=None,
                )
                attempts.append(attempt)

                # Check if this result is satisfactory
                if self._should_accept_result(confidence, index, max_attempts):
                    final_answer = answer
                    final_model = "cognitive_generator"
                    final_confidence = confidence
                    break
            except Exception as e:
                attempt = CascadeAttempt(
                    model="cognitive_generator",
                    answer=None,
                    confidence=0.0,
                    success=False,
                    error=str(e),
                )
                attempts.append(attempt)
                continue

        # If no satisfactory result, use best attempt
        if final_answer is None:
            successful_attempts = [a for a in attempts if a.success]
            if successful_attempts:
                best_attempt = max(successful_attempts, key=lambda a: a.confidence)
                final_answer = best_attempt.answer
                final_model = best_attempt.model
                final_confidence = best_attempt.confidence
            else:
                return {
                    "success": False,
                    "error": "All cascade attempts failed",
                }

        # Clean up cascade depth
        if session_id in self.cascade_depth:
            depth = self.cascade_depth[session_id]
            if depth > 0:
                self.cascade_depth[session_id] = depth - 1

        result = CascadeResult(
            final_answer=final_answer,
            final_model=final_model,
            final_confidence=final_confidence,
            attempts=attempts,
            cascade_depth=current_depth + 1,
        )

        return {
            "success": True,
            "result": result.to_dict(),
        }

    def _cascade_models(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """Cascade models (alias for cascade)"""
        return self._cascade(params)

    def _fallback_chain(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """Get fallback chain"""
        # Return fallback chain (cognitive generator only)
        return {
            "success": True,
            "result": {
                "chain": ["cognitive_generator"],
            },
        }

    def _should_trigger_cascade(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """Determine if cascade should be triggered"""
        confidence = params.get("confidence")
        verification_failed = params.get("verification_failed", False)
        complexity = params.get("complexity", 0.5)

        # Trigger on low confidence
        if confidence is not None and confidence < 0.6:
            return {
                "success": True,
                "result": {"should_trigger": True, "reason": "low_confidence"},
            }

        # Trigger on verification failure
        if verification_failed:
            return {
                "success": True,
                "result": {"should_trigger": True, "reason": "verification_failed"},
            }

        # Trigger on high complexity
        if complexity > 0.8:
            return {
                "success": True,
                "result": {"should_trigger": True, "reason": "high_complexity"},
            }

        return {
            "success": True,
            "result": {"should_trigger": False, "reason": "none"},
        }

    def _extract_confidence(self, answer: str) -> float:
        """Extract confidence from answer (heuristic)"""
        # Simple heuristic: longer answers might indicate higher confidence
        # In real implementation, would use more sophisticated analysis
        if len(answer) > 100:
            return 0.7
        elif len(answer) > 50:
            return 0.6
        else:
            return 0.5

    def _should_accept_result(self, confidence: float, attempt_index: int, total_attempts: int) -> bool:
        """Determine if result should be accepted"""
        # Accept if confidence is high enough
        if confidence >= 0.7:
            return True

        # Accept on last attempt regardless
        if attempt_index >= total_attempts - 1:
            return True

        return False

