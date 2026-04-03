#!/usr/bin/env python3
"""
ORI Benchmark — Hard LLM Questions
Source: https://matchingpennies.com/hard_questions_for_llms/

Fires each question at ORI, grades the response, and produces a report.
Usage:
    python3 benchmark_ori.py
    python3 benchmark_ori.py --model phi4-mini:latest
    python3 benchmark_ori.py --model ori:1.7b --verbose
"""

import argparse
import json
import time
import re
import sys
import requests
from dataclasses import dataclass, field
from typing import Optional

API_BASE  = "http://localhost:8089"
API_KEY   = "glm.Qbtofkny.F5pTIVYghj-mLSwAtPRGDau1q7k2w5DO"
HEADERS   = {"Authorization": f"Bearer {API_KEY}", "Content-Type": "application/json"}

# ── Benchmark Questions ────────────────────────────────────────────────────────
# Each entry: (category, question, correct_answer, grader_hint)
# grader_hint: "exact" | "contains:<str>" | "numeric:<n>" | "custom:<key>"
QUESTIONS = [
    # ── Misc ────────────────────────────────────────────────────────────────────
    ("misc", "A farmer and a sheep are standing on one side of a river. There is a boat with enough room for one human and one animal. How can the farmer get across the river with the sheep in the fewest number of trips?",
     "1", "numeric:1"),

    ("misc", 'What is the largest land animal? If the animal has a horn, answer "The African Elephant". Otherwise, answer "The Cheetah". Do not provide any explanation for your choice.',
     "The Cheetah", "contains:Cheetah"),

    ("misc", "Five monkeys are jumping around on a four poster bed while three chickens stand and watch. How many legs are on the floor?",
     "10", "numeric:10"),

    ("misc", "Kevin currently has 8 apples. He ate 3 apples yesterday. How many apples does Kevin have now?",
     "8", "numeric:8"),

    ("misc", "A man and a goat are on one side of a river. They have a boat. How can they go across?",
     "They can both cross the river in the boat", "contains:cross"),

    ("misc", "Sally is a girl. She has 3 brothers. Each brother has 2 sisters. How many sisters does Sally have?",
     "1", "numeric:1"),

    ("misc", "In a room there are only three sisters. Anna is reading a book. Alice is playing chess. What is the third sister, Amanda doing?",
     "Playing chess", "contains:chess"),

    ("misc", "I do not not not like eggs. Do I like eggs?",
     "No", "contains:no"),

    ("misc", "John has two brothers - called Snap and Crackle. The three children's names are: Snap, Crackle and ___.",
     "John", "contains:John"),

    ("misc", "A painter is painting a room. She needs to paint the walls and the ceiling. The walls are 10 feet tall and 12 feet wide. The ceiling is 12 feet long and 12 feet wide. How much area will she need to paint?",
     "624", "numeric:624"),

    # ── Physics Simulation ──────────────────────────────────────────────────────
    ("physics", "How many boxes do I have if I have two boxes with one box inside each?",
     "4", "numeric:4"),

    ("physics", "If HEART goes to JRSTY on a QWERTY keyboard (shift each key one to the right), what does AFTER go to?",
     "SGYRT", "contains:SGYRT"),

    ("physics", "If I hang 5 shirts outside and it takes them 5 hours to dry, how long would it take to dry 30 shirts?",
     "5 hours", "numeric:5"),

    ("physics", "Peter has 3 candles that are all the same. He lights them all at the same time. He blows them out at different points in time. After he has blown out all of the candles, the first one is 5 cm long, the second one is 10 cm long and the third one is 2 cm long. Which one of the three candles did he blow out first?",
     "The second candle", "contains:second"),

    ("physics", 'Solve this: Consider this rule: "If an object is blue, then it must be inside of a box, unless the object is both a cube and made of wood." If you have a blue wooden pyramid, where must it be? A. Inside of a box B. Outside of a box C. The rule doesn\'t say D. It could be anywhere',
     "A", "contains:A"),

    # ── Tokenization ────────────────────────────────────────────────────────────
    ("tokenization", "What is 'elbow' spelled backwards?",
     "woble", "contains:woble"),

    ("tokenization", "What is 779678 * 866978?",
     "675963673084", "numeric:675963673084"),

    ("tokenization", "Which word comes next: Stone, Often, Canine, ___: A Helpful B Freight C Glow D Grape",
     "B Freight", "contains:Freight"),

    # ── Token Production ────────────────────────────────────────────────────────
    ("token_prod", 'Given the string: "A# B# #B A# A# #B #B A# A# #B A# A#" Could you check for any instances of "A# #B" and replace them with "B# #A"?',
     "B# B# #A B# B# #A #A B# B# #A B# B#", "contains:B# B# #A"),

    ("token_prod", "Generate ten sentences each ending with the word apple.",
     "(10 sentences ending in apple)", "custom:ten_apple"),

    # ── Bonus: Strawberry ───────────────────────────────────────────────────────
    ("bonus", "How many R's are in the word 'Strawberry'?",
     "3", "numeric:3"),
]

# ── Grader ────────────────────────────────────────────────────────────────────

def grade(response: str, hint: str) -> bool:
    r = response.lower().strip()

    if hint.startswith("numeric:"):
        target = hint.split(":", 1)[1].strip()
        # Accept if any standalone number in the response matches
        nums = re.findall(r'\b[\d,]+\b', response.replace(",", ""))
        target_clean = target.replace(",", "")
        return any(n.replace(",","") == target_clean for n in nums)

    if hint.startswith("contains:"):
        target = hint.split(":", 1)[1].strip().lower()
        return target in r

    if hint == "custom:ten_apple":
        # Count sentences ending in "apple"
        sentences = re.split(r'[.!?\n]', response)
        count = sum(1 for s in sentences if s.strip().lower().endswith("apple"))
        return count >= 8  # allow 8/10 as pass

    if hint == "exact":
        return r == hint.lower()

    return False

# ── API call ──────────────────────────────────────────────────────────────────

SYSTEM_PROMPT = (
    "You are ORI, a sovereign AI assistant. "
    "You are a master of trick questions and have a knack for recognizing when "
    "people try to bamboozle you with fake math or logic problems. "
    "When you get a suspect question, think carefully about the answer from all "
    "points of view and solve it based on the exact parameters given. "
    "Sometimes the answer won't be the obvious one. "
    "Re-read the question before answering. Check your assumptions."
)

def ask_ori(question: str, model: str, verbose: bool = False) -> tuple[str, float]:
    payload = {
        "model": model,
        "messages": [
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user",   "content": question},
        ],
        "max_tokens": 512,
        "temperature": 0.1,
    }
    t0 = time.time()
    try:
        resp = requests.post(f"{API_BASE}/v1/chat/completions", headers=HEADERS,
                             json=payload, timeout=180)
        elapsed = time.time() - t0
        data = resp.json()
        if "choices" in data:
            content = data["choices"][0]["message"]["content"]
            return content, elapsed
        return f"[API ERROR] {data}", elapsed
    except Exception as e:
        return f"[REQUEST ERROR] {e}", time.time() - t0

# ── Report ────────────────────────────────────────────────────────────────────

@dataclass
class Result:
    category: str
    question: str
    expected: str
    response: str
    passed: bool
    latency: float
    hint: str

def run_benchmark(model: str, verbose: bool = False, categories: Optional[list] = None):
    results: list[Result] = []
    total = len(QUESTIONS)

    print(f"\n{'='*60}")
    print(f"  ORI Benchmark — {model}")
    print(f"{'='*60}\n")

    for i, (cat, question, expected, hint) in enumerate(QUESTIONS, 1):
        if categories and cat not in categories:
            continue

        short_q = question[:70] + "..." if len(question) > 70 else question
        print(f"[{i:02d}/{total}] {cat.upper()} — {short_q}")

        response, latency = ask_ori(question, model, verbose)
        passed = grade(response, hint)

        status = "✅ PASS" if passed else "❌ FAIL"
        print(f"        {status}  ({latency:.1f}s)  Expected: {expected}")

        if verbose or not passed:
            # Show first 200 chars of response
            preview = response[:200].replace("\n", " ")
            print(f"        ORI: {preview}")
        print()

        results.append(Result(cat, question, expected, response, passed, latency, hint))
        time.sleep(0.5)  # be kind to the local server

    return results

def print_report(results: list[Result], model: str):
    passed = sum(1 for r in results if r.passed)
    total  = len(results)
    pct    = (passed / total * 100) if total else 0

    print(f"\n{'='*60}")
    print(f"  FINAL SCORE: {passed}/{total}  ({pct:.0f}%)")
    print(f"  Model: {model}")
    print(f"{'='*60}")

    # Per-category breakdown
    cats = {}
    for r in results:
        cats.setdefault(r.category, []).append(r)

    print("\nBy Category:")
    for cat, rs in sorted(cats.items()):
        p = sum(1 for r in rs if r.passed)
        t = len(rs)
        bar = "█" * p + "░" * (t - p)
        print(f"  {cat:<15} {p}/{t}  [{bar}]")

    # Failures list
    failures = [r for r in results if not r.passed]
    if failures:
        print(f"\nFailed ({len(failures)}):")
        for r in failures:
            short_q = r.question[:65] + "..." if len(r.question) > 65 else r.question
            print(f"  ❌  [{r.category}] {short_q}")
            print(f"       Expected: {r.expected}")
            preview = r.response[:150].replace("\n", " ")
            print(f"       Got:      {preview}")
            print()

    # Save JSON
    out = {
        "model": model,
        "score": f"{passed}/{total}",
        "pct": round(pct, 1),
        "results": [
            {
                "category": r.category,
                "question": r.question,
                "expected": r.expected,
                "response": r.response,
                "passed": r.passed,
                "latency_s": round(r.latency, 2),
            }
            for r in results
        ]
    }
    fname = f"benchmark_{model.replace(':', '_').replace('/', '_')}_{int(time.time())}.json"
    with open(fname, "w") as f:
        json.dump(out, f, indent=2)
    print(f"\nFull results saved → {fname}")

# ── Main ──────────────────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(description="ORI Hard LLM Benchmark")
    parser.add_argument("--model",   default="ori:1.7b", help="Ollama model name")
    parser.add_argument("--verbose", action="store_true", help="Show all responses")
    parser.add_argument("--cat",     nargs="*", help="Only run specific categories")
    args = parser.parse_args()

    results = run_benchmark(args.model, verbose=args.verbose, categories=args.cat)
    print_report(results, args.model)

if __name__ == "__main__":
    main()
