#!/usr/bin/env python3
"""
ORI Intelligence Benchmark
Fires each question at ORI (full pipeline) AND raw Ollama (no pipeline).
Saves results JSON for judge scoring.
"""

import json
import sys
import time
import argparse
import urllib.request
import urllib.error
from datetime import datetime
from pathlib import Path

ORI_BASE      = "http://localhost:8089"
ORI_API_KEY   = "glm.Qbtofkny.F5pTIVYghj-mLSwAtPRGDau1q7k2w5DO"
OLLAMA_BASE   = "http://localhost:11434"
CHAT_MODEL    = "gemma3:1b"
CODE_MODEL    = "qwen3:1.7b"

SCRIPT_DIR = Path(__file__).parent
QUESTIONS  = SCRIPT_DIR / "questions.json"
RESULTS_DIR = Path(__file__).parent.parent / "arc_results"


def post(url: str, payload: dict, headers: dict, timeout: int = 120) -> tuple[dict | None, float, str | None]:
    body = json.dumps(payload).encode()
    req  = urllib.request.Request(url, data=body, headers=headers, method="POST")
    t0   = time.time()
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            elapsed = time.time() - t0
            return json.loads(resp.read()), elapsed, None
    except urllib.error.HTTPError as e:
        return None, time.time() - t0, f"HTTP {e.code}: {e.read().decode()[:200]}"
    except Exception as e:
        return None, time.time() - t0, str(e)


def query_ori(question: str, category: str) -> tuple[str, float, str | None]:
    url  = f"{ORI_BASE}/v1/chat/completions"
    hdrs = {"Content-Type": "application/json", "Authorization": f"Bearer {ORI_API_KEY}"}
    payload = {
        "model": "oricli-alpha",
        "messages": [{"role": "user", "content": question}],
        "stream": False,
    }
    data, elapsed, err = post(url, payload, hdrs, timeout=180)
    if err or not data:
        return "", elapsed, err
    try:
        return data["choices"][0]["message"]["content"], elapsed, None
    except (KeyError, IndexError) as e:
        return "", elapsed, f"parse error: {e} | raw: {str(data)[:300]}"


def query_ollama_raw(question: str, category: str) -> tuple[str, float, str | None]:
    # Pick model based on category
    model = CODE_MODEL if category == "code" else CHAT_MODEL
    url   = f"{OLLAMA_BASE}/api/chat"
    hdrs  = {"Content-Type": "application/json"}
    payload = {
        "model": model,
        "messages": [{"role": "user", "content": question}],
        "stream": False,
    }
    data, elapsed, err = post(url, payload, hdrs, timeout=300)
    if err or not data:
        return "", elapsed, err
    try:
        return data["message"]["content"], elapsed, None
    except (KeyError, IndexError) as e:
        return "", elapsed, f"parse error: {e} | raw: {str(data)[:300]}"


def run(categories: list[str] | None = None, dry_run: bool = False):
    questions = json.loads(QUESTIONS.read_text())
    if categories:
        questions = [q for q in questions if q["category"] in categories]

    timestamp  = datetime.now().strftime("%Y%m%d_%H%M%S")
    out_dir    = RESULTS_DIR / f"intel_bench_{timestamp}"
    out_dir.mkdir(parents=True, exist_ok=True)

    results = []
    total   = len(questions)

    print(f"\n{'='*60}")
    print(f"  ORI Intelligence Benchmark  —  {total} questions")
    print(f"  ORI:       {ORI_BASE}")
    print(f"  Raw Ollama: {OLLAMA_BASE}  ({CHAT_MODEL} / {CODE_MODEL})")
    print(f"  Output:    {out_dir}")
    print(f"{'='*60}\n")

    for i, q in enumerate(questions, 1):
        qid  = q["id"]
        cat  = q["category"]
        diff = q["difficulty"]
        text = q["question"]

        print(f"[{i:02d}/{total}] {qid}  ({cat}/{diff})")

        if dry_run:
            results.append({"id": qid, "category": cat, "difficulty": diff,
                             "question": text, "ori_response": "DRY RUN", "raw_response": "DRY RUN",
                             "ori_latency": 0.0, "raw_latency": 0.0})
            continue

        # ORI
        print(f"         → ORI ...", end="", flush=True)
        ori_resp, ori_lat, ori_err = query_ori(text, cat)
        if ori_err:
            print(f" ERROR: {ori_err}")
        else:
            print(f" {ori_lat:.1f}s  ({len(ori_resp)} chars)")

        # Raw Ollama
        print(f"         → Raw ...", end="", flush=True)
        raw_resp, raw_lat, raw_err = query_ollama_raw(text, cat)
        if raw_err:
            print(f" ERROR: {raw_err}")
        else:
            print(f" {raw_lat:.1f}s  ({len(raw_resp)} chars)")

        results.append({
            "id": qid,
            "category": cat,
            "difficulty": diff,
            "question": text,
            "scoring_guide": q.get("scoring_guide", ""),
            "ori_response": ori_resp,
            "ori_latency": round(ori_lat, 2),
            "ori_error": ori_err,
            "raw_response": raw_resp,
            "raw_model": CODE_MODEL if cat == "code" else CHAT_MODEL,
            "raw_latency": round(raw_lat, 2),
            "raw_error": raw_err,
        })

        # Brief pause between questions so the Ollama queue drains
        if i < total:
            time.sleep(8)

    # Save raw results
    out_file = out_dir / "results.json"
    out_file.write_text(json.dumps(results, indent=2))
    print(f"\n✓ Results saved → {out_file}")
    print(f"  Pass this file to the judge for scoring.\n")
    return str(out_file)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="ORI Intelligence Benchmark runner")
    parser.add_argument("--categories", nargs="+",
                        choices=["logic","math","code","knowledge","metacognition","reasoning"],
                        help="Only run specific categories")
    parser.add_argument("--dry-run", action="store_true", help="Skip API calls, just validate setup")
    args = parser.parse_args()

    run(categories=args.categories, dry_run=args.dry_run)
