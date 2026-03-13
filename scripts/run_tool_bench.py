#!/usr/bin/env python3
"""
Dynamic ToolBench Runner
Executes tool-use scenarios and evaluates Oricli-Alpha's efficacy.
"""

import os
import sys
import json
import time
from pathlib import Path
from typing import List, Dict, Any

# Add project root to path
REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT))

from oricli_core.brain.registry import ModuleRegistry
from oricli_core.brain.modules.tool_call_parser import tool_call_parser

def run_tool_bench():
    print("🚀 Starting ToolBench Execution...")
    
    # 1. Load scenarios
    scenario_path = REPO_ROOT / "oricli_core" / "data" / "tool_bench_scenarios.json"
    if not scenario_path.exists():
        print(f"✗ Scenarios not found at {scenario_path}. Run generator first.")
        return
        
    with open(scenario_path, "r", encoding="utf-8") as f:
        scenarios = json.load(f)
    
    # 2. Load Cognitive Generator
    ModuleRegistry.discover_modules()
    try:
        cog_gen = ModuleRegistry.get_module("cognitive_generator")
        print("✓ Cognitive Generator loaded for evaluation.")
    except Exception as e:
        print(f"✗ Failed to load Cognitive Generator: {e}")
        return

    results = []
    corrections = []
    
    print(f"Executing {len(scenarios)} scenarios...")
    
    for i, s in enumerate(scenarios):
        query = s["query"]
        expected_tool = s["tool_name"]
        category = s["category"]
        
        print(f"  [{i+1}/{len(scenarios)}] Testing: {query[:50]}...")
        
        try:
            # We use 'generate_response_with_tools' to force tool-seeking behavior
            res = cog_gen.execute("generate_response", {"input": query})
            output_text = res.get("text", "")
            
            # Parse tool calls from output
            tool_calls = tool_call_parser.parse_tool_calls(output_text)
            
            # EVALUATION
            success = False
            error_reason = ""
            
            if not tool_calls:
                if category == "ADVERSARIAL":
                    success = True # Correctly refused to call a tool
                else:
                    error_reason = "No tool call generated"
            else:
                call = tool_calls[0]
                actual_name = call.function.name
                actual_args = call.function.arguments
                
                if actual_name != expected_tool:
                    error_reason = f"Selection error: Picked '{actual_name}' instead of '{expected_tool}'"
                else:
                    # Check syntax (schema validation)
                    # For now, a simple check if all required fields are present
                    expected_schema = s.get("expected_schema", {})
                    required = expected_schema.get("required", [])
                    missing = [r for r in required if r not in actual_args]
                    
                    if missing:
                        error_reason = f"Syntax error: Missing required fields: {missing}"
                    else:
                        success = True
            
            # RECORD RESULTS
            result_entry = {
                "query": query,
                "category": category,
                "expected_tool": expected_tool,
                "actual_output": output_text,
                "success": success,
                "error": error_reason
            }
            results.append(result_entry)
            
            # LOG CORRECTION IF FAILED
            if not success and category != "ADVERSARIAL":
                corrections.append({
                    "prompt": query,
                    "rejected": output_text,
                    "chosen": f"tool_call: {expected_tool}(...)", # Simplified for now
                    "reason": error_reason
                })
                
        except Exception as e:
            print(f"    ✗ Error during execution: {e}")

    # 3. Save Results
    results_path = REPO_ROOT / "oricli_core" / "data" / "tool_bench_results.json"
    with open(results_path, "w", encoding="utf-8") as f:
        json.dump(results, f, indent=2)
        
    # 4. Save Corrections for Phase 3
    if corrections:
        corr_path = REPO_ROOT / "oricli_core" / "data" / "tool_corrections.jsonl"
        with open(corr_path, "a", encoding="utf-8") as f:
            for c in corrections:
                f.write(json.dumps(c) + "\n")
        print(f"✓ Saved {len(corrections)} corrections to {corr_path}")

    # Summary
    total = len(results)
    passed = sum(1 for r in results if r["success"])
    print(f"\n📊 ToolBench Summary:")
    print(f"  Total: {total}")
    print(f"  Passed: {passed} ({passed/total*100:.1f}%)")
    print(f"  Failed: {total - passed}")

if __name__ == "__main__":
    run_tool_bench()
