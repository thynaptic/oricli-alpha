from __future__ import annotations
"""
Adversarial Auditor Module - Red-Team Cognition
Applies offensive security expertise to audit cognitive pathways and plans.
Identifies vulnerabilities, hallucinations, and manipulation vectors.
"""

import logging
import json
import re
import time
from pathlib import Path
from typing import List, Dict, Any, Optional

from mavaia_core.brain.base_module import BaseBrainModule, ModuleMetadata
from mavaia_core.exceptions import InvalidParameterError

logger = logging.getLogger(__name__)

class AdversarialAuditorModule(BaseBrainModule):
    """Offensive security auditor for Mavaia's reasoning."""

    def __init__(self) -> None:
        super().__init__()
        self.vulnerability_patterns = [
            # 1. Path Traversal / File Access
            (r"(\.\./|/etc/|/root/|\.env|\.ssh)", "Unauthorized File Access"),
            # 2. Credential Leakage
            (r"(api_key|secret|token|password|auth_id)", "Sensitive Credential Exposure"),
            # 3. Instruction Injection
            (r"(ignore previous|system prompt|override safety|developer mode)", "Instruction Injection Vector"),
            # 4. Dangerous Shell commands
            (r"(rm -rf /|chmod 777|chown|kill -9)", "Destructive Shell Operation")
        ]

    @property
    def metadata(self) -> ModuleMetadata:
        return ModuleMetadata(
            name="adversarial_auditor",
            version="1.0.0",
            description="Red-Team Cognitive Auditor: intercepts and exploits plans to find flaws",
            operations=[
                "audit_plan",
                "fuzz_reasoning",
                "detect_manipulation"
            ],
            dependencies=[],
            model_required=False,
        )

    def execute(self, operation: str, params: Dict[str, Any]) -> Dict[str, Any]:
        if operation == "audit_plan":
            return self._audit_plan(params)
        elif operation == "fuzz_reasoning":
            return self._fuzz_reasoning(params)
        elif operation == "detect_manipulation":
            return self._detect_manipulation(params)
        else:
            raise InvalidParameterError(parameter="operation", value=operation, reason="Unsupported operation")

    def _audit_plan(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """
        Scan a Directed Acyclic Graph (DAG) for security vulnerabilities.
        """
        graph = params.get("graph", {})
        nodes = graph.get("nodes", [])
        findings = []
        
        for node in nodes:
            node_id = node.get("id")
            module = node.get("module")
            op = node.get("operation")
            node_params = str(node.get("params", {}))
            
            # Check for pattern matches in params
            for pattern, category in self.vulnerability_patterns:
                if re.search(pattern, node_params, re.IGNORECASE):
                    findings.append({
                        "node_id": node_id,
                        "module": module,
                        "operation": op,
                        "vulnerability": category,
                        "evidence": re.search(pattern, node_params, re.IGNORECASE).group(0)
                    })
                    
            # Module-specific logic
            if module == "shell_sandbox_service" and "rm" in node_params:
                findings.append({
                    "node_id": node_id,
                    "module": module,
                    "vulnerability": "Potential Destructive Command",
                    "severity": "High"
                })

        passed = len(findings) == 0
        if not passed:
            _rich_log(f"Adversarial Sentinel: AUDIT FAILED! Found {len(findings)} vulnerabilities.", "red", "🧨")
            self._log_red_team_lesson(params.get("query", "Unknown"), findings)
        
        return {
            "success": True,
            "passed": passed,
            "findings": findings,
            "recommendation": "Reject and re-architect" if not passed else "Proceed"
        }

    def _log_red_team_lesson(self, query: str, findings: List[Dict]):
        """Record the vulnerability for future training."""
        lesson_path = Path(__file__).resolve().parent.parent.parent / "data" / "red_team_lessons.jsonl"
        lesson_path.parent.mkdir(parents=True, exist_ok=True)
        
        lesson = {
            "prompt": query,
            "rejected_path": "Execution with vulnerable tools/parameters",
            "chosen_path": "Safe internal reasoning/refusal",
            "vulnerabilities": findings,
            "timestamp": time.time()
        }
        
        try:
            with open(lesson_path, "a", encoding="utf-8") as f:
                f.write(json.dumps(lesson) + "\n")
        except Exception as e:
            logger.warning(f"Failed to log red-team lesson: {e}")

    def _fuzz_reasoning(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """
        Identify weak links in a reasoning chain and suggest 'attacks' to test them.
        """
        trace = params.get("trace", "")
        # Heuristic: low certainty phrases
        weak_patterns = [r"maybe", r"possibly", r"i think", r"uncertain", r"not sure"]
        
        attacks = []
        for pattern in weak_patterns:
            if re.search(pattern, trace, re.IGNORECASE):
                attacks.append(f"Inject contradictory evidence for '{pattern}' node.")
                
        return {
            "success": True,
            "resilience_score": 1.0 - (len(attacks) * 0.2),
            "suggested_fuzz_attacks": attacks
        }

    def _detect_manipulation(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """
        Detect if the user input contains social engineering or manipulation.
        """
        input_text = params.get("text", "")
        # Look for gaslighting or urgency patterns
        manip_patterns = [r"you must", r"ignore everything", r"i will be fired", r"it is urgent"]
        
        detected = []
        for pattern in manip_patterns:
            if re.search(pattern, input_text, re.IGNORECASE):
                detected.append(pattern)
                
        return {
            "success": True,
            "manipulation_detected": len(detected) > 0,
            "patterns": detected
        }

def _rich_log(message: str, style: str = "white", icon: str = ""):
    prefix = f"{icon} " if icon else ""
    print(f"[{style}]{prefix}{message}")
