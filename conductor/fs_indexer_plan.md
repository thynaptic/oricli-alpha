# Plan: Sovereign Filesystem Indexer

## Objective
Implement a proactive local filesystem indexer that allows Oricli-Alpha to map her own workspace into her Working Memory Graph (COGS). This ensures she knows the location and purpose of her own source code, plans, and documentation without having to manually search every time.

## Architecture

### 1. The Indexing Service (`pkg/service/fs_indexer.go`)
A Ring-0 utility that performs local substrate mapping:
*   **Scanner**: Recursively walks the project root (default: `/home/mike/Mavaia`).
*   **Filter**: Targets high-importance file types (`.go`, `.md`, `.py`, `.ori`, `.json`, `.sh`).
*   **Graph Mapping**: For every matched file, it creates an `Entity` in the COGS graph:
    -   `Label`: Filename.
    -   `Type`: `file`.
    -   `Description`: Full absolute path and file size.
    -   `Uncertainty`: Low (0.1) as the file is verified on disk.

### 2. Semantic Enrichment
For small files (< 100KB), the indexer performs a "Deep Read":
*   Extracts the first 1000 characters.
*   Uses the `GenerationService` to extract 3-5 keywords.
*   Stores keywords in the `Entity.Keywords` field for better relationship anchoring.

### 3. Execution Strategy
*   **Idle Task**: Triggered by the `CuriosityDaemon` when the system is idle and no web foraging is queued.
*   **Manual Tool**: Exposes `vdi_sys_index(path)` in the Toolbox.

## Implementation Steps

### Phase 1: Service Implementation
1.  Create `pkg/service/fs_indexer.go`.
2.  Implement `IndexRecursive(rootPath string)`.
3.  Integrate with `WorkingMemoryGraph.AddEntity`.

### Phase 2: Curiosity Wiring
1.  Update `CuriosityDaemon` to include a `CheckWorkspace()` phase.
2.  If the graph has < 100 "file" entities, trigger a background index of the project root.

### Phase 3: Tool Registration
1.  Add `vdi_sys_index` to `pkg/vdi/tools.go`.

### Phase 4: Verification
1.  Run the indexer on the `pkg/cognition` folder.
2.  Verify the COGS graph contains nodes for `sovereign.go`, `mcts.go`, etc.
3.  Verify she can "locate" her own files in a chat turn.

## Verification & Testing
*   **Performance**: Ensure indexing doesn't block the main event loop (run in goroutine).
*   **Accuracy**: Verify file paths are absolute and accessible.
*   **Graph Density**: Confirm file entities are correctly linked to their parent "folder" concepts.
