# Implementation Plan: External Skills API

## Phase 1: Skill Manager CRUD
- [ ] Add `list_skills` operation to `oricli_core/brain/modules/skill_manager.py`.
- [ ] Add `create_skill` operation to serialize dicts into `.ori` files.
- [ ] Add `update_skill` operation to overwrite `.ori` files.
- [ ] Add `delete_skill` operation to remove `.ori` files.

## Phase 2: API Models
- [ ] Add `SkillCreateRequest`, `SkillUpdateRequest`, `SkillResponse`, `SkillListResponse` to `oricli_core/types/models.py`.

## Phase 3: REST API Endpoints
- [ ] Add `GET /v1/skills` endpoint to `oricli_core/api/server.py`.
- [ ] Add `GET /v1/skills/{skill_name}` endpoint.
- [ ] Add `POST /v1/skills` endpoint.
- [ ] Add `PUT /v1/skills/{skill_name}` endpoint.
- [ ] Add `DELETE /v1/skills/{skill_name}` endpoint.

## Phase 4: Client Integration
- [ ] Add `Skills` class to `oricli_core/client.py` handling remote and local routing.
- [ ] Initialize `self.skills` in `OricliAlphaClient.__init__`.

## Phase 5: Testing & Documentation
- [ ] Write `scripts/test_skills_api.py` to test the new endpoints.
- [ ] Update `docs/EXTERNAL_AGENT_INTEGRATION.md` with instructions on how to use the Skills API.