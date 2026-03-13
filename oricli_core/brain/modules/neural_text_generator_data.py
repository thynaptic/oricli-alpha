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

from oricli_core.exceptions import InvalidParameterError

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
            # Helper to try loading a dataset with various combinations
            def _try_load(path, config=None):
                # 1. Try common splits WITHOUT trust_remote_code first (modern datasets)
                for split in ["train", "data", "main"]:
                    try:
                        if config:
                            return load_dataset(path, config, split=split, streaming=True)
                        else:
                            return load_dataset(path, split=split, streaming=True)
                    except Exception:
                        continue
                
                # 2. Try WITH trust_remote_code fallback for legacy datasets
                for split in ["train", "data", "main"]:
                    try:
                        if config:
                            return load_dataset(path, config, split=split, streaming=True, trust_remote_code=True)
                        else:
                            return load_dataset(path, split=split, streaming=True, trust_remote_code=True)
                    except Exception:
                        continue
                
                # 3. Try discovery of splits if specific ones fail
                try:
                    from datasets import get_dataset_split_names
                    # Try without trust first
                    available_splits = None
                    try:
                        available_splits = get_dataset_split_names(path, config) if config else get_dataset_split_names(path)
                    except Exception:
                        available_splits = get_dataset_split_names(path, config, trust_remote_code=True) if config else get_dataset_split_names(path, trust_remote_code=True)
                    
                    if available_splits:
                        split = available_splits[0]
                        try:
                            return load_dataset(path, config, split=split, streaming=True) if config else load_dataset(path, split=split, streaming=True)
                        except Exception:
                            return load_dataset(path, config, split=split, streaming=True, trust_remote_code=True) if config else load_dataset(path, split=split, streaming=True, trust_remote_code=True)
                except Exception:
                    pass

                # Final attempt: direct dict return
                try:
                    # Without trust
                    try:
                        ds_dict = load_dataset(path, config, streaming=True) if config else load_dataset(path, streaming=True)
                    except Exception:
                        ds_dict = load_dataset(path, config, streaming=True, trust_remote_code=True) if config else load_dataset(path, streaming=True, trust_remote_code=True)
                    
                    if isinstance(ds_dict, dict) and ds_dict:
                        return ds_dict[next(iter(ds_dict.keys()))]
                    return ds_dict
                except Exception:
                    return None

            if dataset_config:
                logger.info(f"Loading HF dataset '{dataset_id}' [config={dataset_config}]...")
                dataset = _try_load(dataset_id, dataset_config)
                
                if dataset is None:
                    logger.info(f"Retrying '{dataset_id}' without config, using '{dataset_config}' as filter...")
                    dataset = _try_load(dataset_id)
                    dataset_filter = dataset_config
            else:
                logger.info(f"Loading HF dataset '{dataset_id}'...")
                dataset = _try_load(dataset_id)
            
            if dataset is None:
                logger.error(f"Failed to load dataset '{dataset_id}' (tried multiple splits/configs)")
                return None
            
            if dataset_filter:
                try:
                    filter_col = None
                    # Sample a few rows to find the filter column
                    sample = []
                    try:
                        it = iter(dataset)
                        for _ in range(50):
                            sample.append(next(it))
                    except (StopIteration, Exception):
                        pass
                    
                    if sample:
                        for col in dataset.column_names:
                            if any(str(x.get(col)).lower() == dataset_filter.lower() for x in sample):
                                filter_col = col
                                break
                    
                    if filter_col:
                        logger.info(f"Filtering column '{filter_col}' by '{dataset_filter}'...")
                        dataset = dataset.filter(lambda x: str(x[filter_col]).lower() == dataset_filter.lower())
                    else:
                        # If no column matches the filter value, check if the filter IS a column name
                        if dataset_filter in dataset.column_names:
                            logger.info(f"Using filter '{dataset_filter}' as target column name.")
                            text_column = dataset_filter
                        else:
                            logger.warning(f"Could not find column or value matching filter '{dataset_filter}'")
                except Exception as e:
                    logger.warning(f"Filtering failed for {dataset_id}: {e}")
            
            all_text = []
            text_columns = ["text", "content", "conversations", "conversation", "message", "messages", "article", "body", "chapter", "chapter_text", "summary", "summary_text"]
            
            # Identify the best column to extract text from
            text_column = None
            
            # 1. If filter matched a column name, use it (verified it exists in dataset.column_names)
            if 'discovered_column' in locals() and discovered_column:
                text_column = discovered_column
            
            # 2. Try standard names if no column identified yet
            if not text_column:
                for col in text_columns:
                    if col in dataset.column_names:
                        # VERIFY it's not empty in the first row
                        try:
                            first_row = next(iter(dataset))
                            if first_row.get(col):
                                text_column = col
                                break
                        except Exception:
                            pass
            
            # 3. Smart discovery from first row (longest non-empty string)
            if not text_column:
                try:
                    first_row = None
                    try:
                        it = iter(dataset)
                        first_row = next(it)
                    except (StopIteration, Exception):
                        pass
                    
                    if first_row:
                        best_col = None
                        max_len = -1
                        for col in dataset.column_names:
                            val = first_row.get(col)
                            if val and isinstance(val, str):
                                if len(val) > max_len:
                                    max_len = len(val)
                                    best_col = col
                            elif val and isinstance(val, (list, dict)) and max_len < 0:
                                best_col = col
                        text_column = best_col
                except Exception:
                    pass
            
            # 4. Final fallback to first column
            if not text_column and dataset.column_names:
                text_column = dataset.column_names[0]
            
            if not text_column:
                logger.error(f"Could not identify any columns in dataset '{dataset_id}'.")
                return None
            
            logger.info(f"Extracting from column '{text_column}'...")
            
            current_size = 0
            # Use an iterator to handle both normal and IterableDataset
            it = iter(dataset)
            for idx in range(10000): # Hard limit for safety
                try:
                    example = next(it)
                except (StopIteration, Exception):
                    break
                    
                if text_column in example:
                    parts = self._extract_text_recursive(example[text_column])
                    if parts:
                        chunk = "\n".join(parts)
                        all_text.append(chunk)
                        current_size += len(chunk)
                
                if max_text_size and current_size >= max_text_size:
                    break
            
            if not all_text:
                logger.warning(f"No text extracted from column '{text_column}' in dataset '{dataset_id}'.")
                return None
                
            combined = "\n\n".join(all_text)
            try:
                cache_file.parent.mkdir(parents=True, exist_ok=True)
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
                safe_filename = dataset_id.replace('/', '_').replace('\\', '_').replace(':', '_')
                cache_file = cache_dir / f"{safe_filename}.txt"
                
                # Check cache first
                if cache_file.exists():
                    try:
                        text = cache_file.read_text(encoding="utf-8")
                        if text:
                            all_text.append(text)
                            continue
                    except Exception:
                        pass
                
                # Load and extract
                text = self._load_dataset_text(dataset_id, cache_file, max_text_size)
                if text:
                    all_text.append(text)
                else:
                    raise RuntimeError(f"Failed to load dataset '{dataset_id}'. Ensure it exists and has text columns.")
        
        if not all_text:
            return ""
            
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

    def load_jsonl_preferences(self, file_path: str, max_items: int = 1000) -> List[Dict[str, str]]:
        """Load preference data from a JSONL file."""
        path = Path(file_path)
        if not path.exists():
            logger.warning(f"DPO data file not found: {file_path}")
            return []
            
        preferences = []
        try:
            with open(path, "r", encoding="utf-8") as f:
                for line in f:
                    if len(preferences) >= max_items:
                        break
                    line = line.strip()
                    if not line:
                        continue
                    try:
                        data = json.loads(line)
                        # Expecting prompt, chosen, rejected
                        if all(k in data for k in ["prompt", "chosen", "rejected"]):
                            preferences.append({
                                "prompt": data["prompt"],
                                "chosen": data["chosen"],
                                "rejected": data["rejected"]
                            })
                    except Exception:
                        continue
        except Exception as e:
            logger.error(f"Failed to load JSONL preferences from {file_path}: {e}")
            
        return preferences

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

    # ── Character-level sequence helpers ─────────────────────────────────────

    def build_character_vocabulary(self, text: str) -> Dict[str, int]:
        """Build a character → index vocabulary from text."""
        chars = sorted(set(text))
        return {ch: i for i, ch in enumerate(chars)}

    def create_character_sequences(
        self,
        text: str,
        sequence_length: int = 100,
    ) -> Tuple[List[str], List[str]]:
        """Slide a window over text to create (input_seq, target_char) pairs."""
        sequences: List[str] = []
        targets: List[str] = []
        for i in range(0, len(text) - sequence_length):
            sequences.append(text[i : i + sequence_length])
            targets.append(text[i + sequence_length])
        return sequences, targets

    def sequences_to_arrays_char(
        self,
        sequences: List[str],
        targets: List[str],
        vocab: Dict[str, int],
    ) -> Tuple[Any, Any]:
        """Convert character sequences to numpy integer arrays for Keras."""
        import numpy as np
        vocab_size = len(vocab)
        seq_len = len(sequences[0]) if sequences else 1
        n = len(sequences)
        X = np.zeros((n, seq_len), dtype=np.int32)
        y = np.zeros((n, vocab_size), dtype=np.float32)
        for i, (seq, target) in enumerate(zip(sequences, targets)):
            for t, ch in enumerate(seq):
                if ch in vocab:
                    X[i, t] = vocab[ch]
            if target in vocab:
                y[i, vocab[target]] = 1.0
        return X, y

    # ── Word-level sequence helpers ───────────────────────────────────────────

    def build_word_vocabulary(
        self, text: str, min_frequency: int = 1
    ) -> Tuple[Dict[str, int], Dict[int, str]]:
        """Build word <-> index vocabularies."""
        from collections import Counter
        words = text.split()
        counts = Counter(words)
        vocab = {"<UNK>": 0}
        for word, freq in counts.most_common():
            if freq >= min_frequency:
                if word not in vocab:
                    vocab[word] = len(vocab)
        vocab_reverse = {idx: word for word, idx in vocab.items()}
        return vocab, vocab_reverse

    def create_word_sequences(
        self,
        text: str,
        sequence_length: int = 20,
        vocab: Optional[Dict[str, int]] = None,
    ) -> Tuple[List[List[int]], List[int]]:
        """Slide a window over tokenised text to create (input_ids, target_id) pairs."""
        words = text.split()
        if vocab is None:
            # Note: returns tuple, but we only need the first part for sequence creation
            vocab, _ = self.build_word_vocabulary(text)
        unk = vocab.get("<UNK>", 0)
        ids = [vocab.get(w, unk) for w in words]
        sequences: List[List[int]] = []
        targets: List[int] = []
        for i in range(0, len(ids) - sequence_length):
            sequences.append(ids[i : i + sequence_length])
            targets.append(ids[i + sequence_length])
        return sequences, targets

    def sequences_to_arrays_word(
        self,
        sequences: List[List[int]],
        targets: List[int],
        vocab: Dict[str, int],
    ) -> Tuple[Any, Any]:
        """Convert word sequences to arrays for training."""
        import numpy as np
        n = len(sequences)
        seq_len = len(sequences[0]) if sequences else 1
        X = np.array(sequences, dtype=np.int32).reshape(n, seq_len)
        y = np.array(targets, dtype=np.int32)
        return X, y

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
