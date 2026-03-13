#!/usr/bin/env python3
import sys
import os
import json
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))
from oricli_core.brain.registry import ModuleRegistry


def main():
    ModuleRegistry.discover_modules()
    fv_bridge = ModuleRegistry.get_module("formal_verification_bridge")
    if not fv_bridge:
        print("Failed to load formal_verification_bridge module.")
        return
        
    print("Formal Verification Bridge module loaded successfully.")
    
    python_code = """
def add_positive(a: int, b: int) -> int:
    if a > 0 and b > 0:
        return a + b
    return 0
"""
    
    print(f"\nSource Python Code:\n{python_code}")
    
    print("\n1. Translating to Lean 4...")
    trans_res = fv_bridge.execute("translate_to_lean", {"source_code": python_code})
    print(f"Translation result keys: {trans_res.keys()}")
    if trans_res.get("success"):
        lean_code = trans_res.get("lean_code")
        print(f"Lean Code Generated:\n{lean_code}")
        
        print("\n2. Verifying Proof (using LLM fallback if Lean is not installed)...")
        ver_res = fv_bridge.execute("verify_proof", {"lean_code": lean_code})
        print("Verification result:")
        print(json.dumps(ver_res, indent=2))
    else:
        print(f"Translation failed: {trans_res.get('error')}")
        
    print("\n3. Testing Full Pipeline (formalize_and_verify) with 1 retry...")
    pipe_res = fv_bridge.execute("formalize_and_verify", {
        "source_code": python_code,
        "max_retries": 1
    })
    
    if pipe_res.get("success"):
        print(f"\nVerification Pipeline Successful!")
        print(f"Status: {pipe_res.get('verification_status')}")
        print(f"Method: {pipe_res.get('method')}")
        print(f"Attempts: {pipe_res.get('attempts')}")
    else:
        print(f"\nVerification Pipeline Failed after {pipe_res.get('attempts', 0)} attempts.")
        print(f"Error: {pipe_res.get('error')}")

if __name__ == "__main__":
    main()
