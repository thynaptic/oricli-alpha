# Plan: Oricli Live Canvas System (Sovereign OpenClaw Parity)

**Objective:** Implement a "Live Canvas" feature in the Sovereign Portal to enable interactive artifacts (code, data, previews) and autonomous computer-use visualization.

## 1. Core Architecture

### Artifact Detection (Backend/LLM)
- Oricli-Alpha will use a specific XML-like tag format to signal artifacts:
  ```xml
  <artifact type="code" title="app.py" language="python">
  print("Hello World")
  </artifact>
  ```
- The Go backbone will preserve these tags in the stream for the UI to intercept.

### Flutter UI Integration
- **Split-View Dashboard:** Introduce a multi-panel layout (Sidebar | Chat | Canvas).
- **ArtifactManager:** A `ChangeNotifier` to track active artifacts in the current session.
- **Renderers:**
    - `CodeArtifactRenderer`: Syntax highlighting and "Copy to Clipboard."
    - `DataArtifactRenderer`: Render CSV/JSON as interactive tables or charts.
    - `BrowserArtifactRenderer`: (Future) Display screenshots/streams from the `ComputerUseModule`.

---

## 2. Implementation Phases

### Phase 1: Split-Screen & Artifact Extraction
- **Step 1:** Implement a `LiveCanvas` panel that appears on the right side of the chat.
- **Step 2:** Update `OricliState` to parse message content for `<artifact>` tags and populate the `ArtifactManager`.
- **Step 3:** Add a "Canvas Toggle" button to the AppBar.

### Phase 2: Specialized Renderers
- **Step 1:** Integrate `flutter_highlight` for beautiful code rendering.
- **Step 2:** Implement a "Version History" for artifacts (e.g., if Oricli updates the code, you can see previous versions).

### Phase 3: Computer-Use Visualization (OpenClaw Bridge)
- **Step 1:** Create an "Environment Preview" widget to show what Oricli's "Hands" are seeing (e.g., a browser screenshot from the VPS).

---

## 3. Verification & Testing
- **Artifact Parsing:** Verify that different types of artifacts are correctly extracted from the LLM response.
- **Performance:** Ensure the UI remains responsive (60fps) even when rendering complex code or large data tables.
- **Sovereignty:** Confirm all rendering happens locally in the browser with no external API calls.
