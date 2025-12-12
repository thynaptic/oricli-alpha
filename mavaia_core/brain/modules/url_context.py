"""
URL Context Module

Implements Google Gemini URL Context feature for extracting and fetching content from URLs.
Supports automatic URL detection, two-step retrieval (cache + live fetch), and metadata tracking.
"""

import re
import hashlib
import time
from typing import Any, Dict, List, Optional
from urllib.parse import urlparse, urlunparse
from datetime import datetime, timedelta

from mavaia_core.brain.base_module import BaseBrainModule, ModuleMetadata
from mavaia_core.exceptions import ModuleOperationError, InvalidParameterError

# Lazy imports to avoid timeout during module discovery
DatabaseStorage = None
StorageConfig = None
WebFetchService = None

def _lazy_import_url_services():
    """Lazy import URL context services only when needed"""
    global DatabaseStorage, StorageConfig, WebFetchService
    if DatabaseStorage is None:
        try:
            from mavaia_core.brain.state_storage.db_storage import DatabaseStorage as DS
            from mavaia_core.brain.state_storage.base_storage import StorageConfig as SC
            from mavaia_core.services.web_fetch_service import WebFetchService as WFS
            DatabaseStorage = DS
            StorageConfig = SC
            WebFetchService = WFS
        except ImportError:
            pass


class URLContextModule(BaseBrainModule):
    """
    URL Context Module for extracting and fetching content from URLs.
    
    Supports automatic URL detection, two-step retrieval (cache + live fetch),
    and returns url_context_metadata with retrieval status.
    """
    
    STATE_TYPE = "url_context"
    MAX_URLS_PER_REQUEST = 20
    MAX_URL_SIZE_BYTES = 34 * 1024 * 1024  # 34MB
    CACHE_TTL_HOURS = 24
    
    def __init__(self):
        """Initialize URL context module."""
        super().__init__()
        self._storage: Optional[DatabaseStorage] = None
        self._web_fetch_service: Optional[WebFetchService] = None
    
    @property
    def metadata(self) -> ModuleMetadata:
        """Return module metadata."""
        return ModuleMetadata(
            name="url_context",
            version="1.0.0",
            description="URL context extraction and fetching with caching",
            operations=[
                "extract_urls",
                "fetch_url_context",
                "get_url_context",
            ],
            dependencies=[],
            enabled=True,
            model_required=False,
        )
    
    def initialize(self) -> bool:
        """Initialize the module and storage backend."""
        # Lazy initialization - don't initialize storage/fetch service at import time
        # They'll be initialized when first needed in execute()
        return True
    
    def _ensure_initialized(self):
        """Ensure storage and web fetch service are initialized"""
        _lazy_import_url_services()
        if DatabaseStorage is None or StorageConfig is None or WebFetchService is None:
            raise RuntimeError("URL context services not available")
        
        if self._storage is None or self._web_fetch_service is None:
            try:
                # Initialize database storage for caching
                config = StorageConfig(
                    storage_type="database",
                    storage_path=None,  # Use default path
                )
                self._storage = DatabaseStorage(config)
                if not self._storage.initialize():
                    raise RuntimeError("Failed to initialize database storage")
                
                # Initialize web fetch service
                self._web_fetch_service = WebFetchService(
                    max_content_tokens=self.MAX_URL_SIZE_BYTES // 4,  # Approximate tokens
                )
            except Exception as e:
                print(f"[URLContext] Initialization failed: {e}")
                raise
    
    def execute(self, operation: str, params: Dict[str, Any]) -> Dict[str, Any]:
        """Execute a URL context operation."""
        # Lazy initialize on first use
        self._ensure_initialized()
        
        try:
            if operation == "extract_urls":
                return self._extract_urls(params)
            elif operation == "fetch_url_context":
                return self._fetch_url_context(params)
            elif operation == "get_url_context":
                return self._get_url_context(params)
            else:
                raise ValueError(f"Unknown operation: {operation}")
        except (InvalidParameterError, ValueError) as e:
            raise ModuleOperationError(
                self.metadata.name,
                operation,
                str(e),
            )
        except Exception as e:
            raise ModuleOperationError(
                self.metadata.name,
                operation,
                f"Unexpected error: {str(e)}",
            )
    
    def _normalize_url(self, url: str) -> str:
        """
        Normalize URL for consistent caching.
        
        Args:
            url: URL string
            
        Returns:
            Normalized URL
        """
        try:
            parsed = urlparse(url)
            # Remove fragment and normalize
            normalized = urlunparse((
                parsed.scheme.lower(),
                parsed.netloc.lower(),
                parsed.path,
                parsed.params,
                parsed.query,
                "",  # Remove fragment
            ))
            return normalized
        except Exception:
            return url
    
    def _url_hash(self, url: str) -> str:
        """
        Generate hash for URL (for cache key).
        
        Args:
            url: URL string
            
        Returns:
            SHA-256 hash hex digest
        """
        normalized = self._normalize_url(url)
        return hashlib.sha256(normalized.encode('utf-8')).hexdigest()
    
    def _extract_urls(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """
        Extract URLs from text.
        
        Args:
            text: Text to extract URLs from
            max_urls: Maximum number of URLs to extract (default: 20)
            
        Returns:
            Dictionary with extracted URLs
        """
        text = params.get("text")
        if text is None:
            raise InvalidParameterError("text", None, "text parameter is required")
        
        # Allow empty string (will return 0 URLs)
        if not isinstance(text, str):
            raise InvalidParameterError("text", text, "text must be a string")
        
        max_urls = params.get("max_urls", self.MAX_URLS_PER_REQUEST)
        if max_urls < 1:
            raise InvalidParameterError("max_urls", max_urls, "max_urls must be >= 1")
        if max_urls > self.MAX_URLS_PER_REQUEST:
            max_urls = self.MAX_URLS_PER_REQUEST
        
        # URL regex pattern - matches http://, https://, and www. URLs
        url_pattern = r'https?://[^\s<>"{}|\\^`\[\]]+|www\.[^\s<>"{}|\\^`\[\]]+'
        
        # Find all URLs
        matches = re.findall(url_pattern, text)
        
        # Normalize and validate URLs
        urls = []
        seen = set()
        
        for match in matches:
            # Add http:// if www. URL
            if match.startswith("www."):
                match = "https://" + match
            
            # Normalize URL
            normalized = self._normalize_url(match)
            
            # Validate URL
            try:
                parsed = urlparse(normalized)
                if not parsed.scheme or not parsed.netloc:
                    continue
                
                # Check if already seen
                if normalized in seen:
                    continue
                
                seen.add(normalized)
                urls.append(normalized)
                
                if len(urls) >= max_urls:
                    break
            except Exception:
                continue
        
        return {
            "success": True,
            "urls": urls,
            "count": len(urls),
        }
    
    def _get_cached_content(self, url: str) -> Optional[Dict[str, Any]]:
        """
        Get cached content for URL.
        
        Args:
            url: URL to get cached content for
            
        Returns:
            Cached content dictionary or None if not cached or expired
        """
        url_hash = self._url_hash(url)
        cache_key = f"{self.STATE_TYPE}:{url_hash}"
        
        cached_data = self._storage.load(self.STATE_TYPE, cache_key)
        if not cached_data:
            return None
        
        # Check if cache is expired
        fetched_at_str = cached_data.get("fetched_at")
        if fetched_at_str:
            try:
                fetched_at = datetime.fromisoformat(fetched_at_str)
                age = datetime.now() - fetched_at
                if age > timedelta(hours=self.CACHE_TTL_HOURS):
                    # Cache expired
                    return None
            except Exception:
                # If we can't parse date, consider cache invalid
                return None
        
        return cached_data
    
    def _cache_content(self, url: str, content: str, content_type: str, size_bytes: int) -> bool:
        """
        Cache URL content.
        
        Args:
            url: URL
            content: Content string
            content_type: Content type
            size_bytes: Content size in bytes
            
        Returns:
            True if cached successfully
        """
        url_hash = self._url_hash(url)
        cache_key = f"{self.STATE_TYPE}:{url_hash}"
        
        cache_data = {
            "url": url,
            "content": content,
            "content_type": content_type,
            "size_bytes": size_bytes,
            "fetched_at": datetime.now().isoformat(),
        }
        
        return self._storage.save(
            self.STATE_TYPE,
            cache_key,
            cache_data,
            metadata={"url": url, "url_hash": url_hash}
        )
    
    def _fetch_url_context(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """
        Fetch URL context (with caching).
        
        Args:
            urls: List of URLs to fetch (up to 20)
            use_cache: Whether to use cache (default: True)
            
        Returns:
            Dictionary with URL context and metadata
        """
        urls = params.get("urls")
        if not urls:
            raise InvalidParameterError("urls", None, "urls parameter is required")
        
        if not isinstance(urls, list):
            raise InvalidParameterError("urls", urls, "urls must be a list")
        
        if len(urls) > self.MAX_URLS_PER_REQUEST:
            raise InvalidParameterError(
                "urls",
                len(urls),
                f"Maximum {self.MAX_URLS_PER_REQUEST} URLs allowed per request"
            )
        
        use_cache = params.get("use_cache", True)
        
        results = []
        metadata_list = []
        
        for url in urls:
            # Normalize URL
            normalized_url = self._normalize_url(url)
            
            # Check cache first if enabled
            cached_content = None
            if use_cache:
                cached_content = self._get_cached_content(normalized_url)
            
            if cached_content:
                # Return cached content
                metadata_list.append({
                    "url": normalized_url,
                    "status": "CACHED",
                    "content_type": cached_content.get("content_type", "unknown"),
                    "size_bytes": cached_content.get("size_bytes", 0),
                    "retrieval_method": "cache",
                    "error": None,
                })
                results.append({
                    "url": normalized_url,
                    "content": cached_content.get("content", ""),
                    "content_type": cached_content.get("content_type", "unknown"),
                })
            else:
                # Fetch live content
                fetch_result = self._web_fetch_service.fetch_url(
                    normalized_url,
                    explicitly_provided=True,
                    enable_citations=False,
                )
                
                if fetch_result.get("success"):
                    content = fetch_result.get("content", "")
                    content_type = fetch_result.get("content_type", "html")
                    size_bytes = len(content.encode('utf-8'))
                    
                    # Check size limit
                    if size_bytes > self.MAX_URL_SIZE_BYTES:
                        metadata_list.append({
                            "url": normalized_url,
                            "status": "FAILED",
                            "content_type": content_type,
                            "size_bytes": size_bytes,
                            "retrieval_method": "live",
                            "error": f"Content size ({size_bytes} bytes) exceeds maximum ({self.MAX_URL_SIZE_BYTES} bytes)",
                        })
                        results.append({
                            "url": normalized_url,
                            "content": None,
                            "content_type": content_type,
                        })
                    else:
                        # Cache the content
                        if use_cache:
                            self._cache_content(normalized_url, content, content_type, size_bytes)
                        
                        metadata_list.append({
                            "url": normalized_url,
                            "status": "SUCCESS",
                            "content_type": content_type,
                            "size_bytes": size_bytes,
                            "retrieval_method": "live",
                            "error": None,
                        })
                        results.append({
                            "url": normalized_url,
                            "content": content,
                            "content_type": content_type,
                        })
                else:
                    # Fetch failed
                    error = fetch_result.get("error", "Unknown error")
                    error_code = fetch_result.get("error_code", "unknown")
                    
                    # Determine if unsupported content type
                    status = "UNSUPPORTED" if "content_type" in error.lower() else "FAILED"
                    
                    metadata_list.append({
                        "url": normalized_url,
                        "status": status,
                        "content_type": None,
                        "size_bytes": 0,
                        "retrieval_method": "live",
                        "error": error,
                    })
                    results.append({
                        "url": normalized_url,
                        "content": None,
                        "content_type": None,
                    })
        
        return {
            "success": True,
            "results": results,
            "url_context_metadata": metadata_list,
            "count": len(results),
        }
    
    def _get_url_context(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """
        Get URL context from text (extract URLs and fetch).
        
        Args:
            text: Text to extract URLs from
            use_cache: Whether to use cache (default: True)
            max_urls: Maximum number of URLs to extract (default: 20)
            
        Returns:
            Dictionary with URL context and metadata
        """
        text = params.get("text")
        if text is None:
            raise InvalidParameterError("text", None, "text parameter is required")
        
        # Allow empty string (will return empty results)
        if not isinstance(text, str):
            raise InvalidParameterError("text", text, "text must be a string")
        
        use_cache = params.get("use_cache", True)
        max_urls = params.get("max_urls", self.MAX_URLS_PER_REQUEST)
        
        # Extract URLs
        extract_result = self._extract_urls({"text": text, "max_urls": max_urls})
        urls = extract_result.get("urls", [])
        
        if not urls:
            return {
                "success": True,
                "results": [],
                "url_context_metadata": [],
                "count": 0,
            }
        
        # Fetch URL context
        return self._fetch_url_context({"urls": urls, "use_cache": use_cache})

