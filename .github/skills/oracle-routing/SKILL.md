# Oracle Routing

Use this skill when the task involves Oracle routing, Anthropic API integration, model tier selection, or backend selection inside ORI.

## Focus

- `pkg/oracle/`
- `pkg/api/server_v2.go`
- `pkg/service/generation.go`
- `pkg/api/workspace_handler.go`
- `pkg/cognition/sovereign.go`

## Workflow

1. Read the current Oracle route and execution code before proposing changes.
2. Check whether the task belongs to:
   - light chat (`claude-haiku-4-5-20251001`)
   - heavy reasoning (`claude-sonnet-4-6`)
   - research (`claude-sonnet-4-6`)
   - image reasoning (Anthropic vision via `AnalyzeImage()`)
3. Keep model tier responsibilities cleanly separated — light stays light.
4. Prefer explicit route policy over scattered ad hoc conditionals.
5. Verify touched packages with focused `go test` or `go build`.

## Repo-specific rules

- `image_reasoning` uses Anthropic vision models via `AnalyzeImage()` — not a separate backend.
- Workspace-local focus wins over broad VPS or sibling repo context.
- Do not reintroduce tool-blind or undeclared model behavior.
- When changing route policy, update tests in `pkg/oracle/oracle_test.go`.
