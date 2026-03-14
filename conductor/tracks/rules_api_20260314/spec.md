# Specification: External Rules API

## Objective
To expose Oricli-Alpha's internal `.ori` rules framework (`oricli_core/rules/`) via the Native REST API. This allows external applications to dynamically manage (CRUD) global safety, routing, and resource policies, aligning rule management with the recently implemented Skills API.

## Background
Currently, global rules are stored as declarative `.ori` files and loaded via the `RulesEngine`. Like skills, they are internal and static unless manually modified on disk. The user has requested the ability to manage these rules externally to inject new constraints or routing preferences without touching the server's filesystem.

## Requirements

### 1. RulesEngine Refactor
Update `oricli_core/rules/engine.py` to support CRUD operations analogous to the `skill_manager`:
- `list_rules`: Return all loaded rules.
- `get_rule`: Return a specific rule by name.
- `create_rule`: Serialize rule data into the `.ori` format, save to disk, and reload.
- `update_rule`: Overwrite an existing rule file and reload.
- `delete_rule`: Remove a rule file and reload.

### 2. REST API Endpoints (`/v1/rules`)
Add new routes to `oricli_core/api/server.py`:
- `GET /v1/rules`: List all rules.
- `GET /v1/rules/{rule_name}`: Retrieve a specific rule.
- `POST /v1/rules`: Create a new rule.
- `PUT /v1/rules/{rule_name}`: Update a rule.
- `DELETE /v1/rules/{rule_name}`: Delete a rule.

### 3. Pydantic Models
Add models to `oricli_core/types/models.py`:
- `RuleCreateRequest`
- `RuleUpdateRequest`
- `RuleResponse`
- `RuleListResponse`

### 4. Client Integration
Extend `OricliAlphaClient` with a `client.rules` namespace, supporting both local execution and remote REST routing.

### 5. Rule Formatting
A valid rule `.ori` file contains:
- `@rule_name`
- `@description`
- `@scope`
- `@categories`
- `<constraints>` list
- `<routing_preferences>` list
- `<resource_policies>` list

## Success Criteria
- External scripts can perform full CRUD on rules over HTTP.
- Created rules are persisted in `oricli_core/rules/` and take effect immediately.
- `OricliAlphaClient` successfully exposes `.rules.create()`, `.rules.list()`, etc.
