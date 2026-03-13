# Specification: Persistent Memory Subconscious

## Objective
Transform memory from a discrete retrieval task into a continuous "field of influence" that shapes Oricli-Alpha's cognitive outputs.

## Core Concepts

1. **The Subconscious Field (`SubconsciousFieldModule`)**:
   - A high-speed, vectorized buffer of recent cognitive states, JIT facts, and dream insights.
   - Unlike the `memory_graph`, which is for historical archival, the `subconscious_field` is for active influence.

2. **Neural Vibration (Continuous Embedding)**:
   - Every user interaction and internal "thought" is encoded into a vibration (vector).
   - The field maintains a weighted average of these vibrations, creating a "current mental state" vector.

3. **Bias Injection**:
   - The `cognitive_generator` pulls the current mental state vector.
   - This vector is used to bias word selection and logic paths, ensuring Oricli-Alpha remains consistent with her recent learnings without explicit context padding.

4. **Background Consolidation**:
   - Periodic "deep-sea" syncs between the Subconscious Field and the long-term `memory_graph`.

## Technical Architecture
- **In-Memory Store**: A circular buffer of high-dimensional vectors.
- **Influence Function**: A mathematical weight applied to the `cognitive_generator`'s routing and synthesis logic.
- **Persistence**: State is saved to `oricli_core/data/subconscious_state.bin` and synced to S3.

## Workflow
1. User provides input.
2. `subconscious_field` provides the "Mental State" (e.g., "Currently focused on blockchain and biology").
3. `cognitive_generator` uses this state to prioritize certain reasoning paths.
4. Output is generated.
5. New output is encoded and "vibrates" back into the field, updating the mental state for the next turn.
