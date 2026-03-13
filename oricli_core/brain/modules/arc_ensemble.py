from __future__ import annotations
"""
ARC Ensemble System

Combines induction (program synthesis) and transduction (neural prediction) methods.
Intelligently selects and combines predictions from both approaches.

Based on "Combining Induction and Transduction for Abstract Reasoning" (arxiv:2411.02272)
"""

import copy
import logging
from typing import Any, Callable, Dict, List, Optional, Tuple

import numpy as np

from oricli_core.brain.modules.arc_data_augmentation import ARCTask
from oricli_core.brain.modules.arc_transduction_model import ARCTransductionModel

logger = logging.getLogger(__name__)


class ARCEnsemble:
    """Ensemble system combining induction and transduction"""
    
    def __init__(
        self,
        induction_model: Optional[Any] = None,
        transduction_model: Optional[ARCTransductionModel] = None
    ):
        """
        Initialize ensemble system.
        
        Args:
            induction_model: Program synthesis model (e.g., custom_reasoning_networks)
            transduction_model: Neural transduction model
        """
        self.induction_model = induction_model
        self.transduction_model = transduction_model or ARCTransductionModel()
    
    def _is_computational_task(self, task: ARCTask) -> bool:
        """
        Heuristically determine if task is computational (good for induction).
        
        Args:
            task: ARC task to analyze
            
        Returns:
            True if task appears computational
        """
        # Simple heuristic: check if outputs have clear mathematical relationships
        # with inputs (size changes, color counts, etc.)
        
        if not task.train_inputs or not task.train_outputs:
            return False
        
        # Check for consistent size changes
        size_changes = []
        for inp, out in zip(task.train_inputs, task.train_outputs):
            inp_np = np.array(inp)
            out_np = np.array(out)
            if inp_np.shape != out_np.shape:
                size_changes.append(True)
        
        if len(size_changes) > len(task.train_inputs) * 0.7:
            # Mostly size changes - likely computational
            return True
        
        # Check for clear color mappings
        color_mappings_consistent = True
        for inp, out in zip(task.train_inputs, task.train_outputs):
            inp_np = np.array(inp)
            out_np = np.array(out)
            inp_colors = set(np.unique(inp_np))
            out_colors = set(np.unique(out_np))
            
            if len(out_colors - inp_colors) > len(inp_colors):
                # Many new colors - might be perceptual
                color_mappings_consistent = False
                break
        
        return color_mappings_consistent
    
    def _is_perceptual_task(self, task: ARCTask) -> bool:
        """
        Heuristically determine if task is perceptual (good for transduction).
        
        Args:
            task: ARC task to analyze
            
        Returns:
            True if task appears perceptual
        """
        # Opposite of computational - fuzzy, pattern-based tasks
        return not self._is_computational_task(task)
    
    def select_method(
        self,
        task: ARCTask,
        characteristics: Optional[Dict[str, Any]] = None
    ) -> str:
        """
        Choose best method for task.
        
        Args:
            task: ARC task
            characteristics: Optional task characteristics
            
        Returns:
            "induction", "transduction", or "ensemble"
        """
        if characteristics is None:
            characteristics = {}
        
        # Use provided characteristic if available
        if "method" in characteristics:
            return characteristics["method"]
        
        # Heuristic selection
        if self._is_computational_task(task):
            return "induction"
        elif self._is_perceptual_task(task):
            return "transduction"
        else:
            return "ensemble"
    
    def predict_induction(
        self,
        task: ARCTask,
        max_attempts: int = 1
    ) -> Tuple[Optional[List[List[Any]]], float]:
        """
        Predict using induction (program synthesis).
        
        Args:
            task: ARC task
            max_attempts: Maximum synthesis attempts
            
        Returns:
            Tuple of (prediction, confidence), (None, 0.0) if failed
        """
        if self.induction_model is None or task.test_input is None:
            return None, 0.0
        
        try:
            # Call induction model (would use custom_reasoning_networks)
            # This is a placeholder - actual implementation would call the real model
            result = self.induction_model.execute("solve_arc_task", {
                "input_grids": task.train_inputs,
                "output_grids": task.train_outputs,
                "test_input": task.test_input
            })
            
            prediction = result.get("predicted_output")
            confidence = result.get("confidence", 0.0)
            
            return prediction, confidence
            
        except Exception as e:
            logger.debug(
                "Induction prediction failed",
                exc_info=True,
                extra={"module_name": "arc_ensemble", "error_type": type(e).__name__},
            )
            return None, 0.0
    
    def predict_transduction(
        self,
        task: ARCTask
    ) -> Tuple[Optional[List[List[Any]]], float]:
        """
        Predict using transduction (neural).
        
        Args:
            task: ARC task
            
        Returns:
            Tuple of (prediction, confidence)
        """
        if task.test_input is None:
            return None, 0.0
        
        train_examples = list(zip(task.train_inputs, task.train_outputs))
        prediction, confidence = self.transduction_model.predict_with_confidence(
            train_examples,
            task.test_input
        )
        
        return prediction, confidence
    
    def combine_predictions(
        self,
        inductive_pred: Optional[List[List[Any]]],
        transductive_pred: Optional[List[List[Any]]],
        inductive_conf: float,
        transductive_conf: float,
        method: str = "confidence_weighted"
    ) -> List[List[Any]]:
        """
        Combine predictions from both methods.
        
        Args:
            inductive_pred: Induction prediction
            transductive_pred: Transduction prediction
            inductive_conf: Induction confidence
            transductive_conf: Transduction confidence
            method: Combination method ("confidence_weighted", "majority", "induction_first")
            
        Returns:
            Combined prediction
        """
        # Filter out None predictions
        predictions = []
        confidences = []
        
        if inductive_pred is not None:
            predictions.append(inductive_pred)
            confidences.append(inductive_conf)
        
        if transductive_pred is not None:
            predictions.append(transductive_pred)
            confidences.append(transductive_conf)
        
        if not predictions:
            # No valid predictions
            return None
        
        if len(predictions) == 1:
            return predictions[0]
        
        # Multiple predictions - combine
        if method == "confidence_weighted":
            # Use highest confidence
            best_idx = np.argmax(confidences)
            return predictions[best_idx]
        
        elif method == "majority":
            # Check if predictions are similar
            pred1_np = np.array(predictions[0])
            pred2_np = np.array(predictions[1])
            
            if np.array_equal(pred1_np, pred2_np):
                # Same prediction - return it
                return predictions[0]
            else:
                # Different - use higher confidence
                best_idx = np.argmax(confidences)
                return predictions[best_idx]
        
        elif method == "induction_first":
            # Prefer induction if available
            if inductive_pred is not None:
                return inductive_pred
            else:
                return transductive_pred
        
        else:
            # Default: highest confidence
            best_idx = np.argmax(confidences)
            return predictions[best_idx]
    
    def predict(
        self,
        task: ARCTask,
        max_induction_attempts: int = 1,
        fallback_to_transduction: bool = True,
        use_ensemble: bool = True
    ) -> Dict[str, Any]:
        """
        Ensemble prediction: try induction first, fallback to transduction.
        
        Args:
            task: ARC task to solve
            max_induction_attempts: Maximum induction attempts
            fallback_to_transduction: Whether to use transduction if induction fails
            use_ensemble: Whether to combine both methods if available
            
        Returns:
            Dictionary with prediction and metadata
        """
        result = {
            "prediction": None,
            "method_used": None,
            "confidence": 0.0,
            "induction_prediction": None,
            "induction_confidence": 0.0,
            "transduction_prediction": None,
            "transduction_confidence": 0.0,
            "success": False
        }
        
        if task.test_input is None:
            return result
        
        # Try induction first
        inductive_pred = None
        inductive_conf = 0.0
        
        if self.induction_model is not None:
            inductive_pred, inductive_conf = self.predict_induction(
                task,
                max_attempts=max_induction_attempts
            )
        
        # Try transduction
        transductive_pred = None
        transductive_conf = 0.0
        
        if fallback_to_transduction or use_ensemble:
            transductive_pred, transductive_conf = self.predict_transduction(task)
        
        # Combine or select
        if use_ensemble and inductive_pred is not None and transductive_pred is not None:
            # Combine both
            combined = self.combine_predictions(
                inductive_pred,
                transductive_pred,
                inductive_conf,
                transductive_conf
            )
            result["prediction"] = combined
            result["method_used"] = "ensemble"
            result["confidence"] = max(inductive_conf, transductive_conf)
            result["success"] = True
        
        elif inductive_pred is not None and inductive_conf > 0.5:
            # Use induction
            result["prediction"] = inductive_pred
            result["method_used"] = "induction"
            result["confidence"] = inductive_conf
            result["success"] = True
        
        elif transductive_pred is not None:
            # Use transduction
            result["prediction"] = transductive_pred
            result["method_used"] = "transduction"
            result["confidence"] = transductive_conf
            result["success"] = True
        
        # Store individual results
        result["induction_prediction"] = inductive_pred
        result["induction_confidence"] = inductive_conf
        result["transduction_prediction"] = transductive_pred
        result["transduction_confidence"] = transductive_conf
        
        return result
    
    def ensemble_predict(
        self,
        task: ARCTask,
        compute_budget: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Ensemble prediction with compute budget constraints.
        
        Args:
            task: ARC task
            compute_budget: Optional budget constraints (max_time, max_attempts, etc.)
            
        Returns:
            Prediction result
        """
        if compute_budget is None:
            compute_budget = {}
        
        max_attempts = compute_budget.get("max_induction_attempts", 1)
        use_transduction = compute_budget.get("use_transduction", True)
        use_ensemble = compute_budget.get("use_ensemble", True)
        
        return self.predict(
            task,
            max_induction_attempts=max_attempts,
            fallback_to_transduction=use_transduction,
            use_ensemble=use_ensemble
        )

