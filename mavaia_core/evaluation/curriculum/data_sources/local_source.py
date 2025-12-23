"""
Local File Data Source

Fallback source for reading from local JSON files.
"""

import json
from pathlib import Path
from typing import Any, Dict, Iterator, Optional

from mavaia_core.evaluation.curriculum.data_sources.base import BaseDataSource


class LocalSource(BaseDataSource):
    """Local file-based data source (fallback)"""
    
    def __init__(self, data_dir: Optional[Path] = None):
        """
        Initialize local source
        
        Args:
            data_dir: Directory containing level/subject JSON files
        """
        if data_dir is None:
            data_dir = Path(__file__).parent.parent / "data"
        self.data_dir = Path(data_dir)
    
    def get_source_name(self) -> str:
        """Return source identifier"""
        return "local"
    
    def supports_filtering(self) -> bool:
        """Local source supports filtering"""
        return True
    
    def stream_questions(
        self,
        level: str,
        subject: str,
        skill_type: Optional[str] = None,
        difficulty_style: Optional[str] = None,
        limit: Optional[int] = None,
    ) -> Iterator[Dict[str, Any]]:
        """
        Stream questions from local JSON files
        
        Args:
            level: Education level
            subject: Subject domain
            skill_type: Skill type filter (optional)
            difficulty_style: Difficulty style filter (optional)
            limit: Maximum number of questions (optional)
        
        Yields:
            Question dictionaries
        """
        question_file = self.data_dir / "levels" / level / f"{subject}.json"
        
        if not question_file.exists():
            return
        
        try:
            with open(question_file, "r", encoding="utf-8") as f:
                data = json.load(f)
                questions = data.get("questions", [])
                
                count = 0
                for question in questions:
                    # Filter by skill_type and difficulty_style if specified
                    # Be lenient - if skill_type/difficulty_style not in question, allow it
                    if skill_type and question.get("skill_type") and question.get("skill_type") != skill_type:
                        continue
                    if difficulty_style and question.get("difficulty_style") and question.get("difficulty_style") != difficulty_style:
                        continue
                    
                    # Ensure question has required fields
                    if not question.get("question"):
                        continue
                    
                    # Ensure question has default values for missing fields
                    if "skill_type" not in question:
                        question["skill_type"] = skill_type or "foundational"
                    if "difficulty_style" not in question:
                        question["difficulty_style"] = difficulty_style or "standard"
                    if "question_type" not in question:
                        question["question_type"] = "free_response"
                    if "metadata" not in question:
                        question["metadata"] = {}
                    
                    yield question
                    count += 1
                    
                    if limit and count >= limit:
                        break
        except (json.JSONDecodeError, IOError) as e:
            # Silently skip invalid files
            return

