---
name: Gemini URL Context Implementation
overview: Implement Google Gemini URL Context feature that enables automatic URL extraction from messages and content fetching. The implementation will support two-step retrieval (database cache + live fetch), automatic URL detection in prompts, and a tool for explicit URL context requests. Results include url_context_metadata with retrieval status.
todos:
  - id: create_url_context_module
    content: Create url_context.py module with BaseBrainModule structure and metadata
    status: completed
  - id: implement_url_extraction
    content: Implement URL extraction from text using regex patterns
    status: completed
    dependencies:
      - create_url_context_module
  - id: implement_cache
    content: Implement database-backed cache for URL content using DatabaseStorage
    status: completed
    dependencies:
      - create_url_context_module
  - id: implement_two_step_retrieval
    content: Implement two-step retrieval (cache check + live fetch)
    status: completed
    dependencies:
      - implement_cache
  - id: implement_metadata
    content: Implement url_context_metadata tracking and formatting
    status: completed
    dependencies:
      - implement_two_step_retrieval
  - id: add_response_models
    content: Add URLContextMetadata model to types/models.py
    status: completed
  - id: integrate_chat_completion
    content: Integrate URL context extraction and fetching in chat completion flow
    status: completed
    dependencies:
      - implement_metadata
      - add_response_models
  - id: register_tool
    content: Register url_context tool in server.py
    status: completed
    dependencies:
      - implement_metadata
  - id: test_implementation
    content: Test URL extraction, caching, and chat completion integration
    status: completed
    dependencies:
      - register_tool
      - integrate_chat_completion
---

# Gemini URL Context Implementation Plan

## Overview

Implement Google Gemini URL Context feature that enables models to access content from URLs provided in requests. The implementation will support automatic URL detection in prompts, two-step retrieval (cache + live fetch), and return url_context_metadata with retrieval status.

## Architecture

The implementation will:

- Create a `URLContextModule` brain module for URL context operations
- Implement automatic URL extraction from messages/prompts
- Use database-backed cache (existing state_storage) for two-step retrieval
- Leverage existing `WebFetchService` for content fetching
- Register `url_context` tool for explicit URL context requests
- Return results with `url_context_metadata` including retrieval status
- Support up to 20 URLs per request with 34MB per URL limit

## Implementation Steps

### 1. Create URL Context Module

**File**: `mavaia_core/brain/modules/url_context.py`

- Inherit from `BaseBrainModule`
- Implement operations: `extract_urls`, `fetch_url_context`, `get_url_context`
- Integrate with existing `WebFetchService` for content fetching
- Use `DatabaseStorage` for caching URL content

### 2. Implement URL Extraction

**File**: `mavaia_core/brain/modules/url_context.py`

- Extract URLs from text using regex patterns
- Support common URL formats (http://, https://, www.)
- Validate URLs before processing
- Limit to 20 URLs per request

### 3. Implement Two-Step Retrieval

**File**: `mavaia_core/brain/modules/url_context.py`

- Step 1: Check database cache for URL content
- Step 2: If not cached, fetch live content using WebFetchService
- Store fetched content in cache with TTL (e.g., 24 hours)
- Return cached content if available and fresh

### 4. Implement URL Context Metadata

**File**: `mavaia_core/brain/modules/url_context.py`

- Track retrieval status for each URL:
  - `SUCCESS`: Content retrieved successfully
  - `CACHED`: Content retrieved from cache
  - `FAILED`: Failed to retrieve content
  - `UNSUPPORTED`: Content type not supported
- Include metadata: URL, status, content_type, size, retrieval_method

### 5. Integrate with Chat Completion Flow

**Files**: `mavaia_core/client.py`, `mavaia_core/api/openai_compatible.py`

- Automatically detect URLs in messages
- Fetch URL context before generating response
- Include URL context in prompt/context
- Return url_context_metadata in response

### 6. Register URL Context Tool

**File**: `mavaia_core/api/server.py`

- Register `url_context` tool
- Tool should call URLContextModule operations
- Support parameters:
  - `urls`: List of URLs to fetch (up to 20)
  - `use_cache`: Whether to use cache (default: True)

### 7. Add URL Context to Response Models

**File**: `mavaia_core/types/models.py`

- Add `url_context_metadata` field to `ChatCompletionResponse`
- Define `URLContextMetadata` model with status and metadata fields

## Files to Create/Modify

1. **New**: `mavaia_core/brain/modules/url_context.py` - URL context module
2. **Modify**: `mavaia_core/types/models.py` - Add URL context metadata models
3. **Modify**: `mavaia_core/api/server.py` - Register url_context tool
4. **Modify**: `mavaia_core/client.py` - Integrate URL context in chat completion
5. **Modify**: `mavaia_core/api/openai_compatible.py` - Handle URL context in API

## Technical Details

### URL Extraction

- Use regex pattern: `r'https?://[^\s<>"{}|\\^`\[\]]+|www\.[^\s<>"{}|\\^`\[\]]+'`
- Validate URLs using `urllib.parse`
- Extract up to 20 URLs per request
- Remove duplicates

### Two-Step Retrieval

- Cache key: `url_context:{url_hash}`
- Cache TTL: 24 hours (configurable)
- Cache stores: content, content_type, size, fetched_at
- On cache miss: fetch using WebFetchService
- On cache hit: return cached content if fresh

### Content Size Limits

- Maximum 34MB per URL
- Check content size before caching
- Reject URLs exceeding size limit
- Track size in metadata

### Supported Content Types

- text/html (via WebFetchService)
- application/json (via WebFetchService)
- application/pdf (via WebFetchService)
- image/* (basic support, metadata only)
- Unsupported types: video/*, audio/*, paywalled content

### URL Context Metadata Format

```python
{
    "url": "https://example.com",
    "status": "SUCCESS" | "CACHED" | "FAILED" | "UNSUPPORTED",
    "content_type": "text/html",
    "size_bytes": 12345,
    "retrieval_method": "cache" | "live",
    "error": None | "error message"
}
```

### Integration with Chat Completion

- Extract URLs from all messages in request
- Fetch URL context before generation
- Include URL content in context passed to cognitive_generator
- Return url_context_metadata in response

## Testing Considerations

- Test URL extraction from various message formats
- Test cache hit and cache miss scenarios
- Test with multiple URLs (up to 20)
- Test size limit enforcement
- Test unsupported content types
- Test error handling (invalid URLs, network failures)
- Test integration with chat completion flow

## Security Considerations

- Validate all URLs before fetching
- Enforce size limits strictly
- Use existing WebFetchService security (domain filtering, etc.)
- Sanitize cached content
- Rate limit URL fetching
- Handle malicious URLs gracefully