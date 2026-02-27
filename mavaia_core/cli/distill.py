"""Distillation training CLI wrapper for mavaia."""

from __future__ import annotations

import runpy
import sys
from pathlib import Path


def _inject_default(args: list[str], flag: str, value: str | None = None) -> None:
    if flag in args:
        return
    args.append(flag)
    if value is not None:
        args.append(value)


def main() -> int:
    repo_root = Path(__file__).resolve().parents[2]
    train_script = repo_root / "scripts" / "train_neural_text_generator.py"

    if not train_script.exists():
        print(f"Error: training script not found at {train_script}", file=sys.stderr)
        return 1

    args = sys.argv[1:]
    _inject_default(args, "--distill")
    if "--model-type" not in args and "--model_type" not in args:
        _inject_default(args, "--model-type", "transformer")
    _inject_default(args, "--teacher-model", "phi4:latest")
    _inject_default(args, "--distill-alpha", "0.7")
    _inject_default(args, "--distill-temp", "2.0")
    _inject_default(args, "--distill-topk", "20")

    sys.argv = [str(train_script)] + args
    runpy.run_path(str(train_script), run_name="__main__")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
