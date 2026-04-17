# Oracle Routing

Use this skill when the task involves Oracle routing, Copilot CLI integration, Codex multimodal routing, or backend selection inside ORI.

## Focus

- `pkg/oracle/`
- `pkg/api/server_v2.go`
- `pkg/service/generation.go`
- `pkg/api/workspace_handler.go`
- `pkg/cognition/sovereign.go`

## Workflow

1. Read the current Oracle route and execution code before proposing changes.
2. Check whether the task belongs to:
   - light chat
   - heavy reasoning
   - research
   - image reasoning
3. Keep Copilot and Codex responsibilities separate.
4. Prefer explicit route policy over scattered ad hoc conditionals.
5. Verify touched packages with focused `go test` or `go build`.

## Repo-specific rules

- `image_reasoning` belongs to Codex, not the standard Copilot lane.
- Workspace-local focus wins over broad VPS or sibling repo context.
- Do not reintroduce tool-blind Copilot behavior.
- When changing route policy, update tests in `pkg/oracle/oracle_test.go`.
