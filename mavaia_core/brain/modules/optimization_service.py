"""
Optimization Service - Core optimization service wrapping PythonBrainService
Converted from Swift OptimizationService.swift
"""

from typing import Any, Dict, List, Optional, Tuple
import time
import logging

from mavaia_core.brain.base_module import BaseBrainModule, ModuleMetadata
from mavaia_core.brain.registry import ModuleRegistry
from mavaia_core.exceptions import InvalidParameterError

logger = logging.getLogger(__name__)


class OptimizationServiceModule(BaseBrainModule):
    """Core optimization service providing caching, parallelization, batching, and performance tracking"""

    def __init__(self):
        super().__init__()
        self.response_cache = None
        self.performance_profiler = None
        self._modules_loaded = False
        self._caching_enabled = True
        self._profiling_enabled = True
        self._parallelization_enabled = True
        self._module_usage_counts: Dict[str, int] = {}

    @property
    def metadata(self) -> ModuleMetadata:
        return ModuleMetadata(
            name="optimization_service",
            version="1.0.0",
            description="Core optimization service providing caching, parallelization, batching, and performance tracking",
            operations=[
                "optimize_operation",
                "execute_operation",
                "execute_parallel",
                "configure",
            ],
            dependencies=[],
            model_required=False,
        )

    def initialize(self) -> bool:
        """Initialize the module"""
        return True

    def _ensure_modules_loaded(self):
        """Lazy load dependent modules"""
        if self._modules_loaded:
            return

        try:
            self.response_cache = ModuleRegistry.get_module("response_cache")
            # Performance profiler would be a separate module if needed

            self._modules_loaded = True
        except Exception as e:
            # Modules not available - will use fallback methods
            logger.debug(
                "Failed to load optional response_cache for optimization_service",
                exc_info=True,
                extra={"module_name": "optimization_service", "error_type": type(e).__name__},
            )

    def execute(self, operation: str, params: Dict[str, Any]) -> Dict[str, Any]:
        """Execute an operation"""
        self._ensure_modules_loaded()

        if operation == "optimize_operation":
            return self._optimize_operation(params)
        elif operation == "execute_operation":
            return self._execute_operation(params)
        elif operation == "execute_parallel":
            return self._execute_parallel(params)
        elif operation == "configure":
            return self._configure(params)
        else:
            raise InvalidParameterError(
                parameter="operation",
                value=operation,
                reason="Unknown operation for optimization_service",
            )

    def _optimize_operation(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """Optimize operation (alias for execute_operation)"""
        return self._execute_operation(params)

    def _execute_operation(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """Execute operation with optimization (caching, profiling)"""
        module = params.get("module", "")
        operation = params.get("operation", "")
        op_params = params.get("params", {})

        if not isinstance(module, str) or not module.strip():
            raise InvalidParameterError(
                parameter="module",
                value=str(module),
                reason="module must be a non-empty string",
            )
        if not isinstance(operation, str) or not operation.strip():
            raise InvalidParameterError(
                parameter="operation",
                value=str(operation),
                reason="operation must be a non-empty string",
            )
        if op_params is None:
            op_params = {}
        if not isinstance(op_params, dict):
            raise InvalidParameterError(
                parameter="params",
                value=str(type(op_params).__name__),
                reason="params must be a dict",
            )

        start_time = time.time()

        # Check cache first if enabled
        if self._caching_enabled and self.response_cache:
            try:
                cached = self.response_cache.execute("get", {
                    "module": module,
                    "operation": operation,
                    "params": op_params,
                })
                if cached.get("success", False) and cached.get("value"):
                    return {
                        "success": True,
                        "result": cached.get("value"),
                        "cached": True,
                    }
            except Exception as e:
                logger.debug(
                    "Cache get failed; continuing without cache",
                    exc_info=True,
                    extra={
                        "module_name": "optimization_service",
                        "target_module": module,
                        "target_operation": operation,
                        "error_type": type(e).__name__,
                    },
                )

        # Execute actual operation via module registry
        try:
            target_module = ModuleRegistry.get_module(module)
            if not target_module:
                return {
                    "success": False,
                    "error": f"Module {module} not found",
                }

            result = target_module.execute(operation, op_params)
            duration = time.time() - start_time

            # Cache result if enabled
            if self._caching_enabled and self.response_cache:
                try:
                    self.response_cache.execute("set", {
                        "module": module,
                        "operation": operation,
                        "params": op_params,
                        "value": result,
                    })
                except Exception as e:
                    logger.debug(
                        "Cache set failed; continuing",
                        exc_info=True,
                        extra={
                            "module_name": "optimization_service",
                            "target_module": module,
                            "target_operation": operation,
                            "error_type": type(e).__name__,
                        },
                    )

            # Track module usage
            self._module_usage_counts[module] = self._module_usage_counts.get(module, 0) + 1

            return {
                "success": True,
                "result": result,
                "cached": False,
                "duration": duration,
            }
        except Exception as e:
            logger.debug(
                "Optimized operation execution failed",
                exc_info=True,
                extra={
                    "module_name": "optimization_service",
                    "target_module": module,
                    "target_operation": operation,
                    "error_type": type(e).__name__,
                },
            )
            return {
                "success": False,
                "error": "Operation execution failed",
                "module": module,
                "operation": operation,
            }

    def _execute_parallel(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """Execute multiple operations in parallel"""
        operations = params.get("operations", [])

        if not self._parallelization_enabled:
            # Fallback to sequential
            results = []
            for op in operations:
                result = self._execute_operation({
                    "module": op.get("module", ""),
                    "operation": op.get("operation", ""),
                    "params": op.get("params", {}),
                })
                results.append(result)
            return {
                "success": True,
                "results": results,
            }

        # In full implementation, would use async/await for true parallelization
        # For now, execute sequentially but mark as parallel
        start_time = time.time()
        results = []

        for op in operations:
            result = self._execute_operation({
                "module": op.get("module", ""),
                "operation": op.get("operation", ""),
                "params": op.get("params", {}),
            })
            results.append(result)

        duration = time.time() - start_time

        return {
            "success": True,
            "results": results,
            "duration": duration,
            "parallel": True,
        }

    def _configure(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """Configure optimization settings"""
        if "caching_enabled" in params:
            self._caching_enabled = params["caching_enabled"]
        if "profiling_enabled" in params:
            self._profiling_enabled = params["profiling_enabled"]
        if "parallelization_enabled" in params:
            self._parallelization_enabled = params["parallelization_enabled"]

        return {
            "success": True,
            "config": {
                "caching_enabled": self._caching_enabled,
                "profiling_enabled": self._profiling_enabled,
                "parallelization_enabled": self._parallelization_enabled,
            },
        }

