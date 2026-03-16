from __future__ import annotations
"""
ARC Transduction Module
Implements the Transduction (Neural Pattern Matching) path for ARC solving.
Uses Test-Time Training (TTT) on augmented training examples.
"""

import logging
import json
import copy
from typing import Dict, Any, List, Optional, Tuple

import numpy as np

from oricli_core.brain.base_module import BaseBrainModule, ModuleMetadata
from oricli_core.brain.registry import ModuleRegistry
from oricli_core.exceptions import InvalidParameterError
from oricli_core.brain.modules.arc_data_augmentation import ARCTask, ARCDataAugmentation
from oricli_core.brain.modules.arc_transduction_model import ARCTransductionModel

logger = logging.getLogger(__name__)

class ARCTransductionModule(BaseBrainModule):
    """Brain module for ARC neural transduction with TTT."""

    def __init__(self) -> None:
        super().__init__()
        self.augmentation = ARCDataAugmentation()
        self.model = ARCTransductionModel()

    @property
    def metadata(self) -> ModuleMetadata:
        return ModuleMetadata(
            name="arc_transduction",
            version="1.0.0",
            description="Solves ARC tasks via neural transduction and Test-Time Training",
            operations=[
                "predict",
                "test_time_train"
            ],
            dependencies=[],
            model_required=False,
        )

    def execute(self, operation: str, params: Dict[str, Any]) -> Dict[str, Any]:
        if operation == "predict":
            task_dict = params.get("task", {})
            task = ARCTask.from_dict(task_dict)
            return self._predict(task)
        elif operation == "test_time_train":
            task_dict = params.get("task", {})
            task = ARCTask.from_dict(task_dict)
            return self._test_time_train(task)
        else:
            raise InvalidParameterError(parameter="operation", value=operation, reason="Unsupported operation")

    def _test_time_train(self, task: ARCTask) -> Dict[str, Any]:
        """
        Perform Test-Time Training (TTT).
        Augments training examples and fine-tunes the model.
        """
        _rich_log("Transduction: Starting Test-Time Training (TTT)...", "cyan", "🧬")
        
        # 1. Augment the task
        augmented_tasks = self.augmentation.augment_task(task)
        _rich_log(f"  - Generated {len(augmented_tasks)} augmented examples for TTT.", "dim")
        
        # 2. Collect all training pairs (original + augmented)
        all_train_pairs = []
        for aug_task, _ in augmented_tasks:
            for inp, out in zip(aug_task.train_inputs, aug_task.train_outputs):
                all_train_pairs.append((inp, out))
        
        # 3. Micro-fine-tuning (Simulated for now)
        # In a real implementation, this would call self.model.train_on_batch(all_train_pairs)
        self.model.train_on_batch(all_train_pairs)
        
        return {"success": True, "num_examples": len(all_train_pairs)}

    def _predict(self, task: ARCTask) -> Dict[str, Any]:
        """Predict the test output using the TTT-enhanced model."""
        # Ensure TTT is done
        self._test_time_train(task)
        
        # In the paper, we apply the 8 standard symmetries to the test input,
        # predict for each, and then reverse the symmetry and ensemble.
        
        predictions = []
        symmetries = self.augmentation.augment_grid(task.test_input) # Returns [(grid, transform_info), ...]
        
        _rich_log(f"Transduction: Predicting across {len(symmetries)} symmetries...", "cyan", "🔮")
        
        train_examples = list(zip(task.train_inputs, task.train_outputs))
        
        for aug_test_input, transform_info in symmetries:
            # Predict using the model
            pred_grid, confidence = self.model.predict_with_confidence(train_examples, aug_test_input)
            
            # Reverse the transformation
            orig_pred_grid = self.augmentation.reverse_transform(pred_grid, transform_info)
            predictions.append((orig_pred_grid, confidence))
            
        # Ensemble predictions (for now, just take the first one or most common)
        # Real ensembling would use arc_reranking
        final_prediction = predictions[0][0]
        
        return {
            "success": True,
            "prediction": final_prediction,
            "confidence": 0.8,
            "method": "transduction"
        }

def _rich_log(message: str, style: str = "white", icon: str = ""):
    prefix = f"{icon} " if icon else ""
    print(f"[{style}]{prefix}{message}")
