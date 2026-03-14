from __future__ import annotations

import io
import sys
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT))

from oricli_core.evaluation.test_runner import (
    _build_benchmark_params,
    _format_benchmark_duration,
    _get_benchmark_arc_data_path,
    _looks_like_missing_input_error,
    _run_benchmarks,
)


def test_build_benchmark_params_for_arc_task_module():
    params = _build_benchmark_params("arc_induction", "synthesize_program")

    assert "task" in params
    assert params["task"]["train_inputs"]
    assert params["task"]["train_outputs"]
    assert params["task"]["test_input"]


def test_build_benchmark_params_for_arc_model_training():
    params = _build_benchmark_params("arc_model_training", "train_induction_model")

    assert "data_path" in params
    assert Path(params["data_path"]).exists()
    assert params["use_full_finetune"] is False


def test_build_benchmark_params_for_generation_operation():
    params = _build_benchmark_params("text_generation_engine", "generate_with_neural")

    assert params["prompt"] == "Reply with exactly: benchmark_ok"
    assert params["messages"][0]["role"] == "user"
    assert params["max_tokens"] == 16


def test_build_benchmark_params_for_nlp_and_answer_modules():
    nlp_params = _build_benchmark_params("advanced_nlp", "analyze_sentiment")
    answer_params = _build_benchmark_params("answer_agent", "format_answer")

    assert nlp_params["text"]
    assert nlp_params["categories"] == ["benchmark", "test"]
    assert answer_params["answer"] == "benchmark_ok"
    assert answer_params["documents"][0]["title"] == "Benchmark Doc"


def test_build_benchmark_params_for_agent_coordinator():
    params = _build_benchmark_params("agent_coordinator", "execute_task")

    assert params["task"]["agent_type"] == "answer"
    assert params["tasks"][0]["id"] == "bench-task"
    assert params["context"]["answer"] == "benchmark_ok"


def test_missing_input_error_classifier():
    assert _looks_like_missing_input_error(RuntimeError("Missing required parameter: task"))
    assert _looks_like_missing_input_error(KeyError("prompt"))
    assert not _looks_like_missing_input_error(RuntimeError("connection refused"))


def test_benchmark_duration_formatter_uses_adaptive_units():
    assert _format_benchmark_duration(0.0000008) == "0.80us"
    assert _format_benchmark_duration(0.00042) == "420.00us"
    assert _format_benchmark_duration(0.042) == "42.00ms"
    assert _format_benchmark_duration(1.2345) == "1.234s"


def test_benchmark_arc_data_path_creates_fixture():
    data_path = Path(_get_benchmark_arc_data_path())

    assert data_path.exists()
    assert data_path.read_text(encoding="utf-8").strip().startswith("[")


def test_run_benchmarks_skips_input_dependent_failures():
    class FakeModule:
        def execute(self, operation, params):
            raise RuntimeError("Missing required parameter: task")

    fake_registry = SimpleNamespace(
        discover_modules=lambda background=False, verbose=False: None,
        list_modules=lambda: ["arc_induction"],
        get_metadata=lambda name: SimpleNamespace(operations=["synthesize_program"]),
        get_module=lambda name, auto_discover=False, wait_timeout=0.5: FakeModule(),
    )

    output = io.StringIO()
    with patch("oricli_core.brain.registry.ModuleRegistry", fake_registry):
        with patch("sys.stdout", output):
            _run_benchmarks(runner=None, args=SimpleNamespace(module="arc_induction"))

    assert "Benchmarking arc_induction... (skipped: requires input params)" in output.getvalue()
