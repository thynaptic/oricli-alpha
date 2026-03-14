# Implementation Plan: External Rules API

## Phase 1: RulesEngine CRUD
- [ ] Add `get_all_rules`, `get_rule_by_name`, `create_rule`, `update_rule`, and `delete_rule` to `RulesEngine` in `oricli_core/rules/engine.py`.
- [ ] Implement `_write_rule_file` to serialize a rule into the custom `.ori` string format.

## Phase 2: API Models
- [ ] Add `RuleCreateRequest`, `RuleUpdateRequest`, `RuleResponse`, `RuleListResponse` to `oricli_core/types/models.py`.

## Phase 3: REST API Endpoints
- [ ] Add `GET /v1/rules` endpoint to `oricli_core/api/server.py`.
- [ ] Add `GET /v1/rules/{rule_name}` endpoint.
- [ ] Add `POST /v1/rules` endpoint.
- [ ] Add `PUT /v1/rules/{rule_name}` endpoint.
- [ ] Add `DELETE /v1/rules/{rule_name}` endpoint.

## Phase 4: Client Integration
- [ ] Create `Rules` class in `oricli_core/client.py` handling remote and local routing.
- [ ] Initialize `self.rules` in `OricliAlphaClient.__init__`.

## Phase 5: Testing
- [ ] Write `scripts/test_rules_api.py` to test the new CRUD endpoints over HTTP.