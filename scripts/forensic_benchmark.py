#!/usr/bin/env python3
import json
import os
from pathlib import Path
from collections import defaultdict

def forensic_analysis(category="data_analysis/tablereformat"):
    base_dir = Path(f"data/live_bench/{category}")
    answer_file = base_dir / "model_answer" / "mavaia.jsonl"
    judgment_file = base_dir / "model_judgment" / "ground_truth_judgment.jsonl"

    if not answer_file.exists():
        print(f"Error: Answer file {answer_file} not found.")
        return

    # Load judgments to get scores
    scores = {}
    if judgment_file.exists():
        with open(judgment_file, 'r') as f:
            for line in f:
                data = json.loads(line)
                scores[data['question_id']] = data.get('score', 0)

    print(f"--- Forensic Analysis: {category} ---")
    
    stats = defaultdict(int)
    total = 0

    with open(answer_file, 'r') as f:
        for line in f:
            total += 1
            data = json.loads(line)
            qid = data['question_id']
            # Get last turn
            llm_output = data['choices'][0]['turns'][-1]
            score = scores.get(qid, 0)

            # Analyze output
            output_lower = llm_output.lower()
            
            is_echo = "please convert the input table" in output_lower or "input table:" in output_lower
            is_conversational = any(word in output_lower for word in ["i'm here to help", "what would you like", "i'd say"])
            has_html = "<table" in output_lower
            has_json = "{" in output_lower and "}" in output_lower
            is_empty = not llm_output.strip()

            if is_echo:
                stats['echo_prompt'] += 1
            elif is_conversational and not has_json:
                stats['conversational_refusal'] += 1
            elif has_html and not has_json:
                stats['returned_html'] += 1
            elif is_empty:
                stats['empty_response'] += 1
            elif has_json:
                stats['has_json'] += 1
            else:
                stats['other_failure'] += 1

            if score > 0:
                stats['correct'] += 1

    print(f"Total Questions: {total}")
    for k, v in stats.items():
        print(f"  {k}: {v} ({v/total:.1%})")
    
    # Show a few examples of failures
    print("\n--- Examples of Failures ---")
    examples_shown = 0
    with open(answer_file, 'r') as f:
        for line in f:
            if examples_shown >= 5: break
            data = json.loads(line)
            llm_output = data['choices'][0]['turns'][-1]
            qid = data['question_id']
            if scores.get(qid, 0) == 0:
                print(f"\nQID: {qid}")
                print(f"LLM Output: {llm_output[:300]}...")
                examples_shown += 1

def main():
    import sys
    cat = sys.argv[1] if len(sys.argv) > 1 else "data_analysis/tablereformat"
    forensic_analysis(cat)

if __name__ == "__main__":
    main()
