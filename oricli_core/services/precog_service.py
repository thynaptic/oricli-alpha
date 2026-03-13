import time
import threading
from typing import Dict, Any, Optional, List

class PreCogService:
    """
    Manages the cache of speculative responses for anticipated user queries.
    """
    _instance = None
    _lock = threading.Lock()
    
    def __new__(cls):
        with cls._lock:
            if cls._instance is None:
                cls._instance = super(PreCogService, cls).__new__(cls)
                cls._instance._initialized = False
            return cls._instance

    def __init__(self):
        if self._initialized:
            return
        self._cache: Dict[str, Dict[str, Any]] = {}
        self._cache_lock = threading.Lock()
        self.ttl_seconds = 600 # 10 minutes
        self._initialized = True

    def cache_speculative_response(self, query: str, response: Dict[str, Any]):
        """
        Store a pre-computed response for a potential future query.
        """
        query_key = self._normalize_query(query)
        with self._cache_lock:
            self._cache[query_key] = {
                "response": response,
                "timestamp": time.time(),
                "original_query": query
            }

    def get_cached_response(self, query: str) -> Optional[Dict[str, Any]]:
        """
        Check for a speculative response. Uses exact and fuzzy matching.
        """
        query_key = self._normalize_query(query)
        
        with self._cache_lock:
            # 1. Cleanup expired entries
            self._cleanup_expired()
            
            # 2. Exact match
            if query_key in self._cache:
                entry = self._cache[query_key]
                print(f"[Pre-Cog] Cache HIT (Exact): {query}")
                return entry["response"]
            
            # 3. Fuzzy match (Jaccard similarity or simple inclusion)
            for cached_key, entry in self._cache.items():
                if self._is_similar(query_key, cached_key):
                    print(f"[Pre-Cog] Cache HIT (Fuzzy): {query} matched '{entry['original_query']}'")
                    return entry["response"]
                    
        return None

    def _normalize_query(self, query: str) -> str:
        import re
        # Lowercase, remove punctuation, strip whitespace
        return re.sub(r'[^a-z0-9\s]', '', query.lower()).strip()

    def _is_similar(self, q1: str, q2: str) -> bool:
        # 1. Token-based Jaccard similarity
        words1 = set(q1.split())
        words2 = set(q2.split())
        if not words1 or not words2:
            return False
            
        intersection = words1.intersection(words2)
        union = words1.union(words2)
        jaccard = len(intersection) / len(union)
        
        if jaccard > 0.5:
            return True
            
        # 2. Keyword Fallback (if all unique keywords match)
        stopwords = {'how', 'do', 'i', 'is', 'a', 'the', 'what', 'can', 'you', 'me', 'to'}
        keywords1 = words1 - stopwords
        keywords2 = words2 - stopwords
        
        if keywords1 and keywords2 and keywords1 == keywords2:
            return True
            
        return False

    def _cleanup_expired(self):
        now = time.time()
        expired_keys = [
            k for k, v in self._cache.items() 
            if now - v["timestamp"] > self.ttl_seconds
        ]
        for k in expired_keys:
            del self._cache[k]

    def clear(self):
        """Clear the entire cache."""
        with self._cache_lock:
            self._cache.clear()
