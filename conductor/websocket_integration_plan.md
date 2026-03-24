# Plan: Real-Time WebSocket Gateway

## Objective
Implement a high-speed WebSocket gateway in Oricli-Alpha to enable real-time state synchronization with the ORI Studio UI. This allows the system to "push" affective, resonant, and visual state changes to the client without waiting for a request.

## Architecture

### 1. WebSocket Hub (`pkg/api/hub.go`)
Implement a central `Hub` to manage active UI client connections:
*   **Connection Management**: Register/Unregister clients.
*   **Broadcast**: Send events to all connected clients.
*   **Concurrency**: Uses thread-safe channels for message distribution.

### 2. State Streaming (`pkg/api/ws_handlers.go`)
Create a dedicated route `/v1/ws` in `ServerV2` that upgrades HTTP connections to WebSockets:
*   **Event Types**:
    -   `resonance_sync`: Streams real-time ERI, ERS, and Musical Key.
    -   `sensory_sync`: Streams real-time Hex colors, opacities, and pulse rates.
    -   `vdi_sync`: Streams browser navigation events and action status.
    -   `kernel_log`: Optional stream of Ring-0 system logs.

### 3. Engine Wiring
*   The `SovereignEngine` will notify the `Hub` whenever a `ProcessInference` cycle completes or a homeostasis reset occurs.
*   The `VDI Manager` will notify the `Hub` on navigation or DOM interaction.

## Implementation Steps

### Phase 1: Infrastructure
1.  Add `github.com/gorilla/websocket` to `go.mod`.
2.  Create `pkg/api/hub.go` with the `Hub` and `Client` structs.

### Phase 2: Handlers & Logic
1.  Create `pkg/api/ws_handlers.go` to handle the Gin websocket upgrade.
2.  Implement the broadcast logic for the 4 core sync types.

### Phase 3: Integration
1.  Initialize the `Hub` in `NewServerV2`.
2.  Inject the `Hub` into the `SovereignEngine` via the `NewSovereignEngine` constructor (or a setter).
3.  Trigger broadcasts at the end of `ProcessInference`.

### Phase 4: Verification
1.  Verify the backbone compiles.
2.  Use a simple `wscat` or JS test script to verify real-time event reception.

## Verification & Testing
*   **Build**: Ensure `oricli-go-v2` compiles.
*   **Latency**: Verify sub-millisecond event dispatch from the Swarm Bus to the WebSocket.
*   **Scalability**: Ensure multiple UI instances can connect and receive independent/shared state.
