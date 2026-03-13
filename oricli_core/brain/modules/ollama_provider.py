from __future__ import annotations
"""
Ollama Provider Module
Provides text generation and chat capabilities using a local Ollama instance.
Part of the strategic pivot to offload prose and light reasoning.
"""

import requests
import json
import logging
import os
from typing import Dict, Any, List, Optional
from oricli_core.brain.base_module import BaseBrainModule, ModuleMetadata
from oricli_core.exceptions import InvalidParameterError

logger = logging.getLogger(__name__)

class OllamaProviderModule(BaseBrainModule):
    """Bridge to local Ollama API for text generation and light reasoning."""

    def __init__(self):
        super().__init__()
        # Default to localhost:11434, allow override via env
        self.base_url = os.getenv("OLLAMA_URL", "http://localhost:11434")
        self.default_model = os.getenv("OLLAMA_MODEL", "qwen2.5:7b")

    @property
    def metadata(self) -> ModuleMetadata:
        return ModuleMetadata(
            name="ollama_provider",
            version="1.0.0",
            description="Interface for local Ollama text generation and reasoning",
            operations=["generate", "chat", "list_models", "generate_text"],
            dependencies=[],
            model_required=False,
        )

    def execute(self, operation: str, params: Dict[str, Any]) -> Dict[str, Any]:
        # Support both 'generate' and 'generate_text' for drop-in compatibility
        if operation in ["generate", "generate_text"]:
            return self._generate(params)
        elif operation == "chat":
            return self._chat(params)
        elif operation == "list_models":
            return self._list_models()
        else:
            raise InvalidParameterError(parameter="operation", value=operation, reason="Unsupported operation")

    def _generate(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """Proxy to Ollama /api/generate endpoint."""
        prompt = params.get("prompt", "")
        if not prompt:
            prompt = params.get("input") or params.get("text") or params.get("query", "")
            
        model = params.get("model", self.default_model)
        system = params.get("system", "")
        template = params.get("template", "")
        options = params.get("options", {})
        
        # Mapping standard params to Ollama options
        if "temperature" in params:
            options["temperature"] = params["temperature"]
        if "max_tokens" in params:
            options["num_predict"] = params["max_tokens"]
        if "top_p" in params:
            options["top_p"] = params["top_p"]
        
        payload = {
            "model": model,
            "prompt": str(prompt),
            "stream": False,
            "system": system,
            "template": template,
            "options": options
        }
        
        try:
            # Short timeout for reachability check, longer for generation
            resp = requests.post(f"{self.base_url.rstrip('/')}/api/generate", json=payload, timeout=90)
            resp.raise_for_status()
            result = resp.json()
            
            response_text = result.get("response", "")
            
            return {
                "success": True,
                "text": response_text,
                "response": response_text,
                "model": model,
                "done": result.get("done", True),
                "method": "ollama"
            }
        except Exception as e:
            logger.warning(f"Ollama generate failed: {e}")
            return {"success": False, "error": str(e)}

    def _chat(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """Proxy to Ollama /api/chat endpoint."""
        messages = params.get("messages", [])
        model = params.get("model", self.default_model)
        options = params.get("options", {})
        
        if "temperature" in params:
            options["temperature"] = params["temperature"]
            
        payload = {
            "model": model,
            "messages": messages,
            "stream": False,
            "options": options
        }
        
        try:
            resp = requests.post(f"{self.base_url.rstrip('/')}/api/chat", json=payload, timeout=90)
            resp.raise_for_status()
            result = resp.json()
            
            chat_content = result.get("message", {}).get("content", "")
            
            return {
                "success": True,
                "text": chat_content,
                "response": chat_content,
                "model": model,
                "done": result.get("done", True),
                "method": "ollama_chat"
            }
        except Exception as e:
            logger.warning(f"Ollama chat failed: {e}")
            return {"success": False, "error": str(e)}

    def _list_models(self) -> Dict[str, Any]:
        """List locally pulled Ollama models."""
        try:
            resp = requests.get(f"{self.base_url.rstrip('/')}/api/tags", timeout=5)
            resp.raise_for_status()
            return {"success": True, "models": resp.json().get("models", [])}
        except Exception as e:
            return {"success": False, "error": str(e)}
