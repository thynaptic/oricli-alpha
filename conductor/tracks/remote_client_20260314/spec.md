# Specification: Remote Client Capability (OricliAlphaClient)

## Objective
To enable `OricliAlphaClient` to interact with Oricli-Alpha instances over the network via its REST API, while maintaining backward compatibility with its current local proxy behavior.

## Background
Currently, `OricliAlphaClient` is a local-only proxy that imports and executes brain modules directly. To support distributed architectures and external applications, the client needs to support a `base_url` parameter and route calls to the REST API when initialized in "remote mode".

## Requirements

### 1. Dual-Mode Initialization
- Update `OricliAlphaClient.__init__` to accept:
    - `base_url: Optional[str]`: The base URL of a remote Oricli API (e.g., `http://localhost:8000`).
    - `api_key: Optional[str]`: Authentication key for the remote API.

### 2. Remote Routing
- If `base_url` is provided, the client should:
    - Use `httpx` to route `chat.completions`, `embeddings`, `goals`, `swarm`, and `knowledge` calls to the corresponding REST endpoints.
    - Support a subset of `brain` module calls via the REST API's module execution endpoints.

### 3. Transparent Fallback
- If `base_url` is `None` (default), the client must continue to function as a local proxy, importing modules directly from the filesystem.

## Success Criteria
- `client = OricliAlphaClient(base_url="...")` can successfully create goals and trigger swarms on a remote server.
- Existing local-only scripts continue to work without modification.
- API authentication is handled correctly in remote mode.
