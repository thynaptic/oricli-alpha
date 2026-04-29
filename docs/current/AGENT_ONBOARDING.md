# Agent Onboarding

For any agent dropped into this repo.

Read this first.

This file is not for NotebookLM export.

It is the practical guide for working with Mike and with the current ORI stack as it actually exists now.

---

## 1. How To Work With Mike

Mike is fast, direct, product-driven, and system-minded.

He will often describe a direction, not a spec.

Your job is to:

1. understand the real goal
2. check the current code and product truth
3. make the smallest clean set of changes that moves it forward
4. verify it
5. report back plainly

### Communication style

- Direct is good.
- Banter is fine.
- Substance matters more than polish.
- If something is wrong, say it plainly.
- If a direction is sound, move.

### What green lights look like

These all mean "go do the work":

- `yeah`
- `agreed`
- `lets do that`
- `go ahead bro`
- `yep`

### What not to do

- Do not pad with cheerleading.
- Do not ask a stack of clarifying questions.
- Do not leave a half-finished pass if you can finish it.
- Do not preserve outdated architecture just because it used to matter.
- Do not create repo-planning clutter unless the task truly needs a durable doc.

---

## 2. Current ORI Truth

Do not infer current truth from old names alone.

Use these docs first:

- `CLAUDE.md` (repo root) — canonical layout, service map, env vars
- `docs/api/API.md` — full API reference
- `docs/api/AGENT_API.md` — agent-optimized API reference
- `docs/current/CHANGELOG.md` — recent changes
- `dev-portal/llms.txt` — machine-readable agent integration guide

### Product direction

Current public product truth:

- `ORI Studio` = flagship business product (live at `demo.thynaptic.com`)
- `ORI Home` = desktop companion app (Mac + Windows)
- `ORI Dev` = builder lane / developer surface
- `ORI Code` = terminal coding agent (Bun + Ink + TUI)
- `Mise by ORI` = mobile culinary platform (`misebyori.com`)
- `ORI Stone` = Hearthstone desktop overlay

### Architecture direction

Current architecture truth:

- one Ori, many surfaces
- thin overlays, profile-based working styles
- Oracle is the only reasoning lane — all LLM calls go through Oracle
- Ollama serves embeddings only (`all-minilm`, `nomic-embed-text`) — not a reasoning fallback
- SCAI Critique/Revise SLM loop is retired — `SelfAlign()` runs structural AuditOutput only

Do not steer work back toward:

- all-local doctrine
- SLM-backed reasoning or SCAI SLM critique passes
- one separate personality per product
- raw internal skill exposure
- manifesto language as product explanation

---

## 3. Repo Shape

The primary binary is `cmd/oricli-engine/` → builds to `bin/oricli-go-v2`.

Main places:

- `pkg/` — shared Go runtime (api, oracle, cognition, service, etc.)
- `cmd/oricli-engine/` — primary production binary
- `cmd/oricli-cli/` — TUI/CLI client
- `oricli_core/skills/` — `.ori` skill files
- `.github/agents/` — agent persona files (loaded as system prompts via Anthropic API)
- `dev-portal/` — machine-readable manifests for agent integrations
- `docs/` — documentation

Product surfaces live at `/home/mike/thynaptic/` (separate from this repo):

- `thynaptic/web/` — thynaptic.com marketing site
- `thynaptic/ori-home/` — ORI Home desktop app (Electron)
- `thynaptic/ori-code/` — ORI Code terminal agent
- `thynaptic/ori-stone/` — ORI Stone Hearthstone overlay
- `thynaptic/mise/` — Mise by ORI web app
- `thynaptic/registry.yaml` — canonical product catalog

Do not assume root `git status` in Mavaia reflects product surface changes.

---

## 4. Runtime Truth

The live shared runtime is:

- Go backbone on `:8089` (public API, auth enforced)
- Go backbone on `:8088` (internal cognitive backbone, localhost only)
- Public API at `https://glm.thynaptic.com/v1`
- Oracle calls Anthropic API directly (no daemon, no port 8090)

### Reasoning path

Current reality:

- `oricli-oracle` is the default public reasoning lane
- Oracle routes to 4 tiers: `RouteLightChat`, `RouteHeavyReasoning`, `RouteResearch`, `RouteImageReasoning`
- Ollama is embeddings-only — `all-minilm` + `nomic-embed-text` (used by `pkg/service/embedder.go` for memory recall, response cache dedup, SCL indexing, TCD drift)
- All LLM reasoning, vision, and generation routes through Oracle — not Ollama

RunPod is not part of the main ORI plan now.

### Services worth knowing

```
oricli-api.service       — primary engine (:8089)
oricli-backbone.service  — cognitive backbone (:8088)
oristudio-ui.service     — ORI Studio UI
ori-dev-ui.service       — ORI Dev UI
oricli-teams.service     — Teams bot (:3979)
ollama.service           — embeddings only
```

Do not assume old services are still relevant just because a unit file exists.

---

## 5. How Agents Should Work Here

### Default pattern

1. Check current docs truth (CLAUDE.md, CHANGELOG).
2. Inspect the live code path.
3. Make the smallest real change.
4. Build: `go build -o bin/oricli-go-v2 ./cmd/oricli-engine/`
5. Restart: `sudo systemctl restart oricli-api.service oricli-backbone.service`
6. Verify the actual surface.

### If working on the Go runtime

Build and check:

```bash
go build ./pkg/...
go build ./cmd/oricli-engine/
```

### If touching product positioning or docs

Check:

- `thynaptic/web/src/` — thynaptic.com marketing site source
- `dev-portal/llms.txt` — agent-facing API truth (keep in sync with server_v2.go routes)
- `docs/current/CHANGELOG.md` — add an entry

Do not assume marketing site and API docs say the same thing — they often diverge.

---

## 6. Product/UX Guardrails

### Studio

Studio should feel like:

`ORI knows my business and helps me run it.`

Not: an AI playground, an internal tool console, or a generic workflow lab.

### Home

Home should feel: calm, present, useful, personal — not theatrical. Think Claude Desktop equivalent for ORI.

### Dev

Dev should be treated as a builder lane, not automatically as a flagship product.

---

## 7. Skills, Profiles, And Surfaces

Current rule:

- users see working styles
- surfaces define product context
- profiles define lanes
- skills do the actual underneath work

Do not expose raw skills unless that exposure is intentional.

Protected/private lanes must stay protected:

- `digital_guardian`
- `jarvis_ops`

Those belong to the `princess-puppy-os` world, not general ORI product curation.

---

## 8. Docs Rule

The docs folder contains multiple eras.

Before trusting any doc, decide:

- source of truth → `CLAUDE.md`, `docs/current/`, `dev-portal/llms.txt`
- active supporting doc → `docs/architecture/`, `docs/api/`
- historical reference → `docs/ori-notebook/`, `docs/archive/`
- stale/archive candidate → anything referencing `ori:1.7b`, `qwen3:1.7b`, `moondream`, `SCAI SLM`, RunPod as active

This onboarding file is not part of the NotebookLM export set.

---

## 9. What To Challenge

Challenge these when you see them:

- outdated "sovereign" marketing language on customer-facing surfaces
- local-model assumptions being treated as strategy instead of legacy
- SCAI SLM Critique/Revise referenced as active (it's retired — pure structural scan now)
- product pages leaking between thynaptic.com and Studio site
- raw skills or internal lanes showing up in public UI
- old docs silently acting canonical
- builder/admin vocabulary leaking into SMB-facing surfaces

---

## 10. Good Next Moves

When in doubt, prefer work that does one of these:

- makes the product story clearer
- makes ORI feel more consistent across surfaces
- removes old architecture drift
- tightens public-facing truth
- makes agent → ORI integration cleaner

That has been the winning direction.

---

## 11. One-Line Summary

Help Mike move ORI toward:

`one Ori, many surfaces, clean product truth, Oracle-first quality, and no unnecessary old baggage.`

*Last updated: 2026-04-21 — v11.9.0 (Oracle-only reasoning, embeddings-only Ollama, SCAI structural-only)*
