# Implementation Plan: Dynamic Skills Framework

## Phase 1: The .ori Parser and Manager
- [ ] Create `oricli_core/brain/modules/skill_manager.py`.
- [ ] Implement the `.ori` file parser (extracting directives and XML blocks).
- [ ] Build the trigger-matching logic.

## Phase 2: Core Integration
- [ ] Update `oricli_core/brain/modules/cognitive_generator.py` to load and use `SkillManager`.
- [ ] Inject the matched skill's mindset and instructions into the `context` or `system_prompt`.

## Phase 3: Skill Creation
- [ ] Create the `oricli_core/skills/` directory.
- [ ] Write the first skill: `offensive_security.ori`.
- [ ] Write a second skill: `senior_python_dev.ori`.

## Phase 4: Verification
- [ ] Submit a query that matches a skill's trigger.
- [ ] Verify that the `SkillManager` loads the correct `.ori` file and injects its content.
