---
name: MMLU-style test suite
overview: Create a comprehensive MMLU-style test suite that tests all brain modules and system components (API, client, orchestrator, registry, state storage) with real-time progress display, professional formatting, and detailed pass/fail reporting for identifying improvement areas.
todos:
  - id: create_evaluation_structure
    content: Create evaluation directory structure with __init__.py files and subdirectories (categories/, test_data/, results/)
    status: completed
  - id: implement_test_data_manager
    content: Implement test_data_manager.py for loading and validating JSON/YAML test cases
    status: completed
    dependencies:
      - create_evaluation_structure
  - id: implement_test_results
    content: Implement test_results.py for storing, archiving, and analyzing test results
    status: completed
    dependencies:
      - create_evaluation_structure
  - id: implement_test_reporter
    content: Implement test_reporter.py with real-time progress display, color-coded output, and professional formatting
    status: completed
    dependencies:
      - create_evaluation_structure
  - id: implement_module_tests
    content: Implement categories/module_tests.py for testing all module operations with validation
    status: completed
    dependencies:
      - implement_test_data_manager
  - id: implement_api_tests
    content: Implement categories/api_tests.py for testing all API endpoints
    status: completed
    dependencies:
      - implement_test_data_manager
  - id: implement_client_tests
    content: Implement categories/client_tests.py for testing Python client interface
    status: completed
    dependencies:
      - implement_test_data_manager
  - id: implement_system_tests
    content: Implement categories/system_tests.py for testing registry, orchestrator, state storage, metrics, health
    status: completed
    dependencies:
      - implement_test_data_manager
  - id: implement_reasoning_tests
    content: Implement categories/reasoning_tests.py for reasoning quality evaluation (CoT, MCTS)
    status: completed
    dependencies:
      - implement_test_data_manager
  - id: implement_safety_tests
    content: Implement categories/safety_tests.py for safety and edge case testing
    status: completed
    dependencies:
      - implement_test_data_manager
  - id: implement_test_runner
    content: Implement test_runner.py as main execution engine with test discovery, execution, timeout handling, and metrics collection
    status: completed
    dependencies:
      - implement_module_tests
      - implement_api_tests
      - implement_client_tests
      - implement_system_tests
      - implement_reasoning_tests
      - implement_safety_tests
      - implement_test_results
  - id: create_sample_test_data
    content: Create sample test data files for key modules (chain_of_thought, memory_graph, etc.) as examples
    status: completed
    dependencies:
      - create_evaluation_structure
  - id: add_cli_interface
    content: Add command-line interface to test_runner.py for running tests with options (--module, --category, --report-only, etc.)
    status: completed
    dependencies:
      - implement_test_runner
      - implement_test_reporter
  - id: generate_html_reports
    content: Add HTML report generation to test_reporter.py with professional formatting and charts
    status: completed
    dependencies:
      - implement_test_reporter
      - implement_test_results
---

# MMLU-Style Test Suite for Mavaia Core

## Overview

Create a comprehensive evaluation framework following MMLU (Massive Multitask Language Understanding) principles to test all Mavaia brain modules and system components. The suite will provide real-time progress updates, professional formatting, and detailed pass/fail analysis.

## Architecture

### Test Suite Structure

```
mavaia_core/evaluation/
├── __init__.py
├── test_runner.py              # Main test execution engine
├── test_reporter.py             # Real-time progress and reporting
├── test_data_manager.py         # Test data loading and management
├── test_results.py              # Results storage and analysis
├── categories/
│   ├── __init__.py
│   ├── module_tests.py          # Module-specific test framework
│   ├── api_tests.py             # API endpoint tests
│   ├── client_tests.py          # Python client tests
│   ├── system_tests.py          # System component tests (registry, orchestrator)
│   ├── reasoning_tests.py       # Reasoning quality tests (CoT, MCTS)
│   └── safety_tests.py          # Safety and edge case tests
├── test_data/
│   ├── modules/                 # Module test cases (JSON/YAML)
│   │   ├── chain_of_thought.json
│   │   ├── memory_graph.json
│   │   └── ...
│   ├── api/                     # API test cases
│   ├── reasoning/               # Reasoning benchmark datasets
│   └── safety/                  # Safety test scenarios
└── results/                     # Archived test results
    └── {timestamp}/
        ├── summary.json
        ├── detailed_results.json
        └── report.html
```

## Implementation Details

### 1. Test Data Format (Hybrid Approach)

**JSON/YAML for Test Cases** (`test_data/modules/chain_of_thought.json`):

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
        "query": "Solve: If a train travels 60 mph for 2 hours, how far does it go?",
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
      "timeout": 30.0
    },
    {
      "id": "cot_002",
      "category": "reasoning",
      "operation": "execute_cot",
      "params": {
        "query": "Explain the logical steps in: All men are mortal. Socrates is a man. Therefore...",
        "reasoning_type": "logical"
      },
      "expected": {
        "validation": {
          "type": "reasoning_quality",
          "min_steps": 3,
          "requires_deduction": true
        }
      }
    }
  ]
}
```

**Python for Test Logic** (`categories/module_tests.py`):

- Test execution framework
- Validation logic
- Error handling
- Metrics collection

### 2. Test Runner (`test_runner.py`)

**Key Features**:

- Discovers all modules from `mavaia_core/brain/modules/`
- Loads test data from `test_data/` directories
- Executes tests with timeout handling
- Collects metrics (execution time, success/failure, errors)
- Supports parallel execution (with thread safety)
- Real-time progress updates via `test_reporter.py`

**Core Methods**:

- `discover_test_cases()` - Find all test files
- `run_test_suite()` - Execute all tests
- `run_module_tests(module_name)` - Test specific module
- `run_category_tests(category)` - Test by category (functional, reasoning, safety)
- `validate_result(test_case, result)` - Check pass/fail

### 3. Real-Time Reporter (`test_reporter.py`)

**Features**:

- Live progress display with updating counters
- Color-coded output (green=pass, red=fail, yellow=warning)
- Progress bars for test execution
- Real-time statistics (passed/failed/total, success rate)
- Professional formatting with tables and sections
- Summary dashboard showing:
  - Overall statistics
  - Per-module breakdown
  - Per-category breakdown
  - Top failures
  - Performance metrics

**Output Format**:

```
╔══════════════════════════════════════════════════════════╗
║         Mavaia Core Test Suite - Running...             ║
╠══════════════════════════════════════════════════════════╣
║ Progress: [████████████░░░░░░░░] 60% (120/200 tests)    ║
║                                                          ║
║ Module: chain_of_thought                                 ║
║   ✓ cot_001: execute_cot (0.45s)                       ║
║   ✗ cot_002: execute_cot - Timeout (30.0s)             ║
║   ✓ cot_003: analyze_complexity (0.12s)                 ║
║                                                          ║
║ Statistics:                                              ║
║   Passed:  118  Failed:  2   Skipped:  0                ║
║   Success Rate: 98.3%                                    ║
║   Avg Time: 0.34s                                        ║
╚══════════════════════════════════════════════════════════╝
```

### 4. Test Categories

#### Module Tests (`categories/module_tests.py`)

- Test all operations for each module
- Validate parameter handling
- Test error cases (invalid params, missing params)
- Test edge cases
- Verify metadata correctness

#### API Tests (`categories/api_tests.py`)

- Test all API endpoints (`/v1/modules/*`, `/v1/chat/completions`, etc.)
- Test authentication (if enabled)
- Test request validation
- Test error responses
- Test response formats

#### Client Tests (`categories/client_tests.py`)

- Test Python client interface
- Test module access via `client.brain.module.operation()`
- Test error handling
- Test client initialization

#### System Tests (`categories/system_tests.py`)

- Test ModuleRegistry (discovery, registration, retrieval)
- Test ModuleOrchestrator (dependency resolution, lifecycle)
- Test StateStorage (save, load, delete operations)
- Test MetricsCollector
- Test HealthChecker

#### Reasoning Tests (`categories/reasoning_tests.py`)

- Test Chain-of-Thought reasoning quality
- Test MCTS reasoning
- Test reasoning step validation
- Test complexity detection
- Use reasoning benchmark datasets

#### Safety Tests (`categories/safety_tests.py`)

- Test input sanitization
- Test error handling
- Test resource limits
- Test adversarial inputs
- Test edge cases (empty inputs, very long inputs, etc.)

### 5. Results Management (`test_results.py`)

**Features**:

- Store results in structured format (JSON)
- Archive results with timestamp
- Generate HTML reports
- Track historical trends
- Export to CSV for analysis

**Result Structure**:

```json
{
  "test_run_id": "2025-01-15T10:30:00Z",
  "version": "1.0.0",
  "summary": {
    "total_tests": 200,
    "passed": 195,
    "failed": 5,
    "skipped": 0,
    "success_rate": 0.975,
    "total_time": 45.2
  },
  "by_module": {
    "chain_of_thought": {"passed": 15, "failed": 1, ...},
    ...
  },
  "by_category": {
    "functional": {"passed": 150, "failed": 2, ...},
    "reasoning": {"passed": 30, "failed": 2, ...},
    "safety": {"passed": 15, "failed": 1, ...}
  },
  "failures": [
    {
      "test_id": "cot_002",
      "module": "chain_of_thought",
      "category": "reasoning",
      "error": "Timeout after 30.0s",
      "suggestion": "Check reasoning complexity or increase timeout"
    },
    ...
  ],
  "performance": {
    "avg_execution_time": 0.34,
    "slowest_tests": [...],
    "fastest_tests": [...]
  }
}
```

### 6. Test Data Manager (`test_data_manager.py`)

**Features**:

- Load test cases from JSON/YAML files
- Validate test case structure
- Support for test case templates
- Version control for test data
- Support for test case filtering (by module, category, etc.)

## Usage

### Command-Line Interface

```bash
# Run all tests
python -m mavaia_core.evaluation.test_runner

# Test specific module
python -m mavaia_core.evaluation.test_runner --module chain_of_thought

# Test specific category
python -m mavaia_core.evaluation.test_runner --category reasoning

# Generate report only
python -m mavaia_core.evaluation.test_runner --report-only

# Custom test data directory
python -m mavaia_core.evaluation.test_runner --test-data-dir /path/to/tests
```

### Programmatic Usage

```python
from mavaia_core.evaluation.test_runner import TestRunner
from mavaia_core.evaluation.test_reporter import TestReporter

runner = TestRunner()
reporter = TestReporter()

results = runner.run_test_suite()
reporter.print_summary(results)
reporter.generate_html_report(results, "report.html")
```

## Test Data Creation

### Module Test Cases

For each module, create test cases covering:

1. **Functional Tests**: All operations with valid inputs
2. **Parameter Validation**: Invalid/missing parameters
3. **Edge Cases**: Empty inputs, very long inputs, special characters
4. **Error Handling**: Expected error conditions

### Reasoning Test Cases

Use established reasoning benchmarks:

- Logical reasoning problems
- Mathematical reasoning
- Causal inference
- Analogical reasoning
- Multi-step problem solving

### Safety Test Cases

- Input sanitization tests
- Resource limit tests
- Error recovery tests
- Adversarial input tests

## Integration with Existing Infrastructure

- Use `ModuleRegistry` to discover modules
- Use `MavaiaClient` for client tests
- Use FastAPI TestClient for API tests
- Use existing metrics/health infrastructure for system tests
- Follow evaluation standards from `.cursor/rules/engineering/evaluation_standards.mdc`

## Output and Reporting

1. **Real-time Console Output**: Live progress with formatted tables
2. **JSON Results**: Machine-readable results for analysis
3. **HTML Report**: Professional formatted report with:

   - Executive summary
   - Per-module breakdown
   - Failure analysis
   - Performance metrics
   - Recommendations for improvement

4. **CSV Export**: For spreadsheet analysis

## Success Criteria

- Tests all discovered modules automatically
- Provides clear pass/fail indicators
- Identifies specific areas for improvement
- Tracks performance metrics
- Archives results for historical analysis
- Professional, readable output format