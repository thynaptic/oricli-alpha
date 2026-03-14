from __future__ import annotations
"""
Regulatory Compliance Auditor Module
A strict, rules-based engine that evaluates proposed plans against 
specific compliance frameworks (GDPR, HIPAA, SOC2).
"""

import json
import logging
import re
from pathlib import Path
from typing import Dict, Any, List, Optional

from oricli_core.brain.base_module import BaseBrainModule, ModuleMetadata
from oricli_core.exceptions import (
    InvalidParameterError,
    ModuleInitializationError,
)

logger = logging.getLogger(__name__)

class RegulatoryComplianceAuditor(BaseBrainModule):
    """
    Strict compliance engine for Oricli-Alpha.
    Evaluates execution plans against defined regulatory frameworks.
    """

    def __init__(self):
        super().__init__()
        self._rules_path = Path(__file__).resolve().parent.parent.parent / "data" / "compliance_rules.json"
        self._frameworks = {}
        self._initialized = False

    @property
    def metadata(self) -> ModuleMetadata:
        return ModuleMetadata(
            name="regulatory_compliance_auditor",
            version="1.0.0",
            description="Strict rules-based engine for GDPR, HIPAA, and SOC2 compliance auditing",
            operations=[
                "audit_plan",
                "check_compliance",
                "get_active_frameworks"
            ],
            dependencies=[],
            enabled=True,
            model_required=False,
        )

    def initialize(self) -> bool:
        """Load compliance rules from JSON configuration."""
        try:
            if not self._rules_path.exists():
                logger.warning(f"Compliance rules file not found at {self._rules_path}")
                return False

            with open(self._rules_path, "r", encoding="utf-8") as f:
                data = json.load(f)
                self._frameworks = data.get("compliance_frameworks", {})
            
            self._initialized = True
            logger.info(f"Loaded compliance rules for frameworks: {list(self._frameworks.keys())}")
            return True
        except Exception as e:
            logger.error(f"Failed to initialize RegulatoryComplianceAuditor: {e}")
            return False

    def execute(self, operation: str, params: Dict[str, Any]) -> Dict[str, Any]:
        if not self._initialized:
            if not self.initialize():
                raise ModuleInitializationError("RegulatoryComplianceAuditor failed to initialize rules.")

        if operation == "audit_plan":
            return self._audit_plan(params)
        elif operation == "check_compliance":
            return self._check_compliance(params)
        elif operation == "get_active_frameworks":
            return {
                "success": True, 
                "frameworks": list(self._frameworks.keys())
            }
        else:
            raise InvalidParameterError(parameter="operation", value=operation, reason="Unsupported operation")

    def _audit_plan(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """
        Audit a full execution plan (DAG or step list) against active frameworks.
        
        Args:
            plan (List[str] | Dict): The plan to audit. Can be a list of steps or a structured dict.
            frameworks (List[str], optional): Specific frameworks to check (defaults to all).
        
        Returns:
            Dict with success, compliant (bool), and violations (list).
        """
        plan_input = params.get("plan")
        target_frameworks = params.get("frameworks", list(self._frameworks.keys()))

        if not plan_input:
            return {"success": False, "error": "No plan provided for auditing"}

        # Normalize plan to a list of strings for regex checking
        steps = []
        if isinstance(plan_input, list):
            steps = [str(s) for s in plan_input]
        elif isinstance(plan_input, dict):
            # Extract steps/nodes/description from a structured plan
            if "steps" in plan_input:
                steps = [str(s) for s in plan_input["steps"]]
            elif "nodes" in plan_input:
                steps = [str(n.get("description", "") + " " + str(n.get("params", ""))) for n in plan_input["nodes"]]
            else:
                steps = [str(plan_input)] # Fallback
        else:
            steps = [str(plan_input)]

        violations = []
        compliant = True

        for step_idx, step_desc in enumerate(steps):
            # Get next step for look-ahead context (heuristic: mitigation often in next step)
            next_step_desc = steps[step_idx + 1] if step_idx + 1 < len(steps) else ""
            
            step_violations = self._check_step(step_desc, target_frameworks, next_step_context=next_step_desc)
            
            if step_violations:
                compliant = False
                for v in step_violations:
                    v["step_index"] = step_idx
                    v["step_content"] = step_desc
                    violations.append(v)

        return {
            "success": True,
            "compliant": compliant,
            "violation_count": len(violations),
            "violations": violations,
            "audited_frameworks": target_frameworks
        }

    def _check_compliance(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """
        Check a single action or text snippet for compliance.
        """
        text = params.get("text") or params.get("action", "")
        frameworks = params.get("frameworks", list(self._frameworks.keys()))
        
        violations = self._check_step(text, frameworks)
        
        return {
            "success": True,
            "compliant": len(violations) == 0,
            "violations": violations
        }

    def _check_step(self, text: str, frameworks: List[str], next_step_context: str = "") -> List[Dict[str, Any]]:
        """
        Internal helper to check text against regex rules.
        """
        violations = []
        text_lower = text.lower()
        next_step_lower = next_step_context.lower() if next_step_context else ""

        for fw_name in frameworks:
            if fw_name not in self._frameworks:
                continue
                
            rules = self._frameworks[fw_name]
            for rule in rules:
                trigger = rule.get("trigger_pattern")
                required = rule.get("required_action")
                
                # If the step matches a trigger pattern (e.g. "collect_email")
                if re.search(trigger, text_lower, re.IGNORECASE):
                    # Check if the REQUIRED action is also present (e.g. "encrypt")
                    # Heuristic: Check current step AND immediate next step
                    
                    # Split required actions by | (OR logic)
                    required_options = required.split("|")
                    mitigation_found = False
                    for opt in required_options:
                        opt_clean = opt.strip()
                        if opt_clean in text_lower or opt_clean in next_step_lower:
                            mitigation_found = True
                            break
                    
                    if not mitigation_found:
                        violations.append({
                            "framework": fw_name,
                            "rule_id": rule.get("id"),
                            "description": rule.get("description"),
                            "severity": rule.get("severity"),
                            "trigger_match": re.search(trigger, text_lower, re.IGNORECASE).group(0),
                            "missing_mitigation": required
                        })
        
        return violations
