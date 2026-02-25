from __future__ import annotations
"""
Web Fetch Service

Secure web fetching service with strict URL validation, domain filtering,
content extraction, and PDF support.
"""

import re
import time
import random
from typing import Dict, Any, List, Optional, Tuple
from urllib.parse import urlparse
from datetime import datetime

# Optional imports
try:
    import requests
    REQUESTS_AVAILABLE = True
except ImportError:
    REQUESTS_AVAILABLE = False
    requests = None

try:
    from bs4 import BeautifulSoup
    BEAUTIFULSOUP_AVAILABLE = True
except ImportError:
    BEAUTIFULSOUP_AVAILABLE = False

try:
    from readability import Document
    READABILITY_AVAILABLE = True
except ImportError:
    READABILITY_AVAILABLE = False

try:
    import PyPDF2
    PYPDF2_AVAILABLE = True
except ImportError:
    PYPDF2_AVAILABLE = False

try:
    import pdfplumber
    PDFPLUMBER_AVAILABLE = True
except ImportError:
    PDFPLUMBER_AVAILABLE = False

from mavaia_core.exceptions import MavaiaError


class WebFetchError(MavaiaError):
    """Base exception for web fetch errors."""
    pass


class URLValidationError(WebFetchError):
    """Raised when URL validation fails."""
    pass


class ContentExtractionError(WebFetchError):
    """Raised when content extraction fails."""
    pass


# User agent rotation
USER_AGENTS = [
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.0 Safari/605.1.15",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:121.0) Gecko/20100101 Firefox/121.0",
]


class URLValidator:
    """URL validation and security checks."""
    
    # Private/internal IP ranges
    PRIVATE_IP_PATTERNS = [
        r"^127\.",  # Loopback
        r"^10\.",  # Private class A
        r"^172\.(1[6-9]|2[0-9]|3[0-1])\.",  # Private class B
        r"^192\.168\.",  # Private class C
        r"^169\.254\.",  # Link-local
        r"^::1$",  # IPv6 loopback
        r"^localhost",
    ]
    
    def __init__(
        self,
        allowed_domains: Optional[List[str]] = None,
        blocked_domains: Optional[List[str]] = None,
    ):
        """
        Initialize URL validator.
        
        Args:
            allowed_domains: List of allowed domains (if set, only these are allowed)
            blocked_domains: List of blocked domains (these are never allowed)
        """
        self.allowed_domains = [d.lower() for d in (allowed_domains or [])]
        self.blocked_domains = [d.lower() for d in (blocked_domains or [])]
    
    def validate_url(
        self,
        url: str,
        explicitly_provided: bool = True,
    ) -> Tuple[bool, Optional[str]]:
        """
        Validate URL according to strict rules.
        
        Args:
            url: URL to validate
            explicitly_provided: Whether URL was explicitly provided by user
            
        Returns:
            Tuple of (is_valid, error_message)
        """
        if not url:
            return False, "invalid_input: URL cannot be empty"
        
        # Strict validation: only explicitly provided URLs
        if not explicitly_provided:
            return False, "invalid_input: URL must be explicitly provided"
        
        # Validate URL format
        if not url.startswith(("http://", "https://")):
            return False, "invalid_input: URL must use http:// or https://"
        
        try:
            parsed = urlparse(url)
        except Exception:
            return False, "invalid_input: Invalid URL format"
        
        # Check for private/internal URLs
        hostname = parsed.hostname or ""
        for pattern in self.PRIVATE_IP_PATTERNS:
            if re.match(pattern, hostname):
                return False, "url_not_accessible: Private/internal URLs are not allowed"
        
        # Check blocked domains
        hostname_lower = hostname.lower()
        for blocked in self.blocked_domains:
            if blocked in hostname_lower or hostname_lower.endswith(f".{blocked}"):
                return False, f"domain_blocked: Domain '{blocked}' is blocked"
        
        # Check allowed domains (if allowlist is set)
        if self.allowed_domains:
            allowed = False
            for allowed_domain in self.allowed_domains:
                if hostname_lower == allowed_domain or hostname_lower.endswith(f".{allowed_domain}"):
                    allowed = True
                    break
            if not allowed:
                return False, f"domain_not_allowed: Domain not in allowlist. Allowed: {self.allowed_domains}"
        
        return True, None


class ContentExtractor:
    """Content extraction from HTML and PDF."""
    
    def __init__(self, max_content_tokens: int = 100000):
        """
        Initialize content extractor.
        
        Args:
            max_content_tokens: Maximum content length (estimated tokens, ~4 chars per token)
        """
        self.max_content_chars = max_content_tokens * 4  # Approximate
    
    def extract_html(self, html: str, url: str) -> Dict[str, Any]:
        """
        Extract content from HTML.
        
        Args:
            html: HTML content
            url: Source URL
            
        Returns:
            Dictionary with extracted content and metadata
        """
        if not BEAUTIFULSOUP_AVAILABLE:
            raise ContentExtractionError("BeautifulSoup is required for HTML extraction")
        
        try:
            soup = BeautifulSoup(html, "html.parser")
            
            # Extract title
            title_tag = soup.find("title")
            title = title_tag.get_text(strip=True) if title_tag else "Untitled"
            
            # Extract metadata
            meta_desc = soup.find("meta", attrs={"name": "description"})
            description = meta_desc.get("content", "") if meta_desc else ""
            
            meta_author = soup.find("meta", attrs={"name": "author"}) or soup.find("meta", attrs={"property": "article:author"})
            author = meta_author.get("content", "") if meta_author else ""
            
            # Extract main content
            if READABILITY_AVAILABLE:
                doc = Document(html)
                content_html = doc.summary()
                content_soup = BeautifulSoup(content_html, "html.parser")
            else:
                # Remove unwanted elements
                for element in soup(["script", "style", "nav", "footer", "header", "aside", "iframe"]):
                    element.decompose()
                
                # Find main content
                main_content = soup.find("main") or soup.find("article") or soup.find("body")
                if main_content:
                    content_soup = main_content
                else:
                    content_soup = soup
            
            # Extract text
            text = content_soup.get_text(separator=" ", strip=True)
            
            # Clean up whitespace
            text = re.sub(r"\s+", " ", text)
            
            # Truncate if too long
            if len(text) > self.max_content_chars:
                text = text[:self.max_content_chars] + "... [truncated]"
            
            return {
                "content": text,
                "title": title,
                "description": description,
                "author": author,
                "content_length": len(text),
            }
        except Exception as e:
            raise ContentExtractionError(f"Failed to extract HTML content: {str(e)}")
    
    def extract_pdf(self, pdf_data: bytes, url: str) -> Dict[str, Any]:
        """
        Extract text from PDF.
        
        Args:
            pdf_data: PDF file content as bytes
            url: Source URL
            
        Returns:
            Dictionary with extracted text and metadata
        """
        if not PYPDF2_AVAILABLE and not PDFPLUMBER_AVAILABLE:
            raise ContentExtractionError("PyPDF2 or pdfplumber is required for PDF extraction")
        
        try:
            text_parts = []
            num_pages = 0
            
            # Try pdfplumber first (better text extraction)
            if PDFPLUMBER_AVAILABLE:
                import io
                pdf_file = io.BytesIO(pdf_data)
                with pdfplumber.open(pdf_file) as pdf:
                    num_pages = len(pdf.pages)
                    for page in pdf.pages:
                        page_text = page.extract_text()
                        if page_text:
                            text_parts.append(page_text)
            elif PYPDF2_AVAILABLE:
                import io
                pdf_file = io.BytesIO(pdf_data)
                pdf_reader = PyPDF2.PdfReader(pdf_file)
                num_pages = len(pdf_reader.pages)
                
                for page in pdf_reader.pages:
                    try:
                        page_text = page.extract_text()
                        if page_text:
                            text_parts.append(page_text)
                    except Exception:
                        continue
            
            text = "\n\n".join(text_parts)
            
            # Truncate if too long
            if len(text) > self.max_content_chars:
                text = text[:self.max_content_chars] + "... [truncated]"
            
            # Try to extract title from metadata
            title = "PDF Document"
            try:
                if PYPDF2_AVAILABLE:
                    import io
                    pdf_file = io.BytesIO(pdf_data)
                    pdf_reader = PyPDF2.PdfReader(pdf_file)
                    if pdf_reader.metadata and pdf_reader.metadata.get("/Title"):
                        title = pdf_reader.metadata["/Title"]
            except Exception:
                pass
            
            return {
                "content": text,
                "title": title,
                "num_pages": num_pages,
                "content_length": len(text),
            }
        except Exception as e:
            raise ContentExtractionError(f"Failed to extract PDF content: {str(e)}")


class CitationGenerator:
    """Generate citations for fetched content."""
    
    @staticmethod
    def generate_citation(url: str, metadata: Dict[str, Any]) -> str:
        """
        Generate citation string.
        
        Args:
            url: Source URL
            metadata: Content metadata
            
        Returns:
            Citation string
        """
        title = metadata.get("title", "Untitled")
        author = metadata.get("author", "")
        access_date = datetime.now().strftime("%Y-%m-%d")
        
        citation_parts = [title]
        if author:
            citation_parts.append(f"by {author}")
        citation_parts.append(f"({url})")
        citation_parts.append(f"Accessed: {access_date}")
        
        return " - ".join(citation_parts)


class WebFetchService:
    """Main web fetch service."""
    
    def __init__(
        self,
        allowed_domains: Optional[List[str]] = None,
        blocked_domains: Optional[List[str]] = None,
        max_content_tokens: int = 100000,
        rate_limit_delay: float = 1.0,
        timeout: int = 30,
    ):
        """
        Initialize web fetch service.
        
        Args:
            allowed_domains: Allowed domains (if set, only these are allowed)
            blocked_domains: Blocked domains
            max_content_tokens: Maximum content tokens
            rate_limit_delay: Delay between requests (seconds)
            timeout: Request timeout (seconds)
        """
        self.validator = URLValidator(allowed_domains, blocked_domains)
        self.extractor = ContentExtractor(max_content_tokens)
        self.citation_generator = CitationGenerator()
        self.rate_limit_delay = rate_limit_delay
        self.timeout = timeout
        self.last_request_time = {}
    
    def _rate_limit(self, domain: str) -> None:
        """Enforce rate limiting per domain."""
        current_time = time.time()
        if domain in self.last_request_time:
            time_since_last = current_time - self.last_request_time[domain]
            if time_since_last < self.rate_limit_delay:
                time.sleep(self.rate_limit_delay - time_since_last)
        self.last_request_time[domain] = time.time()
    
    def _get_headers(self) -> Dict[str, str]:
        """Get random user agent headers."""
        return {
            "User-Agent": random.choice(USER_AGENTS),
            "Accept": "text/html,application/xhtml+xml,application/xml,application/pdf,*/*;q=0.9",
            "Accept-Language": "en-US,en;q=0.5",
            "Accept-Encoding": "gzip, deflate",
            "Connection": "keep-alive",
        }
    
    def fetch_url(
        self,
        url: str,
        explicitly_provided: bool = True,
        enable_citations: bool = True,
    ) -> Dict[str, Any]:
        """
        Fetch content from a URL.
        
        Args:
            url: URL to fetch
            explicitly_provided: Whether URL was explicitly provided
            enable_citations: Whether to generate citations
            
        Returns:
            Dictionary with fetched content and metadata
        """
        # Validate URL
        is_valid, error = self.validator.validate_url(url, explicitly_provided)
        if not is_valid:
            return {
                "success": False,
                "error": error,
                "error_code": error.split(":")[0] if ":" in error else "invalid_input",
            }
        
        # Get domain for rate limiting
        parsed = urlparse(url)
        domain = parsed.hostname or ""
        
        # Rate limit
        self._rate_limit(domain)
        
        if not REQUESTS_AVAILABLE:
            return {
                "success": False,
                "error": "invalid_input: requests library is required",
                "error_code": "invalid_input",
            }
        
        try:
            # Fetch URL
            response = requests.get(
                url,
                headers=self._get_headers(),
                timeout=self.timeout,
                allow_redirects=True,
                stream=True,  # Stream for large files
            )
            response.raise_for_status()
            
            # Check content type
            content_type = response.headers.get("Content-Type", "").lower()
            
            # Handle PDF
            if "application/pdf" in content_type or url.lower().endswith(".pdf"):
                pdf_data = response.content
                extracted = self.extractor.extract_pdf(pdf_data, url)
                content_type_used = "pdf"
            else:
                # Handle HTML
                html = response.text
                extracted = self.extractor.extract_html(html, url)
                content_type_used = "html"
            
            # Generate citation
            citation = None
            if enable_citations:
                citation = self.citation_generator.generate_citation(url, extracted)
            
            return {
                "success": True,
                "url": url,
                "content": extracted["content"],
                "title": extracted.get("title", "Untitled"),
                "description": extracted.get("description", ""),
                "author": extracted.get("author", ""),
                "content_type": content_type_used,
                "content_length": extracted.get("content_length", 0),
                "citation": citation,
                "metadata": {
                    "num_pages": extracted.get("num_pages"),
                    "fetched_at": datetime.now().isoformat(),
                },
            }
        
        except requests.exceptions.Timeout:
            return {
                "success": False,
                "error": "timeout: Request timed out",
                "error_code": "timeout",
            }
        except requests.exceptions.RequestException as e:
            return {
                "success": False,
                "error": f"url_not_accessible: {str(e)}",
                "error_code": "url_not_accessible",
            }
        except ContentExtractionError as e:
            return {
                "success": False,
                "error": f"content_extraction_failed: {str(e)}",
                "error_code": "content_extraction_failed",
            }
        except Exception as e:
            return {
                "success": False,
                "error": f"unknown_error: {str(e)}",
                "error_code": "unknown_error",
            }
    
    def fetch_multiple(
        self,
        urls: List[str],
        explicitly_provided: bool = True,
        enable_citations: bool = True,
        max_uses: int = 10,
    ) -> Dict[str, Any]:
        """
        Fetch multiple URLs.
        
        Args:
            urls: List of URLs to fetch
            explicitly_provided: Whether URLs were explicitly provided
            enable_citations: Whether to generate citations
            max_uses: Maximum number of URLs to fetch
            
        Returns:
            Dictionary with results for each URL
        """
        if len(urls) > max_uses:
            return {
                "success": False,
                "error": f"rate_limit_exceeded: Maximum {max_uses} URLs allowed",
                "error_code": "rate_limit_exceeded",
            }
        
        results = []
        for url in urls:
            result = self.fetch_url(url, explicitly_provided, enable_citations)
            results.append(result)
        
        successful = [r for r in results if r.get("success")]
        failed = [r for r in results if not r.get("success")]
        
        return {
            "success": len(failed) == 0,
            "results": results,
            "successful_count": len(successful),
            "failed_count": len(failed),
        }

