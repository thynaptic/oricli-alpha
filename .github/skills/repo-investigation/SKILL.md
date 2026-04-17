# Repo Investigation

Use this skill for repo surveys, “where were we working,” architecture orientation, or requests to summarize current implementation truth.

## Start here

- `docs/AGENT_KNOWLEDGE_LAYER.md`
- `docs/SESSION_HANDOFF.md`
- recent diffs or recent commits

## Workflow

1. Anchor to the current workspace and current repo first.
2. Prefer implementation truth over stale docs.
3. When summarizing active work, separate:
   - committed direction
   - uncommitted local changes
   - likely next move
4. Keep findings concrete and tied to files or commits.

## Repo-specific rules

- Do not confuse broad ORI platform context with the current repo task.
- If `.github/copilot-instructions.md` conflicts with implementation, trust current code.
- Use `docs/SESSION_HANDOFF.md` as the strongest active-task signal unless fresher code or commits clearly override it.
