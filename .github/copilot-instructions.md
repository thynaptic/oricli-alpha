# Copilot instructions for Mavaia / ORI

This repository is a Go-based ORI runtime, not the older Python/FastAPI stack.

## Core expectations

- Treat `/home/mike/Mavaia` as the active workspace unless the task explicitly points elsewhere.
- Keep responses and changes anchored to the current repo and current product surface.
- Do not let broad VPS knowledge or sibling repos bleed into repo-local work unless the prompt explicitly asks for host-level context.

## Architecture

- Main API surface lives in `pkg/api/`.
- Runtime orchestration and services live in `pkg/service/`.
- Sovereign cognition and prompt shaping live in `pkg/cognition/`.
- Oracle routing and premium CLI backends live in `pkg/oracle/`.
- Product and architecture handoff docs start with:
  - `docs/AGENT_KNOWLEDGE_LAYER.md`
  - `docs/SESSION_HANDOFF.md`

## Engineering rules

- Prefer small, surgical changes over broad refactors unless the task requires a larger migration.
- Preserve existing product boundaries across Studio, Home, Dev, and Red.
- Use `gofmt -w` on edited Go files.
- Run focused `go test` or `go build` checks on touched packages before finishing when feasible.
- Update stale docs when implementation truth changes, especially for Oracle, routing, or public API behavior.
- Repo-level MCP configuration lives in `.mcp.json`.
- The ORI MCP server expects `ORI_API_KEY` (bearer token) in the request headers. `ANTHROPIC_API_KEY` must be set in the engine environment for Oracle to function.

## Oracle guidance

- `light_chat` should stay fast and low-overhead (`claude-haiku-4-5-20251001`).
- `heavy_reasoning` uses `claude-sonnet-4-6` for strong code and architecture work.
- `research` should behave like a read-heavy investigative helper (`claude-sonnet-4-6`).
- `image_reasoning` uses Anthropic vision via `AnalyzeImage()` — not a separate model lane.

## What not to assume

- Do not assume old Python-era files or docs reflect current runtime behavior.
- Do not assume one prompt overlay is equivalent to an agent, a skill, and a tool at the same time.
- Do not silently widen tool permissions or product scope without making the change explicit in code or config.
