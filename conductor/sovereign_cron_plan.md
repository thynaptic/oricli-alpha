# Plan: Sovereign Cron (Temporal Intents)

## Objective
Implement a native scheduling system for Oricli-Alpha that allows her to set autonomous future goals and recurring tasks. This provides her with a "sense of time" and the ability to proactively re-inject tasks into her Swarm Bus.

## Architecture

### 1. The Sovereign Scheduler (`pkg/kernel/scheduler.go`)
A Ring-0 service that manages temporal events:
*   **Storage**: In-memory registry of active timers and tickers.
*   **Execution**: When a timer fires, the scheduler publishes a `CFP` (Call for Proposals) message to the `SwarmBus`.
*   **Capabilities**:
    -   `One-shot`: Execute a task once after a delay.
    -   `Recurring`: Execute a task every N minutes/hours.

### 2. Temporal Intents
A structured payload defining the scheduled task:
*   `Operation`: The swarm module operation to trigger (e.g., "audit_logs", "check_build").
*   `Params`: Data required for the operation.
*   `ExecutionID`: Unique tracking ID for cancellation.

### 3. Tool Bridge
Register a new tool in the `Toolbox`:
*   `sov_schedule_task(operation, params, delay_seconds, interval_seconds)`:
    -   `operation`: Name of the capability to trigger.
    -   `params`: JSON object of arguments.
    -   `delay_seconds`: How long to wait before the first execution.
    -   `interval_seconds`: (Optional) If > 0, the task repeats at this interval.

## Implementation Steps

### Phase 1: Core Scheduler
1.  Create `pkg/kernel/scheduler.go`.
2.  Implement `NewScheduler(bus *bus.SwarmBus)`.
3.  Implement `ScheduleTask(...)` and `CancelTask(id)`.

### Phase 2: Engine Integration
1.  Add `Scheduler` to `SovereignEngine` struct in `pkg/cognition/sovereign.go`.
2.  Register `sov_schedule_task` tool.
3.  Update `cmd/backbone/main.go` to initialize the scheduler.

### Phase 3: Verification
1.  Test a simple "echo" task scheduled for 10 seconds in the future.
2.  Verify the task appears on the Swarm Bus and is picked up by a module (e.g., Gosh).

## Verification & Testing
*   **Precision**: Ensure timers fire within ±100ms of the target time.
*   **Concurrency**: Verify multiple overlapping timers do not cause race conditions.
*   **Sovereignty**: All scheduling logic is local and uses native Go primitives.
