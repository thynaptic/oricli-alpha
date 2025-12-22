"""
Base Data Source Interface

Abstract base class for all curriculum test data sources.
"""

from abc import ABC, abstractmethod
from typing import Any, Dict, Iterator, Optional


class BaseDataSource(ABC):
    """Base class for curriculum test data sources"""
    
    @abstractmethod
    def stream_questions(
        self,
        level: str,
        subject: str,
        skill_type: Optional[str] = None,
        difficulty_style: Optional[str] = None,
        limit: Optional[int] = None,
    ) -> Iterator[Dict[str, Any]]:
        """
        Stream questions matching criteria
        
        Args:
            level: Education level (k5, middle_school, high_school, undergrad, grad, phd)
            subject: Subject domain (math, language, science, logic, etc.)
            skill_type: Skill type filter (optional)
            difficulty_style: Difficulty style filter (optional)
            limit: Maximum number of questions to return (optional)
        
        Yields:
            Question dictionaries matching the curriculum format
        """
        pass
    
    @abstractmethod
    def get_source_name(self) -> str:
        """
        Return source identifier
        
        Returns:
            Source name string
        """
        pass
    
    @abstractmethod
    def supports_filtering(self) -> bool:
        """
        Whether source supports filtering by criteria
        
        Returns:
            True if source can filter by level/subject/skill/difficulty
        """
        pass
    
    def transform_question(
        self,
        raw_question: Dict[str, Any],
        field_mapping: Optional[Dict[str, str]] = None,
    ) -> Dict[str, Any]:
        """
        Transform raw question to curriculum format
        
        Args:
            raw_question: Raw question from source
            field_mapping: Optional field mapping dictionary
        
        Returns:
            Transformed question in curriculum format
        """
        if field_mapping:
            # Apply field mapping
            transformed = {}
            for target_field, source_field in field_mapping.items():
                if source_field in raw_question:
                    transformed[target_field] = raw_question[source_field]
            # Copy any unmapped fields
            for key, value in raw_question.items():
                if key not in field_mapping.values():
                    transformed[key] = value
            return transformed
        return raw_question

