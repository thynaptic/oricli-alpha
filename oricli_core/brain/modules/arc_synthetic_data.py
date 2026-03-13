from __future__ import annotations
"""
ARC Synthetic Data Generator

Generates synthetic ARC problems from existing Python program solutions.
Based on methodology from "Combining Induction and Transduction for Abstract Reasoning" (arxiv:2411.02272)

Method:
1. Start with Python program solutions for ARC tasks
2. For each program f, create probabilistic input generator
3. Generate input-output pairs by executing f on sampled inputs
4. Creates 400k+ synthetic problems
"""

import copy
import random
import logging
from typing import Any, Callable, Dict, List, Optional, Tuple

import numpy as np

from oricli_core.brain.modules.arc_data_augmentation import ARCTask
from oricli_core.exceptions import InvalidParameterError

logger = logging.getLogger(__name__)


class ARCSyntheticDataGenerator:
    """Generate synthetic ARC problems from Python program solutions"""
    
    def __init__(self, random_seed: Optional[int] = None):
        """
        Initialize synthetic data generator.
        
        Args:
            random_seed: Optional random seed for reproducibility
        """
        if random_seed is not None:
            random.seed(random_seed)
            np.random.seed(random_seed)
        
        self._execution_globals = {
            'np': np,
            'numpy': np,
            'random': random,
            'range': range,
            'len': len,
            'min': min,
            'max': max,
            'sum': sum,
            'abs': abs,
            'int': int,
            'float': float,
            'str': str,
            'list': list,
            'dict': dict,
            'tuple': tuple,
            'set': set,
            'sorted': sorted,
            'reversed': reversed,
        }
    
    def _safe_execute_program(
        self, 
        program_code: str, 
        input_grid: List[List[Any]]
    ) -> Optional[List[List[Any]]]:
        """
        Safely execute program on input grid.
        
        Args:
            program_code: Python code that defines a function
            input_grid: Input grid to process
            
        Returns:
            Output grid if execution succeeds, None otherwise
        """
        try:
            # Create execution environment
            local_env = copy.deepcopy(self._execution_globals)
            local_env['input_grid'] = input_grid
            
            # Execute program code
            exec(program_code, local_env)
            
            # Try to find and call the transform function
            if 'transform' in local_env:
                transform_fn = local_env['transform']
                if callable(transform_fn):
                    result = transform_fn(input_grid)
                    # Convert numpy array to list if needed
                    if isinstance(result, np.ndarray):
                        return result.tolist()
                    return result
            
            # Try common function names
            for fn_name in ['solve', 'process', 'apply_transform', 'f']:
                if fn_name in local_env:
                    fn = local_env[fn_name]
                    if callable(fn):
                        result = fn(input_grid)
                        if isinstance(result, np.ndarray):
                            return result.tolist()
                        return result
            
            return None
            
        except Exception as e:
            # Execution failed
            logger.debug(
                "Program execution failed during synthetic data generation",
                exc_info=True,
                extra={"module_name": "arc_synthetic_data", "error_type": type(e).__name__},
            )
            return None
    
    def _validate_grid(self, grid: Any) -> bool:
        """
        Validate grid structure.
        
        Args:
            grid: Grid to validate
            
        Returns:
            True if valid grid
        """
        if not isinstance(grid, list):
            return False
        
        if not grid:
            return False
        
        if not all(isinstance(row, list) for row in grid):
            return False
        
        # Check all rows have same length
        if len(set(len(row) for row in grid)) > 1:
            return False
        
        return True
    
    def _generate_random_grid(
        self,
        width: int = 10,
        height: int = 10,
        n_colors: int = 10,
        sparsity: float = 0.7
    ) -> List[List[Any]]:
        """
        Generate random input grid.
        
        Args:
            width: Grid width
            height: Grid height
            n_colors: Number of colors (0 to n_colors-1)
            sparsity: Probability of cell being background (0), higher = more sparse
            
        Returns:
            Random grid
        """
        grid = []
        for _ in range(height):
            row = []
            for _ in range(width):
                if random.random() < sparsity:
                    # Background
                    row.append(0)
                else:
                    # Random color
                    row.append(random.randint(0, n_colors - 1))
            grid.append(row)
        
        return grid
    
    def _generate_structured_grid(
        self,
        width: int = 10,
        height: int = 10,
        pattern_type: str = "random"
    ) -> List[List[Any]]:
        """
        Generate structured input grid with patterns.
        
        Args:
            width: Grid width
            height: Grid height
            pattern_type: Type of pattern ("random", "filled", "checkerboard", "lines")
            
        Returns:
            Structured grid
        """
        if pattern_type == "random":
            return self._generate_random_grid(width, height)
        elif pattern_type == "filled":
            # Fully filled with random colors
            return self._generate_random_grid(width, height, sparsity=0.0)
        elif pattern_type == "checkerboard":
            grid = []
            for i in range(height):
                row = []
                for j in range(width):
                    if (i + j) % 2 == 0:
                        row.append(1)
                    else:
                        row.append(0)
                grid.append(row)
            return grid
        elif pattern_type == "lines":
            grid = [[0] * width for _ in range(height)]
            # Add horizontal lines
            for i in range(0, height, 2):
                for j in range(width):
                    grid[i][j] = 1
            return grid
        else:
            return self._generate_random_grid(width, height)
    
    def sample_inputs(
        self,
        program_code: str,
        n_samples: int,
        constraints: Optional[Dict[str, Any]] = None
    ) -> List[List[List[Any]]]:
        """
        Sample appropriate input grids for program.
        
        Args:
            program_code: Python program code
            n_samples: Number of samples to generate
            constraints: Optional constraints (width, height, n_colors, pattern_types)
            
        Returns:
            List of sampled input grids
        """
        if constraints is None:
            constraints = {}
        
        width = constraints.get('width', 10)
        height = constraints.get('height', 10)
        n_colors = constraints.get('n_colors', 10)
        pattern_types = constraints.get('pattern_types', ['random', 'filled', 'checkerboard', 'lines'])
        
        inputs = []
        
        for _ in range(n_samples):
            # Randomly select pattern type
            pattern_type = random.choice(pattern_types)
            grid = self._generate_structured_grid(width, height, pattern_type)
            
            # Validate grid
            if self._validate_grid(grid):
                inputs.append(grid)
        
        return inputs
    
    def execute_program(
        self,
        program_code: str,
        inputs: List[List[List[Any]]]
    ) -> List[Optional[List[List[Any]]]]:
        """
        Execute program on multiple inputs.
        
        Args:
            program_code: Python program code
            inputs: List of input grids
            
        Returns:
            List of output grids (None if execution failed)
        """
        outputs = []
        
        for input_grid in inputs:
            output = self._safe_execute_program(program_code, input_grid)
            outputs.append(output)
        
        return outputs
    
    def generate_from_program(
        self,
        program_code: str,
        n_examples: int = 5,
        input_generator: Optional[Callable] = None,
        constraints: Optional[Dict[str, Any]] = None
    ) -> Optional[ARCTask]:
        """
        Generate synthetic ARC task from Python program.
        
        Args:
            program_code: Python code that defines a transform function
            n_examples: Number of training examples to generate
            input_generator: Optional custom input generator function
            constraints: Optional constraints for input generation
            
        Returns:
            ARCTask with generated examples, or None if generation failed
        """
        # Generate inputs
        if input_generator is not None:
            inputs = [input_generator() for _ in range(n_examples)]
        else:
            inputs = self.sample_inputs(program_code, n_examples, constraints)
        
        # Execute program on inputs
        outputs = self.execute_program(program_code, inputs)
        
        # Filter out failed executions
        valid_pairs = []
        for inp, out in zip(inputs, outputs):
            if out is not None and self._validate_grid(out):
                valid_pairs.append((inp, out))
        
        if len(valid_pairs) < 2:
            # Need at least 2 valid examples
            return None
        
        # Split into train and optionally test
        train_inputs = [inp for inp, _ in valid_pairs]
        train_outputs = [out for _, out in valid_pairs]
        
        return ARCTask(
            train_inputs=train_inputs,
            train_outputs=train_outputs,
            test_input=None  # Can generate test separately
        )
    
    def expand_task_collection(
        self,
        base_tasks: List[ARCTask],
        expansion_factor: int = 10
    ) -> List[ARCTask]:
        """
        Create variations of existing tasks.
        
        Args:
            base_tasks: List of base ARC tasks
            expansion_factor: How many variations per base task
            
        Returns:
            Expanded list of tasks
        """
        expanded = []
        
        for base_task in base_tasks:
            # Add original task
            expanded.append(base_task)
            
            # Create variations by adding noise or modifying inputs
            for _ in range(expansion_factor - 1):
                # Create variation by adding slight modifications
                var_inputs = []
                var_outputs = []
                
                for inp, out in zip(base_task.train_inputs, base_task.train_outputs):
                    # Add small random modifications
                    var_inp = copy.deepcopy(inp)
                    var_out = copy.deepcopy(out)
                    
                    # Optionally add noise (with low probability)
                    if random.random() < 0.1:  # 10% chance
                        # Add random cell modification
                        if var_inp and len(var_inp) > 0:
                            row = random.randint(0, len(var_inp) - 1)
                            col = random.randint(0, len(var_inp[0]) - 1)
                            var_inp[row][col] = random.randint(0, 9)
                    
                    var_inputs.append(var_inp)
                    var_outputs.append(var_out)
                
                var_task = ARCTask(
                    train_inputs=var_inputs,
                    train_outputs=var_outputs,
                    test_input=copy.deepcopy(base_task.test_input) if base_task.test_input else None
                )
                expanded.append(var_task)
        
        return expanded
    
    def create_synthetic_task(
        self,
        examples: List[Tuple[List[List[Any]], List[List[Any]]]]
    ) -> ARCTask:
        """
        Format examples as ARC task.
        
        Args:
            examples: List of (input_grid, output_grid) tuples
            
        Returns:
            ARCTask
        """
        if not examples:
            raise InvalidParameterError(
                parameter="examples",
                value="[]",
                reason="Cannot create task from empty examples list",
            )
        
        train_inputs = [inp for inp, _ in examples]
        train_outputs = [out for _, out in examples]
        
        return ARCTask(
            train_inputs=train_inputs,
            train_outputs=train_outputs,
            test_input=None
        )

