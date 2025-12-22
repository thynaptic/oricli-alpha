"""
Model Routing Engine
Routing logic engine with confidence weighting, casual detection, and per-model cooldown/stickiness
Converted from Swift ModelRoutingEngine.swift
"""

from typing import Any, Dict, Optional
import logging
import sys
from pathlib import Path

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent))

from mavaia_core.brain.base_module import BaseBrainModule, ModuleMetadata
from mavaia_core.exceptions import InvalidParameterError

logger = logging.getLogger(__name__)

# Optional imports - models package may not be available
try:
    from models.model_tier_map_models import ModelTierMap
except ImportError:
    # Models not available - define minimal types
    ModelTierMap = None


class ModelRoutingDecision:
    """Model routing decision result"""

    def __init__(self, model: str, use_thinking: bool, is_casual: bool):
        self.model = model
        self.use_thinking = use_thinking
        self.is_casual = is_casual

    def to_dict(self) -> Dict[str, Any]:
        return {
            "model": self.model,
            "use_thinking": self.use_thinking,
            "is_casual": self.is_casual,
        }


class ModelRoutingEngineModule(BaseBrainModule):
    """Routing logic engine for model selection"""

    def __init__(self):
        self.cluster_model_cache: Dict[str, str] = {}
        self.model_cooldown: Dict[str, int] = {}
        self.cooldown_turns = 3
        self.casual_detector = None
        self._modules_loaded = False

    @property
    def metadata(self) -> ModuleMetadata:
        return ModuleMetadata(
            name="model_routing_engine",
            version="1.0.0",
            description="Routing logic engine with confidence weighting, casual detection, and per-model cooldown/stickiness",
            operations=[
                "select_model",
                "route_request",
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

            self.casual_detector = ModuleRegistry.get_module("casual_conversation_detector")

            self._modules_loaded = True
        except Exception as e:
            logger.warning(
                "Failed to load optional dependency modules for model_routing_engine",
                exc_info=True,
                extra={"module_name": "model_routing_engine", "error_type": type(e).__name__},
            )

    def execute(self, operation: str, params: Dict[str, Any]) -> Dict[str, Any]:
        """Execute an operation"""
        self._ensure_modules_loaded()

        if operation == "select_model":
            return self._select_model(params)
        elif operation == "route_request":
            return self._route_request(params)
        else:
            raise InvalidParameterError(
                parameter="operation",
                value=operation,
                reason="Unknown operation for model_routing_engine",
            )

    def _default_model(self) -> str:
        """Get default model even if ModelTierMap isn't available."""
        if ModelTierMap is None:
            return "cognitive_generator"
        return ModelTierMap.default_model()

    def _supports_thinking(self, model: str) -> bool:
        if ModelTierMap is None:
            return False
        return bool(ModelTierMap.supports_thinking(model))

    def _is_local_model(self, model: str) -> bool:
        if ModelTierMap is None:
            return True
        return bool(ModelTierMap.is_local_model(model))

    def _select_model(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """Select the best model for a given input"""
        input_text = params.get("input", "")
        intent_cluster = params.get("intent_cluster")
        confidence = params.get("confidence", 0.5)
        message_length = params.get("message_length", 0)
        is_research_mode = params.get("is_research_mode", False)
        retry_mode_active = params.get("retry_mode_active", False)
        previous_decision = params.get("previous_decision")
        is_creation_action = params.get("is_creation_action", False)

        if not isinstance(input_text, str):
            raise InvalidParameterError("input", str(type(input_text)), "input must be a string")
        if intent_cluster is not None and not isinstance(intent_cluster, str):
            raise InvalidParameterError("intent_cluster", str(type(intent_cluster)), "intent_cluster must be a string")
        try:
            confidence = float(confidence)
        except Exception as e:
            raise InvalidParameterError("confidence", str(confidence), "confidence must be a number") from e
        try:
            message_length = int(message_length)
        except Exception as e:
            raise InvalidParameterError("message_length", str(message_length), "message_length must be an int") from e

        if retry_mode_active and previous_decision:
            decision = ModelRoutingDecision(
                model=previous_decision.get("model", self._default_model()),
                use_thinking=previous_decision.get("use_thinking", False),
                is_casual=previous_decision.get("is_casual", False),
            )
            return {
                "success": True,
                "result": decision.to_dict(),
            }

        # 1. Research mode - use cognitive generator
        if is_research_mode:
            selected_model = self._default_model()
            use_thinking = self._supports_thinking(selected_model)
            self._activate_cooldown(selected_model)

            decision = ModelRoutingDecision(
                model=selected_model,
                use_thinking=use_thinking,
                is_casual=False,
            )
            return {
                "success": True,
                "result": decision.to_dict(),
            }

        # 2. Creation action - use cognitive generator with thinking
        if is_creation_action:
            creation_model = self._default_model()
            self._activate_cooldown(creation_model)
            decision = ModelRoutingDecision(
                model=creation_model,
                use_thinking=True,
                is_casual=False,
            )
            return {
                "success": True,
                "result": decision.to_dict(),
            }

        # 3. Determine if this is casual
        is_casual = False
        if self.casual_detector:
            try:
                casual_result = self.casual_detector.execute(
                    "detect_casual",
                    {
                        "input": input_text,
                        "intent_cluster": intent_cluster,
                        "message_length": message_length,
                    }
                )
                is_casual = casual_result.get("result", {}).get("is_casual", False)
            except Exception as e:
                logger.debug(
                    "Casual detection failed; continuing without casual signal",
                    exc_info=True,
                    extra={"module_name": "model_routing_engine", "error_type": type(e).__name__},
                )

        # Check for imperative verbs (short commands that are NOT casual)
        has_imperative_verb = self._has_imperative_command(input_text, message_length)
        actual_is_casual = is_casual and not has_imperative_verb

        # 4. Cluster memory - remember preferred model for this topic
        if intent_cluster and intent_cluster in self.cluster_model_cache:
            cached_model = self.cluster_model_cache[intent_cluster]
            if self._is_local_model(cached_model):
                use_thinking = self._supports_thinking(cached_model) and not actual_is_casual
                self._activate_cooldown(cached_model)

                decision = ModelRoutingDecision(
                    model=cached_model,
                    use_thinking=use_thinking,
                    is_casual=actual_is_casual,
                )
                return {
                    "success": True,
                    "result": decision.to_dict(),
                }

        # 5. Cooldown/stickiness (model continuity)
        for model, remaining_turns in self.model_cooldown.items():
            if remaining_turns > 0:
                use_thinking = self._supports_thinking(model) and not actual_is_casual
                decision = ModelRoutingDecision(
                    model=model,
                    use_thinking=use_thinking,
                    is_casual=actual_is_casual,
                )
                return {
                    "success": True,
                    "result": decision.to_dict(),
                }

        # 6. Default: use cognitive generator
        default_model = self._default_model()
        use_thinking = self._supports_thinking(default_model) and not actual_is_casual
        self._activate_cooldown(default_model)

        # Cache model for this cluster
        if intent_cluster:
            self.cluster_model_cache[intent_cluster] = default_model

        decision = ModelRoutingDecision(
            model=default_model,
            use_thinking=use_thinking,
            is_casual=actual_is_casual,
        )

        return {
            "success": True,
            "result": decision.to_dict(),
        }

    def _route_request(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """Route request (alias for select_model)"""
        return self._select_model(params)

    def _activate_cooldown(self, model: str):
        """Activate cooldown for a model"""
        self.model_cooldown[model] = self.cooldown_turns

        # Decrement other models
        for m in list(self.model_cooldown.keys()):
            if m != model:
                self.model_cooldown[m] = max(0, self.model_cooldown[m] - 1)

    def _has_imperative_command(self, input_text: str, message_length: int) -> bool:
        """Check if input has imperative verb (short command)"""
        # Short messages with imperative verbs are NOT casual
        if message_length < 20:
            imperative_verbs = ["do", "make", "create", "show", "get", "find", "search", "calculate"]
            words = input_text.lower().split()
            if words and words[0] in imperative_verbs:
                return True
        return False

