# ORI Overview

Status: active supporting doc

ORI is the intelligence system behind multiple product surfaces.

It is designed to feel consistent across products while adapting to the context it is working in.

## In Plain Terms

ORI helps people get useful work done without making them manage a complicated AI system.

Depending on the product surface, that can mean:

- running business jobs and follow-through
- helping at home with planning, notes, and decisions
- supporting technical build and product work
- reviewing security and remediation work

## What ORI Actually Is

ORI is not just a model.

ORI is the system that:

- keeps identity and tone consistent
- remembers context
- routes work to the right tools and reasoning path
- applies product boundaries
- returns the final result in a useful form

That means the intelligence underneath can change without breaking the product experience.

## Product Surfaces

### ORI Studio

The small-business operator surface.

Best for:

- jobs
- desk / review flow
- notes
- approvals
- repeat business work

### ORI Home

The personal and household surface.

Best for:

- planning
- reminders
- notes
- everyday decisions
- household organization

### ORI Dev

The technical builder surface.

Best for:

- implementation
- architecture
- debugging
- technical writing

### ORI Red

The security and assurance surface.

Best for:

- findings
- architecture review
- remediation guidance

## How ORI Thinks

The current architecture is:

1. Ori Core
2. product surface overlay
3. working style profile
4. tools and allowed skills
5. reasoning backend

In practice:

- ORI carries the identity, routing, memory, and product logic
- Oracle is the default reasoning lane for strong user-visible quality
- local models are used for utility, fallback, and lighter support work

## What ORI Is Not

ORI should not be thought of as:

- just a local model
- just a chatbot
- just a wrapper around a third-party API
- a separate personality for every app

The direction is:

`One Ori, many surfaces.`

## If You Need More Detail

Start here:

- [ORI_CORE_ARCHITECTURE.md](/home/mike/Mavaia/docs/ORI_CORE_ARCHITECTURE.md)
- [PRODUCTS.md](/home/mike/Mavaia/docs/PRODUCTS.md)
- [REASONING.md](/home/mike/Mavaia/docs/REASONING.md)
