#!/usr/bin/env python3
"""
Run tests and generate industry comparison report
"""
import sys
from pathlib import Path

# Add project to path
sys.path.insert(0, str(Path(__file__).parent))

from oricli_core.evaluation.test_runner import TestRunner

def main():
    print("=" * 80)
    print("Running OricliAlpha Test Suite")
    print("=" * 80)
    print()
    
    # Create test runner
    runner = TestRunner(verbose=True, use_colors=False)
    
    # Run all test categories
    categories = ['functional', 'reasoning', 'safety', 'api', 'client', 'system']
    
    from oricli_core.evaluation.test_results import TestRunResults, TestStatus
    from datetime import datetime, timezone
    import uuid
    
    all_results = []
    for category in categories:
        print(f"\n{'=' * 80}")
        print(f"Running {category.upper()} tests...")
        print('=' * 80)
        try:
            results = runner.run_test_suite(category=category)
            if results and hasattr(results, 'results'):
                all_results.extend(results.results)
                passed = sum(1 for r in results.results if r.status == TestStatus.PASSED)
                total = len(results.results)
                print(f"\n{category}: {passed}/{total} passed ({passed*100//total if total > 0 else 0}%)")
        except Exception as e:
            print(f"Error running {category}: {e}")
            import traceback
            traceback.print_exc()
    
    if not all_results:
        print("\nNo test results generated. Exiting.")
        return 1
    
    # Create proper TestRunResults object
    combined_results = TestRunResults(
        test_run_id=str(uuid.uuid4()),
        version="1.0.0",
        timestamp=datetime.now(timezone.utc).isoformat(),
    )
    combined_results.results = all_results
    combined_results.compute_statistics()
    
    # Save results
    print(f"\n{'=' * 80}")
    print("Saving results...")
    print('=' * 80)
    archive_path = runner.save_results(
        combined_results,
        archive=True
    )
    print(f"Results saved to: {archive_path}")
    
    # Generate industry comparison
    print(f"\n{'=' * 80}")
    print("Generating Industry Comparison Report...")
    print('=' * 80)
    
    from oricli_core.evaluation.industry_comparison import IndustryComparison
    from pathlib import Path
    
    results_file = Path(archive_path) / "detailed_results.json"
    if not results_file.exists():
        print(f"Error: Results file not found: {results_file}")
        return 1
    
    comparison = IndustryComparison()
    results = comparison.load_results(results_file)
    
    if not results:
        print(f"Error: Could not load results from {results_file}")
        return 1
    
    metrics = comparison.calculate_metrics(results)
    output_file = Path("industry_comparison_report.txt")
    report = comparison.generate_report(output_file)
    
    print("\n" + report)
    print(f"\n📊 Industry comparison report saved to: {output_file}")
    
    return 0

if __name__ == '__main__':
    sys.exit(main())
