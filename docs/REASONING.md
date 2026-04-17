# Reasoning

Status: active supporting doc

This file describes ORI's current reasoning direction at a product and runtime level.

It is not a promise that every historical reasoning subsystem listed in older docs is still the primary path for current user-visible chat.

Use this doc to answer:

- what ORI treats as the real intelligence layer
- what Oracle vs local models are for
- how reasoning relates to profiles, skills, routing, and surfaces
- how to interpret older reasoning docs that still exist in the repo

## Current Truth

Ori is not the model.

Ori is the system that:

- holds identity
- keeps memory
- routes work
- applies skills and profiles
- chooses tools
- enforces permissions
- shapes the final user experience

Reasoning backends sit underneath that system.

Right now, the practical direction is:

- Oracle is the default reasoning lane for user-visible quality
- local small models are utility workers, not the main brain
- surface overlays and profiles shape behavior before any model produces the final answer

This matches:

- [ORI_CORE_ARCHITECTURE.md](/home/mike/Mavaia/docs/ORI_CORE_ARCHITECTURE.md)
- [ORI_PROFILE_AND_SKILL_CURATION.md](/home/mike/Mavaia/docs/ORI_PROFILE_AND_SKILL_CURATION.md)

## Reasoning Stack Today

### 1. ORI Core

This is the real top layer.

It owns:

- persona baseline
- session context
- memory and identity
- routing policy
- profile and skill loading
- tool permissions
- quality and safety defaults

This is what keeps Ori feeling like Ori even when model choices change.

### 2. Surface Overlays

Each product gets a thin reasoning context layer:

- Studio
- Home
- Dev
- Red

The overlay decides:

- what matters on this surface
- what vocabulary is allowed
- what skills are allowed
- what should stay hidden

### 3. Profiles And Skills

Profiles are the user-facing working styles.

Skills are the narrower behavioral lanes attached underneath.

Current rule:

- users should usually choose a working style, not a raw skill
- strict profiles can suppress unrelated trigger-matched skills
- surface overlays can block skills even if they exist globally

### 4. Reasoning Backends

Backends supply compute. They do not define Ori's identity.

Current direction:

- Oracle handles substantive reasoning
- local models handle wake, utility, extraction, and fallback

## Oracle vs Local

### Oracle

Use Oracle for:

- substantive chat
- planning
- writing
- analysis
- business reasoning
- workspace/system design
- anything user-visible where quality matters

### Local small models

Use local only when they clearly win:

- wake and warm paths
- lightweight classification
- extraction
- simple transforms
- offline fallback
- low-value internal utility tasks

Do not treat small local models as the main product intelligence unless the quality bar clearly holds.

## How Routing Should Be Read

Older docs describe a very detailed reasoning stack with many modes:

- MCTS*
- ToT
- CoT
- PAL
- Self-Consistency
- ReAct
- Debate
- Causal reasoning
- SELF-DISCOVER
- and others

Those are useful as implementation/reference concepts, but they are not the same thing as today's product-facing reasoning story.

The current product-facing rule is simpler:

1. Ori Core sets identity and policy
2. surface overlay narrows behavior
3. active profile selects the working lane
4. allowed skills attach emphasis
5. Oracle or local compute executes the turn

That is the lens future work should follow.

## Historical / Deeper Reasoning Methods

The repo still contains deeper reasoning systems and references, including:

- adaptive reasoning logic
- structured search
- decomposition
- debate
- planning
- retrieval and memory grounding
- verification and audit layers

Relevant implementation paths still include:

- `pkg/cognition/`
- `pkg/core/reasoning/`
- `pkg/core/metareasoning/`
- `pkg/service/reasoning_*`

Useful supporting docs:

- [MCTS_REASONING.md](/home/mike/Mavaia/docs/MCTS_REASONING.md)
- [MEMORY_ARCHITECTURE.md](/home/mike/Mavaia/docs/MEMORY_ARCHITECTURE.md)
- [EPISTEMIC_HYGIENE.md](/home/mike/Mavaia/docs/EPISTEMIC_HYGIENE.md)

But these should be read as deeper implementation/reference material, not as the first explanation of how ORI thinks today.

## About The `*` Mark

Some older reasoning docs and notes use an asterisk `*` to mark methods inspired by external research lines or system families rather than copied implementations.

That meaning should stay intact.

In this repo, `*` should be read as:

- inspired by a known research/system lineage
- implemented in ORI's own stack and adapted to ORI's needs
- not a claim of one-to-one parity with the source system

That distinction matters and should not be lost in rewrites.

## Product Rule

Do not let reasoning docs pull the product back into a model-centric story.

The current thesis is:

- Ori is the system
- models are replaceable compute
- overlays, profiles, skills, memory, and routing shape the result
- product quality matters more than preserving an all-local ideal

If a future doc still implies that the model alone is the brain, it needs review.

## Current Direction

Use this as the practical default:

- Oracle-first for user-visible reasoning quality
- local models for utility and fallback
- surface overlays to keep products distinct
- curated profiles and skills instead of raw inventory exposure
- older deep-reasoning systems treated as supporting implementation reference unless actively re-promoted
