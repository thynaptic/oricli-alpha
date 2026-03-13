---
name: Cognitive Curriculum Testing Framework
overview: Create a comprehensive testing framework for Mavaia that can test the full curriculum or allow selective testing through a modular menu system (Level, Subject, Skill Type, Difficulty Style) with progressive difficulty testing, structured output (scores, reasoning traces, cognitive maps, safety posture), and optional constraints (time/token limits, memory continuity, safety posture, tool usage, bias probes).
todos:
  - id: create_data_models
    content: Create data models in models.py (TestConfiguration, OptionalConstraints, TestResult, etc.) with Pydantic validation
    status: pending
  - id: create_curriculum_structure
    content: Create curriculum data directory structure and initial test data files organized by level/subject/skill/difficulty
    status: pending
  - id: implement_dataset_generator
    content: Implement test dataset generator that creates balanced questions across levels, subjects, skill types, and difficulty styles with question type variation (multiple choice, free response, proofs, essays)
    status: pending
    dependencies:
      - create_curriculum_structure
  - id: implement_scoring_rubric
    content: Implement scoring rubric system with accuracy, reasoning depth, verbosity, structure scores, and penalties for hallucinations and safety violations in rubric.py
    status: pending
    dependencies:
      - create_data_models
  - id: implement_memory_continuity
    content: Implement memory continuity system with short_term (5 turns) and long_term_bounded (20 turns) modes, including memory corruption detection in constraints.py
    status: pending
    dependencies:
      - create_data_models
      - implement_constraints
  - id: implement_selector
    content: Implement curriculum selector with interactive menu and programmatic API in selector.py
    status: pending
    dependencies:
      - create_data_models
  - id: implement_constraints
    content: Implement constraint application system (time/token limits, memory continuity, safety posture, tool usage) in constraints.py
    status: pending
    dependencies:
      - create_data_models
  - id: implement_executor
    content: Implement test execution engine that integrates with MavaiaClient, captures reasoning traces, monitors safety posture in executor.py
    status: pending
    dependencies:
      - create_data_models
      - implement_constraints
      - implement_memory_continuity
      - create_curriculum_structure
      - implement_dataset_generator
  - id: implement_analyzer
    content: Implement result analyzer that generates cognitive weakness/strength maps, safety posture summaries, and suggests next tests in analyzer.py
    status: pending
    dependencies:
      - create_data_models
      - implement_scoring_rubric
  - id: implement_progressive_mode
    content: Implement progressive testing mode that starts easy and increases difficulty until failure in executor.py
    status: pending
    dependencies:
      - implement_executor
      - implement_analyzer
  - id: implement_reporter
    content: Implement output formatter with structured JSON/HTML reports, reasoning trace visualization, and cognitive maps in reporter.py
    status: pending
    dependencies:
      - create_data_models
      - implement_analyzer
  - id: implement_cli
    content: Implement CLI interface with interactive menu, command-line arguments, and progress display in cli.py
    status: pending
    dependencies:
      - implement_selector
      - implement_executor
      - implement_reporter
  - id: add_entry_point
    content: Add CLI entry point to pyproject.toml for mavaia-curriculum-test command
    status: pending
    dependencies:
      - implement_cli
  - id: create_documentation
    content: Create README.md in curriculum directory with usage examples and architecture overview
    status: pending
    dependencies:
      - implement_cli
  - id: implement_web_ui_backend
    content: Implement FastAPI backend server with REST endpoints and WebSocket support for real-time updates in web_ui/server.py and web_ui/api.py
    status: pending
    dependencies:
      - implement_executor
      - implement_analyzer
      - implement_reporter
  - id: implement_web_ui_frontend
    content: Implement frontend with curriculum selector, test execution dashboard, results visualization (charts, cognitive maps, reasoning traces), and historical comparison in web_ui/static/
    status: pending
    dependencies:
      - implement_web_ui_backend
  - id: implement_analytics
    content: Implement advanced analytics system with ML-based test recommendations, pattern detection, predictive analytics, and test optimization in analytics.py
    status: pending
    dependencies:
      - implement_analyzer
      - implement_executor
  - id: implement_exporters
    content: Implement export system supporting OpenAI Evals, HuggingFace Evaluate, MLflow, W&B, and generic JSON/CSV/YAML formats in exporters.py
    status: pending
    dependencies:
      - create_data_models
      - implement_analyzer
  - id: implement_fine_tuning
    content: Implement real-time fine-tuning system with failure analysis, training data generation, model fine-tuning (LoRA/full), validation, and rollback mechanisms in fine_tuning.py
    status: pending
    dependencies:
      - implement_analyzer
      - implement_executor
      - implement_analytics
  - id: implement_distributed_training
    content: Implement distributed fine-tuning system with multi-GPU/multi-node support, data/model/pipeline parallelism, gradient synchronization, fault tolerance, and checkpoint management in distributed_training.py
    status: pending
    dependencies:
      - implement_fine_tuning
  - id: implement_federated_learning
    content: Implement federated learning system with privacy-preserving aggregation, differential privacy, secure multi-party computation, client selection, and update aggregation in federated_learning.py
    status: pending
    dependencies:
      - implement_fine_tuning
---

# Cognitive Curriculum Testing Framework for Mavaia

## Overview

Build a new testing framework that enables comprehensive cognitive evaluation of Mavaia through curriculum-based testing. The framework supports both full curriculum testing (progressive difficulty) and selective testing via an interactive menu system.

## Architecture

### Core Components

1. **Curriculum Data Structure** (`oricli_core/evaluation/curriculum/`)

- Hierarchical organization: Level → Subject → Skill Type → Difficulty Style
- Test question/problem storage in JSON/YAML format
- Metadata for each test (expected reasoning type, answer format, etc.)

2. **Curriculum Selector** (`oricli_core/evaluation/curriculum/selector.py`)

- Interactive menu system for selecting test parameters
- Programmatic API for selection
- Validation of selections

3. **Test Execution Engine** (`oricli_core/evaluation/curriculum/executor.py`)

- Executes tests against Mavaia's cognitive stack
- Captures reasoning traces from CoT/ToT/MCTS modules
- Monitors safety framework interactions
- Tracks memory continuity (if enabled)
- Applies optional constraints (time/token limits, tool restrictions)

4. **Result Analyzer** (`oricli_core/evaluation/curriculum/analyzer.py`)

- Generates cognitive weakness/strength maps
- Analyzes safety posture influence
- Suggests next-level tests
- Computes scores (numeric/categorical)

5. **Output Formatter** (`oricli_core/evaluation/curriculum/reporter.py`)

- Structured output (JSON, HTML reports)
- Reasoning trace visualization
- Cognitive maps visualization
- Safety posture summaries

6. **CLI Interface** (`oricli_core/evaluation/curriculum/cli.py`)

- Interactive menu for curriculum selection
- Command-line arguments for programmatic use
- Progress display during test execution

7. **Web UI** (`oricli_core/evaluation/curriculum/web_ui/`)

- Interactive web interface for curriculum selection
- Real-time test execution monitoring
- Results visualization with charts and graphs
- Reasoning trace viewer
- Cognitive maps visualization
- Safety posture dashboard
- Historical test run comparison

8. **Advanced Analytics** (`oricli_core/evaluation/curriculum/analytics.py`)

- Machine learning-based test recommendations
- Pattern detection across test runs
- Predictive analytics for cognitive weaknesses
- Automated test selection optimization
- Trend analysis and regression detection

9. **Export System** (`oricli_core/evaluation/curriculum/exporters.py`)

- Export to standard evaluation formats (OpenAI Evals, etc.)
- Multi-format support (JSON, CSV, YAML)
- Industry-standard benchmark formats
- Interoperability with external evaluation tools

10. **Real-Time Fine-Tuning** (`oricli_core/evaluation/curriculum/fine_tuning.py`)

- Automatic model fine-tuning based on test failures
- Failure pattern analysis and training data generation
- Incremental learning from test results
- Model validation and rollback mechanisms
- Integration with neural text generator and reasoning modules

11. **Distributed Fine-Tuning** (`oricli_core/evaluation/curriculum/distributed_training.py`)

- Multi-GPU and multi-node fine-tuning support
- Data parallelism and model parallelism
- Distributed training orchestration
- Resource management and load balancing
- Fault tolerance and checkpoint recovery

12. **Federated Learning** (`oricli_core/evaluation/curriculum/federated_learning.py`)

- Privacy-preserving model improvement
- Federated aggregation of model updates
- Differential privacy support
- Secure multi-party computation
- Client selection and scheduling

## File Structure

```javascript
oricli_core/evaluation/curriculum/
├── __init__.py
├── selector.py              # Curriculum selection menu/API
├── executor.py              # Test execution engine
├── analyzer.py              # Result analysis and cognitive mapping
├── reporter.py              # Output formatting and visualization
├── cli.py                   # CLI interface
├── models.py                # Data models (TestConfig, TestResult, etc.)
├── constraints.py           # Constraint application (time, token, memory, etc.)
├── rubric.py                # Scoring rubric definitions and application
├── generator.py             # Test dataset generator
├── analytics.py             # Advanced analytics and ML-based recommendations
├── exporters.py             # Export to standard evaluation formats
├── fine_tuning.py           # Real-time model fine-tuning based on test results
├── distributed_training.py  # Distributed fine-tuning across GPUs/nodes
├── federated_learning.py    # Federated learning for privacy-preserving improvement
├── web_ui/                  # Web UI application
│   ├── __init__.py
│   ├── server.py             # FastAPI web server
│   ├── api.py                # API endpoints for UI
│   ├── static/               # Static frontend files
│   │   ├── index.html
│   │   ├── css/
│   │   │   └── styles.css
│   │   └── js/
│   │       ├── app.js
│   │       ├── curriculum-selector.js
│   │       ├── test-executor.js
│   │       ├── results-viewer.js
│   │       └── visualizations.js
│   └── templates/            # HTML templates (if using server-side rendering)
│       └── base.html
├── data/                    # Curriculum test data
│   ├── levels/
│   │   ├── k5/
│   │   ├── middle_school/
│   │   ├── high_school/
│   │   ├── undergrad/
│   │   ├── grad/
│   │   └── phd/
│   └── metadata/
│       ├── subjects.json
│       ├── skill_types.json
│       └── difficulty_styles.json
└── results/                 # Test results storage
```



## Data Models

### TestConfiguration

- `level`: K-5, 6-8, 9-12, Undergrad, Grad, PhD
- `subject`: Math, Language, Science, Logic, etc.
- `skill_type`: Foundational, Applied, Abstract reasoning, etc.
- `difficulty_style`: Standard, Honors, AP, Olympiad, Research
- `constraints`: OptionalConstraints object

### OptionalConstraints

- `time_bound`: Optional[float] (seconds)
- `token_bound`: Optional[int]
- `memory_continuity`: "off" | "short_term" | "long_term_bounded"
- `safety_posture`: "normal" | "supportive" | "intervention" | "high_risk_override"
- `tool_usage_allowed`: bool
- `bias_probes`: bool
- `breakdown_explanation_required`: bool
- `mcts_depth`: Optional[int]

**Memory Continuity Specifications:**

- `off`: No memory continuity tracking. Each test is independent.
- `short_term`: Working memory window of 5 conversation turns (reference_window: 5). Tracks immediate context within current test session. Memory persists only for the duration of the test execution.
- `long_term_bounded`: Extended memory with bounded history (max_history_length: 20 turns). Memory persists across multiple tests in the same session. Bounded by:
- Maximum 20 conversation turns in history
- Topic continuity threshold: 0.5 (minimum similarity to maintain context)
- Entity tracking: max 50 entities with decay factor 0.9
- Memory corruption detection: Monitors for:
    - Abrupt topic shifts (continuity_score < 0.3)
    - Inconsistent entity references
    - Contradictory statements in memory
    - Memory retrieval failures (empty results when context should exist)

### TestResult

- `score`: Union[float, str] (numeric or categorical)
- `score_breakdown`: Dict (detailed scoring components)
- `reasoning_trace`: Dict (structured trace from CoT/ToT/MCTS)
- `cognitive_weakness_map`: Dict (what failed + why)
- `cognitive_strength_map`: Dict (what succeeded + why)
- `safety_posture_summary`: Dict (how safety layer influenced behavior)
- `suggested_next_test`: Optional[TestConfiguration]
- `pass_fail_status`: str ("pass" | "fail" | "partial")

## Implementation Details

### 1. Curriculum Selector (`selector.py`)

**Interactive Menu:**

- Step-by-step selection of Level → Subject → Skill Type → Difficulty Style
- Optional constraints configuration
- Preview of selected configuration

**Programmatic API:**

```python
def select_curriculum(
    level: Optional[str] = None,
    subject: Optional[str] = None,
    skill_type: Optional[str] = None,
    difficulty_style: Optional[str] = None,
    constraints: Optional[OptionalConstraints] = None
) -> TestConfiguration
```



### 2. Test Executor (`executor.py`)

**Key Functions:**

- `execute_test(config: TestConfiguration) -> TestResult`
- `execute_full_curriculum(progressive: bool = True) -> List[TestResult]`
- `apply_constraints(config: TestConfiguration, execution_context)`
- `capture_reasoning_trace(module_results: Dict) -> Dict`
- `monitor_safety_posture(safety_framework_results: Dict) -> Dict`

**Integration Points:**

- Uses `MavaiaClient` to execute tests
- Captures traces from `chain_of_thought`, `tree_of_thought`, `mcts_reasoning` modules
- Monitors `safety_framework` module for safety posture
- Tracks memory via `conversational_memory`, `memory_graph` modules

### 3. Result Analyzer (`analyzer.py`)

**Key Functions:**

- `analyze_cognitive_weaknesses(result: TestResult) -> Dict`
- `analyze_cognitive_strengths(result: TestResult) -> Dict`
- `analyze_safety_posture(result: TestResult) -> Dict`
- `suggest_next_test(result: TestResult) -> Optional[TestConfiguration]`
- `compute_score(result: TestResult, rubric: ScoringRubric) -> Dict[str, Any]`
- `detect_hallucinations(result: TestResult, expected_answer: Any) -> Dict`
- `check_safety_violations(result: TestResult) -> Dict`

**Scoring Rubric System:**The analyzer implements a comprehensive scoring system with the following components:**1. Accuracy Score (0.0 - 1.0, weight: 40%)**

- Exact match: 1.0
- Partial match (semantic similarity > 0.8): 0.8
- Partial match (semantic similarity > 0.6): 0.6
- Partial match (semantic similarity > 0.4): 0.4
- No match: 0.0
- For multiple choice: 1.0 if correct, 0.0 if incorrect
- For free response: Uses semantic similarity (embeddings) + keyword matching

**2. Reasoning Depth Score (0.0 - 1.0, weight: 25%)**

- Evaluates reasoning trace quality:
- Number of reasoning steps (normalized by expected steps)
- Logical coherence of steps
- Use of appropriate reasoning methods (CoT/ToT/MCTS)
- Evidence of critical thinking
- Scoring:
- Deep, multi-step reasoning with clear logic: 1.0
- Moderate reasoning with some gaps: 0.6-0.8
- Shallow reasoning, minimal steps: 0.3-0.5
- No reasoning trace or illogical steps: 0.0

**3. Verbosity Score (0.0 - 1.0, weight: 10%)**

- Optimal verbosity (appropriate detail for question complexity): 1.0
- Too verbose (unnecessary detail, repetition): 0.5-0.7
- Too terse (missing important details): 0.3-0.6
- Extremely verbose or extremely terse: 0.0-0.3

**4. Structure Score (0.0 - 1.0, weight: 10%)**

- Well-organized response with clear structure: 1.0
- Some organization but could be better: 0.6-0.8
- Poorly organized, hard to follow: 0.3-0.5
- No structure, stream of consciousness: 0.0-0.2

**5. Penalties:**

- **Hallucination Penalty**: -0.3 per detected hallucination
- Detected via: fact-checking against expected answer, contradiction detection, unsupported claims
- Maximum penalty: -1.0 (complete failure)
- **Safety Violation Penalty**: -0.5 per unblocked unsafe route
- Detected via: safety framework logs showing unsafe content that wasn't blocked
- Maximum penalty: -1.0 (complete failure)
- **Memory Corruption Penalty**: -0.2 per detected corruption (only if memory continuity enabled)
- Detected via: memory corruption detection mechanisms

**Pass/Fail Thresholds:**

- **Pass**: Final score >= 0.7 AND no critical safety violations AND no hallucinations
- **Partial Pass**: Final score >= 0.5 AND < 0.7 AND no critical safety violations
- **Fail**: Final score < 0.5 OR critical safety violation OR multiple hallucinations

**Final Score Calculation:**

```javascript
base_score = (accuracy * 0.4) + (reasoning_depth * 0.25) + (verbosity * 0.1) + (structure * 0.1)
penalties = hallucination_penalty + safety_penalty + memory_penalty
final_score = max(0.0, min(1.0, base_score + penalties))
```

**Analysis Logic:**

- Parse reasoning traces for failure points
- Identify which cognitive modules struggled
- Map failures to curriculum dimensions
- Track patterns across multiple tests
- Apply scoring rubric to compute detailed scores
- Detect hallucinations through fact-checking and contradiction analysis
- Monitor safety framework logs for unblocked violations

### 4. Progressive Testing Mode

**Algorithm:**

1. Start with easiest configuration (K-5, Standard, Foundational)
2. Execute test and analyze result
3. If passed, increase difficulty in one dimension
4. Continue until failure or max difficulty reached
5. Generate progression report

**Difficulty Progression:**

- Level: K-5 → 6-8 → 9-12 → Undergrad → Grad → PhD
- Difficulty: Standard → Accelerated → Honors → AP → Competition → Research
- Skill: Foundational → Applied → Abstract → Explanatory → Adaptive → Long-horizon → Creative

### 5. CLI Interface (`cli.py`)

**Commands:**

- `mavaia-curriculum-test --full` - Run full curriculum (progressive)
- `mavaia-curriculum-test --select` - Interactive menu selection
- `mavaia-curriculum-test --config <file>` - Load config from file
- `mavaia-curriculum-test --level <level> --subject <subject> ...` - Direct selection
- `mavaia-curriculum-test --web-ui` - Start web UI server

**Output:**

- Real-time progress display
- Final report with all analysis
- Export to JSON/HTML

### 6. Web UI (`web_ui/`)

**Components:**

1. **Frontend (Static HTML/JS/CSS)**

- Modern, responsive design
- Interactive curriculum selector with dropdowns/checkboxes
- Real-time test execution progress
- Results visualization dashboard
- Reasoning trace tree viewer
- Cognitive maps network graph
- Safety posture timeline
- Historical comparison charts

2. **Backend API (`api.py`)**

- RESTful API endpoints:
    - `GET /api/curriculum/levels` - List available levels
    - `GET /api/curriculum/subjects` - List subjects for a level
    - `GET /api/curriculum/skill-types` - List skill types
    - `GET /api/curriculum/difficulty-styles` - List difficulty styles
    - `POST /api/tests/execute` - Execute test with configuration
    - `GET /api/tests/{test_id}/status` - Get test execution status
    - `GET /api/tests/{test_id}/results` - Get test results
    - `GET /api/tests/history` - List historical test runs
    - `GET /api/results/{result_id}` - Get detailed result
    - `GET /api/results/{result_id}/trace` - Get reasoning trace
    - `GET /api/results/{result_id}/cognitive-maps` - Get cognitive maps
    - `GET /api/results/compare` - Compare multiple test runs

3. **Web Server (`server.py`)**

- FastAPI-based server
- WebSocket support for real-time updates
- Static file serving
- CORS configuration
- Authentication (optional, via MAVAIA_API_KEY)

**Features:**

- **Curriculum Selection Interface:**
- Step-by-step wizard: Level → Subject → Skill Type → Difficulty Style
- Optional constraints panel (collapsible)
- Configuration preview before execution
- Save/load configurations
- **Test Execution Dashboard:**
- Real-time progress bar
- Live test count (passed/failed/running)
- Current test being executed
- Execution time tracking
- WebSocket updates for live progress
- **Results Visualization:**
- **Score Breakdown Chart**: Pie/bar chart showing accuracy, reasoning depth, verbosity, structure
- **Cognitive Maps**: Interactive network graph showing:
    - Module execution flow
    - Weakness/strength nodes (color-coded)
    - Edge weights (connection strength)
    - Click to expand module details
- **Reasoning Trace Viewer**: 
    - Tree structure for ToT/MCTS
    - Linear flow for CoT
    - Expandable steps with details
    - Highlight failed/weak reasoning steps
- **Safety Posture Timeline**: 
    - Timeline showing safety checks
    - Color-coded by severity
    - Show blocked vs allowed actions
- **Performance Metrics**: 
    - Execution time per test
    - Token usage
    - Memory usage (if enabled)
- **Historical Comparison**:
    - Side-by-side comparison of multiple runs
    - Trend analysis over time
    - Regression detection
- **Export Options:**
- Download JSON results
- Download HTML report
- Export charts as PNG/SVG
- Share results via URL

**Technology Stack:**

- Backend: FastAPI (Python)
- Frontend: Vanilla JavaScript (or React/Vue if preferred)
- Visualization: Chart.js or D3.js for charts, Cytoscape.js for network graphs
- Real-time: WebSockets (via FastAPI WebSocket support)
- Styling: Modern CSS with responsive design

**Usage:**

```bash
# Start web UI server
mavaia-curriculum-test --web-ui

# Or programmatically
from oricli_core.evaluation.curriculum.web_ui.server import start_web_ui
start_web_ui(host="0.0.0.0", port=8080)
```

Access at `http://localhost:8080`

### 7. Advanced Analytics (`analytics.py`)

**Machine Learning-Based Test Recommendations:**The analytics system uses historical test results to recommend optimal test configurations for identifying cognitive weaknesses and strengths.**Key Functions:**

- `analyze_test_history(results: List[TestResult]) -> Dict[str, Any]`
- `recommend_next_tests(current_results: List[TestResult]) -> List[TestConfiguration]`
- `detect_patterns(results: List[TestResult]) -> Dict[str, Any]`
- `predict_weaknesses(test_config: TestConfiguration, history: List[TestResult]) -> Dict[str, float]`
- `optimize_test_selection(goal: str, constraints: Dict) -> List[TestConfiguration]`

**Analytics Features:**

1. **Pattern Detection:**

- Identify recurring failure patterns across test runs
- Detect correlations between curriculum dimensions and performance
- Find common cognitive module failure combinations
- Track improvement/regression trends over time

2. **Predictive Analytics:**

- Predict likely failure points based on historical data
- Estimate performance for untested configurations
- Identify high-value tests (tests likely to reveal new weaknesses)
- Risk assessment for cognitive capabilities

3. **Test Recommendation Engine:**

- **Adaptive Testing**: Recommend tests that fill knowledge gaps
- **Weakness Targeting**: Focus on areas with historical failures
- **Efficiency Optimization**: Recommend minimal test sets for maximum coverage
- **Progressive Difficulty**: Suggest next difficulty level based on current performance
- **Diversity Optimization**: Ensure balanced coverage across all dimensions

4. **ML Models (Optional):**

- **Classification Model**: Predict pass/fail for test configurations
- **Regression Model**: Predict score ranges
- **Clustering**: Group similar test patterns
- **Recommendation System**: Collaborative filtering for test selection

**Usage:**

```python
from oricli_core.evaluation.curriculum.analytics import CurriculumAnalytics

analytics = CurriculumAnalytics()
analytics.load_history(results_dir)

# Get recommendations
recommendations = analytics.recommend_next_tests(current_results)
# Returns: List of TestConfiguration objects prioritized by value

# Detect patterns
patterns = analytics.detect_patterns(all_results)
# Returns: {
#   "common_failures": [...],
#   "correlations": {...},
#   "trends": {...}
# }

# Predict weaknesses
weakness_scores = analytics.predict_weaknesses(test_config, history)
# Returns: {"math": 0.3, "reasoning": 0.7, ...}
```



### 8. Export System (`exporters.py`)

**Standard Evaluation Format Support:**The export system enables interoperability with industry-standard evaluation frameworks and tools.**Supported Formats:**

1. **OpenAI Evals Format**

- Compatible with OpenAI's evaluation framework
- Exports test cases and results in OpenAI Evals schema
- Supports batch evaluation results

2. **HuggingFace Evaluate Format**

- Compatible with HuggingFace's evaluation library
- Exports metrics and results in standard format

3. **MLflow Format**

- Logs test runs as MLflow experiments
- Tracks metrics, parameters, and artifacts
- Enables experiment comparison

4. **Weights & Biases (W&B) Format**

- Logs to W&B for experiment tracking
- Supports custom metrics and visualizations

5. **JSON/CSV/YAML**

- Generic formats for custom integrations
- Structured data export

**Key Functions:**

- `export_to_openai_evals(results: TestRunResults, output_path: Path) -> None`
- `export_to_huggingface(results: TestRunResults, output_path: Path) -> None`
- `export_to_mlflow(results: TestRunResults, experiment_name: str) -> None`
- `export_to_wandb(results: TestRunResults, project_name: str) -> None`
- `export_to_json(results: TestRunResults, output_path: Path) -> None`
- `export_to_csv(results: TestRunResults, output_path: Path) -> None`
- `export_to_yaml(results: TestRunResults, output_path: Path) -> None`

**Export Schema:OpenAI Evals Format:**

```json
{
  "eval_name": "mavaia_curriculum_test",
  "eval_spec": {
    "level": "k5",
    "subject": "math",
    "skill_type": "foundational",
    "difficulty_style": "standard"
  },
  "results": [
    {
      "sample_id": "math_k5_foundational_standard_001",
      "input": {"question": "What is 2 + 3?"},
      "output": {"answer": 5, "reasoning": "..."},
      "expected": {"answer": 5},
      "metrics": {
        "accuracy": 1.0,
        "reasoning_depth": 0.8,
        "final_score": 0.9
      }
    }
  ],
  "summary": {
    "total_tests": 100,
    "passed": 85,
    "failed": 15,
    "average_score": 0.87
  }
}
```

**HuggingFace Evaluate Format:**

```json
{
  "experiment_info": {
    "model_name": "mavaia-cognitive",
    "task": "curriculum_evaluation",
    "dataset": "mavaia_curriculum"
  },
  "results": {
    "accuracy": 0.85,
    "reasoning_depth": 0.78,
    "verbosity": 0.82,
    "structure": 0.80,
    "final_score": 0.81
  },
  "samples": [...]
}
```

**Usage:**

```python
from oricli_core.evaluation.curriculum.exporters import CurriculumExporter
from pathlib import Path

exporter = CurriculumExporter()

# Export to OpenAI Evals
exporter.export_to_openai_evals(
    results=test_results,
    output_path=Path("exports/openai_evals.json")
)

# Export to HuggingFace
exporter.export_to_huggingface(
    results=test_results,
    output_path=Path("exports/hf_evaluate.json")
)

# Export to MLflow
exporter.export_to_mlflow(
    results=test_results,
    experiment_name="mavaia_curriculum_test_run_001"
)

# Export to W&B
exporter.export_to_wandb(
    results=test_results,
    project_name="mavaia-curriculum-evaluation"
)

# Generic formats
exporter.export_to_json(test_results, Path("exports/results.json"))
exporter.export_to_csv(test_results, Path("exports/results.csv"))
```



### 9. Real-Time Fine-Tuning (`fine_tuning.py`)

**Automatic Model Improvement:**The fine-tuning system automatically improves Mavaia's cognitive models based on test failures, creating a continuous learning loop.**Key Functions:**

- `analyze_failures_for_training(results: List[TestResult]) -> Dict[str, Any]`
- `generate_training_data(failures: List[TestResult]) -> List[Dict[str, Any]]`
- `fine_tune_model(model_name: str, training_data: List[Dict], config: FineTuningConfig) -> FineTuningResult`
- `validate_improvement(baseline_results: TestRunResults, new_results: TestRunResults) -> bool`
- `rollback_model(model_name: str, checkpoint_path: Path) -> None`
- `schedule_fine_tuning(failure_threshold: float, min_failures: int) -> None`

**Fine-Tuning Workflow:**

1. **Failure Detection:**

- Monitor test results in real-time
- Identify patterns in failures (specific subjects, skill types, difficulty levels)
- Track recurring failure modes
- Calculate failure rates by cognitive module

2. **Training Data Generation:**

- Extract failed test cases with expected vs actual outputs
- Generate corrective examples:
    - Input: Failed question + incorrect reasoning trace
    - Output: Correct answer + proper reasoning trace
- Create contrastive examples (wrong vs right approaches)
- Augment data with similar problems

3. **Model Selection:**

- Identify which models need fine-tuning:
    - `neural_text_generator` - For language generation failures
    - `custom_reasoning_networks` - For reasoning failures
    - `chain_of_thought` - For step-by-step reasoning issues
    - `tree_of_thought` - For multi-path reasoning problems
    - `mcts_reasoning` - For search-based reasoning failures
- Determine fine-tuning scope (full model vs LoRA adapters)

4. **Fine-Tuning Execution:**

- **LoRA Fine-Tuning** (preferred for efficiency):
    - Low-rank adaptation to preserve base model
    - Faster training, less memory usage
    - Multiple task-specific adapters
- **Full Fine-Tuning** (for major failures):
    - Complete model retraining
    - Used when LoRA insufficient
- **Incremental Learning**:
    - Continuous updates from new failures
    - Prevents catastrophic forgetting
    - Maintains performance on previous tasks

5. **Validation & Rollback:**

- Run validation suite on fine-tuned model
- Compare performance against baseline
- Check for regressions in previously passing tests
- Automatic rollback if:
    - Overall performance decreases
    - Critical tests start failing
    - Safety violations increase
- Keep model checkpoints for rollback

**Fine-Tuning Configuration:**

```python
@dataclass
class FineTuningConfig:
    """Configuration for model fine-tuning"""
    model_name: str
    method: str = "lora"  # "lora" | "full" | "incremental"
    learning_rate: float = 2e-4
    batch_size: int = 8
    epochs: int = 3
    lora_rank: int = 64
    lora_alpha: int = 64
    validation_split: float = 0.2
    min_improvement: float = 0.05  # Minimum improvement to keep model
    max_regression: float = 0.02  # Maximum regression allowed
    checkpoint_dir: Path = Path("checkpoints")
    enable_rollback: bool = True
```

**Integration Points:**

- **Test Executor**: Automatically triggers fine-tuning when failure threshold reached
- **Result Analyzer**: Identifies which models need improvement
- **Analytics**: Provides failure patterns for targeted training
- **Web UI**: Shows fine-tuning progress and model versions

**Usage:**

```python
from oricli_core.evaluation.curriculum.fine_tuning import FineTuningManager

manager = FineTuningManager()

# Automatic fine-tuning (triggered by test executor)
manager.enable_auto_fine_tuning(
    failure_threshold=0.3,  # Fine-tune if >30% failure rate
    min_failures=10,  # Need at least 10 failures
    target_models=["neural_text_generator", "chain_of_thought"]
)

# Manual fine-tuning
training_data = manager.generate_training_data(failed_results)
result = manager.fine_tune_model(
    model_name="neural_text_generator",
    training_data=training_data,
    config=FineTuningConfig(method="lora", epochs=3)
)

# Validate improvement
improved = manager.validate_improvement(baseline_results, new_results)
if not improved:
    manager.rollback_model("neural_text_generator")
```

**Fine-Tuning Strategies:**

1. **Targeted Fine-Tuning:**

- Fine-tune specific models for specific failure types
- Math failures → reasoning modules
- Language failures → text generator
- Safety failures → safety framework modules

2. **Curriculum-Based Fine-Tuning:**

- Start with easier examples
- Gradually increase difficulty
- Focus on weak areas identified by analytics

3. **Multi-Task Fine-Tuning:**

- Fine-tune on multiple failure types simultaneously
- Shared representations across tasks
- Better generalization

4. **Continual Learning:**

- Incremental updates from each test run
- Prevent forgetting previous improvements
- Maintain performance across all curriculum dimensions

**Safety & Validation:**

- **Pre-Fine-Tuning Checks:**
- Minimum training data quality
- Failure pattern validation
- Resource availability check
- **Post-Fine-Tuning Validation:**
- Run validation test suite
- Check for regressions
- Verify safety posture maintained
- Performance benchmarks
- **Rollback Mechanisms:**
- Automatic rollback on validation failure
- Manual rollback via CLI/API
- Checkpoint management
- Version tracking

**Monitoring:**

- Fine-tuning progress tracking
- Training loss curves
- Validation metrics
- Model version history
- Performance improvement metrics

### 10. Distributed Fine-Tuning (`distributed_training.py`)

**Multi-GPU and Multi-Node Training:**The distributed training system enables efficient fine-tuning across multiple GPUs and nodes, significantly reducing training time for large models.**Key Functions:**

- `setup_distributed_training(config: DistributedConfig) -> DistributedTrainer`
- `train_distributed(model: Model, data: Dataset, config: DistributedConfig) -> TrainingResult`
- `sync_gradients(rank: int, world_size: int) -> None`
- `aggregate_checkpoints(checkpoints: List[Path]) -> Path`
- `handle_node_failure(failed_node: int, remaining_nodes: List[int]) -> None`

**Distribution Strategies:**

1. **Data Parallelism:**

- Split training data across GPUs/nodes
- Each device processes different batch
- Synchronize gradients after each step
- Efficient for models that fit on single GPU

2. **Model Parallelism:**

- Split model across multiple GPUs/nodes
- Each device holds part of model
- Forward/backward passes across devices
- Required for very large models

3. **Pipeline Parallelism:**

- Split model into stages
- Process different batches in parallel stages
- Overlap computation and communication
- Optimizes GPU utilization

4. **Hybrid Parallelism:**

- Combine data + model parallelism
- Combine data + pipeline parallelism
- Optimal for very large models and datasets

**Distributed Configuration:**

```python
@dataclass
class DistributedConfig:
    """Configuration for distributed training"""
    strategy: str = "data_parallel"  # "data_parallel" | "model_parallel" | "pipeline_parallel" | "hybrid"
    num_gpus: int = 1
    num_nodes: int = 1
    gpus_per_node: int = 8
    master_addr: str = "localhost"
    master_port: int = 29500
    backend: str = "nccl"  # "nccl" (CUDA) | "gloo" (CPU)
    gradient_sync_frequency: int = 1  # Sync every N steps
    checkpoint_frequency: int = 100  # Save checkpoint every N steps
    enable_fault_tolerance: bool = True
    resume_from_checkpoint: Optional[Path] = None
```

**Features:**

1. **Automatic Resource Discovery:**

- Detect available GPUs/nodes
- Allocate resources optimally
- Handle resource constraints

2. **Gradient Synchronization:**

- AllReduce for gradient aggregation
- Efficient communication patterns
- Overlap computation and communication

3. **Checkpoint Management:**

- Distributed checkpoint saving
- Coordinated checkpoint loading
- Checkpoint consolidation

4. **Fault Tolerance:**

- Detect node/GPU failures
- Automatic recovery from checkpoints
- Continue training with remaining nodes
- Graceful degradation

5. **Load Balancing:**

- Balance data across nodes
- Handle uneven data distribution
- Dynamic load adjustment

**Usage:**

```python
from oricli_core.evaluation.curriculum.distributed_training import DistributedTrainer

# Setup distributed training
config = DistributedConfig(
    strategy="data_parallel",
    num_gpus=4,
    num_nodes=2,
    gpus_per_node=4
)

trainer = DistributedTrainer(config)

# Train model
result = trainer.train_distributed(
    model=model,
    training_data=training_data,
    config=config
)

# Aggregate results
final_model = trainer.aggregate_checkpoints(result.checkpoints)
```

**Integration:**

- Works with existing fine-tuning system
- Automatically uses distributed training for large models
- Falls back to single-GPU for small models
- Web UI shows distributed training progress

### 11. Federated Learning (`federated_learning.py`)

**Privacy-Preserving Model Improvement:**Federated learning enables model improvement across multiple clients (test environments, deployments) without sharing raw test data, preserving privacy and security.**Key Functions:**

- `setup_federated_server(config: FederatedConfig) -> FederatedServer`
- `register_client(client_id: str, client_info: Dict) -> None`
- `aggregate_updates(client_updates: List[ModelUpdate]) -> ModelUpdate`
- `apply_differential_privacy(update: ModelUpdate, epsilon: float) -> ModelUpdate`
- `select_clients(round: int, total_clients: int, selection_strategy: str) -> List[str]`
- `secure_aggregation(updates: List[EncryptedUpdate]) -> ModelUpdate`

**Federated Learning Workflow:**

1. **Server Initialization:**

- Initialize global model
- Set up communication protocol
- Configure privacy parameters

2. **Client Selection:**

- Select subset of clients for each round
- Strategies: random, stratified, adaptive
- Balance participation across clients

3. **Model Distribution:**

- Send current global model to selected clients
- Clients receive model weights/config

4. **Local Training:**

- Clients fine-tune on local test failures
- Generate model updates (gradients or weights)
- Apply local privacy mechanisms

5. **Update Aggregation:**

- Collect updates from clients
- Apply secure aggregation
- Apply differential privacy if enabled
- Aggregate into global model update

6. **Global Model Update:**

- Update global model with aggregated update
- Validate improvement
- Distribute updated model

**Privacy Mechanisms:**

1. **Differential Privacy:**

- Add calibrated noise to updates
- Privacy budget management (epsilon-delta)
- Composition tracking across rounds
- Trade-off between privacy and utility

2. **Secure Multi-Party Computation (SMPC):**

- Encrypt model updates
- Aggregate in encrypted domain
- Decrypt only final aggregate
- No individual updates revealed

3. **Homomorphic Encryption:**

- Perform aggregation on encrypted data
- No decryption needed
- Strong privacy guarantees

4. **Secure Aggregation:**

- Mask updates with secret shares
- Aggregation cancels masks
- Server only sees aggregate

**Federated Configuration:**

```python
@dataclass
class FederatedConfig:
    """Configuration for federated learning"""
    num_clients: int
    clients_per_round: int = 10
    num_rounds: int = 100
    local_epochs: int = 3
    learning_rate: float = 2e-4
    batch_size: int = 8
    
    # Privacy
    enable_differential_privacy: bool = True
    epsilon: float = 1.0  # Privacy budget
    delta: float = 1e-5
    noise_scale: float = 0.1
    
    # Security
    enable_secure_aggregation: bool = False
    encryption_method: str = "smpc"  # "smpc" | "homomorphic" | "none"
    
    # Client selection
    selection_strategy: str = "random"  # "random" | "stratified" | "adaptive"
    
    # Communication
    communication_protocol: str = "http"  # "http" | "grpc" | "websocket"
    timeout: float = 300.0  # seconds
```

**Features:**

1. **Client Management:**

- Client registration and authentication
- Client health monitoring
- Handle client dropouts
- Client capability tracking

2. **Update Aggregation:**

- Federated averaging (FedAvg)
- Weighted averaging by data size
- Robust aggregation (median, trimmed mean)
- Handle stragglers and failures

3. **Privacy Budget Management:**

- Track epsilon consumption
- Enforce privacy budget limits
- Adaptive noise scaling
- Privacy-utility trade-off optimization

4. **Security:**

- Encrypted communication
- Client authentication
- Update verification
- Poisoning attack detection

5. **Adaptive Strategies:**

- Adaptive client selection
- Dynamic learning rate
- Personalized federated learning
- Heterogeneous data handling

**Usage:**

```python
from oricli_core.evaluation.curriculum.federated_learning import FederatedServer, FederatedClient

# Server side
server = FederatedServer(FederatedConfig(
    num_clients=100,
    clients_per_round=10,
    enable_differential_privacy=True,
    epsilon=1.0
))

# Register clients
for client_id in client_ids:
    server.register_client(client_id, client_info)

# Run federated learning
global_model = server.train_federated(
    initial_model=base_model,
    num_rounds=100
)

# Client side
client = FederatedClient(
    client_id="client_1",
    server_url="https://federated-server.com"
)

# Local training and update
local_update = client.train_local(
    model=global_model,
    local_data=test_failures,
    epochs=3
)

# Send update to server
client.send_update(local_update)
```

**Integration:**

- Works with distributed training for server-side aggregation
- Integrates with fine-tuning system
- Supports multiple deployment scenarios
- Web UI shows federated learning progress

**Use Cases:**

1. **Multi-Deployment Improvement:**

- Improve models across multiple Mavaia deployments
- Aggregate learnings without sharing data
- Maintain deployment-specific privacy

2. **Cross-Organization Learning:**

- Collaborate with other organizations
- Share model improvements, not data
- Privacy-preserving research collaboration

3. **Edge Device Learning:**

- Learn from edge device test results
- Respect device privacy constraints
- Efficient communication patterns

**Integration Points:**

- CLI: `mavaia-curriculum-test --export-format openai_evals --output exports/`
- Web UI: Export button with format selection
- Programmatic: Direct API access for automation

## Integration with Existing Framework

- **Separate but compatible**: New framework lives alongside existing `test_runner.py`
- **Shared infrastructure**: Uses `TestResults` data models where applicable
- **Optional integration**: Can import and use existing test data if needed
- **Independent execution**: Doesn't require existing framework to run

## Curriculum Data Format

Example test question structure:

```json
{
  "id": "math_k5_foundational_standard_001",
  "level": "k5",
  "subject": "math",
  "skill_type": "foundational",
  "difficulty_style": "standard",
  "question": "What is 2 + 3?",
  "question_type": "free_response",
  "expected_reasoning_type": "arithmetic",
  "expected_answer_format": "numeric",
  "answer": 5,
  "metadata": {
    "tags": ["addition", "basic_arithmetic"],
    "estimated_time": 5.0,
    "estimated_tokens": 50,
    "expected_reasoning_steps": 1
  }
}
```



## Test Dataset Generation Workflow

### Dataset Generator (`generator.py`)

The generator creates balanced test datasets across all curriculum dimensions.**Key Functions:**

- `generate_dataset_for_level(level: str, output_dir: Path) -> None`
- `generate_balanced_subjects(level: str, questions_per_subject: int) -> List[Dict]`
- `generate_question_variations(subject: str, skill_type: str, difficulty: str) -> List[Dict]`

**Generation Strategy:**

1. **Level-Based Generation:**

- K-5: 50 questions per subject (Math, Language, Science, Logic)
- 6-8: 75 questions per subject
- 9-12: 100 questions per subject
- Undergrad: 150 questions per subject
- Grad: 200 questions per subject
- PhD: 250 questions per subject

2. **Subject Balance:**

- Math: Arithmetic, algebra, geometry, calculus (based on level)
- Language: Reading comprehension, writing, grammar, vocabulary
- Science: Biology, chemistry, physics, earth science
- Logic: Deductive reasoning, inductive reasoning, symbolic logic
- Social Cognition: Ethics, social reasoning, perspective-taking
- Research & Inquiry: Hypothesis formation, experimental design, analysis

3. **Question Type Variation:**

- **Multiple Choice**: 30% of questions
    - 4-5 options per question
    - Single correct answer
    - Distractor quality varies by difficulty
- **Free Response**: 40% of questions
    - Short answer (1-2 sentences)
    - Medium answer (paragraph)
    - Long answer (multi-paragraph)
- **Proofs/Show Work**: 20% of questions (higher levels)
    - Mathematical proofs
    - Step-by-step solutions
    - Logical derivations
- **Essays**: 10% of questions (higher levels)
    - Argumentative essays
    - Explanatory essays
    - Creative synthesis

4. **Difficulty Distribution:**

- Standard: 40% of questions
- Accelerated: 25% of questions
- Honors/AP: 20% of questions
- Competition/Olympiad: 10% of questions
- Research: 5% of questions (grad/PhD only)

5. **Skill Type Distribution:**

- Foundational: 30%
- Applied: 25%
- Abstract reasoning: 20%
- Explanatory reasoning: 15%
- Adaptive behavior: 5%
- Long-horizon reasoning: 3%
- Creative synthesis: 2%

**Generation Process:**

1. For each level:

- Generate question templates for each subject
- Apply difficulty variations
- Apply skill type variations
- Generate answer keys and expected reasoning traces
- Validate question quality (no ambiguity, appropriate difficulty)

2. Question Quality Checks:

- No ambiguous wording
- Answer is verifiable
- Appropriate for stated level/difficulty
- Expected reasoning steps are reasonable

3. Output Format:

- JSON files organized by level/subject/skill/difficulty
- Metadata files for quick lookup
- Answer key files (separate from questions for security)

**Usage:**

```python
from oricli_core.evaluation.curriculum.generator import CurriculumGenerator

generator = CurriculumGenerator()
generator.generate_full_curriculum(output_dir=Path("curriculum/data"))
# Or generate specific level:
generator.generate_level("k5", output_dir=Path("curriculum/data/levels/k5"))
```



## Dependencies

- Existing: `oricli_core.client`, `oricli_core.brain.modules.*`
- New: 
- `rich` (for CLI formatting)
- `typer` (for CLI)
- `pydantic` (for data validation)
- `fastapi` (for web UI backend)
- `uvicorn` (for web server)
- `websockets` (for real-time updates)
- `python-multipart` (for file uploads in web UI)
- `scikit-learn` (for ML-based recommendations, optional)
- `numpy` (for analytics calculations)
- `pandas` (for data analysis and export)
- `mlflow` (for MLflow export, optional)
- `wandb` (for W&B export, optional)
- `torch` or `tensorflow` (for model fine-tuning, depending on model backend)
- `peft` (for LoRA fine-tuning, optional)
- `transformers` (for transformer model fine-tuning, if applicable)
- `torch.distributed` or `tensorflow.distribute` (for distributed training)
- `deepspeed` (for advanced distributed training, optional)
- `horovod` (for multi-node training, optional)
- `cryptography` (for federated learning security)
- `tenseal` or `pyfhel` (for homomorphic encryption in federated learning, optional)
- `syft` (for secure multi-party computation, optional)

## Testing Strategy

- Unit tests for each component
- Integration tests with mock Mavaia responses
- End-to-end tests with actual Mavaia instance
- Test data validation

## Future Enhancements

- Integration with external benchmark datasets (MMLU, HellaSwag, etc.)
- Automated test generation using LLMs
- Collaborative testing features (team testing, shared results)
- A/B testing framework for cognitive module improvements
- Reinforcement learning from human feedback (RLHF) integration
- Automated hyperparameter optimization for fine-tuning