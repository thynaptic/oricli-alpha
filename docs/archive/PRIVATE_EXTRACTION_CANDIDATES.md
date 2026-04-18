# Private Extraction Candidates

**Document Type:** Repo Governance  
**Status:** Draft  
**Date:** 2026-04-06  

---

## Purpose

This document turns the IP governance policy into an actionable extraction list.

It answers:

- what should eventually move out of the public repo
- what can stay public
- what should be reviewed before any move

Use this with:

- [IP_BOUNDARY.md](/home/mike/Mavaia/docs/IP_BOUNDARY.md)
- [IP_SURFACES.md](/home/mike/Mavaia/docs/IP_SURFACES.md)
- [PUBLIC_ALLOWLIST.md](/home/mike/Mavaia/docs/PUBLIC_ALLOWLIST.md)
- [SERVICE_SURFACES.md](/home/mike/Mavaia/docs/SERVICE_SURFACES.md)
- [EDGE_SURFACES.md](/home/mike/Mavaia/docs/EDGE_SURFACES.md)

---

## Extraction Priorities

### Priority 1 — obvious crown-jewel namespaces

These are the clearest private candidates and should eventually live behind a private/internal boundary.

- `pkg/cognition/`
- `pkg/therapy/`
- `pkg/core/reasoning/`
- `pkg/core/metareasoning/`
- `pkg/safety/`

Why:

- they directly implement reasoning, cognition, regulation, metareasoning, and safety-control logic
- they are repeatedly documented by the private-signal docs
- they are exactly the kind of code major labs would not publish in full

---

### Priority 2 — private packages outside the obvious namespaces

- `pkg/curator/`
- `pkg/oracle/`

Why:

- model ranking, recommendation, and escalation policy are internal decision logic
- they materially teach how ORI selects models or bypasses local inference

---

### Priority 3 — private service-layer files

These should not stay in a public mixed `pkg/service/` forever.

#### Reasoning and cognition execution

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

#### Memory and internal state

- `pkg/service/memory.go`
- `pkg/service/memory_bank.go`
- `pkg/service/memory_graph.go`
- `pkg/service/memory_pipeline.go`
- `pkg/service/state_memory_tools.go`
- `pkg/service/code_memory.go`
- `pkg/service/graph.go`

#### Safety and control logic

- `pkg/service/safety.go`
- `pkg/service/safety_code.go`
- `pkg/service/safety_pro.go`
- `pkg/service/safety_step.go`
- `pkg/service/holistic_safety.go`
- `pkg/service/security_analysis.go`
- `pkg/service/tenant_constitution.go`
- `pkg/service/living_constitution.go`
- `pkg/service/sentinel.go`

#### Internal orchestration

- `pkg/service/agent.go`
- `pkg/service/agent_pipeline.go`
- `pkg/service/multi_agent_pipeline.go`
- `pkg/service/coordinator.go`
- `pkg/service/orchestrator.go`
- `pkg/service/swarm_agents.go`
- `pkg/service/swarm_consensus.go`

Why:

- these are private by behavior even though they live under a generic service package

---

## Can Stay Public

These are good candidates to remain in the public repo:

- `cmd/`
- `pkg/cli/`
- `pkg/core/http/`
- `browserd/` source
- `ui_sovereignclaw/`
- `ui_static/`
- deployment scripts and service files
- browser/runtime/tooling services already allowlisted in [PUBLIC_ALLOWLIST.md](/home/mike/Mavaia/docs/PUBLIC_ALLOWLIST.md)

---

## Review Before Any Move

These are mixed and should not be moved blindly:

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
- demo binaries under `cmd/`
- `docs/EXTERNAL_INTEGRATION.md`

Why:

- some may be generic enough to stay public
- some may be thin wrappers over private systems
- some may need partial splitting rather than a simple move

---

## Suggested Migration Shape

Do not do a giant move all at once.

Use phases:

1. **Policy complete**
   - already done via the governance docs

2. **Fence the private set**
   - stop committing private-default changes casually
   - tag or track them as internal/IP surfaces

3. **Create a private module/repo boundary**
   - move priority 1 and 2 first
   - leave public entrypoints and product shells where they are

4. **Split mixed service surfaces**
   - extract private service-layer files into internal packages
   - leave public wrappers/interfaces in place where necessary

5. **Review the mixed remainder**
   - only then decide whether review-required files belong public or private

---

## Immediate Working Rule

For now:

- Priority 1, 2, and 3 items should be treated as private even if they still physically live here
- do not publish or casually modify them in public-facing cleanup
- public work should stay inside the allowlisted surfaces unless deliberately expanded

