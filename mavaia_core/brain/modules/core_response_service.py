from __future__ import annotations
"""
Core Response Service - Abstraction layer for AI response generation
Routes to CognitiveGeneratorService (local Python) or HybridBridgeService
Converted from Swift CoreResponseService.swift
"""

from typing import Any, Dict, List, Optional
import logging
import time

from mavaia_core.brain.base_module import BaseBrainModule, ModuleMetadata
from mavaia_core.exceptions import InvalidParameterError

# Lazy import models - don't import at module level
ConversationMessage = None
AIPayloadContext = None
ConfidenceSnapshot = None
ConfidenceLevel = None
WebSearchItem = None
Message = None

logger = logging.getLogger(__name__)

def _lazy_import_models():
    """Lazy import models only when needed"""
    global ConversationMessage, AIPayloadContext, ConfidenceSnapshot, ConfidenceLevel, WebSearchItem, Message
    if ConversationMessage is None:
        try:
            from models.core_types import (
                ConversationMessage as CM,
                AIPayloadContext as APC,
                ConfidenceSnapshot as CS,
                ConfidenceLevel as CL,
                WebSearchItem as WSI,
            )
            from models.message_models import Message as M
            ConversationMessage = CM
            AIPayloadContext = APC
            ConfidenceSnapshot = CS
            ConfidenceLevel = CL
            WebSearchItem = WSI
            Message = M
        except ImportError:
            pass  # Models not available


class CoreResponseServiceModule(BaseBrainModule):
    """Main orchestrator for response generation"""

    def __init__(self):
        super().__init__()
        self.cognitive_generator = None
        self.tool_registration = None
        self.safety_framework = None
        self.tool_calling_agent = None
        self.conversational_orchestrator = None
        self.universal_voice_engine = None
        self._tools_registered = False
        self._safety_services_registered = False
        self._modules_loaded = False

    @property
    def metadata(self) -> ModuleMetadata:
        return ModuleMetadata(
            name="core_response_service",
            version="1.0.0",
            description="Abstraction layer for AI response generation - routes to cognitive generator or hybrid bridge",
            operations=[
                "generate_response",
                "generate_response_with_app_context",
                "generate_response_with_tools",
                "check_input",
                "check_response",
                "generate_conversation_title",
                "generate_conversation_summary",
                "summarize_recent_messages",
                "generate_hybrid_phrase_for_completion",
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
            # Lazy import to avoid circular dependency during module discovery
            from mavaia_core.brain.registry import ModuleRegistry

            # Load cognitive generator
            self.cognitive_generator = ModuleRegistry.get_module("cognitive_generator")
            
            # Load universal voice engine for tone detection
            try:
                self.universal_voice_engine = ModuleRegistry.get_module("universal_voice_engine")
            except Exception as e:
                logger.debug(
                    "Failed to load optional universal_voice_engine",
                    exc_info=True,
                    extra={"module_name": "core_response_service", "error_type": type(e).__name__},
                )
            
            # Load tool registration
            self.tool_registration = ModuleRegistry.get_module("tool_registration_service")
            
            # Load safety framework
            self.safety_framework = ModuleRegistry.get_module("safety_framework")
            
            # Load tool calling agent
            self.tool_calling_agent = ModuleRegistry.get_module("tool_calling_agent_service")
            
            # Load conversational orchestrator
            self.conversational_orchestrator = ModuleRegistry.get_module("conversational_orchestrator")

            self._modules_loaded = True

            # Register tools on initialization (non-blocking)
            if self.tool_registration and not self._tools_registered:
                try:
                    self.tool_registration.execute("register_all_tools", {})
                    self._tools_registered = True
                except Exception as e:
                    logger.debug(
                        "Tool registration failed; continuing without pre-registration",
                        exc_info=True,
                        extra={"module_name": "core_response_service", "error_type": type(e).__name__},
                    )

        except Exception as e:
            # Modules not available - will use fallback methods
            logger.warning(
                "Failed to load dependent modules for core_response_service",
                exc_info=True,
                extra={"module_name": "core_response_service", "error_type": type(e).__name__},
            )

    def _ensure_safety_services_registered(self):
        """Ensure safety services are registered (lazy initialization)"""
        if self._safety_services_registered:
            return

        if self.safety_framework:
            try:
                # Register safety services on first use
                self.safety_framework.execute("register_all_safety_services", {})
                self._safety_services_registered = True
            except Exception as e:
                logger.debug(
                    "Safety service registration failed; continuing without registration",
                    exc_info=True,
                    extra={"module_name": "core_response_service", "error_type": type(e).__name__},
                )

    def _build_combined_context(
        self,
        app_context: str,
        payload_context: Optional[Dict[str, Any]],
        conversation_messages: Optional[List[Dict[str, str]]],
        tone_context: Optional[str],
    ) -> str:
        """Build combined context string from various context parameters"""
        context_parts = []

        if app_context:
            context_parts.append(app_context)

        if payload_context:
            context_info = []
            recall = payload_context.get("recall", [])
            if recall:
                context_info.append(f"{len(recall)} recall snippets")
            
            feedback = payload_context.get("feedback", [])
            if feedback:
                context_info.append(f"{len(feedback)} feedback items")
            
            narrative = payload_context.get("narrative_summary")
            if narrative:
                context_info.append("narrative summary")
            
            if context_info:
                context_parts.append(f"Additional context: {', '.join(context_info)}")

        if conversation_messages:
            recent = conversation_messages[-3:]
            recent_text = "\n".join([f"{m.get('role', 'user')}: {m.get('content', '')}" for m in recent])
            context_parts.append(f"Recent conversation:\n{recent_text}")

        if tone_context:
            context_parts.append(f"Tone: {tone_context}")

        return "\n\n".join(context_parts)

    def _build_voice_context(
        self,
        input_text: str,
        context: str = "",
        conversation_history: Optional[List[Dict[str, Any]]] = None,
    ) -> Dict[str, Any]:
        """Detect tone from user input and build voice_context"""
        if conversation_history is None:
            conversation_history = []
        
        # Use universal_voice_engine to detect tone if available
        if self.universal_voice_engine:
            try:
                tone_result = self.universal_voice_engine.execute(
                    "detect_tone_cues",
                    {
                        "input_text": input_text,
                        "conversation_history": conversation_history,
                        "context": context,
                    }
                )
                if tone_result.get("success"):
                    return tone_result.get("voice_context", {})
            except Exception:
                pass
        
        # Default voice context (Mavaia base)
        return {
            "base_personality": "mavaia",
            "tone": "neutral",
            "formality_level": 0.5,
            "technical_level": 0.3,
            "empathy_level": 0.6,
            "conversation_topic": "general",
            "user_history": [],
            "adaptation_confidence": 0.5,
        }

    def _convert_conversation_history(self, messages: Optional[List[Dict[str, str]]]) -> List[Dict[str, str]]:
        """Convert ConversationMessage array to history format for cognitive generator"""
        if not messages:
            return []

        history = []
        current_user_input = None

        for message in messages:
            role = message.get("role", "user")
            content = message.get("content", "")
            
            if role == "user":
                current_user_input = content
            elif role == "assistant" and current_user_input:
                history.append({
                    "input": current_user_input,
                    "response": content,
                })
                current_user_input = None

        return history

    def execute(self, operation: str, params: Dict[str, Any]) -> Dict[str, Any]:
        """Execute an operation"""
        self._ensure_modules_loaded()

        if operation == "generate_response":
            return self._generate_response(params)
        elif operation == "generate_response_with_app_context":
            return self._generate_response_with_app_context(params)
        elif operation == "generate_response_with_tools":
            return self._generate_response_with_tools(params)
        elif operation == "check_input":
            return self._check_input(params)
        elif operation == "check_response":
            return self._check_response(params)
        elif operation == "generate_conversation_title":
            return self._generate_conversation_title(params)
        elif operation == "generate_conversation_summary":
            return self._generate_conversation_summary(params)
        elif operation == "summarize_recent_messages":
            return self._summarize_recent_messages(params)
        elif operation == "generate_hybrid_phrase_for_completion":
            return self._generate_hybrid_phrase_for_completion(params)
        else:
            raise InvalidParameterError(
                parameter="operation",
                value=operation,
                reason="Unknown operation for core_response_service",
            )

    def _generate_response(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """Generate a simple response"""
        input_text = params.get("input", "")
        context = params.get("context", "")
        conversation_history = params.get("conversation_history", [])

        if not self.cognitive_generator:
            return {
                "success": False,
                "error": "Cognitive generator not available",
                "text": "",
            }

        # Detect tone and build voice_context
        voice_context = self._build_voice_context(input_text, context, conversation_history)

        try:
            result = self.cognitive_generator.execute("generate_response", {
                "input": input_text,
                "context": context or "You are a helpful assistant.",
                "voice_context": voice_context,
                "conversation_history": conversation_history,
            })

            return {
                "success": True,
                "text": result.get("text", ""),
                "confidence": result.get("confidence", 0.5),
                "diagnostic": result.get("diagnostic"),
            }
        except Exception as e:
            return {
                "success": False,
                "error": str(e),
                "text": "",
            }

    def _generate_response_with_app_context(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """Generate response with full app context"""
        input_text = params.get("input", "")
        app_context = params.get("app_context", "")
        payload_context = params.get("payload_context")
        conversation_messages = params.get("conversation_messages")
        tone_context = params.get("tone_context")

        # Build combined context
        combined_context = self._build_combined_context(
            app_context,
            payload_context,
            conversation_messages,
            tone_context,
        )

        # Convert conversation messages to history format
        history = self._convert_conversation_history(conversation_messages)

        # Detect tone and build voice_context
        voice_context = self._build_voice_context(input_text, combined_context, history)

        # Use conversational orchestrator if available, otherwise fall back to cognitive generator
        if self.conversational_orchestrator:
            try:
                result = self.conversational_orchestrator.execute("generate_conversational_response", {
                    "input": input_text,
                    "context": combined_context,
                    "voice_context": voice_context,
                    "conversation_id": params.get("conversation_id"),
                    "external_history": history,
                })

                return {
                    "success": True,
                    "text": result.get("text", ""),
                    "confidence": result.get("confidence", 0.5),
                    "diagnostic": result.get("diagnostic"),
                    "model_used": result.get("model_used", "cognitive_generator"),
                }
            except Exception as e:
                # Fall back to cognitive generator
                logger.debug(
                    "Conversational orchestrator failed; falling back to cognitive_generator",
                    exc_info=True,
                    extra={"module_name": "core_response_service", "error_type": type(e).__name__},
                )

        # Fall back to cognitive generator
        return self._generate_response({
            "input": input_text,
            "context": combined_context,
            "conversation_history": history,
        })

    def _generate_response_with_tools(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """Generate response with tool calling support"""
        input_text = params.get("input", "")
        tools = params.get("tools", [])
        context = params.get("context", "")

        if not self.tool_calling_agent:
            # Fall back to regular generation
            return self._generate_response({
                "input": input_text,
                "context": context,
            })

        try:
            result = self.tool_calling_agent.execute("execute_agent_loop", {
                "query": input_text,
                "tools": tools,
                "system_prompt": params.get("system_prompt"),
                "conversation_history": params.get("conversation_history"),
                "use_planning": params.get("use_planning", True),
            })

            return {
                "success": True,
                "text": result.get("final_response", ""),
                "tool_calls": result.get("tool_calls", []),
                "tool_results": result.get("tool_results", []),
                "iterations": result.get("iterations", 0),
            }
        except Exception as e:
            return {
                "success": False,
                "error": str(e),
                "text": "",
            }

    def _check_input(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """Check input for safety issues"""
        self._ensure_safety_services_registered()

        input_text = params.get("input", "")

        if not self.safety_framework:
            return {
                "success": True,
                "is_safe": True,
                "issues": [],
            }

        try:
            result = self.safety_framework.execute("check_input", {
                "input": input_text,
            })

            return {
                "success": True,
                "is_safe": result.get("is_safe", True),
                "issues": result.get("issues", []),
                "warnings": result.get("warnings", []),
            }
        except Exception as e:
            return {
                "success": False,
                "error": str(e),
                "is_safe": True,  # Default to safe if check fails
            }

    def _check_response(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """Check response for safety issues"""
        self._ensure_safety_services_registered()

        response_text = params.get("response", "")

        if not self.safety_framework:
            return {
                "success": True,
                "is_safe": True,
                "issues": [],
            }

        try:
            result = self.safety_framework.execute("check_response", {
                "response": response_text,
            })

            return {
                "success": True,
                "is_safe": result.get("is_safe", True),
                "issues": result.get("issues", []),
                "warnings": result.get("warnings", []),
            }
        except Exception as e:
            return {
                "success": False,
                "error": str(e),
                "is_safe": True,  # Default to safe if check fails
            }

    def _generate_conversation_title(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """Generate conversation title from first message"""
        first_message = params.get("first_message", "")

        if not self.cognitive_generator:
            return {
                "success": False,
                "error": "Cognitive generator not available",
                "title": "",
            }

        try:
            result = self.cognitive_generator.execute("generate_title", {
                "from": first_message,
            })

            return {
                "success": True,
                "title": result.get("title", ""),
            }
        except Exception as e:
            return {
                "success": False,
                "error": str(e),
                "title": "",
            }

    def _generate_conversation_summary(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """Generate conversation summary from messages"""
        messages = params.get("messages", [])

        if not messages:
            return {
                "success": False,
                "error": "No messages provided",
                "summary": "",
            }

        conversation_text = "\n\n".join([
            f"{m.get('role', 'user').capitalize()}: {m.get('content', '')}"
            for m in messages
        ])

        if not self.cognitive_generator:
            return {
                "success": False,
                "error": "Cognitive generator not available",
                "summary": "",
            }

        try:
            result = self.cognitive_generator.execute("generate_summary", {
                "content": conversation_text,
                "max_sentences": params.get("max_sentences", 3),
            })

            return {
                "success": True,
                "summary": result.get("summary", ""),
            }
        except Exception as e:
            return {
                "success": False,
                "error": str(e),
                "summary": "",
            }

    def _summarize_recent_messages(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """Summarize recent messages"""
        messages = params.get("messages", [])
        count = params.get("count", 5)

        recent = messages[-count:] if len(messages) > count else messages

        return self._generate_conversation_summary({
            "messages": recent,
            "max_sentences": 2,
        })

    def _generate_hybrid_phrase_for_completion(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """Generate hybrid phrase for phrase completion"""
        context = params.get("context", "")
        keyword = params.get("keyword")
        max_length = params.get("max_length", 15)
        use_hybrid_phrasing = params.get("use_hybrid_phrasing", True)

        # Try to use hybrid phrasing service if available
        try:
            from mavaia_core.brain.registry import ModuleRegistry
            hybrid_phrasing = ModuleRegistry.get_module("hybrid_phrasing_service")
            
            if hybrid_phrasing and use_hybrid_phrasing:
                result = hybrid_phrasing.execute("generate_hybrid_phrase", {
                    "context": context,
                    "keyword": keyword,
                    "max_length": max_length,
                })
                return {
                    "success": True,
                    "phrase": result.get("phrase"),
                }
        except Exception as e:
            logger.debug(
                "Hybrid phrasing failed; using simple completion",
                exc_info=True,
                extra={"module_name": "core_response_service", "error_type": type(e).__name__},
            )

        # Fall back to simple completion
        return {
            "success": True,
            "phrase": context[:max_length] if len(context) > max_length else context,
        }

