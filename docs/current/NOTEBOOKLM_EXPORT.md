# NotebookLM Export Guide

Use this when exporting the docs folder into NotebookLM or any other reference system.

The goal is not to export everything blindly.

The goal is to export the current truth first, then add supporting context only when it helps.

## Recommended Core Export Set

Start with these:

- [README.md](/home/mike/Mavaia/docs/README.md)
- [public_overview.md](/home/mike/Mavaia/docs/public_overview.md)
- [PRODUCTS.md](/home/mike/Mavaia/docs/PRODUCTS.md)
- [ORI_CORE_ARCHITECTURE.md](/home/mike/Mavaia/docs/ORI_CORE_ARCHITECTURE.md)
- [REASONING.md](/home/mike/Mavaia/docs/REASONING.md)
- [SKILLS.md](/home/mike/Mavaia/docs/SKILLS.md)
- [ORI_PROFILE_AND_SKILL_CURATION.md](/home/mike/Mavaia/docs/ORI_PROFILE_AND_SKILL_CURATION.md)
- [API.md](/home/mike/Mavaia/docs/API.md)
- [AGENT_API.md](/home/mike/Mavaia/docs/AGENT_API.md)
- [RUNPOD_STATUS.md](/home/mike/Mavaia/docs/RUNPOD_STATUS.md)

This set gives NotebookLM the current product, runtime, integration, and reasoning story without overloading it with older doctrine.

## Recommended Supporting Export Set

Add these if you want more product detail:

- [ORI_STUDIO_PRODUCT_VISION.md](/home/mike/Mavaia/docs/ORI_STUDIO_PRODUCT_VISION.md)
- [ORI_STUDIO_OVERVIEW.md](/home/mike/Mavaia/docs/ORI_STUDIO_OVERVIEW.md)
- [ORI_HOME_SPEC.md](/home/mike/Mavaia/docs/ORI_HOME_SPEC.md)
- [SMB_DEVELOPER_GUIDE.md](/home/mike/Mavaia/docs/SMB_DEVELOPER_GUIDE.md)
- [ORI_MCP_IDE_LANES.md](/home/mike/Mavaia/docs/ORI_MCP_IDE_LANES.md)
- [DOCS_SITE_IA.md](/home/mike/Mavaia/docs/DOCS_SITE_IA.md)

## Do Not Use As First-Pass Export

These are useful only as historical or deep reference. Do not let them shape NotebookLM's first understanding of ORI.

- [EXTERNAL_INTEGRATION.md](/home/mike/Mavaia/docs/EXTERNAL_INTEGRATION.md)
- [AGLI_VISION.md](/home/mike/Mavaia/docs/AGLI_VISION.md)
- [AGLI_Phase_II.md](/home/mike/Mavaia/docs/AGLI_Phase_II.md)
- [TR-2026-02-Go-Native-Reasoning-Architecture.md](/home/mike/Mavaia/docs/TR-2026-02-Go-Native-Reasoning-Architecture.md)
- [GHOST_CLUSTER.md](/home/mike/Mavaia/docs/GHOST_CLUSTER.md)
- [ROSETTA.md](/home/mike/Mavaia/docs/ROSETTA.md)
- [DAEMONS.md](/home/mike/Mavaia/docs/DAEMONS.md)
- [HIVE_OS_KERNEL_HANDBOOK.md](/home/mike/Mavaia/docs/HIVE_OS_KERNEL_HANDBOOK.md)
- [THERAPEUTIC_COGNITION.md](/home/mike/Mavaia/docs/THERAPEUTIC_COGNITION.md)
- [SELF_LAYER.md](/home/mike/Mavaia/docs/SELF_LAYER.md)

## Export Order

Best order:

1. `README.md`
2. `public_overview.md`
3. `PRODUCTS.md`
4. `ORI_CORE_ARCHITECTURE.md`
5. `REASONING.md`
6. `SKILLS.md`
7. `ORI_PROFILE_AND_SKILL_CURATION.md`
8. `API.md`
9. `AGENT_API.md`
10. `RUNPOD_STATUS.md`

Then add supporting docs only if NotebookLM needs more detail.

## Rule For Future Exports

If a doc still reads like:

- old `Oricli-Alpha`
- old all-local doctrine
- manifesto language
- research theory instead of current runtime truth

do not include it in the first export set.

NotebookLM should learn what ORI is now, not every version ORI has ever been.
