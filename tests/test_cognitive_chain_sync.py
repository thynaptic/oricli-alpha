#!/usr/bin/env python3
"""
Integration test for cognitive chain synchronization.
Verifies that all modules return standardized formats and data flows correctly.
"""

import sys
import os
from pathlib import Path
from unittest.mock import MagicMock, patch

# Add project root to path
REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT))

from mavaia_core.brain.registry import ModuleRegistry

def test_cognitive_chain_sync():
    """Verify that CognitiveGenerator correctly orchestrates sub-modules with standard APIs."""
    print("Testing cognitive chain synchronization...")
    
    # Enable heavy modules for full registry check
    os.environ["MAVAIA_ENABLE_HEAVY_MODULES"] = "true"
    
    try:
        # Get actual modules (some might be stubs in this environment)
        cg = ModuleRegistry.get_module("cognitive_generator")
        reasoning = ModuleRegistry.get_module("reasoning")
        router = ModuleRegistry.get_module("adapter_router")
        ntg = ModuleRegistry.get_module("neural_text_generator")
        
        if not cg:
            print("✗ CognitiveGenerator not found in registry.")
            sys.exit(1)
            
        # 1. Test status operation on all core modules
        target_modules = ["cognitive_generator", "reasoning", "adapter_router", "neural_text_generator", "research_agent", "synthesis_agent", "agent_coordinator", "multi_agent_orchestrator"]
        
        for name in target_modules:
            mod = ModuleRegistry.get_module(name)
            if not mod:
                print(f"⚠ Skipping status check for optional/missing module: {name}")
                continue
                
            res = mod.execute("status", {})
            if res.get("success") is True:
                print(f"✓ Module '{name}' status: PASS (version {mod.metadata.version})")
            else:
                print(f"✗ Module '{name}' status: FAIL - {res.get('error')}")
                sys.exit(1)
                
        # 2. Test mock execution flow to verify data passing
        with patch.object(reasoning, 'execute') as mock_reason, \
             patch.object(router, 'execute') as mock_route, \
             patch.object(ntg, 'execute') as mock_gen:
             
            # Setup mocks with standardized returns
            mock_reason.return_value = {"success": True, "reasoning": "Test reasoning result"}
            mock_route.return_value = {"success": True, "adapter": "test_adapter"}
            mock_gen.return_value = {"success": True, "text": "Final generated response"}
            
            # Execute generator
            res = cg.execute("generate_response", {"input": "Test query", "context": "Test context"})
            
            if res.get("success") is True:
                print("✓ CognitiveGenerator execution: PASS")
                # Check if result contains expected keys
                if "response" in res or "text" in res:
                    print("✓ Result contains response text.")
                else:
                    print(f"✗ Result missing response text: {res}")
                    sys.exit(1)
            else:
                print(f"✗ CognitiveGenerator execution: FAIL - {res.get('error')}")
                sys.exit(1)
                
        print("\n✨ Cognitive chain synchronization verified!")
        
    except Exception as e:
        print(f"✗ Sync test crashed with error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)

if __name__ == "__main__":
    test_cognitive_chain_sync()
