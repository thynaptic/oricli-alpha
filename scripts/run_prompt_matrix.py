#!/usr/bin/env python3
"""Run a prompt matrix through the cognitive_generator and summarize coherence.

Usage (must use repo venv):
  ./.venv/bin/python scripts/run_prompt_matrix.py

This is intentionally self-contained and does NOT call any external LLM backends.
"""

from __future__ import annotations

import json
import signal
import sys
import time
from pathlib import Path
from typing import Any, Dict, List, Tuple

# Add project root to path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from mavaia_core import MavaiaClient


PROMPTS: List[Tuple[str, str]] = [
    ("greeting", "hi"),
    ("imperative", "Translate 'Good morning' to Spanish."),
    ("imperative", "Translate 'Hello world' to French."),
    ("imperative", "In French, how do you say 'Hello world'?"),
    ("imperative", "Summarize this in one sentence: The Mona Lisa is a portrait by Leonardo da Vinci."),
    ("imperative", "Summarize: Romeo and Juliet are two young lovers from feuding families whose secret relationship ends in tragedy."),
    ("definition", "What is sfumato?"),
    ("explain", "Explain why the sky is blue in simple terms."),
    ("reasoning", "Why does increasing the order of a Markov chain improve local coherence but often reduce generalization?"),
    ("factual", "What is the capital of Australia?"),
    ("coding", "Why does 0.1 + 0.2 == 0.3 evaluate to False in Python?"),
    ("math", "Calculate 15 * 23"),
    ("howto", "How do I undo the last git commit but keep my changes?"),
    ("nonsense", "blorptastic flargle womp?"),
    ("open", "Give me three interesting facts about octopuses."),
]


class _Timeout(Exception):
    pass


def _alarm_handler(signum, frame):  # noqa: ARG001
    raise _Timeout()


def _extract_text(result: Dict[str, Any]) -> str:
    if not isinstance(result, dict):
        return str(result)
    for key in ("response", "text", "answer", "final_answer"):
        val = result.get(key)
        if isinstance(val, str) and val.strip():
            return val.strip()
    return ""


def _is_obviously_bad(text: str) -> bool:
    t = (text or "").strip()
    if not t:
        return True
    if t == "1":
        return True
    lowered = t.lower()
    # Generic assistant boilerplate that indicates we failed to route/use cognition.
    if lowered in {
        "hey! what's up?",
        "i'm here to help. what would you like to know?",
    }:
        return True
    return False


def main() -> int:
    per_prompt_timeout_s = 25

    print("Initializing Mavaia client...", flush=True)
    client = MavaiaClient()
    print("Client ready. Running prompt matrix...\n", flush=True)

    # Use SIGALRM for per-prompt timeouts (Linux VPS).
    signal.signal(signal.SIGALRM, _alarm_handler)

    passed = 0
    failed = 0

    out_dir = Path("mavaia_matrix_results") / "latest"
    out_dir.mkdir(parents=True, exist_ok=True)

    for i, (category, prompt) in enumerate(PROMPTS, start=1):
        start = time.time()
        signal.alarm(per_prompt_timeout_s)
        try:
            result = client.brain.cognitive_generator.generate_response(
                input=prompt,
                context="",
                voice_context={
                    "base_personality": "mavaia",
                    "tone": "neutral",
                    "formality_level": 0.5,
                    "technical_level": 0.5,
                    "empathy_level": 0.5,
                    "conversation_topic": "general",
                    "user_history": [],
                    "adaptation_confidence": 0.5,
                },
            )
            text = _extract_text(result)
            verification = result.get("verification") if isinstance(result, dict) else None
            ok_verify = True
            if isinstance(verification, dict) and verification.get("matches_intent") is False:
                ok_verify = False
            ok = (not _is_obviously_bad(text)) and ok_verify
            dur_ms = int((time.time() - start) * 1000)

            # Always persist the raw result for inspection/regression.
            slug = f"{i:03d}_{category}".replace("/", "_")
            (out_dir / f"{slug}.json").write_text(
                json.dumps(result, indent=2, default=str), encoding="utf-8"
            )

            if ok:
                passed += 1
                print(f"✓ [{category}] {prompt}  ({dur_ms}ms)")
            else:
                failed += 1
                print(f"✗ [{category}] {prompt}  ({dur_ms}ms)")
                if not ok_verify:
                    print(f"  Verification failed: {verification}")
                print(f"  Bad/empty output: {text!r}")

        except _Timeout:
            failed += 1
            dur_ms = int((time.time() - start) * 1000)
            print(f"✗ [{category}] {prompt}  ({dur_ms}ms)")
            print(f"  Timed out after {per_prompt_timeout_s}s")
            slug = f"{i:03d}_{category}".replace("/", "_")
            (out_dir / f"{slug}.json").write_text(
                json.dumps({"prompt": prompt, "category": category, "timeout_s": per_prompt_timeout_s}, indent=2),
                encoding="utf-8",
            )
        except Exception as e:
            failed += 1
            dur_ms = int((time.time() - start) * 1000)
            print(f"✗ [{category}] {prompt}  ({dur_ms}ms)")
            print(f"  Exception: {type(e).__name__}: {e}")
            slug = f"{i:03d}_{category}".replace("/", "_")
            (out_dir / f"{slug}.json").write_text(
                json.dumps({"prompt": prompt, "category": category, "exception": f"{type(e).__name__}: {e}"}, indent=2),
                encoding="utf-8",
            )
        finally:
            signal.alarm(0)

    total = passed + failed
    print(f"\nSummary: passed {passed}/{total}, failed {failed}/{total}")
    return 0 if failed == 0 else 1


if __name__ == "__main__":
    raise SystemExit(main())
