#!/usr/bin/env python3
"""
Verification script for the Code Translation Engine module.
"""

import sys
import os
import json
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from oricli_core.brain.registry import ModuleRegistry

def main():
    print("Initializing Module Registry...")
    ModuleRegistry.discover_modules()
    
    translator = ModuleRegistry.get_module("code_translation_engine")
    if not translator:
        print("Failed to load code_translation_engine module.")
        return
        
    print("Code Translation Engine module loaded successfully.")
    
    # Test code: Bubble Sort
    python_code = """
def bubble_sort(arr):
    n = len(arr)
    for i in range(n):
        for j in range(0, n - i - 1):
            if arr[j] > arr[j + 1]:
                arr[j], arr[j + 1] = arr[j + 1], arr[j]
    return arr
"""
    
    print(f"\nSource Python Code:\n{python_code}")
    
    # 1. Analyze AST
    print("\n1. Analyzing AST Structure...")
    ast_res = translator.execute("analyze_ast_structure", {"source_code": python_code})
    print(json.dumps(ast_res, indent=2))
    
    # 2. Estimate Complexity
    print("\n2. Estimating Complexity...")
    comp_res = translator.execute("estimate_complexity", {"source_code": python_code})
    print(json.dumps(comp_res, indent=2))
    
    # 3. Translate Code
    print("\n3. Translating to Rust...")
    trans_res = translator.execute("translate_code", {
        "source_code": python_code,
        "source_lang": "python",
        "target_lang": "rust"
    })
    
    if trans_res.get("success"):
        print(f"\nComplexity Preserved: Time {trans_res.get('time_complexity_preserved')}, Space {trans_res.get('space_complexity_preserved')}")
        print(f"\nTranslated Rust Code:\n{trans_res.get('translated_code')}")
    else:
        print(f"Translation failed: {trans_res.get('error')}")

if __name__ == "__main__":
    main()
