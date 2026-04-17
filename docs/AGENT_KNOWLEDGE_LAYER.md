# Agent Knowledge Layer

This repo now has a deliberate agent-usable knowledge layer.

The goal is not more documentation. The goal is faster, safer execution by future agents and operators.

Use the layers in this order:

Start with the docs index if you need to orient inside `docs/` itself:

- [README.md](/home/mike/Mavaia/docs/README.md)

## 1. Core layer

- [AGENT_ONBOARDING.md](/home/mike/Mavaia/AGENT_ONBOARDING.md)
- [README.md](/home/mike/Mavaia/docs/README.md)
- [PRODUCTS.md](/home/mike/Mavaia/docs/PRODUCTS.md)

Use this layer to answer:

- what environment am I in?
- what products exist here?
- what operational rules are always true?

## 2. Session layer

- [SESSION_HANDOFF.md](/home/mike/Mavaia/docs/SESSION_HANDOFF.md)

Use this layer to answer:

- what are we focused on right now?
- what is already live on-box?
- what is the next best move?

## 3. Product playbook layer

- [studio/README.md](/home/mike/Mavaia/docs/playbooks/studio/README.md)
- [home/README.md](/home/mike/Mavaia/docs/playbooks/home/README.md)
- [dev/README.md](/home/mike/Mavaia/docs/playbooks/dev/README.md)
- [ORI_CORE_ARCHITECTURE.md](/home/mike/Mavaia/docs/ORI_CORE_ARCHITECTURE.md)

Use this layer to answer:

- what is this product for?
- what should it feel like?
- what should it avoid becoming?
- what belongs globally vs per product?
- what is the cross-product architecture direction?

## 4. Runbook layer

- [live-vps-ui-changes.md](/home/mike/Mavaia/docs/runbooks/live-vps-ui-changes.md)
- [studio-guided-jobs.md](/home/mike/Mavaia/docs/runbooks/studio-guided-jobs.md)

Use this layer to answer:

- what exact operational procedure should I follow?
- how do I make changes safely in this live VPS env?
- what is the canonical Studio job setup pattern?

## 5. Recipe layer

- [create-guided-starter-job.md](/home/mike/Mavaia/docs/recipes/create-guided-starter-job.md)
- [customer-follow-up-job.md](/home/mike/Mavaia/docs/recipes/customer-follow-up-job.md)

Use this layer to answer:

- how do I perform a narrow task end-to-end?
- what does "good" look like for this exact change?

## Design rules

- Keep docs short, direct, and executable.
- Prefer prescriptive guidance over encyclopedic explanation.
- Prefer exact next moves over abstract principles when both are possible.
- Treat these docs as agent fuel, not marketing copy.
- Update the smallest layer that can carry the truth.

## Update rules

- If product direction changes, update the relevant playbook.
- If operational reality changes on-box, update the relevant runbook.
- If session priority changes, update [SESSION_HANDOFF.md](/home/mike/Mavaia/docs/SESSION_HANDOFF.md).
- If a repeated task keeps requiring verbal explanation, create or tighten a recipe.

## Current first-stop path

For most active Studio work, start here:

1. [AGENT_ONBOARDING.md](/home/mike/Mavaia/AGENT_ONBOARDING.md)
2. [SESSION_HANDOFF.md](/home/mike/Mavaia/docs/SESSION_HANDOFF.md)
3. [studio/README.md](/home/mike/Mavaia/docs/playbooks/studio/README.md)
4. [studio-guided-jobs.md](/home/mike/Mavaia/docs/runbooks/studio-guided-jobs.md)
5. [customer-follow-up-job.md](/home/mike/Mavaia/docs/recipes/customer-follow-up-job.md)
