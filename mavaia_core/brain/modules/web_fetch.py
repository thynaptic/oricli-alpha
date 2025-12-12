"""
Web Fetch Module

Secure web fetching with strict URL validation, domain filtering,
and PDF support. Available as both a brain module and built-in tool.
"""

from typing import Dict, Any, Optional, List

from mavaia_core.brain.base_module import BaseBrainModule, ModuleMetadata
from mavaia_core.exceptions import ModuleOperationError, InvalidParameterError

# Lazy imports to avoid timeout during module discovery
WebFetchService = None
WebFetchError = None

def _lazy_import_web_fetch_service():
    """Lazy import WebFetchService only when needed"""
    global WebFetchService, WebFetchError
    if WebFetchService is None:
        try:
            from mavaia_core.services.web_fetch_service import (
                WebFetchService as WFS,
                WebFetchError as WFE,
            )
            WebFetchService = WFS
            WebFetchError = WFE
        except ImportError:
            pass


class WebFetchModule(BaseBrainModule):
    """
    Web fetch module for retrieving content from web pages and PDFs.
    
    Enforces strict URL validation - only URLs explicitly provided by the user
    can be fetched. Supports domain filtering, rate limiting, and citations.
    """
    
    def __init__(self):
        """Initialize web fetch module."""
        super().__init__()
        self._service: Optional[WebFetchService] = None
        self._default_config = {
            "allowed_domains": None,
            "blocked_domains": None,
            "max_content_tokens": 100000,
            "rate_limit_delay": 1.0,
            "timeout": 30,
        }
    
    @property
    def metadata(self) -> ModuleMetadata:
        """Return module metadata."""
        return ModuleMetadata(
            name="web_fetch",
            version="1.0.0",
            description="Secure web fetching with strict URL validation and PDF support",
            operations=[
                "fetch_url",
                "fetch_multiple",
                "validate_url",
            ],
            dependencies=["requests>=2.31.0", "beautifulsoup4>=4.12.0", "PyPDF2>=3.0.0"],
            enabled=True,
            model_required=False,
        )
    
    def initialize(self) -> bool:
        """Initialize the module."""
        # Don't initialize service here - it's heavy, will initialize lazily
        return True
    
    def _ensure_service(self):
        """Lazy initialize service only when needed"""
        _lazy_import_web_fetch_service()
        if WebFetchService is None:
            raise RuntimeError("WebFetchService not available")
        if self._service is None:
        try:
            self._service = WebFetchService(**self._default_config)
        except Exception as e:
                print(f"[WebFetchModule] Failed to initialize service: {e}")
                raise
    
    def execute(self, operation: str, params: Dict[str, Any]) -> Dict[str, Any]:
        """Execute a web fetch operation."""
        self._ensure_service()
        
        try:
            if operation == "fetch_url":
                return self._fetch_url(params)
            elif operation == "fetch_multiple":
                return self._fetch_multiple(params)
            elif operation == "validate_url":
                return self._validate_url(params)
            else:
                raise ValueError(f"Unknown operation: {operation}")
        except (WebFetchError, InvalidParameterError) as e:
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
    
    def _fetch_url(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """
        Fetch content from a URL.
        
        Args:
            url: URL to fetch (required)
            explicitly_provided: Whether URL was explicitly provided (default: True)
            enable_citations: Whether to generate citations (default: True)
            allowed_domains: Optional list of allowed domains
            blocked_domains: Optional list of blocked domains
            max_content_tokens: Maximum content tokens (default: 100000)
        """
        url = params.get("url")
        if not url:
            raise InvalidParameterError("url", "", "URL is required")
        
        explicitly_provided = params.get("explicitly_provided", True)
        enable_citations = params.get("enable_citations", True)
        
        # Update service config if provided
        allowed_domains = params.get("allowed_domains")
        blocked_domains = params.get("blocked_domains")
        max_content_tokens = params.get("max_content_tokens", 100000)
        
        if allowed_domains is not None or blocked_domains is not None or max_content_tokens != 100000:
            # Create new service with updated config
            service = WebFetchService(
                allowed_domains=allowed_domains,
                blocked_domains=blocked_domains,
                max_content_tokens=max_content_tokens,
                rate_limit_delay=self._default_config["rate_limit_delay"],
                timeout=self._default_config["timeout"],
            )
        else:
            service = self._service
        
        result = service.fetch_url(url, explicitly_provided, enable_citations)
        return result
    
    def _fetch_multiple(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """
        Fetch multiple URLs.
        
        Args:
            urls: List of URLs to fetch (required)
            explicitly_provided: Whether URLs were explicitly provided (default: True)
            enable_citations: Whether to generate citations (default: True)
            max_uses: Maximum number of URLs to fetch (default: 10)
            allowed_domains: Optional list of allowed domains
            blocked_domains: Optional list of blocked domains
            max_content_tokens: Maximum content tokens (default: 100000)
        """
        urls = params.get("urls")
        if not urls:
            raise InvalidParameterError("urls", "", "URLs list is required")
        
        if not isinstance(urls, list):
            raise InvalidParameterError("urls", str(type(urls)), "URLs must be a list")
        
        explicitly_provided = params.get("explicitly_provided", True)
        enable_citations = params.get("enable_citations", True)
        max_uses = params.get("max_uses", 10)
        
        # Update service config if provided
        allowed_domains = params.get("allowed_domains")
        blocked_domains = params.get("blocked_domains")
        max_content_tokens = params.get("max_content_tokens", 100000)
        
        if allowed_domains is not None or blocked_domains is not None or max_content_tokens != 100000:
            # Create new service with updated config
            service = WebFetchService(
                allowed_domains=allowed_domains,
                blocked_domains=blocked_domains,
                max_content_tokens=max_content_tokens,
                rate_limit_delay=self._default_config["rate_limit_delay"],
                timeout=self._default_config["timeout"],
            )
        else:
            service = self._service
        
        result = service.fetch_multiple(urls, explicitly_provided, enable_citations, max_uses)
        return result
    
    def _validate_url(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """
        Validate a URL.
        
        Args:
            url: URL to validate (required)
            explicitly_provided: Whether URL was explicitly provided (default: True)
            allowed_domains: Optional list of allowed domains
            blocked_domains: Optional list of blocked domains
        """
        url = params.get("url")
        if not url:
            raise InvalidParameterError("url", "", "URL is required")
        
        explicitly_provided = params.get("explicitly_provided", True)
        allowed_domains = params.get("allowed_domains")
        blocked_domains = params.get("blocked_domains")
        
        # Create validator with config
        from mavaia_core.services.web_fetch_service import URLValidator
        validator = URLValidator(allowed_domains, blocked_domains)
        
        is_valid, error = validator.validate_url(url, explicitly_provided)
        
        return {
            "valid": is_valid,
            "error": error,
            "error_code": error.split(":")[0] if error and ":" in error else None,
        }

