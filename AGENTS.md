# Codex Context For Mavaia / ORI

Mavaia is the ORI platform monorepo for Thynaptic Research. ORI is an OpenAI-compatible reasoning/API layer with session persistence, routing, agent profiles, tool orchestration, memory, and product-surface context.

Read `/home/mike/Mavaia/docs/current/SESSION_HANDOFF.md` first when resuming platform work.

## Repo Layout

- `cmd/oricli-engine/`: primary production headless API binary.
- `cmd/backbone/`: older/full backbone entrypoint; do not use as the default production build target.
- `pkg/api/`: Gin HTTP API. `server_v2.go` is the main router.
- `pkg/oracle/`: direct Anthropic integration, routing, tools, batch, skills, streaming.
- `pkg/llm/`: lightweight Haiku/Sonnet inference wrapper for cognition-tier work.
- `pkg/epistemics/`: conjecture, criticism, synthesis loop.
- `pkg/cognition/`: cognitive modules and daemon behavior.
- `pkg/service/`: generation and service pipeline.
- `pkg/auth/` and `pkg/core/auth/`: tenant/API key validation.
- `dev-portal/`: machine-readable agent manifests and integration docs.
- `ui_sovereignclaw/`: ORI Studio web client.

## Build And Deploy

Production binary path: `/home/mike/Mavaia/bin/oricli-go-v2`

Preferred rebuild shape for live-bound changes:

```bash
cd /home/mike/Mavaia
go build ./cmd/oricli-engine/
ORICLI_ENGINE_PORT=8097 ORICLI_SEED_API_KEY=glm.test.smoke ./oricli-engine
cp oricli-engine bin/oricli-go-v2.new
mv -f bin/oricli-go-v2.new bin/oricli-go-v2
sudo systemctl restart oricli-api
sudo systemctl restart oricli-backbone
curl -s http://127.0.0.1:8088/v1/health
curl -s http://127.0.0.1:8089/v1/health
curl -s https://glm.thynaptic.com/v1/health
```

Use the `.new` swap pattern to avoid text-file-busy issues. After meaningful/live-bound changes: smoke test, verify expected behavior, then restart/deploy the relevant services.

## ORI API Conventions

- Live base URL: `https://glm.thynaptic.com/v1`
- Default model: `oricli-oracle`
- Session ID is `X-Session-ID` header only.
- Empty session ID means stateless one-shot.
- Surface context belongs in `X-Ori-Context`.
- For environment-aware dev integrations, pass `X-Env-OS`, `X-Env-PWD`, `X-Env-Project`, and `X-Env-Shell` when available.
- Update `dev-portal/llms.txt` when API routes or agent integration behavior change.

## Oracle Notes

- `pkg/oracle/oracle.go`: session pool, streaming, vision, agent loader.
- `pkg/oracle/router.go`: route classification.
- `pkg/oracle/model_catalog.go`: model selection and thinking budgets.
- `pkg/oracle/tools.go`: OpenAI-to-Anthropic tool conversion.
- `pkg/oracle/batch.go`: batch lifecycle.
- `pkg/oracle/skills.go`: `.ori` skill overlay loading.

Operational gotchas:

- `ANTHROPIC_API_KEY` must be in systemd env.
- `oracle.Init()` should be called as `go oracle.Init(0)`.
- Tool result messages must preserve `tool_call_id`.
- Extended thinking is not used in `ChatWithTools()`.
- MCP should stay on heavy/research routes.

## Product Direction

Current platform direction:

- ORI is one shared reasoning system with many product surfaces.
- Build reusable intelligence layers before app-specific workflows.
- Research docs should be mined for ORI-wide primitives, not copied as full apps.
- ORI Home now has planning, reflection, and household logistics intelligence layers.
- ORI Studio remains the SMB operator surface.
- ORI Dev remains the builder surface.

Studio guardrails:

- ORI Studio is the SMB operator surface.
- `Jobs` is the customer-facing workflow concept.
- Email-first runtime model is valuable and should be leaned into.
- Starter Jobs should use guided setup modals.
- Keep the tone warm, practical, and relief-oriented.

Avoid:

- AI playground framing.
- Generic workflow-builder framing.
- Dark/aggressive bunker-style marketing.
- Letting ORI Home or ORI Dev concerns dominate Studio.

## Current Platform Next Move

The latest handoff names this as the next best implementation move:

Expose and test the new cognition primitives through a small internal API/tool surface:

- planning plan generation
- reflection plan/review generation
- household logistics Active Pin extraction

Keep the interfaces app-neutral. Clients still own capture, OCR, storage, sync, reminders, calendars, payments, notifications, and consent policy.

## Verification

- For Go changes, run focused `go test` when possible.
- For JS/TS changes, use Bun-first commands.
- For dev portal JSON, validate with `python3 -m json.tool`.
- For UI changes, build and visually verify when a browser/dev server is practical.
- For live-bound changes, finish the loop: smoke test, verify the expected behavior, then restart/deploy the relevant service.
- Test runs can append to `pkg/cognition/.memory/*_audit.jsonl`; remove only generated test-run lines before finishing.

## Cursor Cloud specific instructions

This section is for the Cursor Cloud VM, which differs from the production VPS described above. The repo root here is `/workspace` (not `/home/mike/Mavaia`), and there is **no systemd** — the production `systemctl restart oricli-api/oricli-backbone` and `.new` binary-swap flow do not apply. Build and run directly from `/workspace`.

### Primary service: `oricli-engine`

- Toolchain (pre-installed): Go 1.25, Node 22, Python 3.12. The Go module requires Go >= 1.25.0.
- Build: `go build -o bin/oricli-engine ./cmd/oricli-engine` (the tracked `bin/oricli-engine` is a stale committed binary — rebuild before running; do not commit the rebuilt binary since `bin/` is gitignored).
- Run: `ORICLI_SEED_API_KEY=<token> ./bin/oricli-engine` — serves the OpenAI-compatible API on `:8089` (`ORICLI_ENGINE_PORT`). Since there is no TTY service manager, start it under `tmux` (or `&`), not systemd.
- Health (no auth): `curl http://127.0.0.1:8089/v1/health` → `{"status":"ready",...}`.
- Auth is optional in dev: `MAVAIA_REQUIRE_AUTH` defaults to `false`. `ORICLI_SEED_API_KEY` sets the owner Bearer token; if unset, a key is generated to `.oricli/api_key`.
- Runtime state (`.oricli/`, `.memory/`, `.memory/tasks.db`) is created under the cwd on boot and is untracked/gitignored — safe to leave.

### LLM backend is required for real chat output (non-obvious)

- `/v1/health` works with no LLM, but `POST /v1/chat/completions` needs a generation backend. Without one it returns a `dial tcp 127.0.0.1:11434: connect: connection refused` error.
- Ollama is **not** pre-installed and is intentionally **not** in the update script (system-level service, not a repo dependency). To get real chat responses locally: install Ollama (`curl -fsSL https://ollama.com/install.sh | sh` — the installer needs `zstd`, so `sudo apt-get install -y zstd` first), then run `ollama serve` (no systemd, so start it manually/tmux) and `ollama pull qwen3:0.6b`.
- Point the engine at the pulled model with `OLLAMA_MODEL=qwen3:0.6b` (the `GenerationService` default is otherwise `llama3.2:latest`). Alternatively, provide a cloud key instead of Ollama; note `pkg/oracle/oracle.go` checks `OPENAI_API_KEY` in `Available()` while batch/docs reference `ANTHROPIC_API_KEY`.
- On CPU-only VMs a tiny model like `qwen3:0.6b` keeps first-token latency reasonable (chat completions ~5-9s).

### Lint / test

- `go vet ./cmd/oricli-engine/...` reports a pre-existing "the cancel function returned by context.WithCancel should be called" warning in `main.go` (inside the opt-in `ORICLI_SWARM_ENABLED` block). It is not a build blocker; the binary builds and runs.
- Focused tests are fast and green, e.g. `go test ./pkg/oracle/... ./pkg/mindset/... ./pkg/coalition/...`. A full `go test ./...` covers 137+ packages and is slow — prefer focused runs.

### Optional client surfaces (not needed for API E2E)

- `ui_sovereignclaw/` — React 19 + Vite web client (ORI Studio): `npm install && npm run dev` (Vite `:5173`); set `VITE_API_BASE=http://localhost:8089`.
- `browserd/` — Node + Playwright browser-automation sidecar (`:7791`): `npm install && npx playwright install && npm run dev`.

### ori-capsule (dockerized BYOK secondary surface)

Working name for the slim Docker runtime living in `ori-capsule/` (extractable to its own GitHub repo via `git subtree split -P ori-capsule`).

- **Not** the VPS stack: no Curiosity/Dream/WorldTraveler/Metacog/Swarm/VDI daemons.
- **BYOK** inference: `X-Provider: openai|anthropic|opencode` + Bearer (or `ORI_CAPSULE_KEY` + `X-API-Key`). OpenCode = any OpenAI-compatible `X-Base-URL`.
- Run: `cd ori-capsule && docker compose up --build` → `:8089`. See `ori-capsule/README.md` and `MODULE_CUT.md` for the module-by-module port plan.
- Local binary: `cd ori-capsule && go run ./cmd/ori-capsule`.
- **Local BM25 RAG** (`ori-capsule/RAG.md`): `POST /v1/rag/ingest` + `/v1/rag/query`. Chat inject only with `X-Ori-RAG: bm25` — default chat path stays free of RAG. VPS MemoryBank/chromem/PB sync RAG is intentionally not ported.
