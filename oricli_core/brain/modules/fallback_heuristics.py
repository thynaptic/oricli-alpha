from __future__ import annotations
"""
Fallback Heuristics Module - Intelligent fallback chain selection
Handles confidence-based fallback triggers, context-aware fallback strategies, and fallback chain management
"""

from typing import Dict, Any, List, Optional, Tuple
import json
from pathlib import Path
import logging

from oricli_core.brain.base_module import BaseBrainModule, ModuleMetadata
from oricli_core.exceptions import InvalidParameterError

logger = logging.getLogger(__name__)


class FallbackHeuristicsModule(BaseBrainModule):
    """Intelligent fallback chain selection and management"""

    def __init__(self):
        super().__init__()
        self.config = None
        self.fallback_chains = {}
        self.fallback_strategies = {}
        self._load_config()

    @property
    def metadata(self) -> ModuleMetadata:
        return ModuleMetadata(
            name="fallback_heuristics",
            version="1.0.0",
            description="Intelligent fallback heuristics: chain selection, confidence triggers, context-aware strategies",
            operations=[
                "select_fallback_strategy",
                "should_fallback",
                "get_fallback_chain",
                "evaluate_fallback_trigger",
                "get_next_fallback_step",
            ],
            dependencies=[],
            model_required=False,
        )

    def initialize(self) -> bool:
        """Initialize the module"""
        return True

    def _load_config(self):
        """Load fallback heuristics configuration"""
        config_path = Path(__file__).parent / "fallback_heuristics_config.json"
        try:
            if config_path.exists():
                with open(config_path, "r", encoding="utf-8") as f:
                    self.config = json.load(f)
                    self.fallback_chains = self.config.get("fallback_chains", {})
                    self.fallback_strategies = self.config.get("strategies", {})
            else:
                # Default config
                self.fallback_chains = {
                    "low_confidence": [
                        "personality_response",
                        "conversational_defaults",
                        "generic_response",
                    ],
                    "high_confidence": ["current_method", "personality_response"],
                    "error": [
                        "conversational_defaults",
                        "apology_response",
                        "clarification_request",
                    ],
                    "timeout": [
                        "simple_response",
                        "acknowledgment",
                        "clarification_request",
                    ],
                }
                self.fallback_strategies = {
                    "confidence_threshold": 0.5,
                    "max_fallback_depth": 3,
                    "context_aware": True,
                }
        except Exception as e:
            logger.warning(
                "Failed to load fallback_heuristics config; using empty defaults",
                exc_info=True,
                extra={"module_name": "fallback_heuristics", "error_type": type(e).__name__},
            )
            self.fallback_chains = {}
            self.fallback_strategies = {}

    def execute(self, operation: str, params: Dict[str, Any]) -> Dict[str, Any]:
        """Execute a fallback heuristics operation"""
        if operation == "select_fallback_strategy":
            confidence = params.get("confidence", 0.5)
            error_type = params.get("error_type", "")
            context = params.get("context", {})
            if error_type is None:
                error_type = ""
            if context is None:
                context = {}
            try:
                confidence_float = float(confidence)
            except (TypeError, ValueError):
                raise InvalidParameterError(
                    parameter="confidence",
                    value=str(confidence),
                    reason="confidence must be a number",
                )
            if not isinstance(error_type, str):
                raise InvalidParameterError(
                    parameter="error_type",
                    value=str(type(error_type).__name__),
                    reason="error_type must be a string",
                )
            if not isinstance(context, dict):
                raise InvalidParameterError(
                    parameter="context",
                    value=str(type(context).__name__),
                    reason="context must be a dict",
                )
            return self.select_fallback_strategy(confidence, error_type, context)
        elif operation == "should_fallback":
            confidence = params.get("confidence", 0.5)
            error_occurred = params.get("error_occurred", False)
            response_quality = params.get("response_quality", 0.5)
            try:
                float(confidence)
            except (TypeError, ValueError):
                raise InvalidParameterError("confidence", str(confidence), "confidence must be a number")
            if not isinstance(error_occurred, bool):
                raise InvalidParameterError(
                    parameter="error_occurred",
                    value=str(type(error_occurred).__name__),
                    reason="error_occurred must be a boolean",
                )
            try:
                float(response_quality)
            except (TypeError, ValueError):
                raise InvalidParameterError(
                    parameter="response_quality",
                    value=str(response_quality),
                    reason="response_quality must be a number",
                )
            return self.should_fallback(confidence, error_occurred, response_quality)
        elif operation == "get_fallback_chain":
            strategy = params.get("strategy", "")
            if strategy is None:
                strategy = ""
            if not isinstance(strategy, str):
                raise InvalidParameterError("strategy", str(type(strategy).__name__), "strategy must be a string")
            return self.get_fallback_chain(strategy)
        elif operation == "evaluate_fallback_trigger":
            trigger_type = params.get("trigger_type", "")
            context = params.get("context", {})
            if trigger_type is None:
                trigger_type = ""
            if context is None:
                context = {}
            if not isinstance(trigger_type, str):
                raise InvalidParameterError(
                    parameter="trigger_type",
                    value=str(type(trigger_type).__name__),
                    reason="trigger_type must be a string",
                )
            if not isinstance(context, dict):
                raise InvalidParameterError("context", str(type(context).__name__), "context must be a dict")
            return self.evaluate_fallback_trigger(trigger_type, context)
        elif operation == "get_next_fallback_step":
            current_step = params.get("current_step", "")
            chain = params.get("chain", [])
            attempts = params.get("attempts", 0)
            if current_step is None:
                current_step = ""
            if chain is None:
                chain = []
            if not isinstance(current_step, str):
                raise InvalidParameterError(
                    parameter="current_step",
                    value=str(type(current_step).__name__),
                    reason="current_step must be a string",
                )
            if not isinstance(chain, list):
                raise InvalidParameterError("chain", str(type(chain).__name__), "chain must be a list")
            try:
                attempts_int = int(attempts)
            except (TypeError, ValueError):
                raise InvalidParameterError("attempts", str(attempts), "attempts must be an integer")
            return self.get_next_fallback_step(current_step, chain, attempts)
        else:
            raise InvalidParameterError(
                parameter="operation",
                value=operation,
                reason="Unknown operation for fallback_heuristics",
            )

    def select_fallback_strategy(
        self, confidence: float, error_type: str = "", context: Dict[str, Any] = None
    ) -> Dict[str, Any]:
        """Select appropriate fallback strategy based on confidence and error type"""
        if context is None:
            context = {}

        strategy = "default"
        chain_name = "low_confidence"

        # Determine strategy based on error type
        if error_type:
            if "timeout" in error_type.lower() or "time" in error_type.lower():
                chain_name = "timeout"
                strategy = "timeout_recovery"
            elif "error" in error_type.lower() or "exception" in error_type.lower():
                chain_name = "error"
                strategy = "error_recovery"
            elif (
                "low_confidence" in error_type.lower()
                or "uncertain" in error_type.lower()
            ):
                chain_name = "low_confidence"
                strategy = "confidence_recovery"

        # Override based on confidence level
        threshold = self.fallback_strategies.get("confidence_threshold", 0.5)
        if confidence < threshold:
            chain_name = "low_confidence"
            strategy = "confidence_recovery"
        elif confidence >= 0.8:
            chain_name = "high_confidence"
            strategy = "maintain_quality"

        # Get fallback chain
        chain = self.fallback_chains.get(chain_name, [])

        # Consider context
        context_aware = self.fallback_strategies.get("context_aware", True)
        if context_aware and context:
            # Adjust strategy based on context
            if context.get("is_casual"):
                # Prefer personality_response for casual
                if "personality_response" not in chain:
                    chain.insert(0, "personality_response")
            elif context.get("requires_formality"):
                # Prefer conversational_defaults for formal
                if "conversational_defaults" not in chain:
                    chain.insert(0, "conversational_defaults")

        return {
            "strategy": strategy,
            "chain_name": chain_name,
            "fallback_chain": chain,
            "confidence": confidence,
            "error_type": error_type,
            "context_aware": context_aware,
        }

    def should_fallback(
        self,
        confidence: float,
        error_occurred: bool = False,
        response_quality: float = 0.5,
    ) -> Dict[str, Any]:
        """Determine if fallback should be triggered"""
        threshold = self.fallback_strategies.get("confidence_threshold", 0.5)

        # Always fallback on error
        if error_occurred:
            return {
                "should_fallback": True,
                "reason": "error_occurred",
                "confidence": confidence,
                "priority": "high",
            }

        # Fallback on low confidence
        if confidence < threshold:
            return {
                "should_fallback": True,
                "reason": "low_confidence",
                "confidence": confidence,
                "priority": "medium",
            }

        # Fallback on low response quality
        if response_quality < 0.4:
            return {
                "should_fallback": True,
                "reason": "low_quality",
                "confidence": confidence,
                "response_quality": response_quality,
                "priority": "medium",
            }

        # Check if confidence is borderline
        if threshold <= confidence < threshold + 0.1:
            return {
                "should_fallback": False,
                "reason": "borderline_confidence",
                "confidence": confidence,
                "priority": "low",
                "recommendation": "monitor",
            }

        return {
            "should_fallback": False,
            "reason": "sufficient_quality",
            "confidence": confidence,
            "priority": "low",
        }

    def get_fallback_chain(self, strategy: str) -> Dict[str, Any]:
        """Get fallback chain for a specific strategy"""
        # Map strategy to chain name
        strategy_to_chain = {
            "confidence_recovery": "low_confidence",
            "error_recovery": "error",
            "timeout_recovery": "timeout",
            "maintain_quality": "high_confidence",
        }

        chain_name = strategy_to_chain.get(strategy, strategy)
        chain = self.fallback_chains.get(chain_name, [])

        if not chain:
            # Default chain
            chain = [
                "personality_response",
                "conversational_defaults",
                "generic_response",
            ]

        max_depth = self.fallback_strategies.get("max_fallback_depth", 3)
        chain = chain[:max_depth]

        return {
            "strategy": strategy,
            "chain_name": chain_name,
            "fallback_chain": chain,
            "max_depth": max_depth,
            "steps_remaining": len(chain),
        }

    def evaluate_fallback_trigger(
        self, trigger_type: str, context: Dict[str, Any] = None
    ) -> Dict[str, Any]:
        """Evaluate a specific fallback trigger"""
        if context is None:
            context = {}

        trigger_evaluation = {
            "trigger_type": trigger_type,
            "should_trigger": False,
            "priority": "low",
            "recommended_strategy": "default",
        }

        # Evaluate based on trigger type
        if trigger_type == "low_confidence":
            confidence = context.get("confidence", 0.5)
            threshold = self.fallback_strategies.get("confidence_threshold", 0.5)
            trigger_evaluation["should_trigger"] = confidence < threshold
            trigger_evaluation["priority"] = "medium"
            trigger_evaluation["recommended_strategy"] = "confidence_recovery"

        elif trigger_type == "error":
            error_occurred = context.get("error_occurred", False)
            trigger_evaluation["should_trigger"] = error_occurred
            trigger_evaluation["priority"] = "high"
            trigger_evaluation["recommended_strategy"] = "error_recovery"

        elif trigger_type == "timeout":
            timeout_occurred = context.get("timeout", False)
            trigger_evaluation["should_trigger"] = timeout_occurred
            trigger_evaluation["priority"] = "medium"
            trigger_evaluation["recommended_strategy"] = "timeout_recovery"

        elif trigger_type == "empty_response":
            response_empty = context.get("response_empty", False)
            trigger_evaluation["should_trigger"] = response_empty
            trigger_evaluation["priority"] = "high"
            trigger_evaluation["recommended_strategy"] = "error_recovery"

        elif trigger_type == "inappropriate_response":
            inappropriate = context.get("inappropriate", False)
            trigger_evaluation["should_trigger"] = inappropriate
            trigger_evaluation["priority"] = "high"
            trigger_evaluation["recommended_strategy"] = "error_recovery"

        return trigger_evaluation

    def get_next_fallback_step(
        self, current_step: str, chain: List[str], attempts: int = 0
    ) -> Dict[str, Any]:
        """Get the next step in the fallback chain"""
        max_depth = self.fallback_strategies.get("max_fallback_depth", 3)

        if not chain:
            return {
                "next_step": None,
                "has_next": False,
                "attempts": attempts,
                "max_reached": True,
            }

        # Find current step index
        try:
            current_index = chain.index(current_step) if current_step in chain else -1
        except ValueError:
            current_index = -1

        # Check if we've exceeded max depth
        if attempts >= max_depth:
            return {
                "next_step": None,
                "has_next": False,
                "attempts": attempts,
                "max_reached": True,
                "message": "Maximum fallback depth reached",
            }

        # Get next step
        if current_index >= 0 and current_index < len(chain) - 1:
            next_step = chain[current_index + 1]
            return {
                "next_step": next_step,
                "has_next": True,
                "attempts": attempts + 1,
                "remaining_steps": len(chain) - current_index - 1,
                "max_reached": False,
            }
        elif current_index == -1:
            # Current step not in chain, start from beginning
            return {
                "next_step": chain[0] if chain else None,
                "has_next": len(chain) > 0,
                "attempts": attempts + 1,
                "remaining_steps": len(chain),
                "max_reached": False,
            }
        else:
            # Reached end of chain
            return {
                "next_step": None,
                "has_next": False,
                "attempts": attempts,
                "remaining_steps": 0,
                "max_reached": True,
                "message": "End of fallback chain reached",
            }

    def validate_params(self, operation: str, params: Dict[str, Any]) -> bool:
        """Validate parameters for operations"""
        if operation == "select_fallback_strategy":
            return "confidence" in params
        elif operation == "should_fallback":
            return "confidence" in params
        elif operation == "get_fallback_chain":
            return "strategy" in params
        elif operation == "evaluate_fallback_trigger":
            return "trigger_type" in params
        elif operation == "get_next_fallback_step":
            return "chain" in params
        return True
