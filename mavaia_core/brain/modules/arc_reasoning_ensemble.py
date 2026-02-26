from __future__ import annotations
"""ARC reasoning ensemble.

Provides ARC grid analysis by delegating to the existing ARC logic inside
`advanced_reasoning_solvers`.
"""

from typing import Any, Dict
import sys

from mavaia_core.brain.base_module import BaseBrainModule, ModuleMetadata
from mavaia_core.exceptions import InvalidParameterError


class ArcReasoningEnsembleModule(BaseBrainModule):
    """ARC reasoning ensemble with transformation detection and grid analysis."""

    def __init__(self):
        self._module_registry = None

    @property
    def metadata(self) -> ModuleMetadata:
        return ModuleMetadata(
            name="arc_reasoning_ensemble",
            version="1.0.0",
            description="ARC reasoning ensemble with transformation detection and grid analysis",
            operations=[
                "detect_arc_transformations",
                "analyze_colors",
                "analyze_geometry",
                "infer_fill_rules",
                "infer_extension_rules",
                "infer_repetition_rules",
            ],
            dependencies=[],
            model_required=False,
        )

    def initialize(self) -> bool:
        self._init_module_registry()
        return True

    def _init_module_registry(self) -> None:
        if self._module_registry is None:
            try:
                from mavaia_core.brain.registry import ModuleRegistry

                self._module_registry = ModuleRegistry
            except ImportError:
                print("[ArcReasoningEnsembleModule] ModuleRegistry not available", file=sys.stderr)
                self._module_registry = None

    def _get_solver(self):
        self._init_module_registry()
        if not self._module_registry:
            return None
        # Prefer advanced_reasoning_solvers; it contains the core ARC utilities.
        solver = self._module_registry.get_module("advanced_reasoning_solvers")
        if solver:
            return solver
        return self._module_registry.get_module("spatial_reasoning_solver")

    def execute(self, operation: str, params: Dict[str, Any]) -> Dict[str, Any]:
        solver = self._get_solver()
        if not solver:
            return {"success": False, "error": "ARC solver module unavailable"}

        # Grids can be provided under multiple keys.
        input_grid = params.get("input_grid") or params.get("grid")
        output_grid = params.get("output_grid")

        if operation == "detect_arc_transformations":
            if input_grid is None or output_grid is None:
                return {"success": False, "error": "input_grid and output_grid are required"}
            return {
                "success": True,
                "transformations": solver._detect_arc_transformations(input_grid, output_grid),
            }

        if operation == "analyze_colors":
            if input_grid is None:
                return {"success": False, "error": "grid (or input_grid) is required"}
            return {"success": True, "colors": solver._analyze_colors(input_grid)}

        if operation == "analyze_geometry":
            if input_grid is None:
                return {"success": False, "error": "grid (or input_grid) is required"}
            return {"success": True, "geometry": solver._analyze_geometry(input_grid)}

        if operation == "infer_fill_rules":
            if input_grid is None or output_grid is None:
                return {"success": False, "error": "input_grid and output_grid are required"}
            return {"success": True, "fill_rules": solver._infer_fill_rules(input_grid, output_grid)}

        if operation == "infer_extension_rules":
            if input_grid is None or output_grid is None:
                return {"success": False, "error": "input_grid and output_grid are required"}
            return {
                "success": True,
                "extension_rules": solver._infer_extension_rules(input_grid, output_grid),
            }

        if operation == "infer_repetition_rules":
            if input_grid is None or output_grid is None:
                return {"success": False, "error": "input_grid and output_grid are required"}
            return {
                "success": True,
                "repetition_rules": solver._infer_repetition_rules(input_grid, output_grid),
            }

        raise InvalidParameterError(
            parameter="operation",
            value=str(operation),
            reason="Unknown operation for arc_reasoning_ensemble",
        )
