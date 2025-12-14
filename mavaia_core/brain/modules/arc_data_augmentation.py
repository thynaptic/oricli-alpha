"""
ARC Data Augmentation Module

Implements data augmentation transformations for ARC tasks:
- Transposition (flip rows/columns)
- Color permutation
- Rotation
- Inverse transformations

Based on "Combining Induction and Transduction for Abstract Reasoning" (arxiv:2411.02272)
"""

import copy
import random
from typing import Any, Callable, Dict, List, Optional, Tuple

import numpy as np


class ARCTask:
    """ARC task representation with training examples and test input"""
    
    def __init__(
        self,
        train_inputs: List[List[List[Any]]],
        train_outputs: List[List[List[Any]]],
        test_input: Optional[List[List[Any]]] = None
    ):
        """
        Initialize ARC task.
        
        Args:
            train_inputs: List of training input grids
            train_outputs: List of training output grids
            test_input: Optional test input grid
        """
        self.train_inputs = train_inputs
        self.train_outputs = train_outputs
        self.test_input = test_input
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary"""
        return {
            "train_inputs": self.train_inputs,
            "train_outputs": self.train_outputs,
            "test_input": self.test_input
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "ARCTask":
        """Create from dictionary"""
        return cls(
            train_inputs=data["train_inputs"],
            train_outputs=data["train_outputs"],
            test_input=data.get("test_input")
        )


class ARCDataAugmentation:
    """Data augmentation for ARC tasks"""
    
    def __init__(self, random_seed: Optional[int] = None):
        """
        Initialize augmentation module.
        
        Args:
            random_seed: Optional random seed for reproducibility
        """
        if random_seed is not None:
            random.seed(random_seed)
            np.random.seed(random_seed)
    
    def transpose_grid(self, grid: List[List[Any]]) -> List[List[Any]]:
        """
        Apply transposition transformation: T_t(x) = x^T
        
        Args:
            grid: Input grid (list of rows)
            
        Returns:
            Transposed grid (columns become rows)
        """
        if not grid:
            return grid
        
        # Convert to numpy for easy transposition
        np_grid = np.array(grid)
        transposed = np.transpose(np_grid).tolist()
        return transposed
    
    def transpose_task(self, task: ARCTask) -> ARCTask:
        """
        Apply transposition transformation to entire task.
        
        Args:
            task: ARC task to transform
            
        Returns:
            New ARCTask with transposed grids
        """
        # Transpose all training examples
        transposed_inputs = [self.transpose_grid(g) for g in task.train_inputs]
        transposed_outputs = [self.transpose_grid(g) for g in task.train_outputs]
        
        # Transpose test input if present
        transposed_test = None
        if task.test_input is not None:
            transposed_test = self.transpose_grid(task.test_input)
        
        return ARCTask(
            train_inputs=transposed_inputs,
            train_outputs=transposed_outputs,
            test_input=transposed_test
        )
    
    def generate_color_permutation(self, n_colors: int = 10) -> Dict[int, int]:
        """
        Generate random color permutation.
        
        Args:
            n_colors: Number of colors (default 10 for ARC)
            
        Returns:
            Dictionary mapping old color -> new color
        """
        colors = list(range(n_colors))
        shuffled = colors.copy()
        random.shuffle(shuffled)
        return dict(zip(colors, shuffled))
    
    def permute_colors_grid(
        self, 
        grid: List[List[Any]], 
        permutation: Dict[int, int]
    ) -> List[List[Any]]:
        """
        Apply color permutation to grid.
        
        Args:
            grid: Input grid
            permutation: Dictionary mapping old color -> new color
            
        Returns:
            Grid with permuted colors
        """
        result = copy.deepcopy(grid)
        
        for i in range(len(result)):
            for j in range(len(result[i])):
                old_color = result[i][j]
                # Apply permutation if color is in permutation dict
                if old_color in permutation:
                    result[i][j] = permutation[old_color]
        
        return result
    
    def permute_colors(self, task: ARCTask, permutation: Optional[Dict[int, int]] = None) -> ARCTask:
        """
        Apply color permutation to entire task.
        
        Args:
            task: ARC task to transform
            permutation: Optional permutation dict, generates random if None
            
        Returns:
            New ARCTask with permuted colors
        """
        if permutation is None:
            # Extract all unique colors from task
            all_colors = set()
            for grid in task.train_inputs + task.train_outputs:
                if task.test_input is not None:
                    all_colors.update(_extract_colors_from_grid(task.test_input))
                all_colors.update(_extract_colors_from_grid(grid))
            
            # Generate permutation for all colors found
            max_color = max(all_colors) if all_colors else 9
            permutation = self.generate_color_permutation(max_color + 1)
        
        # Apply permutation to all grids
        permuted_inputs = [
            self.permute_colors_grid(g, permutation) 
            for g in task.train_inputs
        ]
        permuted_outputs = [
            self.permute_colors_grid(g, permutation) 
            for g in task.train_outputs
        ]
        
        permuted_test = None
        if task.test_input is not None:
            permuted_test = self.permute_colors_grid(task.test_input, permutation)
        
        return ARCTask(
            train_inputs=permuted_inputs,
            train_outputs=permuted_outputs,
            test_input=permuted_test
        )
    
    def rotate_grid(self, grid: List[List[Any]], degrees: int) -> List[List[Any]]:
        """
        Rotate grid by specified degrees (90, 180, or 270).
        
        Args:
            grid: Input grid
            degrees: Rotation degrees (must be 90, 180, or 270)
            
        Returns:
            Rotated grid
        """
        if not grid:
            return grid
        
        # Normalize degrees to 0, 90, 180, 270
        degrees = degrees % 360
        if degrees not in [0, 90, 180, 270]:
            raise ValueError(f"Rotation degrees must be 90, 180, or 270, got {degrees}")
        
        np_grid = np.array(grid)
        
        if degrees == 0:
            return grid
        elif degrees == 90:
            # Rotate 90 degrees clockwise
            rotated = np.rot90(np_grid, k=-1).tolist()
        elif degrees == 180:
            # Rotate 180 degrees
            rotated = np.rot90(np_grid, k=2).tolist()
        elif degrees == 270:
            # Rotate 270 degrees clockwise (same as 90 counter-clockwise)
            rotated = np.rot90(np_grid, k=1).tolist()
        
        return rotated
    
    def rotate_task(self, task: ARCTask, degrees: int) -> ARCTask:
        """
        Apply rotation to entire task.
        
        Args:
            task: ARC task to transform
            degrees: Rotation degrees (90, 180, or 270)
            
        Returns:
            New ARCTask with rotated grids
        """
        rotated_inputs = [self.rotate_grid(g, degrees) for g in task.train_inputs]
        rotated_outputs = [self.rotate_grid(g, degrees) for g in task.train_outputs]
        
        rotated_test = None
        if task.test_input is not None:
            rotated_test = self.rotate_grid(task.test_input, degrees)
        
        return ARCTask(
            train_inputs=rotated_inputs,
            train_outputs=rotated_outputs,
            test_input=rotated_test
        )
    
    def generate_transformations(self) -> List[Callable[[ARCTask], Tuple[ARCTask, Callable]]]:
        """
        Generate list of transformation functions with their inverses.
        
        Returns:
            List of (transform_function, inverse_function) tuples.
            Each transform_function takes ARCTask and returns transformed ARCTask.
            Each inverse_function takes a grid and returns inverse-transformed grid.
        """
        transformations = []
        
        # Identity (no transformation)
        def identity_transform(task: ARCTask) -> Tuple[ARCTask, Callable]:
            return task, lambda x: x
        
        transformations.append(identity_transform)
        
        # Transposition (inverse is transposition itself)
        def transpose_transform(task: ARCTask) -> Tuple[ARCTask, Callable]:
            transformed = self.transpose_task(task)
            return transformed, self.transpose_grid
        
        transformations.append(transpose_transform)
        
        # Color permutations (generate multiple random ones)
        for _ in range(3):
            def create_permute_transform(perm: Dict[int, int]):
                def permute_transform(task: ARCTask) -> Tuple[ARCTask, Callable]:
                    transformed = self.permute_colors(task, perm)
                    # Create inverse permutation
                    inv_perm = {v: k for k, v in perm.items()}
                    return transformed, lambda grid: self.permute_colors_grid(grid, inv_perm)
                return permute_transform
            
            perm = self.generate_color_permutation()
            transformations.append(create_permute_transform(perm))
        
        # Rotations
        for degrees in [90, 180, 270]:
            def create_rotate_transform(d: int):
                def rotate_transform(task: ARCTask) -> Tuple[ARCTask, Callable]:
                    transformed = self.rotate_task(task, d)
                    # Inverse rotation
                    inv_degrees = (360 - d) % 360
                    return transformed, lambda grid: self.rotate_grid(grid, inv_degrees)
                return rotate_transform
            
            transformations.append(create_rotate_transform(degrees))
        
        return transformations
    
    def augment_task(self, task: ARCTask) -> List[Tuple[ARCTask, Callable]]:
        """
        Apply all transformations to task.
        
        Args:
            task: ARC task to augment
            
        Returns:
            List of (transformed_task, inverse_transform_function) tuples
        """
        transformations = self.generate_transformations()
        results = []
        
        for transform_fn in transformations:
            transformed_task, inverse_fn = transform_fn(task)
            results.append((transformed_task, inverse_fn))
        
        return results
    
    def apply_inverse_transform(
        self, 
        prediction: List[List[Any]], 
        inverse_transform: Callable[[List[List[Any]]], List[List[Any]]]
    ) -> List[List[Any]]:
        """
        Apply inverse transformation to prediction.
        
        Args:
            prediction: Predicted grid after transformation
            inverse_transform: Inverse transformation function
            
        Returns:
            Grid transformed back to original space
        """
        return inverse_transform(prediction)


def _extract_colors_from_grid(grid: List[List[Any]]) -> set:
    """Extract all unique color values from grid"""
    colors = set()
    for row in grid:
        for cell in row:
            if isinstance(cell, (int, float)):
                colors.add(int(cell))
    return colors

