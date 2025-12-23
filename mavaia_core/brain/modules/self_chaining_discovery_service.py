"""
Self-Chaining Discovery Service
Service for autonomously discovering reasoning structures
Converted from Swift SelfChainingDiscoveryService.swift
"""

from typing import Any, Dict, List, Optional
import json
import re
import logging
import uuid
from dataclasses import dataclass, field

from mavaia_core.brain.base_module import BaseBrainModule, ModuleMetadata
from mavaia_core.brain.registry import ModuleRegistry
from mavaia_core.exceptions import InvalidParameterError

# Optional imports - models package may not be available
try:
    from models.reasoning_models import ReasoningStructure, ReasoningModuleStep, ExecutionPlan, ExecutionStep, ReasoningMetadata
except ImportError:
    # Models not available - define minimal types
    ReasoningStructure = None
    ReasoningModuleStep = None
    ExecutionPlan = None
    ExecutionStep = None
    ReasoningMetadata = None

logger = logging.getLogger(__name__)


@dataclass
class _FallbackReasoningModuleStep:
    module_id: str
    module_name: str = ""
    parameters: Dict[str, Any] = field(default_factory=dict)
    dependencies: List[str] = field(default_factory=list)
    execution_type: str = "sequential"

    def to_dict(self) -> Dict[str, Any]:
        return {
            "module_id": self.module_id,
            "module_name": self.module_name,
            "parameters": dict(self.parameters),
            "dependencies": list(self.dependencies),
            "execution_type": self.execution_type,
        }


@dataclass
class _FallbackExecutionStep:
    step: int
    modules: List[str]
    type: str = "sequential"
    depends_on: Optional[int] = None

    def to_dict(self) -> Dict[str, Any]:
        return {
            "step": self.step,
            "modules": list(self.modules),
            "type": self.type,
            "depends_on": self.depends_on,
        }


@dataclass
class _FallbackExecutionPlan:
    steps: List[_FallbackExecutionStep]
    parallel_groups: List[List[str]] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "steps": [s.to_dict() for s in self.steps],
            "parallel_groups": [list(g) for g in self.parallel_groups],
        }


@dataclass
class _FallbackReasoningMetadata:
    discovered_at: float = 0.0
    confidence: float = 0.5
    reasoning_type: str = ""
    estimated_complexity: float = 0.5

    def to_dict(self) -> Dict[str, Any]:
        return {
            "discovered_at": self.discovered_at,
            "confidence": self.confidence,
            "reasoning_type": self.reasoning_type,
            "estimated_complexity": self.estimated_complexity,
        }


@dataclass
class _FallbackReasoningStructure:
    query: str
    modules: List[_FallbackReasoningModuleStep]
    execution_plan: _FallbackExecutionPlan
    metadata: _FallbackReasoningMetadata
    id: str = field(default_factory=lambda: f"rs_{uuid.uuid4().hex}")

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "query": self.query,
            "modules": [m.to_dict() for m in self.modules],
            "execution_plan": self.execution_plan.to_dict(),
            "metadata": self.metadata.to_dict(),
        }


_ReasoningStructure = ReasoningStructure or _FallbackReasoningStructure
_ReasoningModuleStep = ReasoningModuleStep or _FallbackReasoningModuleStep
_ExecutionPlan = ExecutionPlan or _FallbackExecutionPlan
_ExecutionStep = ExecutionStep or _FallbackExecutionStep
_ReasoningMetadata = ReasoningMetadata or _FallbackReasoningMetadata


class SelfChainingDiscoveryServiceModule(BaseBrainModule):
    """Service for autonomously discovering reasoning structures"""

    def __init__(self):
        super().__init__()
        self.module_registry = None
        self.cognitive_generator = None
        self._modules_loaded = False

    @property
    def metadata(self) -> ModuleMetadata:
        return ModuleMetadata(
            name="self_chaining_discovery_service",
            version="1.0.0",
            description="Service for autonomously discovering reasoning structures",
            operations=[
                "discover_reasoning_structure",
                "discover_chains",
                "build_chain_structure",
                "validate_structure",
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
            self.module_registry = ModuleRegistry.get_module("self_chaining_module_registry")
            self.cognitive_generator = ModuleRegistry.get_module("cognitive_generator")

            self._modules_loaded = True
        except Exception as e:
            logger.debug(
                "Error loading modules for self_chaining_discovery_service",
                exc_info=True,
                extra={"module_name": "self_chaining_discovery_service", "error_type": type(e).__name__},
            )

    def execute(self, operation: str, params: Dict[str, Any]) -> Dict[str, Any]:
        """Execute an operation"""
        self._ensure_modules_loaded()

        match operation:
            case "discover_reasoning_structure":
                return self._discover_reasoning_structure(params)
            case "discover_chains":
                return self._discover_chains(params)
            case "build_chain_structure":
                return self._build_chain_structure(params)
            case "validate_structure":
                return self._validate_structure(params)
            case _:
                raise InvalidParameterError(
                    parameter="operation",
                    value=operation,
                    reason="Unknown operation for self_chaining_discovery_service",
                )

    def _discover_reasoning_structure(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """Discover reasoning structure for a query"""
        query = params.get("query", "")
        context = params.get("context")
        if not isinstance(query, str) or not query.strip():
            raise InvalidParameterError("query", str(query), "query must be a non-empty string")
        if context is not None and not isinstance(context, str):
            raise InvalidParameterError("context", str(type(context).__name__), "context must be a string when provided")

        # Get available modules
        if self.module_registry:
            available_modules_result = self.module_registry.execute("get_all_modules", {})
            module_ids = available_modules_result.get("result", {}).get("module_ids", [])
        else:
            module_ids = []

        # Build discovery prompt
        discovery_prompt = self._build_discovery_prompt(query, context, module_ids)

        # Use cognitive generator for structure discovery
        if not self.cognitive_generator:
            return {"success": False, "error": "Cognitive generator not available"}

        try:
            response_result = self.cognitive_generator.execute(
                "generate_response",
                {
                    "input": discovery_prompt,
                    "context": "You are a reasoning structure discovery system. Return only valid JSON.",
                    "persona": "mavaia",
                },
            )
            raw_response = response_result.get("result", {}).get("response", "")
        except Exception as e:
            logger.debug(
                "Cognitive generator failed during structure discovery",
                exc_info=True,
                extra={"module_name": "self_chaining_discovery_service", "error_type": type(e).__name__},
            )
            return {"success": False, "error": "Structure discovery failed"}

        # Extract JSON from response
        json_data = self._extract_json(raw_response)
        if not json_data:
            return {"success": False, "error": "Invalid discovery response - no JSON found"}

        # Parse into structure
        structure = self._parse_reasoning_structure(json_data, query)

        # Validate structure
        validation_result = self._validate_structure_internal(structure)
        if not validation_result.get("is_valid", False):
            # Attempt refinement
            structure = self._refine_structure(structure, validation_result.get("issues", []))

        return {
            "success": True,
            "result": structure.to_dict() if hasattr(structure, "to_dict") else structure,
        }

    def _discover_chains(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """Discover multiple chains (alias for discover_reasoning_structure)"""
        return self._discover_reasoning_structure(params)

    def _build_chain_structure(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """Build chain structure from components"""
        modules_data = params.get("modules", [])
        execution_plan_data = params.get("execution_plan", {})
        metadata_data = params.get("metadata", {})
        query = params.get("query", "")
        if not isinstance(query, str) or not query.strip():
            raise InvalidParameterError("query", str(query), "query must be a non-empty string")
        if modules_data is None:
            modules_data = []
        if execution_plan_data is None:
            execution_plan_data = {}
        if metadata_data is None:
            metadata_data = {}
        if not isinstance(modules_data, list):
            raise InvalidParameterError("modules", str(type(modules_data).__name__), "modules must be a list")
        if not isinstance(execution_plan_data, dict):
            raise InvalidParameterError(
                "execution_plan", str(type(execution_plan_data).__name__), "execution_plan must be a dict"
            )
        if not isinstance(metadata_data, dict):
            raise InvalidParameterError("metadata", str(type(metadata_data).__name__), "metadata must be a dict")

        # Build structure from components
        modules = [
            _ReasoningModuleStep(
                module_id=m.get("module_id", ""),
                module_name=m.get("module_name", ""),
                parameters=m.get("parameters", {}),
                dependencies=m.get("dependencies", []),
                execution_type=m.get("execution_type", "sequential"),
            )
            for m in modules_data
        ]

        execution_plan = _ExecutionPlan(
            steps=[
                _ExecutionStep(
                    step=s.get("step", 0),
                    modules=s.get("modules", []),
                    type=s.get("type", "sequential"),
                    depends_on=s.get("depends_on"),
                )
                for s in execution_plan_data.get("steps", [])
            ],
            parallel_groups=execution_plan_data.get("parallel_groups", []),
        )

        metadata = _ReasoningMetadata(
            discovered_at=metadata_data.get("discovered_at", 0.0),
            confidence=metadata_data.get("confidence", 0.5),
            reasoning_type=metadata_data.get("reasoning_type", ""),
            estimated_complexity=metadata_data.get("estimated_complexity", 0.5),
        )

        structure = _ReasoningStructure(
            query=query,
            modules=modules,
            execution_plan=execution_plan,
            metadata=metadata,
        )

        return {
            "success": True,
            "result": structure.to_dict() if hasattr(structure, "to_dict") else {
                "id": structure.id,
                "query": structure.query,
                "modules": [{"module_id": m.module_id, "module_name": m.module_name} for m in structure.modules],
            },
        }

    def _validate_structure(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """Validate a reasoning structure"""
        structure_data = params.get("structure", {})
        if structure_data is None:
            structure_data = {}
        if not isinstance(structure_data, dict):
            raise InvalidParameterError("structure", str(type(structure_data).__name__), "structure must be a dict")
        
        # Reconstruct structure from dict
        structure = _ReasoningStructure(
            query=structure_data.get("query", ""),
            modules=[
                _ReasoningModuleStep(
                    module_id=m.get("module_id", ""),
                    module_name=m.get("module_name", ""),
                    parameters=m.get("parameters", {}),
                    dependencies=m.get("dependencies", []),
                    execution_type=m.get("execution_type", "sequential"),
                )
                for m in structure_data.get("modules", [])
            ],
            execution_plan=_ExecutionPlan(
                steps=[
                    _ExecutionStep(
                        step=s.get("step", 0),
                        modules=s.get("modules", []),
                        type=s.get("type", "sequential"),
                        depends_on=s.get("depends_on"),
                    )
                    for s in structure_data.get("execution_plan", {}).get("steps", [])
                ],
                parallel_groups=structure_data.get("execution_plan", {}).get("parallel_groups", []),
            ),
            metadata=_ReasoningMetadata(
                discovered_at=structure_data.get("metadata", {}).get("discovered_at", 0.0),
                confidence=structure_data.get("metadata", {}).get("confidence", 0.5),
                reasoning_type=structure_data.get("metadata", {}).get("reasoning_type", ""),
                estimated_complexity=structure_data.get("metadata", {}).get("estimated_complexity", 0.5),
            ),
        )

        return self._validate_structure_internal(structure)

    def _validate_structure_internal(self, structure: Any) -> Dict[str, Any]:
        """Internal validation logic"""
        issues = []

        # Check all module IDs exist
        if self.module_registry:
            module_ids = [getattr(m, "module_id", "") for m in getattr(structure, "modules", [])]
            validation_result = self.module_registry.execute(
                "validate_module_ids",
                {"module_ids": module_ids}
            )
            invalid_ids = validation_result.get("result", {}).get("invalid_ids", [])
            if invalid_ids:
                issues.append(f"Invalid module IDs: {', '.join(invalid_ids)}")

        # Check dependencies
        for module in getattr(structure, "modules", []):
            if self.module_registry:
                dep_result = self.module_registry.execute(
                    "validate_dependencies",
                    {"module_id": getattr(module, "module_id", "")}
                )
                if not dep_result.get("result", {}).get("satisfied", True):
                    missing = dep_result.get("result", {}).get("missing", [])
                    issues.append(
                        f"Module '{getattr(module, 'module_id', '')}' has missing dependencies: {', '.join(missing)}"
                    )

        # Validate execution plan
        plan_issues = self._validate_execution_plan(
            getattr(structure, "execution_plan", None),
            [getattr(m, "module_id", "") for m in getattr(structure, "modules", [])],
        )
        issues.extend(plan_issues)

        return {
            "is_valid": len(issues) == 0,
            "issues": issues,
        }

    def _validate_execution_plan(self, plan: Any, module_ids: List[str]) -> List[str]:
        """Validate execution plan"""
        issues = []
        if plan is None:
            issues.append("Execution plan is missing")
            return issues

        # Check all modules in steps exist
        for step in getattr(plan, "steps", []):
            for module_id in getattr(step, "modules", []):
                if module_id not in module_ids:
                    issues.append(f"Step {getattr(step, 'step', '?')} references unknown module: {module_id}")

        # Check parallel groups
        for group in getattr(plan, "parallel_groups", []):
            for module_id in group:
                if module_id not in module_ids:
                    issues.append(f"Parallel group references unknown module: {module_id}")

        return issues

    def _extract_json(self, text: str) -> Optional[Dict]:
        """Extract JSON from text response"""
        # Try to find JSON in markdown code blocks
        json_pattern = r"```json\s*(\{.*?\})\s*```"
        match = re.search(json_pattern, text, re.DOTALL)
        if match:
            try:
                return json.loads(match.group(1))
            except json.JSONDecodeError:
                pass

        # Try to find JSON object directly
        start_idx = text.find("{")
        if start_idx != -1:
            end_idx = text.rfind("}")
            if end_idx != -1 and end_idx > start_idx:
                try:
                    return json.loads(text[start_idx:end_idx + 1])
                except json.JSONDecodeError:
                    pass

        return None

    def _parse_reasoning_structure(self, json_data: Dict, query: str) -> Any:
        """Parse reasoning structure from JSON"""
        modules_data = json_data.get("modules", [])
        execution_plan_data = json_data.get("execution_plan", {})
        metadata_data = json_data.get("metadata", {})

        modules = [
            _ReasoningModuleStep(
                module_id=m.get("moduleId", m.get("module_id", "")),
                module_name=m.get("moduleName", m.get("module_name", "")),
                parameters=m.get("parameters", {}),
                dependencies=m.get("dependencies", []),
                execution_type=m.get("executionType", m.get("execution_type", "sequential")),
            )
            for m in modules_data
        ]

        execution_steps = [
            _ExecutionStep(
                step=s.get("step", 0),
                modules=s.get("modules", []),
                type=s.get("type", "sequential"),
                depends_on=s.get("dependsOn", s.get("depends_on")),
            )
            for s in execution_plan_data.get("steps", [])
        ]

        execution_plan = _ExecutionPlan(
            steps=execution_steps,
            parallel_groups=execution_plan_data.get("parallelGroups", execution_plan_data.get("parallel_groups", [])),
        )

        metadata = _ReasoningMetadata(
            discovered_at=metadata_data.get("discoveredAt", 0.0),
            confidence=metadata_data.get("confidence", 0.5),
            reasoning_type=metadata_data.get("reasoningType", metadata_data.get("reasoning_type", "")),
            estimated_complexity=metadata_data.get("estimatedComplexity", metadata_data.get("estimated_complexity", 0.5)),
        )

        return _ReasoningStructure(
            query=query,
            modules=modules,
            execution_plan=execution_plan,
            metadata=metadata,
        )

    def _refine_structure(self, structure: Any, issues: List[str]) -> Any:
        """
        Best-effort deterministic refinement of a structure based on validation issues.

        This is intentionally conservative: remove invalid module references from the execution plan
        and drop modules that are explicitly reported as invalid by the module registry.
        """
        if not issues:
            return structure

        modules = list(getattr(structure, "modules", []) or [])
        execution_plan = getattr(structure, "execution_plan", None)

        invalid_ids: set[str] = set()
        for issue in issues:
            if issue.lower().startswith("invalid module ids:"):
                ids = issue.split(":", 1)[-1]
                for part in ids.split(","):
                    mid = part.strip()
                    if mid:
                        invalid_ids.add(mid)

        if invalid_ids:
            modules = [m for m in modules if getattr(m, "module_id", "") not in invalid_ids]

        valid_ids = {getattr(m, "module_id", "") for m in modules if getattr(m, "module_id", "")}
        if execution_plan is not None and valid_ids:
            # Filter plan steps/groups down to valid module IDs, without assuming mutability.
            new_steps = []
            for step in getattr(execution_plan, "steps", []) or []:
                step_modules = [mid for mid in getattr(step, "modules", []) or [] if mid in valid_ids]
                new_steps.append(
                    _ExecutionStep(
                        step=int(getattr(step, "step", 0) or 0),
                        modules=step_modules,
                        type=str(getattr(step, "type", "sequential") or "sequential"),
                        depends_on=getattr(step, "depends_on", None),
                    )
                )
            new_parallel_groups = [
                [mid for mid in group if mid in valid_ids]
                for group in getattr(execution_plan, "parallel_groups", []) or []
            ]
            execution_plan = _ExecutionPlan(steps=new_steps, parallel_groups=new_parallel_groups)

        # Rebuild structure if it's a fallback dataclass; otherwise return original with minimal mutations.
        if isinstance(structure, _FallbackReasoningStructure):
            return _FallbackReasoningStructure(
                id=structure.id,
                query=structure.query,
                modules=modules,
                execution_plan=execution_plan,
                metadata=structure.metadata,
            )
        return structure

    def _build_discovery_prompt(self, query: str, context: Optional[str], module_ids: List[str]) -> str:
        """Build discovery prompt"""
        prompt = f"""Discover a reasoning structure for the following query:

Query: {query}
"""
        if context:
            prompt += f"\nContext: {context}\n"

        prompt += f"\nAvailable modules: {', '.join(module_ids)}\n"
        prompt += "\nReturn a JSON structure with modules, execution plan, and metadata."

        return prompt

