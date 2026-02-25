#!/usr/bin/env python3
"""Lightweight distributed launcher for NeuralTextGenerator transformer training.

This wraps `torchrun` (or `python -m torch.distributed.run`) and forwards all remaining
args to `scripts/train_neural_text_generator.py`.

Example:
  ./.venv/bin/python scripts/launch_distributed_train.py --nproc-per-node 2 -- --profile transformer_gpt2 --model-type transformer

Note: The RNN (TensorFlow/Keras) paths are not distributed here; this is primarily
for HuggingFace transformer training which supports torchrun-based DDP.
"""

from __future__ import annotations

import argparse
import os
import shutil
import subprocess
import sys
from pathlib import Path


def main() -> int:
    parser = argparse.ArgumentParser(description="Launch distributed training via torchrun")
    parser.add_argument("--nproc-per-node", type=int, default=1, help="Processes per node (GPUs per node)")
    parser.add_argument("--nnodes", type=int, default=1, help="Number of nodes")
    parser.add_argument("--node-rank", type=int, default=0, help="Node rank")
    parser.add_argument("--master-addr", type=str, default="127.0.0.1", help="Master address")
    parser.add_argument("--master-port", type=int, default=29500, help="Master port")
    parser.add_argument(
        "train_args",
        nargs=argparse.REMAINDER,
        help="Arguments forwarded to scripts/train_neural_text_generator.py (prefix with --)",
    )

    args = parser.parse_args()

    repo_root = Path(__file__).resolve().parent.parent
    train_script = repo_root / "scripts" / "train_neural_text_generator.py"

    if not train_script.exists():
        print(f"ERROR: training script not found: {train_script}", file=sys.stderr)
        return 2

    forwarded = list(args.train_args)
    if forwarded and forwarded[0] == "--":
        forwarded = forwarded[1:]

    torchrun = shutil.which("torchrun")
    if torchrun:
        cmd = [
            torchrun,
            f"--nproc_per_node={args.nproc_per_node}",
            f"--nnodes={args.nnodes}",
            f"--node_rank={args.node_rank}",
            f"--master_addr={args.master_addr}",
            f"--master_port={args.master_port}",
            str(train_script),
            *forwarded,
        ]
    else:
        # Fallback: try python -m torch.distributed.run
        cmd = [
            sys.executable,
            "-m",
            "torch.distributed.run",
            "--nproc_per_node",
            str(args.nproc_per_node),
            "--nnodes",
            str(args.nnodes),
            "--node_rank",
            str(args.node_rank),
            "--master_addr",
            str(args.master_addr),
            "--master_port",
            str(args.master_port),
            str(train_script),
            *forwarded,
        ]

    env = os.environ.copy()
    env.setdefault("MASTER_ADDR", str(args.master_addr))
    env.setdefault("MASTER_PORT", str(args.master_port))

    print("Launching:")
    print(" ".join(cmd))

    try:
        p = subprocess.run(cmd, cwd=str(repo_root), env=env)
        return int(p.returncode)
    except FileNotFoundError as e:
        print(f"ERROR: {e}", file=sys.stderr)
        print("You likely need PyTorch installed on the training box (and torchrun available).", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
