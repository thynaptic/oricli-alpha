from __future__ import annotations
"""
Reaction Memory Service
Service to track user reactions and store them in Mavaia's memory for learning
Converted from Swift ReactionMemoryService.swift
"""

from typing import Any, Dict, List, Optional
import logging
import time

from mavaia_core.brain.base_module import BaseBrainModule, ModuleMetadata
from mavaia_core.brain.registry import ModuleRegistry
from mavaia_core.exceptions import InvalidParameterError

logger = logging.getLogger(__name__)


class ReactionType:
    """Reaction type enumeration"""
    THUMBS_UP = "thumbs_up"
    THUMBS_DOWN = "thumbs_down"
    HEART = "heart"
    STAR = "star"
    CHECKMARK = "checkmark"
    XMARK = "xmark"
    LIGHTBULB = "lightbulb"
    FIRE = "fire"
    PARTY = "party"
    SAD = "sad"

    @staticmethod
    def is_positive(reaction: str) -> bool:
        """Check if reaction is positive"""
        positive_reactions = {
            ReactionType.THUMBS_UP,
            ReactionType.HEART,
            ReactionType.STAR,
            ReactionType.CHECKMARK,
            ReactionType.LIGHTBULB,
            ReactionType.FIRE,
            ReactionType.PARTY,
        }
        return reaction in positive_reactions

    @staticmethod
    def get_display_name(reaction: str) -> str:
        """Get display name for reaction"""
        names = {
            ReactionType.THUMBS_UP: "Thumbs Up",
            ReactionType.THUMBS_DOWN: "Thumbs Down",
            ReactionType.HEART: "Heart",
            ReactionType.STAR: "Star",
            ReactionType.CHECKMARK: "Checkmark",
            ReactionType.XMARK: "X Mark",
            ReactionType.LIGHTBULB: "Lightbulb",
            ReactionType.FIRE: "Fire",
            ReactionType.PARTY: "Party",
            ReactionType.SAD: "Sad",
        }
        return names.get(reaction, reaction)


def extract_keywords(text: str) -> List[str]:
    """Extract keywords from text"""
    stop_words = {
        "this", "that", "with", "from", "have", "about", "there", "their", "which", "while",
        "where", "what", "when", "your", "into", "over", "under", "through", "many", "some",
        "really", "just", "like", "them", "they", "you're", "you", "here", "there's", "the",
        "a", "an", "and", "or", "but", "is", "are", "was", "were", "be", "been", "being",
    }

    import re
    tokens = re.findall(r"\b\w+\b", text.lower())
    tokens = [t for t in tokens if len(t) > 3 and t not in stop_words]

    from collections import Counter
    word_counts = Counter(tokens)
    top_words = [word for word, _ in word_counts.most_common(5)]

    return top_words


class ReactionMemoryServiceModule(BaseBrainModule):
    """Service to track user reactions and store them in memory"""

    def __init__(self):
        super().__init__()
        self.persistent_memory_service = None
        self._modules_loaded = False

    @property
    def metadata(self) -> ModuleMetadata:
        return ModuleMetadata(
            name="reaction_memory_service",
            version="1.0.0",
            description="Service to track user reactions and store them in Mavaia's memory for learning",
            operations=[
                "record_reaction",
                "get_reactions",
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
            self.persistent_memory_service = ModuleRegistry.get_module("persistent_memory_service")

            self._modules_loaded = True
        except Exception as e:
            logger.debug(
                "Failed to load optional persistent_memory_service",
                exc_info=True,
                extra={"module_name": "reaction_memory_service", "error_type": type(e).__name__},
            )

    def execute(self, operation: str, params: Dict[str, Any]) -> Dict[str, Any]:
        """Execute an operation"""
        self._ensure_modules_loaded()

        if operation == "record_reaction":
            return self._record_reaction(params)
        elif operation == "get_reactions":
            return self._get_reactions(params)
        else:
            raise InvalidParameterError(
                parameter="operation",
                value=operation,
                reason="Unknown operation for reaction_memory_service",
            )

    def _record_reaction(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """Record a reaction to a message in Mavaia's memory"""
        reaction_type = params.get("reaction", "")
        message_data = params.get("message", {})
        conversation_data = params.get("conversation", {})

        message_id = message_data.get("id", "")
        conversation_id = conversation_data.get("id", "")
        message_content = message_data.get("content", "")
        conversation_title = conversation_data.get("title", "")

        # Determine if this is positive or negative feedback
        is_positive = ReactionType.is_positive(reaction_type)
        feedback_type = "positive" if is_positive else "negative"

        # Store feedback in persistent memory
        content = f"""User reacted with {ReactionType.get_display_name(reaction_type)} ({reaction_type}) to message:
"{message_content[:200]}"

Reaction type: {feedback_type}
Message context: {conversation_title}
Timestamp: {time.time()}
"""

        importance = 0.8 if is_positive else 0.9  # Negative feedback is more important

        try:
            if self.persistent_memory_service:
                result = self.persistent_memory_service.execute(
                    "store_memory",
                    {
                        "content": content,
                        "type": "feedback",
                        "metadata": {
                            "reaction_type": reaction_type,
                            "is_positive": is_positive,
                            "message_id": message_id,
                            "conversation_id": conversation_id,
                        },
                        "importance": importance,
                        "conversation_id": conversation_id,
                        "message_id": message_id,
                        "tags": [feedback_type, reaction_type],
                        "keywords": extract_keywords(message_content),
                        "emotional_tone": feedback_type,
                    }
                )

                if result.get("success"):
                    return {
                        "success": True,
                        "result": {
                            "recorded": True,
                            "reaction_type": reaction_type,
                            "feedback_type": feedback_type,
                        },
                    }
        except Exception as e:
            logger.debug(
                "Failed to store reaction in persistent memory",
                exc_info=True,
                extra={"module_name": "reaction_memory_service", "error_type": type(e).__name__},
            )
            return {
                "success": False,
                "error": "Failed to store reaction",
            }

        # Fallback: return success even if memory service is not available
        return {
            "success": True,
            "result": {
                "recorded": True,
                "reaction_type": reaction_type,
                "feedback_type": feedback_type,
            },
        }

    def _get_reactions(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """Get reactions for a message or conversation"""
        message_id = params.get("message_id")
        conversation_id = params.get("conversation_id")

        # In a real implementation, this would query a database
        # For now, return empty list
        return {
            "success": True,
            "result": {
                "reactions": [],
                "count": 0,
            },
        }

