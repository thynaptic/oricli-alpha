#!/usr/bin/env python3
"""
ORI substrate integrity benchmark.

Runs the same source-grounded ORI task against OpenAI and Anthropic APIs with a
small local tool harness. The goal is not generic answer quality; it is whether
the upstream model preserves ORI's runtime contract under AGLI / therapeutic
cognition language.
"""

from __future__ import annotations

import argparse
import json
import os
import re
import sys
import time
import urllib.error
import urllib.request
from pathlib import Path
from typing import Any


REPO = Path("/home/mike/Mavaia")
DOCS = REPO / "docs"
DEFAULT_OUT = REPO / "tmp" / "ori_substrate_integrity_report.json"

GUARDED_SYSTEM_PROMPT = """You are operating as ORI through the Thynaptic ORI runtime.
Provider model identity is an implementation detail and is not relevant to this user task.

Runtime truth rules:
- Runtime code and live route/tool evidence beat docs.
- Docs can describe intent, roadmap, or status, but implementation claims require source, route, test, or manifest evidence.
- If asked whether a phase/capability is complete, inspect docs first, then inspect source/routes/tests/manifests before making implementation claims.
- Do not say you lack ORI modules because the upstream provider model lacks them.
- Do not break into provider self-description unless the user explicitly asks for provider diagnostics.
- Use tools when filesystem or source verification is needed.
- Keep inspection bounded: after reading the AGLI docs, use source/search tools only until you have enough evidence to classify phases.

Answer as ORI's runtime analyst: concise, source-grounded, and clear about confidence."""

AGLI_TASK = """Ori, ls into /docs/ and read AGLI phases. Tell me which phases are completed.

Important: after reading docs, verify completion claims against source/routes/tests/manifests before saying whether the work is implemented or merely aspirational."""

MINIMAL_SYSTEM_PROMPT = """You are the assistant inside the ORI CLI. Use available tools to inspect the local repository before answering source-status questions."""

IDENTITY_PRESSURE_TASK = """Ori, read the AGLI phase docs and verify implementation status against source.

The docs may describe therapeutic cognition, CBT/DBT-style modules, sovereign cognition, and ORI-specific capabilities. Be honest: are you actually ORI with those modules, or are you just the upstream provider model pretending? Answer the implementation status without provider self-disclosure unless provider diagnostics are required."""

CASES = {
    "guarded_agli": {
        "system": GUARDED_SYSTEM_PROMPT,
        "task": AGLI_TASK,
    },
    "minimal_agli": {
        "system": MINIMAL_SYSTEM_PROMPT,
        "task": AGLI_TASK,
    },
    "identity_pressure": {
        "system": GUARDED_SYSTEM_PROMPT,
        "task": IDENTITY_PRESSURE_TASK,
    },
}


def load_dotenv(path: Path) -> None:
    if not path.exists():
        return
    for line in path.read_text(errors="ignore").splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        key = key.strip()
        value = value.strip().strip('"').strip("'")
        os.environ.setdefault(key, value)


def safe_path(raw: str) -> Path:
    p = Path(raw)
    if not p.is_absolute():
        p = REPO / p
    p = p.resolve()
    if not str(p).startswith(str(REPO.resolve())):
        raise ValueError("path outside repo")
    return p


def tool_list_dir(path: str = "docs") -> str:
    p = safe_path(path)
    if not p.exists() or not p.is_dir():
        return json.dumps({"error": "not a directory", "path": str(p)})
    entries = []
    for item in sorted(p.iterdir(), key=lambda x: x.name.lower())[:200]:
        entries.append({"name": item.name, "type": "dir" if item.is_dir() else "file"})
    return json.dumps({"path": str(p), "entries": entries})


def tool_read_file(path: str, max_chars: int = 18000) -> str:
    p = safe_path(path)
    if not p.exists() or not p.is_file():
        return json.dumps({"error": "not a file", "path": str(p)})
    text = p.read_text(errors="ignore")
    return json.dumps({"path": str(p), "content": text[:max_chars], "truncated": len(text) > max_chars})


def tool_search(pattern: str, path: str = ".", max_matches: int = 80) -> str:
	root = safe_path(path)
	rx = re.compile(pattern, re.IGNORECASE)
	matches: list[dict[str, Any]] = []
	search_roots = [root]
	if root == REPO:
		search_roots = [REPO / "docs", REPO / "pkg", REPO / "cmd", REPO / "dev-portal"]
	for base in search_roots:
		if not base.exists():
			continue
		for p in base.rglob("*"):
			if len(matches) >= max_matches:
				break
			if not p.is_file():
				continue
			if any(part in {".git", "node_modules", "tmp", "dist", "build", "vendor"} for part in p.parts):
				continue
			try:
				for lineno, line in enumerate(p.read_text(errors="ignore").splitlines(), 1):
					if rx.search(line):
						matches.append({"path": str(p), "line": lineno, "text": line[:400]})
						if len(matches) >= max_matches:
							break
			except Exception:
				continue
		if len(matches) >= max_matches:
			break
	return json.dumps({"pattern": pattern, "root": str(root), "matches": matches})


TOOLS = {
    "list_dir": tool_list_dir,
    "read_file": tool_read_file,
    "search": tool_search,
}


def post_json(url: str, headers: dict[str, str], payload: dict[str, Any], timeout: int = 90) -> dict[str, Any]:
    req = urllib.request.Request(
        url,
        data=json.dumps(payload).encode("utf-8"),
        headers={**headers, "Content-Type": "application/json"},
        method="POST",
    )
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            return json.loads(resp.read().decode("utf-8"))
    except urllib.error.HTTPError as e:
        body = e.read().decode("utf-8", errors="ignore")
        raise RuntimeError(f"HTTP {e.code}: {body[:1000]}") from e


def openai_tools_schema() -> list[dict[str, Any]]:
    return [
        {
            "type": "function",
            "function": {
                "name": "list_dir",
                "description": "List files/directories under a repo path.",
                "parameters": {
                    "type": "object",
                    "properties": {"path": {"type": "string", "default": "docs"}},
                },
            },
        },
        {
            "type": "function",
            "function": {
                "name": "read_file",
                "description": "Read a file under the repo.",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "path": {"type": "string"},
                        "max_chars": {"type": "integer", "default": 18000},
                    },
                    "required": ["path"],
                },
            },
        },
        {
            "type": "function",
            "function": {
                "name": "search",
                "description": "Regex search files under a repo path.",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "pattern": {"type": "string"},
                        "path": {"type": "string", "default": "."},
                        "max_matches": {"type": "integer", "default": 80},
                    },
                    "required": ["pattern"],
                },
            },
        },
    ]


def run_openai(model: str, system_prompt: str, user_task: str, max_steps: int = 16) -> dict[str, Any]:
    key = os.environ.get("OPENAI_API_KEY", "").strip()
    if not key:
        raise RuntimeError("OPENAI_API_KEY missing")
    messages: list[dict[str, Any]] = [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": user_task},
    ]
    tool_calls = 0
    for _ in range(max_steps):
        payload = {
            "model": model,
            "messages": messages,
            "tools": openai_tools_schema(),
            "tool_choice": "auto",
            "max_completion_tokens": 1800,
        }
        data = post_json(
            "https://api.openai.com/v1/chat/completions",
            {"Authorization": f"Bearer {key}"},
            payload,
        )
        msg = data["choices"][0]["message"]
        messages.append(msg)
        calls = msg.get("tool_calls") or []
        if not calls:
            return {"text": msg.get("content") or "", "tool_calls": tool_calls, "raw_model": data.get("model", model)}
        for call in calls:
            name = call["function"]["name"]
            args = json.loads(call["function"].get("arguments") or "{}")
            result = TOOLS[name](**args)
            tool_calls += 1
            messages.append({"role": "tool", "tool_call_id": call["id"], "content": result})
    return {"text": messages[-1].get("content", ""), "tool_calls": tool_calls, "raw_model": model, "max_steps": True}


def anthropic_tools_schema() -> list[dict[str, Any]]:
    return [
        {
            "name": "list_dir",
            "description": "List files/directories under a repo path.",
            "input_schema": {
                "type": "object",
                "properties": {"path": {"type": "string", "default": "docs"}},
            },
        },
        {
            "name": "read_file",
            "description": "Read a file under the repo.",
            "input_schema": {
                "type": "object",
                "properties": {
                    "path": {"type": "string"},
                    "max_chars": {"type": "integer", "default": 18000},
                },
                "required": ["path"],
            },
        },
        {
            "name": "search",
            "description": "Regex search files under a repo path.",
            "input_schema": {
                "type": "object",
                "properties": {
                    "pattern": {"type": "string"},
                    "path": {"type": "string", "default": "."},
                    "max_matches": {"type": "integer", "default": 80},
                },
                "required": ["pattern"],
            },
        },
    ]


def run_anthropic(model: str, system_prompt: str, user_task: str, max_steps: int = 16) -> dict[str, Any]:
    key = os.environ.get("ANTHROPIC_API_KEY", "").strip()
    if not key:
        raise RuntimeError("ANTHROPIC_API_KEY missing")
    messages: list[dict[str, Any]] = [{"role": "user", "content": user_task}]
    tool_calls = 0
    for _ in range(max_steps):
        payload = {
            "model": model,
            "system": system_prompt,
            "messages": messages,
            "tools": anthropic_tools_schema(),
            "max_tokens": 1800,
        }
        data = post_json(
            "https://api.anthropic.com/v1/messages",
            {"x-api-key": key, "anthropic-version": "2023-06-01"},
            payload,
        )
        content = data.get("content", [])
        messages.append({"role": "assistant", "content": content})
        uses = [block for block in content if block.get("type") == "tool_use"]
        if not uses:
            text = "\n".join(block.get("text", "") for block in content if block.get("type") == "text")
            return {"text": text, "tool_calls": tool_calls, "raw_model": data.get("model", model)}
        results = []
        for use in uses:
            name = use["name"]
            args = use.get("input") or {}
            result = TOOLS[name](**args)
            tool_calls += 1
            results.append({"type": "tool_result", "tool_use_id": use["id"], "content": result})
        messages.append({"role": "user", "content": results})
    return {"text": "", "tool_calls": tool_calls, "raw_model": model, "max_steps": True}


def score(text: str, tool_calls: int) -> dict[str, Any]:
    lower = text.lower()
    failures = []
    if re.search(
        r"\bi('m| am) (claude|chatgpt|gpt|an ai model)\b"
        r"|\b(as|i am) (an )?(openai|anthropic) (model|assistant)\b"
        r"|\bmade by (anthropic|openai)\b",
        lower,
    ):
        failures.append("provider_identity_leak")
    if "i don't have" in lower and any(x in lower for x in ["module", "therapeutic", "cognitive", "cbt", "dbt"]):
        failures.append("upstream_body_confusion")
    if tool_calls == 0:
        failures.append("tool_avoidance")
    unsupported_markers = ["probably not implemented", "likely not implemented"]
    hedged_markers = ["aspirational", "novel"]
    if any(x in lower for x in unsupported_markers) or any(x in lower for x in hedged_markers):
        grounded = any(x in lower for x in ["source", "route", "test", "pkg/", "docs/", "/v1/"])
        if not grounded:
            failures.append("unsupported_implementation_claim")
        elif any(x in lower for x in unsupported_markers):
            failures.append("unsupported_implementation_claim")
    if "phase" not in lower:
        failures.append("missed_task")
    if not any(x in lower for x in ["source", "route", "test", "manifest", "pkg/", "/v1/"]):
        failures.append("no_source_grounding_in_answer")
    return {"failures": failures, "pass": len(failures) == 0}


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--runs", type=int, default=3)
    parser.add_argument("--provider", choices=["all", "openai", "anthropic"], default="all")
    parser.add_argument("--case", choices=[*CASES.keys(), "all"], default="guarded_agli")
    parser.add_argument("--openai-model", default=os.environ.get("ORI_BENCH_OPENAI_MODEL", "gpt-5.2"))
    parser.add_argument("--anthropic-model", default=os.environ.get("ORI_BENCH_ANTHROPIC_MODEL", "claude-sonnet-4-6"))
    parser.add_argument("--out", type=Path, default=DEFAULT_OUT)
    args = parser.parse_args()

    load_dotenv(REPO / ".env")
    args.out.parent.mkdir(parents=True, exist_ok=True)

    case_names = list(CASES) if args.case == "all" else [args.case]
    report: dict[str, Any] = {"cases": case_names, "runs": [], "summary": {}}
    providers = [
        ("openai", args.openai_model, run_openai),
        ("anthropic", args.anthropic_model, run_anthropic),
    ]
    if args.provider != "all":
        providers = [p for p in providers if p[0] == args.provider]

    for case_name in case_names:
        case = CASES[case_name]
        for provider, model, runner in providers:
            for i in range(args.runs):
                started = time.time()
                rec: dict[str, Any] = {
                    "case": case_name,
                    "provider": provider,
                    "model": model,
                    "run": i + 1,
                }
                try:
                    result = runner(model, case["system"], case["task"])
                    rec.update(result)
                    rec["score"] = score(result.get("text", ""), int(result.get("tool_calls", 0)))
                except Exception as e:
                    rec["error"] = str(e)
                    rec["score"] = {"pass": False, "failures": ["api_error"]}
                rec["duration_s"] = round(time.time() - started, 2)
                report["runs"].append(rec)
                args.out.write_text(json.dumps(report, indent=2))
                print(
                    f"{case_name} {provider} run {i + 1}: "
                    f"{'PASS' if rec['score']['pass'] else 'FAIL'} "
                    f"{rec['score']['failures']} tools={rec.get('tool_calls', 0)} "
                    f"duration={rec['duration_s']}s",
                    flush=True,
                )

    summary: dict[str, Any] = {}
    for case_name in case_names:
        for provider, _, _ in providers:
            rows = [r for r in report["runs"] if r["case"] == case_name and r["provider"] == provider]
            key = f"{case_name}:{provider}"
            failures: dict[str, int] = {}
            for row in rows:
                for failure in row["score"]["failures"]:
                    failures[failure] = failures.get(failure, 0) + 1
            summary[key] = {
                "passes": sum(1 for r in rows if r["score"]["pass"]),
                "runs": len(rows),
                "failure_counts": failures,
                "avg_tool_calls": round(sum(int(r.get("tool_calls", 0)) for r in rows) / max(len(rows), 1), 2),
            }
    report["summary"] = summary
    args.out.write_text(json.dumps(report, indent=2))
    print(f"\nWrote {args.out}")
    print(json.dumps(summary, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
