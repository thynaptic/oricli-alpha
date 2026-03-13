from __future__ import annotations
"""
Web Fetch Module

Secure web fetching with strict URL validation, domain filtering,
and PDF support. Available as both a brain module and built-in tool.
"""

from typing import Dict, Any, Optional, List

from oricli_core.brain.base_module import BaseBrainModule, ModuleMetadata
from oricli_core.exceptions import (
    InvalidParameterError,
    ModuleInitializationError,
    ModuleOperationError,
)
import logging
from urllib.parse import urlparse, urlunparse

# Lazy imports to avoid timeout during module discovery
WebFetchService = None
WebFetchError = None
_WEB_FETCH_IMPORT_FAILURE_LOGGED = False

logger = logging.getLogger(__name__)


def _redact_url(url: str) -> str:
    """Redact URL to avoid logging sensitive query/fragment data."""
    try:
        parsed = urlparse(url)
        # Drop query + fragment, keep scheme/host/path.
        return urlunparse((parsed.scheme, parsed.netloc, parsed.path, "", "", ""))
    except Exception:
        return "<invalid-url>"

def _lazy_import_web_fetch_service():
    """Lazy import WebFetchService only when needed"""
    global WebFetchService, WebFetchError, _WEB_FETCH_IMPORT_FAILURE_LOGGED
    if WebFetchService is None:
        try:
            from oricli_core.services.web_fetch_service import (
                WebFetchService as WFS,
                WebFetchError as WFE,
            )
            WebFetchService = WFS
            WebFetchError = WFE
        except ImportError:
            if not _WEB_FETCH_IMPORT_FAILURE_LOGGED:
                _WEB_FETCH_IMPORT_FAILURE_LOGGED = True
                logger.debug(
                    "web_fetch_service not available; web_fetch disabled until installed",
                    exc_info=True,
                    extra={"module_name": "web_fetch"},
                )


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
            raise ModuleInitializationError(
                module_name=self.metadata.name,
                reason="WebFetchService not available",
            )
        if self._service is None:
            try:
                self._service = WebFetchService(**self._default_config)
            except Exception as e:
                logger.debug(
                    "Failed to initialize WebFetchService",
                    exc_info=True,
                    extra={"module_name": "web_fetch", "error_type": type(e).__name__},
                )
                raise ModuleInitializationError(
                    module_name=self.metadata.name,
                    reason="Failed to initialize WebFetchService",
                ) from e
    
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
                raise InvalidParameterError(
                    "operation", str(operation), "Unknown operation for web_fetch"
                )
        except (InvalidParameterError, ModuleInitializationError, ModuleOperationError):
            raise
        except Exception as e:
            logger.debug(
                "web_fetch operation failed",
                exc_info=True,
                extra={"module_name": "web_fetch", "operation": str(operation), "error_type": type(e).__name__},
            )
            raise ModuleOperationError(
                self.metadata.name,
                str(operation),
                "Unexpected error during web fetch operation",
            ) from e
    
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
        if not isinstance(url, str):
            raise InvalidParameterError("url", str(type(url).__name__), "url must be a string")
        
        explicitly_provided = params.get("explicitly_provided", True)
        enable_citations = params.get("enable_citations", True)
        if not isinstance(explicitly_provided, bool):
            raise InvalidParameterError(
                "explicitly_provided", str(explicitly_provided), "explicitly_provided must be a boolean"
            )
        if not isinstance(enable_citations, bool):
            raise InvalidParameterError(
                "enable_citations", str(enable_citations), "enable_citations must be a boolean"
            )
        
        # Update service config if provided
        allowed_domains = params.get("allowed_domains")
        blocked_domains = params.get("blocked_domains")
        max_content_tokens = params.get("max_content_tokens", 100000)
        if allowed_domains is not None and not isinstance(allowed_domains, list):
            raise InvalidParameterError(
                "allowed_domains", str(type(allowed_domains).__name__), "allowed_domains must be a list when provided"
            )
        if blocked_domains is not None and not isinstance(blocked_domains, list):
            raise InvalidParameterError(
                "blocked_domains", str(type(blocked_domains).__name__), "blocked_domains must be a list when provided"
            )
        try:
            max_content_tokens_int = int(max_content_tokens)
        except (TypeError, ValueError):
            raise InvalidParameterError("max_content_tokens", str(max_content_tokens), "max_content_tokens must be an integer")
        if max_content_tokens_int < 1:
            raise InvalidParameterError("max_content_tokens", str(max_content_tokens_int), "max_content_tokens must be >= 1")
        
        if allowed_domains is not None or blocked_domains is not None or max_content_tokens_int != 100000:
            # Create new service with updated config
            service = WebFetchService(
                allowed_domains=allowed_domains,
                blocked_domains=blocked_domains,
                max_content_tokens=max_content_tokens_int,
                rate_limit_delay=self._default_config["rate_limit_delay"],
                timeout=self._default_config["timeout"],
            )
        else:
            service = self._service
        
        try:
            return service.fetch_url(url, explicitly_provided, enable_citations)
        except Exception as e:
            # Avoid leaking full URL in error messages.
            logger.debug(
                "fetch_url failed",
                exc_info=True,
                extra={"module_name": "web_fetch", "url": _redact_url(url), "error_type": type(e).__name__},
            )
            raise ModuleOperationError(self.metadata.name, "fetch_url", "Failed to fetch URL") from e
    
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
        if not all(isinstance(u, str) and u for u in urls):
            raise InvalidParameterError("urls", "non-string", "All urls must be non-empty strings")
        
        explicitly_provided = params.get("explicitly_provided", True)
        enable_citations = params.get("enable_citations", True)
        max_uses = params.get("max_uses", 10)
        if not isinstance(explicitly_provided, bool):
            raise InvalidParameterError(
                "explicitly_provided", str(explicitly_provided), "explicitly_provided must be a boolean"
            )
        if not isinstance(enable_citations, bool):
            raise InvalidParameterError(
                "enable_citations", str(enable_citations), "enable_citations must be a boolean"
            )
        try:
            max_uses_int = int(max_uses)
        except (TypeError, ValueError):
            raise InvalidParameterError("max_uses", str(max_uses), "max_uses must be an integer")
        if max_uses_int < 1:
            raise InvalidParameterError("max_uses", str(max_uses_int), "max_uses must be >= 1")
        
        # Update service config if provided
        allowed_domains = params.get("allowed_domains")
        blocked_domains = params.get("blocked_domains")
        max_content_tokens = params.get("max_content_tokens", 100000)
        if allowed_domains is not None and not isinstance(allowed_domains, list):
            raise InvalidParameterError(
                "allowed_domains", str(type(allowed_domains).__name__), "allowed_domains must be a list when provided"
            )
        if blocked_domains is not None and not isinstance(blocked_domains, list):
            raise InvalidParameterError(
                "blocked_domains", str(type(blocked_domains).__name__), "blocked_domains must be a list when provided"
            )
        try:
            max_content_tokens_int = int(max_content_tokens)
        except (TypeError, ValueError):
            raise InvalidParameterError("max_content_tokens", str(max_content_tokens), "max_content_tokens must be an integer")
        if max_content_tokens_int < 1:
            raise InvalidParameterError("max_content_tokens", str(max_content_tokens_int), "max_content_tokens must be >= 1")
        
        if allowed_domains is not None or blocked_domains is not None or max_content_tokens_int != 100000:
            # Create new service with updated config
            service = WebFetchService(
                allowed_domains=allowed_domains,
                blocked_domains=blocked_domains,
                max_content_tokens=max_content_tokens_int,
                rate_limit_delay=self._default_config["rate_limit_delay"],
                timeout=self._default_config["timeout"],
            )
        else:
            service = self._service
        
        try:
            return service.fetch_multiple(urls, explicitly_provided, enable_citations, max_uses_int)
        except Exception as e:
            logger.debug(
                "fetch_multiple failed",
                exc_info=True,
                extra={
                    "module_name": "web_fetch",
                    "url_count": len(urls),
                    "error_type": type(e).__name__,
                },
            )
            raise ModuleOperationError(self.metadata.name, "fetch_multiple", "Failed to fetch URLs") from e
    
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
        if not isinstance(url, str):
            raise InvalidParameterError("url", str(type(url).__name__), "url must be a string")
        
        explicitly_provided = params.get("explicitly_provided", True)
        allowed_domains = params.get("allowed_domains")
        blocked_domains = params.get("blocked_domains")
        if not isinstance(explicitly_provided, bool):
            raise InvalidParameterError(
                "explicitly_provided", str(explicitly_provided), "explicitly_provided must be a boolean"
            )
        if allowed_domains is not None and not isinstance(allowed_domains, list):
            raise InvalidParameterError(
                "allowed_domains", str(type(allowed_domains).__name__), "allowed_domains must be a list when provided"
            )
        if blocked_domains is not None and not isinstance(blocked_domains, list):
            raise InvalidParameterError(
                "blocked_domains", str(type(blocked_domains).__name__), "blocked_domains must be a list when provided"
            )
        
        # Create validator with config
        from oricli_core.services.web_fetch_service import URLValidator
        validator = URLValidator(allowed_domains, blocked_domains)
        
        is_valid, error = validator.validate_url(url, explicitly_provided)
        
        return {
            "valid": is_valid,
            "error": error,
            "error_code": error.split(":")[0] if error and ":" in error else None,
        }

