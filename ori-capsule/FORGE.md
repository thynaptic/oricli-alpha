# Forge static verifier in ori-capsule

Port of monorepo `pkg/forge` **constitution / static gate only** — no generator,
no POC LLM gate, no PocketBase tool library, no runtime sandbox re-verify loop.

## What runs

| Gate | When | Rules |
|---|---|---|
| Script constitution | Every `POST /v1/gosh/run` with `script` | Fatal security patterns (rm -rf, /etc, curl\|sh, sudo, restricted binaries, …) |
| Tool constitution | `strict_tool: true` | Above + stdin/JSON/line-limit contract (JIT tools) |
| Go source scan | `source` / `tools[].source` | Reform Stage-1 stubs + Yaegi escape hatches (`os/exec`, `net/http`, …) |

No `go fmt` / `go vet` / `go build` subprocesses.

## API

### `POST /v1/gosh/verify`

Static-only (does not execute):

```json
{
  "script": "echo hi",
  "source": "package main\nfunc main() {}",
  "tools": [{"name": "x", "source": "..."}],
  "strict_tool": false
}
```

### `POST /v1/gosh/run`

Always verifies first unless `skip_verify: true` (tests). Failed constitution
returns `ok: false` with `verify` details — sandbox never opens.

## Out of scope

| Piece | Why |
|---|---|
| `ToolGenerator` / `POCGate` LLM | Extra LLM; opt-in later if ever |
| `ToolLibrary` PB store | Capsule is local-first |
| Runtime JSON-stdout re-verify | Use GOSH run + ActionTracker instead |
| Admin `/v1/forge/*` | Host admin surface |
