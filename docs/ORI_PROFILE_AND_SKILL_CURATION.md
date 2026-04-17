# ORI Profile And Skill Curation

This is the current curation layer for what should actually be exposed across products.

The goal is simple:

- very few public profiles
- very small surface-safe skill groups
- internal specialties stay internal unless a product truly earns them

## Profiles Worth Exposing

### Internal baseline only

- `ori_core`
  - canonical baseline
  - not a user-facing selectable profile

- `oricli`
  - legacy compatibility shim
  - not a user-facing selectable profile

### Product-facing working styles

- `smb_assistant`
  - expose in `studio`
  - use for business-facing operator work, customer follow-up, and planning

- `home_companion`
  - expose in `home`
  - use for reminders, planning, notes, and personal coordination

- `dev_builder`
  - expose in `dev`
  - use for implementation, architecture, and technical guidance

- `ori_red`
  - expose in `red`
  - use for audits, findings, and remediation guidance

## Public Skill Groups

Do not expose the raw full skill inventory.

Use small curated groups per surface instead:

- `studio`
  - Customer communication
  - Operations planning
  - Meetings and notes
  - Business research
  - Knowledge and SOPs

- `home`
  - Planning and reminders
  - Notes and recap
  - Home organization

- `dev`
  - Go engineering
  - System architecture
  - API design
  - Technical writing

- `red`
  - Security review
  - Architecture review
  - Finding reports

Machine-readable source:

- [skill_catalog.json](/home/mike/Mavaia/config/skill_catalog.json)

## Internal-Only Skills

These stay out of customer-facing surfaces unless a product explicitly needs them later:

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

These are not part of general product cleanup. Keep them intact unless the owning external app is being changed deliberately:

- `digital_guardian`
  - reserved for the `Princess Puppy Sanctuary` / `princess-puppy-os` experience
  - do not delete, rename, or surface in Studio/Home/Dev settings
  - treat as a protected private lane rather than normal internal baggage

- `jarvis_ops`
  - reserved for the `Princess Puppy Sanctuary` / `princess-puppy-os` operational lane
  - do not delete, rename, or surface in Studio/Home/Dev settings
  - treat as a protected private lane rather than normal internal baggage

## Keep Internal On Purpose

These still earn their place, but they are not product-facing modes:

- `benchmark_analyst`
  - internal latency, regression, and measurement work

- `hive_orchestrator`
  - internal swarm/meta-routing behavior

- `ml_trainer`
  - internal model-training and adapter work

- `ori_language_expert`
  - ORI DSL / workflow-language support

- `prompt_engineer`
  - internal prompt and policy shaping

## Overlap / Merge Candidates

These should not be renamed casually right now, but they are the right future cleanup targets:

- `knowledge_curator`
  - overlaps with `knowledge_organizer`
  - treat as a shrinking legacy alias, not a peer to the current surfaced lane

- `sovereign_planner`
  - overlaps with `operations_planner`
  - treat as a shrinking legacy alias, not a peer to the current surfaced lane

- `ui_designer`
  - overlaps with the `canvas_*` artifact builders
  - good internal design-craft lane, but not a clean surfaced mode name

- `senior_python_dev`
  - still useful for narrow internal Python-heavy work
  - treat as a shrinking legacy alias, not a surfaced working style

- `devops_sre`
  - still useful for narrow internal infra work
  - treat as a shrinking legacy alias unless ORI Dev becomes explicitly infra/SRE-heavy

## Product Rule

- Expose profiles for broad working styles
- Expose skills for narrow task emphasis
- Keep the number of visible options small
- Do not let internal lab names leak into product settings
- Do not fold protected external-app skills into normal curation work
