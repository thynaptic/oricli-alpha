from __future__ import annotations
"""
Structured Behaviors Module - Conversation flow patterns and routines
Handles conversation sequences, routine behaviors, and multi-turn behavior coordination
"""

from typing import Dict, Any, List, Optional
import json
from pathlib import Path
import logging

from oricli_core.brain.base_module import BaseBrainModule, ModuleMetadata
from oricli_core.exceptions import InvalidParameterError

logger = logging.getLogger(__name__)


class StructuredBehaviorsModule(BaseBrainModule):
    """Structured behaviors for conversation flows and routines"""

    def __init__(self):
        super().__init__()
        self.config = None
        self.behavior_sequences = {}
        self.routine_behaviors = {}
        self.current_sequences = {}
        self._load_config()

    @property
    def metadata(self) -> ModuleMetadata:
        return ModuleMetadata(
            name="structured_behaviors",
            version="1.0.0",
            description="Structured behaviors: conversation flows, routines, multi-turn sequences",
            operations=[
                "get_behavior_sequence",
                "execute_behavior",
                "continue_sequence",
                "reset_sequence",
                "get_routine_behavior",
            ],
            dependencies=[],
            model_required=False,
        )

    def initialize(self) -> bool:
        """Initialize the module"""
        return True

    def _load_config(self):
        """Load structured behaviors configuration"""
        config_path = Path(__file__).parent / "pattern_library.json"
        try:
            if config_path.exists():
                with open(config_path, "r", encoding="utf-8") as f:
                    self.config = json.load(f)
                    self.behavior_sequences = self.config.get("conversation_flows", {})
                    self.routine_behaviors = self.config.get("routines", {})
            else:
                # Default behaviors
                self.behavior_sequences = {
                    "greeting_flow": ["greet", "acknowledge", "ask_interest"],
                    "help_flow": [
                        "acknowledge_request",
                        "clarify_needs",
                        "provide_help",
                    ],
                    "closing_flow": ["summarize", "offer_more", "say_goodbye"],
                }
                self.routine_behaviors = {
                    "confirmation": ["acknowledge", "confirm", "proceed"],
                    "clarification": [
                        "acknowledge_uncertainty",
                        "ask_clarification",
                        "wait_for_response",
                    ],
                }
        except Exception as e:
            logger.warning(
                "Failed to load structured_behaviors config; using empty defaults",
                exc_info=True,
                extra={"module_name": "structured_behaviors", "error_type": type(e).__name__},
            )
            self.behavior_sequences = {}
            self.routine_behaviors = {}

    def execute(self, operation: str, params: Dict[str, Any]) -> Dict[str, Any]:
        """Execute a structured behaviors operation"""
        if operation == "get_behavior_sequence":
            sequence_type = params.get("sequence_type", "")
            if sequence_type is None:
                sequence_type = ""
            if not isinstance(sequence_type, str):
                raise InvalidParameterError(
                    "sequence_type", str(type(sequence_type).__name__), "sequence_type must be a string"
                )
            return self.get_behavior_sequence(sequence_type)
        elif operation == "execute_behavior":
            behavior = params.get("behavior", "")
            context = params.get("context", {})
            sequence_id = params.get("sequence_id", "")
            if behavior is None:
                behavior = ""
            if context is None:
                context = {}
            if sequence_id is None:
                sequence_id = ""
            if not isinstance(behavior, str):
                raise InvalidParameterError("behavior", str(type(behavior).__name__), "behavior must be a string")
            if not isinstance(context, dict):
                raise InvalidParameterError("context", str(type(context).__name__), "context must be a dict")
            if not isinstance(sequence_id, str):
                raise InvalidParameterError(
                    "sequence_id", str(type(sequence_id).__name__), "sequence_id must be a string"
                )
            return self.execute_behavior(behavior, context, sequence_id)
        elif operation == "continue_sequence":
            sequence_id = params.get("sequence_id", "")
            context = params.get("context", {})
            if sequence_id is None:
                sequence_id = ""
            if context is None:
                context = {}
            if not isinstance(sequence_id, str):
                raise InvalidParameterError(
                    "sequence_id", str(type(sequence_id).__name__), "sequence_id must be a string"
                )
            if not isinstance(context, dict):
                raise InvalidParameterError("context", str(type(context).__name__), "context must be a dict")
            return self.continue_sequence(sequence_id, context)
        elif operation == "reset_sequence":
            sequence_id = params.get("sequence_id", "")
            if sequence_id is None:
                sequence_id = ""
            if not isinstance(sequence_id, str):
                raise InvalidParameterError(
                    "sequence_id", str(type(sequence_id).__name__), "sequence_id must be a string"
                )
            return self.reset_sequence(sequence_id)
        elif operation == "get_routine_behavior":
            routine_type = params.get("routine_type", "")
            if routine_type is None:
                routine_type = ""
            if not isinstance(routine_type, str):
                raise InvalidParameterError(
                    "routine_type", str(type(routine_type).__name__), "routine_type must be a string"
                )
            return self.get_routine_behavior(routine_type)
        else:
            raise InvalidParameterError("operation", str(operation), "Unknown operation for structured_behaviors")

    def get_behavior_sequence(self, sequence_type: str) -> Dict[str, Any]:
        """Get a behavior sequence by type"""
        if sequence_type in self.behavior_sequences:
            sequence = self.behavior_sequences[sequence_type]
            return {
                "sequence_type": sequence_type,
                "sequence": sequence,
                "steps": len(sequence),
                "found": True,
            }
        else:
            return {
                "sequence_type": sequence_type,
                "sequence": [],
                "steps": 0,
                "found": False,
            }

    def execute_behavior(
        self, behavior: str, context: Dict[str, Any] = None, sequence_id: str = ""
    ) -> Dict[str, Any]:
        """Execute a specific behavior"""
        if context is None:
            context = {}

        # Track behavior execution if part of sequence
        if sequence_id:
            if sequence_id not in self.current_sequences:
                self.current_sequences[sequence_id] = {
                    "current_step": 0,
                    "behaviors_executed": [],
                    "completed": False,
                }

            self.current_sequences[sequence_id]["behaviors_executed"].append(behavior)

        # Map behaviors to actions (simplified)
        behavior_actions = {
            "greet": {
                "action": "greeting",
                "response_template": "Hello! How can I help you?",
            },
            "acknowledge": {"action": "acknowledgment", "response_template": "I see."},
            "ask_interest": {
                "action": "question",
                "response_template": "What would you like to talk about?",
            },
            "acknowledge_request": {
                "action": "acknowledgment",
                "response_template": "I'd be happy to help with that.",
            },
            "clarify_needs": {
                "action": "question",
                "response_template": "Could you tell me more about what you need?",
            },
            "provide_help": {
                "action": "response",
                "response_template": "Here's what I can suggest...",
            },
            "summarize": {"action": "summary", "response_template": "To summarize..."},
            "offer_more": {
                "action": "question",
                "response_template": "Is there anything else I can help with?",
            },
            "say_goodbye": {
                "action": "closing",
                "response_template": "Goodbye! Take care.",
            },
            "confirm": {
                "action": "confirmation",
                "response_template": "Got it. Proceeding.",
            },
            "proceed": {"action": "proceed", "response_template": "Let's continue."},
            "ask_clarification": {
                "action": "question",
                "response_template": "Could you clarify that?",
            },
            "wait_for_response": {"action": "pause", "response_template": ""},
        }

        behavior_data = behavior_actions.get(
            behavior, {"action": "unknown", "response_template": "I'm processing that."}
        )

        return {
            "behavior": behavior,
            "action": behavior_data["action"],
            "response_template": behavior_data["response_template"],
            "executed": True,
            "sequence_id": sequence_id,
            "context": context,
        }

    def continue_sequence(
        self, sequence_id: str, context: Dict[str, Any] = None
    ) -> Dict[str, Any]:
        """Continue a behavior sequence"""
        if context is None:
            context = {}

        if sequence_id not in self.current_sequences:
            return {
                "sequence_id": sequence_id,
                "next_behavior": None,
                "completed": True,
                "error": "Sequence not found",
            }

        sequence_data = self.current_sequences[sequence_id]

        # Get sequence type from context or sequence data
        sequence_type = context.get(
            "sequence_type", sequence_data.get("sequence_type", "")
        )

        if not sequence_type or sequence_type not in self.behavior_sequences:
            return {
                "sequence_id": sequence_id,
                "next_behavior": None,
                "completed": True,
                "error": "Sequence type not found",
            }

        sequence = self.behavior_sequences[sequence_type]
        current_step = sequence_data.get("current_step", 0)

        if current_step >= len(sequence):
            sequence_data["completed"] = True
            return {
                "sequence_id": sequence_id,
                "next_behavior": None,
                "completed": True,
                "message": "Sequence completed",
            }

        next_behavior = sequence[current_step]
        sequence_data["current_step"] = current_step + 1

        # Execute next behavior
        behavior_result = self.execute_behavior(next_behavior, context, sequence_id)

        return {
            "sequence_id": sequence_id,
            "next_behavior": next_behavior,
            "completed": False,
            "current_step": current_step + 1,
            "total_steps": len(sequence),
            "behavior_result": behavior_result,
        }

    def reset_sequence(self, sequence_id: str) -> Dict[str, Any]:
        """Reset a behavior sequence"""
        if sequence_id in self.current_sequences:
            del self.current_sequences[sequence_id]
            return {"sequence_id": sequence_id, "reset": True}
        else:
            return {
                "sequence_id": sequence_id,
                "reset": False,
                "message": "Sequence not found",
            }

    def get_routine_behavior(self, routine_type: str) -> Dict[str, Any]:
        """Get a routine behavior sequence"""
        if routine_type in self.routine_behaviors:
            routine = self.routine_behaviors[routine_type]
            return {
                "routine_type": routine_type,
                "routine": routine,
                "steps": len(routine),
                "found": True,
            }
        else:
            return {
                "routine_type": routine_type,
                "routine": [],
                "steps": 0,
                "found": False,
            }

    def validate_params(self, operation: str, params: Dict[str, Any]) -> bool:
        """Validate parameters for operations"""
        if operation == "get_behavior_sequence":
            return "sequence_type" in params
        elif operation == "execute_behavior":
            return "behavior" in params
        elif operation == "continue_sequence":
            return "sequence_id" in params
        elif operation == "reset_sequence":
            return "sequence_id" in params
        elif operation == "get_routine_behavior":
            return "routine_type" in params
        return True
