from __future__ import annotations
"""
Cognitive Trace Diagnostics Module

Provides structured, privacy-preserving execution traces across module pipelines.

Primary goals:
- Make routing/execution traceable for debugging and evaluation.
- Provide standardized complexity diagnostics (path length, module hops, fallbacks, timings).
- Avoid logging or storing sensitive inputs (keys/tokens/PII).
"""



import logging
import time
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from mavaia_core.brain.base_module import BaseBrainModule, ModuleMetadata
from mavaia_core.exceptions import (
    InvalidParameterError,
    ModuleNotFoundError,
    ModuleOperationError,
)

logger = logging.getLogger(__name__)


_SENSITIVE_KEY_SUBSTRINGS = (
    "api_key",
    "apikey",
    "token",
    "secret",
    "password",
    "authorization",
    "bearer",
    "private_key",
)


def _is_sensitive_key(key: str) -> bool:
    k = key.lower()
    return any(s in k for s in _SENSITIVE_KEY_SUBSTRINGS)


def _summarize_value(value: Any, *, max_str_len: int = 200, max_list_items: int = 10) -> Any:
    """Return a JSON-serializable, privacy-preserving summary of a value."""
    if value is None:
        return None
    if isinstance(value, bool):
        return value
    if isinstance(value, (int, float)):
        return value
    if isinstance(value, str):
        trimmed = value[:max_str_len]
        return {"type": "str", "len": len(value), "preview": trimmed}
    if isinstance(value, bytes):
        return {"type": "bytes", "len": len(value)}
    if isinstance(value, dict):
        return {str(k): _summarize_value(v) for k, v in list(value.items())[:100]}
    if isinstance(value, list):
        return {
            "type": "list",
            "len": len(value),
            "items": [_summarize_value(v) for v in value[:max_list_items]],
        }
    if isinstance(value, tuple):
        return {"type": "tuple", "len": len(value)}
    return {"type": type(value).__name__}


def _sanitize_params(params: Dict[str, Any]) -> Dict[str, Any]:
    """Redact sensitive keys and summarize values."""
    sanitized: Dict[str, Any] = {}
    for key, value in params.items():
        if _is_sensitive_key(str(key)):
            sanitized[str(key)] = "***REDACTED***"
            continue
        sanitized[str(key)] = _summarize_value(value)
    return sanitized


def _summarize_result(result: Any) -> Dict[str, Any]:
    """Summarize result without storing full payloads."""
    if isinstance(result, dict):
        keys = list(result.keys())
        success = bool(result.get("success", True))
        return {
            "type": "dict",
            "success_field": "success" in result,
            "success_value": success,
            "keys": keys[:50],
        }
    if isinstance(result, str):
        return {"type": "str", "len": len(result), "preview": result[:200]}
    return {"type": type(result).__name__}


def _parse_step_spec(item: Dict[str, Any], *, index: int) -> Dict[str, Any]:
    """Parse and validate a step specification dict."""
    module = item.get("module")
    op = item.get("operation")
    step_params = item.get("params", {})
    if not isinstance(module, str) or not module:
        raise InvalidParameterError("module", str(module), f"step[{index}].module must be a non-empty string")
    if not isinstance(op, str) or not op:
        raise InvalidParameterError("operation", str(op), f"step[{index}].operation must be a non-empty string")
    if not isinstance(step_params, dict):
        raise InvalidParameterError("params", str(type(step_params)), f"step[{index}].params must be a dict")
    return {
        "module": module,
        "operation": op,
        "params": step_params,
        "allow_failure": bool(item.get("allow_failure", False)),
        "is_fallback": bool(item.get("is_fallback", False)),
    }


class CognitiveTraceDiagnosticsModule(BaseBrainModule):
    """Collects structured execution traces for module pipelines."""

    @property
    def metadata(self) -> ModuleMetadata:
        return ModuleMetadata(
            name="cognitive_trace_diagnostics",
            version="1.0.0",
            description=(
                "Collects privacy-preserving execution traces across module pipelines, "
                "including complexity diagnostics (path length, module hops, fallbacks, timings)."
            ),
            operations=["trace_pipeline", "summarize_trace", "validate_trace"],
            dependencies=[],
            model_required=False,
        )

    def execute(self, operation: str, params: Dict[str, Any]) -> Dict[str, Any]:
        if operation == "trace_pipeline":
            return self._trace_pipeline(params)
        if operation == "summarize_trace":
            return self._summarize_trace(params)
        if operation == "validate_trace":
            return self._validate_trace(params)
        raise InvalidParameterError(
            parameter="operation",
            value=operation,
            reason="Unknown operation for cognitive_trace_diagnostics",
        )

    def _trace_pipeline(self, params: Dict[str, Any]) -> Dict[str, Any]:
        steps_raw = params.get("steps")
        stop_on_error = bool(params.get("stop_on_error", True))
        trace_id = params.get("trace_id") or f"trace_{int(time.time() * 1000)}"
        max_steps = int(params.get("max_steps", 100))

        if not isinstance(steps_raw, list) or not steps_raw:
            raise InvalidParameterError("steps", str(type(steps_raw)), "steps must be a non-empty list")
        if max_steps < 1 or max_steps > 1000:
            raise InvalidParameterError("max_steps", str(max_steps), "max_steps must be in [1, 1000]")
        if len(steps_raw) > max_steps:
            raise InvalidParameterError("steps", str(len(steps_raw)), f"Too many steps (max {max_steps})")

        step_specs: list[dict[str, Any]] = []
        for i, item in enumerate(steps_raw):
            if not isinstance(item, dict):
                raise InvalidParameterError("steps", str(type(item)), f"step[{i}] must be an object")
            step_specs.append(_parse_step_spec(item, index=i))

        created_at = datetime.now(timezone.utc).isoformat()
        trace_steps: list[dict[str, Any]] = []
        total_start = time.time()

        last_module: Optional[str] = None
        module_hops = 0
        fallback_invocations = 0

        for idx, spec in enumerate(step_specs):
            if last_module is not None and spec["module"] != last_module:
                module_hops += 1
            last_module = spec["module"]

            step_start = time.time()
            entry: dict[str, Any] = {
                "index": idx,
                "module": spec["module"],
                "operation": spec["operation"],
                "allow_failure": bool(spec["allow_failure"]),
                "is_fallback": bool(spec["is_fallback"]),
                "params_summary": _sanitize_params(spec["params"]),
            }

            try:
                # Import lazily to avoid circular-import issues during module discovery.
                from mavaia_core.brain.registry import ModuleRegistry

                module_instance = ModuleRegistry.get_module(spec["module"])
                if module_instance is None:
                    raise ModuleNotFoundError(spec["module"])

                result = module_instance.execute(spec["operation"], spec["params"])
                entry["result_summary"] = _summarize_result(result)
                entry["success"] = True

            except ModuleNotFoundError:
                entry["success"] = False
                entry["error_type"] = "ModuleNotFoundError"
                entry["error_message"] = f"Module '{spec['module']}' not found"
                if stop_on_error and not spec["allow_failure"]:
                    raise
                if spec["is_fallback"]:
                    fallback_invocations += 1

            except Exception as e:
                entry["success"] = False
                entry["error_type"] = type(e).__name__
                entry["error_message"] = str(e)
                logger.warning(
                    "Pipeline step failed",
                    exc_info=True,
                    extra={
                        "module_name": "cognitive_trace_diagnostics",
                        "step_module": spec["module"],
                        "step_operation": spec["operation"],
                        "error_type": type(e).__name__,
                    },
                )
                if stop_on_error and not spec["allow_failure"]:
                    raise ModuleOperationError(spec["module"], spec["operation"], str(e)) from e
                if spec["is_fallback"]:
                    fallback_invocations += 1

            finally:
                entry["duration_s"] = time.time() - step_start
                trace_steps.append(entry)

        total_duration = time.time() - total_start
        path_length = len(trace_steps)

        trace = {
            "trace_id": trace_id,
            "created_at": created_at,
            "total_duration_s": total_duration,
            "path_length": path_length,
            "module_hops": module_hops,
            "fallback_invocations": fallback_invocations,
            "steps": trace_steps,
        }

        return {"success": True, "trace": trace}

    def _summarize_trace(self, params: Dict[str, Any]) -> Dict[str, Any]:
        trace = params.get("trace")
        if not isinstance(trace, dict):
            raise InvalidParameterError("trace", str(type(trace)), "trace must be a dict")
        steps = trace.get("steps", [])
        if not isinstance(steps, list):
            raise InvalidParameterError("trace.steps", str(type(steps)), "trace.steps must be a list")

        failures = [s for s in steps if isinstance(s, dict) and not s.get("success", True)]
        total_time = float(trace.get("total_duration_s", 0.0) or 0.0)

        return {
            "success": True,
            "summary": {
                "trace_id": trace.get("trace_id"),
                "created_at": trace.get("created_at"),
                "path_length": len(steps),
                "failures": len(failures),
                "total_duration_s": total_time,
                "module_hops": int(trace.get("module_hops", 0) or 0),
                "fallback_invocations": int(trace.get("fallback_invocations", 0) or 0),
                "failure_types": sorted({str(f.get("error_type")) for f in failures if isinstance(f, dict)}),
            },
        }

    def _validate_trace(self, params: Dict[str, Any]) -> Dict[str, Any]:
        trace = params.get("trace")
        if not isinstance(trace, dict):
            return {"success": True, "is_valid": False, "issues": ["trace must be a dict"]}
        issues: list[str] = []
        for field in ("trace_id", "created_at", "steps"):
            if field not in trace:
                issues.append(f"missing field: {field}")
        steps = trace.get("steps")
        if not isinstance(steps, list):
            issues.append("steps must be a list")
        else:
            for i, step in enumerate(steps[:1000]):
                if not isinstance(step, dict):
                    issues.append(f"step[{i}] must be a dict")
                    continue
                for req in ("module", "operation", "duration_s", "success"):
                    if req not in step:
                        issues.append(f"step[{i}] missing {req}")
        return {"success": True, "is_valid": len(issues) == 0, "issues": issues}

