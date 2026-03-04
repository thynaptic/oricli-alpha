#!/usr/bin/env python3
"""
Benchmark Diagnostic Tool
This script is intended to be run on the remote pod to inspect the state
of LiveBench results and identify parsing or generation issues.
"""
import os
import json
import glob
from pathlib import Path

def run_diagnostic(base_dir: str = "LiveBench/livebench/data"):
    print(f"--- Mavaia Benchmark Diagnostic ---")
    base_path = Path(base_dir)
    if not base_path.exists():
        print(f"ERROR: Base directory {base_dir} does not exist.")
        # Try parent dir
        print(f"Contents of {base_path.parent}:")
        if base_path.parent.exists():
            for p in base_path.parent.iterdir():
                print(f"  - {p}")
        return

    print(f"Checking results in: {base_path.absolute()}")
    
    # 1. Find all answer files
    answer_files = list(base_path.glob("**/model_answer/*.jsonl"))
    print(f"Found {len(answer_files)} model answer files.")

    # 2. Sample some answers to check format
    if answer_files:
        print("\n--- Sampling Model Answers ---")
        for f in answer_files[:3]: # Sample up to 3 files
            print(f"\nFile: {f}")
            try:
                with open(f, 'r') as file:
                    lines = file.readlines()
                    if not lines:
                        print("  (Empty file)")
                        continue
                    
                    # Print first line sample
                    sample_line = lines[0].strip()
                    print(f"  Sample Line (first 200 chars): {sample_line[:200]}")
                    
                    try:
                        data = json.loads(sample_line)
                        print("  [SUCCESS] Line is valid JSON.")
                        # Check choices/turns
                        if 'choices' in data and data['choices']:
                            turn = data['choices'][0]['turns'][-1]
                            print(f"  LLM Output Sample (first 200 chars): {turn[:200]}")
                            if "<table" in turn.lower():
                                print("  [WARNING] HTML table detected in output.")
                            if "{" in turn and "}" in turn:
                                print("  [INFO] Potential JSON-like structure in output.")
                        else:
                            print("  [WARNING] 'choices' field missing or empty in JSON.")
                    except json.JSONDecodeError:
                        print("  [ERROR] Line is NOT valid JSON.")
            except Exception as e:
                print(f"  [ERROR] Could not read file: {e}")

    # 3. Find all judgment files
    judgment_files = list(base_path.glob("**/model_judgment/ground_truth_judgment.jsonl"))
    print(f"\nFound {len(judgment_files)} judgment files.")
    
    # 4. Check for 0 scores
    if judgment_files:
        zero_scores = 0
        total_scores = 0
        for f in judgment_files:
            try:
                with open(f, 'r') as file:
                    for line in file:
                        if not line.strip(): continue
                        total_scores += 1
                        data = json.loads(line)
                        if data.get("score") == 0:
                            zero_scores += 1
            except:
                pass
        
        if total_scores > 0:
            print(f"Total evaluated: {total_scores}")
            print(f"Zero scores: {zero_scores} ({zero_scores/total_scores:.1%})")
        else:
            print("No evaluations found in judgment files.")

    print("\n--- Diagnostic Complete ---")

def main():
    # Check if we are in the mavaia root or livebench root
    if Path("LiveBench/livebench/data").exists():
        run_diagnostic("LiveBench/livebench/data")
    elif Path("data").exists() and "live_bench" in os.listdir("data"):
        run_diagnostic("data")
    else:
        run_diagnostic(".")

if __name__ == "__main__":
    main()
