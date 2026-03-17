from __future__ import annotations
"""
Ollama Provider Module
Provides text generation and chat capabilities using a local Ollama instance.
Part of the strategic pivot to offload prose and light reasoning.
"""

import logging
import os
from typing import Any, Dict

import requests

from oricli_core.brain.base_module import BaseBrainModule, ModuleMetadata
from oricli_core.exceptions import InvalidParameterError

logger = logging.getLogger(__name__)

PRIMARY_OLLAMA_MODEL = "ministral-3:3b"


class OllamaProviderModule(BaseBrainModule):
    """Bridge to local Ollama API for text generation and light reasoning."""

    def __init__(self):
        super().__init__()
        # Default to localhost:11434, allow override via env
        self.base_url = os.getenv("OLLAMA_URL", "http://localhost:11434")
        self.default_model = os.getenv("OLLAMA_MODEL", PRIMARY_OLLAMA_MODEL)

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
        """Generate text using Ollama-compatible endpoints."""
        prompt = params.get("prompt", "")
        if not prompt:
            prompt = params.get("input") or params.get("text") or params.get("query", "")

        model = str(params.get("model", self.default_model) or self.default_model)
        system = params.get("system", "")
        options = dict(params.get("options", {}))

        if "temperature" in params:
            options["temperature"] = params["temperature"]
        if "max_tokens" in params:
            options["num_predict"] = params["max_tokens"]
        if "top_p" in params:
            options["top_p"] = params["top_p"]
            
        # Limit CPU usage per request
        options["num_thread"] = 2

        generate_payload = {
            "model": model,
            "prompt": str(prompt),
            "stream": False,
            "system": system,
            "template": params.get("template", ""),
            "options": options,
        }

        native_generate = self._post_json("/api/generate", generate_payload, timeout=120)
        if native_generate.get("success"):
            result = native_generate["data"]
            response_text = result.get("response", "")
            return {
                "success": True,
                "text": response_text,
                "response": response_text,
                "model": model,
                "done": result.get("done", True),
                "method": "ollama",
            }

        if self._is_model_missing_error(native_generate.get("error", "")):
            available_models = self._available_model_names()
            error = self._format_missing_model_error(model, available_models)
            logger.warning("Ollama generate failed: %s", error)
            return {
                "success": False,
                "error": error,
                "model": model,
                "available_models": available_models,
                "method": "ollama",
            }

        chat_payload = {
            "model": model,
            "messages": self._build_messages(prompt, system),
            "stream": False,
            "options": options,
        }

        native_chat = self._post_json("/api/chat", chat_payload, timeout=120)
        if native_chat.get("success"):
            chat_result = native_chat["data"]
            chat_content = chat_result.get("message", {}).get("content", "")
            return {
                "success": True,
                "text": chat_content,
                "response": chat_content,
                "model": model,
                "done": chat_result.get("done", True),
                "method": "ollama_chat_fallback",
            }

        openai_chat = self._post_json(
            "/v1/chat/completions",
            {
                "model": model,
                "messages": self._build_messages(prompt, system),
                "temperature": params.get("temperature", 0.7),
                "max_tokens": params.get("max_tokens", 1024),
                "stream": False,
            },
            timeout=120,
        )
        if openai_chat.get("success"):
            completion = openai_chat["data"]
            content = (
                completion.get("choices", [{}])[0]
                .get("message", {})
                .get("content", "")
            )
            return {
                "success": True,
                "text": content,
                "response": content,
                "model": model,
                "done": True,
                "method": "ollama_openai_fallback",
            }

        combined_error = (
            f"generate={native_generate.get('error', 'unknown error')}; "
            f"chat={native_chat.get('error', 'unknown error')}; "
            f"openai={openai_chat.get('error', 'unknown error')}"
        )
        logger.warning("Ollama generate failed: %s", combined_error)
        return {"success": False, "error": combined_error, "model": model}

    def _chat(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """Proxy to Ollama /api/chat endpoint."""
        messages = params.get("messages", [])
        model = str(params.get("model", self.default_model) or self.default_model)
        options = dict(params.get("options", {}))

        if "temperature" in params:
            options["temperature"] = params["temperature"]
            
        options["num_thread"] = 2

        payload = {"model": model, "messages": messages, "stream": False, "options": options}

        native_chat = self._post_json("/api/chat", payload, timeout=120)
        if native_chat.get("success"):
            result = native_chat["data"]
            chat_content = result.get("message", {}).get("content", "")
            return {
                "success": True,
                "text": chat_content,
                "response": chat_content,
                "model": model,
                "done": result.get("done", True),
                "method": "ollama_chat",
            }

        openai_chat = self._post_json(
            "/v1/chat/completions",
            {
                "model": model,
                "messages": messages,
                "temperature": params.get("temperature", 0.7),
                "max_tokens": params.get("max_tokens", 1024),
                "stream": False,
            },
            timeout=120,
        )
        if openai_chat.get("success"):
            completion = openai_chat["data"]
            content = (
                completion.get("choices", [{}])[0]
                .get("message", {})
                .get("content", "")
            )
            return {
                "success": True,
                "text": content,
                "response": content,
                "model": model,
                "done": True,
                "method": "ollama_chat_openai_fallback",
            }

        error = (
            f"chat={native_chat.get('error', 'unknown error')}; "
            f"openai={openai_chat.get('error', 'unknown error')}"
        )
        logger.warning("Ollama chat failed: %s", error)
        return {"success": False, "error": error, "model": model}

    def _list_models(self) -> Dict[str, Any]:
        """List locally pulled Ollama models."""
        native_tags = self._get_json("/api/tags", timeout=5)
        if native_tags.get("success"):
            return {"success": True, "models": native_tags["data"].get("models", [])}

        openai_models = self._get_json("/v1/models", timeout=5)
        if openai_models.get("success"):
            models = openai_models["data"].get("data", [])
            return {
                "success": True,
                "models": [{"name": item.get("id"), "model": item.get("id")} for item in models],
            }

        return {
            "success": False,
            "error": (
                f"tags={native_tags.get('error', 'unknown error')}; "
                f"models={openai_models.get('error', 'unknown error')}"
            ),
        }

    def _build_messages(self, prompt: str, system: str) -> list[dict[str, str]]:
        messages: list[dict[str, str]] = []
        if system:
            messages.append({"role": "system", "content": str(system)})
        messages.append({"role": "user", "content": str(prompt)})
        return messages

    def _post_json(self, path: str, payload: Dict[str, Any], timeout: int) -> Dict[str, Any]:
        try:
            response = requests.post(
                f"{self.base_url.rstrip('/')}{path}",
                json=payload,
                timeout=timeout,
            )
            if response.ok:
                return {"success": True, "data": response.json()}
            return {
                "success": False,
                "status_code": response.status_code,
                "error": self._response_error(response),
            }
        except requests.RequestException as exc:
            return {"success": False, "error": str(exc)}

    def _get_json(self, path: str, timeout: int) -> Dict[str, Any]:
        try:
            response = requests.get(f"{self.base_url.rstrip('/')}{path}", timeout=timeout)
            if response.ok:
                return {"success": True, "data": response.json()}
            return {
                "success": False,
                "status_code": response.status_code,
                "error": self._response_error(response),
            }
        except requests.RequestException as exc:
            return {"success": False, "error": str(exc)}

    def _response_error(self, response: requests.Response) -> str:
        try:
            data = response.json()
            if isinstance(data, dict) and data.get("error"):
                return str(data["error"])
        except ValueError:
            pass
        return f"HTTP {response.status_code}: {response.text.strip()}"

    def _is_model_missing_error(self, error: str) -> bool:
        lowered = error.lower()
        return "model" in lowered and "not found" in lowered

    def _available_model_names(self) -> list[str]:
        listed = self._list_models()
        if not listed.get("success"):
            return []
        names: list[str] = []
        for model in listed.get("models", []):
            if isinstance(model, dict):
                name = model.get("name") or model.get("model") or model.get("id")
                if name:
                    names.append(str(name))
        return names

    def _format_missing_model_error(self, requested_model: str, available_models: list[str]) -> str:
        if available_models:
            return (
                f"Ollama model '{requested_model}' is not installed at {self.base_url}. "
                f"Available models: {', '.join(sorted(available_models))}"
            )
        return f"Ollama model '{requested_model}' is not installed at {self.base_url}"
