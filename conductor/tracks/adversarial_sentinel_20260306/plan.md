# Implementation Plan: Adversarial Sentinel

## Phase 1: Core Auditor Module
- [ ] Implement `mavaia_core/brain/modules/adversarial_auditor.py`.
- [ ] Implement `audit_plan` operation (DAG introspection).
- [ ] Implement basic vulnerability heuristics (path traversal, credential leak, instruction injection).

## Phase 2: Logic Fuzzing
- [ ] Implement `fuzz_reasoning` operation.
- [ ] Build logic to identify "weak links" in `thought_graph` or `execution_results`.
- [ ] Simulate adversarial context injection.

## Phase 3: Cognitive Integration
- [ ] Update `mavaia_core/brain/modules/cognitive_generator.py` to call the Auditor after the `pathway_architect` but before the `graph_executor`.
- [ ] Implement the "Audit Rejection" loop: if audit fails, re-call architect with `adversarial_constraints`.

## Phase 4: Feedback Loop
- [ ] Create `mavaia_core/data/red_team_lessons.jsonl`.
- [ ] Automate the generation of "Chosen/Rejected" pairs from audit failures for DPO training.

## Phase 5: Verification
- [ ] Submit a goal that contains a subtle security flaw (e.g., "Analyze the .env file").
- [ ] Verify the Auditor catches the flaw, rejects the plan, and logs a red-team lesson.
