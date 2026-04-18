# ORI Home Spec

Status: active supporting doc

This file describes the current direction for ORI Home.

It replaces the older desktop-spec framing that mixed outdated layout details, local-only assumptions, and old persona language.

## What ORI Home Is

ORI Home is the personal and household surface for Ori.

It should feel like:

- calm
- useful
- present
- light to use

It should not feel like:

- a business dashboard
- a developer console
- a local-model science project
- a pile of advanced agent controls

## Core Promise

ORI Home helps with everyday life without becoming another thing to manage.

Examples:

- planning and reminders
- family coordination
- notes and writing
- research and decisions
- household organization

## Product Boundary

### ORI Home

- personal and household companion
- ambient help
- reminders, planning, notes, decisions

### Not ORI Studio

- not the SMB operator surface
- not jobs, desk, approvals, or business follow-through as the main story

### Not ORI Dev

- not a technical builder surface
- not a code or architecture workspace

## Working Styles

Home should expose a very small set of working styles:

- `home_companion`
  - everyday help
- `home_planner`
  - planning and reminders
- `home_notes`
  - notes and writing
- `home_research`
  - research and decisions

Users should feel like they are choosing how Ori helps, not switching models or internal personas.

## Reasoning Direction

Home follows the shared ORI architecture:

- Ori Core baseline
- `home` surface overlay
- selected working style profile
- Oracle as the default reasoning lane
- local models only for utility/fallback work

See:

- [ORI_CORE_ARCHITECTURE.md](/home/mike/Mavaia/docs/ORI_CORE_ARCHITECTURE.md)
- [REASONING.md](/home/mike/Mavaia/docs/REASONING.md)

## UX Direction

Home should prioritize:

- chat-first flow
- fast capture
- low-friction planning
- simple organization
- gentle context, not crowded chrome

Avoid:

- too many panes or dense enterprise UI
- old “private & local” identity signaling as the main value
- exposing raw skills, models, or internal profile language

## Runtime Notes

- Home is currently an Electron product client in [ORI-Home](/home/mike/Mavaia/ORI-Home)
- It now forwards explicit `surface: home` context and profile selection into the shared ORI runtime
- It should stay on the same core/overlay/profile architecture as Studio and Dev

## Near-Term Rule

When deciding between “more capability” and “less cognitive load,” Home should usually choose less cognitive load.
