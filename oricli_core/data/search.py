import os
import logging
from typing import List, Dict, Any, Optional
from dataclasses import dataclass
from pathlib import Path

logger = logging.getLogger(__name__)

# Try to load environment variables from .env if available
try:
    from dotenv import load_dotenv
    # Search for .env in current dir or up to two levels up (project root)
    dotenv_path = Path(".env")
    if not dotenv_path.exists():
        dotenv_path = Path(__file__).resolve().parent.parent.parent / ".env"
    
    if dotenv_path.exists():
        load_dotenv(dotenv_path)
except ImportError:
    pass

@dataclass
class SearchResult:
    id: str
    name: str
    source: str
    description: str
    size_bytes: Optional[int] = None
    popularity_score: float = 0.0
    relevance_score: float = 0.0
    combined_score: float = 0.0
    config: Optional[str] = None
    gated: bool = False

class DatasetSearch:
    """Service for searching datasets across multiple sources."""

    def __init__(self):
        self.hf_api = None
        self.kaggle_api = None
        self._setup_hf()
        self._setup_kaggle()

    def _setup_hf(self):
        try:
            from huggingface_hub import HfApi
            self.hf_api = HfApi()
        except ImportError:
            logger.debug("huggingface_hub package missing, HF search disabled")
        except Exception as e:
            logger.warning(f"HF search disabled: failed to initialize HfApi: {e}")

    def _setup_kaggle(self):
        # Map KAGGLE_API_TOKEN to KAGGLE_KEY if needed
        if os.environ.get("KAGGLE_API_TOKEN") and not os.environ.get("KAGGLE_KEY"):
            os.environ["KAGGLE_KEY"] = os.environ["KAGGLE_API_TOKEN"]
            
        try:
            from kaggle.api.kaggle_api_extended import KaggleApi
            self.kaggle_api = KaggleApi()
            # This will look for ~/.kaggle/kaggle.json or KAGGLE_USERNAME/KAGGLE_KEY env vars
            try:
                self.kaggle_api.authenticate()
            except Exception as auth_err:
                # If authentication fails, we don't want to crash the whole search service
                logger.warning(f"Kaggle authentication failed: {auth_err}")
                self.kaggle_api = None
        except ImportError:
            logger.debug("kaggle package missing, Kaggle search disabled")
        except Exception as e:
            logger.warning(f"Kaggle search disabled: unexpected error: {e}")
            self.kaggle_api = None

    def search_huggingface(self, query: str, limit: int = 10) -> List[SearchResult]:
        """Search Hugging Face for datasets."""
        results = []
        if not self.hf_api:
            return results

        try:
            # Simple search using string query
            datasets = self.hf_api.list_datasets(
                search=query,
                sort="downloads",
                limit=limit * 2 # Get more to filter
            )

            for ds in datasets:
                # Check for gated status
                is_gated = getattr(ds, "gated", False)
                if isinstance(is_gated, str):
                    is_gated = is_gated.lower() not in ("false", "no", "0", "")
                
                results.append(SearchResult(
                    id=ds.id,
                    name=ds.id.split("/")[-1],
                    source="huggingface",
                    description=getattr(ds, "description", "") or "",
                    size_bytes=None, # list_datasets doesn't always provide size
                    popularity_score=float(getattr(ds, "downloads", 0)),
                    gated=bool(is_gated)
                ))
        except Exception as e:
            logger.error(f"HF search failed: {e}")

        return results

    def search_kaggle(self, query: str, limit: int = 5) -> List[SearchResult]:
        """Search Kaggle for datasets."""
        results = []
        if not self.kaggle_api:
            return results

        try:
            # Search datasets
            datasets = self.kaggle_api.dataset_list(search=query)
            
            for ds in datasets[:limit]:
                # Safer attribute access for Kaggle datasets
                ref = getattr(ds, "ref", str(ds))
                title = getattr(ds, "title", ref)
                owner = getattr(ds, "ownerRef", "unknown")
                downloads = getattr(ds, "downloadCount", 0)
                size = getattr(ds, "totalBytes", None)
                
                results.append(SearchResult(
                    id=f"kaggle::{ref}",
                    name=title,
                    source="kaggle",
                    description=f"Kaggle Dataset: {title} by {owner}",
                    popularity_score=float(downloads),
                    size_bytes=size
                ))
        except Exception as e:
            logger.error(f"Kaggle search failed: {e}")

        return results

    def search_wikipedia(self, query: str, limit: int = 5) -> List[SearchResult]:
        """Search Wikipedia for articles."""
        results = []
        try:
            import wikipedia
            search_titles = wikipedia.search(query, results=limit)
            for title in search_titles:
                try:
                    # We don't want to download the whole page here, just enough for metadata
                    # wikipedia.summary(title, sentences=1)
                    results.append(SearchResult(
                        id=f"wikipedia::{title}",
                        name=title,
                        source="wikipedia",
                        description=f"Wikipedia article: {title}",
                        popularity_score=1.0, # Wikipedia articles are implicitly "popular"
                    ))
                except Exception:
                    continue
        except ImportError:
            logger.warning("wikipedia package not installed")
        except Exception as e:
            logger.error(f"Wikipedia search failed: {e}")

        return results

    def search_internet_archive(self, query: str, limit: int = 5) -> List[SearchResult]:
        """Search Internet Archive for items."""
        results = []
        try:
            from internetarchive import search_items
            # Simple search
            items = search_items(f"title:({query}) AND mediatype:texts")
            count = 0
            for item in items:
                if count >= limit:
                    break
                results.append(SearchResult(
                    id=f"internetarchive::{item['identifier']}",
                    name=item.get('title', item['identifier']),
                    source="internetarchive",
                    description=item.get('description', ""),
                    popularity_score=float(item.get('downloads', 0)),
                ))
                count += 1
        except ImportError:
            logger.warning("internetarchive package not installed")
        except Exception as e:
            logger.error(f"Internet Archive search failed: {e}")

        return results

    def search_all(self, query: str, limit_per_source: int = 5) -> List[SearchResult]:
        """Search all sources and combine results with ranking."""
        all_results = []
        all_results.extend(self.search_huggingface(query, limit=limit_per_source))
        all_results.extend(self.search_kaggle(query, limit=limit_per_source))
        all_results.extend(self.search_wikipedia(query, limit=limit_per_source))
        all_results.extend(self.search_internet_archive(query, limit=limit_per_source))
        
        return self.rank_results(query, all_results)

    def rank_results(self, query: str, results: List[SearchResult]) -> List[SearchResult]:
        """Rank results based on relevance and popularity."""
        if not results:
            return []

        # 1. Normalize popularity scores (0.0 to 1.0)
        pop_scores = [r.popularity_score for r in results]
        max_pop = max(pop_scores) if pop_scores else 1.0
        if max_pop == 0: max_pop = 1.0

        for r in results:
            # Source-specific popularity normalization
            if r.source == "wikipedia":
                # Wikipedia articles are high-quality, give them a baseline popularity
                norm_pop = 0.8
            else:
                norm_pop = r.popularity_score / max_pop
            
            # 2. Calculate relevance score (lexical match for now)
            # Simple word overlap check
            query_words = set(query.lower().split())
            name_words = set(r.name.lower().replace("_", " ").replace("-", " ").split())
            desc_words = set(r.description.lower().split())
            
            # Match in name is worth more
            name_match = len(query_words.intersection(name_words)) / len(query_words) if query_words else 0
            desc_match = len(query_words.intersection(desc_words)) / len(query_words) if query_words else 0
            
            relevance = (name_match * 0.7) + (desc_match * 0.3)
            
            # 3. Combined score
            # Weights: 60% relevance, 40% popularity
            r.relevance_score = relevance
            r.combined_score = (relevance * 0.6) + (norm_pop * 0.4)

        # Sort by combined score descending
        ranked = sorted(results, key=lambda x: x.combined_score, reverse=True)
        return ranked
