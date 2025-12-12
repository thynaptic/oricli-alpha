# Mavaia Core Evaluation Framework

MMLU-style test suite for comprehensive evaluation of all Mavaia brain modules and system components.

## Overview

This evaluation framework provides:
- **Real-time progress display** with color-coded output
- **Professional formatting** with tables and statistics
- **Detailed pass/fail reporting** to identify improvement areas
- **Multiple test categories**: functional, reasoning, safety, API, client, system
- **HTML report generation** with charts and analysis
- **Test result archiving** for historical tracking

## Quick Start

### Run All Tests

```bash
python -m mavaia_core.evaluation.test_runner
```

### Run Tests for Specific Module

```bash
python -m mavaia_core.evaluation.test_runner --module chain_of_thought
```

### Run Tests by Category

```bash
python -m mavaia_core.evaluation.test_runner --category reasoning
```

### Generate Report from Existing Results

```bash
python -m mavaia_core.evaluation.test_runner --report-only results/20250115_103000/detailed_results.json
```

## Test Data Format

Test cases are defined in JSON (or YAML) files in the `test_data/` directory.

### Example Test Case

```json
{
  "module": "chain_of_thought",
  "version": "1.0.0",
  "test_suite": [
    {
      "id": "cot_001",
      "category": "functional",
      "operation": "execute_cot",
      "params": {
        "query": "If a train travels 60 mph for 2 hours, how far does it go?",
        "reasoning_type": "analytical"
      },
      "expected": {
        "result_type": "dict",
        "required_fields": ["reasoning", "conclusion"],
        "validation": {
          "type": "contains",
          "field": "conclusion",
          "value": "120"
        }
      },
      "timeout": 30.0,
      "description": "Basic mathematical reasoning test"
    }
  ]
}
```

## Test Categories

- **functional**: Test module operations with valid inputs
- **reasoning**: Test reasoning quality (CoT, MCTS, etc.)
- **safety**: Test safety mechanisms and edge cases
- **api**: Test HTTP API endpoints
- **client**: Test Python client interface
- **system**: Test core system components (registry, orchestrator, etc.)

## Programmatic Usage

```python
from mavaia_core.evaluation.test_runner import TestRunner
from mavaia_core.evaluation.test_reporter import TestReporter

# Create evaluation framework
runner = TestRunner()

# Run all tests
results = runner.run_test_suite()

# Generate HTML report
report_path = runner.generate_report(results)
print(f"Report: {report_path}")

# Save results
archive_path = runner.save_results(results, archive=True)
print(f"Results: {archive_path}")
```

## Output

The test suite provides:

1. **Real-time Console Output**: Live progress with formatted tables
2. **JSON Results**: Machine-readable results for analysis
3. **HTML Report**: Professional formatted report with:
   - Executive summary
   - Per-module breakdown
   - Per-category breakdown
   - Failure analysis
   - Performance metrics
   - Recommendations for improvement

## Directory Structure

```
mavaia_core/evaluation/
├── __init__.py
├── test_runner.py              # Main test execution engine
├── test_reporter.py             # Real-time progress and reporting
├── test_data_manager.py         # Test data loading and management
├── test_results.py              # Results storage and analysis
├── categories/                  # Test category runners
│   ├── module_tests.py
│   ├── api_tests.py
│   ├── client_tests.py
│   ├── system_tests.py
│   ├── reasoning_tests.py
│   └── safety_tests.py
├── test_data/                   # Test case files
│   ├── modules/
│   ├── api/
│   ├── reasoning/
│   └── safety/
└── results/                      # Archived test results
```

## Adding New Test Cases

1. Create or edit a JSON file in `test_data/` directory
2. Follow the test case format (see example above)
3. Run the test suite to execute your new tests

## Requirements

- Python 3.8+
- httpx (for API tests)
- PyYAML (optional, for YAML test files)

Install optional dependencies:
```bash
pip install pyyaml
```

