"""
Web Scraper Module - Web scraping and research capabilities
Handles URL content extraction, multi-source research, fact-checking, and article summarization
"""

import json
import time
import random
import urllib.parse
import urllib.request
from typing import Dict, Any, List, Optional
from collections import defaultdict

from mavaia_core.brain.base_module import BaseBrainModule, ModuleMetadata

# Optional imports - will fail gracefully if dependencies not available
try:
    from bs4 import BeautifulSoup

    WEB_SCRAPING_AVAILABLE = True
except ImportError:
    WEB_SCRAPING_AVAILABLE = False

try:
    import requests

    REQUESTS_AVAILABLE = True
except ImportError:
    REQUESTS_AVAILABLE = False

try:
    from readability import Document

    READABILITY_AVAILABLE = True
except ImportError:
    READABILITY_AVAILABLE = False

# User agent list for rotation
USER_AGENTS = [
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.0 Safari/605.1.15",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:121.0) Gecko/20100101 Firefox/121.0",
]


class WebScraper(BaseBrainModule):
    """Web scraping and research capabilities"""

    def __init__(self):
        self.rate_limit_delay = 1.0  # Seconds between requests
        self.last_request_time = 0

    @property
    def metadata(self) -> ModuleMetadata:
        return ModuleMetadata(
            name="web_scraper",
            version="1.0.0",
            description="Web scraping and research: URL extraction, multi-source research, fact-checking",
            operations=[
                "scrape_url",
                "research_topic",
                "fact_check",
                "summarize_article",
                "extract_links",
            ],
            dependencies=["requests", "beautifulsoup4", "readability-lxml"],
            enabled=True,
            model_required=False,
        )

    def execute(self, operation: str, params: Dict[str, Any]) -> Dict[str, Any]:
        """Execute web scraping operations"""

        if not WEB_SCRAPING_AVAILABLE:
            return {
                "success": False,
                "error": "Web scraping dependencies not available. Install: pip install requests beautifulsoup4 readability-lxml",
            }

        if operation == "scrape_url":
            url = params.get("url", "")
            return self.scrape_url(url)

        elif operation == "research_topic":
            query = params.get("query", "")
            max_sources = params.get("max_sources", 5)
            return self.research_topic(query, max_sources)

        elif operation == "fact_check":
            claim = params.get("claim", "")
            sources = params.get("sources", [])
            return self.fact_check(claim, sources)

        elif operation == "summarize_article":
            url = params.get("url", "")
            return self.summarize_article(url)

        elif operation == "extract_links":
            url = params.get("url", "")
            filter_pattern = params.get("filter_pattern")
            return self.extract_links(url, filter_pattern)

        else:
            raise ValueError(f"Unknown operation: {operation}")

    def _rate_limit(self):
        """Enforce rate limiting"""
        current_time = time.time()
        time_since_last = current_time - self.last_request_time
        if time_since_last < self.rate_limit_delay:
            time.sleep(self.rate_limit_delay - time_since_last)
        self.last_request_time = time.time()

    def _get_headers(self) -> Dict[str, str]:
        """Get random user agent headers"""
        return {
            "User-Agent": random.choice(USER_AGENTS),
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
            "Accept-Language": "en-US,en;q=0.5",
            "Accept-Encoding": "gzip, deflate",
            "Connection": "keep-alive",
        }

    def scrape_url(self, url: str) -> Dict[str, Any]:
        """Extract content from a URL"""
        try:
            if not url or not url.startswith(("http://", "https://")):
                return {"success": False, "error": "Invalid URL format"}

            self._rate_limit()

            # Use requests if available, otherwise urllib
            if REQUESTS_AVAILABLE:
                response = requests.get(url, headers=self._get_headers(), timeout=10)
                response.raise_for_status()
                html = response.text
            else:
                request = urllib.request.Request(url, headers=self._get_headers())
                with urllib.request.urlopen(request, timeout=10) as response:
                    html = response.read().decode("utf-8", errors="ignore")

            # Extract text using readability if available
            if READABILITY_AVAILABLE:
                doc = Document(html)
                title = doc.title()
                content = doc.summary()
                # Clean HTML from content
                soup = BeautifulSoup(content, "html.parser")
                text = soup.get_text(separator=" ", strip=True)
            else:
                # Fallback to basic BeautifulSoup extraction
                soup = BeautifulSoup(html, "html.parser")
                title = soup.find("title")
                title = title.get_text() if title else "Untitled"

                # Remove script and style elements
                for script in soup(["script", "style", "nav", "footer", "header"]):
                    script.decompose()

                # Get main content
                main_content = (
                    soup.find("main") or soup.find("article") or soup.find("body")
                )
                if main_content:
                    text = main_content.get_text(separator=" ", strip=True)
                else:
                    text = soup.get_text(separator=" ", strip=True)

            # Clean up text
            lines = (line.strip() for line in text.splitlines())
            chunks = (phrase.strip() for line in lines for phrase in line.split("  "))
            clean_text = " ".join(chunk for chunk in chunks if chunk)

            # Limit text length
            clean_text = clean_text[:10000]  # Limit to 10k chars

            return {
                "success": True,
                "result": {
                    "url": url,
                    "title": title,
                    "content": clean_text,
                    "content_length": len(clean_text),
                    "extracted_at": time.strftime("%Y-%m-%d %H:%M:%S"),
                },
            }
        except Exception as e:
            return {"success": False, "error": f"Failed to scrape URL: {str(e)}"}

    def research_topic(self, query: str, max_sources: int = 5) -> Dict[str, Any]:
        """Research a topic across multiple sources"""
        try:
            if not query:
                return {"success": False, "error": "Query cannot be empty"}

            # Simple search simulation - in production, would use search API
            # For now, return a structured response indicating research would be performed
            sources = []

            # Try to find relevant URLs (simplified - would use search API in production)
            search_query = urllib.parse.quote_plus(query)

            # Note: Actual Google search scraping is complex and may violate ToS
            # In production, this would use a proper search API (e.g., Google Custom Search API, Bing Search API)
            # Current implementation provides structured response format for search results
            sources.append(
                {
                    "url": f"https://www.google.com/search?q={search_query}",
                    "title": f"Search results for: {query}",
                    "snippet": f"Research query: {query}",
                    "relevance": 1.0,
                }
            )

            return {
                "success": True,
                "result": {
                    "query": query,
                    "sources_found": len(sources),
                    "sources": sources,
                    "note": "Full research requires search API integration",
                },
            }
        except Exception as e:
            return {"success": False, "error": f"Research failed: {str(e)}"}

    def fact_check(self, claim: str, sources: List[str] = None) -> Dict[str, Any]:
        """Verify a claim against sources"""
        try:
            if not claim:
                return {"success": False, "error": "Claim cannot be empty"}

            # If sources provided, check against them
            if sources:
                results = []
                for source_url in sources[:5]:  # Limit to 5 sources
                    self._rate_limit()
                    scrape_result = self.scrape_url(source_url)
                    if scrape_result.get("success"):
                        content = scrape_result["result"].get("content", "")
                        # Simple keyword matching (would use NLP in production)
                        claim_words = set(claim.lower().split())
                        content_words = set(content.lower().split())
                        overlap = (
                            len(claim_words & content_words) / len(claim_words)
                            if claim_words
                            else 0
                        )

                        results.append(
                            {
                                "source": source_url,
                                "relevance": overlap,
                                "content_preview": content[:200],
                            }
                        )

                # Calculate overall verification score
                avg_relevance = (
                    sum(r["relevance"] for r in results) / len(results)
                    if results
                    else 0
                )

                return {
                    "success": True,
                    "result": {
                        "claim": claim,
                        "verification_score": avg_relevance,
                        "sources_checked": len(results),
                        "sources": results,
                        "verdict": "verified" if avg_relevance > 0.3 else "unverified",
                    },
                }
            else:
                # No sources provided - would need to search for sources
                return {
                    "success": True,
                    "result": {
                        "claim": claim,
                        "note": "No sources provided. Use research_topic to find sources first.",
                    },
                }
        except Exception as e:
            return {"success": False, "error": f"Fact-checking failed: {str(e)}"}

    def summarize_article(self, url: str) -> Dict[str, Any]:
        """Summarize an article from a URL"""
        try:
            scrape_result = self.scrape_url(url)
            if not scrape_result.get("success"):
                return scrape_result

            content = scrape_result["result"].get("content", "")
            title = scrape_result["result"].get("title", "Untitled")

            # Simple summarization: extract first few sentences
            sentences = content.split(". ")
            summary_sentences = sentences[:3]  # First 3 sentences
            summary = ". ".join(summary_sentences) + "."

            # Extract key points (simple keyword extraction)
            words = content.lower().split()
            word_freq = defaultdict(int)
            for word in words:
                if len(word) > 4:  # Filter short words
                    word_freq[word] += 1

            top_keywords = sorted(word_freq.items(), key=lambda x: x[1], reverse=True)[
                :5
            ]

            return {
                "success": True,
                "result": {
                    "url": url,
                    "title": title,
                    "summary": summary,
                    "key_points": [word for word, _ in top_keywords],
                    "original_length": len(content),
                    "summary_length": len(summary),
                },
            }
        except Exception as e:
            return {"success": False, "error": f"Summarization failed: {str(e)}"}

    def extract_links(self, url: str, filter_pattern: str = None) -> Dict[str, Any]:
        """Extract links from a URL"""
        try:
            scrape_result = self.scrape_url(url)
            if not scrape_result.get("success"):
                return scrape_result

            self._rate_limit()

            # Get HTML
            if REQUESTS_AVAILABLE:
                response = requests.get(url, headers=self._get_headers(), timeout=10)
                html = response.text
            else:
                request = urllib.request.Request(url, headers=self._get_headers())
                with urllib.request.urlopen(request, timeout=10) as response:
                    html = response.read().decode("utf-8", errors="ignore")

            soup = BeautifulSoup(html, "html.parser")
            links = []

            for a_tag in soup.find_all("a", href=True):
                href = a_tag.get("href")
                text = a_tag.get_text(strip=True)

                # Resolve relative URLs
                if href.startswith("/"):
                    parsed_url = urllib.parse.urlparse(url)
                    href = f"{parsed_url.scheme}://{parsed_url.netloc}{href}"
                elif not href.startswith(("http://", "https://")):
                    continue

                # Apply filter if provided
                if filter_pattern and filter_pattern.lower() not in href.lower():
                    continue

                links.append(
                    {"url": href, "text": text, "title": a_tag.get("title", "")}
                )

            return {
                "success": True,
                "result": {
                    "source_url": url,
                    "links_found": len(links),
                    "links": links[:50],  # Limit to 50 links
                },
            }
        except Exception as e:
            return {"success": False, "error": f"Link extraction failed: {str(e)}"}
