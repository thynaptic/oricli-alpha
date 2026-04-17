# ORI Skills And Working Styles

Status: active supporting doc

This file describes the current shape of profiles and skills in ORI.

It is not a dump of every `.ori` file.
It is the current map of:

- what users should actually see
- what stays internal
- what is protected for private external apps

For the authoritative curation rules, see:

- [ORI_PROFILE_AND_SKILL_CURATION.md](/home/mike/Mavaia/docs/ORI_PROFILE_AND_SKILL_CURATION.md)
- [skill_catalog.json](/home/mike/Mavaia/config/skill_catalog.json)

## Core Rule

Users should usually choose a working style, not a raw skill.

- profiles = broad working styles
- skills = narrower internal capability lanes

That means the normal product path is:

1. Ori Core baseline
2. product surface overlay
3. selected working style profile
4. attached skills underneath

## Working Styles Users Can See

These are the real user-facing profile lanes today.

### Studio

- `studio_customer_comms`
  - Customer communication
- `studio_operations`
  - Operations planning
- `studio_meetings`
  - Meetings and notes
- `studio_research`
  - Business research
- `studio_knowledge`
  - Knowledge and SOPs

### Home

- `home_companion`
  - Everyday help
- `home_planner`
  - Planning and reminders
- `home_notes`
  - Notes and writing
- `home_research`
  - Research and decisions

### Dev

- `dev_builder`
  - Build and code
- `dev_architect`
  - Architecture
- `dev_debugger`
  - Debug and investigate

### Red

- `ori_red`
  - Security review and remediation guidance

### Internal baseline only

- `ori_core`
  - canonical base profile
  - not user-facing

- `oricli`
  - compatibility shim
  - not user-facing

## Surface Skill Groups

These are the small skill groups each product surface is allowed to lean on.

### Studio

- `customer_comms`
  - follow-ups, replies, check-ins, customer-ready drafts
- `operations_planner`
  - next steps, repeat work, planning, follow-through
- `meeting_intelligence`
  - summaries, action items, recap, note cleanup
- `business_researcher`
  - comparisons, context gathering, practical recommendations
- `knowledge_organizer`
  - SOPs, procedures, internal information cleanup

### Home

- `business_researcher`
  - research and decisions
- `operations_planner`
  - planning and reminders
- `meeting_intelligence`
  - notes and recap
- `knowledge_organizer`
  - home organization

### Dev

- `go_engineer`
  - Go services, concurrency, backend implementation
- `system_architect`
  - boundaries, architecture, scaling, technical tradeoffs
- `api_designer`
  - API contracts, OpenAPI shape, endpoint design
- `technical_writer`
  - docs, READMEs, migration notes, implementation guides

### Red

- `offensive_security`
  - security review and findings
- `system_architect`
  - architecture review and trust boundaries
- `technical_writer`
  - evidence-led reporting and remediation summaries

## Internal-Only Skills

These stay out of customer-facing settings unless a product later earns them explicitly.

- `canvas_diagram`
- `canvas_react`
- `canvas_web`
- `data_scientist`
- `hive_orchestrator`
- `ml_trainer`
- `ori_language_expert`
- `prompt_engineer`
- `ui_designer`

## Legacy Internal Aliases

These are not preferred current ORI lanes. Keep them only for compatibility or very narrow internal work, and prefer the cleaner replacement lane everywhere else:

- `knowledge_curator`
  - prefer `knowledge_organizer`
- `sovereign_planner`
  - prefer `operations_planner`
- `senior_python_dev`
  - prefer `dev_builder`
- `devops_sre`
  - prefer `dev_architect`

## Protected External-App Skills

These are not normal cleanup targets and should not leak into Studio, Home, or Dev.

- `digital_guardian`
  - reserved for the `Princess Puppy Sanctuary` / `princess-puppy-os` experience

- `jarvis_ops`
  - reserved for the `Princess Puppy Sanctuary` / `princess-puppy-os` operational lane

## Internal Specialists Worth Keeping

These still have a real internal use, but they are not product-facing modes.

- `benchmark_analyst`
  - latency, benchmarking, regression measurement
- `hive_orchestrator`
  - meta-routing and swarm orchestration
- `ml_trainer`
  - training/adapters/experimentation
- `ori_language_expert`
  - ORI DSL and workflow-language support
- `prompt_engineer`
  - prompt and policy shaping

## Overlap Lanes To Watch

These are the main overlap candidates in the current inventory.

- `knowledge_curator`
  - overlaps with `knowledge_organizer`
  - treat as a shrinking legacy alias, not a peer to the current surfaced lane
- `sovereign_planner`
  - overlaps with `operations_planner`
  - treat as a shrinking legacy alias, not a peer to the current surfaced lane
- `ui_designer`
  - overlaps with the `canvas_*` artifact builders
- `senior_python_dev`
  - overlaps conceptually with `dev_builder`
  - treat as a shrinking legacy alias, not a surfaced Dev lane
- `devops_sre`
  - overlaps conceptually with `dev_architect`
  - treat as a shrinking legacy alias unless ORI Dev becomes explicitly infra-heavy

The current rule is:

- do not casually rename runtime files
- but do prefer the cleaner surfaced lane in routing and UI

## Runtime Rule

Skills are not separate models.

They are behavior layers that shape:

- mindset
- instructions
- constraints
- task emphasis

The active surface overlay can allow or block skills, and strict profiles can suppress unrelated trigger-matched skills.

## Current Direction

The product direction is:

- one Ori
- many surfaces
- very few visible working styles
- small curated skill groups
- internal specialists kept internal

If a future doc or UI exposes the raw full skill inventory, treat that as drift unless there is a very explicit reason.
