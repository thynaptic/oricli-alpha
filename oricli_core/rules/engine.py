from __future__ import annotations

"""
Global rules engine for Oricli-Alpha.

Loads .ori-style rule files from oricli_core/rules/ and evaluates high-level
contexts for safety, routing, and resource policies.
"""

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional
import logging
import os


logger = logging.getLogger(__name__)


@dataclass
class Rule:
    """In-memory representation of a single rule."""

    name: str
    description: str
    scope: str
    categories: List[str] = field(default_factory=list)
    constraints: List[str] = field(default_factory=list)
    routing_preferences: List[str] = field(default_factory=list)
    resource_policies: List[str] = field(default_factory=list)


@dataclass
class RuleContext:
    """
    High-level context for rule evaluation.

    This intentionally stays coarse-grained (no payload contents) to avoid
    leaking sensitive data into logs or rule definitions.
    """

    operation_type: str  # e.g. "module_execute", "tool_call", "shell_exec"
    module_name: Optional[str] = None
    tool_name: Optional[str] = None
    path: Optional[str] = None
    tags: List[str] = field(default_factory=list)


@dataclass
class RuleDecision:
    """Decision returned by the rules engine."""

    allowed: bool
    reasons: List[str] = field(default_factory=list)
    suggested_alternatives: List[str] = field(default_factory=list)


class RulesEngine:
    """Global rules engine that loads and evaluates .ori-style rules."""

    def __init__(self, rules_dir: Optional[Path] = None) -> None:
        self._rules_dir = (
            rules_dir
            if rules_dir is not None
            else Path(__file__).parent  # oricli_core/rules
        )
        self._rules: List[Rule] = []
        self._loaded = False

    def load_rules(self, force: bool = False) -> List[Rule]:
        """Load rules from .ori files (idempotent, cached)."""
        if self._loaded and not force:
            return self._rules

        self._rules = []
        if not self._rules_dir.exists():
            logger.debug(
                "Rules directory does not exist",
                extra={"rules_dir": str(self._rules_dir)},
            )
            self._loaded = True
            return self._rules

        for path in sorted(self._rules_dir.glob("*.ori")):
            try:
                rule = self._parse_rule_file(path)
                if rule:
                    self._rules.append(rule)
            except Exception as exc:
                logger.warning(
                    "Failed to load rule file",
                    exc_info=True,
                    extra={"rules_file": str(path), "error": str(exc)},
                )

        self._loaded = True
        logger.info(
            "Rules loaded",
            extra={
                "rules_dir": str(self._rules_dir),
                "rule_count": len(self._rules),
                "rule_names": [r.name for r in self._rules],
            },
        )
        return self._rules

    def _parse_rule_file(self, path: Path) -> Optional[Rule]:
        """
        Minimal .ori-style parser for rule files.

        Expected structure:
            @rule_name: global_safety
            @description: Core safety rules.
            @scope: global
            @categories: ["safety", "routing"]

            <constraints>
            - deny: shell_sandbox_service on paths outside /workspace and /tmp
            </constraints>
        """
        text = path.read_text(encoding="utf-8")
        name: Optional[str] = None
        description: str = ""
        scope: str = "global"
        categories: List[str] = []
        constraints: List[str] = []
        routing_prefs: List[str] = []
        resource_policies: List[str] = []

        section: Optional[str] = None

        for raw_line in text.splitlines():
            line = raw_line.strip()
            if not line:
                continue

            if line.startswith("@"):
                # Header directive
                if line.startswith("@rule_name:"):
                    name = line.split(":", 1)[1].strip()
                elif line.startswith("@description:"):
                    description = line.split(":", 1)[1].strip()
                elif line.startswith("@scope:"):
                    scope = line.split(":", 1)[1].strip()
                elif line.startswith("@categories:"):
                    cats = line.split(":", 1)[1].strip()
                    # Best-effort parse of ["a", "b"] or comma-separated
                    cats = cats.strip()
                    if cats.startswith("[") and cats.endswith("]"):
                        cats = cats[1:-1]
                    categories = [
                        c.strip().strip("\"'")
                        for c in cats.split(",")
                        if c.strip()
                    ]
                continue

            if line.startswith("<") and line.endswith(">"):
                # Section start or end
                if line.startswith("</"):
                    section = None
                else:
                    section = line[1:-1].strip()
                continue

            if line.startswith("- ") and section:
                content = line[2:].strip()
                if section == "constraints":
                    constraints.append(content)
                elif section == "routing_preferences":
                    routing_prefs.append(content)
                elif section == "resource_policies":
                    resource_policies.append(content)

        if not name:
            logger.warning(
                "Rule file missing @rule_name, skipping",
                extra={"rules_file": str(path)},
            )
            return None

        return Rule(
            name=name,
            description=description,
            scope=scope,
            categories=categories,
            constraints=constraints,
            routing_preferences=routing_prefs,
            resource_policies=resource_policies,
        )

    def evaluate_request(self, context: RuleContext) -> RuleDecision:
        """
        Evaluate a context against loaded rules and return an allow/deny decision.

        v1 implements a small set of hard-coded patterns over the parsed rule
        strings. As we evolve, these can be upgraded to a richer DSL while
        keeping the Rule/RuleContext surface stable.
        """
        self.load_rules()

        allowed = True
        reasons: List[str] = []
        suggested_alternatives: List[str] = []

        # Short-circuit if disabled via env (escape hatch).
        if os.getenv("ORICLI_DISABLE_RULES", "false").lower() in ("true", "1", "yes"):
            return RuleDecision(allowed=True, reasons=["rules_disabled_via_env"])

        # Apply safety constraints for shell sandbox.
        if context.operation_type == "module_execute" and context.module_name == "shell_sandbox_service":
            for rule in self._rules:
                if "safety" not in rule.categories:
                    continue
                for c in rule.constraints:
                    # Example pattern: deny: shell_sandbox_service on paths outside /workspace and /tmp
                    if c.startswith("deny: shell_sandbox_service"):
                        path = context.path or ""
                        if path and not (path.startswith("/workspace") or path.startswith("/tmp")):
                            allowed = False
                            reasons.append(
                                "Denied by global_safety: shell_sandbox_service path outside /workspace or /tmp"
                            )

        # Routing hints (advisory only, but we surface them in decision).
        for rule in self._rules:
            for pref in rule.routing_preferences:
                # Example: prefer: game_theory_solver for multi_agent_payoff_reasoning
                if "prefer:" in pref and "for" in pref:
                    try:
                        _, rest = pref.split("prefer:", 1)
                        target_part, tag_part = rest.split("for", 1)
                        target = target_part.strip()
                        tag = tag_part.strip()
                        if tag in context.tags and target not in suggested_alternatives:
                            suggested_alternatives.append(target)
                    except ValueError:
                        continue

        return RuleDecision(
            allowed=allowed,
            reasons=reasons,
            suggested_alternatives=suggested_alternatives,
        )

    def get_routing_preferences(self, context: RuleContext) -> List[str]:
        """
        Return a list of preferred module/tool names for this context.

        This is a thin wrapper around `evaluate_request` that focuses on
        advisory routing (e.g. preferring game_theory_solver for certain tags).
        """
        decision = self.evaluate_request(context)
        return decision.suggested_alternatives


_global_engine: Optional[RulesEngine] = None


def get_rules_engine() -> RulesEngine:
    """Get a process-global RulesEngine instance."""
    global _global_engine
    if _global_engine is None:
        _global_engine = RulesEngine()
    return _global_engine

