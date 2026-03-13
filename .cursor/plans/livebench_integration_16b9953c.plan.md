---
name: LiveBench Integration
overview: Integrate LiveBench benchmark suite into Mavaia's evaluation framework as a new test category, enabling automatic testing of all brain modules against LiveBench tasks with direct integration of LiveBench's code_runner for code execution.
todos:
  - id: create_livebench_runner
    content: Create LiveBenchTestRunner class in oricli_core/evaluation/categories/livebench_tests.py with basic structure and imports
    status: completed
  - id: implement_question_loading
    content: Implement LiveBench question loading using load_questions/load_questions_jsonl from livebench.common
    status: completed
    dependencies:
      - create_livebench_runner
  - id: implement_module_mapping
    content: Implement automatic module-to-task mapping logic based on module metadata and task categories
    status: completed
    dependencies:
      - create_livebench_runner
  - id: implement_execution_adapter
    content: Create adapter to convert LiveBench questions to Mavaia module execution format and extract responses
    status: completed
    dependencies:
      - implement_question_loading
      - implement_module_mapping
  - id: integrate_code_runner
    content: Integrate livebench.code_runner.eval.utils for safe code execution in coding tasks
    status: completed
    dependencies:
      - create_livebench_runner
  - id: implement_evaluation
    content: Integrate LiveBench evaluation functions from process_results/ to score module responses
    status: completed
    dependencies:
      - implement_execution_adapter
  - id: implement_result_conversion
    content: Convert LiveBench scores and metadata to TestResult format for consistency with other test categories
    status: completed
    dependencies:
      - implement_evaluation
  - id: integrate_test_runner
    content: Add LiveBench category routing in test_runner.py and register LiveBenchTestRunner
    status: completed
    dependencies:
      - create_livebench_runner
  - id: update_category_exports
    content: Add LiveBenchTestRunner to categories/__init__.py exports
    status: completed
    dependencies:
      - create_livebench_runner
  - id: add_category_documentation
    content: Add livebench category to TEST_CATEGORIES dictionary with description in test_runner.py
    status: completed
    dependencies:
      - integrate_test_runner
---

# LiveBench Integration Plan

## Overview

Integrate LiveBench benchmark suite into Mavaia's evaluation framework, allowing all brain modules to be tested against LiveBench's 18 diverse tasks across 6 categories (reasoning, math, coding, language, data analysis, instruction following).

## Architecture

### 1. Create LiveBench Test Runner

**File**: `oricli_core/evaluation/categories/livebench_tests.py`

- Create `LiveBenchTestRunner` class following the pattern of existing test runners
- Implement `run_test_case()` and `run_test_suite()` methods
- Integrate with LiveBench's question loading (`load_questions`, `load_questions_jsonl`)
- Use LiveBench's evaluation functions from `process_results/` for scoring
- Map Mavaia module operations to LiveBench task types automatically
- Convert LiveBench results to `TestResult` format for consistency

### 2. Integrate Code Runner

**File**: `oricli_core/evaluation/categories/livebench_tests.py`

- Import and use `livebench.code_runner.eval.utils` for code execution
- Wrap code execution in safe environment context managers
- Handle timeouts and resource limits using LiveBench's utilities
- Support both standard coding tasks and agentic coding tasks

### 3. Module-to-Task Mapping

**File**: `oricli_core/evaluation/categories/livebench_tests.py`

- Create automatic mapping logic based on module metadata:
  - Reasoning modules → reasoning tasks (web_of_lies, zebra_puzzle, house_traversal, etc.)
  - Code generation modules → coding tasks (coding_completion, LCB_generation, agentic_coding)
  - Math modules → math tasks (AMPS_Hard, math_competitions, olympiad)
  - Language modules → language tasks
  - Data analysis modules → data_analysis tasks
  - Instruction following modules → instruction_following tasks
- Allow manual override via test configuration

### 4. Test Discovery Integration

**File**: `oricli_core/evaluation/test_data_manager.py` (if needed)

- Optionally extend test discovery to include LiveBench questions
- Or handle LiveBench test discovery directly in `LiveBenchTestRunner`

### 5. Test Runner Integration

**File**: `oricli_core/evaluation/test_runner.py`

- Add `livebench_runner` to lazy initialization (line ~55)
- Add "livebench" to `TEST_CATEGORIES` dictionary (line ~1922)
- Route "livebench" category to `LiveBenchTestRunner` in `run_test_suite()` (around line ~400)
- Add LiveBench to category help text and documentation

### 6. Category Exports

**File**: `oricli_core/evaluation/categories/__init__.py`

- Add `LiveBenchTestRunner` to `__all__`
- Add lazy import for `LiveBenchTestRunner` in `__getattr__`

### 7. Module Execution Adapter

**File**: `oricli_core/evaluation/categories/livebench_tests.py`

- Create adapter to convert LiveBench question format to Mavaia module execution format
- Handle multi-turn conversations for LiveBench questions
- Extract model responses from module execution results
- Format responses for LiveBench evaluation functions

### 8. Result Conversion

**File**: `oricli_core/evaluation/categories/livebench_tests.py`

- Convert LiveBench scores (0/1 or multi-score) to TestResult status
- Preserve LiveBench metadata (task, category, question_id) in TestResult
- Map LiveBench errors to appropriate TestStatus values

## Implementation Details

### LiveBench Question Format

```python
{
    "question_id": "...",
    "category": "reasoning",
    "task": "web_of_lies_v2",
    "turns": ["question text..."],
    "ground_truth": "expected answer",
    "livebench_release_date": "2024-07-26"
}
```

### Module Execution Flow

1. Load LiveBench questions for relevant tasks
2. For each question:

   - Map to appropriate Mavaia module based on task category
   - Convert question to module operation parameters
   - Execute module operation
   - Extract response from module result
   - Evaluate using LiveBench's scoring functions
   - Convert to TestResult

### Code Execution Integration

- Use `livebench.code_runner.eval.utils` for safe code execution
- Apply reliability guards and timeout limits
- Handle code execution errors gracefully
- Support both standard and agentic coding evaluations

## Files to Create/Modify

### New Files

- `oricli_core/evaluation/categories/livebench_tests.py` - Main LiveBench test runner

### Modified Files

- `oricli_core/evaluation/test_runner.py` - Add LiveBench category routing
- `oricli_core/evaluation/categories/__init__.py` - Export LiveBenchTestRunner

## Dependencies

- LiveBench package (already installed in `.venv`)
- Existing Mavaia evaluation framework components
- LiveBench's `code_runner` utilities

## Testing Strategy

1. Test with a single LiveBench task first (e.g., web_of_lies_v2)
2. Verify module-to-task mapping works correctly
3. Test code execution integration with coding tasks
4. Verify result conversion and reporting
5. Test with multiple categories and tasks

## Configuration Options

- `--category livebench` - Run all LiveBench tests
- `--category livebench --module <module_name>` - Test specific module against LiveBench
- Support LiveBench-specific options (question_source, bench_name, etc.) via test configuration