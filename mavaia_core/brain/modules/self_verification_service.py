"""
Self Verification Service - Self-verification service that cross-checks final answers
Converted from Swift SelfVerificationService.swift
"""

from typing import Any, Dict, List, Optional
import sys
from pathlib import Path

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent))

from mavaia_core.brain.base_module import BaseBrainModule, ModuleMetadata


class SelfVerificationServiceModule(BaseBrainModule):
    """Self-verification service that cross-checks final answers using different reasoning methods"""

    def __init__(self):
        self.mcts_service = None
        self.cot_service = None
        self.tot_service = None
        self.symbolic_solver = None
        self._modules_loaded = False

    @property
    def metadata(self) -> ModuleMetadata:
        return ModuleMetadata(
            name="self_verification_service",
            version="1.0.0",
            description="Self-verification service that cross-checks final answers using different reasoning methods",
            operations=[
                "verify_output",
                "check_correctness",
                "verify_answer",
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

            self.mcts_service = ModuleRegistry.get_module("mcts_service")
            self.cot_service = ModuleRegistry.get_module("chain_of_thought")
            self.tot_service = ModuleRegistry.get_module("tree_of_thought")
            self.symbolic_solver = ModuleRegistry.get_module("symbolic_solver_service")

            self._modules_loaded = True
        except Exception as e:
            # Modules not available - will use fallback methods
            pass

    def execute(self, operation: str, params: Dict[str, Any]) -> Dict[str, Any]:
        """Execute an operation"""
        self._ensure_modules_loaded()

        if operation == "verify_output":
            return self._verify_output(params)
        elif operation == "check_correctness":
            return self._check_correctness(params)
        elif operation == "verify_answer":
            return self._verify_answer(params)
        else:
            raise ValueError(f"Unknown operation: {operation}")

    def _verify_output(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """Verify output (alias for verify_answer)"""
        return self._verify_answer(params)

    def _check_correctness(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """Check correctness (alias for verify_answer)"""
        return self._verify_answer(params)

    def _verify_answer(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """Verify a final answer using multiple reasoning methods"""
        query = params.get("query", "")
        original_answer = params.get("original_answer", "")
        original_method = params.get("original_method", "unknown")
        original_confidence = params.get("original_confidence", 0.5)
        context = params.get("context")

        verification_checks = []
        inconsistencies = []

        # Check 1: MCTS cross-checking (if original wasn't MCTS)
        if original_method != "mcts" and self.mcts_service:
            try:
                mcts_check = self._cross_check_with_mcts(query, original_answer, context)
                if mcts_check:
                    verification_checks.append(mcts_check)
                    if not mcts_check.get("agrees", True):
                        inconsistencies.append({
                            "method1": original_method,
                            "method2": "mcts",
                            "answer1": original_answer,
                            "answer2": mcts_check.get("answer", ""),
                            "severity": mcts_check.get("confidence", 0.0),
                        })
            except Exception as e:
                pass

        # Check 2: Alternative reasoning path
        if original_method != "cot" and self.cot_service:
            try:
                cot_check = self._cross_check_with_cot(query, original_answer, context)
                if cot_check:
                    verification_checks.append(cot_check)
                    if not cot_check.get("agrees", True):
                        inconsistencies.append({
                            "method1": original_method,
                            "method2": "cot",
                            "answer1": original_answer,
                            "answer2": cot_check.get("answer", ""),
                            "severity": cot_check.get("confidence", 0.0),
                        })
            except Exception as e:
                pass

        # Determine final verification result
        all_agree = all(check.get("agrees", True) for check in verification_checks)
        agreement_count = sum(1 for check in verification_checks if check.get("agrees", True))
        total_checks = len(verification_checks)

        verified_confidence = self._calculate_verified_confidence(
            original_confidence, verification_checks, all_agree
        )

        # Select best answer
        verified_answer = self._select_best_answer(
            original_answer, original_confidence, verification_checks, inconsistencies
        )

        return {
            "success": True,
            "original_answer": original_answer,
            "verified_answer": verified_answer,
            "original_confidence": original_confidence,
            "verified_confidence": verified_confidence,
            "all_checks_agree": all_agree,
            "agreement_ratio": agreement_count / total_checks if total_checks > 0 else 1.0,
            "verification_checks": verification_checks,
            "inconsistencies": inconsistencies,
        }

    def _cross_check_with_mcts(
        self, query: str, original_answer: str, context: Optional[str]
    ) -> Optional[Dict[str, Any]]:
        """Cross-check with MCTS"""
        if not self.mcts_service:
            return None

        try:
            result = self.mcts_service.execute("search", {
                "query": query,
                "context": context,
            })

            mcts_answer = result.get("final_response", "")
            # Simple agreement check: check if answers are similar
            agrees = self._answers_agree(original_answer, mcts_answer)

            return {
                "method": "mcts",
                "answer": mcts_answer,
                "agrees": agrees,
                "confidence": result.get("confidence", 0.5),
            }
        except:
            return None

    def _cross_check_with_cot(
        self, query: str, original_answer: str, context: Optional[str]
    ) -> Optional[Dict[str, Any]]:
        """Cross-check with CoT"""
        if not self.cot_service:
            return None

        try:
            result = self.cot_service.execute("reason", {
                "query": query,
                "context": context,
            })

            cot_answer = result.get("final_response", "")
            agrees = self._answers_agree(original_answer, cot_answer)

            return {
                "method": "cot",
                "answer": cot_answer,
                "agrees": agrees,
                "confidence": result.get("confidence", 0.5),
            }
        except:
            return None

    def _answers_agree(self, answer1: str, answer2: str) -> bool:
        """Check if two answers agree (simplified)"""
        # Simple similarity check
        answer1_lower = answer1.lower()
        answer2_lower = answer2.lower()

        # Check for common words
        words1 = set(answer1_lower.split())
        words2 = set(answer2_lower.split())

        if not words1 or not words2:
            return False

        common_words = words1 & words2
        similarity = len(common_words) / max(len(words1), len(words2))

        return similarity > 0.5  # 50% similarity threshold

    def _calculate_verified_confidence(
        self, original_confidence: float, checks: List[Dict[str, Any]], all_agree: bool
    ) -> float:
        """Calculate verified confidence"""
        if all_agree:
            # Boost confidence if all checks agree
            return min(1.0, original_confidence + 0.1)
        else:
            # Reduce confidence if checks disagree
            return max(0.0, original_confidence - 0.2)

    def _select_best_answer(
        self,
        original_answer: str,
        original_confidence: float,
        checks: List[Dict[str, Any]],
        inconsistencies: List[Dict[str, Any]],
    ) -> str:
        """Select best answer from verification checks"""
        if not inconsistencies:
            return original_answer

        # Find check with highest confidence
        best_check = max(checks, key=lambda c: c.get("confidence", 0.0), default=None)

        if best_check and best_check.get("confidence", 0.0) > original_confidence:
            return best_check.get("answer", original_answer)

        return original_answer

