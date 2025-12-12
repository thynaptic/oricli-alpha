"""
Self-Chaining Discovery Service
Service for autonomously discovering reasoning structures
Converted from Swift SelfChainingDiscoveryService.swift
"""

from typing import Any, Dict, List, Optional
import sys
import json
import re
from pathlib import Path

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent))

from mavaia_core.brain.base_module import BaseBrainModule, ModuleMetadata

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


class SelfChainingDiscoveryServiceModule(BaseBrainModule):
    """Service for autonomously discovering reasoning structures"""

    def __init__(self):
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
            from module_registry import ModuleRegistry

            self.module_registry = ModuleRegistry.get_module("self_chaining_module_registry")
            self.cognitive_generator = ModuleRegistry.get_module("cognitive_generator")

            self._modules_loaded = True
        except Exception as e:
            print(f"Error loading modules: {e}")

    def execute(self, operation: str, params: Dict[str, Any]) -> Dict[str, Any]:
        """Execute an operation"""
        self._ensure_modules_loaded()

        if operation == "discover_reasoning_structure":
            return self._discover_reasoning_structure(params)
        elif operation == "discover_chains":
            return self._discover_chains(params)
        elif operation == "build_chain_structure":
            return self._build_chain_structure(params)
        elif operation == "validate_structure":
            return self._validate_structure(params)
        else:
            raise ValueError(f"Unknown operation: {operation}")

    def _discover_reasoning_structure(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """Discover reasoning structure for a query"""
        query = params.get("query", "")
        context = params.get("context")

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
            raise ValueError("Cognitive generator not available")

        response_result = self.cognitive_generator.execute(
            "generate_response",
            {
                "input": discovery_prompt,
                "context": "You are a reasoning structure discovery system. Return only valid JSON.",
                "persona": "mavaia",
            }
        )

        raw_response = response_result.get("result", {}).get("response", "")

        # Extract JSON from response
        json_data = self._extract_json(raw_response)
        if not json_data:
            raise ValueError("Invalid discovery response - no JSON found")

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

        # Build structure from components
        modules = [
            ReasoningModuleStep(
                module_id=m.get("module_id", ""),
                module_name=m.get("module_name", ""),
                parameters=m.get("parameters", {}),
                dependencies=m.get("dependencies", []),
                execution_type=m.get("execution_type", "sequential"),
            )
            for m in modules_data
        ]

        execution_plan = ExecutionPlan(
            steps=[
                ExecutionStep(
                    step=s.get("step", 0),
                    modules=s.get("modules", []),
                    type=s.get("type", "sequential"),
                    depends_on=s.get("depends_on"),
                )
                for s in execution_plan_data.get("steps", [])
            ],
            parallel_groups=execution_plan_data.get("parallel_groups", []),
        )

        metadata = ReasoningMetadata(
            discovered_at=metadata_data.get("discovered_at", 0.0),
            confidence=metadata_data.get("confidence", 0.5),
            reasoning_type=metadata_data.get("reasoning_type", ""),
            estimated_complexity=metadata_data.get("estimated_complexity", 0.5),
        )

        structure = ReasoningStructure(
            query=params.get("query", ""),
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
        
        # Reconstruct structure from dict
        structure = ReasoningStructure(
            query=structure_data.get("query", ""),
            modules=[
                ReasoningModuleStep(
                    module_id=m.get("module_id", ""),
                    module_name=m.get("module_name", ""),
                    parameters=m.get("parameters", {}),
                    dependencies=m.get("dependencies", []),
                    execution_type=m.get("execution_type", "sequential"),
                )
                for m in structure_data.get("modules", [])
            ],
            execution_plan=ExecutionPlan(
                steps=[
                    ExecutionStep(
                        step=s.get("step", 0),
                        modules=s.get("modules", []),
                        type=s.get("type", "sequential"),
                        depends_on=s.get("depends_on"),
                    )
                    for s in structure_data.get("execution_plan", {}).get("steps", [])
                ],
                parallel_groups=structure_data.get("execution_plan", {}).get("parallel_groups", []),
            ),
            metadata=ReasoningMetadata(
                discovered_at=structure_data.get("metadata", {}).get("discovered_at", 0.0),
                confidence=structure_data.get("metadata", {}).get("confidence", 0.5),
                reasoning_type=structure_data.get("metadata", {}).get("reasoning_type", ""),
                estimated_complexity=structure_data.get("metadata", {}).get("estimated_complexity", 0.5),
            ),
        )

        return self._validate_structure_internal(structure)

    def _validate_structure_internal(self, structure: ReasoningStructure) -> Dict[str, Any]:
        """Internal validation logic"""
        issues = []

        # Check all module IDs exist
        if self.module_registry:
            module_ids = [m.module_id for m in structure.modules]
            validation_result = self.module_registry.execute(
                "validate_module_ids",
                {"module_ids": module_ids}
            )
            invalid_ids = validation_result.get("result", {}).get("invalid_ids", [])
            if invalid_ids:
                issues.append(f"Invalid module IDs: {', '.join(invalid_ids)}")

        # Check dependencies
        for module in structure.modules:
            if self.module_registry:
                dep_result = self.module_registry.execute(
                    "validate_dependencies",
                    {"module_id": module.module_id}
                )
                if not dep_result.get("result", {}).get("satisfied", True):
                    missing = dep_result.get("result", {}).get("missing", [])
                    issues.append(f"Module '{module.module_id}' has missing dependencies: {', '.join(missing)}")

        # Validate execution plan
        plan_issues = self._validate_execution_plan(structure.execution_plan, [m.module_id for m in structure.modules])
        issues.extend(plan_issues)

        return {
            "is_valid": len(issues) == 0,
            "issues": issues,
        }

    def _validate_execution_plan(self, plan: ExecutionPlan, module_ids: List[str]) -> List[str]:
        """Validate execution plan"""
        issues = []

        # Check all modules in steps exist
        for step in plan.steps:
            for module_id in step.modules:
                if module_id not in module_ids:
                    issues.append(f"Step {step.step} references unknown module: {module_id}")

        # Check parallel groups
        for group in plan.parallel_groups:
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

    def _parse_reasoning_structure(self, json_data: Dict, query: str) -> ReasoningStructure:
        """Parse reasoning structure from JSON"""
        modules_data = json_data.get("modules", [])
        execution_plan_data = json_data.get("execution_plan", {})
        metadata_data = json_data.get("metadata", {})

        modules = [
            ReasoningModuleStep(
                module_id=m.get("moduleId", m.get("module_id", "")),
                module_name=m.get("moduleName", m.get("module_name", "")),
                parameters=m.get("parameters", {}),
                dependencies=m.get("dependencies", []),
                execution_type=m.get("executionType", m.get("execution_type", "sequential")),
            )
            for m in modules_data
        ]

        execution_steps = [
            ExecutionStep(
                step=s.get("step", 0),
                modules=s.get("modules", []),
                type=s.get("type", "sequential"),
                depends_on=s.get("dependsOn", s.get("depends_on")),
            )
            for s in execution_plan_data.get("steps", [])
        ]

        execution_plan = ExecutionPlan(
            steps=execution_steps,
            parallel_groups=execution_plan_data.get("parallelGroups", execution_plan_data.get("parallel_groups", [])),
        )

        metadata = ReasoningMetadata(
            discovered_at=metadata_data.get("discoveredAt", 0.0),
            confidence=metadata_data.get("confidence", 0.5),
            reasoning_type=metadata_data.get("reasoningType", metadata_data.get("reasoning_type", "")),
            estimated_complexity=metadata_data.get("estimatedComplexity", metadata_data.get("estimated_complexity", 0.5)),
        )

        return ReasoningStructure(
            query=query,
            modules=modules,
            execution_plan=execution_plan,
            metadata=metadata,
        )

    def _refine_structure(self, structure: ReasoningStructure, issues: List[str]) -> ReasoningStructure:
        """Refine structure based on validation issues"""
        # For now, return structure as-is
        # Full refinement would require cognitive generator call
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

