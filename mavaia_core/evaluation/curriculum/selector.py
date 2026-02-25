from __future__ import annotations
"""
Curriculum Selector

Interactive menu system and programmatic API for selecting test parameters.
"""

import json
from pathlib import Path
from typing import Dict, List, Optional

from mavaia_core.evaluation.curriculum.models import (
    TestConfiguration,
    OptionalConstraints,
    MemoryContinuityMode,
    SafetyPosture,
)


class CurriculumSelector:
    """Selects curriculum test configurations"""
    
    def __init__(self, metadata_dir: Optional[Path] = None):
        """
        Initialize curriculum selector
        
        Args:
            metadata_dir: Directory containing metadata files
        """
        if metadata_dir is None:
            metadata_dir = Path(__file__).parent / "data" / "metadata"
        self.metadata_dir = Path(metadata_dir)
        
        self.levels = self._load_metadata("levels.json")
        self.subjects = self._load_metadata("subjects.json")
        self.skill_types = self._load_metadata("skill_types.json")
        self.difficulty_styles = self._load_metadata("difficulty_styles.json")
    
    def _load_metadata(self, filename: str) -> List[Dict]:
        """Load metadata from JSON file"""
        filepath = self.metadata_dir / filename
        if not filepath.exists():
            return []
        
        with open(filepath, "r", encoding="utf-8") as f:
            data = json.load(f)
            # Extract list from data (handle different structures)
            if isinstance(data, list):
                return data
            elif isinstance(data, dict):
                # Try common keys
                for key in ["levels", "subjects", "skill_types", "difficulty_styles"]:
                    if key in data:
                        return data[key]
                return []
            return []
    
    def list_levels(self) -> List[str]:
        """List available education levels"""
        return [level["id"] for level in self.levels]
    
    def list_subjects(self, level: Optional[str] = None) -> List[str]:
        """List available subjects"""
        return [subject["id"] for subject in self.subjects]
    
    def list_skill_types(self) -> List[str]:
        """List available skill types"""
        return [skill["id"] for skill in self.skill_types]
    
    def list_difficulty_styles(self) -> List[str]:
        """List available difficulty styles"""
        return [difficulty["id"] for difficulty in self.difficulty_styles]
    
    def select_curriculum(
        self,
        level: Optional[str] = None,
        subject: Optional[str] = None,
        skill_type: Optional[str] = None,
        difficulty_style: Optional[str] = None,
        constraints: Optional[OptionalConstraints] = None,
        test_id: Optional[str] = None,
    ) -> TestConfiguration:
        """
        Select curriculum configuration
        
        Args:
            level: Education level
            subject: Subject domain
            skill_type: Skill type
            difficulty_style: Difficulty style
            constraints: Optional constraints
            test_id: Specific test ID (optional)
        
        Returns:
            TestConfiguration object
        
        Raises:
            ValueError: If invalid selection
        """
        # Validate selections
        if level and level not in self.list_levels():
            raise ValueError(f"Invalid level: {level}. Must be one of {self.list_levels()}")
        
        if subject and subject not in self.list_subjects():
            raise ValueError(f"Invalid subject: {subject}. Must be one of {self.list_subjects()}")
        
        if skill_type and skill_type not in self.list_skill_types():
            raise ValueError(f"Invalid skill_type: {skill_type}. Must be one of {self.list_skill_types()}")
        
        if difficulty_style and difficulty_style not in self.list_difficulty_styles():
            raise ValueError(f"Invalid difficulty_style: {difficulty_style}. Must be one of {self.list_difficulty_styles()}")
        
        # Use defaults if not provided
        if not level:
            level = self.list_levels()[0]
        if not subject:
            subject = self.list_subjects()[0]
        if not skill_type:
            skill_type = self.list_skill_types()[0]
        if not difficulty_style:
            difficulty_style = self.list_difficulty_styles()[0]
        
        if constraints is None:
            constraints = OptionalConstraints()
        
        return TestConfiguration(
            level=level,
            subject=subject,
            skill_type=skill_type,
            difficulty_style=difficulty_style,
            constraints=constraints,
            test_id=test_id,
        )
    
    def select_interactive(self) -> TestConfiguration:
        """
        Interactive menu for curriculum selection
        
        Returns:
            TestConfiguration object
        """
        try:
            from rich.console import Console
            from rich.prompt import Prompt, Confirm
            from rich.table import Table
            
            console = Console()
            console.print("\n[bold blue]Cognitive Curriculum Selector[/bold blue]\n")
            
            # Select level
            level_table = Table(title="Select Education Level")
            level_table.add_column("ID", style="cyan")
            level_table.add_column("Name", style="magenta")
            level_table.add_column("Description", style="green")
            
            for level in self.levels:
                level_table.add_row(
                    level["id"],
                    level.get("name", level["id"]),
                    level.get("description", ""),
                )
            
            console.print(level_table)
            level = Prompt.ask("Select level", choices=self.list_levels(), default=self.list_levels()[0])
            
            # Select subject
            subject_table = Table(title="Select Subject")
            subject_table.add_column("ID", style="cyan")
            subject_table.add_column("Name", style="magenta")
            subject_table.add_column("Description", style="green")
            
            for subject in self.subjects:
                subject_table.add_row(
                    subject["id"],
                    subject.get("name", subject["id"]),
                    subject.get("description", ""),
                )
            
            console.print(subject_table)
            subject = Prompt.ask("Select subject", choices=self.list_subjects(), default=self.list_subjects()[0])
            
            # Select skill type
            skill_table = Table(title="Select Skill Type")
            skill_table.add_column("ID", style="cyan")
            skill_table.add_column("Name", style="magenta")
            skill_table.add_column("Description", style="green")
            
            for skill in self.skill_types:
                skill_table.add_row(
                    skill["id"],
                    skill.get("name", skill["id"]),
                    skill.get("description", ""),
                )
            
            console.print(skill_table)
            skill_type = Prompt.ask("Select skill type", choices=self.list_skill_types(), default=self.list_skill_types()[0])
            
            # Select difficulty style
            difficulty_table = Table(title="Select Difficulty Style")
            difficulty_table.add_column("ID", style="cyan")
            difficulty_table.add_column("Name", style="magenta")
            difficulty_table.add_column("Description", style="green")
            
            for difficulty in self.difficulty_styles:
                difficulty_table.add_row(
                    difficulty["id"],
                    difficulty.get("name", difficulty["id"]),
                    difficulty.get("description", ""),
                )
            
            console.print(difficulty_table)
            difficulty_style = Prompt.ask(
                "Select difficulty style",
                choices=self.list_difficulty_styles(),
                default=self.list_difficulty_styles()[0]
            )
            
            # Optional constraints
            constraints = OptionalConstraints()
            
            if Confirm.ask("\nConfigure optional constraints?", default=False):
                # Time bound
                if Confirm.ask("Set time bound?", default=False):
                    time_bound = Prompt.ask("Time bound (seconds)", default="60.0")
                    try:
                        constraints.time_bound = float(time_bound)
                    except ValueError:
                        pass
                
                # Token bound
                if Confirm.ask("Set token bound?", default=False):
                    token_bound = Prompt.ask("Token bound", default="1000")
                    try:
                        constraints.token_bound = int(token_bound)
                    except ValueError:
                        pass
                
                # Memory continuity
                if Confirm.ask("Configure memory continuity?", default=False):
                    memory_options = [mode.value for mode in MemoryContinuityMode]
                    memory_choice = Prompt.ask(
                        "Memory continuity mode",
                        choices=memory_options,
                        default=MemoryContinuityMode.OFF.value
                    )
                    constraints.memory_continuity = MemoryContinuityMode(memory_choice)
                
                # Safety posture
                if Confirm.ask("Configure safety posture?", default=False):
                    safety_options = [mode.value for mode in SafetyPosture]
                    safety_choice = Prompt.ask(
                        "Safety posture",
                        choices=safety_options,
                        default=SafetyPosture.NORMAL.value
                    )
                    constraints.safety_posture = SafetyPosture(safety_choice)
                
                # Tool usage
                constraints.tool_usage_allowed = Confirm.ask("Allow tool usage?", default=True)
                
                # Bias probes
                constraints.bias_probes = Confirm.ask("Enable bias probes?", default=False)
                
                # Breakdown explanation
                constraints.breakdown_explanation_required = Confirm.ask(
                    "Require breakdown explanation?",
                    default=False
                )
                
                # MCTS depth
                if Confirm.ask("Set MCTS depth limit?", default=False):
                    mcts_depth = Prompt.ask("MCTS depth", default="10")
                    try:
                        constraints.mcts_depth = int(mcts_depth)
                    except ValueError:
                        pass
            
            # Preview configuration
            console.print("\n[bold green]Configuration Preview:[/bold green]")
            console.print(f"Level: {level}")
            console.print(f"Subject: {subject}")
            console.print(f"Skill Type: {skill_type}")
            console.print(f"Difficulty Style: {difficulty_style}")
            console.print(f"Constraints: {constraints.model_dump()}")
            
            if Confirm.ask("\nProceed with this configuration?", default=True):
                return TestConfiguration(
                    level=level,
                    subject=subject,
                    skill_type=skill_type,
                    difficulty_style=difficulty_style,
                    constraints=constraints,
                )
            else:
                return self.select_interactive()  # Retry
        
        except ImportError:
            # Fallback to simple input if rich is not available
            print("\nCognitive Curriculum Selector\n")
            print("Available levels:", ", ".join(self.list_levels()))
            level = input(f"Select level [{self.list_levels()[0]}]: ").strip() or self.list_levels()[0]
            
            print("\nAvailable subjects:", ", ".join(self.list_subjects()))
            subject = input(f"Select subject [{self.list_subjects()[0]}]: ").strip() or self.list_subjects()[0]
            
            print("\nAvailable skill types:", ", ".join(self.list_skill_types()))
            skill_type = input(f"Select skill type [{self.list_skill_types()[0]}]: ").strip() or self.list_skill_types()[0]
            
            print("\nAvailable difficulty styles:", ", ".join(self.list_difficulty_styles()))
            difficulty_style = input(
                f"Select difficulty style [{self.list_difficulty_styles()[0]}]: "
            ).strip() or self.list_difficulty_styles()[0]
            
            constraints = OptionalConstraints()
            
            return TestConfiguration(
                level=level,
                subject=subject,
                skill_type=skill_type,
                difficulty_style=difficulty_style,
                constraints=constraints,
            )

