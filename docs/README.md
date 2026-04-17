# Docs Index

This folder has material from multiple eras of ORI.

Do not assume every file here is current, canonical, or equally important.

Use this index first.

## Source Of Truth

These are the current first-stop docs for active product and runtime work:

- [AGENT_KNOWLEDGE_LAYER.md](/home/mike/Mavaia/docs/AGENT_KNOWLEDGE_LAYER.md)
- [AGENT_API.md](/home/mike/Mavaia/docs/AGENT_API.md)
- [API.md](/home/mike/Mavaia/docs/API.md)
- [PRODUCTS.md](/home/mike/Mavaia/docs/PRODUCTS.md)
- [SESSION_HANDOFF.md](/home/mike/Mavaia/docs/SESSION_HANDOFF.md)
- [ORI_CORE_ARCHITECTURE.md](/home/mike/Mavaia/docs/ORI_CORE_ARCHITECTURE.md)
- [ORI_PROFILE_AND_SKILL_CURATION.md](/home/mike/Mavaia/docs/ORI_PROFILE_AND_SKILL_CURATION.md)

## NotebookLM Export

If you are exporting this folder into NotebookLM or another reference system, start with:

- [NOTEBOOKLM_EXPORT.md](/home/mike/Mavaia/docs/NOTEBOOKLM_EXPORT.md)

That file defines:

- the recommended core export set
- the supporting export set
- docs that should stay out of the first-pass export

## Active Supporting Reference

These docs provide deep technical context for the current Go backbone and its subsystems:

- [DAEMONS.md](/home/mike/Mavaia/docs/DAEMONS.md) — Autonomous daemon reference
- [MEMORY_ARCHITECTURE.md](/home/mike/Mavaia/docs/MEMORY_ARCHITECTURE.md) — Four-tier memory stack
- [EPISTEMIC_HYGIENE.md](/home/mike/Mavaia/docs/EPISTEMIC_HYGIENE.md) — Memory sanity and provenance
- [IP_BOUNDARY.md](/home/mike/Mavaia/docs/IP_BOUNDARY.md) — Public vs Private code policy
- [MCTS_REASONING.md](/home/mike/Mavaia/docs/MCTS_REASONING.md) — Strategic planning and MCTS engine
- [ROSETTA.md](/home/mike/Mavaia/docs/ROSETTA.md) — Translation and vocabulary mapping
- [SECURITY.md](/home/mike/Mavaia/docs/SECURITY.md) — Platform security model
- [CHANGELOG.md](/home/mike/Mavaia/docs/CHANGELOG.md) — Version history

## Product Docs

- [playbooks/studio/README.md](/home/mike/Mavaia/docs/playbooks/studio/README.md)
- [playbooks/home/README.md](/home/mike/Mavaia/docs/playbooks/home/README.md)
- [playbooks/dev/README.md](/home/mike/Mavaia/docs/playbooks/dev/README.md)
- [ORI_STUDIO_PRODUCT_VISION.md](/home/mike/Mavaia/docs/ORI_STUDIO_PRODUCT_VISION.md)
- [ORI_STUDIO_OVERVIEW.md](/home/mike/Mavaia/docs/ORI_STUDIO_OVERVIEW.md)
- [ORI_HOME_SPEC.md](/home/mike/Mavaia/docs/ORI_HOME_SPEC.md)
- [SKILLS.md](/home/mike/Mavaia/docs/SKILLS.md)
- [REASONING.md](/home/mike/Mavaia/docs/REASONING.md)

## Studio Implementation (Python Proxy)

These docs cover the Python/Flask proxy layer that handles Studio-specific logic like workflows, pipelines, email commands, and MCP management:

- [STUDIO_API.md](/home/mike/Mavaia/oricli_core/docs/STUDIO_API.md) — Studio-side endpoint reference
- [STUDIO_AGENT_API.md](/home/mike/Mavaia/oricli_core/docs/STUDIO_AGENT_API.md) — Studio agent integration reference
- [STUDIO_EMAIL.md](/home/mike/Mavaia/oricli_core/docs/STUDIO_EMAIL.md) — Email command system reference
- [STUDIO_EXTERNAL_INTEGRATION.md](/home/mike/Mavaia/oricli_core/docs/STUDIO_EXTERNAL_INTEGRATION.md) — Webhooks, OAuth, and MCP guide
- [STUDIO_ONBOARDING.md](/home/mike/Mavaia/oricli_core/docs/STUDIO_ONBOARDING.md) — Studio-specific onboarding details

## Operational Docs

- [runbooks/live-vps-ui-changes.md](/home/mike/Mavaia/docs/runbooks/live-vps-ui-changes.md)
- [runbooks/studio-guided-jobs.md](/home/mike/Mavaia/docs/runbooks/studio-guided-jobs.md)
- [ORI_DEV_DEPLOY.md](/home/mike/Mavaia/docs/ORI_DEV_DEPLOY.md)
- [SOVEREIGN_STACK.md](/home/mike/Mavaia/docs/SOVEREIGN_STACK.md)
- [SMB_DEVELOPER_GUIDE.md](/home/mike/Mavaia/docs/SMB_DEVELOPER_GUIDE.md)

## Current Strategy / Cleanup

- [DOCS_REFACTOR_PLAN.md](/home/mike/Mavaia/docs/DOCS_REFACTOR_PLAN.md)
- [DOCS_SITE_IA.md](/home/mike/Mavaia/docs/DOCS_SITE_IA.md)
- [RUNPOD_STATUS.md](/home/mike/Mavaia/docs/RUNPOD_STATUS.md)

## Historical Context

- [EXTERNAL_INTEGRATION.md](/home/mike/Mavaia/docs/EXTERNAL_INTEGRATION.md) (Marked HISTORICAL)
- [AGLI_Phase_II.md](/home/mike/Mavaia/docs/AGLI_Phase_II.md)
- [AGLI_VISION.md](/home/mike/Mavaia/docs/AGLI_VISION.md)
- [CALI.md](/home/mike/Mavaia/docs/CALI.md)
- [TR-2025-01-Cognitive-System-Naming-Scheme.md](/home/mike/Mavaia/docs/TR-2025-01-Cognitive-System-Naming-Scheme.md)

## Working Rule

Before updating or trusting a doc, decide which bucket it belongs to:

- source of truth
- active supporting reference
- historical context
- stale / archive candidate

If that status is not clear, the file should not silently shape product decisions.
