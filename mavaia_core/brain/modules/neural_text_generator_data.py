import os
import sys
import json
import random
import time
import re
import hashlib
import logging
from abc import ABC, abstractmethod
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple, Union
from datetime import datetime

from mavaia_core.exceptions import InvalidParameterError

logger = logging.getLogger(__name__)

# Try to import Internet Archive support
try:
    from internetarchive import search_items, get_item, download
    INTERNETARCHIVE_AVAILABLE = True
except ImportError:
    INTERNETARCHIVE_AVAILABLE = False

def is_huggingface_available():
    """Check if HuggingFace libraries are available dynamically"""
    try:
        from datasets import load_dataset
        import huggingface_hub
        return True
    except ImportError:
        return False

class BaseDataSource(ABC):
    """
    Abstract base class for data sources
    All data sources must implement this interface
    """

    @abstractmethod
    def get_source_name(self) -> str:
        """Return the name of this data source"""
        pass

    @abstractmethod
    def load_data(
        self,
        book_ids: Optional[List[Any]] = None,
        max_books: int = 3,
        categories: Optional[List[str]] = None,
        max_text_size: Optional[int] = None,
        data_dir: Optional[Path] = None,
        search: Optional[str] = None,
    ) -> Optional[str]:
        """Load data from the source"""
        pass

    def load_preferences(
        self,
        book_ids: Optional[List[Any]] = None,
        max_items: int = 1000,
        data_dir: Optional[Path] = None,
    ) -> List[Dict[str, str]]:
        """Load preference data (prompt, chosen, rejected) for DPO"""
        return []

    def _get_cache_dir(self, data_dir: Optional[Path], source_name: str) -> Path:
        """Get or create cache directory for a data source"""
        if data_dir is None:
            data_dir = Path(__file__).parent.parent.parent / "data"
        
        cache_dir = data_dir / source_name
        cache_dir.mkdir(parents=True, exist_ok=True)
        return cache_dir

    def preprocess_text(self, text: str, lowercase: bool = True, remove_special: bool = True) -> str:
        """Standard text preprocessing"""
        if not text:
            return ""
            
        if lowercase:
            text = text.lower()
            
        if remove_special:
            # Keep alphanumeric, common punctuation, and spaces
            text = re.sub(r'[^a-z0-9\s.,!?\'"-]', ' ', text)
            # Normalize whitespace
            text = re.sub(r'\s+', ' ', text)
            
        return text.strip()

class GutenbergSource(BaseDataSource):
    """Project Gutenberg data source"""

    def get_source_name(self) -> str:
        return "gutenberg"

    def load_data(
        self,
        book_ids: Optional[List[Any]] = None,
        max_books: int = 3,
        categories: Optional[List[str]] = None,
        max_text_size: Optional[int] = None,
        data_dir: Optional[Path] = None,
        search: Optional[str] = None,
    ) -> Optional[str]:
        """Load Project Gutenberg books"""
        cache_dir = self._get_cache_dir(data_dir, "gutenberg")
        all_text = []
        
        if book_ids:
            for book_id in book_ids[:max_books]:
                book_path = cache_dir / f"{book_id}.txt"
                if book_path.exists():
                    try:
                        with open(book_path, "r", encoding="utf-8") as f:
                            all_text.append(f.read())
                    except Exception:
                        pass
        
        return "\n\n".join(all_text) if all_text else None

class WikipediaSource(BaseDataSource):
    """Wikipedia data source"""

    def get_source_name(self) -> str:
        return "wikipedia"

    def load_data(
        self,
        book_ids: Optional[List[Any]] = None,
        max_books: int = 3,
        categories: Optional[List[str]] = None,
        max_text_size: Optional[int] = None,
        data_dir: Optional[Path] = None,
        search: Optional[str] = None,
    ) -> Optional[str]:
        return None

class HuggingFaceSource(BaseDataSource):
    """HuggingFace datasets data source"""

    def __init__(self):
        self._datasets = None
        self._api = None

    def get_source_name(self) -> str:
        return "huggingface"

    def _setup_huggingface_auth(self):
        """Setup HuggingFace authentication from API keys"""
        try:
            from huggingface_hub import login, HfApi
            api_keys = _load_api_keys()
            token = os.environ.get("HF_TOKEN") or api_keys.get("huggingface")
            if token:
                login(token=token, add_to_git_credential=False)
                self._api = HfApi()
                return True
        except ImportError:
            pass
        return False

    def _extract_text_recursive(self, value: Any) -> List[str]:
        """Recursively extract text from nested structures"""
        parts = []
        if isinstance(value, str):
            text = value.strip()
            if text:
                parts.append(text)
        elif isinstance(value, list):
            for item in value:
                parts.extend(self._extract_text_recursive(item))
        elif isinstance(value, dict):
            # Prioritize common text keys
            for k in ["value", "text", "content", "message", "output"]:
                if k in value:
                    parts.extend(self._extract_text_recursive(value[k]))
                    return parts # Only take the first found key to avoid duplicates
            # Otherwise, try all values
            for v in value.values():
                parts.extend(self._extract_text_recursive(v))
        return parts

    def _load_dataset_text(self, dataset_name: str, cache_file: Path, max_text_size: Optional[int] = None) -> Optional[str]:
        """Load and extract text from a HF dataset"""
        if not is_huggingface_available():
            return None
            
        try:
            from datasets import load_dataset
            
            dataset_id = dataset_name
            dataset_filter = None
            dataset_config = None
            
            if "::" in dataset_name:
                dataset_id, dataset_config = dataset_name.split("::", 1)
            elif ":" in dataset_name and "://" not in dataset_name:
                parts = dataset_name.split(":")
                if len(parts) == 2:
                    dataset_id, dataset_config = parts
                elif len(parts) == 3:
                    dataset_id = ":".join(parts[:2])
                    dataset_config = parts[2]

            dataset = None
            try:
                if dataset_config:
                    logger.info(f"Loading HF dataset '{dataset_id}' [config={dataset_config}]...")
                    dataset = load_dataset(dataset_id, dataset_config, split="train", streaming=False)
                else:
                    logger.info(f"Loading HF dataset '{dataset_id}'...")
                    dataset = load_dataset(dataset_id, split="train", streaming=False)
            except Exception as e:
                if dataset_config:
                    try:
                        logger.info(f"Retrying '{dataset_id}' as filter...")
                        dataset = load_dataset(dataset_id, split="train", streaming=False)
                        dataset_filter = dataset_config
                    except Exception:
                        return None
                else:
                    return None
            
            if dataset is None:
                return None
            
            if dataset_filter:
                filter_col = None
                for col in dataset.column_names:
                    sample_size = min(100, len(dataset))
                    if any(str(dataset[i].get(col)) == dataset_filter for i in range(sample_size)):
                        filter_col = col
                        break
                if filter_col:
                    dataset = dataset.filter(lambda x: str(x[filter_col]) == dataset_filter)
            
            all_text = []
            text_columns = ["text", "content", "conversations", "conversation", "message", "messages", "article", "body"]
            
            text_column = None
            for col in text_columns:
                if col in dataset.column_names:
                    text_column = col
                    break
            
            if not text_column:
                for col in dataset.column_names:
                    if len(dataset) > 0:
                        val = dataset[0].get(col)
                        if isinstance(val, (str, list, dict)):
                            text_column = col
                            break
            
            if not text_column:
                return None
            
            logger.info(f"Extracting from column '{text_column}'...")
            
            for idx, example in enumerate(dataset):
                if text_column in example:
                    parts = self._extract_text_recursive(example[text_column])
                    if parts:
                        all_text.append("\n".join(parts))
                
                if max_text_size and sum(len(t) for t in all_text) >= max_text_size:
                    break
            
            if not all_text:
                return None
                
            combined = "\n\n".join(all_text)
            try:
                cache_file.write_text(combined, encoding="utf-8")
            except Exception:
                pass
            return combined

        except Exception as e:
            logger.error(f"Error in _load_dataset_text: {e}", exc_info=True)
            return None

    def load_preferences(
        self,
        book_ids: Optional[List[Any]] = None,
        max_items: int = 1000,
        data_dir: Optional[Path] = None,
    ) -> List[Dict[str, str]]:
        """Load preference data from HuggingFace"""
        if not is_huggingface_available():
            return []
            
        self._setup_huggingface_auth()
        try:
            from datasets import load_dataset
        except ImportError:
            return []
        
        all_preferences = []
        if not book_ids:
            return []
            
        for dataset_name in book_ids:
            try:
                dataset_id = str(dataset_name).strip()
                # Load dataset
                dataset = load_dataset(dataset_id, split="train", streaming=False)
                
                # Identify columns
                cols = dataset.column_names
                prompt_col = next((c for c in ["prompt", "question", "instruction"] if c in cols), None)
                chosen_col = next((c for c in ["chosen", "selected", "preferred"] if c in cols), None)
                rejected_col = next((c for c in ["rejected", "discarded", "not_preferred"] if c in cols), None)
                
                if not (prompt_col and chosen_col and rejected_col):
                    continue

                for i, row in enumerate(dataset):
                    if i >= max_items:
                        break
                    
                    # Extract text
                    prompt = self._extract_text_recursive(row[prompt_col])
                    chosen = self._extract_text_recursive(row[chosen_col])
                    rejected = self._extract_text_recursive(row[rejected_col])
                    
                    if prompt and chosen and rejected:
                        all_preferences.append({
                            "prompt": "\n".join(prompt),
                            "chosen": "\n".join(chosen),
                            "rejected": "\n".join(rejected)
                        })
            except Exception as e:
                logger.debug(f"Failed to load preference data from {dataset_name}: {e}")
                
        return all_preferences

    def load_data(
        self,
        book_ids: Optional[List[Any]] = None,
        max_books: int = 3,
        categories: Optional[List[str]] = None,
        max_text_size: Optional[int] = None,
        data_dir: Optional[Path] = None,
        search: Optional[str] = None,
    ) -> str:
        """Load HuggingFace datasets"""
        if not is_huggingface_available():
            raise ImportError("HuggingFace datasets library not available.")
        
        self._setup_huggingface_auth()
        cache_dir = self._get_cache_dir(data_dir, "huggingface")
        all_text = []
        
        if book_ids:
            for dataset_name in book_ids:
                dataset_id = str(dataset_name).strip()
                safe_filename = dataset_id.replace('/', '_').replace('\\', '_')
                cache_file = cache_dir / f"{safe_filename}.txt"
                
                if cache_file.exists():
                    try:
                        text = cache_file.read_text(encoding="utf-8")
                        if text:
                            all_text.append(text)
                            continue
                    except Exception:
                        pass
                
                text = self._load_dataset_text(dataset_id, cache_file, max_text_size)
                if text:
                    all_text.append(text)
                else:
                    raise RuntimeError(f"Failed to load dataset '{dataset_id}'.")
        
        return "\n\n".join(all_text)

class Registry:
    """Registry for data sources"""
    def __init__(self):
        self._sources = {}
        self.register(GutenbergSource())
        self.register(WikipediaSource())
        self.register(HuggingFaceSource())

    def register(self, source: BaseDataSource):
        self._sources[source.get_source_name()] = source

    def get_source(self, name: str) -> Optional[BaseDataSource]:
        return self._sources.get(name.lower())

    def load_preferences(
        self,
        sources: Union[str, List[str]] = "huggingface",
        book_ids: Optional[List[Any]] = None,
        max_items: int = 1000,
        data_dir: Optional[Path] = None,
    ) -> List[Dict[str, str]]:
        """Load preference data from specified sources"""
        source_names = [sources] if isinstance(sources, str) else sources
        all_preferences = []
        
        for name in source_names:
            source = self.get_source(name)
            if not source:
                continue
                
            try:
                prefs = source.load_preferences(
                    book_ids=book_ids,
                    max_items=max_items,
                    data_dir=data_dir,
                )
                if prefs:
                    all_preferences.extend(prefs)
            except Exception as e:
                logger.error(f"Error loading preferences from {name}: {e}")
                
        return all_preferences

    def load_data(
        self,
        source: Union[str, List[str]] = "gutenberg",
        book_ids: Optional[List[Any]] = None,
        max_books: int = 3,
        categories: Optional[List[str]] = None,
        max_text_size: Optional[int] = None,
        search: Optional[str] = None,
        data_dir: Optional[Path] = None,
    ) -> str:
        """Load data from specified sources"""
        source_names = [source] if isinstance(source, str) else source
        all_texts = []
        
        for name in source_names:
            src = self.get_source(name)
            if not src:
                continue
                
            try:
                text = src.load_data(
                    book_ids=book_ids,
                    max_books=max_books,
                    categories=categories,
                    max_text_size=None,
                    data_dir=data_dir,
                    search=search,
                )
                if text:
                    all_texts.append(text)
            except Exception as e:
                if isinstance(e, (ImportError, RuntimeError)):
                    raise
                logger.error(f"Error loading from {name}: {e}")
                
        if not all_texts:
            raise RuntimeError(f"No data could be loaded from sources: {source_names}")
            
        combined = "\n\n".join(all_texts)
        if max_text_size and len(combined) > max_text_size:
            combined = combined[:max_text_size]
        return combined

    def preprocess_text(self, text: str, lowercase: bool = True, remove_special: bool = True) -> str:
        """Standard text preprocessing"""
        # Use GutenbergSource's implementation as a default
        source = self.get_source("gutenberg")
        if source:
            return source.preprocess_text(text, lowercase, remove_special)
        
        # Simple fallback if gutenberg source not registered
        if lowercase:
            text = text.lower()
        if remove_special:
            text = re.sub(r'[^a-z0-9\s.,!?\'"-]', ' ', text)
            text = re.sub(r'\s+', ' ', text)
        return text.strip()

    @classmethod
    def list_available_sources(cls) -> List[str]:
        return ["gutenberg", "wikipedia", "huggingface"]

    @classmethod
    def get_source_info(cls, name: str) -> Optional[Dict[str, Any]]:
        return {"supports_categories": True, "supports_book_ids": True, "categories": []}

def _load_api_keys() -> Dict[str, Any]:
    return {}

def preprocess_text(text: str, lowercase: bool = True, remove_special: bool = True) -> str:
    source = GutenbergSource()
    return source.preprocess_text(text, lowercase, remove_special)

# Main data pipeline instance
NeuralTextGeneratorData = Registry()
