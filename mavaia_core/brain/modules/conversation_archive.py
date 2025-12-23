"""
Conversation Archive
Manages conversation digestion and cross-conversation memory
Converted from Swift ConversationArchive.swift
"""

from typing import Any, Dict, List, Optional
import re
import logging
from pathlib import Path
from dataclasses import dataclass

from mavaia_core.brain.base_module import BaseBrainModule, ModuleMetadata
from mavaia_core.brain.registry import ModuleRegistry
from mavaia_core.exceptions import InvalidParameterError

# Optional imports - models package may not be available
try:
    from models.conversation_digest_models import ConversationDigest
    from models.core_types import ConversationSummaryContext
except ImportError:
    # Models not available - define minimal types
    ConversationDigest = None
    ConversationSummaryContext = None

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class _FallbackConversationDigest:
    """Minimal in-module fallback for ConversationDigest when models are unavailable."""

    conversation_id: str
    title: str
    summary: str
    key_topics: List[str]
    emotional_tone: str
    message_count: int
    start_date: float
    last_message_date: float
    is_digested: bool
    action_items: List[str]
    decisions: List[str]
    insights: List[str]
    searchable_content: str

    def to_dict(self) -> Dict[str, Any]:
        return {
            "conversation_id": self.conversation_id,
            "title": self.title,
            "summary": self.summary,
            "key_topics": list(self.key_topics),
            "emotional_tone": self.emotional_tone,
            "message_count": self.message_count,
            "start_date": self.start_date,
            "last_message_date": self.last_message_date,
            "is_digested": self.is_digested,
            "action_items": list(self.action_items),
            "decisions": list(self.decisions),
            "insights": list(self.insights),
            "searchable_content": self.searchable_content,
        }


class ConversationArchiveModule(BaseBrainModule):
    """Manages conversation digestion and cross-conversation memory"""

    def __init__(self):
        super().__init__()
        self.cognitive_generator = None
        self._modules_loaded = False
        # In-memory storage for conversation digests
        self._archives: Dict[str, Any] = {}

    @property
    def metadata(self) -> ModuleMetadata:
        return ModuleMetadata(
            name="conversation_archive",
            version="1.0.0",
            description="Manages conversation digestion and cross-conversation memory",
            operations=[
                "digest_conversation",
                "archive_conversation",
                "retrieve_archive",
                "get_recent_digests",
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
            self.cognitive_generator = ModuleRegistry.get_module("cognitive_generator")

            self._modules_loaded = True
        except Exception as e:
            logger.debug(
                "Failed to load dependent modules for conversation_archive",
                exc_info=True,
                extra={"module_name": "conversation_archive", "error_type": type(e).__name__},
            )

    def execute(self, operation: str, params: Dict[str, Any]) -> Dict[str, Any]:
        """Execute an operation"""
        self._ensure_modules_loaded()

        match operation:
            case "digest_conversation":
                return self._digest_conversation(params)
            case "archive_conversation":
                return self._archive_conversation(params)
            case "retrieve_archive":
                return self._retrieve_archive(params)
            case "get_recent_digests":
                return self._get_recent_digests(params)
            case _:
                raise InvalidParameterError(
                    parameter="operation",
                    value=operation,
                    reason="Unknown operation for conversation_archive",
                )

    def _digest_conversation(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """Generate AI summary for a specific conversation"""
        conversation_data = params.get("conversation", {})
        conversation_id = conversation_data.get("id")
        title = conversation_data.get("title", "")
        messages = conversation_data.get("messages", [])
        created_at = conversation_data.get("created_at", 0.0)
        updated_at = conversation_data.get("updated_at", 0.0)

        if not isinstance(conversation_data, dict):
            raise InvalidParameterError("conversation", str(type(conversation_data).__name__), "conversation must be a dict")

        if not conversation_id or not isinstance(conversation_id, str):
            return {"success": False, "error": "conversation.id is required"}

        if title is None:
            title = ""
        if not isinstance(title, str):
            return {"success": False, "error": "conversation.title must be a string"}

        if messages is None:
            messages = []
        if not isinstance(messages, list):
            return {"success": False, "error": "conversation.messages must be a list"}

        try:
            created_at_float = float(created_at)
        except (TypeError, ValueError):
            created_at_float = 0.0
        try:
            updated_at_float = float(updated_at)
        except (TypeError, ValueError):
            updated_at_float = created_at_float

        if not messages:
            return {
                "success": False,
                "error": "Empty conversation",
            }

        # Build conversation transcript
        transcript = self._build_transcript(messages)

        # Generate summary using cognitive generator
        summary_prompt = f"""Analyze this conversation and provide:
1. A 2-3 sentence summary
2. Key topics discussed (3-5 topics)
3. Overall emotional tone (positive/challenging/neutral/excited/frustrated)
4. Any action items mentioned
5. Any decisions made
6. Key insights

Format your response as:
SUMMARY:
[2-3 sentence summary]

TOPICS:
[comma-separated topics]

TONE:
[emotional tone]

ACTION ITEMS:
[list of action items or "None"]

DECISIONS:
[list of decisions or "None"]

INSIGHTS:
[list of insights or "None"]

Conversation:
{transcript}
"""

        if not self.cognitive_generator:
            return {
                "success": False,
                "error": "Cognitive generator not available",
            }

        try:
            response_result = self.cognitive_generator.execute(
                "generate_summary",
                {
                    "content": summary_prompt,
                    "max_sentences": 5,
                }
            )

            response = response_result.get("result", {}).get("summary", "")

            # Parse response
            summary = self._extract_section(response, "SUMMARY")
            topics_text = self._extract_section(response, "TOPICS")
            tone = self._extract_section(response, "TONE").lower()
            action_items_text = self._extract_section(response, "ACTION ITEMS")
            decisions_text = self._extract_section(response, "DECISIONS")
            insights_text = self._extract_section(response, "INSIGHTS")

            topics = [t.strip() for t in topics_text.split(",") if t.strip()]

            action_items = self._parse_list(action_items_text)
            decisions = self._parse_list(decisions_text)
            insights = self._parse_list(insights_text)

            # Create digest (use fallback if models package unavailable)
            digest_cls = ConversationDigest or _FallbackConversationDigest
            digest = digest_cls(
                conversation_id=conversation_id,
                title=title,
                summary=summary,
                key_topics=topics,
                emotional_tone=tone if tone else "neutral",
                message_count=len(messages),
                start_date=created_at_float,
                last_message_date=updated_at_float,
                is_digested=True,
                action_items=action_items,
                decisions=decisions,
                insights=insights,
                searchable_content=transcript,
            )

            # Store digest in memory
            self._archives[conversation_id] = digest

            return {
                "success": True,
                "result": digest.to_dict(),
            }
        except Exception as e:
            logger.debug(
                "Conversation digest failed",
                exc_info=True,
                extra={"module_name": "conversation_archive", "conversation_id": str(conversation_id), "error_type": type(e).__name__},
            )
            return {
                "success": False,
                "error": "Conversation digest failed",
            }

    def _archive_conversation(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """Archive conversation (alias for digest_conversation)"""
        return self._digest_conversation(params)

    def _retrieve_archive(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """Retrieve archived conversation digest"""
        conversation_id = params.get("conversation_id")

        if not conversation_id:
            return {
                "success": False,
                "error": "conversation_id is required",
            }

        digest = self._archives.get(conversation_id)
        if not digest:
            return {
                "success": False,
                "error": f"Archive for conversation {conversation_id} not found",
            }

        return {
            "success": True,
            "result": digest.to_dict(),
        }

    def _get_recent_digests(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """Get recent conversation summaries for AI context"""
        excluding_id = params.get("excluding_id")
        limit = params.get("limit", 3)

        # Get all digests, sorted by last_message_date (most recent first)
        all_digests = list(self._archives.values())
        if excluding_id:
            all_digests = [d for d in all_digests if d.conversation_id != excluding_id]
        
        # Sort by last_message_date descending
        all_digests.sort(key=lambda d: d.last_message_date, reverse=True)
        
        # Limit results
        recent_digests = all_digests[:limit]

        return {
            "success": True,
            "result": {
                "digests": [d.to_dict() for d in recent_digests],
                "count": len(recent_digests),
            },
        }

    def _build_transcript(self, messages: List[Dict[str, Any]]) -> str:
        """Build conversation transcript from messages"""
        transcript_parts = []
        for message in messages:
            role = message.get("role", "user")
            content = message.get("content", "")
            transcript_parts.append(f"{role.capitalize()}: {content}")
        return "\n".join(transcript_parts)

    def _extract_section(self, text: str, section: str) -> str:
        """Extract a section from formatted text"""
        pattern = f"{section}:\\s*(.*?)(?=\\n[A-Z]+:|$)"
        match = re.search(pattern, text, re.DOTALL | re.IGNORECASE)
        if match:
            return match.group(1).strip()
        return ""

    def _parse_list(self, text: str) -> List[str]:
        """Parse a list from text"""
        if not text or text.lower() == "none":
            return []

        # Split by newlines or commas
        items = re.split(r"[\n,]", text)
        return [item.strip() for item in items if item.strip()]

