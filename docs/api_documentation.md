# API Documentation

Complete API documentation for Oricli-Alpha Core.

## Base URL

- Production: `https://oricli.thynaptic.com`
- Local: `http://localhost:8081`

## Authentication

API key authentication is configurable. Configure via:

- Environment variable: `MAVAIA_API_KEY` - Set the API key
- Environment variable: `MAVAIA_REQUIRE_AUTH` - Set to `true` to require authentication (default: `false`)
- Server argument: `--api-key` - Set API key via command line
- Server argument: `--require-auth` - Require authentication for all requests
- Header: `Authorization: Bearer <api-key>` - Provide API key in request header

**Default Behavior:**
- If no API key is configured: All requests are allowed (no authentication)
- If API key is configured but `require_auth=false`: API key is validated if provided, but not required
- If `require_auth=true`: All requests must include valid API key

**Example:**
```bash
# Set API key via environment variable
export MAVAIA_API_KEY="your-secret-key"

# Require authentication
export MAVAIA_REQUIRE_AUTH="true"

# Start server
oricli-server --port 8000

# Or set via command line
oricli-server --port 8000 --api-key "your-secret-key" --require-auth
```

## OpenAI-Compatible Endpoints

### Chat Completions

Create a chat completion.

**Endpoint:** `POST /v1/chat/completions`

**Request:**
```json
{
  "model": "oricli-cognitive",
  "messages": [
    {"role": "user", "content": "Hello, how are you?"}
  ],
  "temperature": 0.7,
  "max_tokens": 1000,
  "stream": false
}
```

**Response:**
```json
{
  "id": "chatcmpl-123",
  "object": "chat.completion",
  "created": 1694268190,
  "model": "oricli-cognitive",
  "choices": [
    {
      "index": 0,
      "message": {
        "role": "assistant",
        "content": "Hello! I'm doing well, thank you for asking."
      },
      "finish_reason": "stop"
    }
  ],
  "usage": {
    "prompt_tokens": 10,
    "completion_tokens": 12,
    "total_tokens": 22
  }
}
```

**Parameters:**
- `model` (string, required): Model identifier (default: "oricli-cognitive")
- `messages` (array, required): Conversation messages
- `temperature` (float, optional): Sampling temperature (0.0-2.0, default: 0.7)
- `max_tokens` (integer, optional): Maximum tokens to generate
- `stream` (boolean, optional): Stream responses (default: false)
- `personality_id` (string, optional): Personality identifier
- `use_memory` (boolean, optional): Use conversation memory (default: true)
- `use_reasoning` (boolean, optional): Use reasoning layer (default: true)

### Embeddings

Create embeddings for text.

**Endpoint:** `POST /v1/embeddings`

**Request:**
```json
{
  "input": "text to embed",
  "model": "oricli-embeddings"
}
```

**Response:**
```json
{
  "object": "list",
  "data": [
    {
      "object": "embedding",
      "embedding": [0.1, 0.2, 0.3, ...],
      "index": 0
    }
  ],
  "model": "oricli-embeddings",
  "usage": {
    "prompt_tokens": 4,
    "total_tokens": 4
  }
}
```

**Parameters:**
- `input` (string or array, required): Text(s) to embed
- `model` (string, optional): Embedding model (default: "oricli-embeddings")

### Models

List available models.

**Endpoint:** `GET /v1/models`

**Response:**
```json
{
  "object": "list",
  "data": [
    {
      "id": "oricli-cognitive",
      "object": "model",
      "created": 1694268190,
      "owned_by": "oricli",
      "permission": [],
      "root": "oricli-cognitive",
      "parent": null
    }
  ]
}
```

## Oricli-Alpha-Specific Endpoints

### List Modules

List available brain modules.

**Endpoint:** `GET /v1/modules`

**Response:**
```json
{
  "modules": [
    {
      "name": "reasoning",
      "version": "1.0.0",
      "description": "Reasoning module",
      "operations": ["reason"],
      "enabled": true,
      "model_required": false
    }
  ]
}
```

### Health Check

Check server health.

**Endpoint:** `GET /health`

**Response:**
```json
{
  "status": "healthy",
  "service": "oricli-core",
  "version": "1.0.0"
}
```

## Error Responses

All errors follow this format:

```json
{
  "error": {
    "message": "Error message",
    "type": "error_type",
    "code": 500
  }
}
```

**Error Types:**
- `invalid_request_error`: Invalid request parameters (400)
- `authentication_error`: Authentication failed (401)
- `server_error`: Server error (500)

### Authentication Errors

When API key authentication is required but fails:

**Response (401):**
```json
{
  "error": {
    "message": "Authentication failed: Invalid API key",
    "type": "authentication_error",
    "code": 401
  }
}
```

**Common Scenarios:**
- Missing `Authorization` header when `MAVAIA_REQUIRE_AUTH=true`
- Invalid API key format (must be `Bearer <token>`)
- Incorrect API key value

**Example:**
```bash
# Missing header
curl -X POST http://localhost:8000/v1/chat/completions \
  -H "Content-Type: application/json" \
  -d '{"model": "oricli-cognitive", "messages": [{"role": "user", "content": "Hello"}]}'
# Returns 401 if authentication required

# Invalid format
curl -X POST http://localhost:8000/v1/chat/completions \
  -H "Authorization: invalid-format" \
  -H "Content-Type: application/json" \
  -d '{"model": "oricli-cognitive", "messages": [{"role": "user", "content": "Hello"}]}'
# Returns 401: "Invalid authorization format. Expected 'Bearer <token>'"

# Wrong API key
curl -X POST http://localhost:8000/v1/chat/completions \
  -H "Authorization: Bearer wrong-key" \
  -H "Content-Type: application/json" \
  -d '{"model": "oricli-cognitive", "messages": [{"role": "user", "content": "Hello"}]}'
# Returns 401: "Invalid API key"
```

### Validation Errors

When request parameters are invalid:

**Response (400):**
```json
{
  "error": {
    "message": "Validation failed for field 'messages': messages is required",
    "type": "invalid_request_error",
    "code": 400
  }
}
```

**Common Scenarios:**
- Missing required fields (`messages`, `input`)
- Invalid parameter types
- Parameter values out of range (e.g., `temperature > 2.0`)

**Example:**
```bash
# Missing messages
curl -X POST http://localhost:8000/v1/chat/completions \
  -H "Content-Type: application/json" \
  -d '{"model": "oricli-cognitive"}'
# Returns 400: "messages is required"

# Invalid temperature
curl -X POST http://localhost:8000/v1/chat/completions \
  -H "Content-Type: application/json" \
  -d '{
    "model": "oricli-cognitive",
    "messages": [{"role": "user", "content": "Hello"}],
    "temperature": 3.0
  }'
# Returns 400: "temperature must be between 0.0 and 2.0"
```

### Server Errors

When an internal error occurs:

**Response (500):**
```json
{
  "error": {
    "message": "Error generating chat completion: cognitive_generator module not available",
    "type": "server_error",
    "code": 500
  }
}
```

**Common Scenarios:**
- Module not found or failed to initialize
- Module operation failed
- Internal processing error

**Example:**
```bash
# Module unavailable
curl -X POST http://localhost:8000/v1/chat/completions \
  -H "Content-Type: application/json" \
  -d '{
    "model": "oricli-cognitive",
    "messages": [{"role": "user", "content": "Hello"}]
  }'
# Returns 500 if cognitive_generator module is not available
```

### Error Handling in Code

**Python:**
```python
import httpx
from oricli_core.exceptions import (
    AuthenticationError,
    ModuleNotFoundError,
    ModuleOperationError
)

try:
    response = httpx.post(
        "http://localhost:8000/v1/chat/completions",
        json={"model": "oricli-cognitive", "messages": [...]},
        headers={"Authorization": "Bearer your-key"}
    )
    response.raise_for_status()
    print(response.json())
except httpx.HTTPStatusError as e:
    if e.response.status_code == 401:
        print("Authentication failed")
    elif e.response.status_code == 400:
        print("Invalid request:", e.response.json())
    else:
        print("Server error:", e.response.json())
```

**JavaScript:**
```javascript
try {
  const response = await fetch('http://localhost:8000/v1/chat/completions', {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
      'Authorization': 'Bearer your-key'
    },
    body: JSON.stringify({
      model: 'oricli-cognitive',
      messages: [{ role: 'user', content: 'Hello' }]
    })
  });
  
  if (!response.ok) {
    const error = await response.json();
    if (response.status === 401) {
      console.error('Authentication failed:', error.error.message);
    } else if (response.status === 400) {
      console.error('Validation error:', error.error.message);
    } else {
      console.error('Server error:', error.error.message);
    }
    return;
  }
  
  const data = await response.json();
  console.log(data);
} catch (error) {
  console.error('Network error:', error);
}
```

## Streaming

### Chat Completions (Streaming)

Set `stream: true` in the request to receive streaming responses:

**Request:**
```json
{
  "model": "oricli-cognitive",
  "messages": [{"role": "user", "content": "Hello"}],
  "stream": true
}
```

**Response (Server-Sent Events):**
```
data: {"id": "chatcmpl-123", "object": "chat.completion.chunk", ...}
data: {"id": "chatcmpl-123", "object": "chat.completion.chunk", ...}
data: [DONE]
```

## Examples

### Python

```python
import httpx

# Chat completion
response = httpx.post(
    "http://localhost:8000/v1/chat/completions",
    json={
        "model": "oricli-cognitive",
        "messages": [{"role": "user", "content": "Hello"}]
    }
)
print(response.json())

# Embeddings
response = httpx.post(
    "http://localhost:8000/v1/embeddings",
    json={
        "input": "text to embed",
        "model": "oricli-embeddings"
    }
)
print(response.json())
```

### cURL

```bash
# Chat completion
curl -X POST http://localhost:8000/v1/chat/completions \
  -H "Content-Type: application/json" \
  -d '{
    "model": "oricli-cognitive",
    "messages": [{"role": "user", "content": "Hello"}]
  }'

# Embeddings
curl -X POST http://localhost:8000/v1/embeddings \
  -H "Content-Type: application/json" \
  -d '{
    "input": "text to embed",
    "model": "oricli-embeddings"
  }'
```

### JavaScript

```javascript
// Chat completion
const response = await fetch('http://localhost:8000/v1/chat/completions', {
  method: 'POST',
  headers: {
    'Content-Type': 'application/json',
  },
  body: JSON.stringify({
    model: 'oricli-cognitive',
    messages: [{ role: 'user', content: 'Hello' }]
  })
});

const data = await response.json();
console.log(data);
```

## Rate Limiting

Rate limiting is not currently implemented but will be added in future versions.

## Versioning

API versioning is handled via the URL path (`/v1/`). Future versions will use `/v2/`, etc.

## OpenAPI Specification

The API includes an OpenAPI specification available at:
- Swagger UI: `http://localhost:8000/docs`
- ReDoc: `http://localhost:8000/redoc`
- OpenAPI JSON: `http://localhost:8000/openapi.json`

