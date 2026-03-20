# Plan: Visual VDI (Model-in-the-Loop)

## Objective
Integrate the Qwen2.5-VL vision model into Oricli-Alpha's VDI layer to enable coordinate-based interaction. This allows the system to "see" UI elements and click them even without stable CSS selectors, achieving true autonomous computer use.

## Architecture

### 1. Vision-Language Integration
*   **Model**: Use `qwen2.5vl` (via Ollama) for high-fidelity UI grounding.
*   **Grounding Logic**: Implement a "Visual Localization" pass that takes a screenshot and an element description (e.g., "the blue login button") and returns pixel coordinates `[x, y]`.

### 2. VDI Enhancements (`pkg/vdi/browser.go`)
*   `Screenshot()`: Captures the current viewport as a base64 string.
*   `ClickAt(x, y)`: Uses `chromedp.MouseClick` to interact with specific pixel coordinates.

### 3. Visual Tooling (`pkg/vdi/tools.go`)
Register a new high-level tool:
*   `vdi_visual_click(description)`: 
    1.  Captures a screenshot.
    2.  Sends it to Qwen2.5-VL with a grounding prompt.
    3.  Parses the `[x1, y1, x2, y2]` bounding box.
    4.  Calculates the center point.
    5.  Executes a native click at those coordinates.

### 4. Curiosity Daemon (Proactive Grounding)
*   Integrate vision into the `CuriosityDaemon`. If Oricli is idle, she can "browse" her own graph or local system visually to identify missing metadata (like transcribing an image found in a local folder).

## Implementation Steps

### Phase 1: VDI Upgrades
1.  Update `pkg/vdi/browser.go` with `Screenshot` and `ClickAt` methods.
2.  Update `pkg/vdi/manager.go` to support viewport dimension tracking.

### Phase 2: Vision Service
1.  Create `pkg/service/vision_grounding.go` to handle the Qwen2.5-VL specific prompts and coordinate parsing.
2.  Implement regex to extract `[x1, y1, x2, y2]` from model output.

### Phase 3: Tool Integration
1.  Register `vdi_visual_click` in Oricli's `Toolbox`.
2.  Register `vdi_visual_scrape` (extracting text from a specific region).

### Phase 4: Verification
1.  Test `vdi_visual_click("Login")` on a test site to verify coordinate precision.
2.  Verify the "Visual Instruction Trace" in her modulated output.

## Verification & Testing
*   **Coordinate Accuracy**: Compare model-returned coordinates with actual element positions.
*   **Latency**: Measure the time for the full loop (Screenshot -> VLM -> Click).
*   **Sovereignty**: Ensure all vision processing happens locally via Ollama.
