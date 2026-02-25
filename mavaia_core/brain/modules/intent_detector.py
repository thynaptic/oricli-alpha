from __future__ import annotations
"""
Intent Detector Module
Detects user intent from input text for cognitive routing
"""

from typing import Dict, Any, Optional
import sys
from pathlib import Path
from mavaia_core.brain.base_module import BaseBrainModule, ModuleMetadata


class IntentDetectorModule(BaseBrainModule):
    """Detects user intent from input text"""
    
    def __init__(self):
        """Initialize the module"""
        self._module_registry = None
    
    @property
    def metadata(self) -> ModuleMetadata:
        """Return module metadata"""
        return ModuleMetadata(
            name="intent_detector",
            version="1.0.0",
            description="Detects user intent from input text for cognitive routing",
            operations=["detect_intent", "categorize_intent"],
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
                print("[IntentDetectorModule] ModuleRegistry not available", file=sys.stderr)
                self._module_registry = None
    
    def execute(self, operation: str, params: Dict[str, Any]) -> Dict[str, Any]:
        """Execute an intent detection operation"""
        try:
            if operation == "detect_intent":
                input_text = params.get("input_text") or params.get("text") or params.get("query", "")
                context = params.get("context", "")
                return self._detect_intent(input_text, context)
            elif operation == "categorize_intent":
                input_text = params.get("input_text") or params.get("text") or params.get("query", "")
                input_lower = params.get("input_lower")
                return self._categorize_intent(input_text, input_lower)
            else:
                return {"success": False, "error": f"Unknown operation: {operation}"}
        except Exception as e:
            return {"success": False, "error": str(e)}
    
    # Intent detection methods will be extracted here
