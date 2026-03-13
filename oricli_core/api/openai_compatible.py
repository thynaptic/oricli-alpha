from __future__ import annotations
"""
OpenAI-Compatible API Implementation
Provides OpenAI-compatible endpoints for chat completions, embeddings, and models
"""

import os
import time
from typing import List, Optional, Dict, Any
from fastapi import HTTPException, Header, Request
from fastapi.responses import StreamingResponse
import json

from oricli_core.client import OricliAlphaClient
from oricli_core.exceptions import AuthenticationError
from oricli_core.services.tool_registry import ToolRegistry
from oricli_core.types.models import (
    ChatCompletionRequest,
    ChatCompletionResponse,
    EmbeddingRequest,
    EmbeddingResponse,
    ModelsListResponse,
    ToolDefinition,
)


class OpenAICompatibleAPI:
    """OpenAI-compatible API handler"""
    
    def __init__(
        self,
        client: Optional[OricliAlphaClient] = None,
        api_key: Optional[str] = None,
        require_auth: bool = False
    ):
        """
        Initialize OpenAI-compatible API
        
        Args:
            client: Optional OricliAlphaClient instance (creates new one if not provided)
            api_key: Optional API key for validation (defaults to MAVAIA_API_KEY env var)
            require_auth: Whether to require authentication (defaults to False)
        """
        self.client = client or OricliAlphaClient()
        # Get API key from parameter, environment variable, or None
        self.api_key = api_key or os.getenv("MAVAIA_API_KEY")
        self.require_auth = require_auth or os.getenv("MAVAIA_REQUIRE_AUTH", "false").lower() == "true"
    
    def verify_api_key(
        self, authorization: Optional[str] = None
    ) -> bool:
        """
        Verify API key from Authorization header
        
        Args:
            authorization: Authorization header value (optional)
        
        Returns:
            True if valid or authentication not required, False otherwise
        
        Raises:
            AuthenticationError: If authentication is required but invalid
        """
        # If no API key is configured and auth is not required, allow all requests
        if not self.api_key and not self.require_auth:
            return True
        
        # If auth is required but no API key is configured, reject all requests
        if self.require_auth and not self.api_key:
            raise AuthenticationError("API key not configured but authentication is required")
        
        # If no authorization header provided
        if authorization is None:
            if self.require_auth:
                raise AuthenticationError("Authorization header required")
            # If auth not required, allow unauthenticated requests
            return True
        
        # Check for Bearer token format
        if not authorization.startswith("Bearer "):
            raise AuthenticationError("Invalid authorization format. Expected 'Bearer <token>'")
        
        # Extract API key from Bearer token
        provided_key = authorization[7:].strip()
        
        # Validate API key
        if not provided_key:
            raise AuthenticationError("Empty API key provided")
        
        if self.api_key and provided_key != self.api_key:
            raise AuthenticationError("Invalid API key")
        
        return True
    
    def _expand_tool_references(self, tools: Optional[List[Any]]) -> Optional[List[ToolDefinition]]:
        """
        Expand tool_reference blocks to full tool definitions.
        
        Args:
            tools: List of tool definitions that may contain tool_reference blocks
                   Can be ToolDefinition objects or dicts
            
        Returns:
            List of expanded tool definitions
        """
        if not tools:
            return None
        
        tool_registry = ToolRegistry()
        expanded_tools = []
        
        for tool in tools:
            # Check if this is a tool_reference (dict with type="tool_reference")
            tool_dict = tool.dict() if isinstance(tool, ToolDefinition) else tool
            
            if isinstance(tool_dict, dict) and tool_dict.get("type") == "tool_reference":
                tool_name = tool_dict.get("name")
                if tool_name:
                    # Get full tool definition from registry
                    tool_def = tool_registry.get_tool(tool_name)
                    if tool_def:
                        # Convert to ToolDefinition model
                        expanded_tools.append(ToolDefinition(
                            name=tool_def.name,
                            description=tool_def.description,
                            parameters=tool_def.parameters,
                            allowed_callers=tool_def.allowed_callers,
                            result_format=tool_def.result_format,
                            defer_loading=tool_def.defer_loading,
                        ))
            elif isinstance(tool, ToolDefinition):
                # Already a full tool definition
                expanded_tools.append(tool)
            elif isinstance(tool_dict, dict):
                # Convert dict to ToolDefinition
                try:
                    expanded_tools.append(ToolDefinition(**tool_dict))
                except Exception:
                    # Skip invalid tool definitions
                    pass
        
        return expanded_tools if expanded_tools else None
    
    async def chat_completions(
        self,
        request: ChatCompletionRequest,
        authorization: Optional[str] = Header(None, alias="Authorization")
    ) -> ChatCompletionResponse:
        """
        Create chat completion (OpenAI-compatible)
        
        POST /v1/chat/completions
        """
        # Verify API key
        try:
            self.verify_api_key(authorization)
        except AuthenticationError as e:
            raise HTTPException(
                status_code=401,
                detail=str(e)
            ) from e
        
        # 1. PRE-COG CACHE CHECK (New Step)
        # Try to deliver an instant speculative answer
        try:
            from oricli_core.services.precog_service import PreCogService
            precog = PreCogService()
            last_message = request.messages[-1].get_text_content() if request.messages else ""
            if last_message:
                cached = precog.get_cached_response(last_message)
                if cached:
                    # deliver instantly (must be formatted as ChatCompletionResponse)
                    # For now, we assume the cache stores the full response object or enough to reconstruct it
                    if isinstance(cached, ChatCompletionResponse):
                        return cached
                    elif isinstance(cached, dict):
                        # Reconstruct if it's a dict from pipeline result
                        # Note: This is a simplified reconstruction
                        from oricli_core.types.models import ChatCompletionChoice, ChatCompletionMessage
                        content = cached.get("answer") or cached.get("text") or ""
                        if content:
                            return ChatCompletionResponse(
                                id=f"precog-{int(time.time())}",
                                object="chat.completion",
                                created=int(time.time()),
                                model=request.model,
                                choices=[ChatCompletionChoice(
                                    index=0,
                                    message=ChatCompletionMessage(role="assistant", content=content),
                                    finish_reason="stop"
                                )],
                                usage={"prompt_tokens": 0, "completion_tokens": 0, "total_tokens": 0}
                            )
        except Exception as e:
            # Pre-cog failure is non-blocking
            pass

        try:
            # Expand tool references if present
            expanded_tools = None
            if request.tools:
                expanded_tools = self._expand_tool_references(request.tools)
            
            # Handle streaming
            if request.stream:
                return await self._stream_chat_completion(request)
            
            # Non-streaming response
            # Extract text content from messages (handles both string and multimodal formats)
            response = self.client.chat.completions.create(
                model=request.model,
                messages=[
                    {"role": msg.role, "content": msg.get_text_content()}
                    for msg in request.messages
                ],
                temperature=request.temperature,
                max_tokens=request.max_tokens,
                stream=False,
                personality_id=request.personality_id,
                use_memory=request.use_memory,
                use_reasoning=request.use_reasoning,
                tools=[tool.dict() for tool in expanded_tools] if expanded_tools else None,
            )
            
            # 2. TRIGGER SPECULATION (New Step)
            # While the user is reading, anticipate the next question
            try:
                from oricli_core.brain.registry import ModuleRegistry
                speculator = ModuleRegistry.get_module("speculator")
                if speculator and response.choices:
                    speculator.execute("speculate", {
                        "conversation_history": [m.dict() for m in request.messages],
                        "last_input": request.messages[-1].get_text_content() if request.messages else "",
                        "last_output": response.choices[0].message.content
                    })
            except Exception:
                pass

            return response
        
        except HTTPException:
            raise
        except Exception as e:
            raise HTTPException(
                status_code=500,
                detail=f"Error generating chat completion: {str(e)}"
            )
    
    async def _stream_chat_completion(
        self, request: ChatCompletionRequest
    ) -> StreamingResponse:
        """Stream chat completion response."""
        # Generate once (non-streaming) and simulate streaming.
        response = self.client.chat.completions.create(
            model=request.model,
            messages=[
                {"role": msg.role, "content": msg.get_text_content()}
                for msg in request.messages
            ],
            temperature=request.temperature,
            max_tokens=request.max_tokens,
            stream=False,
            personality_id=request.personality_id,
            use_memory=request.use_memory,
            use_reasoning=request.use_reasoning,
        )

        trace_id = None
        try:
            if response.metadata and isinstance(response.metadata, dict):
                trace_id = response.metadata.get("trace_id")
        except Exception:
            trace_id = None

        async def generate():
            try:
                content = response.choices[0].message.content
                chunk_size = 10  # Characters per chunk

                for i in range(0, len(content), chunk_size):
                    chunk = content[i:i + chunk_size]
                    chunk_data = {
                        "id": response.id,
                        "object": "chat.completion.chunk",
                        "created": response.created,
                        "model": response.model,
                        "choices": [{
                            "index": 0,
                            "delta": {"content": chunk},
                            "finish_reason": None
                        }]
                    }
                    yield f"data: {json.dumps(chunk_data)}\n\n"

                final_chunk = {
                    "id": response.id,
                    "object": "chat.completion.chunk",
                    "created": response.created,
                    "model": response.model,
                    "choices": [{
                        "index": 0,
                        "delta": {},
                        "finish_reason": "stop"
                    }]
                }
                yield f"data: {json.dumps(final_chunk)}\n\n"
                yield "data: [DONE]\n\n"

            except Exception as e:
                error_data = {
                    "error": {
                        "message": str(e),
                        "type": "server_error",
                        "code": 500
                    }
                }
                yield f"data: {json.dumps(error_data)}\n\n"

        headers = {
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
        }
        if trace_id:
            headers["X-OricliAlpha-Trace-Id"] = str(trace_id)

        return StreamingResponse(
            generate(),
            media_type="text/event-stream",
            headers=headers,
        )
    
    async def embeddings(
        self,
        request: EmbeddingRequest,
        authorization: Optional[str] = Header(None, alias="Authorization")
    ) -> EmbeddingResponse:
        """
        Create embeddings (OpenAI-compatible)
        
        POST /v1/embeddings
        """
        # Verify API key
        try:
            self.verify_api_key(authorization)
        except AuthenticationError as e:
            raise HTTPException(
                status_code=401,
                detail=str(e)
            ) from e
        
        try:
            response = self.client.embeddings.create(
                input=request.input,
                model=request.model,
            )
            
            return response
        
        except HTTPException:
            raise
        except Exception as e:
            raise HTTPException(
                status_code=500,
                detail=f"Error generating embeddings: {str(e)}"
            )
    
    async def models(
        self,
        authorization: Optional[str] = Header(None, alias="Authorization")
    ) -> ModelsListResponse:
        """
        List available models (OpenAI-compatible)
        
        GET /v1/models
        """
        # Verify API key
        try:
            self.verify_api_key(authorization)
        except AuthenticationError as e:
            raise HTTPException(
                status_code=401,
                detail=str(e)
            ) from e
        
        try:
            return self.client.list_models()
        
        except HTTPException:
            raise
        except Exception as e:
            raise HTTPException(
                status_code=500,
                detail=f"Error listing models: {str(e)}"
            )

