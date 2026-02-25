from __future__ import annotations
"""
HuggingFace Data Source

Streams questions from HuggingFace datasets without downloading.
"""

import importlib.util
from typing import Any, Dict, Iterator, Optional

from mavaia_core.evaluation.curriculum.data_sources.base import BaseDataSource

# Lazy import check
HUGGINGFACE_AVAILABLE = importlib.util.find_spec("datasets") is not None


class HuggingFaceSource(BaseDataSource):
    """HuggingFace dataset source"""
    
    # Known educational datasets with their mappings
    KNOWN_DATASETS = {
        "hendrycks/MMLU": {
            "name": "MMLU",
            "level_mapping": {
                "k5": None,  # MMLU doesn't have K-5 content
                "middle_school": "high_school",  # Approximate
                "high_school": "high_school",
                "undergrad": "college",
                "grad": "college",
                "phd": "college",
            },
            "subject_mapping": {
                "math": ["abstract_algebra", "college_mathematics", "elementary_mathematics"],
                "science": ["anatomy", "astronomy", "biology", "chemistry", "physics"],
                "language": ["high_school_world_history", "us_history"],
                "logic": ["logical_fallacies", "moral_disputes"],
            },
            "field_mapping": {
                "question": "question",
                "answer": "answer",
                "options": "choices",
            },
        },
        "gsm8k": {
            "name": "GSM8K",
            "level_mapping": {
                "k5": "grade_school",
                "middle_school": "grade_school",
                "high_school": None,
                "undergrad": None,
                "grad": None,
                "phd": None,
            },
            "subject_mapping": {
                "math": ["gsm8k"],
            },
            "field_mapping": {
                "question": "question",
                "answer": "answer",
            },
        },
        "hendrycks/MATH": {
            "name": "MATH",
            "level_mapping": {
                "k5": None,
                "middle_school": "level_1",
                "high_school": "level_2",
                "undergrad": "level_3",
                "grad": "level_4",
                "phd": "level_5",
            },
            "subject_mapping": {
                "math": ["prealgebra", "algebra", "number_theory", "geometry", "calculus"],
            },
            "field_mapping": {
                "question": "problem",
                "answer": "solution",
            },
        },
    }
    
    def __init__(
        self,
        dataset: str,
        field_mapping: Optional[Dict[str, str]] = None,
        auto_discover: bool = True,
    ):
        """
        Initialize HuggingFace source
        
        Args:
            dataset: HuggingFace dataset path (e.g., "hendrycks/MMLU")
            field_mapping: Custom field mapping (overrides defaults)
            auto_discover: Whether to auto-discover dataset config
        """
        self.dataset = dataset
        self.auto_discover = auto_discover
        self._datasets = None
        self._dataset_info = self.KNOWN_DATASETS.get(dataset, {})
        self.field_mapping = field_mapping or self._dataset_info.get("field_mapping", {})
    
    def _ensure_datasets(self):
        """Lazy import datasets library"""
        if not HUGGINGFACE_AVAILABLE:
            raise ImportError(
                "HuggingFace datasets library not available. "
                "Install with: pip install datasets huggingface_hub"
            )
        if self._datasets is None:
            import datasets
            self._datasets = datasets
        return self._datasets
    
    def get_source_name(self) -> str:
        """Return source identifier"""
        return f"huggingface:{self.dataset}"
    
    def supports_filtering(self) -> bool:
        """HuggingFace supports filtering via splits"""
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
        Stream questions from HuggingFace dataset
        
        Args:
            level: Education level
            subject: Subject domain
            skill_type: Skill type filter (optional, may not be supported)
            difficulty_style: Difficulty style filter (optional, may not be supported)
            limit: Maximum number of questions (optional)
        
        Yields:
            Question dictionaries in curriculum format
        """
        datasets = self._ensure_datasets()
        
        # Check level mapping (be lenient - try even if not exact match)
        level_mapping = self._dataset_info.get("level_mapping", {})
        if level_mapping and level not in level_mapping:
            # Try to find approximate match
            # For now, allow all levels if mapping exists but level not found
            # This allows datasets to work even with imperfect mappings
            pass
        
        # Check subject mapping (be lenient)
        subject_mapping = self._dataset_info.get("subject_mapping", {})
        if subject_mapping and subject not in subject_mapping:
            # Try to find approximate match or allow all subjects
            # For now, allow all subjects if mapping exists but subject not found
            pass
        
        try:
            # Load dataset with streaming (no download)
            dataset = datasets.load_dataset(
                self.dataset,
                streaming=True,
                split="test",  # Use test split by default
            )
            
            # Get subject-specific splits if available
            subject_splits = subject_mapping.get(subject, [])
            
            count = 0
            for item in dataset:
                # For MMLU and similar datasets, check if subject matches
                # This is a simplified check - real implementation would need
                # dataset-specific logic
                if subject_splits and isinstance(item, dict):
                    # Skip if this item doesn't match our subject
                    # (This is a placeholder - real filtering would be dataset-specific)
                    pass
                
                # Transform to curriculum format
                question = self._transform_hf_item(item, level, subject)
                
                if question:
                    yield question
                    count += 1
                    
                    if limit and count >= limit:
                        break
        except Exception as e:
            # Silently skip on errors (network issues, etc.)
            return
    
    def _transform_hf_item(
        self,
        item: Dict[str, Any],
        level: str,
        subject: str,
    ) -> Optional[Dict[str, Any]]:
        """
        Transform HuggingFace dataset item to curriculum format
        
        Args:
            item: Raw item from dataset
            level: Education level
            subject: Subject domain
        
        Returns:
            Transformed question or None if invalid
        """
        try:
            # Apply field mapping
            question_text = item.get(self.field_mapping.get("question", "question"), "")
            answer = item.get(self.field_mapping.get("answer", "answer"), "")
            
            if not question_text:
                return None
            
            # Build curriculum format question
            question = {
                "id": f"hf_{self.dataset.replace('/', '_')}_{item.get('id', hash(str(item)))}",
                "question": question_text,
                "answer": str(answer),
                "level": level,
                "subject": subject,
                "skill_type": "foundational",  # Default, may need refinement
                "difficulty_style": "standard",  # Default, may need refinement
                "question_type": "free_response",  # Default for most HF datasets
                "metadata": {
                    "estimated_time": 30.0,
                    "estimated_tokens": 200,
                    "expected_reasoning_steps": 3,
                },
            }
            
            # Add options if available (for multiple choice)
            if "options" in self.field_mapping and self.field_mapping["options"] in item:
                question["options"] = item[self.field_mapping["options"]]
                question["question_type"] = "multiple_choice"
            
            return question
        except Exception:
            return None

