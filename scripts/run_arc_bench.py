#!/usr/bin/env python3
"""
run_arc_bench.py — Oricli-Alpha ARC Benchmark Runner

Evaluates Oricli-Alpha against:
  - ARC-AGI  : Abstraction & Reasoning Corpus (Chollet) — 400 eval tasks, exact grid match
  - AI2-ARC  : Allen Institute science QA — Easy + Challenge, multiple choice accuracy

Modes:
  --mode local      Hit local Oricli API (localhost:8089) — full reasoning stack, small model
  --mode runpod     Spin up a RunPod vLLM pod (big model, raw inference, no Oricli stack)
  --mode compare    Run both sequentially and produce a side-by-side report

Usage:
  python3 scripts/run_arc_bench.py --suite all --mode local
  python3 scripts/run_arc_bench.py --suite arc-agi --mode runpod --runpod-model Qwen/Qwen2.5-32B-Instruct-AWQ
  python3 scripts/run_arc_bench.py --suite all --mode compare --limit 50
"""

import argparse
import json
import os
import sys
import time
import random
import re
import urllib.request
import urllib.error
from datetime import datetime, timezone

def _now() -> datetime:
    return datetime.now(timezone.utc)
from pathlib import Path
from typing import Any, Optional

# ── paths ──────────────────────────────────────────────────────────────────────
REPO_ROOT  = Path(__file__).resolve().parent.parent
CACHE_DIR  = REPO_ROOT / ".arc_cache"
RESULTS_DIR = REPO_ROOT / "arc_results"
CACHE_DIR.mkdir(exist_ok=True)
RESULTS_DIR.mkdir(exist_ok=True)

# Bootstrap venv if needed
VENV_PYTHON = REPO_ROOT / ".venv" / "bin" / "python3"
if VENV_PYTHON.exists() and sys.prefix != str((REPO_ROOT / ".venv").resolve()):
    os.execv(str(VENV_PYTHON), [str(VENV_PYTHON), str(Path(__file__).resolve())] + sys.argv[1:])

# ── optional rich ──────────────────────────────────────────────────────────────
try:
    from rich.console import Console
    from rich.table import Table
    from rich.panel import Panel
    from rich.progress import Progress, SpinnerColumn, BarColumn, TextColumn, MofNCompleteColumn
    from rich import box
    console = Console()
    USE_RICH = True
except ImportError:
    USE_RICH = False
    console = None

def cprint(msg: str, style: str = ""):
    if USE_RICH:
        console.print(msg, style=style)
    else:
        print(msg)

# ── constants ─────────────────────────────────────────────────────────────────
LOCAL_API    = "http://localhost:8089/v1/chat/completions"
ARC_AGI_BASE = "https://raw.githubusercontent.com/fchollet/ARC-AGI/master/data/evaluation/"
AI2_ARC_BASE = "https://datasets-server.huggingface.co/rows?dataset=allenai%2Fai2_arc&config={config}&split=test&offset={offset}&length=100"

RUNPOD_MODELS = {
    "32b": "Qwen/Qwen2.5-32B-Instruct-AWQ",
    "14b": "Qwen/Qwen2.5-14B-Instruct-AWQ",
    "7b":  "Qwen/Qwen2.5-7B-Instruct-AWQ",
}

# ARC-AGI eval task IDs (sample of 400 — fetched from index on first run)
ARC_AGI_INDEX_URL = "https://api.github.com/repos/fchollet/ARC-AGI/contents/data/evaluation"

# ── HTTP helpers ──────────────────────────────────────────────────────────────

def http_get(url: str, timeout: int = 30) -> Any:
    req = urllib.request.Request(url, headers={"User-Agent": "oricli-arc-bench/1.0"})
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return json.loads(r.read())

def http_post(url: str, payload: dict, timeout: int = 120, api_key: str = "") -> Any:
    data = json.dumps(payload).encode()
    headers = {"Content-Type": "application/json", "User-Agent": "oricli-arc-bench/1.0"}
    if api_key:
        headers["Authorization"] = f"Bearer {api_key}"
    req = urllib.request.Request(url, data=data, headers=headers, method="POST")
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return json.loads(r.read())

# ── dataset loaders ───────────────────────────────────────────────────────────

def load_arc_agi_tasks(limit: Optional[int] = None) -> list[dict]:
    """Download/cache ARC-AGI evaluation tasks."""
    index_cache = CACHE_DIR / "arc_agi_index.json"
    if not index_cache.exists():
        cprint("[cyan]Fetching ARC-AGI task index from GitHub...[/cyan]")
        try:
            entries = http_get(ARC_AGI_INDEX_URL, timeout=15)
            task_names = [e["name"] for e in entries if e["name"].endswith(".json")]
            index_cache.write_text(json.dumps(task_names))
        except Exception as e:
            cprint(f"[red]Failed to fetch index: {e}. Using cached list if available.[/red]")
            if not index_cache.exists():
                raise
    
    task_names = json.loads(index_cache.read_text())
    if limit:
        random.seed(42)
        task_names = random.sample(task_names, min(limit, len(task_names)))

    tasks = []
    tasks_cache = CACHE_DIR / "arc_agi_tasks"
    tasks_cache.mkdir(exist_ok=True)

    cprint(f"[cyan]Loading {len(task_names)} ARC-AGI tasks...[/cyan]")
    for name in task_names:
        cached = tasks_cache / name
        if cached.exists():
            task = json.loads(cached.read_text())
        else:
            url = ARC_AGI_BASE + name
            try:
                task = http_get(url, timeout=10)
                cached.write_text(json.dumps(task))
            except Exception as e:
                cprint(f"[yellow]  skip {name}: {e}[/yellow]")
                continue
        tasks.append({"id": name.replace(".json", ""), "task": task})

    return tasks


def load_ai2_arc(limit: Optional[int] = None) -> list[dict]:
    """Download/cache AI2-ARC Easy + Challenge test sets."""
    all_questions = []
    for config in ("ARC-Easy", "ARC-Challenge"):
        cache_file = CACHE_DIR / f"ai2_arc_{config}.json"
        if cache_file.exists():
            questions = json.loads(cache_file.read_text())
        else:
            cprint(f"[cyan]Downloading AI2-ARC {config}...[/cyan]")
            questions = []
            offset = 0
            while True:
                url = AI2_ARC_BASE.format(config=config.replace("-", "%2F").replace("/", "%2F"), offset=offset)
                # Correct URL encoding for config
                url = f"https://datasets-server.huggingface.co/rows?dataset=allenai%2Fai2_arc&config={config}&split=test&offset={offset}&length=100"
                try:
                    data = http_get(url, timeout=20)
                    rows = data.get("rows", [])
                    if not rows:
                        break
                    for row in rows:
                        r = row["row"]
                        questions.append({
                            "id": r["id"],
                            "question": r["question"],
                            "choices": r["choices"],
                            "answer": r["answerKey"],
                            "config": config,
                        })
                    offset += 100
                    if len(rows) < 100:
                        break
                except Exception as e:
                    cprint(f"[yellow]  HF API error at offset {offset}: {e}[/yellow]")
                    break
            cache_file.write_text(json.dumps(questions))

        all_questions.extend(questions)

    if limit:
        random.seed(42)
        all_questions = random.sample(all_questions, min(limit, len(all_questions)))

    return all_questions

# ── prompt builders ───────────────────────────────────────────────────────────

def build_arc_agi_prompt(task: dict) -> str:
    lines = ["You are solving an ARC-AGI pattern recognition task.",
             "Study the training examples to discover the transformation rule.",
             "Then apply that rule to produce the test output grid.",
             "",
             "=== TRAINING EXAMPLES ==="]
    for i, ex in enumerate(task.get("train", []), 1):
        lines.append(f"\nExample {i}:")
        lines.append(f"  Input:  {json.dumps(ex['input'])}")
        lines.append(f"  Output: {json.dumps(ex['output'])}")
    lines += [
        "",
        "=== TEST INPUT ===",
        json.dumps(task["test"][0]["input"]),
        "",
        "Respond with ONLY the output grid as a valid JSON array of arrays.",
        "No explanation. No markdown. Just the JSON.",
    ]
    return "\n".join(lines)


def build_ai2_arc_prompt(q: dict) -> str:
    labels = q["choices"]["label"]
    texts  = q["choices"]["text"]
    options = "\n".join(f"  {l}: {t}" for l, t in zip(labels, texts))
    return (
        f"Question: {q['question']}\n\n"
        f"Options:\n{options}\n\n"
        "Respond with ONLY the letter of the correct answer (A, B, C, or D). No explanation."
    )

# ── inference ─────────────────────────────────────────────────────────────────

def call_api(prompt: str, api_url: str, model: str, api_key: str = "", temperature: float = 0.0) -> str:
    payload = {
        "model": model,
        "messages": [{"role": "user", "content": prompt}],
        "temperature": temperature,
        "max_tokens": 512,
        "stream": True,
    }
    data = json.dumps(payload).encode()
    headers = {"Content-Type": "application/json", "User-Agent": "oricli-arc-bench/1.0"}
    if api_key:
        headers["Authorization"] = f"Bearer {api_key}"
    try:
        req = urllib.request.Request(api_url, data=data, headers=headers, method="POST")
        content_parts = []
        with urllib.request.urlopen(req, timeout=120) as resp:
            for raw_line in resp:
                line = raw_line.decode("utf-8", errors="replace").strip()
                if not line.startswith("data:"):
                    continue
                payload_str = line[5:].strip()
                if payload_str == "[DONE]":
                    break
                try:
                    chunk = json.loads(payload_str)
                    delta = chunk.get("choices", [{}])[0].get("delta", {})
                    if delta.get("content"):
                        content_parts.append(delta["content"])
                except Exception:
                    continue
        return "".join(content_parts).strip()
    except Exception as e:
        return f"ERROR: {e}"

# ── scoring ───────────────────────────────────────────────────────────────────

def score_arc_agi(response: str, expected: list) -> tuple[bool, str]:
    """Exact grid match after stripping markdown fences."""
    text = response.strip()
    # strip ```json ... ``` fences
    text = re.sub(r"```[a-z]*\n?", "", text).strip()
    try:
        predicted = json.loads(text)
        correct = predicted == expected
        return correct, json.dumps(predicted)
    except Exception:
        # Try to extract the first JSON array from the response
        match = re.search(r"(\[\s*\[.*?\]\s*\])", text, re.DOTALL)
        if match:
            try:
                predicted = json.loads(match.group(1))
                return predicted == expected, json.dumps(predicted)
            except Exception:
                pass
        return False, f"PARSE_FAIL: {text[:80]}"


def score_ai2_arc(response: str, expected: str) -> tuple[bool, str]:
    """Extract first capital letter A-D from response."""
    text = response.strip()
    match = re.search(r"\b([A-D])\b", text)
    if match:
        predicted = match.group(1)
        return predicted == expected, predicted
    # fallback: first char
    if text and text[0] in "ABCD":
        return text[0] == expected, text[0]
    return False, f"PARSE_FAIL: {text[:40]}"

# ── runners ───────────────────────────────────────────────────────────────────

def run_arc_agi_bench(tasks: list, api_url: str, model: str, api_key: str, label: str) -> dict:
    results = []
    correct = 0

    def _run():
        nonlocal correct
        for i, item in enumerate(tasks):
            task_id = item["id"]
            task    = item["task"]
            expected = task["test"][0].get("output")
            if expected is None:
                continue

            prompt   = build_arc_agi_prompt(task)
            response = call_api(prompt, api_url, model, api_key)
            ok, predicted = score_arc_agi(response, expected)
            if ok:
                correct += 1

            results.append({
                "id": task_id,
                "correct": ok,
                "predicted": predicted,
                "expected": json.dumps(expected),
            })

            if USE_RICH:
                progress.update(task_id=task_prog, advance=1,
                                 description=f"[cyan]ARC-AGI[/] {i+1}/{len(tasks)} ✓{correct}")
            elif (i + 1) % 10 == 0:
                pct = correct / (i + 1) * 100
                print(f"  [{i+1}/{len(tasks)}] running acc: {pct:.1f}%")

    if USE_RICH:
        with Progress(SpinnerColumn(), TextColumn("{task.description}"),
                      BarColumn(), MofNCompleteColumn(), console=console) as progress:
            task_prog = progress.add_task(f"[cyan]ARC-AGI ({label})", total=len(tasks))
            _run()
    else:
        print(f"\n[ARC-AGI] {label} — {len(tasks)} tasks")
        _run()

    accuracy = correct / len(results) * 100 if results else 0
    return {"suite": "arc-agi", "label": label, "model": model,
            "total": len(results), "correct": correct, "accuracy": accuracy,
            "results": results}


def run_ai2_arc_bench(questions: list, api_url: str, model: str, api_key: str, label: str) -> dict:
    results     = []
    by_config: dict[str, dict] = {}
    correct     = 0

    def _run():
        nonlocal correct
        for i, q in enumerate(questions):
            config   = q["config"]
            prompt   = build_ai2_arc_prompt(q)
            response = call_api(prompt, api_url, model, api_key)
            ok, predicted = score_ai2_arc(response, q["answer"])
            if ok:
                correct += 1

            by_config.setdefault(config, {"correct": 0, "total": 0})
            by_config[config]["total"] += 1
            if ok:
                by_config[config]["correct"] += 1

            results.append({
                "id": q["id"],
                "config": config,
                "question": q["question"][:80],
                "correct": ok,
                "predicted": predicted,
                "expected": q["answer"],
            })

            if USE_RICH:
                progress.update(task_id=task_prog, advance=1,
                                 description=f"[green]AI2-ARC[/] {i+1}/{len(questions)} ✓{correct}")
            elif (i + 1) % 20 == 0:
                pct = correct / (i + 1) * 100
                print(f"  [{i+1}/{len(questions)}] running acc: {pct:.1f}%")

    if USE_RICH:
        with Progress(SpinnerColumn(), TextColumn("{task.description}"),
                      BarColumn(), MofNCompleteColumn(), console=console) as progress:
            task_prog = progress.add_task(f"[green]AI2-ARC ({label})", total=len(questions))
            _run()
    else:
        print(f"\n[AI2-ARC] {label} — {len(questions)} questions")
        _run()

    accuracy = correct / len(results) * 100 if results else 0
    return {"suite": "ai2-arc", "label": label, "model": model,
            "total": len(results), "correct": correct, "accuracy": accuracy,
            "by_config": {k: {**v, "accuracy": v["correct"] / v["total"] * 100} for k, v in by_config.items()},
            "results": results}

# ── RunPod helpers ────────────────────────────────────────────────────────────

def start_runpod_pod(model_id: str, api_key: str) -> tuple[str, str]:
    """
    Spin up a RunPod vLLM pod via the Oricli API's RunPod escalation.
    Returns (pod_id, endpoint_url).
    """
    cprint(f"[yellow]⚡ Spinning up RunPod pod: {model_id}[/yellow]")
    payload = {
        "model_id": model_id,
        "gpu_vram_gb": 24,
        "wait": True,
    }
    try:
        resp = http_post("http://localhost:8089/v1/runpod/primary/start", payload,
                         timeout=900, api_key=api_key)
        pod_id       = resp.get("pod_id", "")
        endpoint_url = resp.get("endpoint_url", "")
        cprint(f"[green]✓ Pod ready: {pod_id}[/green]")
        cprint(f"  Endpoint: {endpoint_url}")
        return pod_id, endpoint_url
    except Exception as e:
        cprint(f"[red]RunPod start failed: {e}[/red]")
        raise


def stop_runpod_pod(pod_id: str, api_key: str):
    try:
        http_post("http://localhost:8089/v1/runpod/primary/stop",
                  {"pod_id": pod_id}, timeout=30, api_key=api_key)
        cprint(f"[yellow]Pod {pod_id} stopped.[/yellow]")
    except Exception as e:
        cprint(f"[yellow]Warning: failed to stop pod {pod_id}: {e}[/yellow]")

# ── report generator ──────────────────────────────────────────────────────────

REPORT_CSS = """
body { font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', monospace;
       background: #0d0d0d; color: #e0e0e0; max-width: 960px; margin: 40px auto; padding: 20px; }
h1 { color: #E5004C; font-size: 1.8em; }
h2 { color: #aaa; border-bottom: 1px solid #333; padding-bottom: 8px; }
h3 { color: #E5004C; }
.card { background: #1a1a1a; border: 1px solid #2a2a2a; border-radius: 8px;
        padding: 20px; margin: 16px 0; }
.score { font-size: 2.5em; font-weight: bold; color: #E5004C; }
.score.good { color: #22c55e; }
.score.ok   { color: #f59e0b; }
.score.poor { color: #ef4444; }
table { width: 100%; border-collapse: collapse; font-size: 0.85em; }
th { background: #222; color: #aaa; padding: 8px 12px; text-align: left; }
td { padding: 6px 12px; border-bottom: 1px solid #1e1e1e; }
tr:hover td { background: #1e1e1e; }
.badge-correct { color: #22c55e; font-weight: bold; }
.badge-wrong   { color: #ef4444; }
.meta { color: #666; font-size: 0.8em; margin-top: 4px; }
.leaderboard { background: #111; border: 1px solid #333; border-radius: 6px;
               padding: 16px; margin: 12px 0; }
"""

def color_score(pct: float) -> str:
    if pct >= 70: return "good"
    if pct >= 40: return "ok"
    return "poor"

def generate_html_report(all_results: list[dict], run_id: str) -> str:
    ts = _now().strftime("%Y-%m-%d %H:%M UTC")

    def suite_card(r: dict) -> str:
        pct = r["accuracy"]
        cls = color_score(pct)
        detail = ""
        if "by_config" in r:
            rows = "".join(
                f"<tr><td>{cfg}</td><td>{v['correct']}/{v['total']}</td>"
                f"<td class='score {color_score(v['accuracy'])}' style='font-size:1em'>{v['accuracy']:.1f}%</td></tr>"
                for cfg, v in r["by_config"].items()
            )
            detail = f"<table><tr><th>Subset</th><th>Correct</th><th>Accuracy</th></tr>{rows}</table>"

        # Public SOTA reference
        sota = ""
        if r["suite"] == "arc-agi":
            sota = "<div class='leaderboard'>📊 <b>Public SOTA (ARC-AGI-1):</b> ~85% (o3-high) · ~75% (GPT-4o) · ~60% (Claude 3.5 Sonnet)</div>"
        elif r["suite"] == "ai2-arc":
            sota = "<div class='leaderboard'>📊 <b>Public SOTA (AI2-ARC Challenge):</b> ~98% (GPT-4o) · ~95% (Claude 3 Opus)</div>"

        return f"""
<div class='card'>
  <h3>{r['suite'].upper()} — {r['label']}</h3>
  <div class='meta'>Model: {r['model']} · {r['correct']}/{r['total']} correct</div>
  <div class='score {cls}'>{pct:.1f}%</div>
  {sota}
  {detail}
</div>"""

    cards = "\n".join(suite_card(r) for r in all_results)

    # Compare table if we have multiple runs of the same suite
    compare = ""
    by_suite: dict[str, list] = {}
    for r in all_results:
        by_suite.setdefault(r["suite"], []).append(r)
    for suite, runs in by_suite.items():
        if len(runs) > 1:
            rows = "".join(
                f"<tr><td>{r['label']}</td><td>{r['model']}</td>"
                f"<td class='score {color_score(r['accuracy'])}' style='font-size:1em'>{r['accuracy']:.1f}%</td>"
                f"<td>{r['correct']}/{r['total']}</td></tr>"
                for r in runs
            )
            compare += f"""
<div class='card'>
  <h3>⚡ {suite.upper()} — Mode Comparison</h3>
  <table><tr><th>Mode</th><th>Model</th><th>Accuracy</th><th>Correct</th></tr>{rows}</table>
  <div class='meta' style='margin-top:12px'>Delta = reasoning stack vs raw model size advantage</div>
</div>"""

    return f"""<!DOCTYPE html>
<html lang="en">
<head><meta charset="UTF-8"><title>Oricli-Alpha ARC Benchmark — {run_id}</title>
<style>{REPORT_CSS}</style></head>
<body>
<h1>🧠 Oricli-Alpha ARC Benchmark</h1>
<div class='meta'>Run ID: {run_id} · {ts}</div>
<h2>Results</h2>
{cards}
{compare}
<h2>About This Benchmark</h2>
<div class='card'>
  <p><b>ARC-AGI</b> (Abstraction & Reasoning Corpus): Grid-based pattern recognition tasks designed to
  resist memorization. Each task requires discovering a novel rule from 3-5 training examples and applying
  it to a test input. Scored by exact grid match only.</p>
  <p><b>AI2-ARC</b> (Allen Institute): Science multiple-choice questions split into Easy and Challenge sets.
  Challenge questions specifically require multi-step reasoning and cannot be answered by simple retrieval.</p>
  <p><b>Local mode</b>: Oricli-Alpha full stack (MCTS, CoT, safety, memory) with Ollama small models.<br>
  <b>RunPod mode</b>: Large vLLM model (AWQ quantized), direct inference, no Oricli reasoning stack.<br>
  The gap between the two isolates the value of the reasoning architecture vs. raw model scale.</p>
</div>
</body></html>"""

# ── main ──────────────────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(description="Oricli-Alpha ARC Benchmark Runner")
    parser.add_argument("--suite",   choices=["arc-agi", "ai2-arc", "all"], default="all")
    parser.add_argument("--mode",    choices=["local", "runpod", "compare"],  default="local")
    parser.add_argument("--limit",   type=int, default=None,
                        help="Cap tasks per suite (default: all). Use 50 for a quick run.")
    parser.add_argument("--runpod-model", default="14b",
                        help="RunPod model key: 7b | 14b | 32b  (default: 14b)")
    parser.add_argument("--runpod-url", default=None,
                        help="Use an already-running RunPod vLLM endpoint instead of spinning one up")
    parser.add_argument("--local-model", default="qwen3:1.7b",
                        help="Model name to pass to local Oricli API (default: qwen3:1.7b)")
    # Auto-load .env so the key is available without manual export
    _env_file = REPO_ROOT / ".env"
    if _env_file.exists() and not os.environ.get("SOVEREIGN_EXEC_KEY"):
        for _line in _env_file.read_text().splitlines():
            if "=" in _line and not _line.startswith("#"):
                _k, _, _v = _line.partition("=")
                os.environ.setdefault(_k.strip(), _v.strip())

    parser.add_argument("--api-key",
                        default=os.environ.get("ORICLI_SEED_API_KEY") or os.environ.get("SOVEREIGN_EXEC_KEY", ""),
                        help="Oricli API key (auto-loaded from ORICLI_SEED_API_KEY or SOVEREIGN_EXEC_KEY)")
    parser.add_argument("--seed", type=int, default=42)
    args = parser.parse_args()

    random.seed(args.seed)

    run_id = _now().strftime("%Y%m%d_%H%M%S") + f"_{args.mode}_{args.suite}"
    out_dir = RESULTS_DIR / run_id
    out_dir.mkdir(exist_ok=True)

    if USE_RICH:
        console.print(Panel(
            f"[bold #E5004C]Oricli-Alpha ARC Benchmark[/]\n"
            f"Suite: [cyan]{args.suite}[/]  Mode: [yellow]{args.mode}[/]  "
            f"Limit: [cyan]{args.limit or 'all'}[/]  Seed: {args.seed}",
            border_style="dim"
        ))
    else:
        print(f"\n=== Oricli-Alpha ARC Benchmark ===")
        print(f"Suite: {args.suite}  Mode: {args.mode}  Limit: {args.limit or 'all'}")

    # ── load datasets ──────────────────────────────────────────────────────────
    arc_agi_tasks = []
    ai2_arc_qs    = []

    if args.suite in ("arc-agi", "all"):
        arc_agi_tasks = load_arc_agi_tasks(limit=args.limit)
        cprint(f"[green]✓ Loaded {len(arc_agi_tasks)} ARC-AGI tasks[/green]")

    if args.suite in ("ai2-arc", "all"):
        ai2_arc_qs = load_ai2_arc(limit=args.limit)
        cprint(f"[green]✓ Loaded {len(ai2_arc_qs)} AI2-ARC questions[/green]")

    all_results: list[dict] = []
    pod_id = None

    # ── determine run configs ─────────────────────────────────────────────────
    run_configs = []

    if args.mode in ("local", "compare"):
        run_configs.append({
            "label":   "Local (Oricli Stack)",
            "api_url": LOCAL_API,
            "model":   args.local_model,
            "api_key": args.api_key,
        })

    if args.mode in ("runpod", "compare"):
        model_id = RUNPOD_MODELS.get(args.runpod_model, args.runpod_model)
        endpoint_url = args.runpod_url

        if not endpoint_url:
            pod_id, endpoint_url = start_runpod_pod(model_id, args.api_key)

        runpod_api_url = endpoint_url.rstrip("/") + "/chat/completions"
        run_configs.append({
            "label":   f"RunPod ({model_id.split('/')[-1]})",
            "api_url": runpod_api_url,
            "model":   model_id,
            "api_key": os.environ.get("RUNPOD_API_KEY", ""),
        })

    # ── run benchmarks ─────────────────────────────────────────────────────────
    try:
        for cfg in run_configs:
            cprint(f"\n[bold]▶ Running: {cfg['label']}[/bold]")

            if arc_agi_tasks:
                t0 = time.time()
                r = run_arc_agi_bench(arc_agi_tasks, cfg["api_url"], cfg["model"],
                                      cfg["api_key"], cfg["label"])
                r["elapsed_s"] = round(time.time() - t0, 1)
                all_results.append(r)
                cprint(f"  ARC-AGI  accuracy: [bold]{r['accuracy']:.1f}%[/bold] ({r['correct']}/{r['total']}) "
                       f"in {r['elapsed_s']}s")

            if ai2_arc_qs:
                t0 = time.time()
                r = run_ai2_arc_bench(ai2_arc_qs, cfg["api_url"], cfg["model"],
                                      cfg["api_key"], cfg["label"])
                r["elapsed_s"] = round(time.time() - t0, 1)
                all_results.append(r)
                cprint(f"  AI2-ARC  accuracy: [bold]{r['accuracy']:.1f}%[/bold] ({r['correct']}/{r['total']}) "
                       f"in {r['elapsed_s']}s")
                for config, v in r["by_config"].items():
                    cprint(f"    {config}: {v['accuracy']:.1f}% ({v['correct']}/{v['total']})")

    finally:
        if pod_id:
            stop_runpod_pod(pod_id, args.api_key)

    # ── save outputs ───────────────────────────────────────────────────────────
    json_path = out_dir / "results.json"
    html_path = out_dir / "report.html"

    json_path.write_text(json.dumps({
        "run_id": run_id,
        "timestamp": _now().isoformat(),
        "args": vars(args),
        "results": all_results,
    }, indent=2))

    html_path.write_text(generate_html_report(all_results, run_id))

    cprint(f"\n[bold green]✓ Done.[/bold green]")
    cprint(f"  JSON:   {json_path}")
    cprint(f"  Report: {html_path}")

    # ── final summary table ────────────────────────────────────────────────────
    if USE_RICH:
        t = Table(title="Final Scores", box=box.SIMPLE_HEAVY, style="dim")
        t.add_column("Suite",    style="cyan")
        t.add_column("Mode",     style="yellow")
        t.add_column("Model",    style="dim")
        t.add_column("Accuracy", justify="right", style="bold")
        t.add_column("Correct",  justify="right")
        for r in all_results:
            t.add_row(r["suite"], r["label"], r["model"],
                      f"{r['accuracy']:.1f}%", f"{r['correct']}/{r['total']}")
        console.print(t)
    else:
        print("\n=== FINAL SCORES ===")
        for r in all_results:
            print(f"  {r['suite']:12s} | {r['label']:35s} | {r['accuracy']:.1f}% ({r['correct']}/{r['total']})")


if __name__ == "__main__":
    main()
