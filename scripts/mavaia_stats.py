#!/usr/bin/env python3
import os
import json
import time
import subprocess
import argparse
from pathlib import Path
from datetime import datetime

# Try to import rich
try:
    from rich.console import Console
    from rich.table import Table
    from rich.panel import Panel
    from rich.text import Text
    from rich.live import Live
    from rich.progress import Progress, SpinnerColumn, BarColumn, TextColumn
    from rich import box
    from rich.columns import Columns
    from rich.console import Group
    console = Console()
    HAS_RICH = True
except ImportError:
    HAS_RICH = False

def get_size_format(b, factor=1024, suffix="B"):
    for unit in ["", "K", "M", "G", "T", "P"]:
        if b < factor:
            return f"{b:.2f}{unit}{suffix}"
        b /= factor

def get_model_stats(model_dir: Path):
    stats = {"params": "Unknown", "params_raw": 0, "size": "Unknown", "type": "Unknown", "is_lora": False}
    
    if not model_dir.exists():
        return stats
        
    config_path = model_dir / "config.json"
    adapter_config_path = model_dir / "adapter_config.json"
    
    # Check if it's a LoRA adapter
    if adapter_config_path.exists():
        stats["is_lora"] = True
        try:
            with open(adapter_config_path, "r") as f:
                adapter_config = json.load(f)
                stats["type"] = f"LoRA ({adapter_config.get('base_model_name_or_path', 'Unknown').split('/')[-1]})"
                stats["lora_r"] = adapter_config.get("r", "Unknown")
                stats["lora_alpha"] = adapter_config.get("lora_alpha", "Unknown")
        except Exception:
            stats["type"] = "LoRA"
    
    if not config_path.exists() and not stats["is_lora"]:
        if (model_dir / "model" / "config.json").exists():
            config_path = model_dir / "model" / "config.json"
            model_dir = model_dir / "model"
            
    if config_path.exists():
        try:
            with open(config_path, "r") as f:
                config = json.load(f)
                if not stats["is_lora"]:
                    stats["type"] = config.get("model_type", "Unknown")
                
                # Try to get params from config if available
                total_params = 0
                if "n_params" in config:
                    total_params = config["n_params"]
                elif config.get("model_type") == "gpt2":
                    v = config.get("vocab_size", 50257)
                    e = config.get("n_embd", 768)
                    l = config.get("n_layer", 12)
                    total_params = (v * e) + (l * 12 * e * e)
                
                if total_params > 0:
                    stats["params_raw"] = total_params
                    if total_params >= 1e9:
                        stats["params"] = f"{total_params/1e9:.1f}B"
                    else:
                        stats["params"] = f"{total_params/1e6:.0f}M"
        except Exception:
            pass
            
    # Calculate size from all files in directory
    total_size = 0
    try:
        for f in model_dir.glob("*"):
            if f.is_file():
                total_size += f.stat().st_size
        if total_size > 0:
            stats["size"] = get_size_format(total_size)
    except Exception:
        pass
        
    return stats

def resolve_path(p_str, root, env_name):
    if not p_str: return None
    p = Path(p_str)
    if env_name == "Local":
        # Check multiple possible remote bases
        remote_bases = [
            "/workspace/mavaia/mavaia_core/models/neural_text_generator/curriculum",
            "/workspace/mavaia/mavaia_core/models/neural_text_generator/runs"
        ]
        for rb in remote_bases:
            if str(p).startswith(rb):
                rel = p.relative_to(rb)
                # Map to local remote-sync folders
                if "curriculum" in rb:
                    return root / "models" / "neural_text_generator_remote" / "curriculum" / rel
                else:
                    return root / "models" / "neural_text_generator_remote" / "training_data" / "models" / "runs" / rel
        
        # Also handle paths already inside the local repo but absolute from remote
        if str(p).startswith("/workspace/mavaia/"):
            return root / p.relative_to("/workspace/mavaia")
            
    return p

def generate_layout(root, env_name):
    # Detect curriculum path
    curriculum_dir = root / "mavaia_core" / "models" / "neural_text_generator" / "curriculum"
    if not curriculum_dir.exists():
        curriculum_dir = root / "models" / "neural_text_generator_remote" / "curriculum"
        
    progress_path = curriculum_dir / "curriculum_progress.json"
    if not progress_path.exists():
        # Try finding ANY curriculum_progress.json
        alt_path = root / "models" / "neural_text_generator_remote" / "training_data" / "models" / "curriculum" / "curriculum_progress.json"
        if alt_path.exists():
            progress_path = alt_path
        else:
            return Text(f"Error: Curriculum progress not found at {progress_path}", style="bold red")

    try:
        with open(progress_path, "r") as f:
            data = json.load(f)
    except Exception as e:
        return Text(f"Error reading progress: {e}", style="bold red")

    # PRE-SCAN MODELS FOR TOTAL PARAMS
    total_system_params = "Unknown"
    max_params_found = 0
    for stage in data.get("stages", []):
        p = resolve_path(stage.get("run_dir"), root, env_name)
        if not p or not p.exists(): continue
        
        # Check standard transformer and any adapters
        model_dirs = [p / "transformer"] + list(p.glob("adapter_*"))
        for mdir in model_dirs:
            if mdir.exists():
                s = get_model_stats(mdir)
                if s["params_raw"] > max_params_found:
                    max_params_found = s["params_raw"]
                    total_system_params = s["params"]

    # Header
    header = Panel(
        Text.from_markup(f"[bold magenta]MAVAIA INTELLIGENCE CORE[/bold magenta]\n[dim]Environment: {env_name}[/dim]"),
        box=box.DOUBLE, border_style="magenta"
    )

    # Summary Table
    summary = Table(show_header=False, box=box.SIMPLE)
    summary.add_row("Current Status", f"[bold][{'green' if data.get('status') == 'completed' else 'yellow'}]{data.get('status', 'Unknown').upper()}[/][/bold]")
    summary.add_row("Mental Age", f"[bold][cyan]{data.get('current_age')}[/][/bold]")
    summary.add_row("Education Level", f"[bold][blue]{data.get('current_school')}[/][/bold]")
    summary.add_row("Total Parameters", f"[bold][yellow]{total_system_params}[/][/bold]")
    summary.add_row("Last Updated", data.get("updated_at", "N/A"))
    
    plan = data.get("plan", [])
    stages_total = len(plan)
    stages_done = len([s for s in data.get("stages", []) if s.get("status") == "completed"])
    progress_pct = (stages_done / stages_total) * 100 if stages_total > 0 else 0
    progress_bar = f"[ {'#' * int(progress_pct/5)}{'.' * (20 - int(progress_pct/5))} ] {progress_pct:.1f}%"
    summary.add_row("Curriculum Progress", progress_bar)
    
    brain_panel = Panel(summary, title="[bold]Brain Overview[/bold]", border_style="cyan")

    # Stages Table
    stages_table = Table(title="Curriculum Stages", box=box.ROUNDED, header_style="bold magenta", expand=True)
    stages_table.add_column("Stage", style="dim", width=6)
    stages_table.add_column("Title", style="white")
    stages_table.add_column("Dataset", style="green")
    stages_table.add_column("Type", style="blue")
    stages_table.add_column("Status", justify="center")
    stages_table.add_column("Duration", justify="right")

    for i, stage in enumerate(data.get("stages", [])):
        status = stage.get('status', 'Unknown')
        if status == "completed": status_style = "green"
        elif status == "failed": status_style = "red"
        else: status_style = "yellow"
        
        duration = "N/A"
        if "started_at" in stage and "completed_at" in stage:
            try:
                start = datetime.fromisoformat(stage["started_at"].replace("Z", "+00:00"))
                end = datetime.fromisoformat(stage["completed_at"].replace("Z", "+00:00"))
                duration = f"{(end - start).total_seconds():.0f}s"
            except Exception: pass
            
        stage_type = "[bold yellow]Elective[/bold]" if stage.get("is_elective") else "Core"
        dataset = stage.get("dataset", "N/A")
        if isinstance(dataset, list):
            dataset = ", ".join(dataset)
            
        stages_table.add_row(str(i+1), stage.get("title"), dataset, stage_type, f"[{status_style}]{status}[/{status_style}]", duration)

    # Model Artifacts
    model_table = Table(title="Neural Artifacts (Models & LoRA Adapters)", box=box.ROUNDED, header_style="bold blue", expand=True)
    model_table.add_column("Stage Name", style="white")
    model_table.add_column("Artifact Type", style="dim")
    model_table.add_column("Params", justify="right", style="cyan")
    model_table.add_column("Disk Size", justify="right", style="yellow")
    model_table.add_column("Location", style="dim", no_wrap=True)

    found_models = False
    for stage in data.get("stages", []):
        p = resolve_path(stage.get("run_dir"), root, env_name)
        if not p or not p.exists(): continue
            
        # Check standard transformer and any adapters
        mdirs = [p / "transformer"] + list(p.glob("adapter_*"))
        for mdir in mdirs:
            if mdir.exists():
                found_models = True
                stats = get_model_stats(mdir)
                name_display = stage.get("name")
                if stats["is_lora"]:
                    name_display = f"[bold yellow]{name_display}[/bold yellow] (Adapter)"
                model_table.add_row(name_display, stats["type"], stats["params"], stats["size"], str(mdir.relative_to(root) if mdir.is_relative_to(root) else mdir))

    # Sentinel
    sentinel_events = []
    log_file = curriculum_dir / "report_card.txt"
    if log_file.exists():
        try:
            content = log_file.read_text()
            f = content.count('Loss floor reached')
            p = content.count('Plateau detected')
            sentinel_events.append(f"[bold green]{f}[/bold green] Early Exits (Floor)")
            sentinel_events.append(f"[bold yellow]{p}[/bold yellow] Early Exits (Plateau)")
        except Exception: pass
    
    sentinel_panel = Panel(Columns(sentinel_events) if sentinel_events else Text("No sentinel events recorded"), title="[bold]Sentinel Insights[/bold]", border_style="green")

    # Hardware
    hw_panel = None
    try:
        gpu_info = subprocess.run(["nvidia-smi", "--query-gpu=name,memory.used,memory.total", "--format=csv,noheader,nounits"], capture_output=True, text=True)
        if gpu_info.returncode == 0:
            hw_table = Table(show_header=True, box=box.SIMPLE, header_style="bold green")
            hw_table.add_column("GPU")
            hw_table.add_column("VRAM Usage")
            for line in gpu_info.stdout.strip().split("\n"):
                if "," in line:
                    parts = line.split(", ")
                    if len(parts) == 3:
                        name, used, total = parts
                        vram_pct = (int(used) / int(total)) * 100
                        hw_table.add_row(name, f"{used}/{total}MB ({vram_pct:.1f}%)")
            hw_panel = Panel(hw_table, title="[bold]Hardware[/bold]", border_style="green")
    except Exception: pass

    # Layout Assembly
    top_row = Columns([brain_panel, sentinel_panel] + ([hw_panel] if hw_panel else []), expand=True)
    return Group(header, top_row, stages_table, model_table if found_models else Text("No neural artifacts found in filesystem"))

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--live", action="store_true", help="Enable live dynamic updates")
    parser.add_argument("--interval", type=float, default=2.0, help="Refresh interval in seconds")
    args = parser.parse_args()

    if os.path.exists("/workspace/mavaia"):
        root, env_name = Path("/workspace/mavaia"), "RunPod (Remote)"
    else:
        root, env_name = Path(__file__).resolve().parent.parent, "Local"

    if args.live:
        with Live(generate_layout(root, env_name), refresh_per_second=1/args.interval, screen=True) as live:
            while True:
                try:
                    time.sleep(args.interval)
                    live.update(generate_layout(root, env_name))
                except KeyboardInterrupt:
                    break
    else:
        console.print(generate_layout(root, env_name))

if __name__ == "__main__":
    main()
