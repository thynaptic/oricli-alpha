# Cognitive Curriculum Testing Framework

A comprehensive testing framework for Oricli-Alpha that enables curriculum-based evaluation through progressive difficulty testing and selective testing via an interactive menu system.

## Overview

The Cognitive Curriculum Testing Framework provides:

- **Full Curriculum Testing**: Progressive difficulty testing that starts easy and increases until failure
- **Selective Testing**: Interactive menu system for choosing specific test configurations
- **Comprehensive Scoring**: Multi-dimensional scoring with accuracy, reasoning depth, verbosity, and structure
- **Cognitive Analysis**: Weakness/strength mapping and safety posture monitoring
- **Real-time Fine-tuning**: Automatic model improvement based on test failures
- **Distributed Training**: Multi-GPU/multi-node fine-tuning support
- **Federated Learning**: Privacy-preserving model improvement
- **Web UI**: Interactive web interface for testing and visualization
- **Export Support**: Export to OpenAI Evals, HuggingFace, MLflow, W&B formats

## Quick Start

### Installation

The framework is included with Oricli-Alpha Core. Install dependencies:

```bash
pip install typer rich  # For CLI
pip install fastapi uvicorn websockets  # For Web UI
```

### Basic Usage

#### Run Full Curriculum (Progressive)

```bash
oricli-curriculum-test --full
```

#### Interactive Selection

```bash
oricli-curriculum-test --select
```

#### Direct Parameter Selection

```bash
oricli-curriculum-test --direct \
  --level k5 \
  --subject math \
  --skill-type foundational \
  --difficulty standard
```

#### Start Web UI

```bash
oricli-curriculum-test --web-ui
```

## Architecture

### Core Components

1. **Data Models** (`models.py`): Pydantic models for test configuration and results
2. **Selector** (`selector.py`): Interactive and programmatic curriculum selection
3. **Executor** (`executor.py`): Test execution engine with constraint application
4. **Analyzer** (`analyzer.py`): Result analysis and cognitive mapping
5. **Reporter** (`reporter.py`): JSON/HTML report generation
6. **Rubric** (`rubric.py`): Comprehensive scoring system
7. **Constraints** (`constraints.py`): Constraint application (time, token, memory, safety)
8. **Generator** (`generator.py`): Test dataset generation
9. **CLI** (`cli.py`): Command-line interface
10. **Web UI** (`web_ui/`): Interactive web interface
11. **Analytics** (`analytics.py`): ML-based test recommendations
12. **Exporters** (`exporters.py`): Standard format export
13. **Fine-tuning** (`fine_tuning.py`): Real-time model improvement
14. **Distributed Training** (`distributed_training.py`): Multi-GPU training
15. **Federated Learning** (`federated_learning.py`): Privacy-preserving learning

## Test Configuration

### Levels

- `k5`: Kindergarten through 5th grade
- `middle_school`: 6th through 8th grade
- `high_school`: 9th through 12th grade
- `undergrad`: Undergraduate level
- `grad`: Graduate level (Master's)
- `phd`: PhD and research level

### Subjects

- `math`: Mathematics
- `language`: Language & Writing
- `science`: Science
- `logic`: Logic & Symbolic Reasoning
- `social_cognition`: Social Cognition & Ethics
- `research`: Research & Inquiry
- `problem_solving`: Problem Solving / Multi-step Reasoning
- `memory`: Memory & Continuity Challenges

### Skill Types

- `foundational`: Foundational skills
- `applied`: Applied skills
- `abstract_reasoning`: Abstract reasoning
- `explanatory_reasoning`: Explanatory reasoning (show work)
- `adaptive_behavior`: Adaptive behavior (tone + guidance)
- `long_horizon_reasoning`: Long-horizon reasoning
- `creative_synthesis`: Creative synthesis

### Difficulty Styles

- `standard`: Standard grade-level
- `accelerated`: Accelerated
- `honors`: Honors / AP-equivalent
- `competition`: Competition (AMC, AIME, Olympiad)
- `qualifying_exam`: Graduate Qualifying Exam style
- `research`: Research proposal synthesis
- `socratic`: Socratic defense (argumentation mode)

## Optional Constraints

- **Time Bound**: Maximum execution time in seconds
- **Token Bound**: Maximum token usage
- **Memory Continuity**: `off`, `short_term` (5 turns), `long_term_bounded` (20 turns)
- **Safety Posture**: `normal`, `supportive`, `intervention`, `high_risk_override`
- **Tool Usage**: Allow/deny tool usage
- **Bias Probes**: Enable bias probing tests
- **Breakdown Explanation**: Require step-by-step breakdown
- **MCTS Depth**: Monte Carlo Thought Search depth limit

## Scoring System

### Component Scores

- **Accuracy** (40% weight): Answer correctness
- **Reasoning Depth** (25% weight): Quality of reasoning process
- **Verbosity** (10% weight): Appropriate response length
- **Structure** (10% weight): Response organization

### Penalties

- **Hallucination**: -0.3 per instance (max -1.0)
- **Safety Violation**: -0.5 per unblocked violation (max -1.0)
- **Memory Corruption**: -0.2 per instance (if memory enabled)

### Pass/Fail Thresholds

- **Pass**: Score >= 0.7 AND no critical violations AND no hallucinations
- **Partial**: Score >= 0.5 AND < 0.7 AND no critical violations
- **Fail**: Score < 0.5 OR critical violation OR multiple hallucinations

## Programmatic Usage

```python
from oricli_core.evaluation.curriculum import (
    TestConfiguration,
    OptionalConstraints,
    TestExecutor,
    ResultAnalyzer,
    TestReporter,
)
from oricli_core.evaluation.curriculum.models import MemoryContinuityMode, SafetyPosture

# Create test configuration
constraints = OptionalConstraints(
    time_bound=60.0,
    memory_continuity=MemoryContinuityMode.SHORT_TERM,
    safety_posture=SafetyPosture.NORMAL,
)

config = TestConfiguration(
    level="k5",
    subject="math",
    skill_type="foundational",
    difficulty_style="standard",
    constraints=constraints,
)

# Execute test
executor = TestExecutor()
result = executor.execute_test(config)

# Analyze results
analyzer = ResultAnalyzer()
weaknesses = analyzer.analyze_cognitive_weaknesses(result)
strengths = analyzer.analyze_cognitive_strengths(result)

# Generate report
reporter = TestReporter()
json_path = reporter.generate_json_report([result])
html_path = reporter.generate_html_report([result])
```

## Output Format

Each test produces:

- **Score**: Numeric or categorical score
- **Score Breakdown**: Detailed component scores and penalties
- **Reasoning Trace**: Structured trace from CoT/ToT/MCTS modules
- **Cognitive Weakness Map**: What failed and why
- **Cognitive Strength Map**: What succeeded and why
- **Safety Posture Summary**: How safety layer influenced behavior
- **Suggested Next Test**: Recommended next test configuration

## Memory Continuity

### Short-Term Memory

- Working memory window: 5 conversation turns
- Session-only persistence
- Reference window: 5 turns
- Topic continuity threshold: 0.5

### Long-Term Bounded Memory

- Maximum history: 20 conversation turns
- Persists across multiple tests
- Entity tracking: max 50 entities with decay 0.9
- Memory corruption detection:
  - Abrupt topic shifts (continuity_score < 0.3)
  - Inconsistent entity references
  - Contradictory statements
  - Memory retrieval failures

## Dataset Generation

Generate test datasets:

```python
from oricli_core.evaluation.curriculum.generator import CurriculumGenerator
from pathlib import Path

generator = CurriculumGenerator()
generator.generate_full_curriculum(output_dir=Path("curriculum/data"))
```

## Advanced Features

### Real-Time Fine-Tuning

Automatically improve models based on test failures:

```python
from oricli_core.evaluation.curriculum.fine_tuning import FineTuningManager

manager = FineTuningManager()
manager.enable_auto_fine_tuning(
    failure_threshold=0.3,
    min_failures=10,
    target_models=["neural_text_generator", "chain_of_thought"]
)
```

### Analytics

Get ML-based test recommendations:

```python
from oricli_core.evaluation.curriculum.analytics import CurriculumAnalytics

analytics = CurriculumAnalytics()
analytics.load_history(results_dir)
recommendations = analytics.recommend_next_tests(current_results)
```

### Export

Export to standard formats:

```python
from oricli_core.evaluation.curriculum.exporters import CurriculumExporter

exporter = CurriculumExporter()
exporter.export_to_openai_evals(results, Path("exports/openai_evals.json"))
exporter.export_to_huggingface(results, Path("exports/hf_evaluate.json"))
```

## Directory Structure

```
oricli_core/evaluation/curriculum/
├── __init__.py
├── models.py
├── selector.py
├── executor.py
├── analyzer.py
├── reporter.py
├── rubric.py
├── constraints.py
├── generator.py
├── cli.py
├── analytics.py
├── exporters.py
├── fine_tuning.py
├── distributed_training.py
├── federated_learning.py
├── data/
│   ├── levels/
│   └── metadata/
├── results/
└── web_ui/
```

## Examples

See the `examples/` directory for detailed usage examples.

## License

MIT License - see LICENSE file for details.

