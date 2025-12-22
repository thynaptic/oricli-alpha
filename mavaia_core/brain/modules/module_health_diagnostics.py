"""
Module Health Diagnostics

Provides reproducible, programmatic diagnostics for module importability and basic integrity.

This module is designed to help operators and evaluators answer:
- Which brain modules can be imported right now?
- Which modules fail import, and why?
- How long does each module import take?

Notes:
- This module does NOT execute module operations and does not call initialize().
- It avoids leaking sensitive data by truncating error messages and not including stack traces by default.
"""

from __future__ import annotations

import importlib.util
import inspect
import logging
import sys
import time
import uuid
from pathlib import Path
from typing import Any, Dict, List, Optional

from mavaia_core.brain.base_module import BaseBrainModule, ModuleMetadata
from mavaia_core.exceptions import InvalidParameterError

logger = logging.getLogger(__name__)


def _truncate(text: str, limit: int = 400) -> str:
    if len(text) <= limit:
        return text
    return text[:limit] + "…"


def _collect_module_files(modules_dir: Path, include_subdirs: bool) -> list[Path]:
    excluded_names = {
        "__init__.py",
        "base_module.py",
        "module_registry.py",
        "model_manager.py",
        "tot_models.py",
        "cot_models.py",
        "mcts_models.py",
        "tool_calling_models.py",
    }
    files: list[Path] = []
    for f in modules_dir.glob("*.py"):
        if f.name in excluded_names:
            continue
        files.append(f)

    if include_subdirs:
        for subdir in modules_dir.iterdir():
            if not subdir.is_dir():
                continue
            if subdir.name.startswith("__"):
                continue
            if subdir.name == "models":
                continue
            for f in subdir.glob("*.py"):
                if f.name == "__init__.py":
                    continue
                files.append(f)

    return sorted(files)


def _exec_module_with_timeout(spec, module, timeout_s: float) -> tuple[bool, Optional[BaseException]]:
    """Execute module import with a soft timeout using a daemon thread."""
    import threading

    done = {"ok": False}
    err: dict[str, Optional[BaseException]] = {"exc": None}

    def run() -> None:
        try:
            if spec.loader is None:
                raise ImportError("spec.loader is None")
            spec.loader.exec_module(module)
            done["ok"] = True
        except BaseException as e:  # noqa: BLE001 - we are isolating import failures
            err["exc"] = e

    t = threading.Thread(target=run, daemon=True)
    t.start()
    t.join(timeout=timeout_s)

    if t.is_alive():
        return (False, TimeoutError(f"Import timeout after {timeout_s:.2f}s"))
    if err["exc"] is not None:
        return (False, err["exc"])
    return (bool(done["ok"]), None)


class ModuleHealthDiagnosticsModule(BaseBrainModule):
    """Diagnose module importability and basic integrity."""

    @property
    def metadata(self) -> ModuleMetadata:
        return ModuleMetadata(
            name="module_health_diagnostics",
            version="1.0.0",
            description="Diagnostics for module importability and basic integrity (timeouts, errors, import durations).",
            operations=["scan_modules", "scan_module_file"],
            dependencies=[],
            model_required=False,
        )

    def execute(self, operation: str, params: Dict[str, Any]) -> Dict[str, Any]:
        if operation == "scan_modules":
            return self._scan_modules(params)
        if operation == "scan_module_file":
            return self._scan_module_file(params)
        raise InvalidParameterError("operation", operation, "Unknown operation for module_health_diagnostics")

    def _scan_modules(self, params: Dict[str, Any]) -> Dict[str, Any]:
        include_subdirs = bool(params.get("include_subdirs", True))
        max_modules = int(params.get("max_modules", 500))
        import_timeout_s = float(params.get("import_timeout_s", 8.0))
        include_tracebacks = bool(params.get("include_tracebacks", False))

        if max_modules < 1 or max_modules > 5000:
            raise InvalidParameterError("max_modules", str(max_modules), "max_modules must be in [1, 5000]")
        if import_timeout_s <= 0 or import_timeout_s > 120:
            raise InvalidParameterError("import_timeout_s", str(import_timeout_s), "import_timeout_s must be in (0, 120]")

        modules_dir = Path(__file__).parent
        files = _collect_module_files(modules_dir, include_subdirs)[:max_modules]
        # Some legacy modules may still rely on local-import patterns (e.g., `from base_module import ...`
        # or `from cot_models import ...`). We keep compatibility here, but do so in a reversible way to
        # avoid polluting interpreter state for callers.
        import mavaia_core.brain.base_module as package_base_module
        prior_base_module = sys.modules.get("base_module")
        added_sys_path = False
        if str(modules_dir) not in sys.path:
            sys.path.insert(0, str(modules_dir))
            added_sys_path = True
        sys.modules["base_module"] = package_base_module

        entries: list[dict[str, Any]] = []
        ok_count = 0
        fail_count = 0
        try:
            for file_path in files:
                scan = self._scan_one_file(file_path, import_timeout_s, include_tracebacks)
                entries.append(scan)
                if scan["import_ok"]:
                    ok_count += 1
                else:
                    fail_count += 1
        finally:
            # Restore interpreter state
            if added_sys_path:
                try:
                    sys.path.remove(str(modules_dir))
                except ValueError:
                    pass
            if prior_base_module is None:
                sys.modules.pop("base_module", None)
            else:
                sys.modules["base_module"] = prior_base_module

        return {
            "success": True,
            "result": {
                "modules_dir": str(modules_dir),
                "include_subdirs": include_subdirs,
                "max_modules": max_modules,
                "import_timeout_s": import_timeout_s,
                "import_ok": ok_count,
                "import_failed": fail_count,
                "total_scanned": len(entries),
                "entries": entries,
            },
        }

    def _scan_module_file(self, params: Dict[str, Any]) -> Dict[str, Any]:
        path = params.get("path")
        import_timeout_s = float(params.get("import_timeout_s", 8.0))
        include_tracebacks = bool(params.get("include_tracebacks", False))

        if not isinstance(path, str) or not path:
            raise InvalidParameterError("path", str(path), "path must be a non-empty string")
        file_path = Path(path)
        if not file_path.exists() or not file_path.is_file():
            raise InvalidParameterError("path", path, "path must point to an existing file")
        if file_path.suffix != ".py":
            raise InvalidParameterError("path", path, "path must be a .py file")

        return {"success": True, "result": self._scan_one_file(file_path, import_timeout_s, include_tracebacks)}

    def _scan_one_file(self, file_path: Path, import_timeout_s: float, include_tracebacks: bool) -> Dict[str, Any]:
        started = time.time()
        module_name = f"healthscan_{file_path.stem}_{uuid.uuid4().hex[:8]}"

        spec = importlib.util.spec_from_file_location(module_name, file_path)
        if spec is None:
            return {
                "file": str(file_path),
                "import_ok": False,
                "import_time_s": 0.0,
                "error_type": "ImportError",
                "error_message": "spec_from_file_location returned None",
                "module_classes": [],
            }

        module = importlib.util.module_from_spec(spec)
        ok, exc = _exec_module_with_timeout(spec, module, import_timeout_s)
        duration = time.time() - started

        if not ok:
            error_type = type(exc).__name__ if exc is not None else "ImportError"
            error_message = _truncate(str(exc) if exc is not None else "Unknown import failure")
            result: dict[str, Any] = {
                "file": str(file_path),
                "import_ok": False,
                "import_time_s": duration,
                "error_type": error_type,
                "error_message": error_message,
                "module_classes": [],
            }
            if include_tracebacks and exc is not None:
                import traceback

                result["traceback"] = _truncate("".join(traceback.format_exception(type(exc), exc, exc.__traceback__)), 5000)
            return result

        # Discover BaseBrainModule subclasses in the imported module.
        classes: list[dict[str, Any]] = []
        for _, obj in inspect.getmembers(module, inspect.isclass):
            try:
                if issubclass(obj, BaseBrainModule) and obj is not BaseBrainModule:
                    meta_name = None
                    try:
                        instance = obj()
                        meta = getattr(instance, "metadata", None)
                        meta_name = getattr(meta, "name", None) if meta is not None else None
                    except Exception:
                        # Instantiation can be fragile; this is diagnostics only.
                        meta_name = None
                    classes.append({"class_name": obj.__name__, "metadata_name": meta_name})
            except Exception:
                continue

        return {
            "file": str(file_path),
            "import_ok": True,
            "import_time_s": duration,
            "module_classes": classes,
        }

