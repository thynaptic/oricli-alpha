from __future__ import annotations
"""
Web Search Module

Implements web search functionality for Claude Web Search Tool feature.
Uses DuckDuckGo API for search results with domain filtering, localization,
and encrypted content references for citations.
"""

import hashlib
import time
import logging
from typing import Any, Dict, List, Optional
from urllib.parse import urlparse

from mavaia_core.brain.base_module import BaseBrainModule, ModuleMetadata
from mavaia_core.exceptions import ModuleOperationError, InvalidParameterError

# Optional imports for DuckDuckGo search
try:
    from duckduckgo_search import DDGS
    DDGS_AVAILABLE = True
except ImportError:
    DDGS_AVAILABLE = False
    DDGS = None

try:
    import requests
    REQUESTS_AVAILABLE = True
except ImportError:
    REQUESTS_AVAILABLE = False
    requests = None


class WebSearchModule(BaseBrainModule):
    """
    Web Search Module for performing web searches.
    
    Supports DuckDuckGo search with domain filtering, localization,
    and encrypted content references for citations.
    """
    
    def __init__(self):
        """Initialize web search module."""
        super().__init__()
        self._last_search_time = 0
        self._rate_limit_delay = 1.0  # Minimum delay between searches (seconds)
        self._search_count = 0
        self._max_searches_per_session = 100  # Safety limit
    
    @property
    def metadata(self) -> ModuleMetadata:
        """Return module metadata."""
        return ModuleMetadata(
            name="web_search",
            version="1.0.0",
            description="Web search using DuckDuckGo with domain filtering and localization",
            operations=[
                "search_web",
            ],
            dependencies=["duckduckgo-search"] if DDGS_AVAILABLE else [],
            enabled=True,
            model_required=False,
        )
    
    def initialize(self) -> bool:
        """Initialize the module."""
        if not DDGS_AVAILABLE:
            # Module can still be initialized but will return errors when used
            return True
        return True
    
    def execute(self, operation: str, params: Dict[str, Any]) -> Dict[str, Any]:
        """Execute a web search operation."""
        try:
            if operation == "search_web":
                return self._search_web(params)
            else:
                raise InvalidParameterError("operation", str(operation), "Unknown operation for web_search")
        except InvalidParameterError as e:
            raise ModuleOperationError(
                self.metadata.name,
                operation,
                str(e),
            )
        except Exception as e:
            logger = logging.getLogger(__name__)
            logger.debug(
                "web_search operation failed",
                exc_info=True,
                extra={"module_name": "web_search", "operation": str(operation), "error_type": type(e).__name__},
            )
            raise ModuleOperationError(
                self.metadata.name,
                operation,
                "Unexpected error during web search",
            )
    
    def _rate_limit(self) -> None:
        """Enforce rate limiting between searches."""
        current_time = time.time()
        time_since_last = current_time - self._last_search_time
        if time_since_last < self._rate_limit_delay:
            time.sleep(self._rate_limit_delay - time_since_last)
        self._last_search_time = time.time()
    
    def _extract_domain(self, url: str) -> str:
        """
        Extract domain from URL.
        
        Args:
            url: URL string
            
        Returns:
            Domain name (e.g., "example.com")
        """
        try:
            parsed = urlparse(url)
            hostname = parsed.hostname or ""
            # Remove www. prefix for consistent matching
            if hostname.startswith("www."):
                hostname = hostname[4:]
            return hostname.lower()
        except Exception:
            return ""
    
    def _matches_domain(self, url: str, domain: str) -> bool:
        """
        Check if URL matches a domain (including subdomains).
        
        Args:
            url: URL to check
            domain: Domain to match against
            
        Returns:
            True if URL matches domain
        """
        url_domain = self._extract_domain(url)
        domain_lower = domain.lower()
        
        # Exact match
        if url_domain == domain_lower:
            return True
        
        # Subdomain match (e.g., "www.example.com" matches "example.com")
        if url_domain.endswith(f".{domain_lower}"):
            return True
        
        return False
    
    def _filter_results(
        self,
        results: List[Dict[str, Any]],
        allowed_domains: Optional[List[str]] = None,
        blocked_domains: Optional[List[str]] = None,
    ) -> List[Dict[str, Any]]:
        """
        Filter search results by domain.
        
        Args:
            results: List of search results
            allowed_domains: Optional list of allowed domains
            blocked_domains: Optional list of blocked domains
            
        Returns:
            Filtered list of results
        """
        filtered = []
        
        for result in results:
            url = result.get("url", "")
            if not url:
                continue
            
            # Check blocked domains first
            if blocked_domains:
                blocked = False
                for blocked_domain in blocked_domains:
                    if self._matches_domain(url, blocked_domain):
                        blocked = True
                        break
                if blocked:
                    continue
            
            # Check allowed domains
            if allowed_domains:
                allowed = False
                for allowed_domain in allowed_domains:
                    if self._matches_domain(url, allowed_domain):
                        allowed = True
                        break
                if not allowed:
                    continue
            
            filtered.append(result)
        
        return filtered
    
    def _generate_encrypted_content(self, content: str) -> str:
        """
        Generate encrypted_content hash for citation references.
        
        Args:
            content: Content string to hash
            
        Returns:
            SHA-256 hash hex digest
        """
        return hashlib.sha256(content.encode('utf-8')).hexdigest()
    
    def _generate_encrypted_index(self, url: str, index: int) -> str:
        """
        Generate encrypted_index hash for citation references.
        
        Args:
            url: URL string
            index: Result index
            
        Returns:
            SHA-256 hash hex digest
        """
        combined = f"{url}:{index}"
        return hashlib.sha256(combined.encode('utf-8')).hexdigest()
    
    def _search_web(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """
        Perform web search.
        
        Args:
            query: Search query string
            max_results: Maximum number of results (default: 10)
            allowed_domains: Optional list of allowed domains
            blocked_domains: Optional list of blocked domains
            user_location: Optional ISO country code for localization (e.g., "us", "uk")
            
        Returns:
            Dictionary with search results in web_search_tool_result format
        """
        if not DDGS_AVAILABLE:
            return {
                "success": False,
                "error": "duckduckgo-search library is required. Install with: pip install duckduckgo-search",
                "error_code": "dependency_missing",
            }
        
        query = params.get("query")
        if not query:
            raise InvalidParameterError("query", None, "query parameter is required")
        if not isinstance(query, str) or not query.strip():
            raise InvalidParameterError("query", str(query), "query must be a non-empty string")
        
        max_results = params.get("max_results", 10)
        try:
            max_results_int = int(max_results)
        except (TypeError, ValueError):
            raise InvalidParameterError("max_results", str(max_results), "max_results must be an integer")
        if max_results_int < 1:
            raise InvalidParameterError("max_results", str(max_results_int), "max_results must be >= 1")
        if max_results_int > 50:
            max_results_int = 50  # Cap at 50 for safety
        
        allowed_domains = params.get("allowed_domains")
        blocked_domains = params.get("blocked_domains")
        user_location = params.get("user_location")
        if allowed_domains is not None and not isinstance(allowed_domains, list):
            raise InvalidParameterError(
                "allowed_domains", str(type(allowed_domains).__name__), "allowed_domains must be a list when provided"
            )
        if blocked_domains is not None and not isinstance(blocked_domains, list):
            raise InvalidParameterError(
                "blocked_domains", str(type(blocked_domains).__name__), "blocked_domains must be a list when provided"
            )
        if user_location is not None and not isinstance(user_location, str):
            raise InvalidParameterError(
                "user_location", str(type(user_location).__name__), "user_location must be a string when provided"
            )
        
        # Check session limit
        if self._search_count >= self._max_searches_per_session:
            return {
                "success": False,
                "error": "rate_limit_exceeded: Maximum searches per session exceeded",
                "error_code": "rate_limit_exceeded",
            }
        
        # Rate limiting
        self._rate_limit()
        
        try:
            # Perform search using DuckDuckGo
            # Note: DuckDuckGo doesn't have official API, so we use the library
            # which scrapes results. Region parameter may not be fully supported.
            search_params = {}
            if user_location:
                # DuckDuckGo uses region codes, but library may not support it directly
                # We'll try to pass it if the library supports it
                search_params["region"] = user_location.lower()
            
            with DDGS() as ddgs:
                # Perform text search
                # Try with different parameters if first attempt fails
                try:
                    results = list(ddgs.text(
                        query,
                        max_results=max_results_int * 2,  # Get more results for filtering
                        **search_params
                    ))
                except Exception as e:
                    # If search fails, try without extra parameters
                    try:
                        results = list(ddgs.text(query, max_results=max_results_int * 2))
                    except Exception:
                        # If still fails, return empty results with error info
                        logger = logging.getLogger(__name__)
                        logger.debug(
                            "DuckDuckGo search failed",
                            exc_info=True,
                            extra={"module_name": "web_search", "error_type": type(e).__name__},
                        )
                        return {
                            "success": False,
                            "error": "search_failed",
                            "error_code": "search_failed",
                            "results": [],
                            "count": 0,
                        }
            
            # Format results
            formatted_results = []
            for idx, result in enumerate(results):
                title = result.get("title", "")
                url = result.get("href", "")
                snippet = result.get("body", "")
                
                if not url:
                    continue
                
                # Generate encrypted references
                # For encrypted_content, we hash the snippet (or could hash full content if fetched)
                encrypted_content = self._generate_encrypted_content(snippet)
                encrypted_index = self._generate_encrypted_index(url, idx)
                
                formatted_results.append({
                    "title": title,
                    "url": url,
                    "snippet": snippet,
                    "encrypted_content": encrypted_content,
                    "encrypted_index": encrypted_index,
                })
            
            # Apply domain filtering
            if allowed_domains or blocked_domains:
                formatted_results = self._filter_results(
                    formatted_results,
                    allowed_domains=allowed_domains,
                    blocked_domains=blocked_domains,
                )
            
            # Limit to requested number of results
            formatted_results = formatted_results[:max_results_int]
            
            # Increment search count
            self._search_count += 1
            
            # Return in web_search_tool_result format
            return {
                "success": True,
                "type": "web_search_tool_result",
                "results": formatted_results,
                "count": len(formatted_results),
                "query": query,
            }
        
        except Exception as e:
            logger = logging.getLogger(__name__)
            logger.debug(
                "Web search failed",
                exc_info=True,
                extra={"module_name": "web_search", "error_type": type(e).__name__},
            )
            return {
                "success": False,
                "error": "search_failed",
                "error_code": "search_failed",
            }
    
    def reset_session(self) -> None:
        """Reset search count for new session."""
        self._search_count = 0

