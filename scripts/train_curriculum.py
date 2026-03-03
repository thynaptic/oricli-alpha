#!/usr/bin/env python3
"""
Curriculum-style training runner for Mavaia.
Runs sequential training stages over a fixed list of datasets to build a baseline.
"""
import argparse
import json
import os
import sys
import site

# Ensure project root is in path
sys.path.insert(0, os.getcwd())
sys.path.insert(0, str(__import__("pathlib").Path(__file__).parent.parent))

# FORCE PATH RESOLUTION: Ensure we can see libraries installed via --user or system pip
try:
    user_site = site.getusersitepackages()
    if user_site and user_site not in sys.path:
        sys.path.append(user_site)
    for p in ["/usr/local/lib/python3.11/dist-packages", "/usr/lib/python3/dist-packages"]:
        if os.path.exists(p) and p not in sys.path:
            sys.path.append(p)
except Exception:
    pass

import subprocess
import time
import random
from datetime import datetime
from pathlib import Path

# Paths
REPO_ROOT = Path(__file__).resolve().parent.parent
TRAIN_SCRIPT = REPO_ROOT / "scripts" / "train_neural_text_generator.py"
REPORT_SCRIPT = REPO_ROOT / "scripts" / "report_card.py"

# Determine Python executable
VENV_PY = REPO_ROOT / ".venv" / "bin" / "python"
PYTHON_EXE = str(VENV_PY) if VENV_PY.exists() else sys.executable


def _now_iso():
    return datetime.utcnow().replace(microsecond=0).isoformat() + "Z"


class SmartResumePolicy:
    """
    Intelligent decision engine for curriculum resumption.
    Determines if a stage should be skipped, retouched, or fully run.
    """

    def __init__(self, target_loss: float = 0.05, retouch_threshold: float = 0.15):
        self.target_loss = target_loss
        self.retouch_threshold = retouch_threshold

    def decide(self, current_loss: float | None) -> tuple[str, float, float]:
        """
        Returns (mode, data_scale, epoch_scale)
        Modes: 'full', 'skip', 'retouch'
        """
        if current_loss is None:
            return "full", 1.0, 1.0

        if current_loss <= self.target_loss:
            return "skip", 0.0, 0.0

        if current_loss < self.retouch_threshold:
            # Dynamic Scaling: use less data for smaller gaps
            gap = current_loss - self.target_loss
            span = self.retouch_threshold - self.target_loss
            # Scale data between 10% and 50% for retouches
            data_scale = max(0.1, min(0.5, gap / span))
            return "retouch", data_scale, 1.0

        return "full", 1.0, 1.0


def _get_stage_performance(stage_name: str, run_root: Path) -> float | None:
    """
    Scans for the best/latest performance (loss) for a given stage.
    """
    # 1. Look for stage-specific directories in run_root
    # Pattern: <stage_name>_YYYYMMDD_HHMMSS
    stage_dirs = list(run_root.glob(f"{stage_name}_*"))
    
    # Also check remote sync folders if they exist
    remote_sync_root = REPO_ROOT / "models" / "neural_text_generator_remote" / "curriculum"
    if remote_sync_root.exists():
        stage_dirs.extend(list(remote_sync_root.glob(f"{stage_name}_*")))

    if not stage_dirs:
        return None

    # Sort by mtime to get latest run
    stage_dirs.sort(key=lambda d: d.stat().st_mtime, reverse=True)

    for run_dir in stage_dirs:
        # STRATEGY A: Check for HF Trainer state (Transformer models)
        trainer_states = list(run_dir.glob("**/trainer_state.json"))
        if trainer_states:
            latest_state = max(trainer_states, key=lambda p: p.stat().st_mtime)
            try:
                state_data = json.loads(latest_state.read_text())
                history = state_data.get("log_history", [])
                # Find latest entry with loss
                for entry in reversed(history):
                    loss = entry.get("loss") or entry.get("eval_loss")
                    if loss is not None:
                        return float(loss)
            except Exception:
                pass

        # STRATEGY B: Check for custom metrics file (RNN models)
        metrics_files = list(run_dir.glob("**/checkpoints/*_metrics.jsonl"))
        # Fallback to looking for ANY metrics in the run dir
        if not metrics_files:
            metrics_files = list(run_dir.glob("**/*_metrics.jsonl"))
            
        if metrics_files:
            latest_metrics = max(metrics_files, key=lambda p: p.stat().st_mtime)
            try:
                lines = latest_metrics.read_text().strip().splitlines()
                if not lines:
                    continue
                
                # Use the last recorded loss
                last_row = json.loads(lines[-1])
                
                # Check top-level or nested logs
                logs = last_row.get("logs", last_row)
                loss = logs.get("loss") or logs.get("eval_loss")
                
                # Fallback to second-to-last row
                if loss is None and len(lines) > 1:
                    prev_row = json.loads(lines[-2])
                    prev_logs = prev_row.get("logs", prev_row)
                    loss = prev_logs.get("loss")
                    
                if loss is not None:
                    return float(loss)
            except Exception:
                continue
            
    return None


def _load_progress(path: Path):
    if not path.exists():
        return {}
    try:
        return json.loads(path.read_text())
    except Exception:
        return {}


def _write_progress(path: Path, data: dict):
    data["updated_at"] = _now_iso()
    path.write_text(json.dumps(data, indent=2, sort_keys=True))


def _stage_defs(common_epochs: int, data_pct: float, wikitext: bool):
    stages = [
        {
            "name": "tone_oh_dcft_gemini",
            "title": "Stage 1: Tone Phase",
            "age": "Age 7",
            "school": "Elementary School",
            "dataset": "mlfoundations-dev/oh-dcft-v3.1-gemini-1.5-pro",
        },
        {
            "name": "logic_orca_math",
            "title": "Stage 2: Logic Phase",
            "age": "Age 12",
            "school": "Middle School",
            "dataset": "microsoft/orca-math-word-problems-200k",
        },
        {
            "name": "prose_no_robots",
            "title": "Stage 3: Prose Modernization",
            "age": "Age 14",
            "school": "Junior High",
            "dataset": "HuggingFaceH4/no_robots",
        },
        {
            "name": "capability_hotpot_qa",
            "title": "Stage 4: Capability Phase",
            "age": "Age 16",
            "school": "High School",
            "dataset": "hotpot_qa:distractor",
        },
        {
            "name": "context_booksum",
            "title": "Stage 5: Context Phase",
            "age": "Age 19",
            "school": "Undergraduate",
            "dataset": "kmfoda/booksum:chapter",
        },
        {
            "name": "knowledge_wikihop",
            "title": "Stage 6: Knowledge Phase",
            "age": "Age 23",
            "school": "Graduate School",
            "dataset": "kitsdk/wiki_hop",
        },
        {
            "name": "coding_alpaca_python",
            "title": "Stage 7: Coding Phase",
            "age": "Age 27",
            "school": "Doctoral Program",
            "dataset": "iamtarun/python_code_instructions_18k_alpaca",
        },
        {
            "name": "alignment_dpo",
            "title": "Stage 8: Alignment Phase",
            "age": "Post-Doc",
            "school": "Sovereign Alignment",
            "dataset": "Intel/orca_dpo_pairs",
            "is_dpo": True,
        },
        {
            "name": "knowledge_world_dense",
            "title": "Stage 9: Comprehensive World Knowledge",
            "age": "Age 30",
            "school": "Deep Intelligence Integration",
            "dataset": ["tau/commonsense_qa", "HuggingFaceFW/fineweb-edu", "wikimedia/wikipedia:20231101.en"],
        },
    ]
    for s in stages:
        s["epochs"] = common_epochs
        s["data_pct"] = data_pct
    return stages


def _auto_stage_overrides(stage: dict):
    datasets = stage.get("dataset", "")
    if isinstance(datasets, list):
        datasets_str = " ".join(datasets).lower()
    else:
        datasets_str = str(datasets).lower()
        
    overrides = {}
    # Default pod-friendly heuristics by dataset family.
    if "oh-dcft" in datasets_str:
        overrides = {"epochs": 1, "data_pct": 0.2}
    elif "orca-math" in datasets_str:
        overrides = {"epochs": 1, "data_pct": 0.1}
    elif "no_robots" in datasets_str:
        overrides = {"epochs": 2, "data_pct": 0.5} # Smaller, higher quality
    elif "hotpot_qa" in datasets_str:
        overrides = {"epochs": 1, "data_pct": 0.1}
    elif "booksum" in datasets_str:
        overrides = {"epochs": 1, "data_pct": 0.3}
    elif "wiki_hop" in datasets_str:
        overrides = {"epochs": 1, "data_pct": 0.1}
    elif "python_code" in datasets_str:
        overrides = {"epochs": 2, "data_pct": 0.4}
    elif "knowledge_world_dense" == stage["name"] or "fineweb-edu" in datasets_str:
        overrides = {"epochs": 1, "data_pct": 0.1} # Large diversity, keep pct low for speed
    
    if overrides:
        stage["epochs"] = overrides["epochs"]
        stage["data_pct"] = overrides["data_pct"]
        stage["auto_applied"] = True
    return stage


def _extract_loss_from_run(run_dir: Path) -> float | None:
    """
    Specifically looks for loss in a single run directory.
    """
    # 1. Check for HF Trainer state
    trainer_states = list(run_dir.glob("**/trainer_state.json"))
    if trainer_states:
        latest_state = max(trainer_states, key=lambda p: p.stat().st_mtime)
        try:
            state_data = json.loads(latest_state.read_text())
            history = state_data.get("log_history", [])
            for entry in reversed(history):
                loss = entry.get("loss") or entry.get("eval_loss")
                if loss is not None:
                    return float(loss)
        except Exception:
            pass

    # 2. Check for custom metrics
    metrics_files = list(run_dir.glob("**/*_metrics.jsonl"))
    if metrics_files:
        latest_metrics = max(metrics_files, key=lambda p: p.stat().st_mtime)
        try:
            lines = latest_metrics.read_text().strip().splitlines()
            if lines:
                last_row = json.loads(lines[-1])
                logs = last_row.get("logs", last_row)
                loss = logs.get("loss") or logs.get("eval_loss")
                if loss is None and len(lines) > 1:
                    prev_row = json.loads(lines[-2])
                    prev_logs = prev_row.get("logs", prev_row)
                    loss = prev_logs.get("loss")
                if loss is not None:
                    return float(loss)
        except Exception:
            pass
    return None


def _run_stage(stage, run_root: Path, extra_args, progress_path: Path, progress: dict, stop_at_loss: float = 0.05, min_improvement: float = 0.01, anchor_text: str = "", batch_size: int = 4, gradient_checkpointing: bool = True, elective_base: str = None):
    run_dir = run_root / f"{stage['name']}_{time.strftime('%Y%m%d_%H%M%S')}"
    
    # Handle anchor data (Experience Replay)
    if anchor_text:
        print(f"[INFO] Experience Replay: Mixing {len(anchor_text)} chars of anchor data from previous stages.")
        # We pass the anchor text via a temporary local file that train_neural_text_generator can load
        anchor_file = run_root / f"{stage['name']}_anchor.txt"
        anchor_file.write_text(anchor_text, encoding="utf-8")
        # Add to extra args
        if extra_args is None:
            extra_args = []
        # We'll use a new flag --anchor-data in the main training script
        extra_args.extend(["--anchor-data", str(anchor_file)])

    # Deep copy extra_args to avoid mutating original for future stages
    local_extra_args = list(extra_args) if extra_args else []

    load_from = None
    is_elective = stage.get("is_elective", False)
    if is_elective:
        print(f"[INFO] {stage['title']} is an ELECTIVE. Enabling LoRA.")
        if "--lora" not in local_extra_args:
            local_extra_args.append("--lora")
        
        # Handle elective base model
        base_to_use = elective_base
        if not base_to_use:
            # Find last completed NON-ELECTIVE stage
            last_base = None
            for s in reversed(progress.get("stages", [])):
                if not s.get("is_elective") and s.get("status") == "completed":
                    last_base = s.get("run_dir")
                    break
            if last_base:
                base_to_use = last_base
                print(f"[INFO] Using last completed base stage as foundation: {last_base}")
        
        if base_to_use:
            load_from = base_to_use
            local_extra_args.extend(["--adapter-name", stage["name"]])
    else:
        # Core Sequential Stage: Load foundation from previous stage (elective or core)
        if progress.get("stages"):
            # Find absolute last completed stage of any type
            last_completed = None
            for s in reversed(progress.get("stages", [])):
                if s.get("status") == "completed":
                    last_completed = s.get("run_dir")
                    break
            
            if last_completed:
                load_from = last_completed
                print(f"[INFO] Continuing from last completed stage: {load_from}")

    # Handle datasets (can be string or list)
    datasets = stage["dataset"]
    if isinstance(datasets, str):
        datasets = [datasets]

    cmd = [
        PYTHON_EXE,
        str(TRAIN_SCRIPT),
        "--plain-output",
        "--model-type",
        "transformer",
        "--source",
        "huggingface",
        "--epochs",
        str(stage["epochs"]),
        "--data-percentage",
        str(stage["data_pct"]),
        "--stop-at-loss",
        str(stop_at_loss),
        "--min-improvement",
        str(min_improvement),
        "--batch-size",
        str(batch_size),
    ]
    
    # Add all datasets
    cmd.extend(["--book-ids"] + datasets)

    if load_from:
        cmd.extend(["--continue-training", "--run-dir", str(load_from)])
        # Use explicit output-dir for electives so they don't overwrite the base
        cmd.extend(["--output-dir", str(run_dir)])
    else:
        cmd.extend(["--run-dir", str(run_dir)])
    
    if gradient_checkpointing:
        cmd.append("--gradient-checkpointing")

    if stage.get("is_dpo"):
        cmd.append("--dpo")
        
    if local_extra_args:
        cmd.extend(local_extra_args)
    print(f"[INFO] {stage['title']} | {stage['school']} | {stage['age']}")
    print(f"[INFO] Curriculum: {stage['dataset']}")
    if stage.get("auto_applied"):
        print(f"[INFO] Auto settings: epochs={stage['epochs']} data_pct={stage['data_pct']}")
    
    progress_stage = {
        "name": stage["name"],
        "title": stage["title"],
        "school": stage["school"],
        "age": stage["age"],
        "dataset": stage["dataset"],
        "epochs": stage["epochs"],
        "data_pct": stage["data_pct"],
        "is_elective": stage.get("is_elective", False),
        "status": "running",
        "started_at": _now_iso(),
        "run_dir": str(run_dir),
    }
    progress["current_stage"] = stage["name"]
    progress["current_stage_title"] = stage["title"]
    progress["current_school"] = stage["school"]
    progress["current_age"] = stage["age"]
    progress["status"] = "running"
    progress.setdefault("stages", [])
    progress["stages"].append(progress_stage)
    _write_progress(progress_path, progress)
    
    try:
        subprocess.run(cmd, check=True)
        # Extract loss after success
        loss = _extract_loss_from_run(run_dir)
        progress_stage["loss"] = loss
        progress_stage["status"] = "completed"
    except Exception as exc:
        progress_stage["status"] = "failed"
        progress_stage["completed_at"] = _now_iso()
        progress_stage["error"] = str(exc)
        progress["status"] = "failed"
        _write_progress(progress_path, progress)
        raise
        
    progress_stage["completed_at"] = _now_iso()
    _write_progress(progress_path, progress)
    print(f"[INFO] Completed {stage['title']}")

    if REPORT_SCRIPT.exists():
        try:
            report_out = run_root / "report_card.txt"
            subprocess.run(
                [
                    PYTHON_EXE,
                    str(REPORT_SCRIPT),
                    "--format",
                    "text",
                    "--grade-source",
                    "both",
                    "--text-output",
                    str(report_out),
                ],
                check=False,
            )
        except Exception:
            pass


def main():
    ap = argparse.ArgumentParser(description="Run curriculum-style training stages")
    ap.add_argument("--epochs", type=int, default=1, help="Epochs per stage (default: 1)")
    ap.add_argument("--data-percentage", type=float, default=0.2, help="Data percentage per stage (default: 0.2)")
    ap.add_argument("--use-wikitext", action="store_true", help="Use WikiText-103 instead of OpenWebText")
    ap.add_argument("--auto", action="store_true", help="Auto-tune epochs/data percentage per stage for pod runs")
    ap.add_argument("--stage-limit", type=int, default=0, help="Limit number of stages to run (0 = all)")
    ap.add_argument("--stages", help="Specific stage indices or names to run (e.g. 1,5,7 or logic,prose)")
    ap.add_argument("--list-stages", action="store_true", help="List all available curriculum stages and exit")
    ap.add_argument("--replay-pct", type=float, default=0.1, help="Percentage of anchor data to carry forward (0.0 to 1.0)")
    ap.add_argument("--stop-at-loss", type=float, default=0.05, help="Stop stage if loss falls below this value")
    ap.add_argument("--min-improvement", type=float, default=0.01, help="Min improvement to avoid plateau stop")
    ap.add_argument("--batch-size", type=int, default=4, help="Batch size for training stages (default: 4)")
    ap.add_argument("--gradient-checkpointing", action="store_false", dest="no_gradient_checkpointing", help="Disable gradient checkpointing")
    ap.add_argument("--smart-resume", action="store_true", help="Skip stages already acquired or retouch weak ones")
    ap.add_argument("--target-loss", type=float, default=0.05, help="Loss threshold for considering a stage acquired")
    ap.add_argument("--retouch-threshold", type=float, default=0.15, help="Loss threshold for triggering a retouch pass")
    ap.add_argument("--elective", help="Specific stage indices or names to run as LoRA electives (e.g. 6,7 or coding,alignment)")
    ap.add_argument("--elective-base", help="Manual path to a base model for electives (defaults to last non-elective stage output)")
    ap.add_argument("--run-root", default=str(REPO_ROOT / "mavaia_core" / "models" / "neural_text_generator" / "curriculum"))
    ap.add_argument("extra_args", nargs=argparse.REMAINDER, help="Extra args passed to train_neural_text_generator.py")

    args = ap.parse_args()
    
    if args.list_stages:
        stages = _stage_defs(1, 0.2, False)
        print("\nAvailable Curriculum Stages:")
        print("-" * 80)
        print(f"{'Idx':<5} {'Name':<25} {'Title':<30} {'Datasets'}")
        print("-" * 80)
        for i, s in enumerate(stages):
            ds = s["dataset"]
            if isinstance(ds, list):
                ds_str = ", ".join(ds)
            else:
                ds_str = str(ds)
            print(f"{i+1:<5} {s['name']:<25} {s['title']:<30} {ds_str}")
        print("-" * 80)
        return 0

    run_root = Path(args.run_root)
    run_root.mkdir(parents=True, exist_ok=True)

    stages = _stage_defs(args.epochs, args.data_percentage, args.use_wikitext)
    
    # Identify elective stages
    elective_indices = set()
    elective_names = set()
    if args.elective:
        for part in args.elective.split(","):
            part = part.strip()
            try:
                elective_indices.add(int(part))
            except ValueError:
                elective_names.add(part.lower())

    for i, s in enumerate(stages):
        is_elective = False
        if (i + 1) in elective_indices:
            is_elective = True
        else:
            for name in elective_names:
                if name in s["name"].lower() or name in s["title"].lower():
                    is_elective = True
                    break
        s["is_elective"] = is_elective

    if args.stages:
        selected_indices = []
        selected_names = []
        for part in args.stages.split(","):
            part = part.strip()
            if "-" in part:
                try:
                    start, end = part.split("-")
                    selected_indices.extend(range(int(start), int(end) + 1))
                except ValueError:
                    print(f"[WARN] Invalid range format: {part}. Skipping.")
            else:
                try:
                    # Try as integer (index)
                    val = int(part)
                    selected_indices.append(val)
                except ValueError:
                    # Treat as name
                    selected_names.append(part.lower())
        
        # Filter stages
        new_stages = []
        # Check indices (1-based)
        for idx in selected_indices:
            if 1 <= idx <= len(stages):
                new_stages.append(stages[idx-1])
            else:
                print(f"[WARN] Stage index {idx} out of range (max {len(stages)}). Skipping.")
        
        # Check names
        for name in selected_names:
            matched = False
            for s in stages:
                if name in s["name"].lower() or name in s["title"].lower():
                    if s not in new_stages:
                        new_stages.append(s)
                    matched = True
                    break
            if not matched:
                print(f"[WARN] Stage name '{name}' not found. Skipping.")
                
        stages = new_stages
        if not stages:
            print("[ERROR] No valid stages selected. Exiting.")
            return 1
        print(f"[INFO] Running selected stages: {', '.join([s['name'] for s in stages])}")
    elif args.stage_limit > 0:
        print(f"[INFO] Limiting curriculum to first {args.stage_limit} stages.")
        stages = stages[:args.stage_limit]
        
    if args.auto:
        for stage in stages:
            if stage["name"] == "common_knowledge":
                stage["dataset"] = "wikitext:wikitext-103-raw-v1"
            _auto_stage_overrides(stage)
    progress_path = run_root / "curriculum_progress.json"
    progress = _load_progress(progress_path)
    progress.setdefault("created_at", _now_iso())
    progress["status"] = "running"
    progress["stages"] = []
    progress["plan"] = [
        {
            "name": s["name"],
            "title": s["title"],
            "school": s["school"],
            "age": s["age"],
            "dataset": s["dataset"],
            "epochs": s["epochs"],
            "data_pct": s["data_pct"],
            "is_elective": s.get("is_elective", False),
        }
        for s in stages
    ]
    # To avoid re-importing heavy modules locally, we'll use a lightweight data loader
    # to grab samples for the next stage's anchor data.
    accumulated_anchor_text = ""
    
    policy = SmartResumePolicy(target_loss=args.target_loss, retouch_threshold=args.retouch_threshold)
    
    _write_progress(progress_path, progress)
    for stage in stages:
        if args.smart_resume:
            perf = _get_stage_performance(stage["name"], run_root)
            mode, data_scale, epoch_scale = policy.decide(perf)
            
            if mode == "skip":
                print(f"[INFO] Stage '{stage['title']}' acquired (Loss: {perf:.4f}). Skipping pass.")
                # Add a 'skipped' entry to progress so foundation loading can still find a 'completed' path if needed
                # We search for latest run_dir to point to it
                latest_dir = None
                stage_dirs = list(run_root.glob(f"{stage['name']}_*"))
                remote_sync_root = REPO_ROOT / "models" / "neural_text_generator_remote" / "curriculum"
                if remote_sync_root.exists():
                    stage_dirs.extend(list(remote_sync_root.glob(f"{stage['name']}_*")))
                
                if stage_dirs:
                    latest_dir = str(max(stage_dirs, key=lambda d: d.stat().st_mtime))

                progress.setdefault("stages", [])
                progress["stages"].append({
                    "name": stage["name"],
                    "title": stage["title"],
                    "status": "completed",
                    "reason": "skipped (already acquired)",
                    "loss": perf,
                    "run_dir": latest_dir,
                    "completed_at": _now_iso()
                })
                _write_progress(progress_path, progress)
                # Still accumulate anchor data for next stages if possible
                pass 
            elif mode == "retouch":
                orig_pct = stage["data_pct"]
                stage["data_pct"] *= data_scale
                print(f"[INFO] Stage '{stage['title']}' marginal (Loss: {perf:.4f}). Retouching with {stage['data_pct']*100:.1f}% data (was {orig_pct*100:.1f}%).")
                # We'll mark the progress entry later in _run_stage
        
        # If we didn't skip, run the stage
        if not args.smart_resume or mode != "skip":
            _run_stage(
                stage, 
                run_root, 
                args.extra_args, 
                progress_path, 
                progress, 
                stop_at_loss=args.stop_at_loss, 
                min_improvement=args.min_improvement,
                anchor_text=accumulated_anchor_text,
                batch_size=args.batch_size,
                gradient_checkpointing=not args.no_gradient_checkpointing,
                elective_base=args.elective_base
            )
        
        # Accumulate anchor data for the next stage (Experience Replay)
        if args.replay_pct > 0:
            try:
                # We'll grab a small slice of the current stage's cached text
                # Note: This runs on the local machine to prepare the next stage's anchor file
                datasets = stage["dataset"]
                if isinstance(datasets, str):
                    datasets = [datasets]
                
                for ds_id in datasets:
                    safe_filename = ds_id.replace('/', '_').replace(':', '_')
                    cache_file = REPO_ROOT / "mavaia_core" / "data" / "huggingface" / f"{safe_filename}.txt"
                    if cache_file.exists():
                        full_text = cache_file.read_text(encoding="utf-8")
                        # Take a random slice proportional to replay_pct
                        sample_size = int(len(full_text) * (args.replay_pct / (len(stages) * len(datasets))))
                        if sample_size > 0:
                            start_idx = random.randint(0, max(0, len(full_text) - sample_size))
                            anchor_sample = full_text[start_idx : start_idx + sample_size]
                            accumulated_anchor_text += "\n\n" + anchor_sample
                            print(f"[INFO] Added {len(anchor_sample)} chars from {ds_id} to Experience Replay buffer.")
            except Exception as e:
                print(f"[WARN] Could not capture anchor data for {stage['name']}: {e}")

    progress["status"] = "complete"
    _write_progress(progress_path, progress)

    if REPORT_SCRIPT.exists():
        try:
            report_out = run_root / "report_card.txt"
            subprocess.run(
                [
                    PYTHON_EXE,
                    str(REPORT_SCRIPT),
                    "--format",
                    "text",
                    "--grade-source",
                    "both",
                    "--text-output",
                    str(report_out),
                ],
                check=False,
            )
        except Exception:
            pass

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
