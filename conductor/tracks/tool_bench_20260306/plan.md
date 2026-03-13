# Implementation Plan: Dynamic ToolBench Framework

## Phase 1: Dynamic Introspection
- [ ] Create `scripts/tool_bench_generator.py`.
- [ ] Implement logic to import and parse `oricli_core/services/tool_registry.py` schemas.
- [ ] Build the "Synthetic Prompt" generator using internal cognitive modules.

## Phase 2: Benchmark Execution
- [ ] Create `scripts/run_tool_bench.py`.
- [ ] Implement the execution loop (Query -> Oricli-Alpha -> Tool Call Output).
- [ ] Build the automated Grader (Schema validation + Logic check).

## Phase 3: Feedback & Correction
- [ ] Implement `oricli_core/data/tool_corrections.jsonl`.
- [ ] Create the "Correction Generator" (Auto-generates the "Right" way to use the tool when Oricli-Alpha fails).
- [ ] Log results to the buffer.

## Phase 4: Autonomous Training
- [ ] Implement `scripts/oricli_tool_daemon.py`.
- [ ] Add `--train-tool-bench` support to `scripts/runpod_bridge.py`.
- [ ] Update the watchdog to include `tool_corrections` in S3 sync.

## Phase 5: Verification
- [ ] Add a new tool to `tool_registry.py`.
- [ ] Verify ToolBench detects it, generates tests, and logs corrections if Oricli-Alpha fails.
