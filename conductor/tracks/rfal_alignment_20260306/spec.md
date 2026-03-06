# Specification: Conversational RFAL Alignment

**Overview**
Conversational RFAL (Reinforced Award Learning) is an autonomous alignment system that enables Mavaia to learn from organic user feedback and automated checks. By detecting conversational conflicts (e.g., "No, that's not what I meant") and cross-referencing facts and tone, the system generates Direct Preference Optimization (DPO) pairs. These pairs are used to asynchronously update model weights, teaching Mavaia to self-correct hallucinations and maintain contextual tone.

**Functional Requirements**
1.  **Conversational Conflict Detector**:
    *   Monitor user turn N+1 for rejection signals (Keywords like "Actually", "No", "Wrong").
    *   Detect frustration via sentiment analysis.
    *   Identify task repetition as an implicit rejection of the previous output.
2.  **Multi-Factor Reward Engine**:
    *   Calculates a weighted award score using:
        *   **Organic HITL**: Direct user correction (Highest Weight).
        *   **Factual Grounds**: `world_knowledge` verification.
        *   **Tone Alignment**: `AdapterRouter` intent vs. prose style.
3.  **DPO Pair Generator**:
    *   When a conflict is detected, identify the previous response as `Rejected`.
    *   Use the user's corrective input (Turn N+1) as the basis for the `Chosen` response.
    *   Store `[Prompt, Chosen, Rejected]` triplets in `rfal_lessons.jsonl`.
4.  **Asynchronous Lesson Synchronization**:
    *   Maintain a local buffer of alignment lessons.
    *   Trigger an automated DPO training pass via the RunPod bridge once the buffer threshold is reached.
5.  **Epistemic Humility Loop**:
    *   Reward the model for outputting "I don't have enough verified data" when `world_knowledge` confidence is low.

**Non-Functional Requirements**
*   **Zero-Latency Overhead**: Conflict detection and lesson generation must occur in background threads to avoid blocking conversation.
*   **Privacy Preservation**: Lessons must be stored locally and sanitized before being sent to the bridge for training.

**Acceptance Criteria**
*   User saying "No, I meant X" triggers a new entry in the RFAL lesson log.
*   Automated fact-checking correctly penalizes a known technical hallucination.
*   RunPod bridge successfully initiates a DPO fine-tuning pass using collected lessons.
*   Model weights show measurable drift away from "Rejected" patterns in local evaluations.

**Out of Scope**
*   Real-time weight updates (Phase 1 focus is on asynchronous batch sync).
*   Automatic generation of *all* world knowledge (relies on existing knowledge modules).
