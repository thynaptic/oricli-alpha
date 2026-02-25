from __future__ import annotations
"""
Conversation Compression Service - Summarizes long conversations to manage context limits
Converted from Swift ConversationCompressionService.swift
"""

from typing import Any, Dict, List, Optional
import logging

from mavaia_core.brain.base_module import BaseBrainModule, ModuleMetadata
from mavaia_core.brain.registry import ModuleRegistry
from mavaia_core.exceptions import InvalidParameterError

logger = logging.getLogger(__name__)


class ConversationCompressionServiceModule(BaseBrainModule):
    """Summarizes long conversations to manage context limits"""

    def __init__(self):
        super().__init__()
        self.cognitive_generator = None
        self._modules_loaded = False
        self._cache: Dict[str, Dict[str, Any]] = {}
        self._threshold = 40
        self._minimum_compress_count = 16
        self._retain_count = 12

    @property
    def metadata(self) -> ModuleMetadata:
        return ModuleMetadata(
            name="conversation_compression_service",
            version="1.0.0",
            description="Summarizes long conversations to manage context limits",
            operations=[
                "compress_conversation",
                "summarize_conversation",
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
                "Failed to load conversation_compression_service dependencies",
                exc_info=True,
                extra={"module_name": "conversation_compression_service", "error_type": type(e).__name__},
            )

    def execute(self, operation: str, params: Dict[str, Any]) -> Dict[str, Any]:
        """Execute an operation"""
        self._ensure_modules_loaded()

        if operation == "compress_conversation":
            return self._compress_conversation(params)
        elif operation == "summarize_conversation":
            return self._summarize_conversation(params)
        else:
            raise InvalidParameterError(
                parameter="operation",
                value=operation,
                reason="Unknown operation for conversation_compression_service",
            )

    def _compress_conversation(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """Compress a conversation"""
        conversation_id = params.get("conversation_id")
        messages = params.get("messages", [])
        if conversation_id is None or not isinstance(conversation_id, (str, int)) or not str(conversation_id).strip():
            # If no conversation_id, we can still return as non-compressed.
            conversation_id = None
        if messages is None:
            messages = []
        if not isinstance(messages, list):
            raise InvalidParameterError(
                parameter="messages",
                value=str(type(messages).__name__),
                reason="messages must be a list",
            )

        if not conversation_id or len(messages) <= self._threshold:
            return {
                "success": True,
                "summary": None,
                "retained_messages": messages,
            }

        compress_count = max(0, len(messages) - self._retain_count)
        if compress_count < self._minimum_compress_count:
            return {
                "success": True,
                "summary": None,
                "retained_messages": messages,
            }

        head_messages = messages[:compress_count]
        tail_messages = messages[-self._retain_count:]

        # Check cache
        cache_key = str(conversation_id)
        if cache_key in self._cache:
            cached = self._cache[cache_key]
            if (
                cached.get("compressed_count") == compress_count
                and cached.get("last_message_id") == head_messages[-1].get("id") if head_messages else None
            ):
                return {
                    "success": True,
                    "summary": cached.get("summary"),
                    "retained_messages": tail_messages,
                }

        # Build transcript
        transcript = self._build_transcript(head_messages)
        if not transcript:
            return {
                "success": True,
                "summary": None,
                "retained_messages": messages,
            }

        # Generate summary
        summary_prompt = f"""
        Summarize this conversation, preserving:
        - Key topics discussed
        - Important decisions made
        - Emotional tone
        - Action items
        
        Keep it concise (2-3 paragraphs):
        
        {transcript}
        """

        summary = None
        if self.cognitive_generator:
            try:
                result = self.cognitive_generator.execute("generate_summary", {
                    "content": summary_prompt,
                    "max_sentences": 3,
                })
                summary = result.get("summary")
            except Exception as e:
                logger.debug(
                    "Conversation summarization failed; returning uncompressed messages",
                    exc_info=True,
                    extra={"module_name": "conversation_compression_service", "error_type": type(e).__name__},
                )

        if summary:
            # Cache result
            self._cache[cache_key] = {
                "compressed_count": compress_count,
                "last_message_id": head_messages[-1].get("id") if head_messages else None,
                "summary": summary,
            }

            return {
                "success": True,
                "summary": summary,
                "retained_messages": tail_messages,
            }

        return {
            "success": True,
            "summary": None,
            "retained_messages": messages,
        }

    def _summarize_conversation(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """Summarize a conversation (alias for compress_conversation)"""
        return self._compress_conversation(params)

    def _build_transcript(self, messages: List[Dict[str, Any]]) -> str:
        """Build transcript from messages"""
        transcript_lines = []
        for index, message in enumerate(messages):
            role = "Mavaia" if message.get("role") == "assistant" else "User"
            content = message.get("content", "").strip()
            if content:
                transcript_lines.append(f"{index + 1}. {role}: {content}")

        transcript = "\n".join(transcript_lines)

        # Limit transcript size
        limit = 4000
        if len(transcript) > limit:
            transcript = transcript[:limit]

        return transcript

