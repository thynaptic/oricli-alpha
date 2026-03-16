from __future__ import annotations
"""
Instruction Following Module - High-precision task execution and intent detection
Handles formatting tasks, data analysis directives, and rigid output constraints
Designed to bypass conversational drift and enforce strict formatting rules
"""

from typing import Any, Dict, List
import re

from oricli_core.brain.base_module import BaseBrainModule, ModuleMetadata
from oricli_core.exceptions import InvalidParameterError


class InstructionFollowingModule(BaseBrainModule):
    """Execute high-precision tasks with zero conversational filler"""

    def __init__(self):
        super().__init__()
        # Approved keyword list for hard-bypass intent detection
        self.intent_keywords = [
            "json", "jsonl", "csv", "xml", "yaml", 
            "markdown table", "reformat", "convert", 
            "extract", "simplify", "parse", "map", 
            "no filler", "raw only", "strict schema", 
            "without explanation", "calculate", "evaluate", 
            "regex", "schema", "ground truth", 
            "{", "[", "<html>"
        ]

    @property
    def metadata(self) -> ModuleMetadata:
        return ModuleMetadata(
            name="instruction_following",
            version="1.0.0",
            description=(
                "High-precision instruction following: formatting, "
                "data analysis, and strict constraint enforcement"
            ),
            operations=[
                "detect_intent",
                "execute_task",
                "apply_formatting_lock",
            ],
            dependencies=[],
            model_required=False,
        )

    def initialize(self) -> bool:
        """Initialize the module"""
        return True

    def execute(self, operation: str, params: Dict[str, Any]) -> Dict[str, Any]:
        """Execute an instruction following operation"""
        if operation == "detect_intent":
            input_text = params.get("input_text", "")
            if input_text is None:
                input_text = ""
            if not isinstance(input_text, str):
                raise InvalidParameterError("input_text", str(type(input_text).__name__), "input_text must be a string")
            return self.detect_intent(input_text)
            
        elif operation == "execute_task":
            input_text = params.get("input_text", "")
            task_type = params.get("task_type", "generic")
            if input_text is None:
                input_text = ""
            if not isinstance(input_text, str):
                raise InvalidParameterError("input_text", str(type(input_text).__name__), "input_text must be a string")
            return self.execute_task(input_text, task_type)
            
        elif operation == "apply_formatting_lock":
            text = params.get("text", "")
            if text is None:
                text = ""
            if not isinstance(text, str):
                raise InvalidParameterError("text", str(type(text).__name__), "text must be a string")
            return self.apply_formatting_lock(text)
            
        else:
            raise InvalidParameterError("operation", str(operation), "Unknown operation for instruction_following")

    def detect_intent(self, input_text: str) -> Dict[str, Any]:
        """
        Detect if the input text contains a high-precision instruction intent
        """
        input_lower = input_text.lower()
        matched_keywords = []
        
        for keyword in self.intent_keywords:
            # Handle special characters like { or [ or <html>
            if keyword in ["{", "[", "<html>"]:
                if keyword in input_lower:
                    matched_keywords.append(keyword)
            else:
                # Use word boundaries for standard keywords
                pattern = rf"\b{re.escape(keyword)}\b"
                if re.search(pattern, input_lower):
                    matched_keywords.append(keyword)
        
        is_high_precision = len(matched_keywords) > 0
        
        return {
            "is_high_precision": is_high_precision,
            "matched_keywords": matched_keywords,
            "confidence": 1.0 if is_high_precision else 0.0
        }

    def execute_task(self, input_text: str, task_type: str = "generic") -> Dict[str, Any]:
        """
        Prepare parameters for high-precision task execution
        """
        # In this module, "execution" means preparing the routing context
        # to ensure the model knows it is in TASK_EXECUTION mode.
        return {
            "mode": "TASK_EXECUTION",
            "suppress_identity": True,
            "formatting_lock": True,
            "task_type": task_type,
            "input_context": input_text
        }

    def apply_formatting_lock(self, text: str) -> Dict[str, Any]:
        """
        Ensures the output text is not tampered with by conversational filters
        """
        # This is a marker operation that signals to the CognitiveGenerator
        # that the text should be returned as-is.
        return {
            "locked_text": text,
            "formatting_lock_active": True
        }

    def validate_params(self, operation: str, params: Dict[str, Any]) -> bool:
        """Validate parameters for operations"""
        if operation == "detect_intent":
            return "input_text" in params
        elif operation == "execute_task":
            return "input_text" in params
        elif operation == "apply_formatting_lock":
            return "text" in params
        return True
