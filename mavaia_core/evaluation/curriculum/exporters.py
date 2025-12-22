"""
Export System

Export to standard evaluation formats (OpenAI Evals, HuggingFace Evaluate,
MLflow, W&B, and generic JSON/CSV/YAML).
"""

import csv
import json
from pathlib import Path
from typing import Any, Dict, List, Optional

import yaml

from mavaia_core.evaluation.curriculum.models import TestResult


class CurriculumExporter:
    """Exports test results to various formats"""
    
    def export_to_openai_evals(
        self,
        results: List[TestResult],
        output_path: Path,
    ) -> None:
        """
        Export to OpenAI Evals format
        
        Args:
            results: List of test results
            output_path: Output file path
        """
        eval_data = {
            "eval_name": "mavaia_curriculum_test",
            "eval_spec": {
                "framework": "mavaia_curriculum",
            },
            "results": [],
            "summary": {},
        }
        
        # Convert results
        for result in results:
            config = result.test_config
            eval_result = {
                "sample_id": result.test_id,
                "input": {
                    "question": self._extract_question(result),
                    "level": config.level,
                    "subject": config.subject,
                    "skill_type": config.skill_type,
                    "difficulty_style": config.difficulty_style,
                },
                "output": {
                    "answer": self._extract_answer(result),
                    "reasoning": result.reasoning_trace,
                },
                "expected": {
                    "answer": self._extract_expected_answer(result),
                },
                "metrics": {
                    "accuracy": result.score_breakdown.accuracy,
                    "reasoning_depth": result.score_breakdown.reasoning_depth,
                    "final_score": result.score_breakdown.final_score,
                    "pass_fail": result.pass_fail_status.value,
                },
            }
            eval_data["results"].append(eval_result)
        
        # Summary
        total = len(results)
        passed = sum(1 for r in results if r.pass_fail_status.value == "pass")
        eval_data["summary"] = {
            "total_tests": total,
            "passed": passed,
            "failed": total - passed,
            "average_score": sum(r.score_breakdown.final_score for r in results) / total if total > 0 else 0.0,
        }
        
        # Write file
        output_path.parent.mkdir(parents=True, exist_ok=True)
        with open(output_path, "w", encoding="utf-8") as f:
            json.dump(eval_data, f, indent=2, ensure_ascii=False)
    
    def export_to_huggingface(
        self,
        results: List[TestResult],
        output_path: Path,
    ) -> None:
        """
        Export to HuggingFace Evaluate format
        
        Args:
            results: List of test results
            output_path: Output file path
        """
        hf_data = {
            "experiment_info": {
                "model_name": "mavaia-cognitive",
                "task": "curriculum_evaluation",
                "dataset": "mavaia_curriculum",
            },
            "results": {},
            "samples": [],
        }
        
        # Aggregate metrics
        total = len(results)
        if total > 0:
            hf_data["results"] = {
                "accuracy": sum(r.score_breakdown.accuracy for r in results) / total,
                "reasoning_depth": sum(r.score_breakdown.reasoning_depth for r in results) / total,
                "verbosity": sum(r.score_breakdown.verbosity for r in results) / total,
                "structure": sum(r.score_breakdown.structure for r in results) / total,
                "final_score": sum(r.score_breakdown.final_score for r in results) / total,
            }
        
        # Samples
        for result in results:
            hf_data["samples"].append({
                "test_id": result.test_id,
                "input": self._extract_question(result),
                "output": self._extract_answer(result),
                "expected": self._extract_expected_answer(result),
                "metrics": {
                    "accuracy": result.score_breakdown.accuracy,
                    "reasoning_depth": result.score_breakdown.reasoning_depth,
                    "final_score": result.score_breakdown.final_score,
                },
            })
        
        # Write file
        output_path.parent.mkdir(parents=True, exist_ok=True)
        with open(output_path, "w", encoding="utf-8") as f:
            json.dump(hf_data, f, indent=2, ensure_ascii=False)
    
    def export_to_mlflow(
        self,
        results: List[TestResult],
        experiment_name: str,
    ) -> None:
        """
        Export to MLflow
        
        Args:
            results: List of test results
            experiment_name: MLflow experiment name
        """
        try:
            import mlflow
            mlflow.set_experiment(experiment_name)
            
            with mlflow.start_run():
                # Log metrics
                total = len(results)
                if total > 0:
                    mlflow.log_metric("total_tests", total)
                    mlflow.log_metric(
                        "average_score",
                        sum(r.score_breakdown.final_score for r in results) / total
                    )
                    mlflow.log_metric(
                        "pass_rate",
                        sum(1 for r in results if r.pass_fail_status.value == "pass") / total
                    )
                
                # Log artifacts
                json_path = Path("/tmp/mlflow_results.json")
                self.export_to_json(results, json_path)
                mlflow.log_artifact(str(json_path))
        
        except ImportError:
            raise ImportError("mlflow is required. Install with: pip install mlflow")
    
    def export_to_wandb(
        self,
        results: List[TestResult],
        project_name: str,
    ) -> None:
        """
        Export to Weights & Biases
        
        Args:
            results: List of test results
            project_name: W&B project name
        """
        try:
            import wandb
            wandb.init(project=project_name)
            
            # Log metrics
            total = len(results)
            if total > 0:
                wandb.log({
                    "total_tests": total,
                    "average_score": sum(r.score_breakdown.final_score for r in results) / total,
                    "pass_rate": sum(1 for r in results if r.pass_fail_status.value == "pass") / total,
                })
            
            wandb.finish()
        
        except ImportError:
            raise ImportError("wandb is required. Install with: pip install wandb")
    
    def export_to_json(
        self,
        results: List[TestResult],
        output_path: Path,
    ) -> None:
        """
        Export to JSON
        
        Args:
            results: List of test results
            output_path: Output file path
        """
        output_path.parent.mkdir(parents=True, exist_ok=True)
        with open(output_path, "w", encoding="utf-8") as f:
            json.dump(
                [r.to_dict() for r in results],
                f,
                indent=2,
                ensure_ascii=False,
            )
    
    def export_to_csv(
        self,
        results: List[TestResult],
        output_path: Path,
    ) -> None:
        """
        Export to CSV
        
        Args:
            results: List of test results
            output_path: Output file path
        """
        output_path.parent.mkdir(parents=True, exist_ok=True)
        
        with open(output_path, "w", newline="", encoding="utf-8") as f:
            writer = csv.writer(f)
            
            # Header
            writer.writerow([
                "test_id",
                "level",
                "subject",
                "skill_type",
                "difficulty_style",
                "status",
                "score",
                "accuracy",
                "reasoning_depth",
                "verbosity",
                "structure",
                "execution_time",
            ])
            
            # Rows
            for result in results:
                config = result.test_config
                writer.writerow([
                    result.test_id,
                    config.level,
                    config.subject,
                    config.skill_type,
                    config.difficulty_style,
                    result.pass_fail_status.value,
                    result.score_breakdown.final_score,
                    result.score_breakdown.accuracy,
                    result.score_breakdown.reasoning_depth,
                    result.score_breakdown.verbosity,
                    result.score_breakdown.structure,
                    result.execution_time,
                ])
    
    def export_to_yaml(
        self,
        results: List[TestResult],
        output_path: Path,
    ) -> None:
        """
        Export to YAML
        
        Args:
            results: List of test results
            output_path: Output file path
        """
        output_path.parent.mkdir(parents=True, exist_ok=True)
        
        data = {
            "results": [r.to_dict() for r in results],
            "summary": {
                "total": len(results),
                "passed": sum(1 for r in results if r.pass_fail_status.value == "pass"),
                "failed": sum(1 for r in results if r.pass_fail_status.value == "fail"),
            },
        }
        
        with open(output_path, "w", encoding="utf-8") as f:
            yaml.dump(data, f, default_flow_style=False, allow_unicode=True)
    
    def _extract_question(self, result: TestResult) -> str:
        """Extract question from result"""
        # Question would be in test data, simplified here
        return f"Test question for {result.test_config.subject}"
    
    def _extract_answer(self, result: TestResult) -> str:
        """Extract answer from result"""
        # Answer would be in reasoning trace or result data
        return str(result.score)
    
    def _extract_expected_answer(self, result: TestResult) -> Any:
        """Extract expected answer from result"""
        # Expected answer would be in test data
        return None

