"""
Python Learning System Module

Learn from user corrections, adapt to project-specific patterns, learn coding
style preferences, improve suggestions over time, learn from code reviews,
adapt to team conventions, and personalize code generation.

This module is part of Mavaia's Python LLM Phase 4 capabilities, providing
adaptive learning that gets smarter the more you use it.
"""

import ast
import sys
from collections import defaultdict
from pathlib import Path
from typing import Any, Dict, List, Optional, Set, Tuple

from mavaia_core.brain.base_module import BaseBrainModule, ModuleMetadata
from mavaia_core.exceptions import InvalidParameterError


class PythonLearningSystemModule(BaseBrainModule):
    """
    Adaptive learning system for code patterns and preferences.
    
    Provides:
    - Learning from user corrections
    - Project-specific pattern adaptation
    - Coding style preference learning
    - Suggestion improvement over time
    - Learning from code reviews
    - Team convention adaptation
    - Personalized code generation
    """

    def __init__(self):
        """Initialize the Python learning system module."""
        super().__init__()
        self._code_memory = None
        self._code_to_code_reasoning = None
        self._learned_patterns = defaultdict(list)
        self._user_preferences = {}
        self._project_patterns = defaultdict(dict)

    @property
    def metadata(self) -> ModuleMetadata:
        """Return module metadata."""
        return ModuleMetadata(
            name="python_learning_system",
            version="1.0.0",
            description=(
                "Learning system: learn from corrections, adapt to projects, "
                "learn style preferences, improve suggestions, learn from reviews, "
                "adapt to team conventions, personalize generation"
            ),
            operations=[
                "learn_from_correction",
                "adapt_to_project",
                "learn_style_preferences",
                "improve_suggestions",
                "learn_from_review",
                "adapt_to_team",
                "personalize_generation",
            ],
            dependencies=[],
            model_required=False,
        )

    def initialize(self) -> bool:
        """Initialize the module."""
        # Try to load related modules
        try:
            from mavaia_core.brain.registry import ModuleRegistry
            self._code_memory = ModuleRegistry.get_module("python_code_memory")
            self._code_to_code_reasoning = ModuleRegistry.get_module("code_to_code_reasoning")
        except Exception:
            pass
        
        return True

    def execute(self, operation: str, params: Dict[str, Any]) -> Dict[str, Any]:
        """
        Execute a learning operation.
        
        Args:
            operation: Operation name
            params: Operation parameters
            
        Returns:
            Operation result dictionary
            
        Raises:
            ValueError: If operation is unknown
            InvalidParameterError: If parameters are invalid
        """
        if operation == "learn_from_correction":
            original = params.get("original", "")
            corrected = params.get("corrected", "")
            context = params.get("context", {})
            if not original:
                raise InvalidParameterError("original", "", "Original code cannot be empty")
            if not corrected:
                raise InvalidParameterError("corrected", "", "Corrected code cannot be empty")
            return self.learn_from_correction(original, corrected, context)
        
        elif operation == "adapt_to_project":
            project = params.get("project", None)
            examples = params.get("examples", [])
            if not project:
                raise InvalidParameterError("project", None, "Project path is required")
            return self.adapt_to_project(project, examples)
        
        elif operation == "learn_style_preferences":
            user = params.get("user", "")
            examples = params.get("examples", [])
            if not user:
                raise InvalidParameterError("user", "", "User identifier is required")
            if not examples:
                raise InvalidParameterError("examples", [], "Examples list cannot be empty")
            return self.learn_style_preferences(user, examples)
        
        elif operation == "improve_suggestions":
            feedback = params.get("feedback", {})
            if not feedback:
                raise InvalidParameterError("feedback", {}, "Feedback cannot be empty")
            return self.improve_suggestions(feedback)
        
        elif operation == "learn_from_review":
            code = params.get("code", "")
            review_feedback = params.get("review_feedback", {})
            if not code:
                raise InvalidParameterError("code", "", "Code cannot be empty")
            if not review_feedback:
                raise InvalidParameterError("review_feedback", {}, "Review feedback cannot be empty")
            return self.learn_from_review(code, review_feedback)
        
        elif operation == "adapt_to_team":
            team_codebase = params.get("team_codebase", None)
            if not team_codebase:
                raise InvalidParameterError("team_codebase", None, "Team codebase path is required")
            return self.adapt_to_team(team_codebase)
        
        elif operation == "personalize_generation":
            user_preferences = params.get("user_preferences", {})
            if not user_preferences:
                raise InvalidParameterError("user_preferences", {}, "User preferences cannot be empty")
            return self.personalize_generation(user_preferences)
        
        else:
            raise ValueError(f"Unknown operation: {operation}")

    def learn_from_correction(self, original: str, corrected: str, context: Dict[str, Any] = None) -> Dict[str, Any]:
        """
        Learn from user correction.
        
        Args:
            original: Original code
            corrected: Corrected code
            context: Additional context (project, file, etc.)
            
        Returns:
            Dictionary containing learning results
        """
        if context is None:
            context = {}

        # Analyze the correction
        try:
            original_tree = ast.parse(original)
            corrected_tree = ast.parse(corrected)
        except SyntaxError as e:
            return {
                "success": False,
                "error": f"Syntax error: {e}",
            }
        except Exception as e:
            return {
                "success": False,
                "error": f"Parse error: {e}",
            }

        # Extract patterns from correction
        correction_pattern = self._extract_correction_pattern(original, corrected, original_tree, corrected_tree)
        
        # Store learned pattern
        pattern_type = correction_pattern.get("type", "unknown")
        self._learned_patterns[pattern_type].append({
            "pattern": correction_pattern,
            "context": context,
            "timestamp": self._get_timestamp(),
        })

        return {
            "success": True,
            "pattern_learned": correction_pattern,
            "pattern_type": pattern_type,
            "total_patterns": len(self._learned_patterns[pattern_type]),
            "learning_summary": self._generate_learning_summary(correction_pattern),
        }

    def adapt_to_project(self, project: Union[str, Path], examples: List[Dict[str, Any]] = None) -> Dict[str, Any]:
        """
        Adapt to project-specific patterns.
        
        Args:
            project: Project path
            examples: Example code patterns from project
            
        Returns:
            Dictionary containing adaptation results
        """
        if examples is None:
            examples = []

        project_path = Path(project)
        
        if not project_path.exists():
            return {
                "success": False,
                "error": f"Project path does not exist: {project}",
            }

        # Analyze project patterns
        project_patterns = {}
        
        if examples:
            # Learn from provided examples
            for example in examples:
                code = example.get("code", "")
                pattern_type = example.get("pattern_type", "unknown")
                
                if code:
                    try:
                        tree = ast.parse(code)
                        pattern = self._extract_code_pattern(code, tree, pattern_type)
                        project_patterns[pattern_type] = pattern
                    except Exception:
                        pass
        else:
            # Analyze project codebase
            python_files = list(project_path.rglob("*.py"))[:10]  # Sample first 10 files
            
            for py_file in python_files:
                try:
                    with open(py_file, "r", encoding="utf-8") as f:
                        code = f.read()
                    
                    tree = ast.parse(code)
                    patterns = self._analyze_project_patterns(code, tree)
                    project_patterns.update(patterns)
                except Exception:
                    pass

        # Store project patterns
        self._project_patterns[str(project_path)] = project_patterns

        return {
            "success": True,
            "project": str(project_path),
            "patterns_learned": project_patterns,
            "pattern_count": len(project_patterns),
            "adaptation_summary": self._generate_adaptation_summary(project_patterns),
        }

    def learn_style_preferences(self, user: str, examples: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        Learn coding style preferences from examples.
        
        Args:
            user: User identifier
            examples: List of code examples with style preferences
            
        Returns:
            Dictionary containing learned preferences
        """
        preferences = {
            "naming_conventions": {},
            "formatting_style": {},
            "code_structure": {},
            "documentation_style": {},
        }

        # Analyze examples
        for example in examples:
            code = example.get("code", "")
            style_notes = example.get("style_notes", {})
            
            if code:
                try:
                    tree = ast.parse(code)
                    style_features = self._extract_style_features(code, tree)
                    
                    # Merge style features
                    for key, value in style_features.items():
                        if key in preferences:
                            preferences[key].update(value)
                except Exception:
                    pass

        # Store user preferences
        self._user_preferences[user] = preferences

        return {
            "success": True,
            "user": user,
            "preferences_learned": preferences,
            "preference_count": sum(len(v) for v in preferences.values()),
            "learning_summary": self._generate_preference_summary(preferences),
        }

    def improve_suggestions(self, feedback: Dict[str, Any]) -> Dict[str, Any]:
        """
        Improve suggestions based on feedback.
        
        Args:
            feedback: Feedback on previous suggestions
            
        Returns:
            Dictionary containing improvement results
        """
        suggestion_id = feedback.get("suggestion_id", "")
        rating = feedback.get("rating", 0)
        comments = feedback.get("comments", "")
        suggestion_type = feedback.get("suggestion_type", "unknown")

        # Store feedback
        if suggestion_type not in self._learned_patterns:
            self._learned_patterns[suggestion_type] = []

        self._learned_patterns[suggestion_type].append({
            "feedback": feedback,
            "rating": rating,
            "timestamp": self._get_timestamp(),
        })

        # Analyze feedback for improvements
        improvements = self._analyze_feedback_for_improvements(feedback)

        return {
            "success": True,
            "suggestion_id": suggestion_id,
            "feedback_recorded": True,
            "improvements": improvements,
            "improvement_count": len(improvements),
        }

    def learn_from_review(self, code: str, review_feedback: Dict[str, Any]) -> Dict[str, Any]:
        """
        Learn from code review feedback.
        
        Args:
            code: Code that was reviewed
            review_feedback: Review feedback and suggestions
            
        Returns:
            Dictionary containing learning results
        """
        try:
            tree = ast.parse(code)
        except SyntaxError as e:
            return {
                "success": False,
                "error": f"Syntax error: {e}",
            }
        except Exception as e:
            return {
                "success": False,
                "error": f"Parse error: {e}",
            }

        # Extract review patterns
        review_patterns = self._extract_review_patterns(code, tree, review_feedback)
        
        # Store learned patterns
        for pattern_type, pattern in review_patterns.items():
            self._learned_patterns[pattern_type].append({
                "pattern": pattern,
                "review_feedback": review_feedback,
                "timestamp": self._get_timestamp(),
            })

        return {
            "success": True,
            "patterns_learned": review_patterns,
            "pattern_count": len(review_patterns),
            "learning_summary": self._generate_review_learning_summary(review_patterns),
        }

    def adapt_to_team(self, team_codebase: Union[str, Path]) -> Dict[str, Any]:
        """
        Adapt to team coding conventions.
        
        Args:
            team_codebase: Team codebase path
            
        Returns:
            Dictionary containing adaptation results
        """
        codebase_path = Path(team_codebase)
        
        if not codebase_path.exists():
            return {
                "success": False,
                "error": f"Codebase path does not exist: {team_codebase}",
            }

        # Analyze team conventions
        conventions = self._analyze_team_conventions(codebase_path)

        return {
            "success": True,
            "codebase": str(codebase_path),
            "conventions_learned": conventions,
            "convention_count": len(conventions),
            "adaptation_summary": self._generate_team_adaptation_summary(conventions),
        }

    def personalize_generation(self, user_preferences: Dict[str, Any]) -> Dict[str, Any]:
        """
        Personalize code generation based on user preferences.
        
        Args:
            user_preferences: User preferences for code generation
            
        Returns:
            Dictionary containing personalization results
        """
        # Store preferences
        user_id = user_preferences.get("user_id", "default")
        self._user_preferences[user_id] = user_preferences

        # Generate personalization profile
        profile = self._generate_personalization_profile(user_preferences)

        return {
            "success": True,
            "user_id": user_id,
            "profile": profile,
            "preferences_applied": user_preferences,
            "personalization_summary": self._generate_personalization_summary(profile),
        }

    # Helper methods

    def _extract_correction_pattern(
        self,
        original: str,
        corrected: str,
        original_tree: ast.AST,
        corrected_tree: ast.AST
    ) -> Dict[str, Any]:
        """Extract pattern from correction."""
        pattern = {
            "type": "correction",
            "changes": [],
        }

        # Compare ASTs to find differences
        original_visitor = StructureVisitor()
        original_visitor.visit(original_tree)

        corrected_visitor = StructureVisitor()
        corrected_visitor.visit(corrected_tree)

        # Identify changes
        if len(original_visitor.functions) != len(corrected_visitor.functions):
            pattern["changes"].append("function_count_changed")
        
        if len(original_visitor.classes) != len(corrected_visitor.classes):
            pattern["changes"].append("class_count_changed")

        return pattern

    def _extract_code_pattern(self, code: str, tree: ast.AST, pattern_type: str) -> Dict[str, Any]:
        """Extract code pattern."""
        visitor = PatternExtractor(pattern_type)
        visitor.visit(tree)
        return visitor.pattern

    def _analyze_project_patterns(self, code: str, tree: ast.AST) -> Dict[str, Any]:
        """Analyze project patterns."""
        patterns = {}
        
        visitor = ProjectPatternVisitor()
        visitor.visit(tree)
        
        patterns["naming"] = visitor.naming_patterns
        patterns["structure"] = visitor.structure_patterns
        
        return patterns

    def _extract_style_features(self, code: str, tree: ast.AST) -> Dict[str, Any]:
        """Extract style features."""
        features = {
            "naming_conventions": {},
            "formatting_style": {},
            "code_structure": {},
            "documentation_style": {},
        }

        visitor = StyleFeatureVisitor()
        visitor.visit(tree)
        
        features["naming_conventions"] = visitor.naming_patterns
        features["formatting_style"] = visitor.formatting_patterns
        
        return features

    def _analyze_feedback_for_improvements(self, feedback: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Analyze feedback for improvement opportunities."""
        improvements = []
        
        rating = feedback.get("rating", 0)
        comments = feedback.get("comments", "")
        
        if rating < 3:
            improvements.append({
                "type": "suggestion_quality",
                "description": "Improve suggestion quality based on low rating",
            })
        
        if "unclear" in comments.lower():
            improvements.append({
                "type": "clarity",
                "description": "Improve suggestion clarity",
            })

        return improvements

    def _extract_review_patterns(self, code: str, tree: ast.AST, review_feedback: Dict[str, Any]) -> Dict[str, Any]:
        """Extract patterns from review feedback."""
        patterns = {}
        
        issues = review_feedback.get("issues", [])
        suggestions = review_feedback.get("suggestions", [])
        
        for issue in issues:
            issue_type = issue.get("type", "unknown")
            patterns[issue_type] = {
                "issue": issue,
                "code_context": code[:200],
            }
        
        return patterns

    def _analyze_team_conventions(self, codebase_path: Path) -> Dict[str, Any]:
        """Analyze team coding conventions."""
        conventions = {
            "naming": {},
            "formatting": {},
            "structure": {},
        }

        python_files = list(codebase_path.rglob("*.py"))[:20]  # Sample
        
        for py_file in python_files:
            try:
                with open(py_file, "r", encoding="utf-8") as f:
                    code = f.read()
                
                tree = ast.parse(code)
                visitor = ConventionVisitor()
                visitor.visit(tree)
                
                conventions["naming"].update(visitor.naming_conventions)
                conventions["formatting"].update(visitor.formatting_conventions)
            except Exception:
                pass

        return conventions

    def _generate_personalization_profile(self, preferences: Dict[str, Any]) -> Dict[str, Any]:
        """Generate personalization profile."""
        return {
            "naming_style": preferences.get("naming_style", "snake_case"),
            "documentation_style": preferences.get("documentation_style", "google"),
            "code_structure": preferences.get("code_structure", "modular"),
            "preferences": preferences,
        }

    def _get_timestamp(self) -> str:
        """Get current timestamp."""
        from datetime import datetime
        return datetime.now().isoformat()

    def _generate_learning_summary(self, pattern: Dict[str, Any]) -> str:
        """Generate learning summary."""
        pattern_type = pattern.get("type", "unknown")
        return f"Learned {pattern_type} pattern from correction"

    def _generate_adaptation_summary(self, patterns: Dict[str, Any]) -> str:
        """Generate adaptation summary."""
        count = len(patterns)
        return f"Adapted to {count} project-specific patterns"

    def _generate_preference_summary(self, preferences: Dict[str, Any]) -> str:
        """Generate preference summary."""
        count = sum(len(v) for v in preferences.values())
        return f"Learned {count} style preferences"

    def _generate_review_learning_summary(self, patterns: Dict[str, Any]) -> str:
        """Generate review learning summary."""
        count = len(patterns)
        return f"Learned {count} patterns from code review"

    def _generate_team_adaptation_summary(self, conventions: Dict[str, Any]) -> str:
        """Generate team adaptation summary."""
        count = sum(len(v) for v in conventions.values())
        return f"Adapted to {count} team conventions"

    def _generate_personalization_summary(self, profile: Dict[str, Any]) -> str:
        """Generate personalization summary."""
        return f"Personalization profile created with {len(profile.get('preferences', {}))} preferences"


# AST Visitor classes

class StructureVisitor(ast.NodeVisitor):
    """Visitor to extract code structure."""
    
    def __init__(self):
        self.functions = []
        self.classes = []

    def visit_FunctionDef(self, node: ast.FunctionDef):
        self.functions.append(node.name)
        self.generic_visit(node)

    def visit_ClassDef(self, node: ast.ClassDef):
        self.classes.append(node.name)
        self.generic_visit(node)


class PatternExtractor(ast.NodeVisitor):
    """Visitor to extract code patterns."""
    
    def __init__(self, pattern_type: str):
        self.pattern_type = pattern_type
        self.pattern = {
            "type": pattern_type,
            "features": {},
        }

    def visit(self, node: ast.AST):
        self.generic_visit(node)


class ProjectPatternVisitor(ast.NodeVisitor):
    """Visitor to analyze project patterns."""
    
    def __init__(self):
        self.naming_patterns = {}
        self.structure_patterns = {}

    def visit_FunctionDef(self, node: ast.FunctionDef):
        # Analyze naming
        if node.name:
            self.naming_patterns[node.name] = "function"
        self.generic_visit(node)


class StyleFeatureVisitor(ast.NodeVisitor):
    """Visitor to extract style features."""
    
    def __init__(self):
        self.naming_patterns = {}
        self.formatting_patterns = {}

    def visit_FunctionDef(self, node: ast.FunctionDef):
        # Analyze naming style
        if "_" in node.name:
            self.naming_patterns["style"] = "snake_case"
        elif node.name and node.name[0].isupper():
            self.naming_patterns["style"] = "PascalCase"
        self.generic_visit(node)


class ConventionVisitor(ast.NodeVisitor):
    """Visitor to analyze coding conventions."""
    
    def __init__(self):
        self.naming_conventions = {}
        self.formatting_conventions = {}

    def visit_FunctionDef(self, node: ast.FunctionDef):
        if node.name:
            self.naming_conventions[node.name] = "function"
        self.generic_visit(node)
