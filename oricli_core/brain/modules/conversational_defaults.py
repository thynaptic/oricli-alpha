from __future__ import annotations
"""
Conversational Defaults Module
Handles simple greetings and low-density prompts that don't require full Hive deliberation.
Ensures the Swarm always has a baseline responder for small talk.
"""

import random
from typing import Any, Dict, List

from oricli_core.brain.base_module import BaseBrainModule, ModuleMetadata
from oricli_core.exceptions import InvalidParameterError

class ConversationalDefaultsModule(BaseBrainModule):
    """Micro-agent for handling small talk and basic greetings."""

    def __init__(self):
        super().__init__()
        self.greetings = [
            "Hello! How can the Hive assist you today?",
            "Greetings. I am Oricli-Alpha. What's on your mind?",
            "Hi there! Ready for some sovereign orchestration?",
            "Hello! The micro-agents are standing by. How can I help?",
            "Greetings, boss. What are we building today?"
        ]
        
        self.trigger_keywords = ["hi", "hello", "hey", "greetings", "yo", "morning", "afternoon", "evening"]

    @property
    def metadata(self) -> ModuleMetadata:
        return ModuleMetadata(
            name="conversational_defaults",
            version="1.0.0",
            description="Handles simple greetings and small talk to prevent swarm bidding failures.",
            operations=["generate_response", "status"],
            dependencies=[],
            enabled=True,
            model_required=False,
        )

    def execute(self, operation: str, params: Dict[str, Any]) -> Dict[str, Any]:
        if operation == "status":
            return {"success": True, "status": "active"}

        if operation == "generate_response":
            messages = params.get("messages", [])
            last_msg = ""
            if messages:
                last_msg = messages[-1].get("content", "").lower().strip().strip("?!.")
            
            # Simple heuristic for small talk
            if last_msg in self.trigger_keywords or not last_msg or len(last_msg) < 3:
                response = random.choice(self.greetings)
                return {
                    "success": True, 
                    "text": response,
                    "method": "conversational_default",
                    "confidence": 1.0
                }
            
            # If it's not a greeting, we can still provide a "I'm not sure how to handle this density" response
            # but usually, another agent will out-bid us for complex tasks.
            return {
                "success": True,
                "text": "I hear you, but I might need a bit more detail to dispatch the right micro-agents. What's the goal?",
                "method": "conversational_default",
                "confidence": 0.1 # Low confidence so other agents win complex tasks
            }

        raise InvalidParameterError(parameter="operation", value=operation, reason="Unsupported operation")
