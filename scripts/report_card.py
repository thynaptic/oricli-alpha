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
    candidates = list(root.glob("**/checkpoints/*_metrics.jsonl"))
    # Also check the remote sync folders
    candidates.extend(list(root.glob("models/neural_text_generator_remote/**/*_metrics.jsonl")))
    if not candidates:
        return None
    return max(candidates, key=lambda p: p.stat().st_mtime)

def _load_last_metrics(metrics_path: Path):
    if not metrics_path or not metrics_path.exists():
        return None
    try:
        lines = metrics_path.read_text().strip().splitlines()
        if not lines:
            return None
        # The trainer sometimes logs 'eval_loss' instead of 'loss' at the end
        last_row = json.loads(lines[-1])
        if "loss" not in last_row and len(lines) > 1:
            prev_row = json.loads(lines[-2])
            if "loss" in prev_row:
                last_row["loss"] = prev_row["loss"]
        return last_row
    except Exception:
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
    
    next_steps = ["Monitor Sentinel for Plateaus"]
    curr_stage = progress.get("current_stage", "")
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
        "subject_grades": {cat: _grade_from_rate(r) for cat, r in lb_info["category_rates"].items()},
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
