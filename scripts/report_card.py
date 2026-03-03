import argparse
import json
import re
import os
import sys
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path

# Try to import rich for beautiful output
try:
    from rich.console import Console
    from rich.table import Table
    from rich.panel import Panel
    from rich.text import Text
    from rich.progress import Progress, BarColumn, TextColumn
    from rich.columns import Columns
    from rich.layout import Layout
    from rich import box
    USE_RICH = True
except ImportError:
    USE_RICH = False

REPO_ROOT = Path(__file__).resolve().parent.parent

def _now_iso():
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")

def _find_latest(patterns, root: Path):
    candidates = []
    for pattern in patterns:
        candidates.extend(root.glob(pattern))
    if not candidates:
        return None
    return max(candidates, key=lambda p: p.stat().st_mtime)

def _load_json(path: Path):
    if not path or not path.exists():
        return None
    try:
        return json.loads(path.read_text())
    except Exception:
        return None

def _grade_from_rate(rate):
    if rate is None: return "N/A"
    if rate >= 0.90: return "[bold green]A+[/bold green]"
    if rate >= 0.85: return "[green]A[/green]"
    if rate >= 0.75: return "[yellow]B+[/yellow]"
    if rate >= 0.70: return "[yellow]B[/yellow]"
    if rate >= 0.60: return "[orange3]C[/orange3]"
    return "[red]F[/red]"

def _format_rich_report(report):
    console = Console(record=True)
    
    # 1. Header Panel
    header = Panel(
        Text.from_markup(
            f"[bold magenta]MAVAIA COGNITIVE SYSTEM[/bold magenta]\n"
            f"[bold cyan]DIPLOMA OF CURRICULUM GRADUATION[/bold cyan]\n\n"
            f"Student: [white]{report['student']}[/white] | Date: {report['report_date']}"
        ),
        box=box.DOUBLE,
        border_style="magenta",
        padding=(1, 2)
    )
    
    # 2. Current Status Table
    status_table = Table(title="Current Track Progress", show_header=True, box=box.ROUNDED)
    status_table.add_column("Current Stage", style="cyan")
    status_table.add_column("School Level", style="green")
    status_table.add_column("Actual Age", style="yellow")
    status_table.add_column("Cognitive Age", style="bold magenta")
    
    status_table.add_row(
        report['stage_title'],
        report['school'],
        report['actual_age'],
        report['assumed_age']
    )

    # 3. Metrics Dashboard
    metrics_table = Table(title="Performance Metrics", box=box.SIMPLE)
    metrics_table.add_column("Metric", style="dim")
    metrics_table.add_column("Value", style="bold")
    metrics_table.add_column("Status", justify="right")
    
    metrics_table.add_row("Training Loss", report['training_loss'], report['training_loss_trend'])
    metrics_table.add_row("LiveBench Pass Rate", report['livebench_pass_rate'], report['livebench_grade'])
    metrics_table.add_row("Self-Confidence", report['self_confidence'], "✓" if float(report['self_confidence'].replace('N/A','0')) > 0.7 else "⚠")

    # 4. Subject Grades
    subject_table = Table(title="Subject Competency", box=box.MINIMAL)
    subject_table.add_column("Subject", style="cyan")
    subject_table.add_column("Grade", justify="center")
    
    if report["subject_grades"]:
        for name, grade in report["subject_grades"].items():
            subject_table.add_row(name.capitalize(), grade)
    else:
        subject_table.add_row("No benchmarks", "N/A")

    # 5. Gaps and Next Steps
    gaps_text = Text()
    if report["gaps"]:
        for gap in report["gaps"]:
            gaps_text.append(f"• {gap}\n", style="red")
    else:
        gaps_text.append("No critical gaps detected.", style="green")
        
    next_steps_text = Text()
    for step in report["next_steps"]:
        next_steps_text.append(f"→ {step}\n", style="cyan")

    # Layout Assembly
    console.print(header)
    console.print(status_table)
    console.print(Columns([metrics_table, subject_table]))
    
    console.print(Panel(gaps_text, title="Detected Cognitive Gaps", border_style="red"))
    console.print(Panel(next_steps_text, title="Recommended Next Steps", border_style="cyan"))
    
    return console.export_text() if not os.isatty(sys.stdout.fileno()) else ""

def _find_latest_training_metrics(root: Path):
    patterns = [
        "**/checkpoints/*_metrics.jsonl",
        "**/checkpoints/trainer_state.json",
        "**/checkpoints/training_metrics.csv",
        "models/neural_text_generator_remote/**/*_metrics.jsonl",
        "models/neural_text_generator_remote/**/trainer_state.json",
        "models/neural_text_generator_remote/**/training_metrics.csv"
    ]
    candidates = []
    for pattern in patterns:
        candidates.extend(list(root.glob(pattern)))
        
    if not candidates:
        return None
    return max(candidates, key=lambda p: p.stat().st_mtime)

def _load_last_metrics(metrics_path: Path):
    if not metrics_path or not metrics_path.exists():
        return None
    try:
        if metrics_path.suffix == ".jsonl":
            lines = metrics_path.read_text().strip().splitlines()
            if not lines:
                return None
            last_row = json.loads(lines[-1])
            # Handle nested 'logs' if present (RNN format)
            if "logs" in last_row:
                last_row = last_row["logs"]
            if "loss" not in last_row and len(lines) > 1:
                prev_row = json.loads(lines[-2])
                if "logs" in prev_row: prev_row = prev_row["logs"]
                if "loss" in prev_row:
                    last_row["loss"] = prev_row["loss"]
            return last_row
            
        elif metrics_path.name == "trainer_state.json":
            state_data = json.loads(metrics_path.read_text())
            history = state_data.get("log_history", [])
            for entry in reversed(history):
                if "loss" in entry or "eval_loss" in entry:
                    return {
                        "loss": entry.get("loss") or entry.get("eval_loss"),
                        "epoch": entry.get("epoch"),
                        "step": entry.get("step")
                    }
            return None
            
        elif metrics_path.suffix == ".csv":
            import csv
            with open(metrics_path, "r", encoding="utf-8") as f:
                reader = list(csv.DictReader(f))
                if not reader:
                    return None
                
                # Iterate backwards to find the last valid training row
                for row in reversed(reader):
                    # Skip summary rows (often have more columns or specific keys)
                    # A valid row must have 'loss' and it should be a reasonable float
                    try:
                        loss_val = row.get("loss") or row.get("eval_loss")
                        if loss_val is not None:
                            loss_float = float(loss_val)
                            # If loss is massive (like 34.0 when it was 0.18), it's likely a summary value (total loss?)
                            # but we'll take it if it's the only one. 
                            # However, if it has 'None' key (extra columns), it's definitely a summary.
                            if None in row: 
                                continue
                                
                            row["loss"] = loss_float
                            return row
                    except ValueError:
                        continue
                return None
    except Exception:
        return None
    return None

def _loss_trend(metrics_path: Path, max_points: int = 20):
    if not metrics_path or not metrics_path.exists():
        return "N/A"
    try:
        lines = metrics_path.read_text().strip().splitlines()
        vals = []
        for line in lines[-max_points:]:
            try:
                row = json.loads(line)
                loss = row.get("loss")
                if loss is not None: vals.append(float(loss))
            except Exception: continue
        if len(vals) < 2: return "Stable"
        delta = vals[-1] - vals[0]
        if delta < -0.05: return "[bold green]Improviing ↗[/bold green]"
        if delta > 0.05: return "[bold red]Degrading ↘[/bold red]"
        return "Stable →"
    except Exception:
        return "N/A"

def _summarize_livebench(livebench):
    if not livebench:
        return {"summary": None, "category_rates": {}, "gaps": []}
    summary = livebench.get("summary") or {}
    results = livebench.get("results") or []
    totals = defaultdict(int)
    passed = defaultdict(int)
    for item in results:
        rd = item.get("result_data") or {}
        cat = rd.get("livebench_category") or item.get("category")
        if not cat: continue
        totals[cat] += 1
        if item.get("status") == "passed": passed[cat] += 1
    category_rates = {cat: passed[cat]/totals[cat] for cat in totals if totals[cat]}
    gaps = [cat for cat, rate in category_rates.items() if rate < 0.5]
    return {"summary": summary, "category_rates": category_rates, "gaps": gaps}

def main():
    ap = argparse.ArgumentParser(description="Generate a Rich Report Card for Mavaia")
    ap.add_argument("--progress", default="")
    ap.add_argument("--format", choices=["text", "json", "rich"], default="rich")
    ap.add_argument("--output", default="", help="JSON output path")
    ap.add_argument("--text-output", default="", help="Text output path")
    ap.add_argument("--grade-source", choices=["local", "remote", "both"], default="both")
    args = ap.parse_args()

    # Data Discovery
    progress_path = None
    if args.progress:
        progress_path = Path(args.progress)
    else:
        progress_path = _find_latest(["**/curriculum_progress.json"], REPO_ROOT)
    
    progress = _load_json(progress_path) or {}
    
    metrics_path = _find_latest_training_metrics(REPO_ROOT)
    training_metrics = _load_last_metrics(metrics_path)
    
    livebench_path = _find_latest(["livebench_results_*.json"], REPO_ROOT)
    livebench = _load_json(livebench_path)
    
    mavaia_path = _find_latest(["mavaia_result.json"], REPO_ROOT)
    mavaia_result = _load_json(mavaia_path) or {}

    # Logic
    lb_info = _summarize_livebench(livebench)
    pass_rate = (lb_info["summary"] or {}).get("pass_rate")
    
    training_loss = training_metrics.get("loss") if training_metrics else "N/A"
    
    # Map curriculum stages to subjects for grading
    subject_map = {
        "tone_oh_dcft_gemini": "Tone",
        "logic_orca_math": "Logic",
        "prose_no_robots": "Prose",
        "capability_hotpot_qa": "Reasoning",
        "context_booksum": "Context",
        "knowledge_wikihop": "Knowledge",
        "coding_alpaca_python": "Coding",
        "alignment_dpo": "Alignment",
        "knowledge_world_dense": "World Knowledge"
    }
    
    # Initialize grades from benchmarks
    subject_grades = {}
    if lb_info["category_rates"]:
        # ONLY use benchmarks if they are newer than the livebench_results_*.json mtime 
        # (Actually we should check if they are relevant to the current curriculum state)
        for cat, r in lb_info["category_rates"].items():
            subject_grades[cat.capitalize()] = _grade_from_rate(r)
    
    # Check completed curriculum stages
    # If a stage was completed AFTER the last benchmark, we should show "Pending Bench"
    lb_mtime = livebench_path.stat().st_mtime if livebench_path else 0
    
    for s in progress.get("stages", []):
        s_name = s.get("name")
        s_status = s.get("status")
        s_mtime = datetime.fromisoformat(s.get("completed_at").replace("Z", "+00:00")).timestamp() if s.get("completed_at") else 0
        
        subject_name = subject_map.get(s_name)
        if not subject_name: continue
        
        if s_status == "completed":
            # If benchmark is missing OR older than completion, mark as pending
            if subject_name not in subject_grades or lb_mtime < s_mtime:
                subject_grades[subject_name] = "[yellow]Pending Bench[/yellow]"
        elif subject_name not in subject_grades:
            subject_grades[subject_name] = "[dim]Not Started[/dim]"

    # Map cognitive gaps to recommended datasets and curriculum stages
    gap_recommendations = {
        "reasoning": ("Stage 4: Capability", ["kitsdk/hotpot_qa"]),
        "coding": ("Stage 7: Coding", ["iamtarun/python_code_instructions_18k_alpaca", "m-a-p/CodeFeedback-Filtered-Instruction"]),
        "math": ("Stage 2: Logic", ["microsoft/orca-math-word-problems-200k"]),
        "knowledge": ("Stage 6: Knowledge", ["kitsdk/wiki_hop"]),
        "context": ("Stage 5: Context", ["kmfoda/booksum"]),
        "alignment": ("Stage 8: Alignment", ["Intel/orca_dpo_pairs"]),
    }

    next_steps = ["Monitor Sentinel for Plateaus"]
    
    # Dynamically inject recommendations based on gaps
    if lb_info["gaps"]:
        for gap in lb_info["gaps"]:
            gap_lower = gap.lower()
            if gap_lower in gap_recommendations:
                stage, datasets = gap_recommendations[gap_lower]
                next_steps.insert(0, f"Retouch {stage} using: {', '.join(datasets)}")
    
    curr_stage = progress.get("current_stage", "")
    if not next_steps or "Proceed" not in str(next_steps):
        if "alignment" in curr_stage or "knowledge_world" in curr_stage:
            next_steps.insert(0, "Proceed to Stage 9: Comprehensive World Knowledge")
        else:
            next_steps.insert(0, "Continue Curriculum Stage 4: Multi-hop Reasoning")
    
    report = {
        "report_date": _now_iso(),
        "student": "Mavaia",
        "stage_title": progress.get("current_stage_title", "General Training"),
        "school": progress.get("current_school", "Independent Study"),
        "actual_age": progress.get("current_age", "N/A"),
        "assumed_age": f"Age {progress.get('current_age', '??')}", # Placeholder for delta logic
        "livebench_pass_rate": f"{pass_rate*100:.1f}%" if pass_rate else "N/A",
        "livebench_grade": _grade_from_rate(pass_rate),
        "training_loss": f"{training_loss:.4f}" if isinstance(training_loss, float) else "N/A",
        "training_loss_trend": _loss_trend(metrics_path),
        "self_confidence": f"{mavaia_result.get('confidence', 0):.2f}",
        "subject_grades": subject_grades,
        "gaps": lb_info["gaps"],
        "next_steps": next_steps
    }

    text_report = ""
    if USE_RICH and args.format in ("rich", "text"):
        text_report = _format_rich_report(report)
    else:
        # Fallback to simple print if no rich
        text_report = f"Mavaia Report Card - {report['report_date']}\n"
        text_report += f"Loss: {report['training_loss']} | Trend: {report['training_loss_trend']}\n"
        print(text_report)

    if args.output:
        Path(args.output).write_text(json.dumps(report, indent=2))
    
    if args.text_output:
        Path(args.text_output).write_text(text_report)

    return 0

if __name__ == "__main__":
    sys.exit(main())
