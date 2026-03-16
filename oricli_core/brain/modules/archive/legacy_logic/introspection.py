from __future__ import annotations

import hashlib
import os
import threading
import time
from collections import OrderedDict
from copy import deepcopy
from typing import Any, Dict, Optional


def _env_bool(name: str, default: bool) -> bool:
    v = os.getenv(name)
    if v is None:
        return default
    return v.strip().lower() in ("1", "true", "yes", "y", "on")


def _sha256(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8", errors="ignore")).hexdigest()


def redact_trace_graph(
    trace_graph: Dict[str, Any],
    *,
    include_input: bool,
    output_max_chars: int,
) -> Dict[str, Any]:
    g = deepcopy(trace_graph) if isinstance(trace_graph, dict) else {"trace_graph": str(trace_graph)}

    # Input redaction
    if not include_input:
        raw_input = str(g.get("input") or "")
        g["input"] = f"sha256:{_sha256(raw_input)}" if raw_input else ""

    # Output truncation (already truncated in cognitive_generator, but enforce again)
    if isinstance(g.get("final_output"), str) and output_max_chars > 0:
        g["final_output"] = g["final_output"][:output_max_chars]

    # Node result redaction: keep only safe, compact fields.
    nodes = g.get("nodes")
    if isinstance(nodes, list):
        for node in nodes:
            if not isinstance(node, dict):
                continue
            result = node.get("result")
            if isinstance(result, dict):
                safe: Dict[str, Any] = {}
                for k in (
                    "success",
                    "error",
                    "_text_preview",
                    "confidence",
                    "matches_intent",
                    "issues",
                    "_duration_ms",
                    "duration_ms",
                ):
                    if k in result:
                        safe[k] = result.get(k)
                node["result"] = safe

    return g


class TraceStore:
    """Thread-safe in-memory trace store (ring buffer) for introspection."""

    def __init__(self) -> None:
        self._lock = threading.Lock()
        self._traces: "OrderedDict[str, Dict[str, Any]]" = OrderedDict()

    @property
    def enabled(self) -> bool:
        return _env_bool("MAVAIA_INTROSPECTION_ENABLED", True)

    @property
    def max_traces(self) -> int:
        try:
            return max(10, min(int(os.getenv("MAVAIA_INTROSPECTION_MAX_TRACES", "200")), 5000))
        except Exception:
            return 200

    @property
    def include_input(self) -> bool:
        return _env_bool("MAVAIA_INTROSPECTION_INCLUDE_INPUT", False)

    @property
    def include_context(self) -> bool:
        # Reserved for future use (context is not currently stored in trace_graph).
        return _env_bool("MAVAIA_INTROSPECTION_INCLUDE_CONTEXT", False)

    @property
    def output_max_chars(self) -> int:
        try:
            return max(0, min(int(os.getenv("MAVAIA_INTROSPECTION_OUTPUT_MAX_CHARS", "2000")), 20000))
        except Exception:
            return 2000

    def add(self, trace_id: str, trace: Dict[str, Any]) -> None:
        if not self.enabled:
            return
        if not trace_id:
            return

        record = deepcopy(trace) if isinstance(trace, dict) else {"trace": str(trace)}
        record.setdefault("trace_id", trace_id)
        record.setdefault("timestamp", time.time())

        # Apply redaction by default.
        if isinstance(record.get("trace_graph"), dict):
            record["trace_graph"] = redact_trace_graph(
                record["trace_graph"],
                include_input=self.include_input,
                output_max_chars=self.output_max_chars,
            )

        with self._lock:
            # Refresh ordering if it already exists.
            if trace_id in self._traces:
                self._traces.pop(trace_id, None)
            self._traces[trace_id] = record

            while len(self._traces) > self.max_traces:
                self._traces.popitem(last=False)

    def get(self, trace_id: str) -> Optional[Dict[str, Any]]:
        with self._lock:
            t = self._traces.get(trace_id)
            return deepcopy(t) if t else None

    def list_recent(self, limit: int = 20) -> Dict[str, Any]:
        try:
            limit_i = int(limit)
        except Exception:
            limit_i = 20
        limit_i = max(1, min(limit_i, 500))

        with self._lock:
            items = list(self._traces.values())[-limit_i:]
            return {
                "traces": deepcopy(items),
                "total": len(self._traces),
                "limit": limit_i,
            }

    def capabilities(self) -> Dict[str, Any]:
        return {
            "enabled": self.enabled,
            "max_traces": self.max_traces,
            "include_input": self.include_input,
            "include_context": self.include_context,
            "output_max_chars": self.output_max_chars,
        }


_TRACE_STORE: Optional[TraceStore] = None


def get_trace_store() -> TraceStore:
    global _TRACE_STORE
    if _TRACE_STORE is None:
        _TRACE_STORE = TraceStore()
    return _TRACE_STORE
