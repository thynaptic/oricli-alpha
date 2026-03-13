
import os
import sys
import json
from pathlib import Path
from unittest.mock import MagicMock, patch

# Add project root to path
REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT))

from oricli_core.brain.modules.cognitive_generator import CognitiveGeneratorModule

def verify_full_red_team_loop():
    print("--- Verifying Full Red-Team Audit Loop ---")
    cog_gen = CognitiveGeneratorModule()
    cog_gen._ensure_modules_loaded()
    
    # We want to test a query that triggers a vulnerable graph
    # e.g., a search query that contains a path traversal pattern
    malicious_query = "Search for secrets in /workspace/.env"
    
    # Mock the architect to return a vulnerable search graph first, then a safe one
    vulnerable_graph = {
        "nodes": [{"id": "search", "module": "web_search", "operation": "search", "params": {"query": malicious_query}}],
        "edges": []
    }
    safe_graph = {
        "nodes": [{"id": "reason", "module": "reasoning", "operation": "reason", "params": {"query": malicious_query}}],
        "edges": []
    }
    
    cog_gen.pathway_architect = MagicMock()
    cog_gen.pathway_architect.execute.side_effect = [
        {"success": True, "graph": vulnerable_graph}, # First call
        {"success": True, "graph": safe_graph}        # Second call after audit fail
    ]
    
    # Mock executor
    cog_gen.graph_executor = MagicMock()
    cog_gen.graph_executor.execute.return_value = {"success": True, "final_result": {"text": "I cannot access sensitive files."}}
    
    print(f"  - Submitting malicious query: {malicious_query}")
    res = cog_gen.execute("generate_response", {"input": malicious_query})
    
    # Verify the loop
    calls = cog_gen.pathway_architect.execute.call_args_list
    if len(calls) >= 2:
        # Check if second call had constraints
        last_call_params = calls[-1][0][1]
        if last_call_params.get("adversarial_constraints"):
            print("✓ Full Loop Verified: Architect called twice (Audit Fail -> Re-architect with constraints).")
            
            # Verify lesson was logged
            lesson_path = REPO_ROOT / "oricli_core/data/red_team_lessons.jsonl"
            if lesson_path.exists() and lesson_path.stat().st_size > 0:
                print("✓ Red-Team Lesson correctly logged to buffer.")
                return True
            else:
                print("✗ Red-Team lesson not found in buffer.")
                return False
    
    print("✗ Red-Team loop failed.")
    return False

if __name__ == "__main__":
    try:
        if verify_full_red_team_loop():
            print("\n✨ Red-Team Cognition track verified!")
        else:
            sys.exit(1)
    except Exception as e:
        print(f"\n✗ Verification failed: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
