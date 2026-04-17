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

These all mean “go do the work”:

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

- [docs/README.md](/home/mike/Mavaia/docs/README.md)
- [docs/PRODUCTS.md](/home/mike/Mavaia/docs/PRODUCTS.md)
- [docs/ORI_CORE_ARCHITECTURE.md](/home/mike/Mavaia/docs/ORI_CORE_ARCHITECTURE.md)
- [docs/ORI_PROFILE_AND_SKILL_CURATION.md](/home/mike/Mavaia/docs/ORI_PROFILE_AND_SKILL_CURATION.md)
- [docs/API.md](/home/mike/Mavaia/docs/API.md)
- [docs/AGENT_API.md](/home/mike/Mavaia/docs/AGENT_API.md)
- [docs/SESSION_HANDOFF.md](/home/mike/Mavaia/docs/SESSION_HANDOFF.md)

### Product direction

Current public product truth:

- `ORI Studio` = flagship business product
- `ORI Home` = flagship personal product
- `ORI CRM` = planned
- `ORI Dev` = in development / builder lane
- `ORI Red` = incubating / not part of the main public story

### Architecture direction

Current architecture truth:

- one Ori
- many surfaces
- thin overlays
- profile-based working styles
- curated skill boundaries
- Oracle as the default strong reasoning lane
- local Ollama as utility/fallback, not the main product brain

Do not steer work back toward:

- all-local doctrine
- one separate personality per product
- raw internal skill exposure
- manifesto language as product explanation

---

## 3. Repo Shape

This repo is the shared ORI platform plus product clients.

Main places:

- [ui_sovereignclaw/](/home/mike/Mavaia/ui_sovereignclaw/) = ORI Studio web app
- [ORI-Home/](/home/mike/Mavaia/ORI-Home/) = ORI Home
- [products/ori-dev-web/](/home/mike/Mavaia/products/ori-dev-web/) = ORI Dev
- [vuln.ai/](/home/mike/Mavaia/vuln.ai/) = ORI Red
- [pkg/](/home/mike/Mavaia/pkg/) = shared Go runtime
- [cmd/backbone/](/home/mike/Mavaia/cmd/backbone/) = shared backbone entrypoint
- [ui_app.py](/home/mike/Mavaia/ui_app.py) = Studio UI/API shell still in active use
- [docs/](/home/mike/Mavaia/docs/) = current docs set

### Nested repo rule

These are nested repos:

- [ORI-Home/](/home/mike/Mavaia/ORI-Home/)
- [products/ori-dev-web/](/home/mike/Mavaia/products/ori-dev-web/)
- [vuln.ai/](/home/mike/Mavaia/vuln.ai/)

If the change belongs to that product client, work there intentionally.

Do not assume root `git status` tells the full story.

---

## 4. Runtime Truth

The live shared runtime is:

- Go backbone on `:8089`
- Studio shell/UI server on `:5001`
- public API at `https://glm.thynaptic.com/v1`

### Reasoning path

Current reality:

- `oricli-oracle` is the default public reasoning lane
- Oracle uses Copilot-backed models by surface
- local Ollama remains for utility/fallback work

RunPod is not part of the main ORI plan now.

See:

- [docs/RUNPOD_STATUS.md](/home/mike/Mavaia/docs/RUNPOD_STATUS.md)

### Services worth knowing

Common active services:

- `oricli-backbone.service`
- `oristudio-ui.service`
- `ori-dev-ui.service`
- `glm-api.service`
- `ollama.service`

Do not assume old services are still relevant just because a unit file exists.

---

## 5. How Agents Should Work Here

### Default pattern

1. Check current docs truth.
2. Inspect the live code path.
3. Make the smallest real change.
4. Build or resync.
5. Verify the actual surface.

### If working on Studio UI

After UI changes, run:

```bash
./scripts/resync_ui.sh
```

### If working on the Go runtime

Prefer verifying with:

```bash
go test ./pkg/oracle ./pkg/api/...
```

or a narrower target when appropriate.

### If touching product positioning or docs

Check:

- public website source
- Studio site source
- docs source-of-truth set

Do not assume those are the same thing.

We already hit this exact issue with `thynaptic.com` vs `oristudio.thynaptic.com`.

---

## 6. Product/UX Guardrails

### Studio

Studio should feel like:

`ORI knows my business and helps me run it.`

Not:

- an AI playground
- an internal tool console
- a product lineup site
- a generic workflow lab

### Home

Home should feel:

- calm
- present
- useful
- personal, not theatrical

### Dev

Dev should be treated as a builder lane, not automatically as a flagship product.

### Red

Red remains real in architecture, but should not drive the main company story right now.

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

See:

- [docs/SKILLS.md](/home/mike/Mavaia/docs/SKILLS.md)
- [docs/ORI_PROFILE_AND_SKILL_CURATION.md](/home/mike/Mavaia/docs/ORI_PROFILE_AND_SKILL_CURATION.md)

---

## 8. Docs Rule

The docs folder contains multiple eras.

Before trusting any doc, decide:

- source of truth
- active supporting doc
- historical reference
- stale/archive candidate

If exporting docs to NotebookLM later, use:

- [docs/NOTEBOOKLM_EXPORT.md](/home/mike/Mavaia/docs/NOTEBOOKLM_EXPORT.md)

This onboarding file is not part of that export set.

---

## 9. What To Challenge

Challenge these when you see them:

- outdated “sovereign” marketing language on customer-facing surfaces
- local-model assumptions being treated as strategy instead of legacy
- product pages leaking between company site and Studio site
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
