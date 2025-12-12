"""
Pattern Library Module - Response templates and conversation patterns
Handles pattern matching, template generation, variations, and flow patterns
"""

from typing import Dict, Any, List, Optional
import json
import random
import re
import sys
from pathlib import Path

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent))

from mavaia_core.brain.base_module import BaseBrainModule, ModuleMetadata


class PatternLibraryModule(BaseBrainModule):
    """Pattern library for response templates and conversation patterns"""

    def __init__(self):
        self.config = None
        self.patterns = {}
        self.templates = {}
        self.flows = {}
        self.social_patterns = {}
        self._load_config()

    @property
    def metadata(self) -> ModuleMetadata:
        return ModuleMetadata(
            name="pattern_library",
            version="1.0.0",
            description="Pattern library: templates, patterns, flows, social interactions",
            operations=[
                "get_pattern",
                "match_pattern",
                "generate_variations",
                "get_flow",
                "get_social_pattern",
                "fill_template",
            ],
            dependencies=[],
            model_required=False,
        )

    def initialize(self) -> bool:
        """Initialize the module"""
        return True

    def _load_config(self):
        """Load pattern library configuration"""
        config_path = Path(__file__).parent / "pattern_library.json"
        try:
            if config_path.exists():
                with open(config_path, "r", encoding="utf-8") as f:
                    self.config = json.load(f)
                    self.patterns = self.config.get("patterns", {})
                    self.templates = self.config.get("templates", {})
                    self.flows = self.config.get("conversation_flows", {})
                    self.social_patterns = self.config.get("social_patterns", {})
            else:
                # Default patterns
                self.patterns = {}
                self.templates = {}
                self.flows = {}
                self.social_patterns = {}
        except Exception as e:
            print(f"[PatternLibraryModule] Failed to load config: {e}", file=sys.stderr)
            self.patterns = {}
            self.templates = {}
            self.flows = {}
            self.social_patterns = {}

    def execute(self, operation: str, params: Dict[str, Any]) -> Dict[str, Any]:
        """Execute a pattern library operation"""
        if operation == "get_pattern":
            pattern_name = params.get("pattern_name", "")
            return self.get_pattern(pattern_name)
        elif operation == "match_pattern":
            text = params.get("text", "")
            pattern_category = params.get("pattern_category", "")
            return self.match_pattern(text, pattern_category)
        elif operation == "generate_variations":
            template = params.get("template", "")
            count = params.get("count", 3)
            return self.generate_variations(template, count)
        elif operation == "get_flow":
            flow_name = params.get("flow_name", "")
            return self.get_flow(flow_name)
        elif operation == "get_social_pattern":
            pattern_type = params.get("pattern_type", "")
            return self.get_social_pattern(pattern_type)
        elif operation == "fill_template":
            template = params.get("template", "")
            variables = params.get("variables", {})
            return self.fill_template(template, variables)
        else:
            raise ValueError(f"Unknown operation: {operation}")

    def get_pattern(self, pattern_name: str) -> Dict[str, Any]:
        """Get a pattern by name"""
        if pattern_name in self.patterns:
            pattern = self.patterns[pattern_name]
            return {"pattern_name": pattern_name, "pattern": pattern, "found": True}
        else:
            return {"pattern_name": pattern_name, "pattern": None, "found": False}

    def match_pattern(self, text: str, pattern_category: str = "") -> Dict[str, Any]:
        """Match text against patterns"""
        if not text:
            return {"matches": [], "count": 0, "text": text}

        text_lower = text.lower()
        matches = []

        # Search in specified category or all categories
        search_patterns = {}
        if pattern_category and pattern_category in self.patterns:
            search_patterns[pattern_category] = self.patterns[pattern_category]
        else:
            search_patterns = self.patterns

        for category, patterns in search_patterns.items():
            if isinstance(patterns, dict):
                for pattern_name, pattern_data in patterns.items():
                    if isinstance(pattern_data, dict):
                        pattern_strings = pattern_data.get("patterns", [])
                        if not pattern_strings:
                            pattern_strings = [pattern_data.get("pattern", "")]

                        for pattern_str in pattern_strings:
                            if pattern_str and pattern_str.lower() in text_lower:
                                matches.append(
                                    {
                                        "category": category,
                                        "pattern_name": pattern_name,
                                        "pattern": pattern_str,
                                        "match_text": text,
                                        "confidence": 0.8,
                                    }
                                )
            elif isinstance(patterns, list):
                for pattern_str in patterns:
                    if pattern_str and pattern_str.lower() in text_lower:
                        matches.append(
                            {
                                "category": category,
                                "pattern": pattern_str,
                                "match_text": text,
                                "confidence": 0.7,
                            }
                        )

        return {
            "matches": matches,
            "count": len(matches),
            "text": text,
            "category": pattern_category,
        }

    def generate_variations(self, template: str, count: int = 3) -> Dict[str, Any]:
        """Generate variations of a template"""
        if not template:
            return {"variations": [], "count": 0, "template": template}

        variations = []

        # Simple variation generation (replace synonyms, reorder phrases)
        # In a full implementation, this would use more sophisticated NLP

        # Check if template is in template library
        if template in self.templates:
            template_data = self.templates[template]
            variations_list = template_data.get("variations", [])
            if variations_list:
                variations = random.sample(
                    variations_list, min(count, len(variations_list))
                )
            else:
                # Generate simple variations
                base_template = template_data.get("base", template)
                variations = [base_template] * count
        else:
            # Generate simple variations by adding/removing modifiers
            variations = [template]

            # Add variations with different modifiers
            modifiers = ["", "Certainly, ", "Of course, ", "Absolutely, "]
            for i in range(count - 1):
                if i < len(modifiers):
                    variations.append(modifiers[i] + template)
                else:
                    variations.append(template)

        return {
            "variations": variations[:count],
            "count": len(variations[:count]),
            "template": template,
        }

    def get_flow(self, flow_name: str) -> Dict[str, Any]:
        """Get a conversation flow pattern"""
        if flow_name in self.flows:
            flow = self.flows[flow_name]
            return {
                "flow_name": flow_name,
                "flow": flow,
                "steps": len(flow) if isinstance(flow, list) else 0,
                "found": True,
            }
        else:
            return {"flow_name": flow_name, "flow": None, "steps": 0, "found": False}

    def get_social_pattern(self, pattern_type: str) -> Dict[str, Any]:
        """Get a social interaction pattern"""
        if pattern_type in self.social_patterns:
            pattern = self.social_patterns[pattern_type]
            return {"pattern_type": pattern_type, "pattern": pattern, "found": True}
        else:
            return {"pattern_type": pattern_type, "pattern": None, "found": False}

    def fill_template(
        self, template: str, variables: Dict[str, str] = None
    ) -> Dict[str, Any]:
        """Fill a template with variables"""
        if variables is None:
            variables = {}

        if not template:
            return {
                "filled_template": "",
                "variables_used": [],
                "variables_missing": [],
            }

        filled = template
        variables_used = []
        variables_missing = []

        # Find template variables (e.g., {name}, {topic})
        variable_pattern = re.compile(r"\{(\w+)\}")
        matches = variable_pattern.findall(template)

        for var_name in matches:
            if var_name in variables:
                filled = filled.replace(f"{{{var_name}}}", variables[var_name])
                variables_used.append(var_name)
            else:
                variables_missing.append(var_name)
                # Replace missing variables with bracketed variable name
                filled = filled.replace(f"{{{var_name}}}", f"[{var_name}]")

        return {
            "filled_template": filled,
            "variables_used": variables_used,
            "variables_missing": variables_missing,
            "success": len(variables_missing) == 0,
        }

    def validate_params(self, operation: str, params: Dict[str, Any]) -> bool:
        """Validate parameters for operations"""
        if operation == "get_pattern":
            return "pattern_name" in params
        elif operation == "match_pattern":
            return "text" in params
        elif operation == "generate_variations":
            return "template" in params
        elif operation == "get_flow":
            return "flow_name" in params
        elif operation == "get_social_pattern":
            return "pattern_type" in params
        elif operation == "fill_template":
            return "template" in params
        return True
