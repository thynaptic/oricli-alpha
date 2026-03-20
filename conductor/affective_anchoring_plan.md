# Plan: Affective Memory Anchoring

## Objective
Enable Oricli-Alpha to remember the emotional context of past interactions. By storing "Affective Anchors" (Valence, Arousal, Resonance) within the Working Memory Graph (COGS), the system can proactively adapt its personality archetype and supportive tone when specific topics or projects resurface.

## Architecture

### 1. Affective Schema (`pkg/memory/cogs.go`)
Update the `Entity` and `Relationship` structs to include an `AffectiveAnchor`:
*   `Valence`: -1.0 to 1.0 (Pleasantness).
*   `Arousal`: 0.0 to 1.0 (Intensity).
*   `ERI`: Real-time Emotional Resonance Index.

### 2. Recording (Anchoring)
When the `SovereignEngine` creates or updates a node in the graph during `ProcessInference`:
*   Capture the current `AffectiveState`.
*   Attach it to the entity/relationship.
*   If multiple anchors exist for one entity, use an **Exponential Moving Average (EMA)** to track the "Emotional History" of that topic.

### 3. Proactive Pivoting
When Oricli retrieves context from her graph:
*   Identify the "Dominant Affective Tone" of the retrieved entities.
*   If the historical tone indicates high distress (Low Valence, High Arousal), Oricli autonomously sets her `PersonalityEngine` to `Protective` or `Warm` mode *before* the user even responds.
*   If the tone indicates past success (High Valence), she pivots to `Cheerleader` or `Creative`.

## Implementation Steps

### Phase 1: Schema Updates
1.  Update `Entity` struct in `pkg/memory/cogs.go`.
2.  Update `AddEntity` and `UpdateEntity` to handle affective metadata.

### Phase 2: Anchoring Logic
1.  Update `SovereignEngine.ProcessInference` to attach the live `AffectiveState` to new graph nodes.
2.  Implement an `AnchorAffect` helper in the engine.

### Phase 3: Proactive Pivot
1.  Implement `AnalyzeSubGraphAffect` in `WorkingMemoryGraph`.
2.  Add a `PivotPersonality` pass in the cognitive sequence (Step 5.1).

### Phase 4: Verification
1.  Discuss a "Stressful Project" with high distress.
2.  Restart the session and mention the project.
3.  Verify Oricli starts in a more supportive mode (Protective/Warm) automatically.

## Verification & Testing
*   **Emotional Recall**: Verify entities correctly store and retrieve their affective anchors.
*   **Pivoting Accuracy**: Ensure the personality shift matches the historical context.
*   **Decoupling**: Confirm the graph can still function if affective data is missing (graceful degradation).
