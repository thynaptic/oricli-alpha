# Python Coding Benchmark Test Suite

Comprehensive Python coding benchmark for evaluating Oricli-Alpha's code generation capabilities against industry standards.

## Overview

This benchmark suite tests Oricli-Alpha's Python code generation, completion, and reasoning capabilities across 50 diverse problems covering:

- **Algorithms**: Sorting, searching, dynamic programming, graph algorithms
- **Data Structures**: Trees, heaps, hash tables, linked lists, stacks, queues
- **String Manipulation**: Pattern matching, parsing, text processing
- **Math & Logic**: Mathematical operations, logical reasoning
- **File I/O**: CSV parsing, file operations
- **Classes & Design**: Object-oriented programming, design patterns
- **Recursion**: Recursive algorithms and data structures
- **Optimization**: Performance-critical code

## Benchmark Structure

The benchmark is defined in `test_data/modules/python_coding_benchmark.json` and includes:

- **50 test problems** across multiple difficulty levels (Easy, Medium, Hard)
- **Multiple test cases per problem** for comprehensive validation
- **Code execution validation** - Generated code is executed and tested
- **Industry-standard format** compatible with HumanEval, MBPP, and APPS benchmarks

## Running the Benchmark

### Run All Python Coding Tests

```bash
python -m oricli_core.evaluation.test_runner --module reasoning_code_generator
```

### Run Specific Test Categories

```bash
# Run only easy problems
python -m oricli_core.evaluation.test_runner --module reasoning_code_generator --tags easy

# Run only hard problems
python -m oricli_core.evaluation.test_runner --module reasoning_code_generator --tags hard

# Run specific categories
python -m oricli_core.evaluation.test_runner --module reasoning_code_generator --tags algorithms
```

### Generate Benchmark Report

After running tests, generate a comparison report:

```bash
# Run tests and save results
python -m oricli_core.evaluation.test_runner --module reasoning_code_generator > results.json

# Generate comparison report
python -m oricli_core.evaluation.benchmark_comparison results.json benchmark_report.txt
```

## Test Format

Each test case includes:

```json
{
  "id": "python_001",
  "category": "functional",
  "operation": "generate_code_reasoning",
  "params": {
    "requirements": "Write a function that...",
    "reasoning_method": "cot"
  },
  "expected": {
    "validation": {
      "type": "code_execution",
      "test_cases": [
        {"input": {...}, "expected_output": ...}
      ]
    }
  }
}
```

## Validation

The benchmark uses **code execution validation**:

1. **Code Generation**: Oricli-Alpha generates Python code from requirements
2. **Syntax Validation**: Generated code is checked for syntax errors
3. **Execution**: Code is executed with test inputs
4. **Output Validation**: Actual outputs are compared against expected outputs

## Metrics

The benchmark reports:

- **Pass Rate**: Percentage of problems solved correctly
- **Difficulty Breakdown**: Performance by difficulty level (Easy/Medium/Hard)
- **Category Breakdown**: Performance by problem category
- **Execution Time**: Average and total execution time
- **Comparison**: Comparison with industry benchmarks (HumanEval, MBPP, APPS)

## Industry Comparison

The benchmark compares Oricli-Alpha's performance against:

- **HumanEval**: 164 Python programming problems
- **MBPP**: 974 Python programming problems  
- **APPS**: 10,000 competitive programming problems

Reference scores for comparison:
- GPT-4: 67% (HumanEval), 75% (MBPP), 15% (APPS)
- GPT-3.5: 48% (HumanEval), 56% (MBPP), 8% (APPS)
- Claude-3: 84% (HumanEval), 88% (MBPP), 22% (APPS)

## Example Output

```
================================================================================
MAVAIA PYTHON CODING BENCHMARK REPORT
================================================================================
Generated: 2025-01-15 10:30:00

OVERALL METRICS
--------------------------------------------------------------------------------
Total Problems: 50
Passed: 35 (70.00%)
Failed: 10
Timeout: 3
Error: 2
Skipped: 0
Average Execution Time: 12.34s
Total Execution Time: 617.00s

DIFFICULTY BREAKDOWN
--------------------------------------------------------------------------------
Easy: 15/18 (83.33%)
Medium: 15/22 (68.18%)
Hard: 5/10 (50.00%)

COMPARISON WITH INDUSTRY BENCHMARKS
--------------------------------------------------------------------------------
HumanEval:
  Oricli-Alpha Pass Rate: 70.00%
  vs GPT-4: 67.00% (+3.00% difference) ✓
  vs GPT-3.5: 48.00% (+22.00% difference) ✓
  vs Claude-3: 84.00% (-14.00% difference) ✗
```

## Adding New Tests

To add new test problems:

1. Edit `test_data/modules/python_coding_benchmark.json`
2. Add a new test case with:
   - Unique ID (`python_XXX`)
   - Requirements description
   - Test cases with inputs and expected outputs
   - Appropriate tags (difficulty, category)
3. Run the benchmark to validate

## Notes

- Tests use the `reasoning_code_generator` module
- Code execution uses sandbox isolation for safety
- Timeouts are set per problem based on complexity
- All generated code is validated for syntax before execution
