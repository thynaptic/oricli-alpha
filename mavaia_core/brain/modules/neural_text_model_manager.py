from __future__ import annotations
"""Neural text model manager.

Provides file-level model lifecycle operations around `neural_text_generator`.
"""

from typing import Any, Dict, List
import sys
from pathlib import Path
import shutil

from mavaia_core.brain.base_module import BaseBrainModule, ModuleMetadata
from mavaia_core.exceptions import InvalidParameterError


class NeuralTextModelManagerModule(BaseBrainModule):
    """Manages neural text model loading, saving, and lifecycle."""

    def __init__(self):
        self._module_registry = None

    @property
    def metadata(self) -> ModuleMetadata:
        return ModuleMetadata(
            name="neural_text_model_manager",
            version="1.0.0",
            description="Manages neural text model loading, saving, and lifecycle",
            operations=["load_model", "save_model", "list_models", "delete_model"],
            dependencies=[],
            model_required=False,
        )

    def initialize(self) -> bool:
        self._init_module_registry()
        return True

    def _init_module_registry(self) -> None:
        if self._module_registry is None:
            try:
                from mavaia_core.brain.registry import ModuleRegistry

                self._module_registry = ModuleRegistry
            except ImportError:
                print("[NeuralTextModelManagerModule] ModuleRegistry not available", file=sys.stderr)
                self._module_registry = None

    def _get_neural_text_generator(self):
        self._init_module_registry()
        if not self._module_registry:
            return None
        return self._module_registry.get_module("neural_text_generator")

    @staticmethod
    def _default_model_dir() -> Path:
        return (Path(__file__).parent.parent.parent / "models" / "neural_text_generator").resolve()

    def _get_model_dir(self, ntg=None) -> Path:
        if ntg is not None and getattr(ntg, "model_dir", None) is not None:
            try:
                return Path(ntg.model_dir).expanduser().resolve()
            except Exception:
                pass
        return self._default_model_dir()

    def execute(self, operation: str, params: Dict[str, Any]) -> Dict[str, Any]:
        ntg = self._get_neural_text_generator()

        if operation == "load_model":
            if not ntg:
                return {"success": False, "error": "neural_text_generator module unavailable"}
            return ntg.execute("load_model", params)

        if operation == "save_model":
            if not ntg:
                return {"success": False, "error": "neural_text_generator module unavailable"}
            return ntg.execute("save_model", params)

        model_dir = self._get_model_dir(ntg)
        checkpoints_dir = model_dir / "checkpoints"

        if operation == "list_models":
            def exists(p: Path) -> bool:
                try:
                    return p.exists()
                except Exception:
                    return False

            info = {
                "model_dir": str(model_dir),
                "character": {
                    "char_model_latest.keras": exists(model_dir / "char_model_latest.keras"),
                    "char_model_latest.h5": exists(model_dir / "char_model_latest.h5"),
                    "char_model.keras": exists(model_dir / "char_model.keras"),
                    "char_model.h5": exists(model_dir / "char_model.h5"),
                    "char_model.json": exists(model_dir / "char_model.json"),
                },
                "word": {
                    "word_model_latest.keras": exists(model_dir / "word_model_latest.keras"),
                    "word_model_latest.h5": exists(model_dir / "word_model_latest.h5"),
                    "word_model.keras": exists(model_dir / "word_model.keras"),
                    "word_model.h5": exists(model_dir / "word_model.h5"),
                    "word_model.json": exists(model_dir / "word_model.json"),
                },
                "transformer": {
                    "transformer_dir": exists(model_dir / "transformer"),
                },
            }
            # Light checkpoint listing (avoid huge outputs).
            try:
                if checkpoints_dir.exists():
                    info["checkpoints"] = sorted([p.name for p in checkpoints_dir.glob("*.keras")])[:50]
            except Exception:
                pass
            return {"success": True, "models": info}

        if operation == "delete_model":
            model_type = str(params.get("model_type") or params.get("type") or "").lower().strip()
            if not model_type:
                model_type = "all"

            deleted: List[str] = []
            errors: List[str] = []

            def safe_unlink(p: Path) -> None:
                try:
                    if p.exists() and p.is_file():
                        p.unlink()
                        deleted.append(str(p))
                except Exception as e:
                    errors.append(f"{p}: {e}")

            def safe_rmtree(p: Path) -> None:
                try:
                    if p.exists() and p.is_dir():
                        shutil.rmtree(p)
                        deleted.append(str(p))
                except Exception as e:
                    errors.append(f"{p}: {e}")

            def delete_checkpoints(prefix: str) -> None:
                try:
                    if not checkpoints_dir.exists():
                        return
                    for ckpt in checkpoints_dir.glob(f"{prefix}*"):
                        safe_unlink(ckpt)
                except Exception as e:
                    errors.append(str(e))

            if model_type in ("character", "char", "all"):
                for name in [
                    "char_model_latest.keras",
                    "char_model_latest.h5",
                    "char_model.keras",
                    "char_model.h5",
                    "char_model.json",
                ]:
                    safe_unlink(model_dir / name)
                delete_checkpoints("char")
                delete_checkpoints("character")

            if model_type in ("word", "all"):
                for name in [
                    "word_model_latest.keras",
                    "word_model_latest.h5",
                    "word_model.keras",
                    "word_model.h5",
                    "word_model.json",
                ]:
                    safe_unlink(model_dir / name)
                delete_checkpoints("word")

            if model_type in ("transformer", "all"):
                safe_rmtree(model_dir / "transformer")

            return {"success": len(errors) == 0, "deleted": deleted, "errors": errors}

        raise InvalidParameterError(
            parameter="operation",
            value=str(operation),
            reason="Unknown operation for neural_text_model_manager",
        )
