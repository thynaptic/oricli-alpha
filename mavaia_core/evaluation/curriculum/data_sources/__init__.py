"""
Data Sources for Curriculum Testing

Provides remote data sources for streaming test questions without downloading to disk.
"""

from mavaia_core.evaluation.curriculum.data_sources.base import BaseDataSource
from mavaia_core.evaluation.curriculum.data_sources.manager import DataSourceManager
from mavaia_core.evaluation.curriculum.data_sources.local_source import LocalSource
from mavaia_core.evaluation.curriculum.data_sources.huggingface_source import HuggingFaceSource
from mavaia_core.evaluation.curriculum.data_sources.url_source import URLSource

__all__ = [
    "BaseDataSource",
    "DataSourceManager",
    "LocalSource",
    "HuggingFaceSource",
    "URLSource",
]

