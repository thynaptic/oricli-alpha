from __future__ import annotations
"""
ARC Induction Module
Implements the Induction (Program Synthesis) path for ARC solving.
Searches for Python programs that transform training inputs to outputs.
"""

import logging
import json
import traceback
from typing import Dict, Any, List, Optional, Callable
from pathlib import Path

import numpy as np

from oricli_core.brain.base_module import BaseBrainModule, ModuleMetadata
from oricli_core.brain.registry import ModuleRegistry
from oricli_core.exceptions import InvalidParameterError
from oricli_core.brain.modules.arc_data_augmentation import ARCTask

logger = logging.getLogger(__name__)

class ARCInductionModule(BaseBrainModule):
    """Brain module for ARC program synthesis (Induction)."""

    def __init__(self) -> None:
        super().__init__()
        self.ollama_provider = None
        self.max_attempts = 10
        # Common helper functions for ARC programs (the DSL)
        self.dsl_code = """
import numpy as np
from scipy.ndimage import label

def get_objects(grid, connectivity=4):
    \"\"\"Find contiguous objects of the same color (excluding 0).\"\"\"
    grid = np.array(grid)
    unique_colors = np.unique(grid)
    objects = []
    for color in unique_colors:
        if color == 0: continue
        mask = (grid == color).astype(int)
        structure = np.array([[0,1,0],[1,1,1],[0,1,0]]) if connectivity == 4 else np.ones((3,3))
        labeled, num_features = label(mask, structure=structure)
        for i in range(1, num_features + 1):
            coords = np.argwhere(labeled == i)
            objects.append({"color": int(color), "coords": coords})
    return objects

def flood_fill(grid, r, c, new_color):
    \"\"\"Standard flood fill starting from (r, c).\"\"\"
    grid = np.array(grid)
    old_color = grid[r, c]
    if old_color == new_color: return grid
    stack = [(r, c)]
    while stack:
        curr_r, curr_c = stack.pop()
        if grid[curr_r, curr_c] == old_color:
            grid[curr_r, curr_c] = new_color
            for dr, dc in [(0,1), (0,-1), (1,0), (-1,0)]:
                nr, nc = curr_r + dr, curr_c + dc
                if 0 <= nr < grid.shape[0] and 0 <= nc < grid.shape[1]:
                    stack.append((nr, nc))
    return grid

def move_object(grid, obj, dr, dc):
    \"\"\"Move an object by (dr, dc) offset.\"\"\"
    new_grid = np.array(grid)
    # Clear original
    for r, c in obj["coords"]:
        new_grid[r, c] = 0
    # Paint new position
    for r, c in obj["coords"]:
        nr, nc = r + dr, c + dc
        if 0 <= nr < new_grid.shape[0] and 0 <= nc < new_grid.shape[1]:
            new_grid[nr, nc] = obj["color"]
    return new_grid

def get_crop(grid):
    \"\"\"Crop the grid to non-zero elements.\"\"\"
    grid = np.array(grid)
    coords = np.argwhere(grid != 0)
    if coords.size == 0: return grid
    min_r, min_c = coords.min(axis=0)
    max_r, max_c = coords.max(axis=0)
    return grid[min_r:max_r+1, min_c:max_c+1]

def rotate_grid(grid, k=1):
    \"\"\"Rotate grid by k * 90 degrees counter-clockwise.\"\"\"
    return np.rot90(np.array(grid), k)

def flip_grid(grid, axis=0):
    \"\"\"Flip grid vertically (axis=0) or horizontally (axis=1).\"\"\"
    return np.flip(np.array(grid), axis)
"""

    @property
    def metadata(self) -> ModuleMetadata:
        return ModuleMetadata(
            name="arc_induction",
            version="1.0.0",
            description="Searches for Python programs to solve ARC tasks",
            operations=[
                "synthesize_program",
                "solve_task"
            ],
            dependencies=["ollama_provider"],
            model_required=False,
        )

    def initialize(self) -> bool:
        try:
            self.ollama_provider = ModuleRegistry.get_module("ollama_provider")
        except Exception:
            pass
        return True

    def execute(self, operation: str, params: Dict[str, Any]) -> Dict[str, Any]:
        if operation == "synthesize_program":
            task_dict = params.get("task", {})
            task = ARCTask.from_dict(task_dict)
            return self._synthesize_program(task)
        elif operation == "solve_task":
            task_dict = params.get("task", {})
            task = ARCTask.from_dict(task_dict)
            return self._solve_task(task)
        else:
            raise InvalidParameterError(parameter="operation", value=operation, reason="Unsupported operation")

    def _synthesize_program(self, task: ARCTask) -> Dict[str, Any]:
        """Attempt to synthesize a program that solves the training examples."""
        if not self.ollama_provider:
            return {"success": False, "error": "ollama_provider not available"}

        prompt = self._build_synthesis_prompt(task)
        
        best_program = None
        
        for attempt in range(self.max_attempts):
            _rich_log(f"Induction: Attempt {attempt+1}/{self.max_attempts} at program synthesis...", "cyan", "🔨")
            
            res = self.ollama_provider.execute("generate", {
                "prompt": prompt,
                "system": "You are a competitive programmer solving ARC (Abstraction and Reasoning Corpus) tasks. Write a Python function `transform(input_grid)` that maps the input to the output. Return ONLY the code.",
                "temperature": 0.7 + (attempt * 0.05) # Increase temperature over time for diversity
            })
            
            if res.get("success"):
                code = self._extract_code(res.get("text", ""))
                if code:
                    if self._verify_program(code, task):
                        _rich_log(f"Induction: SUCCESS! Found a working program on attempt {attempt+1}.", "green", "✅")
                        return {
                            "success": True, 
                            "program": code, 
                            "attempts": attempt + 1,
                            "method": "induction"
                        }
        
        return {"success": False, "error": "No working program found within budget"}

    def _solve_task(self, task: ARCTask) -> Dict[str, Any]:
        """Main entry point for induction solving."""
        res = self._synthesize_program(task)
        if res.get("success"):
            program = res.get("program")
            try:
                # Run the program on the test input
                output = self._run_program(program, task.test_input)
                return {
                    "success": True,
                    "prediction": output.tolist() if isinstance(output, np.ndarray) else output,
                    "confidence": 1.0, # Program verified on all train cases is high confidence
                    "method": "induction",
                    "program": program
                }
            except Exception as e:
                return {"success": False, "error": f"Execution error: {e}"}
        return res

    def _build_synthesis_prompt(self, task: ARCTask) -> str:
        """Create a prompt describing the ARC task examples."""
        prompt = "Task Description: Find the rule that transforms the input grids to the output grids.\n\n"
        
        for i, (inp, out) in enumerate(zip(task.train_inputs, task.train_outputs)):
            prompt += f"Example {i+1}:\nInput:\n{np.array(inp)}\nOutput:\n{np.array(out)}\n\n"
            
        prompt += "Write a Python function `transform(input_grid)` using numpy that performs this transformation.\n"
        prompt += "You can assume the following helper functions are already imported and available:\n"
        prompt += " - get_objects(grid, connectivity=4) -> returns list of {'color': int, 'coords': [[r,c],...]}\n"
        prompt += " - move_object(grid, obj, dr, dc) -> returns new grid\n"
        prompt += " - get_crop(grid) -> returns cropped grid\n\n"
        prompt += "Test Input to solve:\n"
        prompt += str(np.array(task.test_input))
        prompt += "\n\nProvide ONLY the Python code for `transform`."
        
        return prompt

    def _extract_code(self, text: str) -> str:
        """Extract code from markdown block."""
        import re
        match = re.search(r"```python\n(.*?)\n```", text, re.DOTALL)
        if match:
            return match.group(1)
        return text.strip()

    def _verify_program(self, code: str, task: ARCTask) -> bool:
        """Verify the code against all training examples."""
        try:
            for i, (inp, expected_out) in enumerate(zip(task.train_inputs, task.train_outputs)):
                actual_out = self._run_program(code, inp)
                if not np.array_equal(np.array(actual_out), np.array(expected_out)):
                    _rich_log(f"  - Example {i+1} failed verification.", "yellow")
                    return False
            return True
        except Exception as e:
            _rich_log(f"  - Verification error: {e}", "red")
            return False

    def _run_program(self, code: str, input_grid: List[List[Any]]) -> Any:
        """Execute the synthesized code in a safe-ish way."""
        # Use a shared dictionary for globals and locals to ensure functions can see each other
        exec_globals = {"np": np}
        
        # 1. Load DSL helpers into the scope
        exec(self.dsl_code, exec_globals)
        
        # 2. Load the synthesized 'transform' function
        exec(code, exec_globals)
        
        if "transform" in exec_globals:
            return exec_globals["transform"](np.array(input_grid))
        else:
            raise ValueError("Program did not define 'transform' function")

def _rich_log(message: str, style: str = "white", icon: str = ""):
    prefix = f"{icon} " if icon else ""
    print(f"[{style}]{prefix}{message}")
