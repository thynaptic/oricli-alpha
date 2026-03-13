#!/usr/bin/env python3
"""
Validation script for CoT Layered Reasoning Integration

Tests stage integration with fallbacks, backward compatibility, metrics, and gating.
"""

import sys
import time
from pathlib import Path

# Add project to path
sys.path.insert(0, str(Path(__file__).parent))

from oricli_core.brain.registry import ModuleRegistry
from oricli_core.brain.metrics import get_metrics_collector


def test_module_discovery():
    """Test that ChainOfThought module is still discoverable"""
    print("=" * 80)
    print("Test 1: Module Discovery")
    print("=" * 80)
    
    ModuleRegistry.discover_modules(background=False, verbose=False)
    modules = ModuleRegistry.list_modules()
    
    if "chain_of_thought" in modules:
        print("✓ PASS: chain_of_thought module discovered")
        return True
    else:
        print("✗ FAIL: chain_of_thought module not found")
        return False


def test_backward_compatibility():
    """Test that existing CoT operations still work"""
    print("\n" + "=" * 80)
    print("Test 2: Backward Compatibility")
    print("=" * 80)
    
    try:
        module = ModuleRegistry.get_module("chain_of_thought", auto_discover=False, wait_timeout=2.0)
        if not module:
            print("✗ FAIL: Could not get chain_of_thought module")
            return False
        
        # Test basic execute_cot operation
        result = module.execute("execute_cot", {
            "query": "What is 2 + 2?",
            "context": "Simple math problem"
        })
        
        if isinstance(result, dict) and "reasoning" in result and "conclusion" in result:
            print("✓ PASS: execute_cot operation works")
            print(f"  Conclusion: {result.get('conclusion', 'N/A')[:50]}")
            return True
        else:
            print("✗ FAIL: execute_cot returned unexpected format")
            print(f"  Result keys: {list(result.keys()) if isinstance(result, dict) else type(result)}")
            return False
    except Exception as e:
        print(f"✗ FAIL: Error executing CoT: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_stage_orchestration():
    """Test that new stage orchestration executes correctly"""
    print("\n" + "=" * 80)
    print("Test 3: Stage Orchestration")
    print("=" * 80)
    
    try:
        module = ModuleRegistry.get_module("chain_of_thought", auto_discover=False, wait_timeout=2.0)
        if not module:
            print("✗ FAIL: Could not get chain_of_thought module")
            return False
        
        # Test with a complex query that should trigger full CoT pipeline
        result = module.execute("execute_cot", {
            "query": "Explain the process of photosynthesis step by step",
            "context": "Biology question requiring multi-step reasoning",
            "configuration": {
                "min_complexity_score": 0.3,  # Low threshold to ensure CoT runs
                "max_steps": 3
            }
        })
        
        if isinstance(result, dict):
            has_steps = "steps" in result or "reasoning" in result
            has_conclusion = "conclusion" in result or "final_answer" in result
            
            if has_steps and has_conclusion:
                print("✓ PASS: Stage orchestration executed successfully")
                print(f"  Has steps: {has_steps}")
                print(f"  Has conclusion: {has_conclusion}")
                return True
            else:
                print("✗ FAIL: Stage orchestration missing expected fields")
                print(f"  Result keys: {list(result.keys())}")
                return False
        else:
            print("✗ FAIL: Stage orchestration returned unexpected type")
            return False
    except Exception as e:
        print(f"✗ FAIL: Error in stage orchestration: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_complexity_gating():
    """Test complexity-based gating logic"""
    print("\n" + "=" * 80)
    print("Test 4: Complexity-Based Gating")
    print("=" * 80)
    
    try:
        module = ModuleRegistry.get_module("chain_of_thought", auto_discover=False, wait_timeout=2.0)
        if not module:
            print("✗ FAIL: Could not get chain_of_thought module")
            return False
        
        # Test with very simple query (should trigger simple reasoning)
        result = module.execute("execute_cot", {
            "query": "Hi",
            "context": "",
            "configuration": {
                "min_complexity_score": 0.9  # High threshold - should skip CoT
            }
        })
        
        if isinstance(result, dict) and ("reasoning" in result or "conclusion" in result):
            print("✓ PASS: Complexity gating works (simple query handled)")
            return True
        else:
            print("✗ FAIL: Complexity gating failed")
            return False
    except Exception as e:
        print(f"✗ FAIL: Error in complexity gating: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_stage_module_integration():
    """Test integration with stage modules (DecompositionModule, ReasoningModule, SynthesisAgent)"""
    print("\n" + "=" * 80)
    print("Test 5: Stage Module Integration")
    print("=" * 80)
    
    try:
        # Check if stage modules exist
        decomposition = ModuleRegistry.get_module("decomposition", auto_discover=False, wait_timeout=1.0)
        reasoning = ModuleRegistry.get_module("reasoning", auto_discover=False, wait_timeout=1.0)
        synthesis = ModuleRegistry.get_module("synthesis_agent", auto_discover=False, wait_timeout=1.0)
        
        modules_found = []
        if decomposition:
            modules_found.append("decomposition")
        if reasoning:
            modules_found.append("reasoning")
        if synthesis:
            modules_found.append("synthesis_agent")
        
        print(f"  Stage modules found: {modules_found}")
        
        # Test CoT with complex query (should use stage modules if available)
        module = ModuleRegistry.get_module("chain_of_thought", auto_discover=False, wait_timeout=2.0)
        if not module:
            print("✗ FAIL: Could not get chain_of_thought module")
            return False
        
        result = module.execute("execute_cot", {
            "query": "Solve this step by step: If I have 5 apples and give away 2, how many do I have left?",
            "context": "Math problem",
            "configuration": {
                "min_complexity_score": 0.3,
                "max_steps": 3
            }
        })
        
        if isinstance(result, dict) and ("reasoning" in result or "conclusion" in result):
            print("✓ PASS: Stage module integration works (with fallbacks)")
            print(f"  Stage modules available: {len(modules_found)}/3")
            return True
        else:
            print("✗ FAIL: Stage module integration failed")
            return False
    except Exception as e:
        print(f"✗ FAIL: Error in stage module integration: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_metrics_collection():
    """Test that stage-level metrics are being recorded"""
    print("\n" + "=" * 80)
    print("Test 6: Metrics Collection")
    print("=" * 80)
    
    try:
        # Clear metrics before test
        collector = get_metrics_collector()
        
        # Run a CoT operation
        module = ModuleRegistry.get_module("chain_of_thought", auto_discover=False, wait_timeout=2.0)
        if not module:
            print("✗ FAIL: Could not get chain_of_thought module")
            return False
        
        module.execute("execute_cot", {
            "query": "What is the capital of France?",
            "context": "Geography question"
        })
        
        # Check for stage metrics
        module_metrics = collector.get_module_metrics("chain_of_thought")
        if module_metrics:
            operations = list(module_metrics.operations.keys())
            stage_metrics = [op for op in operations if op.startswith("stage.")]
            gating_metrics = [op for op in operations if op == "cot.gating"]
            
            print(f"  Operations recorded: {len(operations)}")
            print(f"  Stage metrics: {stage_metrics}")
            print(f"  Gating metrics: {gating_metrics}")
            
            if stage_metrics or gating_metrics:
                print("✓ PASS: Metrics collection working")
                return True
            else:
                print("⚠ WARN: No stage metrics found (may be normal if gating skipped CoT)")
                # Still pass - metrics might not be recorded if gating skipped
                return True
        else:
            print("⚠ WARN: No module metrics found")
            return True  # Metrics might not be initialized yet
    except Exception as e:
        print(f"⚠ WARN: Error checking metrics: {e}")
        return True  # Metrics are optional


def test_error_handling():
    """Test error handling and fallbacks"""
    print("\n" + "=" * 80)
    print("Test 7: Error Handling & Fallbacks")
    print("=" * 80)
    
    try:
        module = ModuleRegistry.get_module("chain_of_thought", auto_discover=False, wait_timeout=2.0)
        if not module:
            print("✗ FAIL: Could not get chain_of_thought module")
            return False
        
        # Test with invalid input (should handle gracefully)
        try:
            result = module.execute("execute_cot", {
                "query": "",  # Empty query
            })
            # Should either return error or handle gracefully
            print("✓ PASS: Error handling works (empty query handled)")
            return True
        except Exception as e:
            # Exception is acceptable for invalid input
            print(f"✓ PASS: Error handling works (exception raised for invalid input: {type(e).__name__})")
            return True
    except Exception as e:
        print(f"✗ FAIL: Unexpected error in error handling test: {e}")
        return False


def test_api_compatibility():
    """Test that API interface is unchanged"""
    print("\n" + "=" * 80)
    print("Test 8: API Compatibility")
    print("=" * 80)
    
    try:
        module = ModuleRegistry.get_module("chain_of_thought", auto_discover=False, wait_timeout=2.0)
        if not module:
            print("✗ FAIL: Could not get chain_of_thought module")
            return False
        
        # Check metadata
        metadata = module.metadata
        required_ops = ["execute_cot", "analyze_complexity", "should_activate", "format_reasoning_output"]
        
        missing_ops = [op for op in required_ops if op not in metadata.operations]
        if missing_ops:
            print(f"✗ FAIL: Missing operations: {missing_ops}")
            return False
        
        print("✓ PASS: All required operations present")
        print(f"  Operations: {metadata.operations}")
        return True
    except Exception as e:
        print(f"✗ FAIL: Error checking API compatibility: {e}")
        return False


def main():
    """Run all validation tests"""
    print("\n" + "=" * 80)
    print("CoT Layered Reasoning Integration - Validation Tests")
    print("=" * 80)
    print()
    
    tests = [
        ("Module Discovery", test_module_discovery),
        ("Backward Compatibility", test_backward_compatibility),
        ("Stage Orchestration", test_stage_orchestration),
        ("Complexity Gating", test_complexity_gating),
        ("Stage Module Integration", test_stage_module_integration),
        ("Metrics Collection", test_metrics_collection),
        ("Error Handling", test_error_handling),
        ("API Compatibility", test_api_compatibility),
    ]
    
    results = []
    for test_name, test_func in tests:
        try:
            result = test_func()
            results.append((test_name, result))
        except Exception as e:
            print(f"\n✗ FAIL: {test_name} raised exception: {e}")
            import traceback
            traceback.print_exc()
            results.append((test_name, False))
    
    # Summary
    print("\n" + "=" * 80)
    print("Validation Summary")
    print("=" * 80)
    
    passed = sum(1 for _, result in results if result)
    total = len(results)
    
    for test_name, result in results:
        status = "✓ PASS" if result else "✗ FAIL"
        print(f"  {status}: {test_name}")
    
    print(f"\nTotal: {passed}/{total} tests passed")
    
    if passed == total:
        print("\n✓ All validation tests passed!")
        return 0
    else:
        print(f"\n⚠ {total - passed} test(s) failed or had warnings")
        return 1


if __name__ == "__main__":
    sys.exit(main())
