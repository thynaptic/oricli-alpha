# Implementation Plan: Remote Client Capability

## Phase 1: Client Refactor

### 1.1 `__init__` Update
- [ ] Add `base_url` and `api_key` parameters to `OricliAlphaClient.__init__`.
- [ ] Initialize an `httpx.Client` if `base_url` is provided.

### 1.2 Remote Helper Methods
- [ ] Implement `_make_remote_request(method, path, data, params)` to handle HTTP communication and error parsing.

### 1.3 Routing Logic
- [ ] Update `Goals`, `Swarm`, and `Knowledge` classes to check `self._client.base_url`.
- [ ] If remote, use `_make_remote_request` instead of direct service/module calls.
- [ ] Update `ChatCompletions.create` and `Embeddings.create` to support remote routing.

## Phase 2: Brain Module Proxy (Remote)

### 2.1 Remote Module Execution
- [ ] Update `BrainModuleWrapper.execute_operation` to route calls to `POST /v1/modules/{module_name}/{operation}` if the client is in remote mode.

## Phase 3: Validation

### 3.1 Scenario Testing
- [ ] Run `scripts/test_native_api.py` with `base_url="http://localhost:8083"` to verify full remote functionality.
- [ ] Run a standard local smoke test to ensure no regressions in local mode.
