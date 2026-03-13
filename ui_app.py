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
import os
import sys
import time
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
API_BASE = os.getenv("MAVAIA_API_BASE", "http://localhost:8000")

# Debug: Print API_BASE at module load
import sys
sys.stderr.write(f"[DEBUG] UI app loaded, API_BASE={API_BASE}\n")
sys.stderr.flush()
API_KEY = os.getenv("MAVAIA_API_KEY")
ATTACHMENT_LIMIT_MB = float(os.getenv("MAVAIA_UI_ATTACHMENT_MB", "5"))
MAX_ATTACHMENT_BYTES = int(ATTACHMENT_LIMIT_MB * 1024 * 1024)
RETRY_COUNT = 3

app = Flask(__name__, static_folder=str(STATIC_DIR))
if CORS_AVAILABLE:
    CORS(app)  # Enable CORS for production use if available


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
    """Health check with API connectivity verification"""
    try:
        # Check API connectivity
        with _client() as client:
            resp = client.get(
                f"{API_BASE}/health",
                headers=_build_headers(),
                timeout=5.0,
            )
            api_healthy = resp.status_code == 200
    except Exception:  # noqa: BLE001
        api_healthy = False

    return jsonify({
        "ok": True,
        "api_connected": api_healthy,
        "api_base": API_BASE,
    })


@app.route("/events", methods=["GET"])
def events_stub() -> Response:
    return jsonify({"events": [], "note": "stub"})


@app.route("/", methods=["GET"])
def index() -> Response:
    return send_from_directory(app.static_folder, "index.html")


@app.route("/static/<path:filename>", methods=["GET"])
def static_files(filename: str) -> Response:
    return send_from_directory(app.static_folder, filename)


@app.route("/models", methods=["GET"])
def models() -> Response:
    """Proxy to models listing endpoint"""
    target = f"{API_BASE}/v1/models"
    try:
        resp = _forward_with_retry("GET", target)
        return Response(
            resp.content, status=resp.status_code, content_type=resp.headers.get("content-type")
        )
    except Exception as exc:  # noqa: BLE001
        return jsonify({"error": {"message": str(exc), "type": "server_error", "code": 502}}), 502


@app.route("/modules", methods=["GET"])
def modules() -> Response:
    """Proxy to modules listing endpoint"""
    target = f"{API_BASE}/v1/modules"
    try:
        resp = _forward_with_retry("GET", target)
        # Ensure we return JSON content type
        content_type = resp.headers.get("content-type", "application/json")
        return Response(
            resp.content, status=resp.status_code, content_type=content_type
        )
    except ConnectError as exc:
        error_msg = f"Cannot connect to API at {API_BASE}. Is the API server running?"
        print(f"Error connecting to API: {exc}", file=sys.stderr)
        return jsonify({"error": {"message": error_msg, "type": "connection_error", "code": 502}}), 502
    except HTTPStatusError as exc:
        error_msg = f"API returned error {exc.response.status_code}: {exc.response.text}"
        print(f"API error: {error_msg}", file=sys.stderr)
        return jsonify({"error": {"message": error_msg, "type": "api_error", "code": exc.response.status_code}}), exc.response.status_code
    except Exception as exc:  # noqa: BLE001
        error_msg = f"Error fetching modules: {str(exc)}"
        print(f"Unexpected error: {error_msg}", file=sys.stderr)
        import traceback
        traceback.print_exc(file=sys.stderr)
        return jsonify({"error": {"message": error_msg, "type": "server_error", "code": 502}}), 502


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


def _sse_stream(target_url: str, payload: Dict[str, Any]) -> Iterable[str]:
    """
    Transparent SSE pass-through. If upstream already prefixes with 'data:', forward as-is;
    otherwise wrap the chunk. Do not append extra DONE markers beyond upstream.
    """
    for attempt in range(RETRY_COUNT):
        try:
            with _client().stream(
                "POST", target_url, json=payload, headers=_build_headers(), timeout=None
            ) as r:
                r.raise_for_status()
                for chunk in r.iter_text():
                    if not chunk:
                        continue
                    trimmed = chunk.strip()
                    if trimmed.startswith("data:"):
                        yield f"{trimmed}\n\n"
                    else:
                        yield f"data: {trimmed}\n\n"
                return
        except Exception as exc:  # noqa: BLE001
            if attempt < RETRY_COUNT - 1:
                time.sleep(_backoff(attempt))
                continue
            error_payload = json.dumps({
                "error": {
                    "message": str(exc),
                    "type": "server_error",
                    "code": 500
                }
            })
            yield f"data: {error_payload}\n\n"
            yield "data: [DONE]\n\n"
            return


@app.route("/chat", methods=["POST"])
def chat() -> Response:
    payload = request.get_json(silent=True) or {}
    stream = bool(payload.get("stream", True))

    try:
        _enforce_attachment_limit(payload)
    except ValueError as exc:
        return jsonify({"error": {"message": str(exc), "type": "invalid_request_error", "code": 400}}), 400

    target_url = f"{API_BASE}/v1/chat/completions"

    if stream:
        return Response(_sse_stream(target_url, payload), mimetype="text/event-stream")

    try:
        resp = _forward_with_retry("POST", target_url, json_body=payload)
        return Response(
            resp.content, status=resp.status_code, content_type=resp.headers.get("content-type")
        )
    except Exception as exc:  # noqa: BLE001
        return jsonify({"error": {"message": str(exc), "type": "server_error", "code": 502}}), 502


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

