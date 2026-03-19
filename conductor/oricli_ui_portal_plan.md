# Plan: Oricli-UI Sovereign Portal (Flutter Web)

**Objective:** Create a high-fidelity, sovereign web interface for Oricli-Alpha using Flutter Web. The UI will feature a "Thynaptic" aesthetic (dark mode, glow, noise) and a custom Canvas-driven "Hive Swarm" visualization of the 250+ cognitive modules.

## 1. Key Components & Architecture

### Frontend: Flutter Web (Dart)
- **State Management:** `ChangeNotifier` and `ValueNotifier` for local/app state.
- **Navigation:** `go_router` for smooth page transitions and deep-linking.
- **UI Architecture:** 
    - `HiveSwarmPainter`: Custom `CustomPainter` to render the 250+ module nodes and their bidding "pulses."
    - `ThynapticTheme`: Custom `ThemeExtension` for the premium dark-mode tokens (glow, noise, shadows).
    - `SovereignApiClient`: A clean, robust client to interact with the Go-native API on port 8089.

### Backend Integration: Go Backbone
- **Static File Server:** Update `cmd/backbone/main.go` to serve the compiled Flutter `build/web` directory on port 8090.
- **CORS Support:** Ensure the API gateway allows requests from the UI (localhost:8090).

---

## 2. Phased Implementation Steps

### Phase 1: Foundation & Core Chat (Infrastructure)
- **Step 1:** Initialize the Flutter Web project: `flutter create --platforms web oricli_ui`.
- **Step 2:** Add required dependencies: `go_router`, `http`, `google_fonts`, `flutter_riverpod` (or keep it simple with `Provider`/`ChangeNotifier`).
- **Step 3:** Implement `SovereignApiClient` to handle `chat.completions` and `swarm/run`.
- **Step 4:** Build the basic Chat UI with a terminal-like feel and support for Markdown rendering.

### Phase 2: Thynaptic Aesthetics (Styling)
- **Step 1:** Implement `ThynapticThemeExtension` for custom glow colors and noise texture overlays.
- **Step 2:** Add "Subconscious Field" background: a subtle, animated gradient that reacts to the system's "mood."
- **Step 3:** Optimize Typography with `GoogleFonts.oswald` for headers and `GoogleFonts.robotoMono` for system logs.

### Phase 3: The Hive Swarm Canvas (Visualization)
- **Step 1:** Create `HiveSwarmPainter` to draw 250+ nodes in a force-directed or circular layout.
- **Step 2:** Implement "Pulse" animations for nodes when they bid on a query.
- **Step 3:** Add interactivity: hover over a node to see its module metadata (e.g., `reasoning_module`, `vision_agent`).

### Phase 4: Production Integration (Go)
- **Step 1:** Modify `pkg/api/server_v2.go` to include a static file handler for the Flutter build.
- **Step 2:** Update the `oricli-ui.service` (if it exists) to point to the new Go-served UI.

---

## 3. Verification & Testing

### Verification
- **Functional:** Confirm the UI correctly sends queries to port 8089 and displays responses.
- **Visual:** Verify 60fps performance for the Canvas animations and correctness of the Thynaptic theme.
- **Sovereign:** Ensure the UI is served entirely from the local backbone with no external dependencies (except font assets).

### Testing
- **Widget Tests:** Verify the `ChatMessage` and `HiveNode` components render correctly.
- **Integration Tests:** Test the full flow from user query -> UI -> API -> Response -> UI.

---

## 4. Migration & Future
- **Legacy:** Keep `ui_static/` as a backup/reference.
- **Scaling:** Future support for 3D visualization using `three_js` or advanced Flutter 3D features.
