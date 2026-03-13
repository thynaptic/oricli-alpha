from __future__ import annotations
"""
ARC Test-Time Training Module

Fine-tunes transduction model at test time using augmented examples.
Does not require ground truth test output - uses training examples as pseudo-test cases.

Based on "Combining Induction and Transduction for Abstract Reasoning" (arxiv:2411.02272)
"""

import random
from typing import Any, Callable, Dict, List, Optional

from oricli_core.brain.modules.arc_data_augmentation import ARCTask, ARCDataAugmentation
from oricli_core.brain.modules.arc_transduction_model import ARCTransductionModel


from oricli_core.brain.base_module import BaseBrainModule, ModuleMetadata
from oricli_core.exceptions import InvalidParameterError

class ARCTestTimeTrainingModule(BaseBrainModule):
    """Brain module for ARC test-time training."""

    def __init__(self) -> None:
        super().__init__()
        self.trainer = ARCTestTimeTraining()

    @property
    def metadata(self) -> ModuleMetadata:
        return ModuleMetadata(
            name="arc_test_time_training",
            version="1.0.0",
            description="Fine-tunes transduction models at test time for ARC",
            operations=[
                "test_time_train",
                "create_pseudo_tasks"
            ],
            dependencies=[],
            model_required=False,
        )

    def execute(self, operation: str, params: Dict[str, Any]) -> Dict[str, Any]:
        if operation == "test_time_train":
            task_dict = params.get("task", {})
            task = ARCTask.from_dict(task_dict)
            model = params.get("model") # Expecting actual model object or proxy
            if not isinstance(model, ARCTransductionModel):
                # Use a fresh model if none provided
                model = ARCTransductionModel()
            
            fine_tuned = self.trainer.test_time_train(model, task)
            return {"success": True, "model": fine_tuned}
        elif operation == "create_pseudo_tasks":
            task_dict = params.get("task", {})
            task = ARCTask.from_dict(task_dict)
            pseudo_tasks = self.trainer.create_pseudo_tasks(task)
            return {"success": True, "pseudo_tasks": [t.to_dict() for t in pseudo_tasks]}
        else:
            raise InvalidParameterError(parameter="operation", value=operation, reason="Unsupported operation")

class ARCTestTimeTraining:
    """Test-time training for ARC transduction models"""
    
    def __init__(self, augmentation_fn: Optional[Callable] = None):
        """
        Initialize test-time training.
        
        Args:
            augmentation_fn: Optional augmentation function (creates default if None)
        """
        self.augmentation = ARCDataAugmentation() if augmentation_fn is None else augmentation_fn
    
    def create_pseudo_tasks(
        self,
        task: ARCTask,
        augmentation_fn: Optional[Callable] = None,
        n_augmentations: int = 10
    ) -> List[ARCTask]:
        """
        Create pseudo-training tasks by treating each example as test case.
        
        For each training example, we treat it as a "fake test case" and use
        the remaining examples as training data. This creates pseudo tasks that
        can be used for test-time training without ground truth test outputs.
        
        Args:
            task: Original ARC task
            augmentation_fn: Optional augmentation function
            n_augmentations: Number of augmentations per pseudo task
            
        Returns:
            List of pseudo ARC tasks for training
        """
        if len(task.train_inputs) < 2:
            # Need at least 2 examples to create pseudo tasks
            return []
        
        pseudo_tasks = []
        
        # For each training example, create a pseudo task
        for test_idx in range(len(task.train_inputs)):
            # Use this example as "test" case
            pseudo_test_input = task.train_inputs[test_idx]
            pseudo_test_output = task.train_outputs[test_idx]
            
            # Use remaining examples as training data
            pseudo_train_inputs = [
                task.train_inputs[i] 
                for i in range(len(task.train_inputs)) 
                if i != test_idx
            ]
            pseudo_train_outputs = [
                task.train_outputs[i] 
                for i in range(len(task.train_outputs)) 
                if i != test_idx
            ]
            
            # Create base pseudo task
            base_pseudo_task = ARCTask(
                train_inputs=pseudo_train_inputs,
                train_outputs=pseudo_train_outputs,
                test_input=pseudo_test_input
            )
            
            # Apply augmentations
            if augmentation_fn is not None:
                aug_tasks = augmentation_fn(base_pseudo_task)
                pseudo_tasks.extend(aug_tasks)
            else:
                # Use default augmentation
                aug_results = self.augmentation.augment_task(base_pseudo_task)
                # Extract just the tasks (not the inverse functions)
                aug_tasks = [aug_task for aug_task, _ in aug_results]
                pseudo_tasks.extend(aug_tasks)
            
            # Also add base task
            pseudo_tasks.append(base_pseudo_task)
        
        return pseudo_tasks[:n_augmentations * len(task.train_inputs)]
    
    def compute_test_time_loss(
        self,
        model: ARCTransductionModel,
        pseudo_task: ARCTask
    ) -> float:
        """
        Compute training loss for pseudo task.
        
        Args:
            model: Transduction model
            pseudo_task: Pseudo task (with test_input and expected output)
            
        Returns:
            Loss value (lower is better)
        """
        if pseudo_task.test_input is None or not pseudo_task.train_inputs:
            return float('inf')
        
        # Create training examples
        train_examples = list(zip(
            pseudo_task.train_inputs,
            pseudo_task.train_outputs
        ))
        
        # Predict
        predicted_output = model.predict(train_examples, pseudo_task.test_input)
        
        # Compute loss (simple: grid difference)
        # In full implementation, this would use proper loss function
        try:
            import numpy as np
            pred_np = np.array(predicted_output)
            target_np = np.array(pseudo_task.train_outputs[0])  # Use first output as target
            
            # Simple L2 loss (would be more sophisticated in full implementation)
            if pred_np.shape == target_np.shape:
                loss = np.mean((pred_np - target_np) ** 2)
            else:
                loss = float('inf')
        except Exception:
            loss = float('inf')
        
        return loss
    
    def test_time_train(
        self,
        model: ARCTransductionModel,
        task: ARCTask,
        epochs: int = 3,
        learning_rate: float = 2e-4,
        batch_size: int = 2
    ) -> ARCTransductionModel:
        """
        Fine-tune model on task at test time.
        
        Args:
            model: Model to fine-tune
            task: ARC task to train on
            epochs: Number of training epochs
            learning_rate: Learning rate for fine-tuning
            batch_size: Batch size for training
            
        Returns:
            Fine-tuned model (may be same instance, modified in-place)
        """
        # Create pseudo tasks
        pseudo_tasks = self.create_pseudo_tasks(task)
        
        if not pseudo_tasks:
            # Cannot create pseudo tasks, return original model
            return model
        
        # Training loop (simplified - full implementation would do proper backprop)
        for epoch in range(epochs):
            # Shuffle pseudo tasks
            random.shuffle(pseudo_tasks)
            
            # Process in batches
            for i in range(0, len(pseudo_tasks), batch_size):
                batch = pseudo_tasks[i:i + batch_size]
                
                # Compute loss for batch
                batch_losses = []
                for pseudo_task in batch:
                    loss = self.compute_test_time_loss(model, pseudo_task)
                    batch_losses.append(loss)
                
                # In full implementation, would:
                # 1. Backpropagate gradients
                # 2. Update model weights
                # 3. Track training metrics
                
                # Placeholder: model would be updated here
                # model.update_weights(batch_losses, learning_rate)
        
        return model
    
    def test_time_train_with_augmentation(
        self,
        model: ARCTransductionModel,
        task: ARCTask,
        epochs: int = 3,
        learning_rate: float = 2e-4,
        augmentation_repeats: int = 10
    ) -> ARCTransductionModel:
        """
        Test-time training with multiple augmented versions.
        
        Args:
            model: Model to fine-tune
            task: ARC task
            epochs: Training epochs
            learning_rate: Learning rate
            augmentation_repeats: How many times to repeat augmentation
            
        Returns:
            Fine-tuned model
        """
        # Create multiple augmented versions
        all_pseudo_tasks = []
        
        for _ in range(augmentation_repeats):
            pseudo_tasks = self.create_pseudo_tasks(task)
            all_pseudo_tasks.extend(pseudo_tasks)
        
        # Train on all pseudo tasks
        if all_pseudo_tasks:
            # Create combined task with all pseudo examples
            combined_inputs = []
            combined_outputs = []
            
            for pseudo_task in all_pseudo_tasks:
                combined_inputs.extend(pseudo_task.train_inputs)
                combined_outputs.extend(pseudo_task.train_outputs)
            
            combined_task = ARCTask(
                train_inputs=combined_inputs,
                train_outputs=combined_outputs,
                test_input=task.test_input
            )
            
            return self.test_time_train(
                model, 
                combined_task, 
                epochs=epochs, 
                learning_rate=learning_rate
            )
        
        return model

