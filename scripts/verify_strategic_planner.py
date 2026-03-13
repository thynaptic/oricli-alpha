
import os
import sys
from pathlib import Path
from unittest.mock import MagicMock, patch

# Add project root to path
REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT))

from oricli_core.brain.modules.cognitive_generator import CognitiveGeneratorModule
from oricli_core.brain.modules.strategic_planner import StrategicPlannerModule

def verify_strategic_planner():
    print("--- Verifying Strategic Pre-Execution Planner ---")
    
    planner = StrategicPlannerModule()
    
    # Mock dependencies
    planner.tree_of_thought = MagicMock()
    planner.tree_of_thought.execute.return_value = {
        "success": True,
        "thoughts": ["Approach 1: Analysis", "Approach 2: Execution", "Approach 3: Hybrid"]
    }
    
    planner.mcts_search_engine = MagicMock()
    planner.mcts_search_engine.execute.side_effect = [
        {"success": True, "confidence": 0.6},
        {"success": True, "confidence": 0.9},
        {"success": True, "confidence": 0.7}
    ]
    
    planner.chain_of_thought = MagicMock()
    planner.chain_of_thought.execute.return_value = {
        "success": True,
        "steps": ["Step 1", "Step 2", "Step 3", "Step 4", "Step 5"]
    }
    
    planner._modules_loaded = True
    
    print("  - Creating strategic plan for a complex goal...")
    goal = "Build a scalable microservices architecture for a fintech app."
    res = planner.execute("create_strategic_plan", {"goal": goal})
    
    if res.get("success"):
        print("✓ Strategic plan created successfully.")
        print(f"✓ Selected Strategy: {res.get('selected_strategy')}")
        print(f"✓ Number of Steps: {len(res.get('steps', []))}")
        
        if res.get("selected_strategy") == "Approach 2: Execution" and len(res.get("steps", [])) == 5:
            print("✓ Planner correctly selected the highest scoring strategy and decomposed it.")
            return True
    
    print("✗ Strategic planning verification failed.")
    return False

def verify_generator_integration():
    print("\n--- Verifying Generator Integration ---")
    cog_gen = CognitiveGeneratorModule()
    cog_gen._ensure_modules_loaded()
    
    # Mock components
    cog_gen.strategic_planner = MagicMock()
    cog_gen.strategic_planner.execute.return_value = {
        "success": True,
        "selected_strategy": "Mocked Strategy",
        "steps": ["Mocked Step 1", "Mocked Step 2"]
    }
    
    # Mock architect and executor to avoid full run
    cog_gen.pathway_architect = MagicMock()
    cog_gen.pathway_architect.execute.return_value = {"success": False} # Fallback to linear
    cog_gen._execute_module_chain = MagicMock()
    cog_gen._execute_module_chain.return_value = {"success": True, "text": "Execution complete."}
    
    # Complex query to trigger planning
    complex_query = "This is a very long and complex query that definitely requires strategic planning before any action is taken by the system."
    
    print(f"  - Submitting complex query to generator...")
    res = cog_gen.execute("generate_response", {"input": complex_query})
    
    # Check if planner was called
    if cog_gen.strategic_planner.execute.called:
        print("✓ Generator successfully consulted Strategic Planner for complex query.")
        # Check if plan was injected into context (first arg of _execute_module_chain)
        args, kwargs = cog_gen._execute_module_chain.call_args
        context = args[1].get("context", "")
        if "[Strategic Plan]" in context and "Mocked Strategy" in context:
            print("✓ Strategic plan correctly injected into cognitive context.")
            return True
            
    print("✗ Generator integration verification failed.")
    return False

if __name__ == "__main__":
    try:
        if verify_strategic_planner() and verify_generator_integration():
            print("\n✨ Strategic Pre-Execution Planner verified!")
        else:
            sys.exit(1)
    except Exception as e:
        print(f"\n✗ Verification failed: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
