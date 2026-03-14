# Implementation Plan: External Agents API

## Phase 1: AgentProfileService Refactor
- [ ] Implement `list_all_profiles`, `create_custom_profile`, `update_custom_profile`, and `delete_custom_profile` in `oricli_core/services/agent_profile_service.py`.
- [ ] Add persistence logic to save/load custom profiles from `oricli_core/data/custom_profiles.json`.

## Phase 2: API Models
- [ ] Add `AgentCreateRequest`, `AgentUpdateRequest`, `AgentResponse`, `AgentListResponse` to `oricli_core/types/models.py`.

## Phase 3: REST API Endpoints
- [ ] Add `GET /v1/agents` endpoint to `oricli_core/api/server.py`.
- [ ] Add `GET /v1/agents/{agent_name}` endpoint.
- [ ] Add `POST /v1/agents` endpoint.
- [ ] Add `PUT /v1/agents/{agent_name}` endpoint.
- [ ] Add `DELETE /v1/agents/{agent_name}` endpoint.

## Phase 4: Client Integration
- [ ] Create `Agents` class in `oricli_core/client.py`.
- [ ] Initialize `self.agents` in `OricliAlphaClient.__init__`.

## Phase 5: Swarm Integration & Validation
- [ ] Ensure `ModuleRegistry` or `HiveNode` can resolve the new custom profiles during task bidding.
- [ ] Write `scripts/test_agents_api.py` to verify the full factory-to-execution flow.
- [ ] Create `docs/AGENTS_API.md`.
