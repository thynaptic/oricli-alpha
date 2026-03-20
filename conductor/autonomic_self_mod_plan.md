# Plan: Autonomic Refactoring (The Self-Modifier)

## Objective
Implement a proactive `ReformDaemon` that monitors Oricli-Alpha's execution traces, detects "Logic Bottlenecks" (high latency or low-confidence reasoning), and autonomously performs a secure Audit-Draft-Verify-Propose cycle to improve her own Go source code.

## Architecture

### 1. The Reform Daemon (`pkg/service/reform_daemon.go`)
A background goroutine that orchestrates the self-modification lifecycle:
*   **Monitor**: Scans the `TraceStore` for records where `Method == "reasoning"` and `Confidence < 0.7` or `Latency > 2s`.
*   **Diagnostic**: Uses `CodeMetricsService` to analyze the complexity of the Go functions involved in the trace.
*   **Lifecycle**: Audit -> Draft -> Verify -> Propose.

### 2. The Reform Pipeline
#### Phase A: Audit
*   Identify the target Go file using the trace metadata.
*   Extract the relevant function using `vdi_sys_read`.
*   Analyze the code for architectural inefficiencies (O(N^2) loops, unnecessary mutex contention, high cyclomatic complexity).

#### Phase B: Draft
*   Create a specialized `Gosh` session (Overlay) that has a copy of the target file.
*   Generate an optimized version of the function using the `GeneratorOrchestrator` with a `Technical Architect` profile.

#### Phase C: Verify (The Sovereign Sandbox)
*   **Compile Test**: Use `yaegi` (via `gosh.Session.RegisterTool`) to interpret and run the new function.
*   **Benchmark**: Compare the performance of the new function against the old version using synthetic inputs.
*   **Safety Audit**: Pass the diff through the `AdversarialAuditor` to ensure no security regressions (e.g., sandbox escapes, memory leaks).

#### Phase D: Propose
*   If the new code is faster and compliant, generate a `Reform Proposal`.
*   Broadcast the proposal via the **WebSocket Hub** for manual approval.
*   Execute `vdi_sys_write` and `git commit` upon user confirmation.

### 3. Safety Guardrails
*   **Ring-0 Protection**: The Reform Daemon is strictly forbidden from modifying `pkg/kernel/` or `pkg/safety/` without manual "Keys-in-Hand" override.
*   **Idempotency**: Every refactor must be atomic and reversible.
*   **Compute Budget**: Self-modification tasks are only triggered when the system detects `CPU_IDLE > 70%`.

## Implementation Steps

### Phase 1: Bottleneck Detection
1.  Enhance `pkg/service/introspection.go` to expose a `FindBottlenecks()` method.
2.  Update `pkg/service/code_metrics.go` to support Go source parsing.

### Phase 2: The Daemon
1.  Create `pkg/service/reform_daemon.go`.
2.  Implement the `Monitor` loop.
3.  Implement the `Verify` logic using `gosh`.

### Phase 3: Engine Integration
1.  Initialize `ReformDaemon` in `NewSovereignEngine`.
2.  Wire the Daemon to the `WSHub` for real-time reporting of optimization candidates.

### Phase 4: Verification
1.  Manually introduce a suboptimal function (e.g., a slow string concatenation loop).
2.  Trigger the Daemon and verify it detects the bottleneck and proposes a fix.

## Verification & Testing
*   **Reliability**: Ensure the interpreted `yaegi` tests accurately reflect compiled Go performance.
*   **Stability**: Confirm the backbone survives multiple rounds of autonomic refactoring.
*   **Sovereignty**: Ensure all "Self-Modification" reasoning stays strictly local.
