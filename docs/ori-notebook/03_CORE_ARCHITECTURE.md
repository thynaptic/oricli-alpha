# ORI Core Architecture

This is the product-level architecture direction for ORI across Studio, Home, Dev, Red, CRM, and future surfaces.

The goal is simple:

`One Ori, many surfaces.`

Not:

- one giant prompt per product
- one separate personality per app
- one local model carrying the whole system

## Core Thesis

Ori is not the model.

Ori is the system that:

- holds identity
- keeps memory
- routes work
- chooses tools
- applies permissions
- carries tone
- delivers the final experience

Models are replaceable reasoning backends underneath her.

That means:

- ORI stays consistent
- products can expand without rebuilding the brain
- model swaps do not break the brand
- local inference is optional, not existential

## Architecture Shape

### 1. ORI Core

This layer should be global across products.

It owns:

- baseline persona
- memory and identity seeding
- active scratchpad / tactical workspace state
- routing policy
- tool permissions
- skill/profile loading
- user/session context
- response style defaults
- quality and safety rules

This is the real brain.

### 2. Reasoning Backends

This layer should be swappable.

It includes:

- Oracle for high-quality reasoning
- small local models for cheap utility work
- future specialist backends only when clearly justified

Backends should not define the product personality.

They should only supply compute.

### 3. Surface Overlays

Each product gets a light overlay, not a new identity.

Examples:

- `ORI Studio`
  - SMB operator surface
  - jobs, desk, notes, approvals, follow-through

- `ORI Home`
  - personal/home companion surface
  - household, reminders, family coordination, ambient help

- `ORI Dev`
  - technical builder/operator surface
  - code, product shaping, repo work, systems thinking

- `ORI Red`
  - security and assurance surface
  - audits, findings, remediation guidance, technical validation

- `ORI CRM` (planned)
  - sales operator surface
  - follow-up, closing support, objection handling, pitch and script generation
  - not a full CRM replacement platform

Each overlay should define:

- what matters here
- what tone adjustments are allowed
- what tools are available
- what should be hidden

It should not redefine Ori from scratch.

## What Belongs Globally

Keep these in the core:

- calm, precise, quietly in control baseline
- concise answer-first behavior
- memory system
- session handling
- tool routing
- identity and trust rules
- general safety and privacy constraints
- default quality bar

## What Belongs Per Product

Keep these in thin overlays:

- vocabulary
- UI-specific behavior
- product-specific permissions
- product-specific goals
- product-specific tool subsets
- user-facing examples and expectations

Examples:

- Studio says `Jobs`
- Home says `Plans`, `Reminders`, or `What should we handle`
- Dev allows repo/file/system language that Studio should never expose
- CRM should say `Follow-up`, `Closing`, `Accounts`, or `Next touch`

## Routing Direction

Use the right intelligence source for the job.

### Oracle default

Use Oracle for:

- substantive chat
- planning
- writing
- analysis
- business reasoning
- workspace/system design
- anything user-visible where quality matters

### Local small-model utility

Use small local models only when they clearly win.

Good uses:

- wake/warm path
- cheap classification
- extraction
- lightweight transforms
- offline fallback
- low-value internal utility tasks

Bad uses:

- primary product intelligence
- important drafting
- nuanced reasoning
- premium demos
- user trust-critical conversations

## Product Rule

Do not let any single model define ORI.

If a model is slow, dumb, overfit, or replaced, Ori should still feel like Ori because the system stays stable above it.

## Current Direction

This is the direction to continue from current reality:

- Studio should be Oracle-first for substantive reasoning
- Studio may keep a local lane for explicit fast/on-box use
- Home should likely follow the same pattern
- Dev can keep more explicit model and tool control where needed
- Red should stay evidence-first and tool-bounded, with security-specific skills allowed explicitly rather than inherited accidentally
- CRM should stay email-first and sales-focused, without drifting into a full CRM platform

## What We Need To Do To Start It

### 1. Lock the core persona

Create and maintain one true Ori baseline.

Needs:

- one canonical core persona file or builder source
- one source of truth for identity seeding
- one source of truth for tone rules

Current status:

- partly done
- still needs clearer centralization

### 2. Define surface overlays

Create thin overlays for:

- Studio
- Home
- Dev
- Red
- CRM (planned)

Each overlay should answer:

- what is this surface for?
- what tools are allowed?
- what tone shift is allowed?
- what should be hidden?

### 3. Make routing explicit

Do not rely on accidental defaults.

We need:

- a clear default reasoning backend per surface
- explicit local fallback rules
- clear rules for when Oracle is required

### 4. Separate utility models from user-facing intelligence

Small local models should be treated as helpers, not the main act.

We need:

- a named utility lane
- a named premium reasoning lane
- no user-facing language that treats raw local model IDs as product choices

### 5. Unify configuration names

We should move toward product language like:

- `Ori default`
- `Local fast lane`
- `Deeper reasoning`

Not:

- raw model tags
- backend-specific naming in user-facing surfaces

### 6. Document ownership boundaries

We need clear answers to:

- what belongs in core?
- what belongs in overlays?
- what belongs only in one product?
- what should never bleed across products?

## Immediate Implementation Checklist

Start with these:

1. Create one `Ori Core` prompt/profile source of truth.
2. Create one lightweight overlay file per product: Studio, Home, Dev.
3. Make Oracle the default reasoning path anywhere quality is user-visible.
4. Keep local models only for utility, wake, fallback, and cheap internal work.
5. Remove or hide raw model plumbing from user-facing surfaces unless the product explicitly needs it.
6. Add routing docs for future agents so this does not drift back into ad hoc prompt piles.

## Success Criteria

We are in the right state when:

- Ori feels like the same presence across products
- each product still feels purpose-built
- model swaps do not require rewriting the personality
- local model limits no longer bottleneck the product thesis
- new products can launch with a thin overlay instead of a new brain

## Anti-Patterns

Avoid:

- giant per-product prompts
- product-specific rewrites of Ori’s identity
- trying to make a tiny local model carry premium reasoning
- exposing raw backend details in user-facing settings
- mixing Dev concerns into Studio or Home

## Short Version

The best direction is:

`One Ori OS, many product surfaces.`

Ori is the operator system.
Oracle is the reasoning muscle.
Local models are helpers, not the whole brain.
