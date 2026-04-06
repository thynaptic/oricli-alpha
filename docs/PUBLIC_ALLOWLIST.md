# Public Allowlist

**Document Type:** Repo Governance  
**Status:** Active  
**Date:** 2026-04-06  

---

## Purpose

This document defines the code and docs surfaces that are considered publishable by default.

Use this together with:

- [IP_BOUNDARY.md](/home/mike/Mavaia/docs/IP_BOUNDARY.md)
- [IP_SURFACES.md](/home/mike/Mavaia/docs/IP_SURFACES.md)

Rule:

- if it is not on this allowlist, do not assume it is safe to publish
- if it is on this allowlist but later absorbs private logic, remove it from the allowlist

---

## Public-Default Namespaces

These are allowed by default.

### Runtime / entrypoints

- `cmd/`

Notes:

- Demo binaries may still expose internal concepts by name, but the directory itself is public-default.
- If a demo binary embeds private cognition behavior or private prompts, review it before publishing.

### CLI and transport

- `pkg/cli/`
- `pkg/core/http/`

These are platform plumbing, not crown-jewel cognition.

### Product shells and frontend surfaces

- `ui_sovereignclaw/`
- `ui_static/`
- `browserd/`

Notes:

- `browserd/.playwright/`
- `browserd/.state/`
- `browserd/node_modules/`
- `ui_sovereignclaw/node_modules/`

are not publication targets and should be treated as local/generated.

### Deployment and operator docs

- `scripts/`
- service unit files in repo root
- operational docs intended for deployment or product use

---

## Public Docs

These are safe to publish by default:

- `docs/API.md`
- `docs/PRODUCTS.md`
- `docs/ORI_DEV_DEPLOY.md`
- `docs/ORI_HOME_SPEC.md`
- `docs/CHANGELOG.md`
- `docs/SECURITY.md`
- `docs/public_overview.md`
- `docs/IP_BOUNDARY.md`
- `docs/IP_SURFACES.md`
- `docs/PUBLIC_ALLOWLIST.md`

These are also usually public:

- product overview docs
- deployment docs
- API reference docs
- changelogs
- product topology docs

Do **not** treat architecture docs as public by default unless explicitly listed here.

---

## Public Service-Layer Allowlist

The `pkg/service/` directory is mixed. Only the following files are public-default right now:

### Browser and tool runtime

- `pkg/service/browser_module.go`
- `pkg/service/browser_service.go`
- `pkg/service/browser_tools.go`
- `pkg/service/planner.go`
- `pkg/service/tool.go`

### Generic platform services

- `pkg/service/document.go`
- `pkg/service/document_ingestor.go`
- `pkg/service/documentation_generator.go`
- `pkg/service/project_understanding.go`
- `pkg/service/web.go`
- `pkg/service/web_ingestion.go`
- `pkg/service/searxng_searcher.go`
- `pkg/service/code_analyzer.go`
- `pkg/service/code_embeddings.go`
- `pkg/service/code_engine.go`
- `pkg/service/code_explanation.go`
- `pkg/service/code_memory.go`
- `pkg/service/code_metrics.go`
- `pkg/service/code_realtime.go`
- `pkg/service/code_review.go`
- `pkg/service/codebase_search.go`
- `pkg/service/image_gen_manager.go`
- `pkg/service/vision.go`
- `pkg/service/voice_engine.go`
- `pkg/service/research.go`
- `pkg/service/tool_forge_service.go`

### Likely public but still keep an eye on them

- `pkg/service/document.go`
- `pkg/service/rag.go`
- `pkg/service/registry.go`
- `pkg/service/orchestrator.go`

These can stay public as long as they do not start embedding private cognition or safety heuristics.

---

## Not Public By Default

Even if these are outside the obvious private namespaces, do not treat them as public automatically:

- `pkg/service/generation.go`
- `pkg/service/reasoning_*.go`
- `pkg/service/memory*.go`
- `pkg/service/emotional_inference.go`
- `pkg/service/meta_evaluator.go`
- `pkg/service/introspection.go`
- `pkg/service/subconscious.go`
- `pkg/service/precog.go`
- `pkg/service/semantic_understanding.go`
- `pkg/service/safety*.go`
- `pkg/service/tenant_constitution.go`
- `pkg/curator/`
- `pkg/oracle/`

These are either private-default or review-required under the IP boundary.

---

## Generated / Local-Only Surfaces

These are not publication targets:

- `node_modules/`
- `.playwright/`
- `.state/`
- temp snapshots and local logs
- generated static artifacts unless intentionally versioned

Examples:

- `browserd/.playwright/`
- `browserd/.state/`
- `ui_sovereignclaw/node_modules/`

---

## Fast Publish Rule

Before publishing a file, ask:

1. Is it inside a public-default namespace?
2. Is it named in the public service-layer allowlist if it lives under `pkg/service/`?
3. Does it avoid implementing cognition, safety, memory, model-policy, or regulation internals?

If any answer is `no`, stop and review it against:

- [IP_BOUNDARY.md](/home/mike/Mavaia/docs/IP_BOUNDARY.md)
- [IP_SURFACES.md](/home/mike/Mavaia/docs/IP_SURFACES.md)

---

## Immediate Working Set

For current cleanup, treat these as safely public:

- `cmd/`
- `pkg/cli/`
- `pkg/core/http/`
- `ui_sovereignclaw/`
- `ui_static/`
- `browserd/` source files
- deployment scripts and service files
- public docs listed above

Everything else should be assumed private or review-required until explicitly promoted into this allowlist.

