from __future__ import annotations

import sys
from pathlib import Path
from unittest.mock import MagicMock, patch

REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT))

from oricli_core.brain.modules.ollama_provider import OllamaProviderModule


def _mock_response(status_code: int, payload: dict) -> MagicMock:
    response = MagicMock()
    response.status_code = status_code
    response.ok = 200 <= status_code < 300
    response.json.return_value = payload
    response.text = str(payload)
    return response


def test_generate_uses_native_generate_endpoint():
    provider = OllamaProviderModule()

    with patch("requests.post") as mock_post:
        mock_post.return_value = _mock_response(200, {"response": "hello from qwen", "done": True})

        result = provider.execute("generate", {"prompt": "hello"})

    assert result["success"] is True
    assert result["text"] == "hello from qwen"
    assert result["model"] == provider.default_model
    assert result["method"] == "ollama"


def test_generate_falls_back_to_chat_when_generate_fails():
    provider = OllamaProviderModule()

    with patch("requests.post") as mock_post:
        mock_post.side_effect = [
            _mock_response(404, {"error": "endpoint not found"}),
            _mock_response(200, {"message": {"content": "chat fallback works"}, "done": True}),
        ]

        result = provider.execute("generate", {"prompt": "hello"})

    assert result["success"] is True
    assert result["text"] == "chat fallback works"
    assert result["method"] == "ollama_chat_fallback"


def test_generate_reports_missing_requested_model():
    provider = OllamaProviderModule()

    with patch("requests.post") as mock_post, patch("requests.get") as mock_get:
        mock_post.return_value = _mock_response(404, {"error": "model 'qwen2.5:7b' not found"})
        mock_get.return_value = _mock_response(
            200,
            {
                "models": [
                    {"name": "llama3.2:latest"},
                    {"name": "mxbai-embed-large:latest"},
                ]
            },
        )

        result = provider.execute("generate", {"prompt": "hello"})

    assert result["success"] is False
    assert "qwen2.5:7b" in result["error"]
    assert "llama3.2:latest" in result["error"]
    assert result["available_models"] == ["llama3.2:latest", "mxbai-embed-large:latest"]


def test_list_models_falls_back_to_openai_models_endpoint():
    provider = OllamaProviderModule()

    with patch("requests.get") as mock_get:
        mock_get.side_effect = [
            _mock_response(404, {"error": "not found"}),
            _mock_response(200, {"data": [{"id": "qwen2.5:7b"}, {"id": "llama3.2:latest"}]}),
        ]

        result = provider.execute("list_models", {})

    assert result["success"] is True
    assert result["models"][0]["name"] == "qwen2.5:7b"
