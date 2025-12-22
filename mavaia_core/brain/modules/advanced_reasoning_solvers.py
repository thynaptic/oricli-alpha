"""
Advanced Reasoning Solvers Module
Specialized solvers for complex reasoning puzzles: zebra puzzles, spatial reasoning, ARC, web of lies
"""

from typing import Dict, Any, Optional
import sys
from mavaia_core.brain.base_module import BaseBrainModule, ModuleMetadata


class AdvancedReasoningSolversModule(BaseBrainModule):
    """Advanced solvers for complex reasoning puzzles"""
    
    def __init__(self):
        """Initialize the module"""
        self._module_registry = None
        self._symbolic_solver_module = None
        self._meta_evaluator = None
        self._solver_modules = {}
    
    @property
    def metadata(self) -> ModuleMetadata:
        """Return module metadata"""
        return ModuleMetadata(
            name="advanced_reasoning_solvers",
            version="1.0.0",
            description="Advanced solvers for complex reasoning puzzles: zebra puzzles, spatial reasoning, ARC, web of lies",
            operations=[
                "solve_zebra_puzzle",
                "solve_spatial_problem",
                "solve_arc_problem",
                "solve_web_of_lies",
                "parse_puzzle_constraints",
            ],
            dependencies=[],
            model_required=False,
        )
    
    def initialize(self) -> bool:
        """Initialize the module"""
        self._init_module_registry()
        return True
    
    def _init_module_registry(self):
        """Lazy initialization of module registry"""
        if self._module_registry is None:
            try:
                from mavaia_core.brain.registry import ModuleRegistry
                self._module_registry = ModuleRegistry
            except ImportError:
                print("[AdvancedReasoningSolversModule] ModuleRegistry not available", file=sys.stderr)
                self._module_registry = None
    
    def _get_symbolic_solver_module(self):
        """Get the symbolic solver module (lazy load)"""
        if self._symbolic_solver_module is None:
            self._init_module_registry()
            if self._module_registry:
                try:
                    self._symbolic_solver_module = self._module_registry.get_module("symbolic_solver")
                    if self._symbolic_solver_module:
                        if not hasattr(self._symbolic_solver_module, 'initialized'):
                            try:
                                self._symbolic_solver_module.initialize()
                            except Exception:
                                pass
                        elif not self._symbolic_solver_module.initialized:
                            try:
                                self._symbolic_solver_module.initialize()
                            except Exception:
                                pass
                except Exception as e:
                    print(f"[AdvancedReasoningSolversModule] Failed to load symbolic_solver module: {e}", file=sys.stderr)
        return self._symbolic_solver_module
    
    def _get_meta_evaluator(self):
        """Get the meta_evaluator module (lazy load)"""
        if self._meta_evaluator is None:
            self._init_module_registry()
            if self._module_registry:
                try:
                    self._meta_evaluator = self._module_registry.get_module("meta_evaluator")
                except Exception:
                    pass
        return self._meta_evaluator
    
    def execute(self, operation: str, params: Dict[str, Any]) -> Dict[str, Any]:
        """Execute a solver operation - routes to specialized solver modules"""
        try:
            self._init_module_registry()
            
            # Route to specialized solver modules
            if operation == "solve_zebra_puzzle":
                zebra_solver = self._get_solver_module("zebra_puzzle_solver")
                if zebra_solver:
                    return zebra_solver.execute(operation, params)
                else:
                    return {"success": False, "error": "Zebra puzzle solver module not available"}
            
            elif operation == "solve_spatial_problem":
                spatial_solver = self._get_solver_module("spatial_reasoning_solver")
                if spatial_solver:
                    return spatial_solver.execute(operation, params)
                else:
                    return {"success": False, "error": "Spatial reasoning solver module not available"}
            
            elif operation == "solve_arc_problem":
                arc_solver = self._get_solver_module("arc_solver")
                if arc_solver:
                    return arc_solver.execute(operation, params)
                else:
                    return {"success": False, "error": "ARC solver module not available"}
            
            elif operation == "solve_web_of_lies":
                web_solver = self._get_solver_module("web_of_lies_solver")
                if web_solver:
                    return web_solver.execute(operation, params)
                else:
                    return {"success": False, "error": "Web of lies solver module not available"}
            
            elif operation == "parse_puzzle_constraints":
                # This can be handled by zebra puzzle solver
                zebra_solver = self._get_solver_module("zebra_puzzle_solver")
                if zebra_solver:
                    return zebra_solver.execute(operation, params)
                else:
                    return {"success": False, "error": "Zebra puzzle solver module not available"}
            
            else:
                return {"success": False, "error": f"Unknown operation: {operation}"}
        except Exception as e:
            return {"success": False, "error": str(e)}
    
    def _get_solver_module(self, module_name: str):
        """Get a specialized solver module (lazy load)"""
        if not hasattr(self, '_solver_modules'):
            self._solver_modules = {}
        
        if module_name not in self._solver_modules:
            self._init_module_registry()
            if self._module_registry:
                try:
                    module = self._module_registry.get_module(module_name)
                    if module:
                        if not hasattr(module, 'initialized') or not module.initialized:
                            try:
                                module.initialize()
                            except Exception:
                                pass
                        self._solver_modules[module_name] = module
                except Exception as e:
                    print(f"[AdvancedReasoningSolversModule] Failed to load {module_name}: {e}", file=sys.stderr)
                    self._solver_modules[module_name] = None
        
        return self._solver_modules.get(module_name)

    # Note: Solver methods have been moved to specialized modules:
    # - zebra_puzzle_solver.py: _solve_zebra_puzzle, _parse_puzzle_constraints, etc.
    # - spatial_reasoning_solver.py: _solve_spatial_problem, _create_spatial_relation_graph
    # - arc_solver.py: _solve_arc_problem, _solve_arc_task, etc.
    # - web_of_lies_solver.py: _solve_web_of_lies
    # This module now acts as a coordinator/router to the specialized modules.
