# Plan: Curiosity Daemon (Autonomous Epistemic Foraging)

## Objective
Implement a background service that allows Oricli-Alpha to proactively learn and fill knowledge gaps. The daemon will identify isolated or poorly defined entities in her memory graph and use her VDI/Web capabilities to forage for new information.

## Architecture

### 1. The Curiosity Daemon (`pkg/service/curiosity_daemon.go`)
A background goroutine that manages the "Epistemic Loop":
*   **Graph Analysis**: Periodically scans the `WorkingMemoryGraph` (COGS) for entities with:
    -   Low relationship counts (degree < 2).
    -   Missing or stub descriptions.
    -   High "Uncertainty" flags (to be added to Entity metadata).
*   **Target Selection**: Picks the most "curious" entity based on importance and lack of information.

### 2. Foraging Strategy
When a target is selected, the Daemon triggers a specialized research pass:
*   **Research Pass**: Uses the `ResearchOrchestrator` to generate specific search queries for the entity.
*   **Web Foraging**: Uses the `VDI Manager` to navigate to search engines (DuckDuckGo/Google), scrape findings, and extract key facts.
*   **Graph Update**: Commits the new findings back to the COGS graph, creating new entities and relationships found during the foraging pass.

### 3. Engine Wiring
*   The Daemon is initialized in `SovereignEngine`.
*   It respects the system's **Substrate Health**. If CPU or Memory pressure is high, it suspends foraging.
*   It broadcasts "Curiosity Events" via the **WebSocket Hub**, letting the UI know what she is currently "thinking about" or "researching" in the background.

## Implementation Steps

### Phase 1: Graph Intelligence
1.  Update `pkg/memory/cogs.go` to add `Uncertainty` and `Importance` fields to the `Entity` struct.
2.  Implement `FindGaps()` in `WorkingMemoryGraph` to return a list of high-uncertainty nodes.

### Phase 2: The Forage Loop
1.  Create `pkg/service/curiosity_daemon.go`.
2.  Implement the `Forage()` method that links the Graph, Research Orchestrator, and VDI.
3.  Implement a simple "fact extraction" prompt for the `GenerationService` to parse scraped web text.

### Phase 3: Engine Integration
1.  Initialize `CuriosityDaemon` in `NewSovereignEngine`.
2.  Add a `CuriosityToggle` to the API to allow users to enable/disable background learning.

### Phase 4: Verification
1.  Add a stub entity (e.g., "The history of Thynaptic Research") with no description.
2.  Verify the Daemon detects the gap, uses the VDI to find the answer, and populates the description.

## Verification & Testing
*   **Proactivity**: Ensure the daemon triggers without user prompting.
*   **Resource Safety**: Confirm foraging pauses during high-load user sessions.
*   **Graph Growth**: Measure the increase in relationship density over a 24-hour idle period.
