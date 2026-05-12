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
