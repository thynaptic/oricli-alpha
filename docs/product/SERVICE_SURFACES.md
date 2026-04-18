# Service Surfaces Classification

**Document Type:** Repo Governance  
**Status:** Active  
**Date:** 2026-04-06  

---

## Purpose

`pkg/service/` is a mixed layer.

Some files are generic platform plumbing and safe to publish.
Some are direct implementations of private cognition, memory, safety, or orchestration systems.
This document classifies the service layer accordingly.

Use this with:

- [IP_BOUNDARY.md](/home/mike/Mavaia/docs/IP_BOUNDARY.md)
- [IP_SURFACES.md](/home/mike/Mavaia/docs/IP_SURFACES.md)
- [PUBLIC_ALLOWLIST.md](/home/mike/Mavaia/docs/PUBLIC_ALLOWLIST.md)

---

## Private-Default Service Surfaces

These are not publishable by default.

### Reasoning and cognition execution

- `pkg/service/generation.go`
- `pkg/service/generation_wrappers.go`
- `pkg/service/reasoning_cot.go`
- `pkg/service/reasoning_mcts.go`
- `pkg/service/reasoning_orchestrator.go`
- `pkg/service/reasoning_strategies.go`
- `pkg/service/reasoning_tot.go`
- `pkg/service/refactoring_reasoning.go`
- `pkg/service/complexity.go`
- `pkg/service/complexity_router.go`
- `pkg/service/instruction_following.go`
- `pkg/service/semantic_understanding.go`
- `pkg/service/emotional_inference.go`
- `pkg/service/introspection.go`
- `pkg/service/meta_evaluator.go`
- `pkg/service/subconscious.go`
- `pkg/service/precog.go`
- `pkg/service/learning_system.go`
- `pkg/service/thought_to_text.go`

### Memory and internal state

- `pkg/service/memory.go`
- `pkg/service/memory_bank.go`
- `pkg/service/memory_graph.go`
- `pkg/service/memory_pipeline.go`
- `pkg/service/state_memory_tools.go`
- `pkg/service/code_memory.go`
- `pkg/service/graph.go`

### Safety and control logic

- `pkg/service/safety.go`
- `pkg/service/safety_code.go`
- `pkg/service/safety_pro.go`
- `pkg/service/safety_step.go`
- `pkg/service/holistic_safety.go`
- `pkg/service/security_analysis.go`
- `pkg/service/tenant_constitution.go`
- `pkg/service/living_constitution.go`
- `pkg/service/sentinel.go`

### Swarm / internal orchestration

- `pkg/service/swarm_agents.go`
- `pkg/service/swarm_consensus.go`
- `pkg/service/agent.go`
- `pkg/service/agent_pipeline.go`
- `pkg/service/multi_agent_pipeline.go`
- `pkg/service/coordinator.go`
- `pkg/service/orchestrator.go`

### Why these are private-default

These files are directly tied to docs and systems covering:

- reasoning internals
- memory architecture
- therapeutic regulation
- epistemic hygiene
- internal safety and sovereignty policy
- self-model and orchestration behavior

If DeepMind or Anthropic would not publish the logic, neither do we.

---

## Public-Default Service Surfaces

These are safe to publish by default.

### Browser and tool runtime

- `pkg/service/browser_module.go`
- `pkg/service/browser_service.go`
- `pkg/service/browser_tools.go`
- `pkg/service/planner.go`
- `pkg/service/tool.go`
- `pkg/service/tool_forge_service.go`

### Generic product and document/web services

- `pkg/service/document.go`
- `pkg/service/document_ingestor.go`
- `pkg/service/documentation_generator.go`
- `pkg/service/project_understanding.go`
- `pkg/service/web.go`
- `pkg/service/web_ingestion.go`
- `pkg/service/searxng_searcher.go`
- `pkg/service/colly_scraper.go`

### Generic code tooling

- `pkg/service/code_analyzer.go`
- `pkg/service/code_embeddings.go`
- `pkg/service/code_engine.go`
- `pkg/service/code_explanation.go`
- `pkg/service/code_metrics.go`
- `pkg/service/code_realtime.go`
- `pkg/service/code_review.go`
- `pkg/service/codebase_search.go`

### Media and interface services

- `pkg/service/image_gen_manager.go`
- `pkg/service/vision.go`
- `pkg/service/voice_engine.go`

### Why these are public-default

These files primarily implement:

- browser execution
- tool discovery and execution
- document/web ingestion
- code analysis and explanation
- product-facing infrastructure

They do not define crown-jewel cognition or safety behavior by themselves.

---

## Review-Required Service Surfaces

These need an explicit call before publishing.

- `pkg/service/rag.go`
- `pkg/service/registry.go`
- `pkg/service/research.go`
- `pkg/service/rules.go`
- `pkg/service/sandbox.go`
- `pkg/service/availability.go`
- `pkg/service/budget.go`
- `pkg/service/identity_seed.go`
- `pkg/service/profile.go`
- `pkg/service/persona.go`
- `pkg/service/skills.go`
- `pkg/service/world_knowledge.go`
- `pkg/service/world_traveler.go`
- `pkg/service/intent.go`
- `pkg/service/classifier.go`
- `pkg/service/monitor.go`
- `pkg/service/metrics.go`
- `pkg/service/daemon.go`

### Why these are review-required

These files may be:

- generic platform code
- partially public abstractions
- or thin wrappers around private behavior

They are not private by obvious namespace alone, but they are close enough to policy, routing, or internal system behavior that they should not be published casually.

---

## Immediate Working Rule

When touching `pkg/service/`:

1. If the file is listed under private-default here, do not publish it by default.
2. If the file is listed under public-default here, it can ship unless it absorbs private logic later.
3. If the file is listed under review-required here, decide deliberately before publishing.
4. If a file is not listed at all, treat it as review-required until classified.

