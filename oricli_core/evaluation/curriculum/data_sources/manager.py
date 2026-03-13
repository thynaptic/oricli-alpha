from __future__ import annotations
"""
Data Source Manager

Central registry and orchestration for all data sources.
"""

from typing import Any, Dict, Iterator, List, Optional

from oricli_core.evaluation.curriculum.data_sources.base import BaseDataSource
from oricli_core.evaluation.curriculum.data_sources.config import DataSourceConfig, SourceConfig
from oricli_core.evaluation.curriculum.data_sources.huggingface_source import HuggingFaceSource
from oricli_core.evaluation.curriculum.data_sources.local_source import LocalSource
from oricli_core.evaluation.curriculum.data_sources.url_source import URLSource


class DataSourceManager:
    """Manager for all data sources"""
    
    def __init__(self, config_path: Optional[str] = None):
        """
        Initialize data source manager
        
        Args:
            config_path: Path to configuration file (optional)
        """
        self.config = DataSourceConfig(config_path)
        self.sources: Dict[str, BaseDataSource] = {}
        self._initialize_sources()
    
    def _initialize_sources(self) -> None:
        """Initialize all configured sources"""
        # Add local source as fallback (always available, fast)
        local_source = LocalSource()
        self.sources["local"] = local_source
        
        # Add configured sources (skip HuggingFace initially to avoid slow imports)
        for source_config in self.config.get_sources():
            # Skip HuggingFace sources on initial load - they can be slow
            if source_config.type.lower() == "huggingface":
                continue
            try:
                source = self._create_source(source_config)
                if source:
                    self.sources[source.get_source_name()] = source
            except Exception:
                # Skip sources that fail to initialize
                continue
    
    def _create_source(self, config: SourceConfig) -> Optional[BaseDataSource]:
        """
        Create a data source from configuration
        
        Args:
            config: Source configuration
        
        Returns:
            Data source instance or None
        """
        source_type = config.type.lower()
        
        if source_type == "local":
            data_dir = config.config.get("path")
            return LocalSource(data_dir)
        
        elif source_type == "huggingface":
            dataset = config.config.get("dataset")
            if not dataset:
                return None
            field_mapping = config.config.get("field_mapping")
            auto_discover = config.config.get("auto_discover", True)
            return HuggingFaceSource(
                dataset=dataset,
                field_mapping=field_mapping,
                auto_discover=auto_discover,
            )
        
        elif source_type == "url":
            url = config.config.get("url")
            if not url:
                return None
            name = config.config.get("name", url)
            auth = config.config.get("auth")
            field_mapping = config.config.get("field_mapping")
            method = config.config.get("method", "GET")
            headers = config.config.get("headers")
            return URLSource(
                url=url,
                name=name,
                auth=auth,
                field_mapping=field_mapping,
                method=method,
                headers=headers,
            )
        
        return None
    
    def get_source(self, source_name: Optional[str] = None) -> Optional[BaseDataSource]:
        """
        Get a specific source by name
        
        Args:
            source_name: Source name (None for default/auto)
        
        Returns:
            Data source instance or None
        """
        if source_name:
            return self.sources.get(source_name)
        
        # Return first non-local source, or local as fallback
        for name, source in self.sources.items():
            if name != "local":
                return source
        return self.sources.get("local")
    
    def list_sources(self) -> List[str]:
        """
        List all available source names
        
        Returns:
            List of source names
        """
        return list(self.sources.keys())
    
    def stream_questions(
        self,
        level: str,
        subject: str,
        skill_type: Optional[str] = None,
        difficulty_style: Optional[str] = None,
        limit: Optional[int] = None,
        source_name: Optional[str] = None,
    ) -> Iterator[Dict[str, Any]]:
        """
        Stream questions from available sources
        
        Args:
            level: Education level
            subject: Subject domain
            skill_type: Skill type filter (optional)
            difficulty_style: Difficulty style filter (optional)
            limit: Maximum number of questions (optional)
            source_name: Specific source to use (None for auto)
        
        Yields:
            Question dictionaries
        """
        # Try specified source first
        if source_name:
            source = self.get_source(source_name)
            if source:
                yield from source.stream_questions(
                    level=level,
                    subject=subject,
                    skill_type=skill_type,
                    difficulty_style=difficulty_style,
                    limit=limit,
                )
            return
        
        # Try all sources in order (skip local unless it's the only one)
        sources_tried = 0
        for name, source in self.sources.items():
            if name == "local" and len(self.sources) > 1:
                # Skip local if we have other sources
                continue
            
            try:
                count = 0
                for question in source.stream_questions(
                    level=level,
                    subject=subject,
                    skill_type=skill_type,
                    difficulty_style=difficulty_style,
                    limit=limit,
                ):
                    yield question
                    count += 1
                    if limit and count >= limit:
                        return
                
                # If we got questions from this source, we're done
                if count > 0:
                    return
            except Exception:
                # Try next source on error
                continue
            
            sources_tried += 1
        
        # If no sources worked, try local as last resort
        if sources_tried > 0:
            local_source = self.sources.get("local")
            if local_source:
                yield from local_source.stream_questions(
                    level=level,
                    subject=subject,
                    skill_type=skill_type,
                    difficulty_style=difficulty_style,
                    limit=limit,
                )
    
    def get_question(
        self,
        level: str,
        subject: str,
        skill_type: Optional[str] = None,
        difficulty_style: Optional[str] = None,
        source_name: Optional[str] = None,
    ) -> Optional[Dict[str, Any]]:
        """
        Get a single question matching criteria
        
        Args:
            level: Education level
            subject: Subject domain
            skill_type: Skill type filter (optional)
            difficulty_style: Difficulty style filter (optional)
            source_name: Specific source to use (None for auto)
        
        Returns:
            Question dictionary or None
        """
        # Try with filters first
        for question in self.stream_questions(
            level=level,
            subject=subject,
            skill_type=skill_type,
            difficulty_style=difficulty_style,
            limit=1,
            source_name=source_name,
        ):
            return question
        
        # If no match with filters, try without filters (more lenient)
        if skill_type or difficulty_style:
            for question in self.stream_questions(
                level=level,
                subject=subject,
                skill_type=None,
                difficulty_style=None,
                limit=1,
                source_name=source_name,
            ):
                # Apply filters manually if question has those fields
                if skill_type and question.get("skill_type") and question.get("skill_type") != skill_type:
                    continue
                if difficulty_style and question.get("difficulty_style") and question.get("difficulty_style") != difficulty_style:
                    continue
                return question
        
        return None

