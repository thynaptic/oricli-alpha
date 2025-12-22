"""
Neural Text Generator Data Pipeline
Handles data loading, preprocessing, and sequence creation for training
Supports multiple data sources: Gutenberg, Wikipedia, LibriVox, OpenLibrary
"""

import re
import sys
import time
import html
import os
from abc import ABC, abstractmethod
from pathlib import Path
from typing import List, Tuple, Dict, Any, Optional, Union
import json
import importlib.util

# Lazy imports - don't import heavy libraries at module level
REQUESTS_AVAILABLE = None
requests = None

WIKIPEDIA_AVAILABLE = None
wikipedia = None

INTERNETARCHIVE_AVAILABLE = None
search_items = None
get_item = None
download = None

def _lazy_import_requests():
    """Lazy import requests"""
    global REQUESTS_AVAILABLE, requests
    if REQUESTS_AVAILABLE is None:
        try:
            import requests as req
            requests = req
            REQUESTS_AVAILABLE = True
        except ImportError:
            REQUESTS_AVAILABLE = False
    return REQUESTS_AVAILABLE

def _lazy_import_wikipedia():
    """Lazy import wikipedia"""
    global WIKIPEDIA_AVAILABLE, wikipedia
    if WIKIPEDIA_AVAILABLE is None:
        try:
            import wikipedia as wiki
            wikipedia = wiki
            WIKIPEDIA_AVAILABLE = True
        except ImportError:
            WIKIPEDIA_AVAILABLE = False
    return WIKIPEDIA_AVAILABLE

def _lazy_import_internetarchive():
    """Lazy import internetarchive"""
    global INTERNETARCHIVE_AVAILABLE, search_items, get_item, download
    if INTERNETARCHIVE_AVAILABLE is None:
        try:
            from internetarchive import search_items as si, get_item as gi, download as dl
            search_items = si
            get_item = gi
            download = dl
            INTERNETARCHIVE_AVAILABLE = True
        except ImportError:
            INTERNETARCHIVE_AVAILABLE = False
    return INTERNETARCHIVE_AVAILABLE

# HuggingFace datasets and hub can be very heavy to import and may pull in
# additional ML frameworks. To avoid hangs when this module is imported
# (e.g. for `--list-sources`), we only check for their presence here and
# import them lazily inside the HuggingFace-specific methods.
HUGGINGFACE_AVAILABLE = importlib.util.find_spec("datasets") is not None
HF_API_AVAILABLE = importlib.util.find_spec("huggingface_hub") is not None


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
    ) -> str:
        """
        Load data from this source
        
        Args:
            book_ids: Source-specific identifiers (book IDs, article titles, etc.)
            max_books: Maximum number of items to load
            categories: Category filters (source-specific)
            max_text_size: Maximum text size in characters
            data_dir: Directory for caching
        
        Returns:
            Combined text from all loaded items
        """
        pass
    
    @abstractmethod
    def get_available_categories(self) -> List[str]:
        """Return list of available categories for this source"""
        pass
    
    @abstractmethod
    def supports_categories(self) -> bool:
        """Whether this source supports category filtering"""
        pass
    
    @abstractmethod
    def supports_book_ids(self) -> bool:
        """Whether this source supports item ID selection"""
        pass
    
    def _get_cache_dir(self, data_dir: Optional[Path], source_name: str) -> Path:
        """Get cache directory for this source"""
        if data_dir is None:
            base_dir = Path(__file__).parent.parent.parent / "data"
        else:
            base_dir = data_dir.parent if data_dir.name in ["gutenberg", "wikipedia", "librivox", "openlibrary"] else data_dir
        cache_dir = base_dir / source_name
        cache_dir.mkdir(parents=True, exist_ok=True)
        return cache_dir


class GutenbergSource(BaseDataSource):
    """Project Gutenberg data source"""
    
    BOOK_CATEGORIES = {
        "fiction": [84, 1342, 11, 2701, 74, 98, 158, 16328],
        "non_fiction": [2600, 3300, 35, 36, 41],
        "technical": [829, 1400, 1661],
        "philosophy": [863, 1497, 1500],
        "poetry": [1065, 1066, 1067],
        "drama": [1112, 1524],
        "adventure": [120, 1661, 74],
        "mystery": [345, 766, 209],
        "science_fiction": [84, 36, 829],
        "classic": [84, 1342, 11, 74, 98],
    }
    
    def get_source_name(self) -> str:
        return "gutenberg"
    
    def get_available_categories(self) -> List[str]:
        return list(self.BOOK_CATEGORIES.keys())
    
    def supports_categories(self) -> bool:
        return True
    
    def supports_book_ids(self) -> bool:
        return True
    
    def get_books_by_category(self, categories: List[str]) -> List[int]:
        """Get book IDs for specified categories"""
        book_ids = []
        for category in categories:
            if category in self.BOOK_CATEGORIES:
                book_ids.extend(self.BOOK_CATEGORIES[category])
        # Remove duplicates while preserving order
        seen = set()
        unique_ids = []
        for book_id in book_ids:
            if book_id not in seen:
                seen.add(book_id)
                unique_ids.append(book_id)
        return unique_ids
    
    def load_data(
        self,
        book_ids: Optional[List[Any]] = None,
        max_books: int = 3,
        categories: Optional[List[str]] = None,
        max_text_size: Optional[int] = None,
        data_dir: Optional[Path] = None,
        search: Optional[str] = None,
    ) -> str:
        """Load Project Gutenberg books"""
        cache_dir = self._get_cache_dir(data_dir, "gutenberg")
        
        # Get book IDs from categories if provided
        if categories:
            category_book_ids = self.get_books_by_category(categories)
            if book_ids is None:
                book_ids = category_book_ids
            else:
                # Convert book_ids to integers if they're strings
                converted_ids = []
                for bid in book_ids:
                    try:
                        converted_ids.append(int(bid))
                    except (ValueError, TypeError):
                        # Skip invalid IDs
                        print(
                            f"[GutenbergSource] Invalid book ID: {bid}, skipping",
                            file=sys.stderr,
                        )
                # Merge with existing book_ids
                book_ids = list(set(converted_ids + category_book_ids))
        
        # Convert book_ids to integers if they're strings
        if book_ids is not None:
            converted_ids = []
            for bid in book_ids:
                try:
                    converted_ids.append(int(bid))
                except (ValueError, TypeError):
                    print(
                        f"[GutenbergSource] Invalid book ID: {bid}, skipping",
                        file=sys.stderr,
                    )
            book_ids = converted_ids if converted_ids else None
        
        if book_ids is None:
            # Default: popular books
            book_ids = [84, 1342, 11]  # Frankenstein, Pride and Prejudice, Alice
        
        all_text = []
        
        for book_id in book_ids[:max_books]:
            book_file = cache_dir / f"book_{book_id}.txt"
            
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
                        f"[GutenbergSource] Failed to download book {book_id}: {e}",
                        file=sys.stderr,
                    )
            else:
                print(
                    f"[GutenbergSource] requests not available, cannot download book {book_id}",
                    file=sys.stderr,
                )
        
        if not all_text:
            # Fallback: return sample text
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


class WikipediaSource(BaseDataSource):
    """Wikipedia data source"""
    
    # Wikipedia category mappings
    CATEGORY_MAPPINGS = {
        "fiction": ["Category:Fiction", "Category:Novels", "Category:Literature"],
        "non_fiction": ["Category:Non-fiction", "Category:History", "Category:Science"],
        "technical": ["Category:Technology", "Category:Computer_science", "Category:Engineering"],
        "philosophy": ["Category:Philosophy", "Category:Ethics", "Category:Logic"],
        "poetry": ["Category:Poetry", "Category:Poets"],
        "drama": ["Category:Theatre", "Category:Plays", "Category:Drama"],
        "adventure": ["Category:Adventure_fiction", "Category:Adventure_novels"],
        "mystery": ["Category:Mystery_fiction", "Category:Detective_fiction"],
        "science_fiction": ["Category:Science_fiction", "Category:Speculative_fiction"],
        "classic": ["Category:Classical_literature", "Category:Classic_books"],
    }
    
    # Popular article titles for default selection
    DEFAULT_ARTICLES = [
        "Artificial intelligence",
        "Machine learning",
        "Natural language processing",
        "Computer science",
        "Mathematics",
        "Physics",
        "Literature",
        "History",
        "Philosophy",
        "Science",
    ]
    
    def get_source_name(self) -> str:
        return "wikipedia"
    
    def get_available_categories(self) -> List[str]:
        return list(self.CATEGORY_MAPPINGS.keys())
    
    def supports_categories(self) -> bool:
        return True
    
    def supports_book_ids(self) -> bool:
        return True  # Uses article titles as IDs
    
    def load_data(
        self,
        book_ids: Optional[List[Any]] = None,
        max_books: int = 3,
        categories: Optional[List[str]] = None,
        max_text_size: Optional[int] = None,
        data_dir: Optional[Path] = None,
        search: Optional[str] = None,
    ) -> str:
        """Load Wikipedia articles"""
        cache_dir = self._get_cache_dir(data_dir, "wikipedia")
        
        article_titles = []
        
        # Get articles from categories if provided
        if categories:
            for category in categories:
                if category in self.CATEGORY_MAPPINGS:
                    # For simplicity, use default articles matching category
                    # In a full implementation, would query Wikipedia API for category members
                    wiki_categories = self.CATEGORY_MAPPINGS[category]
                    # Use first few default articles as examples
                    article_titles.extend(self.DEFAULT_ARTICLES[:3])
        
        # Use provided article titles (book_ids parameter)
        if book_ids:
            article_titles.extend([str(title) for title in book_ids])
        
        if not article_titles:
            article_titles = self.DEFAULT_ARTICLES[:max_books]
        
        all_text = []
        
        for article_title in article_titles[:max_books]:
            # Sanitize filename
            safe_title = re.sub(r'[^\w\s-]', '', article_title).strip().replace(' ', '_')
            article_file = cache_dir / f"{safe_title}.txt"
            
            # Try to load from cache first
            if article_file.exists():
                try:
                    with open(article_file, "r", encoding="utf-8") as f:
                        text = f.read()
                        if text:
                            all_text.append(text)
                            continue
                except Exception:
                    pass
            
            # Download from Wikipedia
            if WIKIPEDIA_AVAILABLE:
                try:
                    # Set language and disable auto-suggest
                    wikipedia.set_lang("en")
                    page = wikipedia.page(article_title, auto_suggest=False)
                    text = page.content
                    
                    # Save to cache
                    with open(article_file, "w", encoding="utf-8") as f:
                        f.write(text)
                    all_text.append(text)
                    
                    # Rate limiting
                    time.sleep(0.5)
                except wikipedia.exceptions.DisambiguationError as e:
                    # Use first option
                    try:
                        page = wikipedia.page(e.options[0], auto_suggest=False)
                        text = page.content
                        with open(article_file, "w", encoding="utf-8") as f:
                            f.write(text)
                        all_text.append(text)
                        time.sleep(0.5)
                    except Exception as e2:
                        print(
                            f"[WikipediaSource] Failed to load article '{article_title}': {e2}",
                            file=sys.stderr,
                        )
                except Exception as e:
                    print(
                        f"[WikipediaSource] Failed to load article '{article_title}': {e}",
                        file=sys.stderr,
                    )
            elif REQUESTS_AVAILABLE:
                # Fallback to direct API call
                try:
                    api_url = "https://en.wikipedia.org/api/rest_v1/page/summary/" + article_title.replace(' ', '_')
                    response = requests.get(api_url, timeout=30)
                    if response.status_code == 200:
                        data = response.json()
                        text = data.get('extract', '')
                        if text:
                            # Get full article
                            api_url = f"https://en.wikipedia.org/api/rest_v1/page/html/{article_title.replace(' ', '_')}"
                            response = requests.get(api_url, timeout=30)
                            if response.status_code == 200:
                                # Simple HTML stripping
                                text = html.unescape(response.text)
                                # Remove HTML tags (simple regex)
                                text = re.sub(r'<[^>]+>', '', text)
                                
                                with open(article_file, "w", encoding="utf-8") as f:
                                    f.write(text)
                                all_text.append(text)
                    time.sleep(0.5)
                except Exception as e:
                    print(
                        f"[WikipediaSource] Failed to load article '{article_title}': {e}",
                        file=sys.stderr,
                    )
            else:
                print(
                    f"[WikipediaSource] Wikipedia library and requests not available, cannot download article '{article_title}'",
                    file=sys.stderr,
                )
        
        if not all_text:
            # Fallback text
            fallback_text = (
                "Wikipedia is a free online encyclopedia. "
                "It contains articles on many topics. "
                "This is sample text when Wikipedia data is unavailable. "
            ) * 50
            if max_text_size:
                return fallback_text[:max_text_size]
            return fallback_text
        
        combined_text = "\n\n".join(all_text)
        
        # Limit text size if specified
        if max_text_size and len(combined_text) > max_text_size:
            combined_text = combined_text[:max_text_size]
        
        return combined_text


class LibriVoxSource(BaseDataSource):
    """LibriVox audiobook data source"""
    
    # LibriVox collection/genre mappings
    CATEGORY_MAPPINGS = {
        "fiction": ["Fiction", "Novels", "Literature"],
        "non_fiction": ["Non-fiction", "History", "Biography"],
        "technical": ["Science", "Technology", "Education"],
        "philosophy": ["Philosophy", "Ethics"],
        "poetry": ["Poetry"],
        "drama": ["Drama", "Theatre"],
        "adventure": ["Adventure"],
        "mystery": ["Mystery", "Detective"],
        "science_fiction": ["Science Fiction"],
        "classic": ["Classic Literature"],
    }
    
    def get_source_name(self) -> str:
        return "librivox"
    
    def get_available_categories(self) -> List[str]:
        return list(self.CATEGORY_MAPPINGS.keys())
    
    def supports_categories(self) -> bool:
        return True
    
    def supports_book_ids(self) -> bool:
        return True
    
    def load_data(
        self,
        book_ids: Optional[List[Any]] = None,
        max_books: int = 3,
        categories: Optional[List[str]] = None,
        max_text_size: Optional[int] = None,
        data_dir: Optional[Path] = None,
        search: Optional[str] = None,
    ) -> str:
        """Load LibriVox content"""
        cache_dir = self._get_cache_dir(data_dir, "librivox")
        
        # LibriVox doesn't have a direct API, so we'll use Internet Archive metadata
        # For now, return a note that LibriVox integration requires additional setup
        # In a full implementation, would query Internet Archive API for LibriVox items
        
        if REQUESTS_AVAILABLE:
            all_text = []
            
            # Try to get LibriVox catalog via Internet Archive
            # LibriVox items are typically available on archive.org
            try:
                # Example: Search for LibriVox items
                # This is a simplified implementation
                search_url = "https://archive.org/advancedsearch.php"
                params = {
                    "q": "collection:librivoxaudio",
                    "fl": "identifier,title",
                    "output": "json",
                    "rows": str(max_books),
                }
                
                response = requests.get(search_url, params=params, timeout=30)
                if response.status_code == 200:
                    # Note: This is a simplified approach
                    # Full implementation would parse results and download text transcripts
                    print(
                        "[LibriVoxSource] LibriVox integration requires Internet Archive API access. "
                        "Using fallback text.",
                        file=sys.stderr,
                    )
            except Exception as e:
                print(
                    f"[LibriVoxSource] Error accessing LibriVox catalog: {e}",
                    file=sys.stderr,
                )
            
            if not all_text:
                # Fallback text
                fallback_text = (
                    "LibriVox provides free public domain audiobooks. "
                    "This is sample text when LibriVox data is unavailable. "
                    "Full integration requires Internet Archive API access. "
                ) * 50
                if max_text_size:
                    return fallback_text[:max_text_size]
                return fallback_text
            
            combined_text = "\n\n".join(all_text)
            if max_text_size and len(combined_text) > max_text_size:
                combined_text = combined_text[:max_text_size]
            return combined_text
        else:
            fallback_text = (
                "LibriVox provides free public domain audiobooks. "
                "Requests library required for LibriVox access. "
            ) * 50
            if max_text_size:
                return fallback_text[:max_text_size]
            return fallback_text


class OpenLibrarySource(BaseDataSource):
    """OpenLibrary/Internet Archive data source"""
    
    # OpenLibrary subject mappings
    CATEGORY_MAPPINGS = {
        "fiction": ["Fiction", "Novels"],
        "non_fiction": ["Non-fiction", "History"],
        "technical": ["Technology", "Science"],
        "philosophy": ["Philosophy"],
        "poetry": ["Poetry"],
        "drama": ["Drama"],
        "adventure": ["Adventure stories"],
        "mystery": ["Mystery fiction"],
        "science_fiction": ["Science fiction"],
        "classic": ["Classic literature"],
    }
    
    def get_source_name(self) -> str:
        return "openlibrary"
    
    def get_available_categories(self) -> List[str]:
        return list(self.CATEGORY_MAPPINGS.keys())
    
    def supports_categories(self) -> bool:
        return True
    
    def supports_book_ids(self) -> bool:
        return True  # Uses work IDs, ISBNs, or OLIDs
    
    def load_data(
        self,
        book_ids: Optional[List[Any]] = None,
        max_books: int = 3,
        categories: Optional[List[str]] = None,
        max_text_size: Optional[int] = None,
        data_dir: Optional[Path] = None,
        search: Optional[str] = None,
    ) -> str:
        """Load OpenLibrary/Internet Archive books"""
        cache_dir = self._get_cache_dir(data_dir, "openlibrary")
        
        all_text = []
        
        if REQUESTS_AVAILABLE:
            # OpenLibrary API
            base_url = "https://openlibrary.org"
            
            # Default work IDs if none provided
            default_works = [
                "OL82563W",  # Moby Dick
                "OL7353617W",  # Pride and Prejudice
                "OL82565W",  # Alice's Adventures in Wonderland
            ]
            
            work_ids = book_ids if book_ids else default_works[:max_books]
            
            for work_id in work_ids[:max_books]:
                work_file = cache_dir / f"work_{work_id}.txt"
                
                # Try cache first
                if work_file.exists():
                    try:
                        with open(work_file, "r", encoding="utf-8") as f:
                            text = f.read()
                            if text:
                                all_text.append(text)
                                continue
                    except Exception:
                        pass
                
                try:
                    # Get work details
                    work_url = f"{base_url}/works/{work_id}.json"
                    response = requests.get(work_url, timeout=30)
                    if response.status_code == 200:
                        work_data = response.json()
                        
                        # Try to find Internet Archive identifier
                        ia_id = None
                        if "ia" in work_data:
                            ia_id = work_data["ia"][0] if isinstance(work_data["ia"], list) else work_data["ia"]
                        
                        # If we have an IA identifier, try to get full text
                        if ia_id:
                            # Internet Archive text access
                            ia_text_url = f"https://archive.org/stream/{ia_id}/{ia_id}_djvu.txt"
                            text_response = requests.get(ia_text_url, timeout=30)
                            if text_response.status_code == 200:
                                text = text_response.text
                                with open(work_file, "w", encoding="utf-8") as f:
                                    f.write(text)
                                all_text.append(text)
                                time.sleep(0.5)
                                continue
                        
                        # Fallback: use work description/title
                        title = work_data.get("title", "Unknown")
                        description = work_data.get("description", {})
                        if isinstance(description, dict):
                            description_text = description.get("value", "")
                        else:
                            description_text = str(description)
                        
                        text = f"{title}\n\n{description_text}"
                        with open(work_file, "w", encoding="utf-8") as f:
                            f.write(text)
                        all_text.append(text)
                        time.sleep(0.5)
                except Exception as e:
                    print(
                        f"[OpenLibrarySource] Failed to load work {work_id}: {e}",
                        file=sys.stderr,
                    )
        
        if not all_text:
            # Fallback text
            fallback_text = (
                "OpenLibrary provides access to millions of books. "
                "This is sample text when OpenLibrary data is unavailable. "
                "Full text access requires Internet Archive integration. "
            ) * 50
            if max_text_size:
                return fallback_text[:max_text_size]
            return fallback_text
        
        combined_text = "\n\n".join(all_text)
        
        # Limit text size if specified
        if max_text_size and len(combined_text) > max_text_size:
            combined_text = combined_text[:max_text_size]
        
        return combined_text


class InternetArchiveSource(BaseDataSource):
    """Internet Archive data source using the internetarchive library"""
    
    # Internet Archive collection/subject mappings
    CATEGORY_MAPPINGS = {
        "fiction": ["collection:opensource", "mediatype:texts", "subject:Fiction"],
        "non_fiction": ["collection:opensource", "mediatype:texts", "subject:History"],
        "technical": ["collection:opensource", "mediatype:texts", "subject:Technology"],
        "philosophy": ["collection:opensource", "mediatype:texts", "subject:Philosophy"],
        "poetry": ["collection:opensource", "mediatype:texts", "subject:Poetry"],
        "drama": ["collection:opensource", "mediatype:texts", "subject:Drama"],
        "adventure": ["collection:opensource", "mediatype:texts", "subject:Adventure"],
        "mystery": ["collection:opensource", "mediatype:texts", "subject:Mystery"],
        "science_fiction": ["collection:opensource", "mediatype:texts", "subject:Science Fiction"],
        "classic": ["collection:opensource", "mediatype:texts", "collection:americana"],
    }
    
    # Popular collections for default selection
    DEFAULT_COLLECTIONS = [
        "opensource",  # Open source books
        "americana",  # American literature
        "librivoxaudio",  # LibriVox audiobooks (may have text)
    ]
    
    def get_source_name(self) -> str:
        return "internetarchive"
    
    def get_available_categories(self) -> List[str]:
        return list(self.CATEGORY_MAPPINGS.keys())
    
    def supports_categories(self) -> bool:
        return True
    
    def supports_book_ids(self) -> bool:
        return True  # Uses IA item identifiers
    
    def _build_search_query(self, categories: Optional[List[str]] = None) -> str:
        """Build Internet Archive search query from categories"""
        query_parts = ["mediatype:texts"]
        
        if categories:
            # Collect collections and subjects separately
            collections = []
            subjects = []
            
            for category in categories:
                if category in self.CATEGORY_MAPPINGS:
                    # Use the first mapping (collection or subject)
                    mapping = self.CATEGORY_MAPPINGS[category][0]
                    if mapping.startswith("collection:"):
                        collections.append(mapping)
                    elif mapping.startswith("subject:"):
                        subjects.append(mapping)
            
            # Add collections (use first one if multiple)
            if collections:
                query_parts.append(collections[0])
            else:
                # Default to opensource collection
                query_parts.append("collection:opensource")
            
            # Add subjects (combine with OR if multiple)
            if subjects:
                if len(subjects) == 1:
                    query_parts.append(subjects[0])
                else:
                    # Multiple subjects: use OR grouping
                    subject_query = "(" + " OR ".join(subjects) + ")"
                    query_parts.append(subject_query)
        else:
            # Default to opensource collection
            query_parts.append("collection:opensource")
        
        return " AND ".join(query_parts)
    
    def _extract_text_from_item(self, item, cache_file: Path) -> Optional[str]:
        """Extract text from an Internet Archive item"""
        try:
            # Look for text files in the item
            text_files = []
            for file in item.files:
                # Prefer plain text files
                if file.format in ["Text", "Plain Text", "TXT"] or file.name.endswith(('.txt', '.text')):
                    text_files.append(file)
                # Also consider other text formats
                elif file.format in ["DjVuTXT", "EPUB", "PDF"]:
                    text_files.append(file)
            
            # Sort by preference: .txt files first, then others
            text_files.sort(key=lambda f: (not f.name.endswith('.txt'), f.name))
            
            if not text_files:
                # Try to get any text-like file
                for file in item.files:
                    if file.format and "text" in file.format.lower():
                        text_files.append(file)
                        break
            
            if not text_files:
                # Use metadata as fallback
                title = item.metadata.get('title', 'Unknown')
                description = item.metadata.get('description', '')
                if isinstance(description, list):
                    description = ' '.join(description)
                return f"{title}\n\n{description}"
            
            # Download the first text file
            text_file = text_files[0]
            
            # Download to cache directory
            download_dir = cache_file.parent
            download_dir.mkdir(parents=True, exist_ok=True)
            
            # Download the file (IA library creates subdirectory with item identifier)
            try:
                item.download(
                    files=[text_file.name],
                    destdir=str(download_dir),
                    verbose=False,
                    ignore_existing=True,
                )
                
                # IA library creates a subdirectory with the item identifier
                downloaded_path = download_dir / item.identifier / text_file.name
                
                # Also check if file was downloaded directly (some versions)
                if not downloaded_path.exists():
                    downloaded_path = download_dir / text_file.name
                
                if downloaded_path.exists():
                    with open(downloaded_path, "r", encoding="utf-8", errors="ignore") as f:
                        text = f.read()
                    
                    # Save to cache
                    with open(cache_file, "w", encoding="utf-8") as f:
                        f.write(text)
                    
                    return text
            except Exception as download_error:
                # If download fails, try to get text via API
                print(
                    f"[InternetArchiveSource] Download failed for {item.identifier}, trying API: {download_error}",
                    file=sys.stderr,
                )
                # Fall through to metadata fallback
            
        except Exception as e:
            print(
                f"[InternetArchiveSource] Error extracting text from {item.identifier}: {e}",
                file=sys.stderr,
            )
        
        return None
    
    def load_data(
        self,
        book_ids: Optional[List[Any]] = None,
        max_books: int = 3,
        categories: Optional[List[str]] = None,
        max_text_size: Optional[int] = None,
        data_dir: Optional[Path] = None,
        search: Optional[str] = None,
    ) -> str:
        """Load Internet Archive items"""
        if not INTERNETARCHIVE_AVAILABLE:
            fallback_text = (
                "Internet Archive library not available. "
                "Install with: pip install internetarchive "
            ) * 50
            if max_text_size:
                return fallback_text[:max_text_size]
            return fallback_text
        
        cache_dir = self._get_cache_dir(data_dir, "internetarchive")
        all_text = []
        
        # If specific item identifiers provided, use those
        if book_ids:
            for item_id in book_ids[:max_books]:
                cache_file = cache_dir / f"{item_id}.txt"
                
                # Try cache first
                if cache_file.exists():
                    try:
                        with open(cache_file, "r", encoding="utf-8") as f:
                            text = f.read()
                            if text:
                                all_text.append(text)
                                continue
                    except Exception:
                        pass
                
                try:
                    item = get_item(str(item_id))
                    text = self._extract_text_from_item(item, cache_file)
                    if text:
                        all_text.append(text)
                    time.sleep(0.5)  # Rate limiting
                except Exception as e:
                    print(
                        f"[InternetArchiveSource] Failed to load item {item_id}: {e}",
                        file=sys.stderr,
                    )
        else:
            # Search for items based on categories
            query = self._build_search_query(categories)
            
            try:
                # Search for items
                search = search_items(
                    query,
                    fields=["identifier", "title", "mediatype"],
                    params={"rows": max_books * 2},  # Get extra in case some fail
                )
                
                item_count = 0
                for result in search:
                    if item_count >= max_books:
                        break
                    
                    item_id = result.get("identifier")
                    if not item_id:
                        continue
                    
                    cache_file = cache_dir / f"{item_id}.txt"
                    
                    # Try cache first
                    if cache_file.exists():
                        try:
                            with open(cache_file, "r", encoding="utf-8") as f:
                                text = f.read()
                                if text:
                                    all_text.append(text)
                                    item_count += 1
                                    continue
                        except Exception:
                            pass
                    
                    try:
                        item = get_item(item_id)
                        text = self._extract_text_from_item(item, cache_file)
                        if text:
                            all_text.append(text)
                            item_count += 1
                        time.sleep(0.5)  # Rate limiting
                    except Exception as e:
                        print(
                            f"[InternetArchiveSource] Failed to load item {item_id}: {e}",
                            file=sys.stderr,
                        )
                        continue
            except Exception as e:
                print(
                    f"[InternetArchiveSource] Search failed: {e}",
                    file=sys.stderr,
                )
        
        if not all_text:
            # Fallback text
            fallback_text = (
                "Internet Archive provides access to millions of texts. "
                "This is sample text when Internet Archive data is unavailable. "
            ) * 50
            if max_text_size:
                return fallback_text[:max_text_size]
            return fallback_text
        
        combined_text = "\n\n".join(all_text)
        
        # Limit text size if specified
        if max_text_size and len(combined_text) > max_text_size:
            combined_text = combined_text[:max_text_size]
        
        return combined_text


class DataSourceRegistry:
    """Registry for managing data sources"""
    
    def __init__(self):
        self._sources: Dict[str, BaseDataSource] = {}
        self._register_default_sources()
    
    def _register_default_sources(self):
        """Register all available data sources"""
        self.register(GutenbergSource())
        self.register(WikipediaSource())
        self.register(LibriVoxSource())
        self.register(OpenLibrarySource())
        if INTERNETARCHIVE_AVAILABLE:
            self.register(InternetArchiveSource())
        # Always register HuggingFace source (will fail gracefully if library not available)
        try:
            self.register(HuggingFaceSource())
        except Exception as e:
            print(
                f"[DataSourceRegistry] Warning: Could not register HuggingFace source: {e}",
                file=sys.stderr,
            )
    
    def register(self, source: BaseDataSource):
        """Register a data source"""
        self._sources[source.get_source_name()] = source
    
    def get_source(self, name: str) -> Optional[BaseDataSource]:
        """Get a data source by name"""
        return self._sources.get(name.lower())
    
    def list_sources(self) -> List[str]:
        """List all registered source names"""
        return list(self._sources.keys())
    
    def load_data(
        self,
        sources: Union[str, List[str]],
        book_ids: Optional[List[Any]] = None,
        max_books: int = 3,
        categories: Optional[List[str]] = None,
        max_text_size: Optional[int] = None,
        data_dir: Optional[Path] = None,
        search: Optional[str] = None,
    ) -> str:
        """
        Load data from one or more sources
        
        Args:
            sources: Single source name or list of source names
            book_ids: Source-specific identifiers
            max_books: Maximum items per source
            categories: Category filters
            max_text_size: Maximum total text size
            data_dir: Cache directory
        
        Returns:
            Combined text from all sources
        """
        if isinstance(sources, str):
            source_names = [sources]
        else:
            source_names = sources
        
        all_texts = []
        
        for source_name in source_names:
            source = self.get_source(source_name)
            if source is None:
                print(
                    f"[DataSourceRegistry] Unknown source: {source_name}, skipping",
                    file=sys.stderr,
                )
                continue
            
            # Progress logging so long-running downloads don't look like a hang
            print(
                f"[DataSourceRegistry] Loading data from source '{source_name}'...",
                file=sys.stderr,
            )
            start_time = time.time()
            try:
                text = source.load_data(
                    book_ids=book_ids,
                    max_books=max_books,
                    categories=categories,
                    max_text_size=None,  # Don't limit per source
                    data_dir=data_dir,
                    search=search,
                )
                duration = time.time() - start_time
                print(
                    f"[DataSourceRegistry] Finished source '{source_name}' in {duration:.1f}s "
                    f"({len(text) if text else 0:,} chars)",
                    file=sys.stderr,
                )
                if text:
                    all_texts.append(text)
            except Exception as e:
                duration = time.time() - start_time
                print(
                    f"[DataSourceRegistry] Error loading from {source_name} after {duration:.1f}s: {e}",
                    file=sys.stderr,
                )
        
        if not all_texts:
            # Fallback
            fallback_text = (
                "No data could be loaded from the specified sources. "
                "This is fallback text for training. "
            ) * 100
            if max_text_size:
                return fallback_text[:max_text_size]
            return fallback_text
        
        combined_text = "\n\n".join(all_texts)
        
        # Apply global max_text_size limit
        if max_text_size and len(combined_text) > max_text_size:
            combined_text = combined_text[:max_text_size]
        
        return combined_text


def _load_api_keys() -> Dict[str, Any]:
    """Load API keys from config file or environment variables"""
    api_keys = {}
    
    # Try to load from config file
    config_path = Path(__file__).parent.parent.parent / "data" / "api_keys.json"
    if config_path.exists():
        try:
            with open(config_path, "r", encoding="utf-8") as f:
                api_keys = json.load(f)
        except Exception as e:
            print(
                f"[NeuralTextGeneratorData] Warning: Could not load API keys from config: {e}",
                file=sys.stderr,
            )
    
    # Override with environment variables (environment takes precedence)
    if os.getenv("MAVAIA_HUGGINGFACE_TOKEN"):
        if "huggingface" not in api_keys:
            api_keys["huggingface"] = {}
        api_keys["huggingface"]["token"] = os.getenv("MAVAIA_HUGGINGFACE_TOKEN")
    
    if os.getenv("HF_TOKEN"):  # Also check standard HF env var
        if "huggingface" not in api_keys:
            api_keys["huggingface"] = {}
        api_keys["huggingface"]["token"] = os.getenv("HF_TOKEN")
    
    return api_keys


class HuggingFaceSource(BaseDataSource):
    """HuggingFace datasets data source"""
    
    # HuggingFace dataset category mappings
    CATEGORY_MAPPINGS = {
        "fiction": [
            "bookcorpus",
            "wikitext",
            "stories",
        ],
        "non_fiction": [
            "wikipedia",
            "scientific_papers",
            "news",
        ],
        "technical": [
            "code",
            "scientific_papers",
            "stackexchange",
        ],
        "philosophy": [
            "philosophy",
            "books",
        ],
        "poetry": [
            "poetry",
            "literature",
        ],
        "drama": [
            "drama",
            "theatre",
        ],
        "adventure": [
            "stories",
            "books",
        ],
        "mystery": [
            "stories",
            "books",
        ],
        "science_fiction": [
            "science_fiction",
            "stories",
        ],
        "classic": [
            "books",
            "literature",
        ],
    }
    
    # Popular text datasets for default selection
    DEFAULT_DATASETS = [
        "wikitext",  # Wikipedia text
        "bookcorpus",  # Books corpus
        "openwebtext",  # Open web text
    ]
    
    def get_source_name(self) -> str:
        return "huggingface"
    
    def get_available_categories(self) -> List[str]:
        return list(self.CATEGORY_MAPPINGS.keys())
    
    def supports_categories(self) -> bool:
        return True
    
    def supports_book_ids(self) -> bool:
        return True  # Uses dataset names/IDs
    
    def _setup_huggingface_auth(self):
        """Setup HuggingFace authentication from API keys"""
        if not HUGGINGFACE_AVAILABLE:
            return
        
        api_keys = _load_api_keys()
        hf_token = None
        
        if "huggingface" in api_keys:
            hf_token = api_keys["huggingface"].get("token")
        
        if hf_token:
            os.environ["HF_TOKEN"] = hf_token
            os.environ["HUGGING_FACE_HUB_TOKEN"] = hf_token
    
    def _search_datasets(self, query: str, max_results: int = 10) -> List[str]:
        """Search for datasets on HuggingFace"""
        if not HUGGINGFACE_AVAILABLE or not HF_API_AVAILABLE:
            return []
        
        try:
            from huggingface_hub import HfApi
            api = HfApi()
            datasets = api.list_datasets(search=query, limit=max_results)
            return [ds.id for ds in datasets]
        except Exception as e:
            print(
                f"[HuggingFaceSource] Dataset search failed: {e}",
                file=sys.stderr,
            )
            return []
    
    def _load_dataset_text(self, dataset_name: str, cache_file: Path, max_text_size: Optional[int] = None) -> Optional[str]:
        """
        Load text from a HuggingFace dataset
        
        Supports full dataset paths like "Anthropic/AnthropicInterviewer" or simple names like "wikitext".
        Automatically handles different dataset configurations and splits.
        
        Args:
            dataset_name: Dataset identifier (e.g., "wikitext", "Anthropic/AnthropicInterviewer")
            cache_file: Path to cache file for storing loaded text
            max_text_size: Maximum text size to load (None = no limit)
        
        Returns:
            Combined text from dataset or None if loading failed
        """
        if not HUGGINGFACE_AVAILABLE:
            return None
        
        try:
            # Lazily import HuggingFace datasets only when actually needed
            try:
                from datasets import load_dataset  # type: ignore[import]
            except Exception as e:
                print(
                    f"[HuggingFaceSource] Failed to import datasets library: {e}",
                    file=sys.stderr,
                )
                return None
            
            # Try to load dataset - handle different formats
            # Some datasets require config names, others don't
            dataset = None
            error_msg = None
            
            # First, try loading with "train" split (most common)
            try:
                dataset = load_dataset(dataset_name, split="train", streaming=False)
            except Exception as e1:
                error_msg = str(e1)
                # If that fails, try loading without split (gets all splits)
                try:
                    dataset_dict = load_dataset(dataset_name, streaming=False)
                    # Try to find train split
                    if "train" in dataset_dict:
                        dataset = dataset_dict["train"]
                    elif len(dataset_dict) > 0:
                        # Use first available split
                        first_split = list(dataset_dict.keys())[0]
                        dataset = dataset_dict[first_split]
                        print(
                            f"[HuggingFaceSource] Using split '{first_split}' for dataset {dataset_name}",
                            file=sys.stderr,
                        )
                    else:
                        raise ValueError(f"No splits available in dataset {dataset_name}")
                except Exception:
                    # If that also fails, try with default config
                    try:
                        dataset_dict = load_dataset(dataset_name, split="train", streaming=False)
                        dataset = dataset_dict
                    except Exception:
                        # Last attempt: try loading with trust_remote_code for custom datasets
                        try:
                            dataset = load_dataset(
                                dataset_name,
                                split="train",
                                streaming=False,
                                trust_remote_code=True,
                            )
                        except Exception:
                            print(
                                f"[HuggingFaceSource] Failed to load dataset {dataset_name}: {error_msg}",
                                file=sys.stderr,
                            )
                            print(
                                "[HuggingFaceSource] Attempted: default split, all splits, and trust_remote_code=True",
                                file=sys.stderr,
                            )
                            return None
            
            if dataset is None:
                return None
            
            all_text = []
            text_columns = [
                "text", "content", "article", "sentence", "body", "passage",
                "input", "output", "prompt", "response", "message", "messages",
                "conversation", "dialogue", "transcript", "transcription"
            ]
            
            # Find text column
            text_column = None
            for col in text_columns:
                if col in dataset.column_names:
                    text_column = col
                    break
            
            if not text_column:
                # Use first column that looks like text
                for col in dataset.column_names:
                    if len(dataset) > 0:
                        sample_value = dataset[0].get(col)
                        if sample_value and isinstance(sample_value, str) and len(sample_value) > 10:
                            text_column = col
                            break
            
            if not text_column:
                # Fallback: try to find any string column
                for col in dataset.column_names:
                    if len(dataset) > 0:
                        sample_value = dataset[0].get(col)
                        if isinstance(sample_value, str):
                            text_column = col
                            break
            
            if not text_column:
                # Last resort: check if dataset has nested structures (like conversations)
                # Try to extract text from nested fields
                if len(dataset) > 0:
                    first_example = dataset[0]
                    # Check for common nested structures
                    for col in dataset.column_names:
                        value = first_example.get(col)
                        if isinstance(value, list) and len(value) > 0:
                            # Might be a list of messages/conversations
                            if isinstance(value[0], dict):
                                # Try to extract text from dict items
                                for item in value:
                                    if isinstance(item, dict):
                                        # Look for text-like keys
                                        for key in ["text", "content", "message", "role", "value"]:
                                            if key in item and isinstance(item[key], str):
                                                # Found nested text - we'll handle this specially
                                                text_column = col
                                                break
                                        if text_column:
                                            break
                        if text_column:
                            break
            
            if not text_column:
                print(
                    f"[HuggingFaceSource] Could not find text column in dataset {dataset_name}. "
                    f"Available columns: {dataset.column_names}",
                    file=sys.stderr,
                )
                return None
            
            print(
                f"[HuggingFaceSource] Using column '{text_column}' for dataset {dataset_name}",
                file=sys.stderr,
            )
            
            # Extract text from dataset
            for idx, example in enumerate(dataset):
                try:
                    if text_column in example:
                        value = example[text_column]
                        
                        # Handle different value types
                        if isinstance(value, str):
                            text = value.strip()
                            if text:
                                all_text.append(text)
                        elif isinstance(value, list):
                            # Handle list of strings or list of dicts
                            for item in value:
                                if isinstance(item, str):
                                    text = item.strip()
                                    if text:
                                        all_text.append(text)
                                elif isinstance(item, dict):
                                    # Extract text from dict (e.g., conversation messages)
                                    for key in ["text", "content", "message", "value"]:
                                        if key in item and isinstance(item[key], str):
                                            text = item[key].strip()
                                            if text:
                                                all_text.append(text)
                                            break
                    else:
                        # Try to extract from nested structure
                        # This handles cases where the column contains nested data
                        pass
                
                except Exception as e:
                    # Skip problematic examples but continue
                    if idx < 5:  # Only log first few errors to avoid spam
                        print(
                            f"[HuggingFaceSource] Warning: Skipping example {idx} in {dataset_name}: {e}",
                            file=sys.stderr,
                        )
                    continue
                
                # Limit total text size
                if max_text_size:
                    current_size = sum(len(t) for t in all_text)
                    if current_size >= max_text_size:
                        break
            
            if not all_text:
                print(
                    f"[HuggingFaceSource] No text extracted from dataset {dataset_name}",
                    file=sys.stderr,
                )
                return None
            
            combined_text = "\n\n".join(all_text)
            
            # Save to cache
            try:
                with open(cache_file, "w", encoding="utf-8") as f:
                    f.write(combined_text)
            except Exception as e:
                print(
                    f"[HuggingFaceSource] Warning: Could not save cache for {dataset_name}: {e}",
                    file=sys.stderr,
                )
            
            print(
                f"[HuggingFaceSource] Loaded {len(all_text)} examples ({len(combined_text):,} characters) from {dataset_name}",
                file=sys.stderr,
            )
            
            return combined_text
            
        except Exception as e:
            print(
                f"[HuggingFaceSource] Failed to load dataset {dataset_name}: {e}",
                file=sys.stderr,
            )
            import traceback
            if "not found" in str(e).lower() or "does not exist" in str(e).lower():
                print(
                    f"[HuggingFaceSource] Hint: Make sure the dataset name is correct. "
                    f"For datasets with organization (e.g., 'Anthropic/AnthropicInterviewer'), "
                    f"use the full path: 'organization/dataset_name'",
                    file=sys.stderr,
                )
            return None
    
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
        if not HUGGINGFACE_AVAILABLE:
            error_msg = (
                "HuggingFace datasets library not available. "
                "Install with: pip install datasets huggingface_hub"
            )
            print(f"[HuggingFaceSource] {error_msg}", file=sys.stderr)
            fallback_text = error_msg * 10
            if max_text_size:
                return fallback_text[:max_text_size]
            return fallback_text
        
        # Setup authentication
        self._setup_huggingface_auth()
        
        cache_dir = self._get_cache_dir(data_dir, "huggingface")
        all_text = []
        
        # If specific dataset names provided, use those (takes precedence over search)
        if book_ids:
            print(
                f"[HuggingFaceSource] Loading {len(book_ids[:max_books])} specified dataset(s)...",
                file=sys.stderr,
            )
            for dataset_name in book_ids[:max_books]:
                # Clean dataset name - preserve full paths like "Anthropic/AnthropicInterviewer"
                dataset_id = str(dataset_name).strip()
                
                # Create safe cache filename (replace / with _ but keep original for loading)
                safe_filename = dataset_id.replace('/', '_').replace('\\', '_')
                cache_file = cache_dir / f"{safe_filename}.txt"
                
                print(
                    f"[HuggingFaceSource] Loading dataset: {dataset_id}",
                    file=sys.stderr,
                )
                
                # Try cache first
                if cache_file.exists():
                    try:
                        with open(cache_file, "r", encoding="utf-8") as f:
                            text = f.read()
                            if text:
                                all_text.append(text)
                                print(
                                    f"[HuggingFaceSource] ✓ Loaded {dataset_id} from cache ({len(text):,} characters)",
                                    file=sys.stderr,
                                )
                                continue
                    except Exception:
                        pass
                
                # Load dataset from HuggingFace Hub
                text = self._load_dataset_text(dataset_id, cache_file, max_text_size)
                if text:
                    all_text.append(text)
                else:
                    print(
                        f"[HuggingFaceSource] ✗ Failed to load dataset {dataset_id}",
                        file=sys.stderr,
                    )
        else:
            # Search for datasets
            dataset_names = []
            
            # If search term provided, use it
            if search:
                print(
                    f"[HuggingFaceSource] Searching for datasets: '{search}'",
                    file=sys.stderr,
                )
                search_results = self._search_datasets(search, max_results=max_books * 2)
                dataset_names.extend(search_results)
            
            # Also search based on categories if provided
            if categories:
                for category in categories:
                    if category in self.CATEGORY_MAPPINGS:
                        # Search for datasets matching category keywords
                        for keyword in self.CATEGORY_MAPPINGS[category]:
                            search_results = self._search_datasets(keyword, max_results=2)
                            dataset_names.extend(search_results)
            
            # If no search or categories, use default datasets
            if not dataset_names and not search:
                dataset_names = self.DEFAULT_DATASETS[:max_books]
            
            # Remove duplicates while preserving order
            seen = set()
            unique_datasets = []
            for ds in dataset_names:
                if ds not in seen:
                    seen.add(ds)
                    unique_datasets.append(ds)
            
            # Load datasets
            for dataset_name in unique_datasets[:max_books]:
                cache_file = cache_dir / f"{dataset_name.replace('/', '_')}.txt"
                
                # Try cache first
                if cache_file.exists():
                    try:
                        with open(cache_file, "r", encoding="utf-8") as f:
                            text = f.read()
                            if text:
                                all_text.append(text)
                                continue
                    except Exception:
                        pass
                
                # Load dataset
                text = self._load_dataset_text(dataset_name, cache_file, max_text_size)
                if text:
                    all_text.append(text)
        
        if not all_text:
            # Fallback text
            fallback_text = (
                "HuggingFace provides access to thousands of datasets. "
                "This is sample text when HuggingFace data is unavailable. "
                "Install datasets library and optionally set HF_TOKEN for private datasets. "
            ) * 50
            if max_text_size:
                return fallback_text[:max_text_size]
            return fallback_text
        
        combined_text = "\n\n".join(all_text)
        
        # Limit text size if specified
        if max_text_size and len(combined_text) > max_text_size:
            combined_text = combined_text[:max_text_size]
        
        return combined_text


# Global registry instance
_registry = DataSourceRegistry()


class NeuralTextGeneratorData:
    """Data loading and preprocessing for neural text generation"""
    
    @staticmethod
    def get_books_by_category(categories: List[str]) -> List[int]:
        """
        Get book IDs for specified categories (Gutenberg-specific)
        
        Args:
            categories: List of category names (e.g., ["fiction", "technical"])
        
        Returns:
            List of book IDs
        """
        gutenberg_source = _registry.get_source("gutenberg")
        if gutenberg_source and isinstance(gutenberg_source, GutenbergSource):
            return gutenberg_source.get_books_by_category(categories)
        return []
    
    @staticmethod
    def load_data(
        source: Union[str, List[str], None] = None,
        book_ids: Optional[List[Any]] = None,
        max_books: int = 3,
        categories: Optional[List[str]] = None,
        max_text_size: Optional[int] = None,
        data_dir: Optional[Path] = None,
        search: Optional[str] = None,
    ) -> str:
        """
        Load data from specified source(s)
        
        Args:
            source: Source name(s) - "gutenberg", "wikipedia", "librivox", "openlibrary", 
                    "internetarchive", "huggingface", or list of sources. Defaults to "gutenberg" for backward compatibility.
            book_ids: Source-specific identifiers (Gutenberg IDs, article titles, IA item IDs, HF dataset names, etc.)
            max_books: Maximum number of items to load per source
            categories: List of categories to load from (source-specific)
            max_text_size: Maximum text size in characters (None = no limit)
            data_dir: Directory to cache downloaded data
        
        Returns:
            Combined text from all sources (limited to max_text_size if specified)
        """
        if source is None:
            source = "gutenberg"  # Default for backward compatibility
        
        return _registry.load_data(
            sources=source,
            book_ids=book_ids,
            max_books=max_books,
            categories=categories,
            max_text_size=max_text_size,
            data_dir=data_dir,
            search=search,
        )
    
    @staticmethod
    def load_gutenberg_data(
        book_ids: Optional[List[int]] = None,
        max_books: int = 3,
        data_dir: Optional[Path] = None,
        categories: Optional[List[str]] = None,
        max_text_size: Optional[int] = None,
    ) -> str:
        """
        Load Project Gutenberg books (backward compatibility method)
        
        Args:
            book_ids: Specific book IDs to load (e.g., [84, 1342] for Frankenstein, Pride and Prejudice)
            max_books: Maximum number of books to load if book_ids not specified
            data_dir: Directory to cache downloaded books
            categories: List of categories to load books from (e.g., ["fiction", "technical"])
            max_text_size: Maximum text size in characters (None = no limit)
        
        Returns:
            Combined text from all books (limited to max_text_size if specified)
        """
        return NeuralTextGeneratorData.load_data(
            source="gutenberg",
            book_ids=book_ids,
            max_books=max_books,
            categories=categories,
            max_text_size=max_text_size,
            data_dir=data_dir,
        )
    
    @staticmethod
    def list_available_sources() -> List[str]:
        """List all available data sources"""
        return _registry.list_sources()
    
    @staticmethod
    def get_source_info(source_name: str) -> Optional[Dict[str, Any]]:
        """Get information about a data source"""
        source = _registry.get_source(source_name)
        if source is None:
            return None
        
        return {
            "name": source.get_source_name(),
            "categories": source.get_available_categories(),
            "supports_categories": source.supports_categories(),
            "supports_book_ids": source.supports_book_ids(),
        }

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

