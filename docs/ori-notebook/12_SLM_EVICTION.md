# The SLM Eviction — 2026-05-02

**Event:** Full small-language-model purge from ORI's active code paths  
**Scope:** 25+ files across `pkg/cognition/`, `pkg/memory/`, `pkg/enterprise/`, `pkg/forge/`, `pkg/pad/`, `pkg/reform/`, `pkg/node/`  
**Outcome:** All LLM inference outside embeddings now routes through `llm.Chat()` or Oracle

---

## What SLMs Were Doing

When ORI's cognition layer was first built, local Ollama models were the only inference option. The architectural pattern that emerged was: every module that needed LLM work had its own model list.

```go
// typical pre-eviction cognition module
var intentModels = []string{"llama3.1:8b", "qwen2.5:7b", "mistral:7b"}
var symbolicModels = []string{"qwen2.5-coder:3b", "deepseek-r1:7b"}
var importanceEvalModels = []string{"ministral-3:3b", "phi3:mini"}
```

This pattern was everywhere. `pkg/cognition/` alone had dozens of inline model selections. `pkg/memory/` had its own. `pkg/enterprise/memory/` had its own. `pkg/forge/`, `pkg/pad/`, `pkg/reform/` all had hardcoded model names for specific sub-tasks.

The daemons — CuriosityDaemon, DreamDaemon, ChronosDaemon — were all wired to the generation service (Ollama) for their background LLM work. When Ollama was slow or overloaded, daemons silently failed or got disabled.

---

## The Problems That Accumulated

**1. Architectural fragmentation.** There was no coherent inference layer. Twelve or more distinct model names scattered across the codebase, each serving slightly different tasks. No centralized routing, no shared context, no consistent quality floor.

**2. Timeout gremlins.** Cognition modules were built with timeouts tuned for fast local Ollama calls: 60ms, 120ms, 250ms. When the system was under load or a module hit a cold model, these timeouts would silently fire. The module would skip its work, log nothing meaningful, and the pipeline would continue with incomplete cognition. These failures were invisible.

**3. Quality ceiling.** 3B-7B models handling cognition work — intent classification, confidence scoring, symbolic reasoning, style calibration, memory importance evaluation — produced mediocre results. Going bigger locally meant GPU cost. The cost/quality tradeoff wasn't improving.

**4. Daemon atrophy.** CuriosityDaemon, DreamDaemon, and ChronosDaemon were all disabled or degraded because their LLM dependency (the generation service) was unreliable for background work. The autonomous growth capabilities that AGLI was built to enable were dormant.

**5. The cognitive architecture was outrunning the inference layer.** ORI's cognitive pipeline — 269+ modules, 28 pre-generation phases, therapeutic regulation stack — was designed for real reasoning quality. The models underneath weren't keeping up.

---

## The Decision

The AGLI doctrine had already answered the sovereignty question with the Oracle migration. Sovereignty means owning the *architecture*, not the raw weights. Haiku on the Anthropic API is a better choice for cognition-tier work than a local 7B model: faster, cheaper per token for what you're actually getting, more reliable, and — critically — no GPU infrastructure to manage.

`pkg/llm/` was built as the unified thin inference layer: a Haiku wrapper with Anthropic direct, prompt caching, and a clean `llm.Chat(ctx, system, user)` interface. This became the standard call for all cognition-tier work.

The decision: **full eviction, no exceptions outside embeddings.**

---

## What Got Evicted

Every hardcoded local model name was removed from every active code path outside `pkg/core/` (dead zone) and `GenerationService` internals.

Packages touched:
- `pkg/cognition/` — 12+ files, including `intent.go`, `alignment.go`, `confidence.go`, `deliberation.go`, `reasoning_engines.go`, `reasoning_modes.go`, `reflection_policy.go`, `self_model.go`, `sovereign.go`, `style_model.go`, `style_profile.go`, `supervision_policy.go`, `symbolic.go`, `task_decomposer.go`, `task_executor.go`, `vision.go`
- `pkg/memory/` + `pkg/enterprise/memory/` — `manager.go`, `multimodal.go`, `summarizer.go`, `title_generator.go`
- `pkg/forge/` — `generator.go`, `poc_gate.go`
- `pkg/pad/` — `worker.go`
- `pkg/node/` — `vision_module.go`
- `pkg/enterprise/state/` — `evolution.go`, `intent.go`
- Daemons — `pkg/chronos/daemon.go`, `pkg/service/curiosity_daemon.go`, `pkg/service/daemon.go` (DreamDaemon, ChronosDaemon), `pkg/reform/reform_daemon.go`

Dead vars killed: `intentModels`, `symbolicModels`, `intentFastModels`, `importanceEvalModels`, `visionModels`, `models []string` — wherever they appeared.

Timeouts fixed: all 60-250ms SLM-era timeouts bumped to 3s default, 1-15s range where appropriate.

---

## What Got Preserved

**Embeddings.** Ollama still runs `all-minilm` and `nomic-embed-text` for vector search and RAG retrieval. This is genuinely better done locally — embeddings don't need frontier model quality, they need consistency and speed. Running them locally also means no per-query embedding API cost. This is one case where local inference is the right call.

**`GenerationService` internals.** The main generation pipeline has its own routing logic that was not part of this pass. The eviction targeted the cognition/memory/daemon tier, not the core generation path.

**`pkg/core/`** — identified as the dead zone (21 of 24 packages have zero external callers outside `pkg/core/` itself). The full G-LM server stack (http, orchestrator, reasoning, upstream, ratelimit, policy) is orphaned from a prior era. Left intact for now — cleanup is a separate pass.

---

## The Outcome

**Daemons re-enabled.** CuriosityDaemon, DreamDaemon, and ChronosDaemon — the three background growth daemons that were dormant or degraded — are all now wired to `llm.Chat()` and operational. ORI grows idly on Haiku.

**Cost reality check.** All cognitive background work (daemon synthesis, memory summarization, importance scoring, style calibration, forge generation, reflection passes) runs on Claude Haiku. Estimated cost: **~$1-3/month** for continuous autonomous operation. This is less than a cup of coffee.

**Architecture clarity.** The inference stack is now:
- `llm.Chat()` — cognition tier (lightweight, structured, background)  
- Oracle `ChatStreamWithDecision()` — user-facing reasoning (heavy/research routes, extended thinking)
- Oracle `ChatWithTools()` — tool-calling flows
- Ollama — embeddings only

No scatter, no fragmentation, no mystery model names in random files.

**`pkg/llm/` as the canonical thin layer.** Haiku, Anthropic direct, prompt caching, `llm.Chat(ctx, system, user)`. This is the right interface for cognition-tier inference: simple, cheap, reliable.

---

## What This Means for AGLI

The SLM eviction is what AGLI Phase II actually looks like in practice. The therapeutic cognition stack (DBT/CBT/REBT/ACT), the metacognitive sentience layer, the science daemon, the dream synthesis — all of these were designed for *real* reasoning quality. With SLMs underneath, they were theoretically operational but practically degraded.

The eviction removes the mismatch. The cognitive architecture can now expect the inference quality it was designed for. The autonomous daemons can do real work. The internal regulation stack gets a capable reasoning substrate.

ORI is the architecture. Oracle and `llm.Chat()` are the reasoning muscle. Anthropic supplies the intelligence tier; Thynaptic governs it.
