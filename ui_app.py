"""
Production-ready Flask UI server for OricliAlpha Core.

Routes:
- "/" serves the SPA shell
- "/static/*" serves JS/CSS assets
- "/chat" proxies to the OpenAI-compatible chat endpoint (streaming supported)
- "/models" proxies to the models endpoint
- "/modules" proxies to the modules listing endpoint
- "/embeddings" proxies to the embeddings endpoint
- "/health" returns health status with API connectivity check
- "/events" stub for future tracing/logging
"""

from __future__ import annotations

import json
import logging
import math
import os
import re
import signal as _signal
import subprocess as _subprocess
import sys
import threading
import time
import uuid
import secrets
import urllib.parse
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Dict, Iterable, Optional

try:
    import httpx
    from httpx import ConnectError, HTTPStatusError
except ImportError:
    print(
        "Error: httpx is not installed. Install dependencies with: pip install -e .",
        file=sys.stderr
    )
    sys.exit(1)

try:
    from flask import Flask, Response, jsonify, request, send_from_directory
except ImportError:
    print(
        "Error: Flask is not installed. Install dependencies with: pip install -e .",
        file=sys.stderr
    )
    sys.exit(1)

try:
    from flask_cors import CORS
    CORS_AVAILABLE = True
except ImportError:
    CORS_AVAILABLE = False


STATIC_DIR = Path(__file__).parent / "ui_static"
API_BASE    = os.getenv("MAVAIA_API_BASE",    "http://localhost:8089")   # Go backbone
OLLAMA_BASE = os.getenv("MAVAIA_OLLAMA_BASE", "http://localhost:11434")  # Ollama
API_KEY = os.getenv("MAVAIA_API_KEY")
ATTACHMENT_LIMIT_MB = float(os.getenv("MAVAIA_UI_ATTACHMENT_MB", "5"))
MAX_ATTACHMENT_BYTES = int(ATTACHMENT_LIMIT_MB * 1024 * 1024)
RETRY_COUNT = 3

# Google OAuth2
GOOGLE_CLIENT_ID     = os.getenv("GOOGLE_OAUTH_CLIENT_ID", "357323906391-2b5pfagemqmfglk1j5u7uln8jqtpmfvh.apps.googleusercontent.com")
GOOGLE_CLIENT_SECRET = os.getenv("GOOGLE_OAUTH_CLIENT_SECRET", "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")
GOOGLE_REDIRECT_URI  = "https://sovereignclaw.thynaptic.com/connections/oauth/callback/google"
GOOGLE_SCOPES = " ".join([
    "openid", "email", "profile",
    "https://www.googleapis.com/auth/gmail.readonly",
    "https://www.googleapis.com/auth/drive.readonly",
    "https://www.googleapis.com/auth/calendar.readonly",
    "https://www.googleapis.com/auth/documents.readonly",
    "https://www.googleapis.com/auth/tasks.readonly",
    "https://www.googleapis.com/auth/forms.body.readonly",
    "https://www.googleapis.com/auth/spreadsheets.readonly",
])
_OAUTH_STATES: dict[str, float] = {}  # state -> created_at timestamp (CSRF guard)

app = Flask(__name__, static_folder=str(STATIC_DIR))
if CORS_AVAILABLE:
    CORS(app)  # Enable CORS for production use if available

log = logging.getLogger(__name__)


def _client() -> httpx.Client:
    return httpx.Client(timeout=None)


def _backoff(attempt: int) -> float:
    return min(2 ** attempt, 8)


def _build_headers(extra: Optional[Dict[str, str]] = None) -> Dict[str, str]:
    headers: Dict[str, str] = {}
    if API_KEY:
        headers["Authorization"] = f"Bearer {API_KEY}"
    if extra:
        headers.update(extra)
    return headers


def _approx_base64_size(b64_string: str) -> int:
    # Rough size approximation of base64 payload
    return int(len(b64_string) * 3 / 4)


def _enforce_attachment_limit(payload: Dict[str, Any]) -> None:
    total_bytes = 0

    # Attachments array (preferred)
    for att in payload.get("attachments", []):
        if isinstance(att, dict):
            data = att.get("data")
            if isinstance(data, str):
                total_bytes += _approx_base64_size(data)

    # Embedded in message content blocks (fallback)
    for message in payload.get("messages", []):
        contents = message.get("content")
        if isinstance(contents, list):
            for part in contents:
                if isinstance(part, dict):
                    data = part.get("data") or part.get("file", {}).get("data")
                    if isinstance(data, str):
                        total_bytes += _approx_base64_size(data)

    if total_bytes > MAX_ATTACHMENT_BYTES:
        raise ValueError(
            f"Attachments exceed limit of {ATTACHMENT_LIMIT_MB} MB (got ~{total_bytes / 1_048_576:.2f} MB)"
        )


def _forward_with_retry(
    method: str, url: str, *, json_body: Optional[Dict[str, Any]] = None
) -> httpx.Response:
    last_exc: Optional[Exception] = None
    for attempt in range(RETRY_COUNT):
        try:
            with _client() as client:
                resp = client.request(
                    method, url, json=json_body, headers=_build_headers(), timeout=None
                )
                resp.raise_for_status()
                return resp
        except Exception as exc:  # noqa: BLE001
            last_exc = exc
            if attempt < RETRY_COUNT - 1:
                time.sleep(_backoff(attempt))
                continue
            raise last_exc
    raise RuntimeError("Unreachable")


@app.route("/health", methods=["GET"])
def health() -> Response:
    """Health check — backbone + Ollama connectivity."""
    backbone_ok = False
    ollama_ok   = False
    try:
        with _client() as client:
            r = client.get(f"{API_BASE}/v1/health", timeout=3.0)
            backbone_ok = r.status_code == 200
    except Exception:  # noqa: BLE001
        pass
    try:
        with _client() as client:
            r = client.get(f"{OLLAMA_BASE}/api/tags", timeout=3.0)
            ollama_ok = r.status_code == 200
    except Exception:  # noqa: BLE001
        pass

    return jsonify({
        "ok":           True,
        "backbone":     backbone_ok,
        "ollama":       ollama_ok,
        "api_base":     API_BASE,
        "ollama_base":  OLLAMA_BASE,
    })


@app.route("/api/eri", methods=["GET"])
def proxy_eri() -> Response:
    """Proxy ERI + swarm resonance state from backbone — polled by UI for live color theming."""
    try:
        with _client() as client:
            resp = client.get(
                f"{API_BASE}/v1/eri",
                timeout=3.0,
            )
            if resp.status_code == 200:
                return jsonify(resp.json())
    except Exception:  # noqa: BLE001
        pass
    # Fallback neutral state if backbone unreachable
    return jsonify({"eri": 0.5, "ers": 0.5, "pacing": 0.5, "volatility": 0.0, "coherence": 1.0, "state": "Stable"})



    return jsonify({"events": [], "note": "stub"})


@app.route("/", methods=["GET"])
def index() -> Response:
    return send_from_directory(app.static_folder, "index.html")


@app.route("/static/<path:filename>", methods=["GET"])
def static_files(filename: str) -> Response:
    return send_from_directory(app.static_folder, filename)


@app.route("/<path:filename>", methods=["GET"])
def spa_assets(filename: str) -> Response:
    """Serve Vite build assets (e.g. /assets/*, /favicon.svg) and fall back to index.html for SPA routes."""
    asset_path = Path(app.static_folder) / filename
    if asset_path.exists() and asset_path.is_file():
        return send_from_directory(app.static_folder, filename)
    return send_from_directory(app.static_folder, "index.html")


@app.route("/models", methods=["GET"])
def models() -> Response:
    """Return chat-capable models from Ollama, sorted with the backbone default first."""
    # Patterns that identify embedding/vision-only models — not valid for /api/chat
    _EMBED_PATTERNS = ("embed", "minilm", "nomic", "mxbai", "bge-", "e5-", "gte-")

    try:
        with _client() as client:
            r = client.get(f"{OLLAMA_BASE}/api/tags", timeout=5.0)
            r.raise_for_status()
            tags = r.json().get("models", [])

        backbone_default = os.getenv("OLLAMA_MODEL", "qwen3:1.7b")

        chat_models = []
        for m in tags:
            name = m["name"].lower()
            if any(pat in name for pat in _EMBED_PATTERNS):
                continue  # skip embedding-only models
            chat_models.append(m["name"])

        # Backbone default goes first so the UI picks it as activeModel
        chat_models.sort(key=lambda n: (0 if n == backbone_default else 1, n))

        model_list = [
            {"id": name, "object": "model", "owned_by": "ollama"}
            for name in chat_models
        ]
        return jsonify({"object": "list", "data": model_list})
    except Exception:  # noqa: BLE001
        return jsonify({"object": "list", "data": []})


@app.route("/modules", methods=["GET"])
def modules() -> Response:
    """Proxy to backbone live skills/modules listing."""
    target = f"{API_BASE}/v1/modules"
    try:
        resp = _forward_with_retry("GET", target)
        return Response(resp.content, status=resp.status_code,
                        content_type=resp.headers.get("content-type", "application/json"))
    except Exception:
        return jsonify({"modules": [], "count": 0})


@app.route("/embeddings", methods=["POST"])
def embeddings() -> Response:
    """Proxy to embeddings endpoint"""
    payload = request.get_json(silent=True) or {}
    target = f"{API_BASE}/v1/embeddings"
    try:
        resp = _forward_with_retry("POST", target, json_body=payload)
        return Response(
            resp.content, status=resp.status_code, content_type=resp.headers.get("content-type")
        )
    except Exception as exc:  # noqa: BLE001
        return jsonify({"error": {"message": str(exc), "type": "server_error", "code": 502}}), 502


@app.route("/images/generations", methods=["POST"])
def image_generations() -> Response:
    """Proxy to RunPod image generation endpoint."""
    payload = request.get_json(silent=True) or {}
    target = f"{API_BASE}/v1/images/generations"
    try:
        resp = _forward_with_retry("POST", target, json_body=payload)
        return Response(
            resp.content, status=resp.status_code, content_type=resp.headers.get("content-type", "application/json")
        )
    except Exception as exc:  # noqa: BLE001
        return jsonify({"error": {"message": str(exc), "type": "server_error", "code": 502}}), 502


def _strip_artifact_xml(text: str) -> str:
    """
    The Go backbone wraps every response in sovereign <artifact> XML tags.
    Strip the wrapper so the content is clean prose/code for the client.
    e.g. <artifact type="code" language="go">...</artifact>  →  ```go\n...\n```
    """
    import re as _re
    # Match <artifact ...>content</artifact> — including multi-line
    m = _re.search(r'<artifact[^>]*language=["\']?(\w+)["\']?[^>]*>([\s\S]*?)</artifact>', text)
    if m:
        lang, content = m.group(1).strip(), m.group(2).strip()
        if lang and lang not in ("text", "message", "plain"):
            return f"```{lang}\n{content}\n```"
        return content
    # Fallback: strip any <artifact> tags without language
    m2 = _re.search(r'<artifact[^>]*>([\s\S]*?)</artifact>', text)
    if m2:
        return m2.group(1).strip()
    return text


def _sse_stream(target_url: str, payload: Dict[str, Any]) -> Iterable[str]:
    """
    SSE pass-through with proper line-buffering.

    httpx's iter_text() returns arbitrary byte chunks that can split mid-line,
    causing partial 'data:' payloads to be silently dropped.  iter_lines()
    returns complete lines, so we reconstruct proper SSE events.

    Non-streaming fallback: if the backend returns a plain JSON blob
    (no SSE events at all), we convert it to one delta + [DONE].
    """
    for attempt in range(RETRY_COUNT):
        try:
            with _client().stream(
                "POST", target_url, json=payload, headers=_build_headers(), timeout=None
            ) as r:
                r.raise_for_status()
                sse_seen = False
                accumulated = ""
                for line in r.iter_lines():
                    if not line:
                        continue
                    if line.startswith(":"):
                        # SSE comment (e.g. ": keep-alive") — forward to client so
                        # Cloudflare's 524 idle timer keeps resetting.
                        yield f"{line}\n\n"
                    elif line.startswith("data:"):
                        sse_seen = True
                        yield f"{line}\n\n"
                    elif sse_seen:
                        # Ignore non-data SSE fields (event:, id:, retry:)
                        pass
                    else:
                        # No SSE yet — accumulating plain JSON body (non-streaming backend)
                        accumulated += line

                # Plain JSON fallback — convert to SSE delta so the client stream reader works
                if accumulated:
                    try:
                        body = json.loads(accumulated)
                        content = (
                            body.get("choices", [{}])[0]
                            .get("message", {})
                            .get("content", "")
                        )
                        if content:
                            content = _strip_artifact_xml(content)
                            yield f"data: {json.dumps({'id': body.get('id', 'chatcmpl-0'), 'object': 'chat.completion.chunk', 'choices': [{'index': 0, 'delta': {'role': 'assistant', 'content': content}, 'finish_reason': None}]})}\n\n"
                            yield f"data: {json.dumps({'id': body.get('id', 'chatcmpl-0'), 'object': 'chat.completion.chunk', 'choices': [{'index': 0, 'delta': {}, 'finish_reason': 'stop'}]})}\n\n"
                        else:
                            yield f"data: {accumulated}\n\n"
                    except (json.JSONDecodeError, IndexError, KeyError):
                        yield f"data: {accumulated}\n\n"
                    yield "data: [DONE]\n\n"
                return
        except Exception as exc:  # noqa: BLE001
            if attempt < RETRY_COUNT - 1:
                time.sleep(_backoff(attempt))
                continue
            error_payload = json.dumps({
                "error": {"message": str(exc), "type": "server_error", "code": 500}
            })
            yield f"data: {error_payload}\n\n"
            yield "data: [DONE]\n\n"
            return


@app.route("/agents/save", methods=["POST"])
def save_agent() -> Response:
    """Write a user-created agent as a .ori skill file to oricli_core/skills/."""
    data = request.get_json(force=True) or {}
    raw_name = data.get("name", "").strip()
    if not raw_name:
        return jsonify({"error": "name is required"}), 400

    file_stem = re.sub(r"[^a-z0-9_]", "_", raw_name.lower())
    file_stem = re.sub(r"_+", "_", file_stem).strip("_")
    if not file_stem:
        return jsonify({"error": "invalid name"}), 400

    skills_dir = Path(__file__).parent / "oricli_core" / "skills"
    skills_dir.mkdir(parents=True, exist_ok=True)
    dest = skills_dir / f"{file_stem}.ori"

    lines: list[str] = []
    lines.append(f"@skill_name: {file_stem}")
    lines.append(f"@description: {data.get('description') or raw_name}")

    triggers = [t.strip() for t in data.get("triggers", []) if t.strip()]
    if triggers:
        lines.append(f"@triggers: [{', '.join(f'{chr(34)}{t}{chr(34)}' for t in triggers)}]")

    assigned_skills = data.get("skills", [])
    if assigned_skills:
        lines.append(f"@requires_skills: [{', '.join(f'{chr(34)}{s}{chr(34)}' for s in assigned_skills)}]")

    assigned_rules = data.get("rules", [])
    if assigned_rules:
        lines.append(f"@enforces_rules: [{', '.join(f'{chr(34)}{r}{chr(34)}' for r in assigned_rules)}]")

    lines.append("")

    mindset = (data.get("mindset") or "").strip()
    if mindset:
        lines += ["<mindset>", mindset, "</mindset>", ""]

    instructions = (data.get("instructions") or "").strip()
    if instructions:
        lines += ["<instructions>", instructions, "</instructions>", ""]

    constraints = (data.get("constraints") or "").strip()
    if constraints:
        lines += ["<constraints>", constraints, "</constraints>"]

    dest.write_text("\n".join(lines), encoding="utf-8")
    return jsonify({"success": True, "path": str(dest), "file": f"{file_stem}.ori"})


@app.route("/agents/list", methods=["GET"])
def list_agents_ori() -> Response:
    """Return parsed .ori agent data for the UI agent switcher."""
    skills_dir = Path(__file__).parent / "oricli_core" / "skills"
    if not skills_dir.exists():
        return jsonify({"agents": []})

    agents = []
    for p in sorted(skills_dir.glob("*.ori")):
        try:
            text = p.read_text(encoding="utf-8")
            agent = _parse_ori(p.stem, text)
            agents.append(agent)
        except Exception:
            agents.append({"id": p.stem, "name": p.stem, "description": "", "systemPrompt": "", "emoji": "🤖"})
    return jsonify({"agents": agents})


def _parse_ori(slug: str, text: str) -> dict:
    """Parse a .ori file into a dict with id, name, description, systemPrompt, emoji."""
    import re as _re

    def _tag(tag: str) -> str:
        m = _re.search(rf'<{tag}>([\s\S]*?)</{tag}>', text)
        return m.group(1).strip() if m else ''

    def _meta(key: str) -> str:
        m = _re.search(rf'^@{key}:\s*(.+)', text, _re.MULTILINE)
        return m.group(1).strip() if m else ''

    name        = _meta('skill_name') or _meta('rule_name') or slug
    description = _meta('description') or ''
    mindset     = _tag('mindset')
    instructions = _tag('instructions')
    constraints  = _tag('constraints')

    parts: list[str] = []
    if mindset:      parts.append(mindset)
    if instructions: parts.append(f"Instructions:\n{instructions}")
    if constraints:  parts.append(f"Constraints:\n{constraints}")
    system_prompt = "\n\n".join(parts) if parts else f"You are {name}. {description}"

    # Pick a representative emoji based on slug keywords
    EMOJI_MAP = {
        'go': '🔧', 'rust': '⚙️', 'python': '🐍', 'senior_python': '🐍',
        'api': '🔌', 'devops': '🚀', 'sre': '🚀', 'ml': '🧠', 'data': '📊',
        'security': '🔐', 'offensive': '🔐', 'research': '🔬',
        'architect': '🏗️', 'system': '🏗️', 'hive': '🐝',
        'knowledge': '📚', 'curator': '📚', 'writer': '✍️',
        'prompt': '💬', 'benchmark': '📈', 'guardian': '🛡️',
        'planner': '🗺️', 'sovereign': '👑', 'jarvis': '🤖',
    }
    emoji = '🤖'
    for k, e in EMOJI_MAP.items():
        if k in slug.lower():
            emoji = e
            break

    # Format display name
    display_name = name.replace('_', ' ').title()

    return {
        "id":           slug,
        "name":         display_name,
        "description":  description,
        "systemPrompt": system_prompt,
        "emoji":        emoji,
    }


def _slugify(name: str) -> str:
    slug = re.sub(r"[^a-z0-9_]", "_", name.lower())
    return re.sub(r"_+", "_", slug).strip("_")


def _ori_list(items: list[str], quote: str = '"') -> str:
    return "[" + ", ".join(f"{quote}{i}{quote}" for i in items) + "]"


@app.route("/skills/save", methods=["POST"])
def save_skill() -> Response:
    """Write a user-created skill as a .ori file to oricli_core/skills/."""
    data = request.get_json(force=True) or {}
    raw_name = data.get("name", "").strip()
    if not raw_name:
        return jsonify({"error": "name is required"}), 400

    slug = _slugify(raw_name)
    if not slug:
        return jsonify({"error": "invalid name"}), 400

    dest_dir = Path(__file__).parent / "oricli_core" / "skills"
    dest_dir.mkdir(parents=True, exist_ok=True)
    dest = dest_dir / f"{slug}.ori"

    lines: list[str] = [
        f"@skill_name: {slug}",
        f"@description: {data.get('description') or raw_name}",
    ]
    triggers = [t.strip() for t in data.get("triggers", []) if t.strip()]
    if triggers:
        lines.append(f"@triggers: {_ori_list(triggers)}")
    tools = [t.strip() for t in data.get("requires_tools", []) if t.strip()]
    if tools:
        lines.append(f"@requires_tools: {_ori_list(tools)}")
    lines.append("")

    for tag, key in [("<mindset>", "mindset"), ("<instructions>", "instructions"), ("<constraints>", "constraints")]:
        body = (data.get(key) or "").strip()
        if body:
            close = tag.replace("<", "</")
            lines += [tag, body, close, ""]

    dest.write_text("\n".join(lines), encoding="utf-8")
    return jsonify({"success": True, "path": str(dest), "file": f"{slug}.ori"})


@app.route("/rules/save", methods=["POST"])
def save_rule() -> Response:
    """Write a user-created rule as a .ori file to oricli_core/rules/."""
    data = request.get_json(force=True) or {}
    raw_name = data.get("name", "").strip()
    if not raw_name:
        return jsonify({"error": "name is required"}), 400

    slug = _slugify(raw_name)
    if not slug:
        return jsonify({"error": "invalid name"}), 400

    dest_dir = Path(__file__).parent / "oricli_core" / "rules"
    dest_dir.mkdir(parents=True, exist_ok=True)
    dest = dest_dir / f"{slug}.ori"

    lines: list[str] = [
        f"@rule_name: {slug}",
        f"@description: {data.get('description') or raw_name}",
        f"@scope: {data.get('scope') or 'global'}",
    ]
    categories = [c.strip() for c in data.get("categories", []) if c.strip()]
    if categories:
        lines.append(f"@categories: {_ori_list(categories)}")
    lines.append("")

    constraints = (data.get("constraints") or "").strip()
    if constraints:
        lines += ["<constraints>", constraints, "</constraints>"]

    dest.write_text("\n".join(lines), encoding="utf-8")
    return jsonify({"success": True, "path": str(dest), "file": f"{slug}.ori"})


import urllib.parse
from bs4 import BeautifulSoup


def _ddg_search(query: str, max_results: int = 6) -> list:
    """Scrape DuckDuckGo HTML results — no API key needed."""
    try:
        with httpx.Client(timeout=12.0, follow_redirects=True) as client:
            resp = client.get(
                "https://html.duckduckgo.com/html/",
                params={"q": query},
                headers={"User-Agent": "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36"},
            )
        soup = BeautifulSoup(resp.text, "html.parser")
        results = []
        for r in soup.select(".result")[:max_results]:
            title_el = r.select_one(".result__title a, .result__a")
            snip_el  = r.select_one(".result__snippet")
            if not (title_el and snip_el):
                continue
            href = title_el.get("href", "")
            parsed = urllib.parse.parse_qs(urllib.parse.urlparse(href).query)
            actual_url = urllib.parse.unquote(parsed.get("uddg", [href])[0])
            results.append({
                "title":   title_el.get_text(strip=True),
                "snippet": snip_el.get_text(strip=True),
                "url":     actual_url,
            })
        return results
    except Exception:
        return []


# ── Epistemic filtering ───────────────────────────────────────────────────────

_constitution_cache: dict | None = None
_CONSTITUTION_PATHS = [
    os.path.join(os.path.dirname(__file__), "data/source_constitution.json"),
    "data/source_constitution.json",
]

def _load_constitution() -> dict:
    """Load and cache the Source Constitution from disk. Falls back to
    a minimal safe default if the file is absent."""
    global _constitution_cache
    if _constitution_cache is not None:
        return _constitution_cache
    for path in _CONSTITUTION_PATHS:
        try:
            with open(path, "r", encoding="utf-8") as f:
                _constitution_cache = json.load(f)
            return _constitution_cache
        except (OSError, json.JSONDecodeError):
            continue
    # Minimal fallback — never fails
    _constitution_cache = {
        "ingestion_rules": {
            "min_snippet_length": 40, "min_title_length": 5,
            "min_combined_score": 0.30, "borderline_min": 0.30, "borderline_max": 0.55,
            "relevance_weight": 0.55, "trust_weight": 0.45,
            "block_paywalled_signals": ["Subscribe to read", "Members only"],
            "block_content_signals": ["404 Not Found", "Access Denied"],
        },
        "trust_tiers": {
            "tier1": {"score": 0.95, "domains": ["arxiv.org", "ncbi.nlm.nih.gov", "nature.com", "ieee.org", "who.int"]},
            "tier2": {"score": 0.80, "domains": ["reuters.com", "bbc.com", "wikipedia.org", "github.com", "stackoverflow.com"]},
            "tier0": {"score": 0.10, "domains": ["infowars.com", "naturalnews.com"]},
        },
        "tld_scores": {".edu": 0.88, ".gov": 0.90, ".org": 0.65},
        "default_score": 0.50,
        "hard_blocked_domains": ["infowars.com", "naturalnews.com"],
        "hard_blocked_url_patterns": ["/login", "/subscribe", "/paywall"],
    }
    return _constitution_cache


def _build_trust_index() -> dict[str, float]:
    """Flatten all trust tiers into a single domain→score lookup dict."""
    c = _load_constitution()
    idx: dict[str, float] = {}
    for tier in c.get("trust_tiers", {}).values():
        score = tier.get("score", 0.50)
        for domain in tier.get("domains", []):
            idx[domain.lower()] = score
    return idx

_trust_index: dict[str, float] | None = None

def _get_trust_index() -> dict[str, float]:
    global _trust_index
    if _trust_index is None:
        _trust_index = _build_trust_index()
    return _trust_index


_STOP_WORDS = frozenset({
    "the","a","an","is","are","was","were","be","been","being",
    "have","has","had","do","does","did","will","would","could","should",
    "may","might","shall","can","need","dare","ought","used",
    "and","or","but","if","in","on","at","to","for","of","with",
    "by","from","up","about","into","through","during","before","after",
    "above","below","between","each","more","most","other","some","such",
    "no","nor","not","only","own","same","so","than","too","very",
    "just","as","this","that","these","those","it","its","how","what",
    "which","who","when","where","why","all","both","few","many","much",
})


def _source_trust_score(url: str) -> float:
    """Return 0-1 trust score for a URL using the Source Constitution."""
    c = _load_constitution()
    hard_blocked = {d.lower() for d in c.get("hard_blocked_domains", [])}
    try:
        parsed = urllib.parse.urlparse(url)
        host = parsed.netloc.lower().lstrip("www.")
        if host in hard_blocked:
            return 0.0
        # Check hard-blocked URL patterns
        for pat in c.get("hard_blocked_url_patterns", []):
            if pat in url.lower():
                return 0.0
        idx = _get_trust_index()
        if host in idx:
            return idx[host]
        for domain, score in idx.items():
            if host.endswith("." + domain):
                return score
        # TLD fallback from constitution
        tld_scores = c.get("tld_scores", {})
        for tld, score in tld_scores.items():
            if host.endswith(tld):
                return score
        return float(c.get("default_score", 0.50))
    except Exception:
        return 0.40


def _passes_ingestion_rules(title: str, snippet: str, url: str) -> tuple[bool, str]:
    """Check constitution ingestion rules against a result."""
    c = _load_constitution()
    rules = c.get("ingestion_rules", {})
    if len(title) < rules.get("min_title_length", 5):
        return False, "title too short"
    if len(snippet) < rules.get("min_snippet_length", 40):
        return False, "snippet too short"
    lower = snippet.lower()
    for sig in rules.get("block_paywalled_signals", []):
        if sig.lower() in lower:
            return False, f"paywall: {sig}"
    for sig in rules.get("block_content_signals", []):
        if sig.lower() in lower:
            return False, f"blocked signal: {sig}"
    return True, ""


def _relevance_score(query: str, title: str, snippet: str) -> float:
    """Token-overlap relevance score between query and result content (0-1).
    Title matches are weighted 2× snippet matches. Score is normalised so
    a perfect-overlap result returns 1.0."""
    q_tokens = {t for t in re.findall(r"[a-z0-9]+", query.lower()) if t not in _STOP_WORDS and len(t) > 2}
    if not q_tokens:
        return 0.5  # no signal — neutral

    haystack_title   = set(re.findall(r"[a-z0-9]+", title.lower()))
    haystack_snippet = set(re.findall(r"[a-z0-9]+", snippet.lower()))

    title_hits   = len(q_tokens & haystack_title)
    snippet_hits = len(q_tokens & haystack_snippet)
    # Weighted: title 2×, snippet 1×, normalised by query token count
    raw = (title_hits * 2 + snippet_hits) / (len(q_tokens) * 3)
    return min(raw, 1.0)


def _answers_query_llm(query: str, title: str, snippet: str) -> bool:
    """Fast LLM YES/NO gate: does this snippet actually answer the query?
    Only called on borderline results (0.25 ≤ combined_score ≤ 0.55).
    Times out quickly — if the LLM is slow, we pass the result through."""
    try:
        answer = _llm_complete([
            {"role": "system", "content": (
                "You are an epistemic filter. Answer only YES or NO. "
                "Does the following text usefully answer or address the research query? "
                "Be strict — low-quality SEO pages, navigation menus, and off-topic results should be NO."
            )},
            {"role": "user", "content": f"Query: {query}\n\nTitle: {title}\nText: {snippet[:400]}"},
        ], max_tokens=5, timeout=12.0)
        return "YES" in answer.upper()
    except Exception:
        return True  # fail-open — don't discard on timeout


def _epistemic_filter(query: str, results: list[dict]) -> list[dict]:
    """Score and filter search results before synthesis using the Source Constitution.

    Pipeline:
      1. Ingestion rules (length, paywall, block signals)
      2. Combined score = relevance_weight * relevance + trust_weight * trust
      3. Hard drop if combined < threshold (from constitution)
      4. LLM YES/NO gate only for borderline scores (borderline_min ≤ combined < borderline_max)

    Returns filtered results sorted best-first, each annotated with
    '_epistemic' metadata: {relevance, trust, combined, passed_llm}.
    """
    if not results:
        return results

    c = _load_constitution()
    rules = c.get("ingestion_rules", {})
    threshold      = float(rules.get("min_combined_score", 0.30))
    borderline_min = float(rules.get("borderline_min", 0.30))
    borderline_max = float(rules.get("borderline_max", 0.55))
    rel_w          = float(rules.get("relevance_weight", 0.55))
    trust_w        = float(rules.get("trust_weight", 0.45))

    scored: list[tuple[float, dict]] = []
    for r in results:
        title   = r.get("title", "")
        snippet = r.get("snippet", r.get("body", ""))
        url     = r.get("url", "")

        # Layer 0: ingestion rules
        ok, reason = _passes_ingestion_rules(title, snippet, url)
        if not ok:
            continue

        rel      = _relevance_score(query, title, snippet)
        trust    = _source_trust_score(url)
        combined = rel_w * rel + trust_w * trust

        passed_llm: bool | None = None

        if combined < threshold:
            continue
        elif borderline_min <= combined < borderline_max:
            passed_llm = _answers_query_llm(query, title, snippet)
            if not passed_llm:
                continue

        scored.append((combined, {
            **r,
            "_epistemic": {
                "relevance": round(rel, 3),
                "trust":     round(trust, 3),
                "combined":  round(combined, 3),
                "passed_llm": passed_llm,
            },
        }))

    scored.sort(key=lambda x: x[0], reverse=True)
    return [r for _, r in scored]


def _llm_complete(messages: list, max_tokens: int = 2000, timeout: float = 120.0, extra_headers: dict = None) -> str:
    """Synchronous LLM call — handles both plain-JSON and SSE responses.

    The backbone returns SSE (text/event-stream) for some model tiers even
    when stream=False is requested. We detect that case and accumulate all
    content chunks into a single string.
    """
    payload = {
        "model": "oricli-cognitive",
        "stream": False,
        "max_tokens": max_tokens,
        "messages": messages,
    }
    try:
        with _client() as client:
            resp = client.post(
                f"{API_BASE}/v1/chat/completions",
                json=payload,
                headers=_build_headers(extra=extra_headers),
                timeout=timeout,
            )
            resp.raise_for_status()
            raw = resp.text.strip()
            if not raw:
                return "[error: empty response from backbone]"

            # Detect SSE: starts with ": keep-alive" comment or "data:" lines
            if raw.startswith(": keep-alive") or raw.startswith("data:"):
                return _extract_text_from_sse(raw)

            # Plain JSON response
            try:
                data = json.loads(raw)
            except Exception:
                # May still be partial SSE without the keep-alive prefix
                if "\ndata:" in raw or raw.startswith("data:"):
                    return _extract_text_from_sse(raw)
                return f"[error: invalid JSON from backbone: {raw[:200]}]"

            content = (
                data.get("choices", [{}])[0]
                .get("message", {})
                .get("content", "")
            )
            return _strip_artifact_xml(content)
    except Exception as exc:  # noqa: BLE001
        return f"[error: {exc}]"


def _extract_text_from_sse(raw: str) -> str:
    """Parse SSE text and accumulate all content into a single string."""
    parts: list[str] = []
    for line in raw.splitlines():
        line = line.strip()
        if not line or not line.startswith("data:"):
            continue
        payload_str = line[len("data:"):].strip()
        if payload_str == "[DONE]":
            break
        try:
            obj = json.loads(payload_str)
        except Exception:
            continue
        # Format 1: {"type":"content","text":"..."}  (backbone research events)
        if obj.get("type") == "content" and obj.get("text"):
            parts.append(obj["text"])
            continue
        # Format 2: delta streaming {"choices":[{"delta":{"content":"..."}}]}
        choices = obj.get("choices", [])
        if choices:
            delta = choices[0].get("delta", {})
            msg   = choices[0].get("message", {})
            chunk = delta.get("content") or msg.get("content") or ""
            if chunk:
                parts.append(chunk)
    result = "".join(parts).strip()
    return _strip_artifact_xml(result) if result else "[error: no content in SSE response]"


def _sse_event(data: dict) -> str:
    return f"data: {json.dumps(data)}\n\n"


@app.route("/search", methods=["GET"])
def search_endpoint() -> Response:
    """Quick web search — returns JSON snippets for canvas context injection."""
    q = request.args.get("q", "").strip()
    if not q:
        return jsonify({"error": "q required"}), 400
    return jsonify({"query": q, "results": _ddg_search(q, max_results=6)})


@app.route("/research/stream", methods=["POST"])
def research_stream() -> Response:
    """SSE research pipeline. Emits typed events: step, step_done, search_result, plan, content, done, error."""
    from flask import stream_with_context
    data  = request.get_json(force=True) or {}
    topic = data.get("topic", "").strip()
    mode  = data.get("mode", "normal")

    if not topic:
        return jsonify({"error": "topic required"}), 400

    def generate():
        try:
            if mode == "deep":
                yield from _research_deep(topic)
            else:
                yield from _research_normal(topic)
        except Exception as exc:  # noqa: BLE001
            yield _sse_event({"type": "error", "message": str(exc)})
            yield _sse_event({"type": "done"})

    return Response(
        stream_with_context(generate()),
        mimetype="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )


def _research_normal(topic: str):
    yield _sse_event({"type": "step", "index": 0, "total": 3, "label": f'Searching the web for "{topic}"', "status": "active"})
    raw_results = _ddg_search(topic, max_results=8)
    yield _sse_event({"type": "step_done", "index": 0})

    # ── Epistemic filter ──────────────────────────────────────────────────────
    yield _sse_event({"type": "step", "index": 1, "total": 3, "label": "Scoring & filtering sources", "status": "active"})
    results = _epistemic_filter(topic, raw_results)
    dropped = len(raw_results) - len(results)
    yield _sse_event({"type": "step_done", "index": 1})
    yield _sse_event({
        "type": "search_result", "query": topic, "results": results,
        "epistemic": {"total_raw": len(raw_results), "passed": len(results), "dropped": dropped},
    })

    yield _sse_event({"type": "step", "index": 2, "total": 3, "label": "Synthesizing findings", "status": "active"})

    snippets = "\n\n".join(
        f"[{i+1}] **{r['title']}** (relevance: {r.get('_epistemic', {}).get('relevance', '?')}, trust: {r.get('_epistemic', {}).get('trust', '?')})\n{r['snippet']}\nSource: {r['url']}"
        for i, r in enumerate(results)
    ) if results else "No sufficiently relevant web results found — answer from general knowledge."

    report = _llm_complete([
        {"role": "system", "content": "You are a research assistant. Write a comprehensive, well-structured markdown report based on the provided search results. Use ## headings, bullet points, and inline citations like [1]. End with a ## Sources section listing each URL."},
        {"role": "user", "content": f"Research topic: {topic}\n\nSearch results (epistemically filtered, highest relevance first):\n{snippets}\n\nWrite a complete markdown report."},
    ], max_tokens=2000)

    yield _sse_event({"type": "step_done", "index": 2})
    yield _sse_event({"type": "content", "text": report, "title": topic})
    yield _sse_event({"type": "done"})


def _research_deep(topic: str):
    import re as _re

    # Step 0: Plan
    yield _sse_event({"type": "step", "index": 0, "total": 6, "label": "Planning research questions", "status": "active"})
    plan_resp = _llm_complete([
        {"role": "system", "content": "You are a research planner. Output exactly 3 specific research sub-questions as a numbered list (1. 2. 3.) with no other text."},
        {"role": "user",   "content": f"Break this into 3 targeted sub-questions for deep research: {topic}"},
    ], max_tokens=300)
    yield _sse_event({"type": "step_done", "index": 0})

    questions = _re.findall(r'\d+\.\s*(.+)', plan_resp)
    questions  = [q.strip() for q in questions if q.strip()][:3] or [topic]
    total      = 1 + len(questions) + 1 + 1  # plan + per-search + filter step + synthesize

    yield _sse_event({"type": "plan", "questions": questions, "total": total})

    # Steps 1-N: Search each sub-question
    all_results: list[dict] = []
    for i, q in enumerate(questions):
        yield _sse_event({"type": "step", "index": i + 1, "total": total, "label": f"Searching: {q[:70]}", "status": "active"})
        raw = _ddg_search(q, max_results=6)
        filtered = _epistemic_filter(q, raw)
        all_results.append({"question": q, "results": filtered, "raw_count": len(raw)})
        yield _sse_event({"type": "step_done", "index": i + 1})
        yield _sse_event({
            "type": "search_result", "query": q, "results": filtered,
            "epistemic": {"total_raw": len(raw), "passed": len(filtered), "dropped": len(raw) - len(filtered)},
        })

    # Epistemic summary step
    filter_idx = 1 + len(questions)
    yield _sse_event({"type": "step", "index": filter_idx, "total": total, "label": "Epistemic cross-check complete", "status": "active"})
    total_raw     = sum(r["raw_count"] for r in all_results)
    total_passed  = sum(len(r["results"]) for r in all_results)
    yield _sse_event({"type": "step_done", "index": filter_idx})
    yield _sse_event({
        "type": "epistemic_summary",
        "total_raw": total_raw, "passed": total_passed, "dropped": total_raw - total_passed,
        "pass_rate": round(total_passed / max(total_raw, 1), 2),
    })

    # Final: Synthesize
    synth_idx = filter_idx + 1
    yield _sse_event({"type": "step", "index": synth_idx, "total": total, "label": "Synthesizing comprehensive report", "status": "active"})

    ctx_parts: list[str] = []
    for item in all_results:
        ctx_parts.append(f"### {item['question']}")
        for j, r in enumerate(item["results"]):
            ep = r.get("_epistemic", {})
            ctx_parts.append(
                f"[{j+1}] **{r['title']}** (rel={ep.get('relevance','?')} trust={ep.get('trust','?')}): "
                f"{r['snippet']} ({r['url']})"
            )
    context = "\n\n".join(ctx_parts) if ctx_parts else "No sufficiently relevant results."

    report = _llm_complete([
        {"role": "system", "content": "You are an expert research synthesizer. Write a deeply detailed markdown report using ## headings. Include analysis beyond just summaries, inline citations [1][2], and a ## Sources section at the end. Prioritise higher-scored sources."},
        {"role": "user",   "content": f"Topic: {topic}\n\nResearch findings (epistemically filtered, highest relevance first per section):\n{context}\n\nWrite a comprehensive deep research report."},
    ], max_tokens=3000, timeout=180.0)

    yield _sse_event({"type": "step_done", "index": synth_idx})
    yield _sse_event({"type": "content", "text": report, "title": topic})
    yield _sse_event({"type": "done"})


@app.route("/chat", methods=["POST"])
def chat() -> Response:
    payload = request.get_json(silent=True) or {}
    stream = bool(payload.get("stream", True))

    try:
        _enforce_attachment_limit(payload)
    except ValueError as exc:
        return jsonify({"error": {"message": str(exc), "type": "invalid_request_error", "code": 400}}), 400

    # Inject local RAG context if we have relevant indexed docs
    messages = payload.get("messages", [])
    last_user = next((m.get("content", "") for m in reversed(messages) if m.get("role") == "user"), "")
    if last_user and isinstance(last_user, str) and len(last_user) > 5:
        rag_hits = _rag_search(last_user, limit=4)
        if rag_hits:
            ctx_lines = []
            for h in rag_hits:
                meta = h.get("metadata", {})
                pub = meta.get("published", "")
                src = h["source"]
                ctx_lines.append(f"**{h['title']}** ({pub}) [{src}]\n{h['snippet']}")
            rag_block = "Relevant knowledge from your indexed sources:\n\n" + "\n\n---\n\n".join(ctx_lines)
            payload = {**payload, "messages": [{"role": "system", "content": rag_block}] + messages}

    target_url = f"{API_BASE}/v1/chat/completions"

    if stream:
        return Response(
            _sse_stream(target_url, payload),
            mimetype="text/event-stream",
            headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
        )

    try:
        resp = _forward_with_retry("POST", target_url, json_body=payload)
        return Response(
            resp.content, status=resp.status_code, content_type=resp.headers.get("content-type")
        )
    except Exception as exc:  # noqa: BLE001
        return jsonify({"error": {"message": str(exc), "type": "server_error", "code": 502}}), 502



# ── MCP Server Management ─────────────────────────────────────────────────────

_MCP_SERVERS_FILE = Path(__file__).parent / ".oricli" / "mcp_servers.json"
_MCP_ACTIVE_CONFIG = Path(__file__).parent / "oricli_core" / "mcp_config.json"
_MCP_LOCK = threading.Lock()


def _load_mcp_servers() -> list[dict]:
    try:
        if _MCP_SERVERS_FILE.exists():
            return json.loads(_MCP_SERVERS_FILE.read_text())
    except Exception:
        pass
    # Bootstrap from existing mcp_config.json if present
    try:
        if _MCP_ACTIVE_CONFIG.exists():
            raw = json.loads(_MCP_ACTIVE_CONFIG.read_text())
            servers = []
            for name, cfg in raw.get("mcpServers", {}).items():
                servers.append({
                    "id": name,
                    "name": name.replace("_", " ").replace("-", " ").title(),
                    "description": "",
                    "command": cfg.get("command", ""),
                    "args": cfg.get("args", []),
                    "env": cfg.get("env", {}),
                    "enabled": True,
                })
            if servers:
                _save_mcp_servers(servers)
            return servers
    except Exception:
        pass
    return []


def _save_mcp_servers(servers: list[dict]) -> None:
    _MCP_SERVERS_FILE.parent.mkdir(parents=True, exist_ok=True)
    _MCP_SERVERS_FILE.write_text(json.dumps(servers, indent=2))
    _write_active_mcp_config(servers)


def _write_active_mcp_config(servers: list[dict]) -> None:
    """Write the filtered mcp_config.json with only enabled servers."""
    active: dict = {"mcpServers": {}}
    for s in servers:
        if s.get("enabled"):
            entry: dict = {"command": s["command"], "args": s.get("args", [])}
            if s.get("env"):
                entry["env"] = s["env"]
            active["mcpServers"][s["id"]] = entry
    _MCP_ACTIVE_CONFIG.parent.mkdir(parents=True, exist_ok=True)
    _MCP_ACTIVE_CONFIG.write_text(json.dumps(active, indent=2))


@app.route("/mcp/servers", methods=["GET"])
def list_mcp_servers() -> Response:
    with _MCP_LOCK:
        servers = _load_mcp_servers()
    return jsonify({"servers": servers})


@app.route("/mcp/servers", methods=["POST"])
def create_mcp_server() -> Response:
    data = request.get_json(force=True, silent=True) or {}
    raw_id = re.sub(r"[^a-z0-9_\-]", "_", (data.get("id") or data.get("name", "")).lower())
    raw_id = re.sub(r"_+", "_", raw_id).strip("_")
    if not raw_id:
        return jsonify({"error": "id or name is required"}), 400
    server = {
        "id":          raw_id,
        "name":        data.get("name") or raw_id.replace("_", " ").title(),
        "description": data.get("description", ""),
        "command":     data.get("command", "npx"),
        "args":        data.get("args", []),
        "env":         data.get("env", {}),
        "enabled":     data.get("enabled", True),
    }
    with _MCP_LOCK:
        servers = _load_mcp_servers()
        if any(s["id"] == raw_id for s in servers):
            return jsonify({"error": f"Server '{raw_id}' already exists"}), 409
        servers.append(server)
        _save_mcp_servers(servers)
    return jsonify({"server": server}), 201


@app.route("/mcp/servers/<server_id>", methods=["PUT"])
def update_mcp_server(server_id: str) -> Response:
    data = request.get_json(force=True, silent=True) or {}
    with _MCP_LOCK:
        servers = _load_mcp_servers()
        for i, s in enumerate(servers):
            if s["id"] == server_id:
                servers[i] = {**s, **{k: v for k, v in data.items() if k != "id"}}
                _save_mcp_servers(servers)
                return jsonify({"server": servers[i]})
    return jsonify({"error": "not found"}), 404


@app.route("/mcp/servers/<server_id>", methods=["DELETE"])
def delete_mcp_server(server_id: str) -> Response:
    with _MCP_LOCK:
        servers = [s for s in _load_mcp_servers() if s["id"] != server_id]
        _save_mcp_servers(servers)
    return jsonify({"ok": True})


@app.route("/mcp/servers/<server_id>/toggle", methods=["POST"])
def toggle_mcp_server(server_id: str) -> Response:
    with _MCP_LOCK:
        servers = _load_mcp_servers()
        for s in servers:
            if s["id"] == server_id:
                s["enabled"] = not s.get("enabled", False)
                _save_mcp_servers(servers)
                return jsonify({"server": s, "enabled": s["enabled"]})
    return jsonify({"error": "not found"}), 404


@app.route("/mcp/reload", methods=["POST"])
def reload_mcp_backbone() -> Response:
    """Restart the oricli-backbone service so it picks up the new mcp_config.json."""
    try:
        result = _subprocess.run(
            ["sudo", "systemctl", "restart", "oricli-backbone.service"],
            capture_output=True, text=True, timeout=15,
        )
        if result.returncode == 0:
            return jsonify({"ok": True, "message": "Backbone restarted — MCP servers reloading."})
        return jsonify({"ok": False, "message": result.stderr.strip() or "Restart failed"}), 500
    except Exception as exc:
        return jsonify({"ok": False, "message": str(exc)}), 500


# ── Task Scheduler ────────────────────────────────────────────────────────────

try:
    from apscheduler.schedulers.background import BackgroundScheduler
    from apscheduler.triggers.cron import CronTrigger
    from apscheduler.triggers.date import DateTrigger
    _SCHEDULER = BackgroundScheduler(timezone="UTC")
    _SCHEDULER.start()
    _SCHEDULER_AVAILABLE = True
except Exception:
    _SCHEDULER = None  # type: ignore[assignment]
    _SCHEDULER_AVAILABLE = False

_TASKS_FILE = Path(__file__).parent / ".oricli" / "tasks.json"
_TASKS_LOCK = threading.Lock()


def _load_tasks() -> list[dict]:
    try:
        if _TASKS_FILE.exists():
            return json.loads(_TASKS_FILE.read_text())
    except Exception:
        pass
    return []


def _save_tasks(tasks: list[dict]) -> None:
    _TASKS_FILE.parent.mkdir(parents=True, exist_ok=True)
    _TASKS_FILE.write_text(json.dumps(tasks, indent=2))


def _patch_task(task_id: str, patch: dict) -> None:
    with _TASKS_LOCK:
        tasks = _load_tasks()
        for t in tasks:
            if t["id"] == task_id:
                t.update(patch)
                break
        _save_tasks(tasks)


def _run_task_now(task_id: str) -> None:
    """Execute a task: load its agent system prompt, send goal to LLM, store result."""
    with _TASKS_LOCK:
        tasks = _load_tasks()
        task = next((t for t in tasks if t["id"] == task_id), None)
    if not task:
        return

    _patch_task(task_id, {
        "status": "running",
        "lastRun": datetime.now(timezone.utc).isoformat(),
    })

    # Build agent system prompt from .ori file
    system_content: str | None = None
    agent_id = task.get("agentId")
    if agent_id:
        ori_path = Path(__file__).parent / "oricli_core" / "skills" / f"{agent_id}.ori"
        if ori_path.exists():
            ori_text = ori_path.read_text(encoding="utf-8")
            parsed = _parse_ori(agent_id, ori_text)
            system_content = parsed.get("systemPrompt")

    messages: list[dict] = []
    if system_content:
        messages.append({"role": "system", "content": system_content})
    messages.append({"role": "user", "content": task["goal"]})

    try:
        result = _llm_complete(messages)
        _patch_task(task_id, {
            "status": "done",
            "lastResult": result,
            "lastRun": datetime.now(timezone.utc).isoformat(),
        })
    except Exception as exc:
        _patch_task(task_id, {
            "status": "error",
            "lastResult": f"Error: {exc}",
            "lastRun": datetime.now(timezone.utc).isoformat(),
        })


def _schedule_task(task: dict) -> None:
    """Register a task with APScheduler based on its schedule config."""
    if not _SCHEDULER_AVAILABLE:
        return
    tid = task["id"]
    stype = task.get("scheduleType", "manual")

    # Remove existing job if any
    try:
        _SCHEDULER.remove_job(tid)
    except Exception:
        pass

    if stype == "cron":
        expr = task.get("scheduleValue", "").strip()
        if not expr:
            return
        parts = expr.split()
        if len(parts) == 5:
            m, h, dom, mon, dow = parts
            trigger = CronTrigger(minute=m, hour=h, day=dom, month=mon, day_of_week=dow, timezone="UTC")
            _SCHEDULER.add_job(_run_task_now, trigger, args=[tid], id=tid, replace_existing=True)
    elif stype == "once":
        dt_str = task.get("scheduleValue", "")
        try:
            run_at = datetime.fromisoformat(dt_str.replace("Z", "+00:00"))
            trigger = DateTrigger(run_date=run_at, timezone="UTC")
            _SCHEDULER.add_job(_run_task_now, trigger, args=[tid], id=tid, replace_existing=True)
        except Exception:
            pass


# Re-register persisted tasks on startup
for _t in _load_tasks():
    if _t.get("scheduleType") in ("cron", "once") and _t.get("status") not in ("done", "error"):
        _schedule_task(_t)


@app.route("/tasks", methods=["GET"])
def list_tasks() -> Response:
    with _TASKS_LOCK:
        tasks = _load_tasks()
    return jsonify({"tasks": tasks})


@app.route("/tasks", methods=["POST"])
def create_task() -> Response:
    data = request.get_json(force=True, silent=True) or {}
    if not data.get("goal"):
        return jsonify({"error": "goal is required"}), 400

    task: dict = {
        "id":            str(uuid.uuid4()),
        "name":          data.get("name") or data["goal"][:60],
        "goal":          data["goal"],
        "agentId":       data.get("agentId") or None,
        "agentName":     data.get("agentName") or "Default",
        "agentEmoji":    data.get("agentEmoji") or "✨",
        "scheduleType":  data.get("scheduleType", "manual"),   # manual | once | cron
        "scheduleValue": data.get("scheduleValue", ""),
        "status":        "idle",
        "lastRun":       None,
        "lastResult":    None,
        "createdAt":     datetime.now(timezone.utc).isoformat(),
    }
    with _TASKS_LOCK:
        tasks = _load_tasks()
        tasks.append(task)
        _save_tasks(tasks)

    _schedule_task(task)
    return jsonify({"task": task}), 201


@app.route("/tasks/<task_id>", methods=["DELETE"])
def delete_task(task_id: str) -> Response:
    if _SCHEDULER_AVAILABLE:
        try:
            _SCHEDULER.remove_job(task_id)
        except Exception:
            pass
    with _TASKS_LOCK:
        tasks = [t for t in _load_tasks() if t["id"] != task_id]
        _save_tasks(tasks)
    return jsonify({"ok": True})


@app.route("/tasks/<task_id>/run", methods=["POST"])
def run_task(task_id: str) -> Response:
    """Trigger a task immediately (non-blocking)."""
    with _TASKS_LOCK:
        tasks = _load_tasks()
        task = next((t for t in tasks if t["id"] == task_id), None)
    if not task:
        return jsonify({"error": "task not found"}), 404
    threading.Thread(target=_run_task_now, args=[task_id], daemon=True).start()
    return jsonify({"ok": True, "status": "running"})


# ── Connections (External API integrations) ───────────────────────────────────

_CONNECTIONS_FILE = Path(__file__).parent / ".oricli" / "connections.json"
_CONN_LOCK = threading.Lock()


def _load_connections() -> dict:
    try:
        if _CONNECTIONS_FILE.exists():
            return json.loads(_CONNECTIONS_FILE.read_text())
    except Exception:
        pass
    return {}


def _save_connections(data: dict) -> None:
    _CONNECTIONS_FILE.parent.mkdir(parents=True, exist_ok=True)
    _CONNECTIONS_FILE.write_text(json.dumps(data, indent=2))


def _schedule_auto_index(conn_id: str, interval_hours: int) -> None:
    """Register or replace a recurring APScheduler job for a connection."""
    if not _SCHEDULER_AVAILABLE:
        return
    job_id = f"auto_index_{conn_id}"
    try:
        _SCHEDULER.remove_job(job_id)
    except Exception:
        pass
    _SCHEDULER.add_job(
        _trigger_auto_index,
        trigger="interval",
        hours=interval_hours,
        id=job_id,
        args=[conn_id],
        replace_existing=True,
        misfire_grace_time=300,
    )
    log.info("[AutoIndex] Scheduled %s every %dh", conn_id, interval_hours)


def _cancel_auto_index(conn_id: str) -> None:
    if not _SCHEDULER_AVAILABLE:
        return
    try:
        _SCHEDULER.remove_job(f"auto_index_{conn_id}")
        log.info("[AutoIndex] Cancelled schedule for %s", conn_id)
    except Exception:
        pass


def _trigger_auto_index(conn_id: str) -> None:
    """Called by the scheduler — load fresh creds and kick off the index job."""
    with _CONN_LOCK:
        data = _load_connections()
    cfg = data.get(conn_id, {})
    if not cfg.get("auto_index") or not cfg.get("enabled", True):
        return
    creds = cfg.get("credentials", {})
    if not creds or conn_id not in _FETCHERS:
        return
    log.info("[AutoIndex] Running scheduled index for %s", conn_id)
    t = threading.Thread(target=_run_index_job, args=(conn_id, creds, {}), daemon=True)
    t.start()


def _boot_auto_index_schedules() -> None:
    """On startup, re-register all connections that have auto_index enabled."""
    if not _SCHEDULER_AVAILABLE:
        return
    with _CONN_LOCK:
        data = _load_connections()
    for conn_id, cfg in data.items():
        if cfg.get("auto_index") and cfg.get("enabled", True) and conn_id in _FETCHERS:
            interval_hours = int(cfg.get("index_interval_hours") or 24)
            _schedule_auto_index(conn_id, interval_hours)


@app.route("/connections", methods=["GET"])
def list_connections() -> Response:
    with _CONN_LOCK:
        data = _load_connections()
    return jsonify({"connections": data})


@app.route("/connections/<conn_id>", methods=["PUT"])
def save_connection(conn_id: str) -> Response:
    payload = request.get_json(force=True, silent=True) or {}
    with _CONN_LOCK:
        data = _load_connections()
        existing = data.get(conn_id, {})
        data[conn_id] = {**existing, **payload, "id": conn_id, "updatedAt": datetime.now(timezone.utc).isoformat()}
        _save_connections(data)
    cfg = data[conn_id]
    # Dynamically register or cancel the auto-index schedule
    if cfg.get("auto_index") and cfg.get("enabled", True):
        interval_hours = int(cfg.get("index_interval_hours") or 24)
        _schedule_auto_index(conn_id, interval_hours)
        # For Telegram: register webhook instead of scheduling a polling job
        if conn_id == "telegram":
            token = (cfg.get("credentials") or {}).get("bot_token", "")
            if token:
                ok, msg = _telegram_register_webhook(token)
                log.info("[Telegram] Webhook registration: %s — %s", ok, msg)
        # Kick off an immediate first run if never indexed
        elif conn_id not in (_load_index_status()) and conn_id in _FETCHERS:
            creds = cfg.get("credentials", {})
            if creds:
                t = threading.Thread(target=_run_index_job, args=(conn_id, creds, {}), daemon=True)
                t.start()
    else:
        _cancel_auto_index(conn_id)
    return jsonify({"connection": cfg})


@app.route("/connections/<conn_id>", methods=["DELETE"])
def delete_connection(conn_id: str) -> Response:
    with _CONN_LOCK:
        data = _load_connections()
        data.pop(conn_id, None)
        _save_connections(data)
    return jsonify({"ok": True})


@app.route("/connections/<conn_id>/test", methods=["POST"])
def test_connection(conn_id: str) -> Response:
    """Lightweight connectivity test for each integration type."""
    with _CONN_LOCK:
        data = _load_connections()
    cfg = data.get(conn_id, {})
    creds = cfg.get("credentials", {})

    try:
        ok, msg = _test_conn(conn_id, creds)
        return jsonify({"ok": ok, "message": msg})
    except Exception as exc:
        return jsonify({"ok": False, "message": str(exc)})


@app.route("/connections/oauth/authorize/google")
def google_oauth_authorize():
    """Redirect user to Google OAuth consent screen."""
    state = secrets.token_urlsafe(16)
    _OAUTH_STATES[state] = time.time()
    cutoff = time.time() - 600
    for s in list(_OAUTH_STATES):
        if _OAUTH_STATES[s] < cutoff:
            del _OAUTH_STATES[s]
    params = urllib.parse.urlencode({
        "client_id":     GOOGLE_CLIENT_ID,
        "redirect_uri":  GOOGLE_REDIRECT_URI,
        "response_type": "code",
        "scope":         GOOGLE_SCOPES,
        "access_type":   "offline",
        "prompt":        "consent",
        "state":         state,
    })
    from flask import redirect as _redirect
    return _redirect(f"https://accounts.google.com/o/oauth2/v2/auth?{params}")


@app.route("/connections/oauth/callback/google")
def google_oauth_callback():
    """Handle Google OAuth callback — exchange code for tokens."""
    from flask import redirect as _redirect
    error = request.args.get("error", "")
    if error:
        return _redirect("/?error=google_auth_denied#/connections")

    state = request.args.get("state", "")
    if state not in _OAUTH_STATES:
        return "Invalid or expired state. Please try again.", 400
    _OAUTH_STATES.pop(state, None)

    code = request.args.get("code", "")
    try:
        r = httpx.post("https://oauth2.googleapis.com/token", data={
            "code":          code,
            "client_id":     GOOGLE_CLIENT_ID,
            "client_secret": GOOGLE_CLIENT_SECRET,
            "redirect_uri":  GOOGLE_REDIRECT_URI,
            "grant_type":    "authorization_code",
        }, timeout=15)
        r.raise_for_status()
        tokens = r.json()
    except Exception as exc:
        return f"Token exchange failed: {exc}", 500

    user_email, user_name = "", ""
    try:
        ur = httpx.get("https://www.googleapis.com/oauth2/v2/userinfo",
                       headers={"Authorization": f"Bearer {tokens['access_token']}"}, timeout=10)
        if ur.status_code == 200:
            ui = ur.json()
            user_email = ui.get("email", "")
            user_name  = ui.get("name", "")
    except Exception:
        pass

    expiry = (datetime.now(timezone.utc) + timedelta(seconds=tokens.get("expires_in", 3600))).isoformat()
    creds = {
        "access_token":  tokens["access_token"],
        "refresh_token": tokens.get("refresh_token", ""),
        "token_expiry":  expiry,
        "user_email":    user_email,
        "user_name":     user_name,
    }
    with _CONN_LOCK:
        conns = _load_connections()
        conns["google_workspace"] = {
            "id":          "google_workspace",
            "credentials": creds,
            "enabled":     True,
            "updatedAt":   datetime.now(timezone.utc).isoformat(),
        }
        _save_connections(conns)

    return _redirect("/?connected=google#/connections")


def _refresh_google_token(creds: dict) -> dict:
    """Refresh Google access token if within 5 min of expiry. Returns (possibly updated) creds."""
    expiry_str = creds.get("token_expiry", "")
    if expiry_str:
        try:
            expiry = datetime.fromisoformat(expiry_str)
            if expiry.tzinfo is None:
                expiry = expiry.replace(tzinfo=timezone.utc)
            if datetime.now(timezone.utc) < expiry - timedelta(minutes=5):
                return creds  # still fresh
        except Exception:
            pass

    refresh_token = creds.get("refresh_token", "")
    if not refresh_token:
        raise ValueError("No refresh token — user must re-authorize via Connections page")

    r = httpx.post("https://oauth2.googleapis.com/token", data={
        "client_id":     GOOGLE_CLIENT_ID,
        "client_secret": GOOGLE_CLIENT_SECRET,
        "refresh_token": refresh_token,
        "grant_type":    "refresh_token",
    }, timeout=15)
    r.raise_for_status()
    tokens = r.json()

    new_creds = dict(creds)
    new_creds["access_token"] = tokens["access_token"]
    new_creds["token_expiry"] = (
        datetime.now(timezone.utc) + timedelta(seconds=tokens.get("expires_in", 3600))
    ).isoformat()

    with _CONN_LOCK:
        conns = _load_connections()
        if "google_workspace" in conns:
            conns["google_workspace"]["credentials"] = new_creds
            _save_connections(conns)

    return new_creds


def _test_conn(conn_id: str, creds: dict) -> tuple[bool, str]:
    """Returns (success, message) for a connection test."""
    import httpx as _hx

    def _get(url: str, headers: dict = {}, params: dict = {}, timeout: float = 8.0):
        r = _hx.get(url, headers=headers, params=params, timeout=timeout)
        r.raise_for_status()
        return r

    # ── Communication ─────────────────────────────────────────────────────────
    if conn_id == "discord":
        token = creds.get("bot_token", "")
        if not token: return False, "Bot token required"
        r = _get("https://discord.com/api/v10/users/@me", headers={"Authorization": f"Bot {token}"})
        return True, f"Connected as {r.json().get('username', 'unknown')}"

    if conn_id == "telegram":
        token = creds.get("bot_token", "")
        if not token: return False, "Bot token required"
        r = _get(f"https://api.telegram.org/bot{token}/getMe")
        name = r.json().get("result", {}).get("username", "unknown")
        return True, f"Connected as @{name}"

    if conn_id == "slack":
        token = creds.get("bot_token", "")
        if not token: return False, "Bot token required"
        r = _get("https://slack.com/api/auth.test", headers={"Authorization": f"Bearer {token}"})
        d = r.json()
        if not d.get("ok"): return False, d.get("error", "Auth failed")
        return True, f"Connected to {d.get('team', 'workspace')} as {d.get('user', 'bot')}"

    if conn_id == "ms_teams":
        # Just validate the tenant / client id fields are set
        if not creds.get("client_id") or not creds.get("tenant_id"):
            return False, "Client ID and Tenant ID required"
        return True, "Credentials saved (OAuth flow required to activate)"

    # ── Productivity ──────────────────────────────────────────────────────────
    if conn_id == "notion":
        token = creds.get("api_key", "")
        if not token: return False, "API key required"
        r = _get("https://api.notion.com/v1/users/me", headers={"Authorization": f"Bearer {token}", "Notion-Version": "2022-06-28"})
        name = r.json().get("name") or r.json().get("bot", {}).get("owner", {}).get("user", {}).get("name", "bot")
        return True, f"Connected as {name}"

    if conn_id == "todoist":
        token = creds.get("api_token", "")
        if not token: return False, "API token required"
        r = _get("https://api.todoist.com/sync/v9/user", headers={"Authorization": f"Bearer {token}"})
        return True, f"Connected as {r.json().get('full_name', 'user')}"

    if conn_id == "trello":
        key = creds.get("api_key", ""); token = creds.get("token", "")
        if not key or not token: return False, "API key and token required"
        r = _get("https://api.trello.com/1/members/me", params={"key": key, "token": token})
        return True, f"Connected as {r.json().get('fullName', r.json().get('username', 'user'))}"

    if conn_id == "airtable":
        token = creds.get("api_key", "")
        if not token: return False, "API key required"
        r = _get("https://api.airtable.com/v0/meta/whoami", headers={"Authorization": f"Bearer {token}"})
        return True, f"Connected as {r.json().get('id', 'user')}"

    if conn_id == "linear":
        token = creds.get("api_key", "")
        if not token: return False, "API key required"
        r = _hx.post("https://api.linear.app/graphql", json={"query": "{ viewer { name } }"},
                     headers={"Authorization": token}, timeout=8)
        r.raise_for_status()
        name = r.json().get("data", {}).get("viewer", {}).get("name", "user")
        return True, f"Connected as {name}"

    if conn_id == "asana":
        token = creds.get("personal_access_token", "")
        if not token: return False, "Personal access token required"
        r = _get("https://app.asana.com/api/1.0/users/me", headers={"Authorization": f"Bearer {token}"})
        return True, f"Connected as {r.json().get('data', {}).get('name', 'user')}"

    # ── Enterprise ────────────────────────────────────────────────────────────
    if conn_id == "google_workspace":
        at = creds.get("access_token")
        if not at:
            return False, "Not connected — use Authorize with Google"
        try:
            refreshed = _refresh_google_token(creds)
            at = refreshed["access_token"]
        except Exception as exc:
            return False, f"Token refresh failed — please re-authorize ({exc})"
        r = _get("https://www.googleapis.com/oauth2/v2/userinfo",
                 headers={"Authorization": f"Bearer {at}"})
        if r and r.status_code == 200:
            email = r.json().get("email", "unknown")
            return True, f"Connected as {email}"
        return False, "Token invalid — please re-authorize via the Connections page"

    if conn_id == "microsoft_365":
        if not creds.get("client_id") or not creds.get("tenant_id"):
            return False, "Client ID and Tenant ID required"
        return True, "Credentials saved (OAuth flow required to activate)"

    if conn_id == "workday":
        if not creds.get("tenant_url") or not creds.get("client_id"):
            return False, "Tenant URL and Client ID required"
        return True, "Credentials saved (OAuth flow required)"

    if conn_id == "hubspot":
        token = creds.get("access_token", "") or creds.get("api_key", "")
        if not token: return False, "Access token required"
        r = _get("https://api.hubapi.com/crm/v3/owners", headers={"Authorization": f"Bearer {token}"})
        count = len(r.json().get("results", []))
        return True, f"Connected — {count} owner(s) found"

    if conn_id == "salesforce":
        if not creds.get("instance_url") or not creds.get("access_token"):
            return False, "Instance URL and access token required"
        r = _get(f"{creds['instance_url']}/services/data/v57.0/", headers={"Authorization": f"Bearer {creds['access_token']}"})
        return True, f"Connected to {creds['instance_url']}"

    if conn_id == "jira":
        email = creds.get("email", ""); token = creds.get("api_token", ""); domain = creds.get("domain", "")
        if not email or not token or not domain: return False, "Email, API token, and domain required"
        import base64 as _b64
        auth = _b64.b64encode(f"{email}:{token}".encode()).decode()
        r = _get(f"https://{domain}/rest/api/3/myself", headers={"Authorization": f"Basic {auth}"})
        return True, f"Connected as {r.json().get('displayName', 'user')}"

    # ── Research & Knowledge ──────────────────────────────────────────────────
    if conn_id == "arxiv":
        r = _get("https://export.arxiv.org/api/query", params={"search_query": "ti:test", "max_results": "1"})
        return True, "arXiv API reachable (no key required)"

    if conn_id == "pubmed":
        r = _get("https://eutils.ncbi.nlm.nih.gov/entrez/eutils/esearch.fcgi", params={"db": "pubmed", "term": "test", "retmax": "1", "format": "json"})
        return True, "PubMed API reachable (no key required)"

    if conn_id == "semantic_scholar":
        r = _get("https://api.semanticscholar.org/graph/v1/paper/search", params={"query": "test", "limit": "1"})
        return True, "Semantic Scholar reachable (no key required)"

    if conn_id == "newsapi":
        key = creds.get("api_key", "")
        if not key: return False, "API key required"
        r = _get("https://newsapi.org/v2/top-headlines", params={"country": "us", "pageSize": "1", "apiKey": key})
        return True, f"Connected — {r.json().get('totalResults', 0)} articles available"

    if conn_id == "reddit":
        cid = creds.get("client_id", ""); secret = creds.get("client_secret", "")
        if not cid or not secret: return False, "Client ID and secret required"
        ua = creds.get("user_agent", "SovereignClaw/1.0")
        r = _hx.post("https://www.reddit.com/api/v1/access_token",
                     auth=(cid, secret), data={"grant_type": "client_credentials"},
                     headers={"User-Agent": ua}, timeout=8)
        if r.status_code != 200: return False, f"Auth failed ({r.status_code})"
        return True, "Connected (app-only OAuth)"

    if conn_id == "wikipedia":
        r = _get("https://en.wikipedia.org/w/api.php", params={"action": "query", "format": "json", "titles": "Test"})
        return True, "Wikipedia API reachable (no key required)"

    if conn_id == "youtube":
        key = creds.get("api_key", "")
        if not key: return False, "API key required"
        r = _get("https://www.googleapis.com/youtube/v3/videos", params={"part": "id", "id": "dQw4w9WgXcQ", "key": key})
        return True, f"Connected — {len(r.json().get('items', []))} result(s)"

    if conn_id == "github_api":
        token = creds.get("personal_access_token", "")
        if not token: return False, "Personal access token required"
        r = _get("https://api.github.com/user", headers={"Authorization": f"Bearer {token}"})
        return True, f"Connected as {r.json().get('login', 'user')}"

    if conn_id == "gitlab":
        token = creds.get("personal_access_token", ""); host = creds.get("host", "https://gitlab.com")
        if not token: return False, "Personal access token required"
        r = _get(f"{host}/api/v4/user", headers={"PRIVATE-TOKEN": token})
        return True, f"Connected as {r.json().get('username', 'user')}"

    if conn_id == "pinecone":
        key = creds.get("api_key", ""); env = creds.get("environment", "")
        if not key: return False, "API key required"
        r = _get(f"https://controller.{env}.pinecone.io/databases", headers={"Api-Key": key})
        return True, f"Connected — {len(r.json())} index(es)"

    if conn_id == "supabase":
        url = creds.get("url", ""); key = creds.get("anon_key", "")
        if not url or not key: return False, "URL and anon key required"
        r = _get(f"{url}/rest/v1/", headers={"apikey": key, "Authorization": f"Bearer {key}"})
        return True, f"Connected to {url}"

    # Generic fallback — just validate required fields are non-empty
    required = [v for v in creds.values() if v]
    if required:
        return True, "Credentials saved (live test not available for this integration)"
    return False, "No credentials provided"


# ══════════════════════════════════════════════════════════════════════════════
# Workflows — persistent multi-step execution engine
# ══════════════════════════════════════════════════════════════════════════════

_WORKFLOWS_FILE   = Path(__file__).parent / ".oricli" / "workflows.json"
_WORKFLOW_RUNS_FILE = Path(__file__).parent / ".oricli" / "workflow_runs.json"
_PROJECTS_FILE    = Path(__file__).parent / ".oricli" / "projects.json"
_WF_LOCK  = threading.Lock()
_WFR_LOCK = threading.Lock()
_PROJ_LOCK = threading.Lock()
_RUN_CONTROL: dict[str, str] = {}  # run_id → "cancel" | "pause" | "resume"


def _load_workflows() -> list:
    if _WORKFLOWS_FILE.exists():
        try:
            return json.loads(_WORKFLOWS_FILE.read_text())
        except Exception:
            pass
    return []


def _save_workflows(data: list) -> None:
    _WORKFLOWS_FILE.parent.mkdir(parents=True, exist_ok=True)
    _WORKFLOWS_FILE.write_text(json.dumps(data, indent=2))


def _load_projects() -> dict:
    if _PROJECTS_FILE.exists():
        try:
            return json.loads(_PROJECTS_FILE.read_text())
        except Exception:
            pass
    return {}


def _save_projects(data: dict) -> None:
    _PROJECTS_FILE.parent.mkdir(parents=True, exist_ok=True)
    _PROJECTS_FILE.write_text(json.dumps(data, indent=2))


def _load_runs() -> dict:
    if _WORKFLOW_RUNS_FILE.exists():
        try:
            return json.loads(_WORKFLOW_RUNS_FILE.read_text())
        except Exception:
            pass
    return {}


def _save_runs(data: dict) -> None:
    _WORKFLOW_RUNS_FILE.parent.mkdir(parents=True, exist_ok=True)
    _WORKFLOW_RUNS_FILE.write_text(json.dumps(data, indent=2))


_WF_BUILTIN_VARS: frozenset = frozenset({
    "output", "input", "date", "time", "datetime", "workflow_name",
    "doc_text", "doc_filename",
})


def _wf_interpolate(text: str, context: dict) -> str:
    """Replace {{var}} in step text. Resolves built-ins then context keys."""
    import re as _re
    from datetime import datetime as _dt
    now = _dt.now()
    builtins = {
        "date":          now.strftime("%B %-d, %Y"),
        "time":          now.strftime("%-I:%M %p"),
        "datetime":      now.strftime("%Y-%m-%d %H:%M"),
        "input":         context.get("output", ""),   # alias
    }
    full_ctx = {**builtins, **context}
    def replacer(m):
        key = m.group(1).strip()
        return str(full_ctx.get(key, m.group(0)))
    return _re.sub(r'\{\{([^}]+)\}\}', replacer, text or "")


def _scan_user_vars(wf: dict) -> list[str]:
    """Return sorted list of user-defined {{var}} names not covered by builtins."""
    import re as _re
    found: set[str] = set()
    for step in wf.get("steps", []):
        sources = [
            step.get("value", ""), step.get("input", ""),
            step.get("condition", ""),
            json.dumps(step.get("params") or {}),
        ]
        for text in sources:
            for m in _re.finditer(r'\{\{([^}]+)\}\}', text or ""):
                key = m.group(1).strip()
                if key not in _WF_BUILTIN_VARS and not key.startswith("step_"):
                    found.add(key)
    return sorted(found)


def _execute_step(step: dict, context: dict, run_id: str, step_idx: int, system_prompt: str = "", _sub_depth: int = 0) -> dict:
    """Execute one step. Returns {output, status, error}."""
    import httpx as _hx

    # Shared constants
    _LLM_TIMEOUT   = 300.0   # 5 min — local models are slow under load
    _MAX_CTX_CHARS = 12_000  # truncate large previous outputs before sending to LLM

    step_type  = step.get("type", "prompt")
    step_input = _wf_interpolate(step.get("value", "") or step.get("input", ""), context)
    result: dict = {"status": "done", "output": "", "error": None}

    def _trim(text: str, limit: int = _MAX_CTX_CHARS) -> str:
        if len(text) <= limit:
            return text
        return text[:limit] + f"\n\n…[truncated, {len(text) - limit} chars omitted]"

    try:
        if step_type == "prompt":
            messages = []
            if system_prompt:
                messages.append({"role": "system", "content": system_prompt})
            # Only inject prior context as system message if the user prompt doesn't
            # already reference {{output}} explicitly — avoids confusing duplicates
            output_in_prompt = "{{output}}" in (step.get("value", "") or step.get("input", ""))
            if context.get("output") and not output_in_prompt:
                messages.append({"role": "system", "content": f"Prior context:\n\n{_trim(context['output'])}"})
            messages.append({"role": "user", "content": step_input or "Continue."})
            result["output"] = _llm_complete(messages, max_tokens=3000, timeout=_LLM_TIMEOUT)

        elif step_type == "template":
            # Pure variable substitution — no LLM call. Useful for assembling
            # structured documents from prior step outputs.
            result["output"] = step_input  # _wf_interpolate already ran on line 1738

        elif step_type == "summarize":
            target = context.get("output", "")
            if not target:
                result["output"] = "(nothing to summarize)"
            else:
                instruction = step_input.strip() or "Summarize the following content concisely, highlighting key points and any action items."
                result["output"] = _llm_complete([
                    {"role": "system", "content": "You are a concise summarizer. Extract the essential information without losing important facts."},
                    {"role": "user", "content": f"{instruction}\n\n---\n{_trim(target)}"},
                ], max_tokens=1500, timeout=_LLM_TIMEOUT)

        elif step_type == "transform":
            target = context.get("output", step_input)
            result["output"] = _llm_complete([
                {"role": "system", "content": "Transform the input according to the instruction. Return only the transformed result."},
                {"role": "user", "content": f"Instruction: {step_input}\n\nInput:\n{_trim(target)}"},
            ], max_tokens=3000, timeout=_LLM_TIMEOUT)

        elif step_type == "extract":
            target = context.get("output", step_input)
            result["output"] = _llm_complete([
                {"role": "system", "content": "Extract the requested information. Return valid JSON only."},
                {"role": "user", "content": f"Extract: {step_input}\n\nSource:\n{_trim(target)}"},
            ], max_tokens=2000, timeout=_LLM_TIMEOUT)

        elif step_type == "web":
            query = (step_input or context.get("output", "")).strip()
            if not query:
                result["output"] = "⚠️ Web Search step has no query. Set the step value to a search term (e.g. 'latest AI news'), or use {{output}} to search using the prior step's output."
            else:
                # If prior output is very long, it's a bad query — extract first sentence only
                if len(query) > 300:
                    query = query.split("\n")[0][:300].strip()
                results = _ddg_search(query, max_results=5)
                if results:
                    lines = [f"**{r.get('title', '')}**\n{r.get('snippet', r.get('body', ''))}\n{r.get('url', '')}" for r in results]
                    result["output"] = f"Web search results for: {query}\n\n" + "\n\n---\n\n".join(lines)
                else:
                    result["output"] = f"No results found for: {query}"

        elif step_type == "fetch_url":
            url = step_input.strip()
            if not url.startswith("http"):
                raise ValueError(f"Invalid URL: {url}")
            r = _hx.get(url, timeout=20, follow_redirects=True,
                        headers={"User-Agent": "SovereignClaw/1.0"})
            r.raise_for_status()
            import html as _html
            import re as _re
            text = _html.unescape(_re.sub(r"<[^>]+>", " ", r.text))
            text = _re.sub(r"\s{3,}", "\n", text)[:8000]
            result["output"] = f"Content from {url}:\n\n{text.strip()}"

        elif step_type == "ingest_doc":
            doc_text = context.get("doc_text", "")
            doc_filename = context.get("doc_filename", "document")
            if not doc_text:
                raise ValueError("No document provided. Upload a file when starting the workflow.")
            save = step.get("saveToMemory", False) or context.get("save_to_memory", False)
            if save:
                _rag_ingest([{
                    "title":    doc_filename,
                    "content":  doc_text,
                    "source":   f"doc:{doc_filename}",
                    "metadata": {"filename": doc_filename, "source_type": "documents"},
                }], "documents")
            result["output"] = doc_text

        elif step_type == "rag_query":
            query = step_input or context.get("output", "")
            # Resolve source filter — '__all__' or None means search everything
            rag_source = step.get("ragSource") or step.get("rag_source")
            source_type = None if (not rag_source or rag_source == "__all__") else rag_source
            # Try backbone first
            _backbone_rag_ok = False
            try:
                r = _hx.post(
                    f"{_BACKBONE_URL}/v1/knowledge/query",
                    json={"query": query, "limit": 8},
                    headers={"Authorization": f"Bearer {_BACKBONE_KEY}"},
                    timeout=30,
                )
                if r.status_code == 200:
                    data = r.json()
                    facts = data.get("facts") or data.get("results") or []
                    if facts:
                        result["output"] = f"Knowledge query: {query}\n\n" + "\n\n".join(str(f) for f in facts[:8])
                        _backbone_rag_ok = True
            except Exception:
                pass
            # Fall back to local RAG store (with optional connection filter)
            if not _backbone_rag_ok:
                hits = _rag_search(query, limit=8, source_type=source_type)
                src_label = f" [{source_type}]" if source_type else ""
                if hits:
                    lines = [f"[{h['source']}] {h['title']}\n{h['snippet']}" for h in hits]
                    result["output"] = f"Knowledge query{src_label}: {query}\n\n" + "\n\n---\n\n".join(lines)
                else:
                    result["output"] = f"No indexed knowledge found{src_label} for: {query}"

        elif step_type == "condition":
            # Legacy: just evaluate and output true/false
            prev = context.get("output", "")
            result["output"] = _llm_complete([
                {"role": "system", "content": "Evaluate the following condition against the context. Reply with only 'true' or 'false'."},
                {"role": "user", "content": f"Condition: {step_input}\n\nContext: {prev}"},
            ], max_tokens=10)

        elif step_type == "if_else":
            # True branching: evaluate condition, run thenSteps or elseSteps
            condition_q = step.get("condition", step_input).strip()
            prev = context.get("output", "")
            verdict = _llm_complete([
                {"role": "system", "content": "Evaluate the condition below against the given context. Reply with only the single word 'true' or 'false'."},
                {"role": "user", "content": f"Condition: {condition_q}\n\nContext:\n{prev[:3000]}"},
            ], max_tokens=10).strip().lower()
            took_branch = "true" if "true" in verdict else "false"
            branch_steps = step.get("thenSteps", []) if took_branch == "true" else step.get("elseSteps", [])
            branch_context = dict(context)
            for bi, bs in enumerate(branch_steps):
                br = _execute_step(bs, branch_context, run_id, f"{step_idx}_b{bi}", system_prompt, _sub_depth)
                branch_context["output"] = br.get("output", branch_context.get("output", ""))
            result["output"] = branch_context.get("output", prev)
            result["branch"] = took_branch

        elif step_type == "notify":
            # Send a notification via a configured connection
            # Format: "connection_id: message" e.g. "discord: {{output}}"
            parts = step_input.split(":", 1)
            conn_id = parts[0].strip().lower()
            message = parts[1].strip() if len(parts) > 1 else context.get("output", "Workflow notification")

            with _CONN_LOCK:
                conns = _load_connections()
            cfg = conns.get(conn_id, {})
            creds = cfg.get("credentials", {})

            if conn_id == "discord" and creds.get("bot_token"):
                channel_id = creds.get("guild_id", step.get("channel", ""))
                if channel_id:
                    r = _hx.post(
                        f"https://discord.com/api/v10/channels/{channel_id}/messages",
                        headers={"Authorization": f"Bot {creds['bot_token']}", "Content-Type": "application/json"},
                        json={"content": message[:2000]},
                        timeout=15,
                    )
                    result["output"] = f"Discord notification sent (status {r.status_code})"
                else:
                    result["output"] = "Discord notify: no channel_id configured"
            elif conn_id == "telegram" and creds.get("bot_token"):
                chat_id = creds.get("default_chat_id", "")
                if chat_id:
                    r = _hx.post(
                        f"https://api.telegram.org/bot{creds['bot_token']}/sendMessage",
                        json={"chat_id": chat_id, "text": message[:4096]},
                        timeout=15,
                    )
                    result["output"] = f"Telegram notification sent (status {r.status_code})"
                else:
                    result["output"] = "Telegram notify: no chat_id configured"
            elif conn_id == "slack" and creds.get("bot_token"):
                channel = creds.get("default_channel", "#general")
                r = _hx.post(
                    "https://slack.com/api/chat.postMessage",
                    headers={"Authorization": f"Bearer {creds['bot_token']}"},
                    json={"channel": channel, "text": message},
                    timeout=15,
                )
                result["output"] = f"Slack notification sent (status {r.status_code})"
            else:
                result["output"] = f"Notify: connection '{conn_id}' not configured or not supported"

        elif step_type == "code":
            # Sandboxed Python exec — restricted builtins
            import io, contextlib
            safe_globals: dict = {
                "__builtins__": {
                    "print": print, "len": len, "range": range, "str": str, "int": int,
                    "float": float, "list": list, "dict": dict, "tuple": tuple, "set": set,
                    "bool": bool, "abs": abs, "round": round, "min": min, "max": max,
                    "sum": sum, "sorted": sorted, "enumerate": enumerate, "zip": zip,
                    "map": map, "filter": filter, "isinstance": isinstance, "type": type,
                    "repr": repr, "json": __import__("json"),
                },
                "input_text": context.get("output", ""),
                "context": dict(context),
            }
            buf = io.StringIO()
            with contextlib.redirect_stdout(buf):
                exec(step_input, safe_globals)  # noqa: S102
            result["output"] = buf.getvalue() or safe_globals.get("result", "(no output)")

        elif step_type == "sub_workflow":
            target_wf_id = step_input.strip() or step.get("workflowId", "")
            if not target_wf_id:
                raise ValueError("sub_workflow step requires a workflow ID")
            child_output = _execute_sub_workflow(target_wf_id, context, _depth=_sub_depth)
            result["output"] = child_output

        elif step_type == "fetch_connection":
            # Pull live data from a configured connection and emit as output
            conn_id = (step.get("connectionId") or step_input).strip()
            query_hint = step.get("query", "").strip()
            if not conn_id:
                raise ValueError("fetch_connection step requires a connection ID")
            fetcher = _FETCHERS.get(conn_id)
            if fetcher is None:
                raise ValueError(f"Connection '{conn_id}' is not fetchable")
            with _CONN_LOCK:
                conns = _load_connections()
            cfg = conns.get(conn_id, {})
            creds = cfg.get("credentials", cfg)
            opts: dict = {k: v for k, v in cfg.items() if k != "credentials"}
            # For telegram, pass a query so the fetcher reads from local RAG
            if query_hint:
                opts["query"] = query_hint
            docs = fetcher(creds, opts)
            if not docs:
                result["output"] = f"No data returned from connection '{conn_id}'"
            else:
                # Optional keyword filter on top of fetched docs
                if query_hint:
                    q_toks = set(query_hint.lower().split())
                    scored = []
                    for d in docs:
                        text = f"{d.get('title','')} {d.get('content','')}".lower()
                        score = sum(1 for t in q_toks if t in text)
                        if score:
                            scored.append((score, d))
                    if scored:
                        scored.sort(key=lambda x: x[0], reverse=True)
                        docs = [d for _, d in scored[:20]]
                lines = []
                for d in docs[:25]:
                    title = d.get("title") or d.get("subject") or "(untitled)"
                    content = (d.get("content") or "").strip()[:500]
                    lines.append(f"### {title}\n{content}")
                result["output"] = "\n\n---\n\n".join(lines)

        else:
            result["output"] = f"Unknown step type: {step_type}"

    except Exception as exc:
        result["status"] = "error"
        result["error"] = str(exc)
        result["output"] = f"[Error in step: {exc}]"

    return result


def _execute_sub_workflow(wf_id: str, initial_context: dict, _depth: int = 0) -> str:
    """Run a sub-workflow synchronously and return its final output.

    Cycles are prevented by a hard depth cap of 5. The parent's current
    ``output`` is injected into the child's context so chaining works
    without any extra config.
    """
    _MAX_DEPTH = 5
    if _depth >= _MAX_DEPTH:
        raise RuntimeError(f"Sub-workflow depth limit ({_MAX_DEPTH}) reached — possible cycle detected")

    with _WF_LOCK:
        workflows = _load_workflows()
    wf = next((w for w in workflows if w["id"] == wf_id), None)
    if not wf:
        raise ValueError(f"Sub-workflow not found: {wf_id}")

    steps = wf.get("steps", [])
    system_prompt = ""
    agent_id = wf.get("agentId")
    if agent_id:
        ori_path = Path(__file__).parent / "oricli_core" / "skills" / f"{agent_id}.ori"
        if ori_path.exists():
            parsed = _parse_ori(agent_id, ori_path.read_text(encoding="utf-8"))
            system_prompt = parsed.get("systemPrompt", "")

    # Seed child context with parent's current output
    context: dict = dict(initial_context)
    context.setdefault("output", "")

    for idx, step in enumerate(steps):
        # Propagate depth so nested sub_workflow steps also respect the cap
        step_result = _execute_step(step, context, run_id="sub", step_idx=idx,
                                    system_prompt=system_prompt, _sub_depth=_depth + 1)
        context["output"] = step_result["output"]
        context[f"step_{idx}_output"] = step_result["output"]
        context[f"step_{idx + 1}_input"] = step_result["output"]
        if step_result["status"] == "error" and step.get("haltOnError", True):
            raise RuntimeError(step_result["error"] or "Sub-workflow step failed")

    return context.get("output", "")


def _run_workflow_job(wf_id: str, run_id: str) -> None:
    """Background thread: execute all workflow steps sequentially."""
    with _WF_LOCK:
        workflows = _load_workflows()
    wf = next((w for w in workflows if w["id"] == wf_id), None)
    if not wf:
        return

    steps = wf.get("steps", [])
    system_prompt = ""
    agent_id = wf.get("agentId")
    if agent_id:
        ori_path = Path(__file__).parent / "oricli_core" / "skills" / f"{agent_id}.ori"
        if ori_path.exists():
            parsed = _parse_ori(agent_id, ori_path.read_text(encoding="utf-8"))
            system_prompt = parsed.get("systemPrompt", "")

    def update_run(patch: dict):
        with _WFR_LOCK:
            runs = _load_runs()
            run = runs.get(run_id, {})
            run.update(patch)
            runs[run_id] = run
            _save_runs(runs)

    update_run({"status": "running", "started": datetime.now(timezone.utc).isoformat(),
                "steps": [{"status": "pending", "output": "", "error": None} for _ in steps]})

    context: dict = {"output": "", "step_0_output": "", "workflow_name": wf.get("name", "")}
    all_outputs = []

    # Inject doc_text and user_vars from run payload into context
    with _WFR_LOCK:
        runs = _load_runs()
    run_meta = runs.get(run_id, {})
    if run_meta.get("doc_text"):
        context["doc_text"] = run_meta["doc_text"]
        context["doc_filename"] = run_meta.get("doc_filename", "document")
        context["save_to_memory"] = run_meta.get("save_to_memory", False)
    # User-defined run-time variables (e.g. {{topic}}, {{client_name}})
    for k, v in (run_meta.get("user_vars") or {}).items():
        context[k] = v

    for idx, step in enumerate(steps):
        # ── Stop / Pause control ──────────────────────────────────────────
        ctrl = _RUN_CONTROL.get(run_id)
        if ctrl == "cancel":
            _RUN_CONTROL.pop(run_id, None)
            update_run({"status": "cancelled", "finished": datetime.now(timezone.utc).isoformat(),
                        "final_output": context.get("output", "")})
            return
        if ctrl == "pause":
            update_run({"status": "paused"})
            while _RUN_CONTROL.get(run_id) == "pause":
                time.sleep(0.5)
            if _RUN_CONTROL.get(run_id) == "cancel":
                _RUN_CONTROL.pop(run_id, None)
                update_run({"status": "cancelled", "finished": datetime.now(timezone.utc).isoformat(),
                            "final_output": context.get("output", "")})
                return
            _RUN_CONTROL.pop(run_id, None)
            update_run({"status": "running"})
        # ─────────────────────────────────────────────────────────────────

        # Mark step as running
        with _WFR_LOCK:
            runs = _load_runs()
            run = runs.get(run_id, {})
            run["steps"][idx]["status"] = "running"
            run["steps"][idx]["started"] = datetime.now(timezone.utc).isoformat()
            runs[run_id] = run
            _save_runs(runs)

        step_result = _execute_step(step, context, run_id, idx, system_prompt)
        all_outputs.append(step_result["output"])

        # Update context for chaining
        context["output"] = step_result["output"]
        context[f"step_{idx}_output"] = step_result["output"]
        context[f"step_{idx + 1}_input"] = step_result["output"]

        # Persist step result
        with _WFR_LOCK:
            runs = _load_runs()
            run = runs.get(run_id, {})
            run["steps"][idx].update({
                "status":   step_result["status"],
                "output":   step_result["output"],
                "error":    step_result["error"],
                "finished": datetime.now(timezone.utc).isoformat(),
            })
            runs[run_id] = run
            _save_runs(runs)

        if step_result["status"] == "error" and step.get("haltOnError", True):
            update_run({"status": "error", "finished": datetime.now(timezone.utc).isoformat(),
                        "final_output": step_result["output"]})
            return

    update_run({"status": "done", "finished": datetime.now(timezone.utc).isoformat(),
                "final_output": context["output"]})


# ── Workflow CRUD routes ──────────────────────────────────────────────────────

@app.route("/workflows", methods=["GET"])
def list_workflows_api() -> Response:
    with _WF_LOCK:
        return jsonify({"workflows": _load_workflows()})


@app.route("/workflows", methods=["POST"])
def create_workflow() -> Response:
    body = request.get_json(silent=True) or {}
    wf = {
        "id":          str(uuid.uuid4()),
        "name":        body.get("name", "Untitled workflow"),
        "description": body.get("description", ""),
        "project_id":  body.get("project_id") or None,
        "agentId":     body.get("agentId"),
        "agentName":   body.get("agentName", "Default"),
        "agentEmoji":  body.get("agentEmoji", "✨"),
        "steps":       body.get("steps", []),
        "createdAt":   datetime.now(timezone.utc).isoformat(),
        "updatedAt":   datetime.now(timezone.utc).isoformat(),
    }
    with _WF_LOCK:
        wfs = _load_workflows()
        wfs.append(wf)
        _save_workflows(wfs)
    return jsonify({"workflow": wf})


@app.route("/workflows/<wf_id>", methods=["PUT"])
def update_workflow(wf_id: str) -> Response:
    body = request.get_json(silent=True) or {}
    with _WF_LOCK:
        wfs = _load_workflows()
        for wf in wfs:
            if wf["id"] == wf_id:
                wf.update({k: v for k, v in body.items() if k not in ("id", "createdAt")})
                wf["updatedAt"] = datetime.now(timezone.utc).isoformat()
                break
        _save_workflows(wfs)
    return jsonify({"ok": True})


@app.route("/workflows/<wf_id>", methods=["DELETE"])
def delete_workflow_api(wf_id: str) -> Response:
    with _WF_LOCK:
        wfs = _load_workflows()
        wfs = [w for w in wfs if w["id"] != wf_id]
        _save_workflows(wfs)
    return jsonify({"ok": True})


@app.route("/workflows/ingest-doc", methods=["POST"])
def workflow_ingest_doc() -> Response:
    """Extract text from an uploaded PDF/TXT/CSV for use in a workflow step."""
    file = request.files.get("file")
    if not file:
        return jsonify({"error": "No file provided"}), 400

    filename = file.filename or "document"
    ext = filename.rsplit(".", 1)[-1].lower() if "." in filename else ""
    raw = file.read()
    text = ""

    try:
        if ext == "pdf":
            import pypdf, io as _io
            reader = pypdf.PdfReader(_io.BytesIO(raw))
            pages = [p.extract_text() or "" for p in reader.pages]
            text = "\n\n".join(p.strip() for p in pages if p.strip())
        elif ext == "csv":
            import csv, io as _io
            decoded = raw.decode("utf-8", errors="replace")
            reader = csv.reader(_io.StringIO(decoded))
            rows = list(reader)
            if rows:
                header = rows[0]
                lines = [", ".join(header)]
                for row in rows[1:]:
                    lines.append(", ".join(row))
                text = "\n".join(lines)
        elif ext in ("txt", "md", "rst", "log", "json", "yaml", "yml", "xml", "html"):
            text = raw.decode("utf-8", errors="replace")
        else:
            return jsonify({"error": f"Unsupported file type: .{ext}. Use PDF, TXT, or CSV."}), 400
    except Exception as exc:
        return jsonify({"error": f"Failed to extract text: {exc}"}), 500

    if not text.strip():
        return jsonify({"error": "No readable text found in document"}), 400

    return jsonify({
        "filename": filename,
        "chars": len(text),
        "preview": text[:300],
        "text": text[:50_000],  # cap at 50k chars
    })


@app.route("/workflows/<wf_id>/run", methods=["POST"])
def run_workflow(wf_id: str) -> Response:
    body = request.get_json(silent=True) or {}
    run_id = str(uuid.uuid4())
    with _WFR_LOCK:
        runs = _load_runs()
        runs[run_id] = {
            "id":           run_id,
            "wf_id":        wf_id,
            "status":       "queued",
            "steps":        [],
            "created":      datetime.now(timezone.utc).isoformat(),
            "final_output": None,
            "doc_text":     body.get("doc_text", ""),
            "save_to_memory": bool(body.get("save_to_memory", False)),
            "doc_filename": body.get("doc_filename", ""),
            "user_vars":    body.get("user_vars") or {},
        }
        _save_runs(runs)
    t = threading.Thread(target=_run_workflow_job, args=(wf_id, run_id), daemon=True)
    t.start()
    return jsonify({"run_id": run_id, "status": "queued"})


@app.route("/workflows/<wf_id>/vars", methods=["GET"])
def get_workflow_vars(wf_id: str) -> Response:
    """Return list of user-defined {{var}} names used in the workflow's steps."""
    with _WF_LOCK:
        wfs = _load_workflows()
    wf = next((w for w in wfs if w["id"] == wf_id), None)
    if not wf:
        return jsonify({"error": "not found"}), 404
    return jsonify({"vars": _scan_user_vars(wf)})


@app.route("/workflows/runs/<run_id>", methods=["GET"])
def get_run_status(run_id: str) -> Response:
    with _WFR_LOCK:
        runs = _load_runs()
    run = runs.get(run_id)
    if not run:
        return jsonify({"error": "run not found"}), 404
    return jsonify(run)


@app.route("/workflows/runs/<run_id>/cancel", methods=["POST"])
def cancel_run(run_id: str) -> Response:
    with _WFR_LOCK:
        runs = _load_runs()
        run = runs.get(run_id, {})
        if run.get("status") in ("done", "error", "cancelled"):
            return jsonify({"status": run.get("status")})
        # Persist cancelling immediately so the poller sees it and stops overwriting
        run["status"] = "cancelling"
        runs[run_id] = run
        _save_runs(runs)
    _RUN_CONTROL[run_id] = "cancel"
    return jsonify({"status": "cancelling"})


@app.route("/workflows/runs/<run_id>/pause", methods=["POST"])
def pause_run(run_id: str) -> Response:
    with _WFR_LOCK:
        runs = _load_runs()
        run = runs.get(run_id, {})
        if run:
            run["status"] = "pausing"
            runs[run_id] = run
            _save_runs(runs)
    _RUN_CONTROL[run_id] = "pause"
    return jsonify({"status": "pausing"})


@app.route("/workflows/runs/<run_id>/resume", methods=["POST"])
def resume_run(run_id: str) -> Response:
    if _RUN_CONTROL.get(run_id) == "pause":
        _RUN_CONTROL[run_id] = "resume"
    return jsonify({"status": "resuming"})


@app.route("/workflows/<wf_id>/runs", methods=["GET"])
def list_wf_runs(wf_id: str) -> Response:
    with _WFR_LOCK:
        runs = _load_runs()
    wf_runs = sorted(
        [r for r in runs.values() if r.get("wf_id") == wf_id],
        key=lambda r: r.get("created", ""), reverse=True
    )[:20]
    return jsonify({"runs": wf_runs})


# ── Pipeline (visual orchestration canvas) CRUD + run ────────────────────────

_PIPELINES_FILE = Path(__file__).parent / ".oricli" / "pipelines.json"
_PIPE_LOCK = threading.Lock()


def _load_pipelines() -> list:
    if _PIPELINES_FILE.exists():
        try:
            return json.loads(_PIPELINES_FILE.read_text())
        except Exception:
            pass
    return []


def _save_pipelines(data: list) -> None:
    _PIPELINES_FILE.parent.mkdir(parents=True, exist_ok=True)
    _PIPELINES_FILE.write_text(json.dumps(data, indent=2))


def _topo_sort(nodes: list, edges: list) -> list[str]:
    """Return node ids in topological execution order (Kahn's algorithm)."""
    in_degree: dict[str, int] = {n["id"]: 0 for n in nodes}
    adj: dict[str, list[str]] = {n["id"]: [] for n in nodes}
    for e in edges:
        src, tgt = e.get("source"), e.get("target")
        if src in adj and tgt in in_degree:
            adj[src].append(tgt)
            in_degree[tgt] += 1
    queue = [nid for nid, deg in in_degree.items() if deg == 0]
    order: list[str] = []
    while queue:
        nid = queue.pop(0)
        order.append(nid)
        for tgt in adj[nid]:
            in_degree[tgt] -= 1
            if in_degree[tgt] == 0:
                queue.append(tgt)
    return order


def _run_pipeline_job(pipeline_id: str, run_id: str) -> None:
    """Execute pipeline workflows in topological order, chaining outputs."""
    with _PIPE_LOCK:
        pipelines = _load_pipelines()
    pipeline = next((p for p in pipelines if p["id"] == pipeline_id), None)
    if not pipeline:
        return

    nodes  = pipeline.get("nodes", [])
    edges  = pipeline.get("edges", [])
    order  = _topo_sort(nodes, edges)
    node_map = {n["id"]: n for n in nodes}

    # Run metadata — node_statuses: {node_id: {status, output, error, started, finished}}
    run_data: dict = {
        "id":           run_id,
        "pipeline_id":  pipeline_id,
        "status":       "running",
        "started":      datetime.now(timezone.utc).isoformat(),
        "node_statuses": {n["id"]: {"status": "pending", "output": "", "error": None} for n in nodes},
    }

    runs_file = Path(__file__).parent / ".oricli" / "pipeline_runs.json"

    def _save_run():
        runs_file.parent.mkdir(parents=True, exist_ok=True)
        all_runs: dict = {}
        if runs_file.exists():
            try:
                all_runs = json.loads(runs_file.read_text())
            except Exception:
                pass
        all_runs[run_id] = run_data
        runs_file.write_text(json.dumps(all_runs, indent=2))

    _save_run()

    context_output = ""  # chained output between nodes

    for node_id in order:
        node = node_map.get(node_id)
        if not node:
            continue
        wf_id = node.get("wfId") or node.get("data", {}).get("wfId")
        if not wf_id:
            run_data["node_statuses"][node_id]["status"] = "skipped"
            _save_run()
            continue

        run_data["node_statuses"][node_id]["status"] = "running"
        run_data["node_statuses"][node_id]["started"] = datetime.now(timezone.utc).isoformat()
        _save_run()

        try:
            # Execute the workflow as a sub-workflow, passing chained context
            with _WF_LOCK:
                workflows = _load_workflows()
            wf = next((w for w in workflows if w["id"] == wf_id), None)
            if not wf:
                raise ValueError(f"Workflow '{wf_id}' not found")

            init_ctx: dict = {
                "output":        context_output,
                "input":         context_output,
                "workflow_name": wf.get("name", ""),
            }
            result_output = _execute_sub_workflow(wf_id, init_ctx)
            context_output = result_output

            run_data["node_statuses"][node_id].update({
                "status":   "done",
                "output":   result_output,
                "finished": datetime.now(timezone.utc).isoformat(),
            })
        except Exception as exc:
            run_data["node_statuses"][node_id].update({
                "status":   "error",
                "error":    str(exc),
                "output":   f"[Error: {exc}]",
                "finished": datetime.now(timezone.utc).isoformat(),
            })
        _save_run()

    run_data["status"]   = "done"
    run_data["finished"] = datetime.now(timezone.utc).isoformat()
    run_data["final_output"] = context_output
    _save_run()


@app.route("/pipelines", methods=["GET"])
def list_pipelines() -> Response:
    with _PIPE_LOCK:
        return jsonify({"pipelines": _load_pipelines()})


@app.route("/pipelines", methods=["POST"])
def create_pipeline() -> Response:
    body = request.get_json(silent=True) or {}
    pipe: dict = {
        "id":          f"pipe_{uuid.uuid4().hex[:10]}",
        "name":        body.get("name", "Untitled Pipeline"),
        "description": body.get("description", ""),
        "nodes":       body.get("nodes", []),
        "edges":       body.get("edges", []),
        "createdAt":   datetime.now(timezone.utc).isoformat(),
        "updatedAt":   datetime.now(timezone.utc).isoformat(),
    }
    with _PIPE_LOCK:
        pipes = _load_pipelines()
        pipes.append(pipe)
        _save_pipelines(pipes)
    return jsonify(pipe), 201


@app.route("/pipelines/<pipe_id>", methods=["PUT"])
def update_pipeline(pipe_id: str) -> Response:
    body = request.get_json(silent=True) or {}
    with _PIPE_LOCK:
        pipes = _load_pipelines()
        idx = next((i for i, p in enumerate(pipes) if p["id"] == pipe_id), None)
        if idx is None:
            return jsonify({"error": "Not found"}), 404
        pipes[idx].update({k: v for k, v in body.items() if k not in ("id", "createdAt")})
        pipes[idx]["updatedAt"] = datetime.now(timezone.utc).isoformat()
        _save_pipelines(pipes)
        return jsonify(pipes[idx])


@app.route("/pipelines/<pipe_id>", methods=["DELETE"])
def delete_pipeline(pipe_id: str) -> Response:
    with _PIPE_LOCK:
        pipes = _load_pipelines()
        pipes = [p for p in pipes if p["id"] != pipe_id]
        _save_pipelines(pipes)
    return jsonify({"ok": True})


@app.route("/pipelines/<pipe_id>/run", methods=["POST"])
def run_pipeline(pipe_id: str) -> Response:
    run_id = f"prun_{uuid.uuid4().hex[:12]}"
    t = threading.Thread(target=_run_pipeline_job, args=(pipe_id, run_id), daemon=True)
    t.start()
    return jsonify({"run_id": run_id})


@app.route("/pipelines/runs/<run_id>", methods=["GET"])
def get_pipeline_run(run_id: str) -> Response:
    runs_file = Path(__file__).parent / ".oricli" / "pipeline_runs.json"
    if not runs_file.exists():
        return jsonify({"error": "Not found"}), 404
    try:
        all_runs = json.loads(runs_file.read_text())
        run = all_runs.get(run_id)
        if not run:
            return jsonify({"error": "Not found"}), 404
        return jsonify(run)
    except Exception as exc:
        return jsonify({"error": str(exc)}), 500

@app.route("/projects", methods=["GET"])
def list_projects() -> Response:
    with _PROJ_LOCK:
        projects = _load_projects()
    with _WF_LOCK:
        workflows = _load_workflows()
    # Attach workflow count to each project
    counts: dict[str, int] = {}
    for wf in workflows:
        pid = wf.get("project_id")
        if pid:
            counts[pid] = counts.get(pid, 0) + 1
    result = [dict(p, wf_count=counts.get(p["id"], 0)) for p in projects.values()]
    result.sort(key=lambda p: p.get("createdAt", ""))
    return jsonify({"projects": result})


@app.route("/projects", methods=["POST"])
def create_project() -> Response:
    body = request.get_json(silent=True) or {}
    proj = {
        "id":        str(uuid.uuid4()),
        "name":      body.get("name", "New Project"),
        "color":     body.get("color", "#7c6af7"),
        "createdAt": datetime.now(timezone.utc).isoformat(),
    }
    with _PROJ_LOCK:
        projects = _load_projects()
        projects[proj["id"]] = proj
        _save_projects(projects)
    return jsonify({"project": proj})


@app.route("/projects/<proj_id>", methods=["PATCH"])
def update_project(proj_id: str) -> Response:
    body = request.get_json(silent=True) or {}
    with _PROJ_LOCK:
        projects = _load_projects()
        if proj_id not in projects:
            return jsonify({"error": "not found"}), 404
        for k, v in body.items():
            if k not in ("id", "createdAt"):
                projects[proj_id][k] = v
        _save_projects(projects)
    return jsonify({"project": projects[proj_id]})


@app.route("/projects/<proj_id>", methods=["DELETE"])
def delete_project(proj_id: str) -> Response:
    with _PROJ_LOCK:
        projects = _load_projects()
        projects.pop(proj_id, None)
        _save_projects(projects)
    # Unassign workflows that belonged to this project
    with _WF_LOCK:
        wfs = _load_workflows()
        for wf in wfs:
            if wf.get("project_id") == proj_id:
                wf["project_id"] = None
        _save_workflows(wfs)
    return jsonify({"ok": True})


@app.route("/projects/<proj_id>/run", methods=["POST"])
def run_project(proj_id: str) -> Response:
    """Fire all entry-point workflows in a project (those not targeted by any sub_workflow step within the project)."""
    with _WF_LOCK:
        all_wfs = _load_workflows()
    proj_wfs = [w for w in all_wfs if w.get("project_id") == proj_id]
    if not proj_wfs:
        return jsonify({"error": "No workflows in this project"}), 400

    proj_ids = {w["id"] for w in proj_wfs}

    # Build set of wf_ids that are targets of a sub_workflow step within this project
    targeted: set[str] = set()
    for wf in proj_wfs:
        for step in wf.get("steps", []):
            if step.get("type") == "sub_workflow":
                tid = (step.get("params") or {}).get("wf_id") or step.get("wf_id")
                if tid and tid in proj_ids:
                    targeted.add(tid)

    entry_wfs = [w for w in proj_wfs if w["id"] not in targeted]
    if not entry_wfs:
        # Cycle or all targeted — just run all
        entry_wfs = proj_wfs

    run_ids = []
    for wf in entry_wfs:
        run_id = str(uuid.uuid4())
        with _WFR_LOCK:
            runs = _load_runs()
            runs[run_id] = {
                "id":           run_id,
                "wf_id":        wf["id"],
                "project_id":   proj_id,
                "status":       "queued",
                "steps":        [],
                "created":      datetime.now(timezone.utc).isoformat(),
                "final_output": None,
            }
            _save_runs(runs)
        threading.Thread(target=_run_workflow_job, args=(wf["id"], run_id), daemon=True).start()
        run_ids.append(run_id)

    return jsonify({"ok": True, "run_ids": run_ids, "entry_workflows": [w["id"] for w in entry_wfs]})


# ── ORI Syntax: Serializer + Parser + Routes ─────────────────────────────────

_ORI_TYPE_TO_KW: dict[str, str] = {
    "prompt": "prompt", "summarize": "summarize", "transform": "transform",
    "extract": "extract", "web": "web", "code": "code", "template": "template",
    "notify": "notify", "memory_search": "search", "rag_query": "rag",
    "ingest_doc": "ingest", "fetch_connection": "fetch", "sub_workflow": "run",
}
_ORI_KW_TO_TYPE: dict[str, str] = {v: k for k, v in _ORI_TYPE_TO_KW.items() if k != "sub_workflow"}


def _ori_serialize(wf: dict, all_workflows: list | None = None) -> str:
    """Serialize a workflow dict to .ori source text."""
    import re as _re
    wf_name_map = {w["id"]: w["name"] for w in (all_workflows or [])}

    lines: list[str] = [f'workflow "{wf.get("name", "Untitled")}" {{']
    if wf.get("description"):
        lines.append(f'  description: "{wf["description"]}"')
    if wf.get("agentId"):
        lines.append(f'  agent: @{wf["agentId"]}')
    if wf.get("sendToCanvas"):
        lines.append(f'  sendToCanvas: true')

    # Detect user-defined vars
    vars_found: set[str] = set()
    for step in wf.get("steps", []):
        for text in [step.get("value", ""), step.get("condition", ""),
                     json.dumps(step.get("params") or {}), step.get("input", "")]:
            for m in re.finditer(r'\{\{([^}]+)\}\}', text or ""):
                key = m.group(1).strip()
                if key not in _WF_BUILTIN_VARS and not key.startswith("step_"):
                    vars_found.add(key)
    if vars_found:
        lines.append("")
        for v in sorted(vars_found):
            lines.append(f"  var {v}")

    def fmt_val(v: str) -> str:
        if not v:
            return ""
        if "\n" in v:
            return f" `{v}`"
        return f' "{v.replace(chr(34), chr(92)+chr(34))}"'

    def ser(steps: list, indent: str = "  ") -> list[str]:
        out: list[str] = []
        for step in steps:
            stype = step.get("type", "prompt")
            label = step.get("label", "")
            value = step.get("value", "") or step.get("input", "")
            lp = f"[{label}]" if label else ""

            if stype == "if_else":
                cond = step.get("condition") or value or ""
                out.append(f'{indent}if "{cond}" {{')
                out.extend(ser(step.get("thenSteps") or [], indent + "  "))
                out.append(f'{indent}}}')
                if step.get("elseSteps"):
                    out.append(f'{indent}else {{')
                    out.extend(ser(step.get("elseSteps") or [], indent + "  "))
                    out.append(f'{indent}}}')

            elif stype == "sub_workflow":
                wf_id = (step.get("params") or {}).get("wf_id") or value or ""
                display = wf_name_map.get(wf_id, "")
                comment = f"  # {display}" if display and display != wf_id else ""
                out.append(f'{indent}run @{wf_id}{comment}')

            elif stype == "fetch_connection":
                conn_id = (step.get("params") or {}).get("connectionId", "")
                kw = value or ""
                kw_part = f' "{kw}"' if kw else ""
                out.append(f'{indent}step{lp}: fetch @{conn_id}{kw_part}')

            else:
                kw = _ORI_TYPE_TO_KW.get(stype, stype)
                out.append(f'{indent}step{lp}: {kw}{fmt_val(value)}')
        return out

    lines.append("")
    lines.extend(ser(wf.get("steps", [])))

    if wf.get("sendToCanvas"):
        lines.append("")
        lines.append("  output → canvas")

    lines.append("}")
    return "\n".join(lines)


def _ori_parse(source: str) -> dict:
    """Parse .ori source → {ok, workflow, diagnostics, vars}."""
    diagnostics: list[dict] = []

    def err(msg: str):  diagnostics.append({"level": "error",   "message": msg})
    def warn(msg: str): diagnostics.append({"level": "warning", "message": msg})
    def info(msg: str): diagnostics.append({"level": "info",    "message": msg})

    # Strip line comments
    src = re.sub(r'#[^\n]*', '', source)

    hdr = re.search(r'workflow\s+"([^"]+)"\s*\{', src)
    if not hdr:
        err('Missing workflow declaration. Expected: workflow "Name" { ... }')
        return {"ok": False, "workflow": None, "diagnostics": diagnostics, "vars": []}

    wf: dict = {
        "id": str(uuid.uuid4()), "name": hdr.group(1), "description": "",
        "agentId": None, "agentName": "Default", "agentEmoji": "✨",
        "steps": [], "sendToCanvas": False, "project_id": None,
    }
    vars_found: set[str] = set()

    # Extract outer block
    def extract_block(s: str, from_pos: int) -> tuple[str, int]:
        depth = 0
        i = from_pos
        while i < len(s):
            if s[i] == '{':
                depth += 1
            elif s[i] == '}':
                depth -= 1
                if depth == 0:
                    return s[from_pos + 1:i], i + 1
            i += 1
        return s[from_pos + 1:], len(s)

    # Find brace that closes the workflow header
    brace_pos = src.index('{', hdr.start())
    body, _ = extract_block(src, brace_pos)

    def get_stmts(text: str) -> list[str]:
        """Split body text into balanced statements."""
        stmts: list[str] = []
        lines = text.splitlines()
        j = 0
        while j < len(lines):
            line = lines[j].strip()
            if not line:
                j += 1
                continue
            opens = line.count('{') - line.count('}')
            if opens > 0:
                buf = [line]
                j += 1
                depth = opens
                while j < len(lines) and depth > 0:
                    bl = lines[j]
                    depth += bl.count('{') - bl.count('}')
                    buf.append(bl.strip())
                    j += 1
                stmts.append('\n'.join(buf))
            else:
                stmts.append(line)
                j += 1
        return stmts

    def read_val(text: str) -> str:
        t = text.strip()
        mq = re.match(r'"((?:[^"\\]|\\.)*)"', t)
        if mq:
            return mq.group(1).replace('\\"', '"')
        mb = re.match(r'`(.*?)`', t, re.DOTALL)
        if mb:
            return mb.group(1)
        return t

    def extract_block_from_stmt(stmt: str) -> tuple[str, str]:
        """Return (inner, after_close) for the first {...} block in stmt."""
        s = stmt.index('{')
        e = stmt.rindex('}')
        return stmt[s + 1:e].strip(), stmt[e + 1:].strip()

    def parse_stmts(stmts: list[str]) -> list[dict]:
        steps: list[dict] = []
        k = 0
        while k < len(stmts):
            stmt = stmts[k]

            # metadata
            m = re.match(r'description\s*:\s*"([^"]*)"', stmt)
            if m: wf["description"] = m.group(1); k += 1; continue

            m = re.match(r'agent\s*:\s*@(\S+)', stmt)
            if m: wf["agentId"] = m.group(1); k += 1; continue

            if re.match(r'sendToCanvas\s*:\s*true', stmt):
                wf["sendToCanvas"] = True; k += 1; continue

            m = re.match(r'var\s+(\w+)', stmt)
            if m: vars_found.add(m.group(1)); k += 1; continue

            m = re.match(r'output\s*(?:→|->)\s*(\S+)', stmt)
            if m:
                if m.group(1) == "canvas": wf["sendToCanvas"] = True
                k += 1; continue

            # run @wf-id
            m = re.match(r'run\s+@(\S+)', stmt)
            if m:
                steps.append({"id": str(uuid.uuid4()), "type": "sub_workflow",
                               "value": m.group(1), "label": "",
                               "params": {"wf_id": m.group(1)}})
                k += 1; continue

            # if "cond" { ... } [else { ... }]
            m = re.match(r'if\s+"([^"]*)"', stmt)
            if m and '{' in stmt:
                condition = m.group(1)
                then_body, _ = extract_block_from_stmt(stmt)
                then_steps = parse_stmts(get_stmts(then_body))
                else_steps: list[dict] = []
                if k + 1 < len(stmts) and re.match(r'else\s*\{', stmts[k + 1]):
                    else_body, _ = extract_block_from_stmt(stmts[k + 1])
                    else_steps = parse_stmts(get_stmts(else_body))
                    k += 1
                steps.append({"id": str(uuid.uuid4()), "type": "if_else",
                               "value": condition, "condition": condition, "label": "",
                               "thenSteps": then_steps, "elseSteps": else_steps})
                k += 1; continue

            # step[label]: type [@conn] ["value"]
            m = re.match(r'step(?:\[([^\]]*)\])?\s*:\s*(\w+)(.*)', stmt)
            if m:
                s_label = m.group(1) or ""
                s_kw    = m.group(2)
                s_rest  = m.group(3).strip()

                if s_kw == "fetch":
                    at_m = re.search(r'@(\S+)', s_rest)
                    kw_m = re.search(r'"([^"]*)"', s_rest)
                    steps.append({"id": str(uuid.uuid4()), "type": "fetch_connection",
                                  "value": kw_m.group(1) if kw_m else "", "label": s_label,
                                  "params": {"connectionId": at_m.group(1) if at_m else ""}})
                else:
                    s_type = _ORI_KW_TO_TYPE.get(s_kw, s_kw)
                    s_val  = read_val(s_rest) if s_rest else ""
                    steps.append({"id": str(uuid.uuid4()), "type": s_type,
                                  "value": s_val, "label": s_label})
                k += 1; continue

            # skip else / closing braces / unknown
            if stmt and not stmt.startswith("else") and stmt != "}":
                warn(f'Unrecognized statement: "{stmt[:70]}"')
            k += 1
        return steps

    wf["steps"] = parse_stmts(get_stmts(body))

    if not wf["steps"]:
        warn("No steps found in workflow body")
    else:
        info(f"{len(wf['steps'])} step(s) parsed successfully")
    if vars_found:
        info(f"Variables declared: {', '.join(sorted(vars_found))}")
    for step in wf["steps"]:
        if step["type"] == "sub_workflow":
            warn(f"run @{step['value']} — verify this workflow ID exists")

    return {
        "ok": not any(d["level"] == "error" for d in diagnostics),
        "workflow": wf,
        "diagnostics": diagnostics,
        "vars": sorted(vars_found),
    }


@app.route("/ori/compile", methods=["POST"])
def ori_compile() -> Response:
    body = request.get_json(silent=True) or {}
    source = body.get("source", "")
    if not source.strip():
        return jsonify({"ok": False, "workflow": None,
                        "diagnostics": [{"level": "error", "message": "Empty source"}], "vars": []})
    return jsonify(_ori_parse(source))


@app.route("/ori/decompile/<wf_id>", methods=["GET"])
def ori_decompile(wf_id: str) -> Response:
    with _WF_LOCK:
        wfs = _load_workflows()
    wf = next((w for w in wfs if w["id"] == wf_id), None)
    if not wf:
        return jsonify({"error": "not found"}), 404
    source = _ori_serialize(wf, all_workflows=wfs)
    return jsonify({"source": source, "wf_id": wf_id})


# ── ORI AI Assist ──────────────────────────────────────────────────────────────
_ORI_SYNTAX_KNOWLEDGE = """
# ORI Workflow DSL — Syntax Reference

## Structure
```
workflow "Name" {
  description: "..."
  agent: @agent-id        # optional
  sendToCanvas: true      # optional
  var topic               # runtime variable (prompted before run)
  var limit = "10"        # with default
  step[label]: type "value"
  step: type "value"
  if "condition" { step: ... } else { step: ... }
  parallel { step: ... \n  step: ... }
  run @workflow-id
  output → canvas
}
```

## Step types
prompt, web, summarize, transform, extract, template, code, notify, search, rag, ingest, fetch, run

## Built-in variables
{{output}} {{input}} {{date}} {{time}} {{datetime}} {{workflow_name}} {{doc_text}} {{doc_filename}} {{step_LABEL_output}}

## User variables
Declared with `var name` or `var name = "default"`, referenced as `{{name}}`.
Runtime variables are prompted before each run.

## Conditionals
`if "condition string" { ... } else { ... }` — condition evaluated as true/false by AI against previous output.

## Parallel
`parallel { step: ... \n  step: ... }` — steps run simultaneously, outputs concatenated.
"""


def _ori_ai_system() -> str:
    return (
        "You are an expert ORI workflow developer for the ORI Studio sovereign AI platform. "
        "You write precise, idiomatic .ori workflow files.\n\n"
        + _ORI_SYNTAX_KNOWLEDGE
        + "\nOutput rules:\n"
        "- generate/edit/fix modes: output ONLY .ori source code — no markdown fences, no explanations\n"
        "- NEVER output Go code, Python code, or any programming language — ONLY the ORI DSL shown above\n"
        "- NEVER output HTML tags, CSS class names, or any markup\n"
        "- explain mode: be concise and technical\n"
        "- Use meaningful step labels: step[research], step[brief], step[report]\n"
        "- Chain steps via {{output}} rather than repeating queries\n"
        "- When fixing diagnostics, address every listed error and warning\n"
        "- A valid workflow ALWAYS starts with: workflow \"Name\" {\n"
    )


@app.route("/ori/ai-assist", methods=["POST"])
def ori_ai_assist():
    data = request.get_json(silent=True) or {}
    mode        = data.get("mode", "generate")   # generate | edit | explain | fix
    instruction = data.get("instruction", "")
    source      = data.get("source", "")
    sel_text    = data.get("sel_text", "")
    diagnostics = data.get("diagnostics", [])    # [{level, message, line?}, ...]

    sys_msg = _ori_ai_system()

    def _fmt_diagnostics(diags):
        lines = []
        for i, d in enumerate(diags, 1):
            code  = 'E' if d.get('level') == 'error' else 'W' if d.get('level') == 'warning' else 'I'
            n     = str(i).zfill(3)
            loc   = f" (line {d['line']})" if d.get('line') else ""
            lines.append(f"  {code}[{n}]{loc}: {d.get('message', '')}")
        return "\n".join(lines)

    if mode == "generate":
        diag_ctx = ""
        if diagnostics:
            diag_ctx = f"\n\nCompiler diagnostics to be aware of:\n{_fmt_diagnostics(diagnostics)}\n"
        user_msg = (
            f"Build a complete .ori workflow file for this request:\n\n{instruction}{diag_ctx}\n\n"
            "Output only valid .ori source code."
        )
    elif mode == "edit":
        ctx = f"\nFull workflow context:\n{source}\n" if source else ""
        diag_ctx = f"\nCurrent diagnostics:\n{_fmt_diagnostics(diagnostics)}\n" if diagnostics else ""
        user_msg = (
            f"{ctx}{diag_ctx}\nEdit this selected section:\n{sel_text}\n\n"
            f"Instruction: {instruction}\n\n"
            "Output ONLY the replacement .ori code for the selected section."
        )
    elif mode == "explain":
        code = sel_text or source
        user_msg = f"Explain this .ori workflow code concisely and technically:\n{code}"
    elif mode == "fix":
        diag_text = _fmt_diagnostics(diagnostics) if diagnostics else "  (no specific diagnostics provided)"
        extra = f"\n\nAdditional instruction: {instruction}" if instruction.strip() else ""
        user_msg = (
            f"This .ori workflow has compiler diagnostics that must ALL be fixed:\n\n"
            f"{diag_text}\n\n"
            f"Current source code:\n{source}{extra}\n\n"
            "Fix every diagnostic. Output ONLY the corrected .ori source code."
        )
    else:
        return jsonify({"error": "unknown mode"}), 400

    def _stream():
        """Stream tokens directly from backbone → avoids 524 (no silent wait)."""
        import json as _json
        payload = {
            "model": "oricli-cognitive",
            "stream": True,
            "max_tokens": 2500,
            "messages": [
                {"role": "system", "content": sys_msg},
                {"role": "user",   "content": user_msg},
            ],
        }
        # Immediate keepalive so Cloudflare sees bytes before it times out
        yield ": keepalive\n\n"
        try:
            with _client().stream(
                "POST",
                f"{API_BASE}/v1/chat/completions",
                json=payload,
                headers=_build_headers(extra={"X-Code-Context": "true"}),
            ) as resp:
                resp.raise_for_status()
                fence_buf = ""       # accumulate to detect/strip opening fence
                fence_stripped = False
                open_fence_re = __import__('re').compile(r'^```\w*\n')
                for raw_line in resp.iter_lines():
                    if not raw_line.startswith("data:"):
                        continue
                    data = raw_line[5:].strip()
                    if data == "[DONE]":
                        break
                    try:
                        delta = _json.loads(data)["choices"][0]["delta"].get("content", "")
                    except Exception:
                        continue
                    if not delta:
                        continue
                    # Strip leading ``` fence once we have enough to detect it
                    if not fence_stripped:
                        fence_buf += delta
                        if len(fence_buf) >= 12 or '\n' in fence_buf:
                            fence_stripped = True
                            fence_buf = open_fence_re.sub("", fence_buf, count=1)
                            if fence_buf:
                                yield f"data: {_json.dumps({'text': fence_buf})}\n\n"
                        # else keep buffering
                        continue
                    yield f"data: {_json.dumps({'text': delta})}\n\n"
        except Exception as exc:
            yield f"data: {_json.dumps({'error': str(exc)})}\n\n"
        yield "data: [DONE]\n\n"

    return Response(
        _stream(),
        mimetype="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )


_INDEX_STATUS_FILE = Path(__file__).parent / ".oricli" / "index_status.json"
_INDEX_LOCK = threading.Lock()
_BACKBONE_URL = os.getenv("MAVAIA_BACKBONE_URL", "http://localhost:8089")
_BACKBONE_KEY = os.getenv("MAVAIA_API_KEY", "glm.8eHruhzb.IPtP2toLOSKATWc5f_KXrRQOO6JcvFBB")

# ── Local RAG store ────────────────────────────────────────────────────────────
_LOCAL_RAG_PATH = Path(__file__).parent / ".oricli" / "rag_docs.json"
_RAG_LOCK = threading.Lock()


def _rag_load() -> dict:
    """Load local RAG store — dict keyed by source id."""
    if _LOCAL_RAG_PATH.exists():
        try:
            return json.loads(_LOCAL_RAG_PATH.read_text())
        except Exception:
            pass
    return {}


def _rag_save(store: dict) -> None:
    _LOCAL_RAG_PATH.write_text(json.dumps(store, ensure_ascii=False))


def _rag_ingest(docs: list[dict], source_prefix: str) -> int:
    """Store docs in local RAG store. Returns count of new/updated docs."""
    with _RAG_LOCK:
        store = _rag_load()
        count = 0
        for doc in docs:
            key = doc.get("source") or f"{source_prefix}:{count}"
            store[key] = {
                "title":       doc.get("title", ""),
                "content":     doc.get("content", ""),
                "source":      key,
                "source_type": source_prefix,
                "metadata":    doc.get("metadata", {}),
                "indexed_at":  datetime.now(timezone.utc).isoformat(),
            }
            count += 1
        _rag_save(store)
    _bm25_rag.invalidate()  # mark index dirty after write
    return count


# ── BM25 RAG index ─────────────────────────────────────────────────────────────
# Okapi BM25 — same parameters as pkg/memory/bm25.go (k1=1.2, b=0.75).
# Replaces the naive token-count scorer. LLM is never involved in retrieval.

class _BM25Rag:
    """In-memory BM25 index over the local JSON RAG store.

    The index is rebuilt lazily whenever the backing store file changes
    (checked via mtime). Thread-safe via the shared _RAG_LOCK for reads
    and a dedicated lock for index mutation.
    """
    K1 = 1.2
    B  = 0.75

    def __init__(self) -> None:
        self._lock = threading.Lock()
        self._index: dict[str, dict] = {}   # docid → {tf, length, doc}
        self._df:    dict[str, int]  = {}   # term  → doc count
        self._avg_len: float = 0.0
        self._mtime: float = 0.0
        self._dirty: bool = True

    def invalidate(self) -> None:
        """Mark index as dirty so the next search triggers a rebuild."""
        with self._lock:
            self._dirty = True

    @staticmethod
    def _tokenize(text: str) -> list[str]:
        return [t for t in re.findall(r"[a-z0-9]+", text.lower()) if len(t) >= 2]

    def _needs_rebuild(self) -> bool:
        if self._dirty:
            return True
        try:
            return _LOCAL_RAG_PATH.stat().st_mtime != self._mtime
        except OSError:
            return True

    def _rebuild(self, store: dict) -> None:
        index: dict[str, dict] = {}
        df: dict[str, int]     = {}
        total_len = 0
        for key, doc in store.items():
            text   = f"{doc.get('title', '')} {doc.get('content', '')}".strip()
            tokens = self._tokenize(text)
            tf: dict[str, int] = {}
            for t in tokens:
                tf[t] = tf.get(t, 0) + 1
            index[key] = {"tf": tf, "length": len(tokens), "doc": doc}
            total_len += len(tokens)
            for term in tf:
                df[term] = df.get(term, 0) + 1
        self._index   = index
        self._df      = df
        self._avg_len = total_len / max(len(index), 1)
        self._dirty   = False
        try:
            self._mtime = _LOCAL_RAG_PATH.stat().st_mtime
        except OSError:
            self._mtime = 0.0

    def search(self, query: str, limit: int = 5, source_type: str | None = None) -> list[dict]:
        with _RAG_LOCK:
            store = _rag_load()
        if not store:
            return []

        with self._lock:
            if self._needs_rebuild():
                self._rebuild(store)

            q_terms = list(set(self._tokenize(query)))
            if not q_terms:
                return []

            N = len(self._index)
            scores: dict[str, float] = {}
            for term in q_terms:
                df = self._df.get(term, 0)
                if df == 0:
                    continue
                idf = math.log(1.0 + ((N - df + 0.5) / (df + 0.5)))
                for docid, entry in self._index.items():
                    if source_type and entry["doc"].get("source_type") != source_type:
                        continue
                    tf = entry["tf"].get(term, 0)
                    if tf == 0:
                        continue
                    dl    = max(entry["length"], 1)
                    avgdl = max(self._avg_len, 1.0)
                    score = idf * (tf * (self.K1 + 1)) / (
                        tf + self.K1 * (1.0 - self.B + self.B * dl / avgdl)
                    )
                    scores[docid] = scores.get(docid, 0.0) + score

            if not scores:
                return []

            top = sorted(scores.items(), key=lambda x: x[1], reverse=True)[:limit]
            results = []
            for docid, score in top:
                doc     = self._index[docid]["doc"]
                snippet = doc.get("content", "")[:400].strip()
                results.append({
                    "source":   doc["source"],
                    "title":    doc.get("title", ""),
                    "snippet":  snippet,
                    "score":    round(score, 4),
                    "metadata": doc.get("metadata", {}),
                })
            return results


_bm25_rag = _BM25Rag()


def _rag_search(query: str, limit: int = 5, source_type: str | None = None) -> list[dict]:
    """BM25 search over local RAG store (Okapi BM25, k1=1.2, b=0.75)."""
    return _bm25_rag.search(query, limit=limit, source_type=source_type)


def _load_index_status() -> dict:
    if _INDEX_STATUS_FILE.exists():
        try:
            return json.loads(_INDEX_STATUS_FILE.read_text())
        except Exception:
            pass
    return {}


def _save_index_status(data: dict) -> None:
    _INDEX_STATUS_FILE.write_text(json.dumps(data, indent=2))


def _ingest_doc(text: str, source: str, metadata: dict) -> bool:
    """POST a single document to the Go backbone /v1/ingest endpoint. Returns True on success."""
    import httpx as _hx
    payload = {"text": text, "source": source, "metadata": metadata}
    try:
        r = _hx.post(
            f"{_BACKBONE_URL}/v1/ingest",
            json=payload,
            headers={"Authorization": f"Bearer {_BACKBONE_KEY}"},
            timeout=30.0,
        )
        return r.status_code < 400
    except Exception:
        return False


def _ingest_batch(docs: list[dict], source_prefix: str) -> int:
    """Ingest docs into backbone; fall back to local RAG store on failure."""
    # Try backbone first; if it fails or returns 0, use local store
    backbone_count = 0
    backbone_ok = True
    for doc in docs:
        text = f"# {doc.get('title', '')}\n\n{doc.get('content', '')}".strip()
        if not text or len(text) < 20:
            continue
        meta = {"title": doc.get("title", ""), "source_type": source_prefix, **doc.get("metadata", {})}
        if _ingest_doc(text, doc.get("source", source_prefix), meta):
            backbone_count += 1
        else:
            backbone_ok = False

    if backbone_count > 0:
        return backbone_count

    # Backbone unavailable — store locally
    log.info("[RAG] Backbone ingest unavailable, writing %d docs to local store", len(docs))
    return _rag_ingest(docs, source_prefix)


# ── Per-service fetchers ───────────────────────────────────────────────────────

def _fetch_notion(creds: dict, opts: dict) -> list[dict]:
    import httpx as _hx
    token = creds.get("api_key", "")
    if not token:
        raise ValueError("Notion API key required")
    db_id = opts.get("query") or creds.get("database_id", "")
    headers = {"Authorization": f"Bearer {token}", "Notion-Version": "2022-06-28", "Content-Type": "application/json"}
    docs = []
    if db_id:
        # Query a database
        url = f"https://api.notion.com/v1/databases/{db_id}/query"
        body: dict = {"page_size": min(int(opts.get("max_results", 50)), 100)}
        r = _hx.post(url, headers=headers, json=body, timeout=15)
        r.raise_for_status()
        for page in r.json().get("results", []):
            pid = page["id"]
            title_parts = []
            for prop in page.get("properties", {}).values():
                if prop.get("type") == "title":
                    title_parts = [t["plain_text"] for t in prop.get("title", [])]
                    break
            title = " ".join(title_parts) or pid
            # Fetch page blocks for content
            blocks_r = _hx.get(f"https://api.notion.com/v1/blocks/{pid}/children", headers=headers, timeout=15)
            content_parts = []
            if blocks_r.status_code == 200:
                for blk in blocks_r.json().get("results", []):
                    rt = blk.get(blk.get("type", ""), {}).get("rich_text", [])
                    content_parts.append(" ".join(t.get("plain_text", "") for t in rt))
            docs.append({"title": title, "content": "\n".join(content_parts), "source": f"notion:{pid}", "metadata": {"url": f"https://notion.so/{pid.replace('-', '')}"}})
    else:
        # Search all pages
        r = _hx.post("https://api.notion.com/v1/search", headers=headers, json={"page_size": min(int(opts.get("max_results", 30)), 100)}, timeout=15)
        r.raise_for_status()
        for obj in r.json().get("results", []):
            pid = obj["id"]
            title = ""
            if obj.get("object") == "page":
                for prop in obj.get("properties", {}).values():
                    if prop.get("type") == "title":
                        title = " ".join(t["plain_text"] for t in prop.get("title", []))
                        break
            elif obj.get("object") == "database":
                title_list = obj.get("title", [])
                title = " ".join(t.get("plain_text", "") for t in title_list)
            docs.append({"title": title or pid, "content": f"Notion object: {obj.get('object')} — {title}", "source": f"notion:{pid}", "metadata": {}})
    return docs


def _fetch_github(creds: dict, opts: dict) -> list[dict]:
    import httpx as _hx
    token = creds.get("personal_access_token", "") or creds.get("api_key", "")
    repo = opts.get("query") or creds.get("default_owner", "")
    headers = {"Accept": "application/vnd.github+json", "X-GitHub-Api-Version": "2022-11-28"}
    if token:
        headers["Authorization"] = f"Bearer {token}"
    docs = []
    max_r = int(opts.get("max_results", 30))
    if "/" in str(repo):
        # Repo issues
        r = _hx.get(f"https://api.github.com/repos/{repo}/issues", headers=headers, params={"state": "all", "per_page": min(max_r, 100)}, timeout=15)
        r.raise_for_status()
        for issue in r.json():
            docs.append({
                "title": f"#{issue['number']}: {issue['title']}",
                "content": issue.get("body") or "",
                "source": f"github:{repo}:issue:{issue['number']}",
                "metadata": {"url": issue["html_url"], "state": issue["state"]},
            })
        # README
        readme_r = _hx.get(f"https://api.github.com/repos/{repo}/readme", headers=headers, timeout=15)
        if readme_r.status_code == 200:
            import base64
            content = base64.b64decode(readme_r.json()["content"]).decode("utf-8", errors="replace")
            docs.append({"title": f"{repo} README", "content": content, "source": f"github:{repo}:readme", "metadata": {}})
    else:
        # Search public repos for user/org
        r = _hx.get(f"https://api.github.com/users/{repo}/repos", headers=headers, params={"per_page": min(max_r, 100), "sort": "updated"}, timeout=15)
        if r.status_code == 200:
            for rep in r.json()[:max_r]:
                docs.append({
                    "title": rep["full_name"],
                    "content": rep.get("description") or "",
                    "source": f"github:{rep['full_name']}",
                    "metadata": {"url": rep["html_url"], "language": rep.get("language", "")},
                })
    return docs


def _fetch_gitlab(creds: dict, opts: dict) -> list[dict]:
    import httpx as _hx
    token = creds.get("personal_access_token", "")
    host = creds.get("host", "https://gitlab.com").rstrip("/")
    query = opts.get("query", "")
    headers = {"PRIVATE-TOKEN": token} if token else {}
    docs = []
    max_r = int(opts.get("max_results", 30))
    if query:
        r = _hx.get(f"{host}/api/v4/projects/{query.replace('/', '%2F')}/issues",
                    headers=headers, params={"per_page": min(max_r, 100)}, timeout=15)
        if r.status_code == 200:
            for issue in r.json():
                docs.append({"title": f"#{issue['iid']}: {issue['title']}", "content": issue.get("description") or "",
                              "source": f"gitlab:{query}:issue:{issue['iid']}", "metadata": {"url": issue.get("web_url", "")}})
    return docs


def _fetch_jira(creds: dict, opts: dict) -> list[dict]:
    import httpx as _hx
    import base64
    domain = creds.get("domain", "")
    email = creds.get("email", "")
    token = creds.get("api_token", "")
    if not all([domain, email, token]):
        raise ValueError("Jira domain, email and API token required")
    auth = base64.b64encode(f"{email}:{token}".encode()).decode()
    headers = {"Authorization": f"Basic {auth}", "Content-Type": "application/json"}
    jql = opts.get("query") or "ORDER BY updated DESC"
    max_r = int(opts.get("max_results", 30))
    r = _hx.get(f"https://{domain}/rest/api/3/search",
                headers=headers, params={"jql": jql, "maxResults": min(max_r, 100), "fields": "summary,description,status"}, timeout=15)
    r.raise_for_status()
    docs = []
    for issue in r.json().get("issues", []):
        f = issue.get("fields", {})
        desc = f.get("description") or {}
        text = ""
        if isinstance(desc, dict):
            for block in desc.get("content", []):
                for child in block.get("content", []):
                    text += child.get("text", "") + " "
        docs.append({"title": f"{issue['key']}: {f.get('summary', '')}", "content": text.strip(),
                     "source": f"jira:{issue['key']}", "metadata": {"status": f.get("status", {}).get("name", "")}})
    return docs


def _fetch_linear(creds: dict, opts: dict) -> list[dict]:
    import httpx as _hx
    token = creds.get("api_key", "")
    if not token:
        raise ValueError("Linear API key required")
    query_str = opts.get("query", "")
    max_r = int(opts.get("max_results", 30))
    gql = """
    query($first: Int, $filter: IssueFilter) {
      issues(first: $first, filter: $filter, orderBy: updatedAt) {
        nodes { id title description state { name } url }
      }
    }
    """
    variables: dict = {"first": min(max_r, 100)}
    if query_str:
        variables["filter"] = {"title": {"containsIgnoreCase": query_str}}
    r = _hx.post("https://api.linear.app/graphql",
                 headers={"Authorization": token, "Content-Type": "application/json"},
                 json={"query": gql, "variables": variables}, timeout=15)
    r.raise_for_status()
    docs = []
    for issue in r.json().get("data", {}).get("issues", {}).get("nodes", []):
        docs.append({"title": issue["title"], "content": issue.get("description") or "",
                     "source": f"linear:{issue['id']}", "metadata": {"url": issue.get("url", ""), "state": issue.get("state", {}).get("name", "")}})
    return docs


def _fetch_asana(creds: dict, opts: dict) -> list[dict]:
    import httpx as _hx
    token = creds.get("personal_access_token", "")
    if not token:
        raise ValueError("Asana personal access token required")
    workspace = creds.get("workspace_gid", "")
    headers = {"Authorization": f"Bearer {token}"}
    max_r = int(opts.get("max_results", 30))
    params: dict = {"limit": min(max_r, 100), "opt_fields": "name,notes,completed,due_on"}
    if workspace:
        params["workspace"] = workspace
    r = _hx.get("https://app.asana.com/api/1.0/tasks", headers=headers, params=params, timeout=15)
    r.raise_for_status()
    docs = []
    for task in r.json().get("data", []):
        docs.append({"title": task["name"], "content": task.get("notes") or "",
                     "source": f"asana:{task['gid']}", "metadata": {"completed": str(task.get("completed", False))}})
    return docs


def _fetch_todoist(creds: dict, opts: dict) -> list[dict]:
    import httpx as _hx
    token = creds.get("api_token", "")
    if not token:
        raise ValueError("Todoist API token required")
    max_r = int(opts.get("max_results", 50))
    params: dict = {}
    if opts.get("query"):
        params["filter"] = opts["query"]
    # Todoist REST API v2 (/rest/v2/tasks) was removed (410 Gone).
    # New endpoint is /api/v1/tasks.
    r = _hx.get("https://api.todoist.com/api/v1/tasks",
                headers={"Authorization": f"Bearer {token}"}, params=params, timeout=15)
    r.raise_for_status()
    data = r.json()
    # API v1 returns {"results": [...], "next_cursor": "..."} — v2 returned a plain list
    tasks = data.get("results", data) if isinstance(data, dict) else data
    docs = []
    for task in tasks[:max_r]:
        due = task.get("due") or {}
        due_str = due.get("string") or due.get("date") or ""
        docs.append({"title": task.get("content", ""), "content": task.get("description") or "",
                     "source": f"todoist:{task['id']}", "metadata": {"priority": str(task.get("priority", 1)), "due": due_str}})
    return docs


def _fetch_trello(creds: dict, opts: dict) -> list[dict]:
    import httpx as _hx
    api_key = creds.get("api_key", "")
    token = creds.get("token", "")
    board_id = opts.get("query") or creds.get("board_id", "")
    if not all([api_key, token, board_id]):
        raise ValueError("Trello API key, token and board ID required")
    params = {"key": api_key, "token": token}
    r = _hx.get(f"https://api.trello.com/1/boards/{board_id}/cards", params={**params, "fields": "name,desc,url"}, timeout=15)
    r.raise_for_status()
    docs = []
    for card in r.json()[:int(opts.get("max_results", 50))]:
        docs.append({"title": card["name"], "content": card.get("desc") or "",
                     "source": f"trello:{card['id']}", "metadata": {"url": card.get("url", "")}})
    return docs


def _fetch_airtable(creds: dict, opts: dict) -> list[dict]:
    import httpx as _hx
    token = creds.get("api_key", "")
    base_id = opts.get("query") or creds.get("base_id", "")
    if not all([token, base_id]):
        raise ValueError("Airtable token and base ID required")
    headers = {"Authorization": f"Bearer {token}"}
    # List tables first
    meta_r = _hx.get(f"https://api.airtable.com/v0/meta/bases/{base_id}/tables", headers=headers, timeout=15)
    meta_r.raise_for_status()
    tables = meta_r.json().get("tables", [])
    docs = []
    max_r = int(opts.get("max_results", 50))
    for table in tables[:3]:
        r = _hx.get(f"https://api.airtable.com/v0/{base_id}/{table['id']}", headers=headers, params={"maxRecords": max_r}, timeout=15)
        if r.status_code != 200:
            continue
        for record in r.json().get("records", []):
            fields = record.get("fields", {})
            title = next(iter(fields.values()), record["id"])
            content = " | ".join(f"{k}: {v}" for k, v in fields.items() if isinstance(v, str))
            docs.append({"title": str(title), "content": content, "source": f"airtable:{record['id']}", "metadata": {"table": table["name"]}})
    return docs


def _fetch_discord(creds: dict, opts: dict) -> list[dict]:
    import httpx as _hx
    token = creds.get("bot_token", "")
    if not token:
        raise ValueError("Discord bot token required")
    channel_id = opts.get("query") or ""
    headers = {"Authorization": f"Bot {token}"}
    docs = []
    max_r = int(opts.get("max_results", 50))
    if channel_id:
        r = _hx.get(f"https://discord.com/api/v10/channels/{channel_id}/messages",
                    headers=headers, params={"limit": min(max_r, 100)}, timeout=15)
        r.raise_for_status()
        for msg in r.json():
            if msg.get("content"):
                docs.append({"title": f"@{msg['author']['username']} at {msg['timestamp'][:10]}",
                             "content": msg["content"], "source": f"discord:{channel_id}:{msg['id']}", "metadata": {"channel": channel_id}})
    else:
        guild_id = creds.get("guild_id", "")
        if guild_id:
            ch_r = _hx.get(f"https://discord.com/api/v10/guilds/{guild_id}/channels", headers=headers, timeout=15)
            ch_r.raise_for_status()
            for ch in ch_r.json()[:5]:
                if ch.get("type") == 0:
                    msg_r = _hx.get(f"https://discord.com/api/v10/channels/{ch['id']}/messages",
                                    headers=headers, params={"limit": 20}, timeout=15)
                    if msg_r.status_code == 200:
                        for msg in msg_r.json():
                            if msg.get("content"):
                                docs.append({"title": f"#{ch['name']} — @{msg['author']['username']}",
                                             "content": msg["content"], "source": f"discord:{ch['id']}:{msg['id']}", "metadata": {"channel": ch["name"]}})
    return docs


def _fetch_telegram(creds: dict, opts: dict) -> list[dict]:
    """Telegram uses push-based webhook ingestion. Return what's already in the local RAG store."""
    # Messages arrive via POST /connections/telegram/webhook and are stored locally.
    # No polling needed — just surface what we've already accumulated.
    hits = _rag_search("", limit=200, source_type="telegram")
    return [{"title": h["title"], "content": h["snippet"], "source": h["source"], "metadata": h["metadata"]} for h in hits]


def _telegram_register_webhook(token: str) -> tuple[bool, str]:
    """Register our Flask endpoint as the Telegram webhook for this bot."""
    import httpx as _hx
    import hashlib
    # Derive a stable secret from the token (Telegram passes it back in X-Telegram-Bot-Api-Secret-Token)
    secret = hashlib.sha256(token.encode()).hexdigest()[:32]
    webhook_url = f"https://sovereignclaw.thynaptic.com/connections/telegram/webhook"
    try:
        r = _hx.post(
            f"https://api.telegram.org/bot{token}/setWebhook",
            json={"url": webhook_url, "secret_token": secret, "allowed_updates": ["message", "channel_post"]},
            timeout=10,
        )
        data = r.json()
        if data.get("ok"):
            return True, f"Webhook registered → {webhook_url}"
        return False, data.get("description", "Unknown error")
    except Exception as exc:
        return False, str(exc)


def _fetch_slack(creds: dict, opts: dict) -> list[dict]:
    import httpx as _hx
    token = creds.get("bot_token", "")
    if not token:
        raise ValueError("Slack bot token required")
    query = opts.get("query", "")
    max_r = int(opts.get("max_results", 30))
    headers = {"Authorization": f"Bearer {token}"}
    docs = []
    if query:
        r = _hx.get("https://slack.com/api/search.messages", headers=headers, params={"query": query, "count": min(max_r, 100)}, timeout=15)
        r.raise_for_status()
        for match in r.json().get("messages", {}).get("matches", []):
            docs.append({"title": f"#{match.get('channel', {}).get('name', 'unknown')} — Slack",
                         "content": match.get("text", ""), "source": f"slack:{match.get('ts', '')}", "metadata": {}})
    else:
        # List recent messages from default channel
        channel = creds.get("default_channel", "general").lstrip("#")
        ch_r = _hx.get("https://slack.com/api/conversations.list", headers=headers, params={"limit": 200}, timeout=15)
        ch_id = ""
        if ch_r.status_code == 200:
            for ch in ch_r.json().get("channels", []):
                if ch.get("name") == channel:
                    ch_id = ch["id"]
                    break
        if ch_id:
            hist_r = _hx.get("https://slack.com/api/conversations.history",
                              headers=headers, params={"channel": ch_id, "limit": max_r}, timeout=15)
            if hist_r.status_code == 200:
                for msg in hist_r.json().get("messages", []):
                    if msg.get("text"):
                        docs.append({"title": f"#{channel} — Slack", "content": msg["text"],
                                     "source": f"slack:{ch_id}:{msg['ts']}", "metadata": {"channel": channel}})
    return docs


def _fetch_hubspot(creds: dict, opts: dict) -> list[dict]:
    import httpx as _hx
    token = creds.get("access_token", "")
    if not token:
        raise ValueError("HubSpot access token required")
    headers = {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}
    max_r = int(opts.get("max_results", 30))
    entity = opts.get("query", "contacts")
    r = _hx.get(f"https://api.hubapi.com/crm/v3/objects/{entity}",
                headers=headers, params={"limit": min(max_r, 100), "properties": "firstname,lastname,email,name,title,description"}, timeout=15)
    r.raise_for_status()
    docs = []
    for obj in r.json().get("results", []):
        props = obj.get("properties", {})
        name = " ".join(filter(None, [props.get("firstname", ""), props.get("lastname", ""), props.get("name", "")])) or obj["id"]
        content = " | ".join(f"{k}: {v}" for k, v in props.items() if v and k not in ("hs_object_id", "createdate", "lastmodifieddate"))
        docs.append({"title": name.strip(), "content": content, "source": f"hubspot:{obj['id']}", "metadata": {"entity": entity}})
    return docs


def _fetch_supabase(creds: dict, opts: dict) -> list[dict]:
    import httpx as _hx
    url = creds.get("url", "").rstrip("/")
    key = creds.get("service_role_key") or creds.get("anon_key", "")
    table = opts.get("query", "")
    if not all([url, key, table]):
        raise ValueError("Supabase URL, key, and table name (in query field) required")
    max_r = int(opts.get("max_results", 50))
    r = _hx.get(f"{url}/rest/v1/{table}",
                headers={"apikey": key, "Authorization": f"Bearer {key}", "Range": f"0-{max_r - 1}"}, timeout=15)
    r.raise_for_status()
    docs = []
    for row in r.json():
        title = row.get("title") or row.get("name") or row.get("id") or "record"
        content = " | ".join(f"{k}: {v}" for k, v in row.items() if isinstance(v, (str, int, float)) and v)
        docs.append({"title": str(title), "content": content, "source": f"supabase:{table}:{row.get('id', '')}", "metadata": {"table": table}})
    return docs


def _fetch_salesforce(creds: dict, opts: dict) -> list[dict]:
    import httpx as _hx
    instance_url = creds.get("instance_url", "").rstrip("/")
    token = creds.get("access_token", "")
    if not all([instance_url, token]):
        raise ValueError("Salesforce instance URL and access token required")
    soql = opts.get("query") or "SELECT Id, Name, Description FROM Account LIMIT 30"
    r = _hx.get(f"{instance_url}/services/data/v59.0/query",
                headers={"Authorization": f"Bearer {token}"}, params={"q": soql}, timeout=15)
    r.raise_for_status()
    docs = []
    for rec in r.json().get("records", []):
        name = rec.get("Name", rec.get("Id", "record"))
        content = " | ".join(f"{k}: {v}" for k, v in rec.items() if isinstance(v, (str, int, float)) and k != "attributes")
        docs.append({"title": name, "content": content, "source": f"salesforce:{rec.get('Id', '')}", "metadata": {}})
    return docs


# ── Research fetchers (mostly free) ──────────────────────────────────────────

def _fetch_arxiv(creds: dict, opts: dict) -> list[dict]:
    import httpx as _hx
    import xml.etree.ElementTree as ET

    # Parse comma-separated categories into proper arXiv cat: query
    # e.g. "cs.AI, cs.LG, stat.ML" → "cat:cs.AI OR cat:cs.LG OR cat:stat.ML"
    raw_cats = opts.get("query") or creds.get("default_categories", "cs.AI")
    cats = [c.strip() for c in raw_cats.replace(";", ",").split(",") if c.strip()]
    if not cats:
        cats = ["cs.AI"]

    # Build category filter — arXiv API uses cat: prefix for subject classification
    cat_query = " OR ".join(f"cat:{c}" for c in cats)

    # Optional date filter: only fetch papers submitted in the last N days
    days_back = int(creds.get("days_back") or 7)
    max_r = int(opts.get("max_results") or creds.get("max_results") or 50)

    # arXiv API doesn't support submittedDate range filter combined with OR category queries.
    # Instead: fetch latest N papers sorted by submittedDate and filter client-side by date.
    search_query = cat_query

    r = _hx.get("https://export.arxiv.org/api/query", params={
        "search_query": search_query,
        "max_results":  max_r,
        "sortBy":       "submittedDate",
        "sortOrder":    "descending",
    }, timeout=30)
    r.raise_for_status()

    cutoff_dt = datetime.now(timezone.utc) - timedelta(days=days_back)

    ns = "http://www.w3.org/2005/Atom"
    root = ET.fromstring(r.text)
    docs = []
    for entry in root.findall(f"{{{ns}}}entry"):
        def _text(tag: str) -> str:
            el = entry.find(f"{{{ns}}}{tag}")
            return (el.text or "").strip() if el is not None else ""

        title     = _text("title")
        summary   = _text("summary")
        arxiv_id  = _text("id")
        published = _text("published")
        link      = next((l.get("href", "") for l in entry.findall(f"{{{ns}}}link") if l.get("title") == "pdf"), "")
        paper_cats = [c.get("term", "") for c in entry.findall(f"{{{ns}}}category")]
        authors    = []
        for a in entry.findall(f"{{{ns}}}author"):
            name_el = a.find(f"{{{ns}}}name")
            if name_el is not None and name_el.text:
                authors.append(name_el.text)

        # Client-side date filter — skip papers older than days_back
        if days_back > 0 and published:
            try:
                pub_dt = datetime.fromisoformat(published.replace("Z", "+00:00"))
                if pub_dt < cutoff_dt:
                    continue
            except Exception:
                pass

        content = f"Authors: {', '.join(authors[:5])}\nPublished: {published[:10]}\nCategories: {', '.join(paper_cats)}\n\n{summary}"
        docs.append({
            "title":    title,
            "content":  content[:3000],
            "source":   f"arxiv:{arxiv_id.split('/')[-1]}",
            "metadata": {"url": link or arxiv_id, "categories": paper_cats, "published": published[:10]},
        })
    return docs


def _fetch_pubmed(creds: dict, opts: dict) -> list[dict]:
    import httpx as _hx
    query = opts.get("query", "")
    if not query:
        raise ValueError("Search query required for PubMed")
    api_key = creds.get("api_key", "")
    max_r = int(opts.get("max_results", 10))
    params: dict = {"db": "pubmed", "term": query, "retmax": max_r, "retmode": "json"}
    if api_key:
        params["api_key"] = api_key
    search_r = _hx.get("https://eutils.ncbi.nlm.nih.gov/entrez/eutils/esearch.fcgi", params=params, timeout=20)
    search_r.raise_for_status()
    ids = search_r.json().get("esearchresult", {}).get("idlist", [])
    if not ids:
        return []
    fetch_params: dict = {"db": "pubmed", "id": ",".join(ids), "retmode": "xml", "rettype": "abstract"}
    if api_key:
        fetch_params["api_key"] = api_key
    fetch_r = _hx.get("https://eutils.ncbi.nlm.nih.gov/entrez/eutils/efetch.fcgi", params=fetch_params, timeout=20)
    import xml.etree.ElementTree as ET
    root = ET.fromstring(fetch_r.text)
    docs = []
    for article in root.iter("PubmedArticle"):
        pmid_el = article.find(".//PMID")
        title_el = article.find(".//ArticleTitle")
        abstract_el = article.find(".//AbstractText")
        pmid = pmid_el.text if pmid_el is not None else ""
        title = title_el.text if title_el is not None else ""
        abstract = abstract_el.text if abstract_el is not None else ""
        docs.append({"title": title, "content": abstract, "source": f"pubmed:{pmid}",
                     "metadata": {"url": f"https://pubmed.ncbi.nlm.nih.gov/{pmid}/"}})
    return docs


def _fetch_semantic_scholar(creds: dict, opts: dict) -> list[dict]:
    import httpx as _hx
    query = opts.get("query", "")
    if not query:
        raise ValueError("Search query required for Semantic Scholar")
    api_key = creds.get("api_key", "")
    max_r = int(opts.get("max_results", 10))
    headers = {}
    if api_key:
        headers["x-api-key"] = api_key
    r = _hx.get("https://api.semanticscholar.org/graph/v1/paper/search",
                headers=headers, params={"query": query, "limit": min(max_r, 100), "fields": "title,abstract,url,year,authors"}, timeout=20)
    r.raise_for_status()
    docs = []
    for paper in r.json().get("data", []):
        authors = ", ".join(a.get("name", "") for a in paper.get("authors", [])[:3])
        content = paper.get("abstract") or ""
        if authors:
            content = f"Authors: {authors}\n\n{content}"
        docs.append({"title": paper.get("title", ""), "content": content,
                     "source": f"s2:{paper.get('paperId', '')}", "metadata": {"url": paper.get("url", ""), "year": str(paper.get("year", ""))}})
    return docs


def _fetch_wikipedia(creds: dict, opts: dict) -> list[dict]:
    import httpx as _hx
    query = opts.get("query", "")
    if not query:
        raise ValueError("Search query required for Wikipedia")
    lang = creds.get("default_language", "en")
    max_r = int(opts.get("max_results", 5))
    base = f"https://{lang}.wikipedia.org/w/api.php"
    search_r = _hx.get(base, params={"action": "query", "list": "search", "srsearch": query, "srlimit": max_r, "format": "json"}, timeout=15)
    search_r.raise_for_status()
    docs = []
    for result in search_r.json().get("query", {}).get("search", []):
        page_r = _hx.get(base, params={"action": "query", "titles": result["title"], "prop": "extracts", "exintro": True, "format": "json"}, timeout=15)
        if page_r.status_code == 200:
            pages = page_r.json().get("query", {}).get("pages", {})
            for page in pages.values():
                import html
                extract = html.unescape(re.sub(r"<[^>]+>", "", page.get("extract", "")))
                docs.append({"title": page.get("title", result["title"]), "content": extract,
                             "source": f"wikipedia:{result['title'].replace(' ', '_')}",
                             "metadata": {"url": f"https://{lang}.wikipedia.org/wiki/{result['title'].replace(' ', '_')}"}})
    return docs


def _fetch_newsapi(creds: dict, opts: dict) -> list[dict]:
    import httpx as _hx
    api_key = creds.get("api_key", "")
    if not api_key:
        raise ValueError("NewsAPI key required")
    query = opts.get("query", "")
    if not query:
        raise ValueError("Search query required for NewsAPI")
    lang = creds.get("default_language", "en")
    max_r = int(opts.get("max_results", 20))
    r = _hx.get("https://newsapi.org/v2/everything",
                params={"q": query, "language": lang, "pageSize": min(max_r, 100), "sortBy": "relevancy"},
                headers={"X-Api-Key": api_key}, timeout=15)
    r.raise_for_status()
    docs = []
    for article in r.json().get("articles", []):
        content = " ".join(filter(None, [article.get("description", ""), article.get("content", "")]))
        docs.append({"title": article.get("title", ""), "content": content,
                     "source": f"newsapi:{article.get('url', '')}",
                     "metadata": {"url": article.get("url", ""), "source": article.get("source", {}).get("name", "")}})
    return docs


def _fetch_reddit(creds: dict, opts: dict) -> list[dict]:
    import httpx as _hx
    client_id = creds.get("client_id", "")
    client_secret = creds.get("client_secret", "")
    user_agent = creds.get("user_agent", "SovereignClaw/1.0")
    if not all([client_id, client_secret]):
        raise ValueError("Reddit client_id and client_secret required")
    # Obtain app-only token
    token_r = _hx.post("https://www.reddit.com/api/v1/access_token",
                        auth=(client_id, client_secret), data={"grant_type": "client_credentials"},
                        headers={"User-Agent": user_agent}, timeout=15)
    token_r.raise_for_status()
    access_token = token_r.json().get("access_token", "")
    query = opts.get("query", "")
    max_r = int(opts.get("max_results", 20))
    headers = {"Authorization": f"Bearer {access_token}", "User-Agent": user_agent}
    endpoint = f"https://oauth.reddit.com/search" if query else "https://oauth.reddit.com/hot"
    params: dict = {"limit": min(max_r, 100)}
    if query:
        params["q"] = query
        params["type"] = "link"
    r = _hx.get(endpoint, headers=headers, params=params, timeout=15)
    r.raise_for_status()
    docs = []
    for post in r.json().get("data", {}).get("children", []):
        d = post.get("data", {})
        content = d.get("selftext") or d.get("url", "")
        docs.append({"title": d.get("title", ""), "content": content,
                     "source": f"reddit:{d.get('id', '')}", "metadata": {"subreddit": d.get("subreddit", ""), "score": str(d.get("score", 0))}})
    return docs


def _fetch_youtube(creds: dict, opts: dict) -> list[dict]:
    import httpx as _hx
    api_key = creds.get("api_key", "")
    if not api_key:
        raise ValueError("YouTube Data API key required")
    query = opts.get("query", "")
    if not query:
        raise ValueError("Search query required for YouTube")
    max_r = int(opts.get("max_results", 10))
    r = _hx.get("https://www.googleapis.com/youtube/v3/search",
                params={"part": "snippet", "q": query, "maxResults": min(max_r, 50), "type": "video", "key": api_key}, timeout=15)
    r.raise_for_status()
    docs = []
    for item in r.json().get("items", []):
        snip = item.get("snippet", {})
        vid_id = item.get("id", {}).get("videoId", "")
        docs.append({"title": snip.get("title", ""), "content": snip.get("description", ""),
                     "source": f"youtube:{vid_id}",
                     "metadata": {"url": f"https://youtube.com/watch?v={vid_id}", "channel": snip.get("channelTitle", "")}})
    return docs


def _fetch_github_api(creds: dict, opts: dict) -> list[dict]:
    return _fetch_github(creds, opts)


def _fetch_google_workspace(creds: dict, opts: dict) -> list[dict]:
    """Fetch content from Gmail, Drive, Docs, Calendar, Tasks, Sheets, Forms."""
    creds = _refresh_google_token(creds)
    at = creds["access_token"]
    hdrs = {"Authorization": f"Bearer {at}"}
    docs: list[dict] = []

    # ── Gmail: recent important/unread messages ───────────────────────────────
    try:
        r = httpx.get("https://gmail.googleapis.com/gmail/v1/users/me/messages",
                      params={"maxResults": 30, "q": "is:unread OR is:starred"},
                      headers=hdrs, timeout=20)
        if r.status_code == 200:
            for msg in r.json().get("messages", [])[:20]:
                mr = httpx.get(
                    f"https://gmail.googleapis.com/gmail/v1/users/me/messages/{msg['id']}",
                    params={"format": "metadata", "metadataHeaders": ["Subject", "From", "Date"]},
                    headers=hdrs, timeout=10)
                if mr.status_code == 200:
                    meta = {h["name"]: h["value"] for h in mr.json().get("payload", {}).get("headers", [])}
                    docs.append({
                        "title":    f"Gmail: {meta.get('Subject', '(no subject)')}",
                        "content":  f"From: {meta.get('From','')}\nDate: {meta.get('Date','')}\n\n{mr.json().get('snippet','')}",
                        "source":   f"https://mail.google.com/mail/u/0/#inbox/{msg['id']}",
                        "metadata": {"service": "gmail", "type": "email"},
                    })
    except Exception as exc:
        print(f"[Google/Gmail] {exc}")

    # ── Drive + Docs + Sheets ─────────────────────────────────────────────────
    try:
        r = httpx.get("https://www.googleapis.com/drive/v3/files",
                      params={"pageSize": 50, "orderBy": "modifiedTime desc",
                              "fields": "files(id,name,mimeType,modifiedTime,webViewLink)",
                              "q": "trashed=false"},
                      headers=hdrs, timeout=20)
        if r.status_code == 200:
            for f in r.json().get("files", []):
                mime = f.get("mimeType", "")
                name = f.get("name", "")
                content = f"Modified: {f.get('modifiedTime','')}"

                if mime == "application/vnd.google-apps.document":
                    dr = httpx.get(f"https://docs.googleapis.com/v1/documents/{f['id']}",
                                   headers=hdrs, timeout=10)
                    if dr.status_code == 200:
                        parts = []
                        for el in dr.json().get("body", {}).get("content", []):
                            for pe in el.get("paragraph", {}).get("elements", []):
                                parts.append(pe.get("textRun", {}).get("content", ""))
                        content = "".join(parts)[:3000]

                elif mime == "application/vnd.google-apps.spreadsheet":
                    sr = httpx.get(f"https://sheets.googleapis.com/v4/spreadsheets/{f['id']}/values/A1:Z50",
                                   headers=hdrs, timeout=10)
                    if sr.status_code == 200:
                        rows = sr.json().get("values", [])
                        content = "\n".join("\t".join(str(c) for c in row) for row in rows[:30])

                elif mime == "application/vnd.google-apps.form":
                    fr = httpx.get(f"https://forms.googleapis.com/v1/forms/{f['id']}",
                                   headers=hdrs, timeout=10)
                    if fr.status_code == 200:
                        fd = fr.json()
                        questions = [q.get("title", "") for q in fd.get("items", [])]
                        content = f"Form: {fd.get('info', {}).get('title', name)}\nQuestions: {', '.join(questions[:20])}"

                docs.append({
                    "title":    f"Drive: {name}",
                    "content":  content[:3000],
                    "source":   f.get("webViewLink", f"https://drive.google.com/file/d/{f['id']}"),
                    "metadata": {"service": "drive", "mime": mime},
                })
    except Exception as exc:
        print(f"[Google/Drive] {exc}")

    # ── Calendar: upcoming events ─────────────────────────────────────────────
    try:
        now_iso = datetime.now(timezone.utc).isoformat()
        r = httpx.get("https://www.googleapis.com/calendar/v3/calendars/primary/events",
                      params={"maxResults": 20, "orderBy": "startTime",
                              "singleEvents": "true", "timeMin": now_iso},
                      headers=hdrs, timeout=15)
        if r.status_code == 200:
            for ev in r.json().get("items", []):
                start = ev.get("start", {}).get("dateTime") or ev.get("start", {}).get("date", "")
                docs.append({
                    "title":    f"Calendar: {ev.get('summary', '(no title)')}",
                    "content":  f"Start: {start}\nDescription: {ev.get('description','')}\nLocation: {ev.get('location','')}",
                    "source":   ev.get("htmlLink", "https://calendar.google.com"),
                    "metadata": {"service": "calendar", "type": "event"},
                })
    except Exception as exc:
        print(f"[Google/Calendar] {exc}")

    # ── Tasks ─────────────────────────────────────────────────────────────────
    try:
        r = httpx.get("https://tasks.googleapis.com/tasks/v1/users/@me/lists",
                      headers=hdrs, timeout=10)
        if r.status_code == 200:
            for tl in r.json().get("items", []):
                tr = httpx.get(f"https://tasks.googleapis.com/tasks/v1/lists/{tl['id']}/tasks",
                               params={"showCompleted": "false", "maxResults": 50},
                               headers=hdrs, timeout=10)
                if tr.status_code == 200:
                    for task in tr.json().get("items", []):
                        docs.append({
                            "title":    f"Task: {task.get('title','(no title)')}",
                            "content":  f"List: {tl.get('title','')}\nDue: {task.get('due','No due date')}\nNotes: {task.get('notes','')}",
                            "source":   "https://tasks.google.com/",
                            "metadata": {"service": "tasks", "type": "task"},
                        })
    except Exception as exc:
        print(f"[Google/Tasks] {exc}")

    return docs


# ── Master dispatcher ─────────────────────────────────────────────────────────

_FETCHERS: dict = {
    "discord":          _fetch_discord,
    "telegram":         _fetch_telegram,
    "slack":            _fetch_slack,
    "notion":           _fetch_notion,
    "todoist":          _fetch_todoist,
    "trello":           _fetch_trello,
    "airtable":         _fetch_airtable,
    "linear":           _fetch_linear,
    "asana":            _fetch_asana,
    "jira":             _fetch_jira,
    "salesforce":       _fetch_salesforce,
    "hubspot":          _fetch_hubspot,
    "supabase":         _fetch_supabase,
    "arxiv":            _fetch_arxiv,
    "pubmed":           _fetch_pubmed,
    "semantic_scholar": _fetch_semantic_scholar,
    "newsapi":          _fetch_newsapi,
    "reddit":           _fetch_reddit,
    "wikipedia":        _fetch_wikipedia,
    "youtube":          _fetch_youtube,
    "github_api":       _fetch_github_api,
    "gitlab":           _fetch_gitlab,
    "google_workspace": _fetch_google_workspace,
}


def _run_index_job(conn_id: str, creds: dict, opts: dict) -> None:
    """Background thread: fetch docs and ingest into RAG backbone."""
    status_data: dict = {}
    with _INDEX_LOCK:
        status_data = _load_index_status()
        status_data[conn_id] = {"status": "indexing", "started": datetime.now(timezone.utc).isoformat(), "docs": 0, "error": None}
        _save_index_status(status_data)

    try:
        fetcher = _FETCHERS.get(conn_id)
        if fetcher is None:
            raise ValueError(f"No fetcher implemented for '{conn_id}'")
        docs = fetcher(creds, opts)
        count = _ingest_batch(docs, conn_id)
        with _INDEX_LOCK:
            status_data = _load_index_status()
            status_data[conn_id] = {
                "status": "indexed",
                "last_indexed": datetime.now(timezone.utc).isoformat(),
                "docs": count,
                "total_fetched": len(docs),
                "error": None,
            }
            _save_index_status(status_data)
    except Exception as exc:
        with _INDEX_LOCK:
            status_data = _load_index_status()
            status_data[conn_id] = {
                "status": "error",
                "last_indexed": datetime.now(timezone.utc).isoformat(),
                "docs": 0,
                "error": str(exc),
            }
            _save_index_status(status_data)


@app.route("/connections/index/status", methods=["GET"])
def get_all_index_status() -> Response:
    with _INDEX_LOCK:
        status = _load_index_status()
    # Augment with local RAG doc counts per source_type
    with _RAG_LOCK:
        store = _rag_load()
    counts: dict[str, int] = {}
    for doc in store.values():
        st = doc.get("source_type", "unknown")
        counts[st] = counts.get(st, 0) + 1
    for conn_id, cnt in counts.items():
        if conn_id in status:
            status[conn_id]["local_docs"] = cnt
        else:
            status[conn_id] = {"status": "indexed", "docs": cnt, "local_docs": cnt}
    return jsonify(status)


@app.route("/rag/search", methods=["GET", "POST"])
def rag_search_endpoint() -> Response:
    """Search the local RAG store."""
    if request.method == "POST":
        body = request.get_json(silent=True) or {}
        query = body.get("query", "")
        limit = int(body.get("limit", 5))
        source_type = body.get("source_type")
    else:
        query = request.args.get("q", "")
        limit = int(request.args.get("limit", 5))
        source_type = request.args.get("source_type")
    if not query:
        return jsonify({"error": "query required"}), 400
    hits = _rag_search(query, limit=limit, source_type=source_type)
    return jsonify({"query": query, "results": hits, "count": len(hits)})


@app.route("/connections/<conn_id>/index", methods=["POST"])
def index_connection(conn_id: str) -> Response:
    """Trigger background RAG indexing for a connection."""
    with _CONN_LOCK:
        data = _load_connections()
    cfg = data.get(conn_id, {})
    creds = cfg.get("credentials", {})
    opts = request.get_json(silent=True) or {}

    if not cfg:
        return jsonify({"ok": False, "error": "Connection not configured"}), 400
    if not creds:
        return jsonify({"ok": False, "error": "No credentials saved for this connection"}), 400
    if conn_id not in _FETCHERS:
        return jsonify({"ok": False, "error": f"Indexing not yet supported for '{conn_id}'"}), 400

    t = threading.Thread(target=_run_index_job, args=(conn_id, creds, opts), daemon=True)
    t.start()
    return jsonify({"ok": True, "status": "indexing", "message": f"Indexing {conn_id} in background…"})



@app.route("/connections/telegram/webhook", methods=["POST"])
def telegram_webhook() -> Response:
    """Receive incoming Telegram updates via webhook and ingest into local RAG store."""
    import hashlib
    # Verify secret token (set during webhook registration)
    with _CONN_LOCK:
        conns = _load_connections()
    tg_cfg = conns.get("telegram", {})
    token = (tg_cfg.get("credentials") or {}).get("bot_token", "")

    if token:
        expected_secret = hashlib.sha256(token.encode()).hexdigest()[:32]
        incoming_secret = request.headers.get("X-Telegram-Bot-Api-Secret-Token", "")
        if incoming_secret != expected_secret:
            return jsonify({"ok": False}), 403

    update = request.get_json(silent=True) or {}
    msg = update.get("message") or update.get("channel_post") or {}
    text = msg.get("text", "")
    if text:
        chat = msg.get("chat", {})
        doc = {
            "title":    f"Telegram: {chat.get('title', chat.get('first_name', 'DM'))}",
            "content":  text,
            "source":   f"telegram:{msg.get('message_id', update.get('update_id', 'unknown'))}",
            "metadata": {
                "chat_id":  str(chat.get("id", "")),
                "chat_name": chat.get("title") or chat.get("first_name", ""),
                "date":     str(msg.get("date", "")),
            },
        }
        threading.Thread(target=_rag_ingest, args=([doc], "telegram"), daemon=True).start()

    return jsonify({"ok": True})


# ══════════════════════════════════════════════════════════════════════════════
# Logs — proxy backbone trace + loglines endpoints, serve UI log tail
# ══════════════════════════════════════════════════════════════════════════════

@app.route("/api/v1/memories")
def proxy_memories() -> Response:
    """Proxy GET /api/v1/memories → backbone /v1/memories."""
    params = request.args.to_dict(flat=False)
    try:
        with _client() as client:
            r = client.get(
                f"{_BACKBONE_URL}/v1/memories",
                headers={"Authorization": f"Bearer {_BACKBONE_KEY}"},
                params=params,
                timeout=15,
            )
            return jsonify(r.json()), r.status_code
    except Exception as exc:
        return jsonify({"error": str(exc), "items": [], "total": 0}), 502


@app.route("/api/v1/memories/knowledge")
def proxy_memories_knowledge() -> Response:
    """Proxy GET /api/v1/memories/knowledge → backbone /v1/memories/knowledge."""
    params = request.args.to_dict(flat=False)
    try:
        with _client() as client:
            r = client.get(
                f"{_BACKBONE_URL}/v1/memories/knowledge",
                headers={"Authorization": f"Bearer {_BACKBONE_KEY}"},
                params=params,
                timeout=15,
            )
            return jsonify(r.json()), r.status_code
    except Exception as exc:
        return jsonify({"error": str(exc), "items": [], "total": 0}), 502


@app.route("/api/v1/goals", methods=["GET"])
def proxy_goals_list() -> Response:
    """Proxy GET /api/v1/goals → backbone /v1/goals."""
    try:
        with _client() as client:
            r = client.get(
                f"{_BACKBONE_URL}/v1/goals",
                headers={"Authorization": f"Bearer {_BACKBONE_KEY}"},
                params=request.args,
                timeout=10,
            )
            return jsonify(r.json())
    except Exception as exc:
        return jsonify({"error": str(exc), "goals": [], "count": 0}), 502


@app.route("/api/v1/goals", methods=["POST"])
def proxy_goals_create() -> Response:
    """Proxy POST /api/v1/goals → backbone /v1/goals."""
    try:
        with _client() as client:
            r = client.post(
                f"{_BACKBONE_URL}/v1/goals",
                headers={"Authorization": f"Bearer {_BACKBONE_KEY}", "Content-Type": "application/json"},
                json=request.get_json(),
                timeout=10,
            )
            return jsonify(r.json()), r.status_code
    except Exception as exc:
        return jsonify({"error": str(exc)}), 502


@app.route("/api/v1/goals/<goal_id>", methods=["PUT"])
def proxy_goals_update(goal_id: str) -> Response:
    """Proxy PUT /api/v1/goals/:id → backbone /v1/goals/:id."""
    try:
        with _client() as client:
            r = client.put(
                f"{_BACKBONE_URL}/v1/goals/{goal_id}",
                headers={"Authorization": f"Bearer {_BACKBONE_KEY}", "Content-Type": "application/json"},
                json=request.get_json(),
                timeout=10,
            )
            return jsonify(r.json()), r.status_code
    except Exception as exc:
        return jsonify({"error": str(exc)}), 502


@app.route("/api/v1/goals/<goal_id>", methods=["DELETE"])
def proxy_goals_delete(goal_id: str) -> Response:
    """Proxy DELETE /api/v1/goals/:id → backbone /v1/goals/:id."""
    try:
        with _client() as client:
            r = client.delete(
                f"{_BACKBONE_URL}/v1/goals/{goal_id}",
                headers={"Authorization": f"Bearer {_BACKBONE_KEY}"},
                timeout=10,
            )
            return jsonify(r.json()), r.status_code
    except Exception as exc:
        return jsonify({"error": str(exc)}), 502


@app.route("/api/v1/daemons", methods=["GET"])
def proxy_daemons() -> Response:
    """Proxy GET /api/v1/daemons → backbone /v1/daemons."""
    try:
        with _client() as client:
            r = client.get(
                f"{_BACKBONE_URL}/v1/daemons",
                headers={"Authorization": f"Bearer {_BACKBONE_KEY}"},
                timeout=10,
            )
            return jsonify(r.json())
    except Exception as exc:
        return jsonify({"error": str(exc), "daemons": []}), 502


@app.route("/api/v1/documents/upload", methods=["POST"])
def proxy_document_upload() -> Response:
    """Proxy POST /api/v1/documents/upload → backbone /v1/documents/upload."""
    try:
        if "file" not in request.files:
            return jsonify({"error": "missing 'file' field"}), 400
        f = request.files["file"]
        with _client() as client:
            r = client.post(
                f"{_BACKBONE_URL}/v1/documents/upload",
                headers={"Authorization": f"Bearer {_BACKBONE_KEY}"},
                files={"file": (f.filename, f.stream, f.content_type or "application/octet-stream")},
                timeout=60,
            )
            return jsonify(r.json()), r.status_code
    except Exception as exc:
        return jsonify({"error": str(exc)}), 502


@app.route("/api/v1/documents", methods=["GET"])
def proxy_documents_list() -> Response:
    """Proxy GET /api/v1/documents → backbone /v1/documents."""
    try:
        with _client() as client:
            r = client.get(
                f"{_BACKBONE_URL}/v1/documents",
                headers={"Authorization": f"Bearer {_BACKBONE_KEY}"},
                timeout=10,
            )
            return jsonify(r.json())
    except Exception as exc:
        return jsonify({"error": str(exc), "documents": []}), 502


@app.route("/api/v1/feedback", methods=["POST"])
def proxy_reaction_feedback() -> Response:
    """Proxy POST /api/v1/feedback → backbone /v1/feedback."""
    try:
        with _client() as client:
            r = client.post(
                f"{_BACKBONE_URL}/v1/feedback",
                json=request.get_json(force=True),
                headers={"Authorization": f"Bearer {_BACKBONE_KEY}"},
                timeout=10,
            )
            return jsonify(r.json()), r.status_code
    except Exception as exc:
        return jsonify({"error": str(exc)}), 502


@app.route("/api/v1/sovereign/identity", methods=["GET"])
def proxy_sovereign_identity_get() -> Response:
    """Proxy GET /api/v1/sovereign/identity → backbone /v1/sovereign/identity."""
    try:
        with _client() as client:
            r = client.get(
                f"{_BACKBONE_URL}/v1/sovereign/identity",
                headers={"Authorization": f"Bearer {_BACKBONE_KEY}"},
                timeout=10,
            )
            return jsonify(r.json()), r.status_code
    except Exception as exc:
        return jsonify({"error": str(exc)}), 502


@app.route("/api/v1/sovereign/identity", methods=["PUT"])
def proxy_sovereign_identity_put() -> Response:
    """Proxy PUT /api/v1/sovereign/identity → backbone /v1/sovereign/identity."""
    try:
        with _client() as client:
            r = client.put(
                f"{_BACKBONE_URL}/v1/sovereign/identity",
                json=request.get_json(force=True),
                headers={"Authorization": f"Bearer {_BACKBONE_KEY}"},
                timeout=10,
            )
            return jsonify(r.json()), r.status_code
    except Exception as exc:
        return jsonify({"error": str(exc)}), 502


@app.route("/logs/traces")
def logs_traces() -> Response:
    limit = request.args.get("limit", "50")
    try:
        with _client() as client:
            r = client.get(
                f"{_BACKBONE_URL}/v1/traces",
                headers={"Authorization": f"Bearer {_BACKBONE_KEY}"},
                params={"limit": limit},
                timeout=10,
            )
            return jsonify(r.json())
    except Exception as exc:
        return jsonify({"success": False, "traces": [], "error": str(exc)})


@app.route("/logs/raw")
def logs_raw() -> Response:
    n = int(request.args.get("n", "300"))
    sources = request.args.getlist("source") or ["backbone", "ui"]
    lines_out = []

    if "backbone" in sources:
        log_path = Path(__file__).parent / "go_backbone.log"
        if log_path.exists():
            try:
                raw = log_path.read_text(errors="replace").splitlines()
                for l in raw[-n:]:
                    lines_out.append({"source": "backbone", "raw": l})
            except Exception:
                pass

    if "ui" in sources:
        try:
            import subprocess
            result = subprocess.run(
                ["journalctl", "-u", "sovereignclaw-ui.service", "-n", str(n), "--no-pager", "-o", "short"],
                capture_output=True, text=True, timeout=5,
            )
            for l in result.stdout.splitlines():
                lines_out.append({"source": "ui", "raw": l})
        except Exception:
            pass

    # Sort backbone lines by timestamp prefix if present, keep ui lines at end
    return jsonify({"lines": lines_out[-n:], "total": len(lines_out)})


def main() -> None:
    """Main entry point for the UI server"""
    import sys
    # Force unbuffered output
    sys.stdout.reconfigure(line_buffering=True) if hasattr(sys.stdout, 'reconfigure') else None
    sys.stderr.reconfigure(line_buffering=True) if hasattr(sys.stderr, 'reconfigure') else None
    
    port = int(os.getenv("MAVAIA_UI_PORT", "5000"))
    host = os.getenv("MAVAIA_UI_HOST", "0.0.0.0")
    
    # Check if static directory exists
    if not STATIC_DIR.exists():
        print(f"Warning: Static directory not found: {STATIC_DIR}", file=sys.stderr, flush=True)
        print("UI may not work correctly without static files.", file=sys.stderr, flush=True)
    
    print(f"Starting OricliAlpha UI server...", flush=True)
    print(f"  Host: {host}", flush=True)
    print(f"  Port: {port}", flush=True)
    print(f"  API Base: {API_BASE}", flush=True)
    print(f"  Static files: {STATIC_DIR}", flush=True)
    print(f"\nOpen http://localhost:{port} in your browser", flush=True)
    print("Press CTRL+C to stop\n", flush=True)

    # Re-register any auto-index schedules from saved connection config
    _boot_auto_index_schedules()

    try:
        # Flask development server - use threaded mode
        # Note: This is the development server, not production-ready
        print(f"[DEBUG] About to start Flask app.run()", flush=True)
        sys.stderr.write(f"[DEBUG] Starting Flask on {host}:{port}\n")
        sys.stderr.flush()
        
        # Start Flask server (this blocks until server stops)
        app.run(host=host, port=port, debug=False, threaded=True, use_reloader=False)
        
        # This line won't be reached until server stops
        print(f"[DEBUG] Flask server stopped", flush=True)
    except KeyboardInterrupt:
        print("\nShutting down...", flush=True)
    except OSError as exc:
        if "Address already in use" in str(exc):
            print(f"\nError: Port {port} is already in use.", file=sys.stderr, flush=True)
            print(f"Try using a different port: MAVAIA_UI_PORT=5001 python3 ui_app.py", file=sys.stderr, flush=True)
        else:
            print(f"\nError starting server: {exc}", file=sys.stderr, flush=True)
        raise
    except Exception as exc:  # noqa: BLE001
        print(f"\nError starting server: {exc}", file=sys.stderr, flush=True)
        import traceback
        traceback.print_exc(file=sys.stderr)
        sys.stderr.flush()
        raise


if __name__ == "__main__":
    main()

