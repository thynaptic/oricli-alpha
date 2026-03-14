from __future__ import annotations
"""
Skill Manager Module
Scans, parses, and manages declarative .ori skill files.
Injects specialized mindsets and constraints dynamically based on triggers.
"""

import os
import re
import json
import logging
from pathlib import Path
from typing import Dict, Any, List, Optional

from oricli_core.brain.base_module import BaseBrainModule, ModuleMetadata
from oricli_core.exceptions import InvalidParameterError

logger = logging.getLogger(__name__)

class SkillManagerModule(BaseBrainModule):
    """Manages declarative .ori skills for dynamic persona adoption."""

    def __init__(self):
        super().__init__()
        self.skills_dir = Path(__file__).resolve().parent.parent.parent / "skills"
        self.skills_dir.mkdir(parents=True, exist_ok=True)
        self.skills_cache: Dict[str, Dict[str, Any]] = {}
        self._load_skills()

    @property
    def metadata(self) -> ModuleMetadata:
        return ModuleMetadata(
            name="skill_manager",
            version="1.1.0",
            description="Manages declarative .ori skills for dynamic persona adoption",
            operations=[
                "match_skills",
                "get_skill",
                "reload_skills",
                "list_skills",
                "create_skill",
                "update_skill",
                "delete_skill"
            ],
            dependencies=[],
            model_required=False,
        )

    def execute(self, operation: str, params: Dict[str, Any]) -> Dict[str, Any]:
        if operation == "match_skills":
            return self._match_skills(params)
        elif operation == "get_skill":
            return self._get_skill(params)
        elif operation == "reload_skills":
            self._load_skills()
            return {"success": True, "count": len(self.skills_cache)}
        elif operation == "list_skills":
            return self._list_skills()
        elif operation == "create_skill":
            return self._create_skill(params)
        elif operation == "update_skill":
            return self._update_skill(params)
        elif operation == "delete_skill":
            return self._delete_skill(params)
        else:
            raise InvalidParameterError(parameter="operation", value=operation, reason="Unsupported operation")

    def _list_skills(self) -> Dict[str, Any]:
        """List all loaded skills."""
        return {
            "success": True,
            "skills": list(self.skills_cache.values())
        }

    def _create_skill(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """Create a new .ori skill file."""
        skill_name = params.get("skill_name")
        if not skill_name:
            return {"success": False, "error": "skill_name is required"}
            
        file_path = self.skills_dir / f"{skill_name}.ori"
        if file_path.exists():
            return {"success": False, "error": f"Skill '{skill_name}' already exists. Use update_skill."}
            
        return self._write_skill_file(file_path, params)

    def _update_skill(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """Update an existing .ori skill file."""
        skill_name = params.get("skill_name")
        if not skill_name:
            return {"success": False, "error": "skill_name is required"}
            
        file_path = self.skills_dir / f"{skill_name}.ori"
        if not file_path.exists():
            return {"success": False, "error": f"Skill '{skill_name}' does not exist. Use create_skill."}
            
        return self._write_skill_file(file_path, params)

    def _delete_skill(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """Delete a .ori skill file."""
        skill_name = params.get("skill_name")
        if not skill_name:
            return {"success": False, "error": "skill_name is required"}
            
        file_path = self.skills_dir / f"{skill_name}.ori"
        if not file_path.exists():
            return {"success": False, "error": f"Skill '{skill_name}' not found."}
            
        try:
            file_path.unlink()
            if skill_name in self.skills_cache:
                del self.skills_cache[skill_name]
            return {"success": True, "message": f"Skill '{skill_name}' deleted."}
        except Exception as e:
            logger.error(f"Failed to delete skill {skill_name}: {e}")
            return {"success": False, "error": str(e)}

    def _write_skill_file(self, file_path: Path, params: Dict[str, Any]) -> Dict[str, Any]:
        """Helper to serialize dict into .ori format and write to disk."""
        skill_name = params.get("skill_name")
        description = params.get("description", "")
        triggers = params.get("triggers", [])
        requires_tools = params.get("requires_tools", [])
        mindset = params.get("mindset", "")
        instructions = params.get("instructions", "")
        
        # Serialize format
        content = f"@skill_name: {skill_name}\n"
        content += f"@description: {description}\n"
        content += f'@triggers: {json.dumps(triggers)}\n'
        content += f'@requires_tools: {json.dumps(requires_tools)}\n\n'
        
        if mindset:
            content += f"<mindset>\n{mindset}\n</mindset>\n\n"
        if instructions:
            content += f"<instructions>\n{instructions}\n</instructions>\n"
            
        try:
            file_path.write_text(content, encoding="utf-8")
            # Reload specific skill to memory
            skill_data = self._parse_ori_file(file_path)
            self.skills_cache[skill_name] = skill_data
            return {"success": True, "skill": skill_data}
        except Exception as e:
            logger.error(f"Failed to write skill {skill_name}: {e}")
            return {"success": False, "error": str(e)}

    def _load_skills(self):
        """Scans and parses all .ori files in the skills directory."""
        self.skills_cache.clear()
        
        if not self.skills_dir.exists():
            return
            
        for file_path in self.skills_dir.glob("*.ori"):
            try:
                skill_data = self._parse_ori_file(file_path)
                if skill_data and "skill_name" in skill_data:
                    self.skills_cache[skill_data["skill_name"]] = skill_data
                    logger.info(f"Loaded skill: {skill_data['skill_name']}")
            except Exception as e:
                logger.error(f"Failed to load skill {file_path.name}: {e}")

    def _parse_ori_file(self, file_path: Path) -> Dict[str, Any]:
        """Parses the custom .ori format."""
        content = file_path.read_text(encoding="utf-8")
        
        skill_data = {
            "skill_name": "",
            "description": "",
            "triggers": [],
            "requires_tools": [],
            "mindset": "",
            "instructions": ""
        }
        
        # Parse Directives (@directive: value)
        for line in content.splitlines():
            if line.startswith("@"):
                parts = line.split(":", 1)
                if len(parts) == 2:
                    key = parts[0].strip()[1:] # remove @
                    val = parts[1].strip()
                    
                    if key in ["triggers", "requires_tools"]:
                        try:
                            # Safely evaluate JSON-like arrays
                            import ast
                            val_list = ast.literal_eval(val)
                            if isinstance(val_list, list):
                                skill_data[key] = val_list
                        except Exception:
                            # Fallback to simple split if not a valid list string
                            skill_data[key] = [v.strip().strip('"\'') for v in val.strip("[]").split(",") if v.strip()]
                    else:
                        skill_data[key] = val

        # Parse XML Blocks (<block>content</block>)
        mindset_match = re.search(r"<mindset>(.*?)</mindset>", content, re.DOTALL | re.IGNORECASE)
        if mindset_match:
            skill_data["mindset"] = mindset_match.group(1).strip()
            
        instructions_match = re.search(r"<instructions>(.*?)</instructions>", content, re.DOTALL | re.IGNORECASE)
        if instructions_match:
            skill_data["instructions"] = instructions_match.group(1).strip()

        return skill_data

    def _match_skills(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """Find the best matching skills for a given query."""
        query = str(params.get("query", "")).lower()
        if not query:
            return {"success": True, "matches": []}
            
        matches = []
        for name, data in self.skills_cache.items():
            triggers = data.get("triggers", [])
            for trigger in triggers:
                # Simple keyword matching for now. Can be upgraded to embeddings later.
                if trigger.lower() in query:
                    matches.append(data)
                    break # One trigger is enough
                    
        return {
            "success": True,
            "matches": matches
        }

    def _get_skill(self, params: Dict[str, Any]) -> Dict[str, Any]:
        skill_name = params.get("skill_name")
        if not skill_name or skill_name not in self.skills_cache:
            return {"success": False, "error": f"Skill '{skill_name}' not found."}
            
        return {
            "success": True,
            "skill": self.skills_cache[skill_name]
        }
