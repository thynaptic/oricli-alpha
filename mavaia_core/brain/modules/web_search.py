from __future__ import annotations
"""Web Search Module

Implements web search functionality for the brain.

This module intentionally avoids DuckDuckGo (DDG) and instead scrapes HTML
results from Mojeek with strict timeouts.
"""

import hashlib
import time
import logging
from typing import Any, Dict, List, Optional
from urllib.parse import urlparse, quote

from mavaia_core.brain.base_module import BaseBrainModule, ModuleMetadata
from mavaia_core.exceptions import ModuleOperationError, InvalidParameterError

try:
    import requests
    REQUESTS_AVAILABLE = True
except ImportError:
    REQUESTS_AVAILABLE = False
    requests = None

try:
    from bs4 import BeautifulSoup
    BS4_AVAILABLE = True
except ImportError:
    BS4_AVAILABLE = False
    BeautifulSoup = None


class WebSearchModule(BaseBrainModule):
    """
    Web Search Module for performing web searches.
    
    Scrapes Mojeek HTML results with domain filtering and encrypted content
    references for citations.
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
            description="Web search using Mojeek HTML with domain filtering and localization",
            operations=[
                "search_web",
            ],
            dependencies=[],
            enabled=True,
            model_required=False,
        )
    
    def initialize(self) -> bool:
        """Initialize the module."""
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
        if not REQUESTS_AVAILABLE or not BS4_AVAILABLE:
            return {
                "success": False,
                "error": "requests and beautifulsoup4 are required for web search",
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

        # Default to higher-signal sources for direct factual questions.
        # This makes snippets less noisy (e.g., avoids random book citations) and improves coherence.
        if allowed_domains is None:
            ql = query.strip().lower()
            if ql.startswith(("what ", "who ", "when ", "where ", "define ", "definition of")):
                allowed_domains = ["wikipedia.org"]
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
            headers = {
                "User-Agent": (
                    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 "
                    "(KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36"
                ),
                "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
                "Accept-Language": "en-US,en;q=0.9",
                "Connection": "keep-alive",
            }
            resp = requests.get(
                "https://www.mojeek.com/search",
                params={"q": query},
                headers=headers,
                timeout=(5, 12),
            )

            formatted_results: list[dict[str, Any]] = []
            if resp.status_code == 200:
                soup = BeautifulSoup(resp.text, "html.parser")

                ul = soup.find("ul", class_="results-standard")
                if ul:
                    items = ul.find_all("li", recursive=False)
                else:
                    items = []

                for idx, li in enumerate(items):
                    if len(formatted_results) >= max_results_int:
                        break

                    h2 = li.find("h2")
                    a = h2.find("a", class_="title") if h2 else None
                    if not a:
                        continue

                    url = (a.get("href") or "").strip()
                    title = a.get_text(" ", strip=True)
                    snippet_p = li.find("p", class_="s")
                    snippet = snippet_p.get_text(" ", strip=True) if snippet_p else ""

                    if not url:
                        continue

                    encrypted_content = self._generate_encrypted_content(snippet or title)
                    encrypted_index = self._generate_encrypted_index(url, idx)

                    formatted_results.append(
                        {
                            "title": title,
                            "url": url,
                            "snippet": snippet,
                            "encrypted_content": encrypted_content,
                            "encrypted_index": encrypted_index,
                        }
                    )

            # If Mojeek is blocked (e.g., HTTP 403) or returns no results, fall back to Wikipedia search.
            if not formatted_results:
                formatted_results = self._search_wikipedia(query, max_results_int, headers)

            if not formatted_results and resp.status_code != 200:
                return {
                    "success": False,
                    "error": f"search_http_{resp.status_code}",
                    "error_code": "search_failed",
                    "results": [],
                    "count": 0,
                }
            
            # Apply domain filtering
            if allowed_domains or blocked_domains:
                formatted_results = self._filter_results(
                    formatted_results,
                    allowed_domains=allowed_domains,
                    blocked_domains=blocked_domains,
                )

            # Filter out obviously irrelevant results (no keyword overlap with query)
            # This helps avoid returning portal/search landing pages as "answers".
            try:
                import re
                query_lower = query.lower()
                stopwords = {
                    "what", "why", "how", "does", "do", "did", "is", "are", "was", "were",
                    "the", "a", "an", "and", "or", "to", "of", "in", "on", "for", "with",
                    "who", "when", "where", "which", "that", "this",
                }
                query_terms = {
                    w for w in re.findall(r"[a-zA-Z0-9]+", query_lower)
                    if len(w) > 2 and w not in stopwords
                }
                if query_terms:
                    filtered_by_relevance = []
                    for r in formatted_results:
                        blob = f"{r.get('title','')} {r.get('snippet','')}".lower()
                        terms = {
                            w for w in re.findall(r"[a-zA-Z0-9]+", blob)
                            if len(w) > 2 and w not in stopwords
                        }
                        if query_terms.intersection(terms):
                            filtered_by_relevance.append(r)
                    formatted_results = filtered_by_relevance
            except Exception:
                pass
            
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
    
    def _search_wikipedia(
        self, query: str, max_results: int, headers: Dict[str, str] | None = None
    ) -> List[Dict[str, Any]]:
        """Fallback web search using Wikipedia's public API."""
        if not REQUESTS_AVAILABLE:
            return []

        try:
            wiki_headers = dict(headers or {})
            wiki_headers["Accept"] = "application/json"

            resp = requests.get(
                "https://en.wikipedia.org/w/api.php",
                params={
                    "action": "query",
                    "list": "search",
                    "srsearch": query,
                    "format": "json",
                    "utf8": 1,
                    "srlimit": max_results,
                },
                headers=wiki_headers,
                timeout=(5, 12),
            )
            if resp.status_code != 200:
                return []

            data = resp.json() if resp.content else {}
            hits = (
                data.get("query", {}).get("search", [])
                if isinstance(data, dict)
                else []
            )

            import re
            out: list[dict[str, Any]] = []
            for idx, item in enumerate(hits[:max_results]):
                title = (item.get("title") or "").strip()
                snippet = (item.get("snippet") or "").strip()
                if snippet:
                    snippet = re.sub(r"<[^>]+>", "", snippet)
                if not title:
                    continue
                url = f"https://en.wikipedia.org/wiki/{quote(title.replace(' ', '_'))}"

                encrypted_content = self._generate_encrypted_content(snippet or title)
                encrypted_index = self._generate_encrypted_index(url, idx)

                out.append(
                    {
                        "title": title,
                        "url": url,
                        "snippet": snippet,
                        "encrypted_content": encrypted_content,
                        "encrypted_index": encrypted_index,
                    }
                )
            return out
        except Exception:
            return []

    def reset_session(self) -> None:
        """Reset search count for new session."""
        self._search_count = 0

