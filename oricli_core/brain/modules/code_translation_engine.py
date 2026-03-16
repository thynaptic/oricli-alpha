from __future__ import annotations
"""
Code Translation Engine Module

Specialized AST-based reasoning for porting code between languages
while maintaining identical Big-O complexity.
"""

import ast
import json
import logging
import re
from typing import Dict, Any, List, Optional

from oricli_core.brain.base_module import BaseBrainModule, ModuleMetadata
from oricli_core.exceptions import InvalidParameterError

logger = logging.getLogger(__name__)

class CodeTranslationEngine(BaseBrainModule):
    """Translates code between languages using AST analysis and complexity preservation."""

    def __init__(self):
        super().__init__()
        self.is_initialized = False

    @property
    def metadata(self) -> ModuleMetadata:
        return ModuleMetadata(
            name="code_translation_engine",
            version="1.0.0",
            description="Translates code between languages while preserving Big-O complexity.",
            operations=[
                "translate_code",
                "analyze_ast_structure",
                "estimate_complexity"
            ],
            dependencies=[],
            model_required=False,
        )

    def initialize(self) -> bool:
        self.is_initialized = True
        return True

    def execute(self, operation: str, params: Dict[str, Any]) -> Dict[str, Any]:
        if not self.is_initialized:
            self.initialize()

        if operation == "translate_code":
            return self._translate_code(params)
        elif operation == "analyze_ast_structure":
            return self._analyze_ast_structure(params)
        elif operation == "estimate_complexity":
            return self._estimate_complexity(params)
        else:
            raise InvalidParameterError("operation", operation, "Unknown operation")

    def _analyze_ast_structure(self, params: Dict[str, Any]) -> Dict[str, Any]:
        source_code = params.get("source_code")
        if not source_code:
            raise InvalidParameterError("source_code", str(source_code), "source_code is required")
            
        try:
            tree = ast.parse(source_code)
        except SyntaxError as e:
            return {"success": False, "error": f"Syntax error in source code: {e}"}
            
        analysis = {
            "functions": [],
            "classes": [],
            "max_loop_depth": 0,
            "has_recursion": False,
            "loop_count": 0
        }
        
        # Helper to find max loop depth
        def get_loop_depth(node, current_depth=0):
            max_depth = current_depth
            for child in ast.iter_child_nodes(node):
                if isinstance(child, (ast.For, ast.While)):
                    depth = get_loop_depth(child, current_depth + 1)
                    max_depth = max(max_depth, depth)
                else:
                    depth = get_loop_depth(child, current_depth)
                    max_depth = max(max_depth, depth)
            return max_depth
            
        analysis["max_loop_depth"] = get_loop_depth(tree)
        
        for node in ast.walk(tree):
            if isinstance(node, ast.FunctionDef):
                func_info = {
                    "name": node.name,
                    "args": [arg.arg for arg in node.args.args],
                    "has_recursion": False,
                    "loops": 0
                }
                
                # Check for recursion and loops within this function
                for child in ast.walk(node):
                    if isinstance(child, ast.Call):
                        if isinstance(child.func, ast.Name) and child.func.id == node.name:
                            func_info["has_recursion"] = True
                            analysis["has_recursion"] = True
                    elif isinstance(child, (ast.For, ast.While)):
                        func_info["loops"] += 1
                        analysis["loop_count"] += 1
                        
                analysis["functions"].append(func_info)
                
            elif isinstance(node, ast.ClassDef):
                analysis["classes"].append({
                    "name": node.name,
                    "methods": [n.name for n in node.body if isinstance(n, ast.FunctionDef)]
                })
                
        return {"success": True, "analysis": analysis}

    def _estimate_complexity(self, params: Dict[str, Any]) -> Dict[str, Any]:
        source_code = params.get("source_code")
        if not source_code:
            raise InvalidParameterError("source_code", str(source_code), "source_code is required")
            
        try:
            from oricli_core.brain.registry import ModuleRegistry
            ModuleRegistry.discover_modules()
            cog_gen = ModuleRegistry.get_module("cognitive_generator")
            
            if not cog_gen:
                return {"success": False, "error": "cognitive_generator not available"}
                
            prompt = f"""
            Analyze the following code and determine its Big-O time and space complexity.
            Format the output as a strict JSON object with two keys: 'time_complexity' and 'space_complexity'.
            Provide the standard Big-O notation (e.g., "O(N)", "O(N^2)", "O(1)").
            
            Code:
            {source_code}
            
            Output JSON only:
            """
            
            res = cog_gen.execute("generate_response", {"input": prompt})
            output_text = res.get("text", "")
            
            json_match = re.search(r"\{.*\}", output_text, re.DOTALL)
            if not json_match:
                return {"success": False, "error": "Failed to parse JSON from generator"}
                
            data = json.loads(json_match.group(0))
            
            return {
                "success": True,
                "time_complexity": data.get("time_complexity", "Unknown"),
                "space_complexity": data.get("space_complexity", "Unknown")
            }
            
        except Exception as e:
            logger.error(f"Error in estimate_complexity: {e}")
            return {"success": False, "error": str(e)}

    def _translate_code(self, params: Dict[str, Any]) -> Dict[str, Any]:
        source_code = params.get("source_code")
        source_lang = params.get("source_lang", "python").lower()
        target_lang = params.get("target_lang")
        
        if not source_code or not target_lang:
            raise InvalidParameterError("source_code/target_lang", "missing", "Both source_code and target_lang are required")
            
        ast_hints = {}
        if source_lang == "python":
            ast_res = self._analyze_ast_structure({"source_code": source_code})
            if ast_res.get("success"):
                ast_hints = ast_res.get("analysis", {})
                
        complexity_res = self._estimate_complexity({"source_code": source_code})
        time_complexity = complexity_res.get("time_complexity", "Unknown")
        space_complexity = complexity_res.get("space_complexity", "Unknown")
        
        try:
            from oricli_core.brain.registry import ModuleRegistry
            cog_gen = ModuleRegistry.get_module("cognitive_generator")
            
            if not cog_gen:
                return {"success": False, "error": "cognitive_generator not available"}
                
            prompt = f"""
            You are an expert code translator. Translate the following {source_lang} code into {target_lang}.
            
            CRITICAL CONSTRAINTS:
            1. You MUST maintain the exact same Big-O time complexity: {time_complexity}
            2. You MUST maintain the exact same Big-O space complexity: {space_complexity}
            
            AST Structural Hints (if applicable):
            {json.dumps(ast_hints, indent=2)}
            
            Source Code:
            ```{source_lang}
            {source_code}
            ```
            
            Output ONLY the translated {target_lang} code inside a markdown code block. Do not include explanations.
            """
            
            res = cog_gen.execute("generate_response", {"input": prompt})
            output_text = res.get("text", "")
            
            # Extract code block
            code_match = re.search(r"```(?:\w+)?\n(.*?)```", output_text, re.DOTALL)
            translated_code = code_match.group(1).strip() if code_match else output_text.strip()
            
            return {
                "success": True,
                "translated_code": translated_code,
                "time_complexity_preserved": time_complexity,
                "space_complexity_preserved": space_complexity,
                "ast_hints_used": bool(ast_hints)
            }
            
        except Exception as e:
            logger.error(f"Error in translate_code: {e}")
            return {"success": False, "error": str(e)}
