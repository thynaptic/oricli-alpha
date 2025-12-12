# Thynaptic RFC (Request for Comments) System

## Overview

The Thynaptic RFC system is an automated governance mechanism that requires RFCs to be filed before making changes to core architecture. This system ensures all architectural changes are properly documented, reviewed, and approved through Cursor ruleset validation.

## When RFCs Are Required

RFCs are **mandatory** before making changes to:

### Core Architecture Files

**Brain System Core:**
- `mavaia_core/brain/base_module.py` - BaseBrainModule interface
- `mavaia_core/brain/registry.py` - ModuleRegistry
- `mavaia_core/brain/orchestrator.py` - ModuleOrchestrator
- `mavaia_core/brain/state_storage/base_storage.py` - BaseStorage interface
- `mavaia_core/brain/dependency_graph.py` - Dependency management
- `mavaia_core/brain/module_lifecycle.py` - Lifecycle management

**API & Client Core:**
- `mavaia_core/api/server.py` - FastAPI server structure
- `mavaia_core/api/openai_compatible.py` - OpenAI compatibility layer
- `mavaia_core/client.py` - MavaiaClient interface

**Architecture Rules:**
- `.cursor/rules/engineering/architecture_rules.mdc` - Architecture governance

### Pattern-Based Detection

RFCs are also required for:
- Changes to abstract base classes (ABC)
- Changes to public interfaces/APIs
- Changes to module discovery mechanisms
- Changes to orchestration patterns
- Breaking changes to module interfaces
- New architectural patterns or paradigms

## RFC Process

### 1. Create RFC

Use the template in `RFC_TEMPLATE.md` to create a new RFC file:
- File name: `RFC-YYYY-NNN-Title.md` (e.g., `RFC-2025-01-Module-Interface-Refactor.md`)
- Place in: `.cursor/rules/governance/RFC/`
- Follow the template structure exactly

### 2. Complete Required Sections

All RFCs must include:
- RFC metadata (number, title, status, dates)
- Abstract
- Motivation
- Proposed Changes
- Impact Analysis
- Alternatives Considered
- Implementation Plan
- Approval Checklist

### 3. Automated Approval

RFCs are automatically approved when:
- All required sections are completed (non-empty)
- RFC follows template format
- RFC number follows format: `RFC-YYYY-NNN`
- RFC is listed in `RFC_INDEX.md`
- Status is set to `APPROVED`

### 4. Update Index

Add your RFC to `RFC_INDEX.md` with:
- RFC number
- Title
- Status
- Date created
- Affected areas

## RFC Status Lifecycle

1. **DRAFT** - RFC is being written, not yet complete
2. **REVIEW** - RFC is complete and ready for validation
3. **APPROVED** - RFC has passed automated validation and is approved
4. **IMPLEMENTED** - Changes from RFC have been implemented
5. **REJECTED** - RFC was rejected (with reason documented)

## Enforcement

The Cursor ruleset automatically:
- Detects changes to core architecture files
- Checks for corresponding RFC file
- Validates RFC format and completeness
- Blocks changes if RFC is missing or invalid
- Provides clear error messages with instructions

## RFC Numbering

RFCs are numbered sequentially: `RFC-YYYY-NNN`
- YYYY: Year (e.g., 2025)
- NNN: Sequential number (001, 002, etc.)

Check `RFC_INDEX.md` for the next available number.

## Style Guidelines

RFCs must follow the **Hard Technical Doctrine** style:
- Clinical, mechanistic language
- Evidence-driven claims
- Zero narrative or marketing prose
- All claims must reference mechanisms or protocols
- Structured sections with clear headings

## Related Documentation

- RFC Template: `RFC_TEMPLATE.md`
- RFC Index: `RFC_INDEX.md`
- Architecture Rules: `.cursor/rules/engineering/architecture_rules.mdc`
- Department Standards: `.cursor/rules/governance/department_standards.mdc`

