# ORI MCP IDE Lanes

## Purpose

This doc defines how ORI MCP should evolve for agent use inside IDEs and local coding environments.

The goal is not "more tools." The goal is clearer agent operating modes.

In practice, agents inside IDEs want to do three different things:

1. build against ORI correctly
2. simulate how ORI would behave in a product lane
3. wire ORI into an app or agent host cleanly

ORI MCP should support those three jobs explicitly.

---

## Core framing

ORI MCP inside an IDE should let an agent:

- build with ORI
- simulate ORI
- connect to ORI

That is a much stronger framing than "ORI has an MCP server."

---

## Lane 1: Build With ORI

### What it is

This is the implementation-advisor lane.

The agent is building software that uses ORI and needs help making correct choices.

### Main jobs

- choose the right surface
- choose whether a working style is needed
- choose the safest request shape
- review integration plans
- review payloads and API decisions
- draft implementation guidance

### Current v1 tools that fit

- `ask_ori`
- `plan_with_ori`
- `review_with_ori`
- `draft_with_ori`
- `list_surfaces`
- `list_working_styles`
- `get_request_template`
- `get_capabilities`

### Future tools that would fit

- `review_request_payload`
- `choose_surface_for_task`
- `choose_working_style_for_task`
- `generate_integration_snippet`

### Safety level

Read-only.

This lane should stay advisory by default.

---

## Lane 2: Simulate ORI

### What it is

This is the product-behavior lane.

The agent is not just asking how to integrate ORI. It is testing how ORI would respond inside a specific product surface.

### Main jobs

- simulate Studio behavior
- simulate Home behavior
- simulate Dev behavior
- simulate Red behavior
- test copy and product flows against the right ORI lane
- compare baseline Ori vs a working style

### Current v1 tools that fit

- `ask_ori`
- `draft_with_ori`
- `review_with_ori`

### How to use them

Use:

- `surface`
- optional `profile`

This lets an IDE agent do things like:

- "How would ORI respond in Studio?"
- "Draft this as Home companion."
- "Review this as Dev builder."
- "Draft this as a sales follow-up lane once ORI CRM exists."

### Future tools that would fit

- `simulate_reply`
- `compare_working_styles`
- `explain_surface_behavior`

### Safety level

Read-only.

This lane should never mutate live product state by default.

It is for product simulation, not product control.

---

## Lane 3: Connect To ORI

### What it is

This is the installation and setup lane.

The agent needs to wire ORI into an environment, host, editor, or app.

### Main jobs

- install ORI MCP into a host
- get the right config for a given environment
- get request templates
- understand auth requirements
- understand public guarantees and limitations

### Current v1 tools and files that fit

Tool:

- `get_install_guide`

Machine files:

- `agent.json`
- `.well-known/agent.json`
- `openapi.json`
- `requests.json`
- `capabilities.json`
- `install-guides.json`
- `mcp-config.example.json`

### Future tools that would fit

- `generate_mcp_config`
- `validate_mcp_config`
- `recommend_install_path`

### Safety level

Mostly read-only, with optional local config generation later.

Do not add live secrets handling or host mutation by default.

---

## Public v1 shape

ORI MCP v1 should stay small and predictable.

### Public tools

- `ask_ori`
- `get_install_guide`
- `plan_with_ori`
- `review_with_ori`
- `draft_with_ori`
- `list_surfaces`
- `list_working_styles`
- `get_request_template`
- `get_capabilities`

### Public rule

ORI MCP v1 is an agent toolkit, not a full control plane.

That means:

- no hidden/internal lanes
- no live workflow mutation
- no raw memory editing
- no product-specific side effects by default

---

## What should stay out of v1

These should not be part of the first public ORI MCP release:

- direct workflow/job mutation
- direct board/task deletion
- hidden skill access
- internal-only profile selection
- broad write actions into connected products
- anything that bypasses the public runtime rules

---

## How this becomes a differentiator

Most agent integrations stop at:

- "here is an API"
- "here is a tool"

ORI MCP becomes stronger when it helps an agent do all three IDE jobs:

1. build with ORI
2. simulate ORI
3. connect to ORI

That is the real product difference.

Not "we support MCP."

But:

"ORI helps agents build, test, and wire ORI correctly from inside their environment."

---

## Suggested v2 path

If v1 proves useful, the next good extensions are:

1. `choose_surface_for_task`
Returns the best-fit surface for a described task.

2. `recommend_working_style`
Returns the best-fit working style for a task and surface.

3. `generate_integration_snippet`
Returns a small code snippet in a target language.

4. `validate_request_shape`
Checks whether a proposed ORI API payload is valid and sensible.

5. `compare_simulated_replies`
Shows how baseline Ori vs a chosen working style would likely differ.

These deepen the three core lanes without turning ORI MCP into an unsafe control surface.

---

## Bottom line

ORI MCP in IDEs should be treated as:

- a build advisor
- a product simulator
- an integration operator

## Product tool packs

ORI MCP should keep one shared core toolkit, then grow small product packs on top of it.

### Shared core

These belong to all products:

- `ask_ori`
- `get_install_guide`
- `plan_with_ori`
- `review_with_ori`
- `draft_with_ori`
- `list_surfaces`
- `list_working_styles`
- `get_request_template`
- `get_capabilities`

### Studio pack

Good future candidates:

- `summarize_board`
- `list_jobs`
- `review_recent_runs`
- `suggest_connections`
- `draft_follow_up`

### Home pack

Good future candidates:

- `plan_day`
- `organize_notes`
- `draft_household_message`
- `summarize_home_context`

### Dev pack

Good future candidates:

- `choose_surface_for_task`
- `recommend_working_style`
- `validate_request_shape`
- `generate_integration_snippet`

### CRM pack (planned)

Good future candidates:

- `draft_follow_up`
- `generate_pitch`
- `generate_sales_script`
- `handle_objection`
- `summarize_account`
- `suggest_next_touch`

CRM should be treated as a sales operator surface, not a full CRM platform.

That is the clean path.

It is useful now, and it gets more valuable as agent-native development becomes normal.
