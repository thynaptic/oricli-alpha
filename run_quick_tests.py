#!/usr/bin/env python3
"""
Quick test script to verify fixes for chain_of_thought and memory_graph modules
"""
import sys
from pathlib import Path

# Add project to path
sys.path.insert(0, str(Path(__file__).parent))

from oricli_core.evaluation.test_runner import TestRunner
from oricli_core.evaluation.test_data_manager import TestDataManager

def main():
    print("Loading test data...", flush=True)
    manager = TestDataManager()
    manager.load_all_test_suites()
    
    # Get specific test cases that were failing
    cot_tests = [tc for tc in manager.get_test_cases() 
                 if tc.module == 'chain_of_thought' and tc.category == 'functional']
    mg_tests = [tc for tc in manager.get_test_cases() 
                if tc.module == 'memory_graph' and tc.category == 'functional']
    
    print(f"Found {len(cot_tests)} CoT tests and {len(mg_tests)} memory_graph tests\n", flush=True)
    
    from oricli_core.evaluation.categories.module_tests import ModuleTestRunner
    module_runner = ModuleTestRunner()
    
    results = []
    
    # Run CoT tests
    if cot_tests:
        print("=== Running Chain of Thought tests ===", flush=True)
        for test in cot_tests:
            result = module_runner.run_test_case(test, timeout=30.0)
            results.append(result)
            status = '✓ PASS' if result.status.value == 'PASSED' else '✗ FAIL'
            msg = result.error_message or "OK"
            print(f"  {test.id}: {status} - {msg}", flush=True)
    
    # Run memory_graph tests  
    if mg_tests:
        print("\n=== Running Memory Graph tests ===", flush=True)
        for test in mg_tests:
            result = module_runner.run_test_case(test, timeout=10.0)
            results.append(result)
            status = '✓ PASS' if result.status.value == 'PASSED' else '✗ FAIL'
            msg = result.error_message or "OK"
            print(f"  {test.id}: {status} - {msg}", flush=True)
    
    # Summary
    passed = sum(1 for r in results if r.status.value == 'PASSED')
    total = len(results)
    print(f"\n=== Summary ===", flush=True)
    print(f"Passed: {passed}/{total} ({passed*100//total if total > 0 else 0}%)", flush=True)
    
    if passed == total:
        print("All tests passed! ✓", flush=True)
        return 0
    else:
        print(f"{total - passed} test(s) failed", flush=True)
        return 1

if __name__ == '__main__':
    sys.exit(main())
