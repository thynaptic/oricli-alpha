# ORI Server State — Current Architecture

> Last updated: 2026-04-18  
> VPS: `thyn` (glm.thynaptic.com)

---

## Service Topology

Three systemd services run on the VPS. Two of them handle live API traffic.

```
Internet
  └── Cloudflare
        └── Caddy (glm.thynaptic.com)
              ├── /v1/mcp   ──────────────► oricli-api.service     :8088
              └── everything else ────────► oricli-backbone.service :8089
```

### `oricli-backbone.service` — primary chat/completions handler
- **Binary**: `/home/mike/Mavaia/bin/oricli-go-v2`
- **Built from**: `cmd/oricli-engine/` (NOT `cmd/backbone/` — despite the name)
- **Port**: 8089 (default, no env override)
- **API key**: `glm.Qbtofkny.F5pTIVYghj-mLSwAtPRGDau1q7k2w5DO`
- **Handles**: all `/v1/chat/completions`, `/v1/models`, and general API traffic
- **Startup script**: `/home/mike/Mavaia/scripts/start_go_hive_pure.sh` → `exec /home/mike/Mavaia/bin/oricli-go-v2`

### `oricli-api.service` — MCP runtime endpoint
- **Binary**: `/home/mike/Mavaia/bin/oricli-go-v2` (same binary, different port)
- **Built from**: `cmd/oricli-engine/`
- **Port**: 8088 (`ORICLI_ENGINE_PORT=8088` in service env)
- **API key**: `ori.8f9f406a.Mo5YFWO0Tx5IKE46fG1mXfA7kAyLzy`
- **Handles**: `/v1/mcp` only (Caddy routes this path specifically to 8088)
- **ExecStart**: `ExecStart=/home/mike/Mavaia/bin/oricli-go-v2`

### `glm-api.service` — G-LM governance sidecar (secondary)
- **Binary**: `/home/mike/G-LM/bin/glm-api`
- **Configured for**: port 8089, upstream to localhost:8088
- **Status**: running (PID active) but currently not binding to 8089 — backbone takes that port first. GLM handles governance/rate-limit duties when it was the primary layer; in current deployment it runs passively.

---

## Runtime Contract Snapshot

This is the current public-facing runtime contract as served by `dev-portal/agent.json`
and enforced by the live API:

- **Runtime base URL**: `https://glm.thynaptic.com/v1`
- **Auth format**: `Authorization: Bearer ori.<prefix>.<secret>`
- **Legacy auth accepted**: `glm.<prefix>.<secret>`
- **Public default model**: `oricli-oracle`
- **Default routing**: `oracle_first`
- **Surface header**: `X-Ori-Context`
- **Environment headers**: `X-Env-OS`, `X-Env-PWD`, `X-Env-Project`, `X-Env-Shell`
- **Default profile behavior**: no profile is required; if omitted, ORI stays on the
  default baseline for that surface

### Surfaced Profiles (current manifest)

- **studio**: `studio_customer_comms`, `studio_operations`, `studio_meetings`,
  `studio_research`, `studio_knowledge`, `ori_north`, `big_sister`
- **home**: `home_companion`, `home_planner`, `home_notes`, `home_research`,
  `big_sister`
- **dev**: `dev_builder`, `dev_architect`, `dev_debugger`, `ori_code`
- **red**: `ori_red`

### Oracle / Copilot Routing (internal runtime reality)

The public API exposes ORI and `oricli-oracle` as the stable entrypoint. Internally,
Oracle currently routes into Copilot/Codex tiers like this:

- **Light chat** → `claude-haiku-4.5` (auto-selected via SDK `ListModels`)
- **Heavy reasoning / code work** → `auto` (Copilot selects best available in real-time)
- **Research / dev** → `claude-sonnet-4.6` (best available Sonnet via SDK `ListModels`)
- **Image reasoning** → Codex (`ori-multimodal`)

These are internal router defaults from `pkg/oracle/oracle.go`, not separate public
models. They may be overridden via `ORACLE_COPILOT_MODEL*` env vars without changing
the public API contract.

---

## The Shared Binary Problem

**Critical gotcha**: Both `oricli-backbone` and `oricli-api` run the **same binary file** at `/home/mike/Mavaia/bin/oricli-go-v2`. The binary is built from `cmd/oricli-engine/`.

**Why `cmd/oricli-engine` and NOT `cmd/backbone`:**
- `cmd/backbone/main.go` hardcodes `apiPort := 8089` and ignores `ORICLI_ENGINE_PORT`
- `cmd/oricli-engine/main.go` reads `ORICLI_ENGINE_PORT` from the environment → same binary, two ports
- The `oricli-api` service sets `ORICLI_ENGINE_PORT=8088`, backbone leaves it unset → defaults to 8089

**How to rebuild and deploy (both services):**

```bash
# 1. Build
go build -o /tmp/oricli-go-v2 ./cmd/oricli-engine/

# 2. Stop both (can't replace a running binary on Linux)
sudo systemctl stop oricli-backbone oricli-api

# 3. Replace
cp /tmp/oricli-go-v2 /home/mike/Mavaia/bin/oricli-go-v2

# 4. Start both
sudo systemctl start oricli-backbone oricli-api

# 5. Verify
ss -tlnp | grep 808   # should see both :8088 and :8089
```

**Previous deploy mistake to avoid**: running `go build -o /usr/local/bin/oricli-engine ./cmd/oricli-engine/` and restarting `oricli-api` did nothing useful — neither service loads from that path.

---

## Workspace Isolation (Remote Clients)

ORI Code (and other remote clients) send workspace headers with each request:

```
X-Ori-Workspace-Cwd:     /Users/cass/Documents/GitHub/ORI-Cast
X-Ori-Workspace-Project: ORI-Cast
X-Ori-Workspace-Branch:  main
```

### The Bug (now fixed)
Without these fixes, ORI would answer "what dir are we in?" with `thynaptic/oricli-alpha` — the Mavaia server's own repo — instead of the client's workspace. Three root causes:

1. **Race condition**: `SovereignEngine` fields (`CurrentRemotePWD` etc.) are shared mutable state on a singleton. Concurrent requests clobbered each other's workspace context.
2. **Copilot repo injection**: The `copilot` CLI, run from `/home/mike/Mavaia`, picks up `.github/copilot-instructions.md` and the GitHub remote origin, overriding any workspace context in the prompt.
3. **Response cache bypass missing**: The `lastMsg`-keyed response cache didn't account for workspace headers — a cached Mavaia-context response could be returned for a workspace-aware query.

### The Fixes (all shipped in commit `c0c453c`)

**Per-request context isolation** (`pkg/cognition/sovereign.go`):
```go
// WorkSpace is passed via context.WithValue, not mutated on the engine singleton
func WithRemoteWorkspace(ctx context.Context, cwd, project, repoRoot, branch string) context.Context
```
`ProcessInference` extracts the workspace from ctx at the top and passes it through — no shared state mutation.

**Compact system prompt** (`pkg/api/server_v2.go`):
When `remotePWD != ""`, the full Mavaia sovereign composite prompt (full of VPS paths and operational context) is replaced with a minimal workspace-scoped system message before the oracle call.

**Oracle isolation sentinel** (`pkg/oracle/oracle.go` + `pkg/oracle/router.go`):
```go
oracleDecision.Agent = "-"          // strips --agent flag
oracleDecision.WorkingDir = os.TempDir()  // copilot runs from /tmp, not /home/mike/Mavaia
```
The `"-"` sentinel in `copilotArgs` passes `--no-custom-instructions --disable-builtin-mcps` to the copilot CLI, stripping all GitHub repo context injection.

**Response cache bypass** (`pkg/api/server_v2.go:1123`):
```go
// Remote workspace requests bypass cache (same query, different answers per workspace)
if !forcedEngine && req.SpaceID == "" && remotePWD == "" && s.ResponseCache != nil && lastMsg != "" {
```

---

## MCP Runtime Endpoint

`POST https://glm.thynaptic.com/v1/mcp`

Routes to **port 8088** (oricli-api.service) via Caddy split-route.  
Auth: `Authorization: Bearer ori.8f9f406a.Mo5YFWO0Tx5IKE46fG1mXfA7kAyLzy`

JSON-RPC 2.0 protocol. Supported methods:

| Method | Description |
|--------|-------------|
| `initialize` | Handshake, returns server info |
| `tools/list` | Returns all 6 ori-runtime tools |
| `tools/call` | Invoke a specific tool |

**Available tools**: `check_health`, `get_key_info`, `get_capabilities`, `list_surfaces`, `list_working_styles`, `get_request_template`

Implementation: `pkg/api/mcp_runtime.go`  
Route registration: `pkg/api/server_v2.go` → `protected.POST("/mcp", s.handleMCP)`  
Copilot MCP config: `.mcp.json` (tracked, `.gitignore` has `!.mcp.json` exception)

---

## Caddy Config

`/etc/caddy/Caddyfile` — `glm.thynaptic.com` block:

```caddy
glm.thynaptic.com {
    tls /etc/caddy/certs/cf_origin.crt /etc/caddy/certs/cf_origin.key

    # MCP endpoint → oricli-api (port 8088)
    handle /v1/mcp {
        reverse_proxy 127.0.0.1:8088 { ... }
    }

    # Everything else → oricli-backbone (port 8089)
    reverse_proxy 127.0.0.1:8089 { ... }
}
```

---

## ori-code (ORI CLI — Mac client)

- **Repo**: `/home/mike/ori-code`
- **Runtime**: Bun (not Node.js)
- **Current version**: `v0.9.15` (released via Homebrew tap)
- **API base**: `https://glm.thynaptic.com/v1` (hardcoded in `src/config/defaults.ts`)
- **Client defaults**: `surface=dev`, `profile=ori_code`, `model=oricli-oracle`
- **Important distinction**: those are `ori-code` client defaults, not the shared public
  runtime default. The runtime default remains `oricli-oracle` with Oracle-first routing.
- **MCP client**: `src/runtime/ori-client.ts` → `invokeMCPTool()` posts to `${apiBase}/mcp`
- **Agent tools**: `src/agent/tools.ts` — all 6 ori-runtime tools wired into `AGENT_TOOLS` and `executeToolCall`
- **Release script**: `scripts/release.sh` — bumps `package.json` + `src/cli/args.ts`, tags, pushes, creates GitHub release tarball, updates `cassianwolfe/homebrew-tap` formula

---

## Key File Locations

| What | Path |
|------|------|
| Main API server source | `pkg/api/server_v2.go` |
| MCP runtime handler | `pkg/api/mcp_runtime.go` |
| Sovereign engine + workspace context | `pkg/cognition/sovereign.go` |
| Composite prompt builder | `pkg/cognition/instructions.go` |
| Oracle router + Decision struct | `pkg/oracle/router.go` |
| Oracle/Copilot dispatch | `pkg/oracle/oracle.go` |
| Output safety filter (leak detection) | `pkg/safety/adversarial.go` |
| Deployed binary | `/home/mike/Mavaia/bin/oricli-go-v2` |
| Build source | `cmd/oricli-engine/main.go` |
| Caddy config | `/etc/caddy/Caddyfile` |
| Backbone startup script | `/home/mike/Mavaia/scripts/start_go_hive_pure.sh` |
