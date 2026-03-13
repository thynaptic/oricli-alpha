---
name: Web Fetch Tool Implementation
overview: Implement a web fetch tool similar to Anthropic's web fetch tool. The tool retrieves full content from web pages and PDF documents, with strict URL validation (only explicitly provided URLs), domain filtering, rate limiting, PDF extraction support, and citations. It will be available both as a brain module for direct access and as a built-in server tool for programmatic calling.
todos: []
---

# Web Fetch Tool Implementation Plan

## Overview

Implement a secure web fetch tool that retrieves full content from web pages and PDF documents. The tool enforces strict URL validation (only URLs explicitly provided by the user), supports domain filtering, rate limiting, PDF extraction, and citations. Available both as a brain module and as a built-in server tool.

## Architecture

### Components

1. **Web Fetch Module** (`oricli_core/brain/modules/web_fetch.py`)

   - BaseBrainModule implementation for direct web fetching
   - URL validation and security checks
   - HTML content extraction and cleaning
   - PDF text extraction
   - Citation generation
   - Rate limiting

2. **Web Fetch Tool Service** (`oricli_core/services/web_fetch_service.py`)

   - Service layer for web fetching operations
   - URL validation logic
   - Domain filtering (allowed/blocked domains)
   - Content extraction and processing
   - PDF parsing integration

3. **Tool Registration** (Integration with ToolRegistry)

   - Register web_fetch as a built-in server tool
   - Support for `web_fetch_20250910` tool type
   - Configuration options: max_uses, allowed_domains, blocked_domains, citations, max_content_tokens

4. **API Integration** (`oricli_core/api/server.py`)

   - Endpoint for web fetch operations
   - Tool invocation support via tool registry

## Implementation Details

### 1. Web Fetch Module (`oricli_core/brain/modules/web_fetch.py`)

**Operations:**

- `fetch_url` - Fetch content from a URL (HTML or PDF)
- `fetch_multiple` - Fetch multiple URLs in batch
- `validate_url` - Validate URL before fetching
- `extract_pdf` - Extract text from PDF (if URL is PDF)

**Features:**

- Strict URL validation - only URLs explicitly provided
- Domain filtering (allowed_domains, blocked_domains)
- Rate limiting to prevent abuse
- HTML content extraction with BeautifulSoup
- PDF text extraction with PyPDF2 or pdfplumber
- Content cleaning (remove scripts, styles, etc.)
- Citation generation with source URL and metadata
- Max content tokens limit
- User-Agent rotation
- Timeout handling
- Error handling with specific error codes

### 2. Web Fetch Service (`oricli_core/services/web_fetch_service.py`)

**Key Classes:**

- `WebFetchService` - Main service class
- `URLValidator` - URL validation and security checks
- `ContentExtractor` - Content extraction (HTML/PDF)
- `CitationGenerator` - Generate citations for fetched content

**Security Features:**

- Strict URL validation: only URLs from explicit input
- Domain allowlist/blocklist checking
- Protocol validation (only http/https)
- Content size limits
- Rate limiting per domain/IP
- User-Agent rotation
- Timeout limits

### 3. Tool Configuration

**Tool Definition Structure:**

```python
{
    "type": "web_fetch_20250910",
    "name": "web_fetch",
    "max_uses": 10,  # Maximum fetches per request
    "allowed_domains": ["example.com"],  # Optional allowlist
    "blocked_domains": ["private.example.com"],  # Optional blocklist
    "citations": {"enabled": True},
    "max_content_tokens": 100000,
}
```

### 4. URL Validation Rules

**Strict Validation (Anthropic-style):**

- Only URLs that are explicitly provided by the user in the request
- URLs cannot be constructed dynamically or from tool results
- URLs must be valid HTTP/HTTPS URLs
- Domain must pass allowlist/blocklist checks (if configured)
- No redirects to unauthorized domains
- No data exfiltration via URL parameters

**Validation Flow:**

1. Check if URL was explicitly provided in request
2. Validate URL format (http/https)
3. Check domain against allowlist (if set)
4. Check domain against blocklist (if set)
5. Validate URL is accessible (no private/internal URLs)
6. Check rate limits

### 5. Content Extraction

**HTML Extraction:**

- Use BeautifulSoup for parsing
- Extract main content (similar to readability)
- Remove scripts, styles, navigation, ads
- Clean HTML to plain text
- Preserve structure (headings, lists, etc.)
- Extract metadata (title, description, author)

**PDF Extraction:**

- Detect PDF via Content-Type or file extension
- Use PyPDF2 or pdfplumber for text extraction
- Extract text from all pages
- Preserve structure where possible
- Handle encrypted/protected PDFs gracefully

### 6. Citations

**Citation Format:**

- Source URL
- Title (if available)
- Author (if available)
- Publication date (if available)
- Access date
- Content excerpt or summary

### 7. Error Handling

**Error Codes (Anthropic-compatible):**

- `invalid_input` - Invalid URL format or missing URL
- `url_not_accessible` - URL cannot be accessed
- `domain_not_allowed` - Domain not in allowlist
- `domain_blocked` - Domain in blocklist
- `content_too_large` - Content exceeds max_content_tokens
- `rate_limit_exceeded` - Too many requests
- `pdf_extraction_failed` - PDF cannot be parsed
- `timeout` - Request timed out

## File Structure

```
oricli_core/
├── services/
│   └── web_fetch_service.py
├── brain/
│   └── modules/
│       └── web_fetch.py
├── api/
│   └── server.py (extended)
└── types/
    └── models.py (extended)
```

## Dependencies

Add to `pyproject.toml`:

- `requests>=2.31.0` - HTTP client
- `beautifulsoup4>=4.12.0` - HTML parsing
- `PyPDF2>=3.0.0` or `pdfplumber>=0.9.0` - PDF extraction
- `readability-lxml>=0.8.1` - Content extraction (optional enhancement)

## Security Considerations

- **Strict URL validation** - Only explicitly provided URLs
- **Domain filtering** - Allowlist/blocklist support
- **Rate limiting** - Prevent abuse and DoS
- **Content size limits** - Prevent memory exhaustion
- **Timeout limits** - Prevent hanging requests
- **No data exfiltration** - URLs cannot contain sensitive data
- **User-Agent rotation** - Avoid blocking
- **Error sanitization** - Don't leak internal details

## Integration Points

1. **Tool Registry Integration:**

   - Register as built-in server tool
   - Support programmatic calling from code execution
   - Configuration via tool definition

2. **Brain Module Integration:**

   - Available as `web_fetch` module
   - Can be called directly: `client.brain.web_fetch.fetch_url(...)`

3. **API Integration:**

   - Endpoint: `POST /v1/web_fetch` (optional direct endpoint)
   - Tool invocation via `/v1/tools/invoke` with `web_fetch` tool

## Testing Strategy

- Unit tests for URL validation
- Unit tests for content extraction (HTML/PDF)
- Integration tests for full fetch workflow
- Security tests for UR