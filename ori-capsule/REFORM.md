# Reform constitutions in ori-capsule

Port of monorepo `pkg/reform` **constitutions only** — prompt inject for
canvas/code surfaces. No ReformDaemon, no go-vet verifier pipeline, no Ops
constitution (VPS `!command` exec).

## Surfaces

| Trigger | Constitution | Header / cue |
|---|---|---|
| Canvas | `CanvasConstitution` | `X-Ori-Surface: canvas` (or user text contains `canvas`) |
| Code / Dev | `CodeConstitution` | `X-Ori-Surface: dev` |
| Default chat | none | — |

Canvas wins when both canvas and code context are true.

## What is injected

Language-agnostic canvas principles (complete artifacts, no CDN/secrets, etc.)
or Go-oriented code principles (surgical scope, compile-clean, perimeter).

Injected into `/v1/chat/completions` system extras alongside safety constraints.
Zero extra LLM calls.

## Out of scope (VPS)

| Piece | Why |
|---|---|
| `pkg/service/reform_daemon.go` | Host trace→constitution loop |
| `pkg/reform/verifier.go` | `go fmt` / `go vet` / `go build` subprocesses |
| `pkg/reform/ops_constitution.go` | SovereignExec / systemd allowlist |
