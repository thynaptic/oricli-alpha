"""
Neural Text Generator Data Pipeline
Handles data loading, preprocessing, and sequence creation for training
"""

import re
import sys
from pathlib import Path
from typing import List, Tuple, Dict, Any, Optional
import json

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent))

try:
    import requests
    REQUESTS_AVAILABLE = True
except ImportError:
    REQUESTS_AVAILABLE = False


class NeuralTextGeneratorData:
    """Data loading and preprocessing for neural text generation"""

    # Category-based book mappings
    BOOK_CATEGORIES = {
        "fiction": [84, 1342, 11, 2701, 74, 98, 158, 16328],  # Frankenstein, Pride and Prejudice, Alice, Moby Dick, etc.
        "non_fiction": [2600, 3300, 35, 36, 41],  # War and Peace, Ulysses, etc.
        "technical": [829, 1400, 1661],  # Scientific texts
        "philosophy": [863, 1497, 1500],  # Philosophical works
        "poetry": [1065, 1066, 1067],  # Poetry collections
        "drama": [1112, 1524],  # Plays
        "adventure": [120, 1661, 74],  # Adventure stories
        "mystery": [345, 766, 209],  # Mystery novels
        "science_fiction": [84, 36, 829],  # Sci-fi
        "classic": [84, 1342, 11, 74, 98],  # Classic literature
    }

    @staticmethod
    def get_books_by_category(categories: List[str]) -> List[int]:
        """
        Get book IDs for specified categories
        
        Args:
            categories: List of category names (e.g., ["fiction", "technical"])
        
        Returns:
            List of book IDs
        """
        book_ids = []
        for category in categories:
            if category in NeuralTextGeneratorData.BOOK_CATEGORIES:
                book_ids.extend(NeuralTextGeneratorData.BOOK_CATEGORIES[category])
        # Remove duplicates while preserving order
        seen = set()
        unique_ids = []
        for book_id in book_ids:
            if book_id not in seen:
                seen.add(book_id)
                unique_ids.append(book_id)
        return unique_ids

    @staticmethod
    def load_gutenberg_data(
        book_ids: Optional[List[int]] = None,
        max_books: int = 3,
        data_dir: Optional[Path] = None,
        categories: Optional[List[str]] = None,
        max_text_size: Optional[int] = None,
    ) -> str:
        """
        Load Project Gutenberg books
        
        Args:
            book_ids: Specific book IDs to load (e.g., [84, 1342] for Frankenstein, Pride and Prejudice)
            max_books: Maximum number of books to load if book_ids not specified
            data_dir: Directory to cache downloaded books
            categories: List of categories to load books from (e.g., ["fiction", "technical"])
            max_text_size: Maximum text size in characters (None = no limit)
        
        Returns:
            Combined text from all books (limited to max_text_size if specified)
        """
        if data_dir is None:
            data_dir = Path(__file__).parent.parent.parent / "data" / "gutenberg"
        data_dir.mkdir(parents=True, exist_ok=True)

        # Get book IDs from categories if provided
        if categories:
            category_book_ids = NeuralTextGeneratorData.get_books_by_category(categories)
            if book_ids is None:
                book_ids = category_book_ids
            else:
                # Merge with existing book_ids
                book_ids = list(set(book_ids + category_book_ids))

        if book_ids is None:
            # Default: popular books for general language modeling
            book_ids = [84, 1342, 11]  # Frankenstein, Pride and Prejudice, Alice in Wonderland

        all_text = []
        
        for book_id in book_ids[:max_books]:
            book_file = data_dir / f"book_{book_id}.txt"
            
            # Try to load from cache first
            if book_file.exists():
                try:
                    with open(book_file, "r", encoding="utf-8") as f:
                        text = f.read()
                        if text:
                            all_text.append(text)
                            continue
                except Exception:
                    pass  # If cache is corrupted, re-download
            
            # Download from Project Gutenberg
            if REQUESTS_AVAILABLE:
                try:
                    url = f"https://www.gutenberg.org/files/{book_id}/{book_id}-0.txt"
                    response = requests.get(url, timeout=30)
                    if response.status_code == 200:
                        text = response.text
                        # Save to cache
                        with open(book_file, "w", encoding="utf-8") as f:
                            f.write(text)
                        all_text.append(text)
                    else:
                        # Try alternative URL format
                        url = f"https://www.gutenberg.org/cache/epub/{book_id}/pg{book_id}.txt"
                        response = requests.get(url, timeout=30)
                        if response.status_code == 200:
                            text = response.text
                            with open(book_file, "w", encoding="utf-8") as f:
                                f.write(text)
                            all_text.append(text)
                except Exception as e:
                    print(
                        f"[NeuralTextGeneratorData] Failed to download book {book_id}: {e}",
                        file=sys.stderr,
                    )
            else:
                print(
                    f"[NeuralTextGeneratorData] requests not available, cannot download book {book_id}",
                    file=sys.stderr,
                )

        if not all_text:
            # Fallback: return sample text for testing
            fallback_text = (
                "The quick brown fox jumps over the lazy dog. "
                "This is a sample text for training when Gutenberg data is unavailable. "
                "It contains common words and simple sentences. "
                "The model will learn basic language patterns from this text. "
            ) * 100
            if max_text_size:
                return fallback_text[:max_text_size]
            return fallback_text

        combined_text = "\n\n".join(all_text)
        
        # Limit text size if specified
        if max_text_size and len(combined_text) > max_text_size:
            combined_text = combined_text[:max_text_size]
        
        return combined_text

    @staticmethod
    def preprocess_text(text: str, lowercase: bool = True, remove_special: bool = True) -> str:
        """
        Preprocess text for training
        
        Args:
            text: Raw text
            lowercase: Convert to lowercase
            remove_special: Remove special characters
        
        Returns:
            Preprocessed text
        """
        if lowercase:
            text = text.lower()

        if remove_special:
            # Remove Project Gutenberg headers/footers
            text = re.sub(r"\*\*\*.*?\*\*\*", "", text, flags=re.DOTALL)
            text = re.sub(r"Project Gutenberg.*?END.*?Project Gutenberg", "", text, flags=re.DOTALL | re.IGNORECASE)
            
            # Keep only alphanumeric, spaces, and basic punctuation
            text = re.sub(r"[^\w\s.,!?;:()'-]", " ", text)
            
            # Normalize whitespace
            text = re.sub(r"\s+", " ", text)
            text = text.strip()

        return text

    @staticmethod
    def create_character_sequences(
        text: str, sequence_length: int = 100, step: int = 3
    ) -> Tuple[List[str], List[str]]:
        """
        Create character-level training sequences
        
        Args:
            text: Preprocessed text
            sequence_length: Length of input sequences
            step: Step size for sliding window
        
        Returns:
            Tuple of (input_sequences, target_sequences)
        """
        if len(text) < sequence_length + 1:
            # Pad with repetition if text is too short
            text = text * (sequence_length // len(text) + 2)

        sequences = []
        targets = []

        for i in range(0, len(text) - sequence_length, step):
            seq = text[i : i + sequence_length]
            target = text[i + sequence_length]
            sequences.append(seq)
            targets.append(target)

        return sequences, targets

    @staticmethod
    def create_word_sequences(
        text: str, sequence_length: int = 100, step: int = 10
    ) -> Tuple[List[List[str]], List[str]]:
        """
        Create word-level training sequences
        
        Args:
            text: Preprocessed text
            sequence_length: Length of input sequences (in words)
            step: Step size for sliding window
        
        Returns:
            Tuple of (input_sequences, target_sequences)
        """
        words = text.split()
        
        if len(words) < sequence_length + 1:
            # Pad with repetition if text is too short
            words = words * (sequence_length // len(words) + 2)

        sequences = []
        targets = []

        for i in range(0, len(words) - sequence_length, step):
            seq = words[i : i + sequence_length]
            target = words[i + sequence_length]
            sequences.append(seq)
            targets.append(target)

        return sequences, targets

    @staticmethod
    def build_character_vocabulary(text: str) -> Dict[str, int]:
        """
        Build character-to-index mapping
        
        Args:
            text: Preprocessed text
        
        Returns:
            Dictionary mapping characters to indices
        """
        unique_chars = sorted(set(text))
        vocab = {char: idx for idx, char in enumerate(unique_chars)}
        return vocab

    @staticmethod
    def build_word_vocabulary(
        text: str, min_frequency: int = 2
    ) -> Tuple[Dict[str, int], Dict[int, str]]:
        """
        Build word-to-index mapping
        
        Args:
            text: Preprocessed text
            min_frequency: Minimum word frequency to include in vocabulary
        
        Returns:
            Tuple of (word_to_index, index_to_word) dictionaries
        """
        words = text.split()
        
        # Count word frequencies
        word_counts = {}
        for word in words:
            word_counts[word] = word_counts.get(word, 0) + 1

        # Filter by minimum frequency
        filtered_words = [
            word for word, count in word_counts.items() if count >= min_frequency
        ]
        
        # Add special tokens
        vocab_words = ["<UNK>", "<PAD>", "<START>", "<END>"] + sorted(filtered_words)
        
        word_to_index = {word: idx for idx, word in enumerate(vocab_words)}
        index_to_word = {idx: word for word, idx in word_to_index.items()}

        return word_to_index, index_to_word

    @staticmethod
    def sequences_to_arrays_char(
        sequences: List[str], targets: List[str], vocab: Dict[str, int]
    ) -> Tuple[Any, Any]:
        """
        Convert character sequences to numpy arrays
        
        Args:
            sequences: Input sequences
            targets: Target characters
            vocab: Character vocabulary
        
        Returns:
            Tuple of (X, y) arrays
        """
        try:
            import numpy as np
        except ImportError:
            raise ImportError("numpy is required for sequence conversion")

        vocab_size = len(vocab)
        sequence_length = len(sequences[0]) if sequences else 0

        X = np.zeros((len(sequences), sequence_length), dtype=np.int32)
        y = np.zeros((len(sequences), vocab_size), dtype=np.float32)

        for i, (seq, target) in enumerate(zip(sequences, targets)):
            for j, char in enumerate(seq):
                X[i, j] = vocab.get(char, 0)
            
            target_idx = vocab.get(target, 0)
            y[i, target_idx] = 1.0

        return X, y

    @staticmethod
    def sequences_to_arrays_word(
        sequences: List[List[str]], targets: List[str], vocab: Dict[str, int]
    ) -> Tuple[Any, Any]:
        """
        Convert word sequences to numpy arrays
        
        Args:
            sequences: Input sequences
            targets: Target words
            vocab: Word vocabulary
        
        Returns:
            Tuple of (X, y) arrays
        """
        try:
            import numpy as np
        except ImportError:
            raise ImportError("numpy is required for sequence conversion")

        vocab_size = len(vocab)
        sequence_length = len(sequences[0]) if sequences else 0
        unk_idx = vocab.get("<UNK>", 0)

        X = np.zeros((len(sequences), sequence_length), dtype=np.int32)
        y = np.zeros(len(sequences), dtype=np.int32)

        for i, (seq, target) in enumerate(zip(sequences, targets)):
            for j, word in enumerate(seq):
                X[i, j] = vocab.get(word, unk_idx)
            
            y[i] = vocab.get(target, unk_idx)

        return X, y

