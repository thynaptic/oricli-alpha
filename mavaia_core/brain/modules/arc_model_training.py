from __future__ import annotations
"""
ARC Model Training Infrastructure

Training pipeline for induction and transduction models.
Implements hyperparameters and training procedures from the paper.

Based on "Combining Induction and Transduction for Abstract Reasoning" (arxiv:2411.02272)
"""

import json
import logging
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

from mavaia_core.brain.modules.arc_data_augmentation import ARCTask
from mavaia_core.brain.modules.arc_synthetic_data import ARCSyntheticDataGenerator
from mavaia_core.brain.modules.arc_transduction_model import ARCTransductionModel
from mavaia_core.exceptions import InvalidParameterError

logger = logging.getLogger(__name__)


class ARCModelTraining:
    """Training infrastructure for ARC models"""
    
    # Hyperparameters from paper
    INDUCTION_LORA_RANK = 64
    INDUCTION_LORA_ALPHA = 64
    INDUCTION_LEARNING_RATE = 2e-4
    INDUCTION_BATCH_SIZE = 8  # per device
    INDUCTION_NUM_DEVICES = 8
    INDUCTION_EPOCHS = 3
    INDUCTION_FULL_FINETUNE_LR = 1e-5
    INDUCTION_FULL_FINETUNE_BATCH = 16
    INDUCTION_FULL_FINETUNE_EPOCHS = 2
    
    TRANSDUCTION_LEARNING_RATE = 1e-5
    TRANSDUCTION_WEIGHT_DECAY = 1e-2
    TRANSDUCTION_BATCH_SIZE = 8  # per device
    TRANSDUCTION_EPOCHS = 2  # 3 for engineering results
    
    TEST_TIME_LORA_RANK = 64
    TEST_TIME_LORA_ALPHA = 64
    TEST_TIME_LEARNING_RATE = 2e-4
    TEST_TIME_BATCH_SIZE = 2  # per device
    TEST_TIME_NUM_DEVICES = 4
    TEST_TIME_EPOCHS = 3
    
    def __init__(self, output_dir: Optional[str] = None):
        """
        Initialize training infrastructure.
        
        Args:
            output_dir: Directory to save models and checkpoints
        """
        self.output_dir = Path(output_dir) if output_dir else Path("./arc_models")
        self.output_dir.mkdir(parents=True, exist_ok=True)
        self.synthetic_generator = ARCSyntheticDataGenerator()
    
    def train_induction_model(
        self,
        data_path: str,
        output_path: Optional[str] = None,
        use_full_finetune: bool = False
    ) -> Dict[str, Any]:
        """
        Train program synthesis (induction) model.
        
        Args:
            data_path: Path to training data (JSON file with ARC tasks)
            output_path: Optional output path for model
            use_full_finetune: Whether to use full fine-tuning (for last 230k data)
            
        Returns:
            Dictionary with training results
        """
        if output_path is None:
            model_name = "induction_full" if use_full_finetune else "induction_lora"
            output_path = str(self.output_dir / f"{model_name}.pt")
        
        # Load training data
        training_data = self._load_training_data(data_path)
        
        if not training_data:
            return {
                "success": False,
                "error": "No training data loaded"
            }
        
        # Configure hyperparameters
        if use_full_finetune:
            config = {
                "learning_rate": self.INDUCTION_FULL_FINETUNE_LR,
                "batch_size": self.INDUCTION_FULL_FINETUNE_BATCH,
                "epochs": self.INDUCTION_FULL_FINETUNE_EPOCHS,
                "training_type": "full_finetune",
                "weight_decay": 0.05,
                "gradient_accumulate_steps": 1,
                "scheduler": "cosine"
            }
        else:
            config = {
                "lora_rank": self.INDUCTION_LORA_RANK,
                "lora_alpha": self.INDUCTION_LORA_ALPHA,
                "learning_rate": self.INDUCTION_LEARNING_RATE,
                "batch_size": self.INDUCTION_BATCH_SIZE,
                "per_device_batch": self.INDUCTION_BATCH_SIZE,
                "num_devices": self.INDUCTION_NUM_DEVICES,
                "epochs": self.INDUCTION_EPOCHS,
                "training_type": "lora_finetune",
                "weight_decay": 0,
                "gradient_accumulate_steps": 2,
                "scheduler": "cosine"
            }
        
        # Placeholder for actual training
        # In full implementation, this would:
        # 1. Initialize model (LLM with LoRA or full fine-tuning)
        # 2. Create data loader from training_data
        # 3. Training loop with optimizer
        # 4. Save checkpoints
        # 5. Save final model
        
        logger.info(
            "Training induction model (placeholder pipeline)",
            extra={"module_name": "arc_model_training", "examples": len(training_data), "training_type": config.get("training_type")},
        )
        logger.debug(
            "Induction training config",
            extra={"module_name": "arc_model_training", "config": {k: str(v) for k, v in config.items()}},
        )
        
        # Save config
        config_path = output_path.replace(".pt", "_config.json")
        with open(config_path, "w") as f:
            json.dump(config, f, indent=2)
        
        return {
            "success": True,
            "model_path": output_path,
            "config_path": config_path,
            "num_examples": len(training_data),
            "config": config
        }
    
    def train_transduction_model(
        self,
        data_path: str,
        output_path: Optional[str] = None,
        epochs: Optional[int] = None
    ) -> Dict[str, Any]:
        """
        Train neural transduction model.
        
        Args:
            data_path: Path to training data
            output_path: Optional output path for model
            epochs: Optional number of epochs (default 2, use 3 for engineering)
            
        Returns:
            Dictionary with training results
        """
        if output_path is None:
            output_path = str(self.output_dir / "transduction.pt")
        
        if epochs is None:
            epochs = self.TRANSDUCTION_EPOCHS
        
        # Load training data
        training_data = self._load_training_data(data_path)
        
        if not training_data:
            return {
                "success": False,
                "error": "No training data loaded"
            }
        
        # Configure hyperparameters
        config = {
            "learning_rate": self.TRANSDUCTION_LEARNING_RATE,
            "weight_decay": self.TRANSDUCTION_WEIGHT_DECAY,
            "batch_size": self.TRANSDUCTION_BATCH_SIZE,
            "epochs": epochs,
            "training_type": "full_finetune",
            "gradient_accumulate_steps": 2,
            "num_devices": 8,
            "scheduler": "cosine",
            "beam_width": 3  # Can be 20-40 for engineering results
        }
        
        # Initialize model
        model = ARCTransductionModel()
        
        # Placeholder for actual training
        # In full implementation, this would:
        # 1. Initialize neural architecture (Transformer/CNN)
        # 2. Create data loader
        # 3. Training loop
        # 4. Save model
        
        logger.info(
            "Training transduction model (placeholder pipeline)",
            extra={"module_name": "arc_model_training", "examples": len(training_data), "training_type": config.get("training_type")},
        )
        logger.debug(
            "Transduction training config",
            extra={"module_name": "arc_model_training", "config": {k: str(v) for k, v in config.items()}},
        )
        
        # Save config
        config_path = output_path.replace(".pt", "_config.json")
        with open(config_path, "w") as f:
            json.dump(config, f, indent=2)
        
        # Save model (placeholder)
        model.save_model(output_path)
        
        return {
            "success": True,
            "model_path": output_path,
            "config_path": config_path,
            "num_examples": len(training_data),
            "config": config
        }
    
    def fine_tune_on_task(
        self,
        model: ARCTransductionModel,
        task: ARCTask,
        epochs: Optional[int] = None
    ) -> ARCTransductionModel:
        """
        Test-time fine-tuning on specific task.
        
        Args:
            model: Model to fine-tune
            task: ARC task to train on
            epochs: Number of epochs (default from config)
            
        Returns:
            Fine-tuned model
        """
        from mavaia_core.brain.modules.arc_test_time_training import ARCTestTimeTraining
        
        if epochs is None:
            epochs = self.TEST_TIME_EPOCHS
        
        # Configure test-time training
        config = {
            "lora_rank": self.TEST_TIME_LORA_RANK,
            "lora_alpha": self.TEST_TIME_LORA_ALPHA,
            "learning_rate": self.TEST_TIME_LEARNING_RATE,
            "batch_size": self.TEST_TIME_BATCH_SIZE,
            "per_device_batch": self.TEST_TIME_BATCH_SIZE,
            "num_devices": self.TEST_TIME_NUM_DEVICES,
            "epochs": epochs,
            "training_type": "lora_finetune",
            "weight_decay": 0,
            "gradient_accumulate_steps": 2,
            "scheduler": "cosine"
        }
        
        # Use test-time training
        trainer = ARCTestTimeTraining()
        fine_tuned_model = trainer.test_time_train(
            model,
            task,
            epochs=epochs,
            learning_rate=config["learning_rate"],
            batch_size=config["batch_size"]
        )
        
        return fine_tuned_model
    
    def _load_training_data(self, data_path: str) -> List[ARCTask]:
        """
        Load training data from file.
        
        Args:
            data_path: Path to JSON file with ARC tasks
            
        Returns:
            List of ARC tasks
        """
        try:
            with open(data_path, "r") as f:
                data = json.load(f)
            
            tasks = []
            if isinstance(data, list):
                for item in data:
                    if isinstance(item, dict):
                        task = ARCTask.from_dict(item)
                        tasks.append(task)
            elif isinstance(data, dict):
                # Single task
                task = ARCTask.from_dict(data)
                tasks.append(task)
            
            return tasks
            
        except Exception as e:
            logger.warning(
                "Failed to load ARC training data",
                exc_info=True,
                extra={"module_name": "arc_model_training", "data_path": str(data_path), "error_type": type(e).__name__},
            )
            return []
    
    def generate_synthetic_data(
        self,
        base_programs: List[str],
        examples_per_program: int = 5,
        output_path: Optional[str] = None
    ) -> str:
        """
        Generate synthetic training data from Python programs.
        
        Args:
            base_programs: List of Python program code strings
            examples_per_program: Number of examples to generate per program
            output_path: Optional output path for generated data
            
        Returns:
            Path to generated data file
        """
        if output_path is None:
            output_path = str(self.output_dir / "synthetic_training_data.json")
        
        all_tasks = []
        
        for program_code in base_programs:
            # Generate task from program
            task = self.synthetic_generator.generate_from_program(
                program_code,
                n_examples=examples_per_program
            )
            
            if task:
                all_tasks.append(task.to_dict())
        
        # Save to file
        with open(output_path, "w") as f:
            json.dump(all_tasks, f, indent=2)
        
        logger.info(
            "Generated synthetic ARC tasks",
            extra={"module_name": "arc_model_training", "task_count": len(all_tasks), "output_path": str(output_path)},
        )
        
        return output_path
    
    def create_training_config(
        self,
        model_type: str,
        custom_config: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Create training configuration.
        
        Args:
            model_type: "induction" or "transduction"
            custom_config: Optional custom configuration overrides
            
        Returns:
            Configuration dictionary
        """
        if model_type == "induction":
            config = {
                "lora_rank": self.INDUCTION_LORA_RANK,
                "lora_alpha": self.INDUCTION_LORA_ALPHA,
                "learning_rate": self.INDUCTION_LEARNING_RATE,
                "batch_size": self.INDUCTION_BATCH_SIZE,
                "epochs": self.INDUCTION_EPOCHS,
                "gradient_accumulate_steps": 2,
                "num_devices": self.INDUCTION_NUM_DEVICES,
                "weight_decay": 0,
                "scheduler": "cosine",
                "training_type": "lora_finetune"
            }
        elif model_type == "transduction":
            config = {
                "learning_rate": self.TRANSDUCTION_LEARNING_RATE,
                "weight_decay": self.TRANSDUCTION_WEIGHT_DECAY,
                "batch_size": self.TRANSDUCTION_BATCH_SIZE,
                "epochs": self.TRANSDUCTION_EPOCHS,
                "gradient_accumulate_steps": 2,
                "num_devices": 8,
                "scheduler": "cosine",
                "training_type": "full_finetune",
                "beam_width": 3
            }
        else:
            raise InvalidParameterError("model_type", str(model_type), "Unknown model_type (expected 'induction' or 'transduction')")
        
        # Apply custom overrides
        if custom_config:
            config.update(custom_config)
        
        return config

