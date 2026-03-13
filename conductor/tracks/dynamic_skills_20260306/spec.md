# Specification: Dynamic Skills Framework

## Objective
To enable Oricli-Alpha to dynamically adopt specialized skills, mindsets, and constraints at runtime using declarative `.ori` files, improving task-specific performance and context efficiency.

## Core Components

1. **The `.ori` Format**:
   - A hybrid Markdown/Directive syntax.
   - Directives: `@skill_name`, `@description`, `@triggers`, `@requires_tools`.
   - XML blocks: `<mindset>`, `<instructions>`.

2. **Skill Manager Module (`skill_manager.py`)**:
   - Scans and parses all `.ori` files in the `oricli_core/skills/` directory on boot.
   - Evaluates incoming queries against `@triggers` to find the most relevant skill(s).
   - Extracts and formats the `<mindset>` and `<instructions>` for injection into the prompt.

3. **Cognitive Integration**:
   - `cognitive_generator` queries the `SkillManager` during the intent detection phase.
   - If a skill matches, its mindset and instructions are injected into the system context.
   - The architect ensures any tools required by `@requires_tools` are available in the execution graph.

## Workflow
1. User: "Can you analyze this Python script for security flaws?"
2. `cognitive_generator` detects intent and consults `SkillManager`.
3. `SkillManager` matches "security flaws" to `offensive_security.ori`'s triggers.
4. The mindset ("You are an elite offensive security researcher...") and instructions are loaded.
5. The response is generated under the strict guidance of the injected skill.
