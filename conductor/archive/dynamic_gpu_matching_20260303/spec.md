# Specification: Dynamic GPU Matching for Training Size

## Overview
Enhance `scripts/runpod_bridge.py` with intelligent GPU matching logic. The system will dynamically calculate the VRAM requirements for a specific training task and select the most appropriate RunPod instance based on a balanced scoring of headroom, cost, and availability.

## Functional Requirements
1.  **VRAM Requirement Calculation**:
    -   Implement a scoring function that estimates minimum VRAM needed.
    -   Input factors: Model parameters (e.g., gpt2 vs larger future models), Dataset size (extracted from curriculum or args), and Hyperparameters (Batch Size, Sequence Length).
2.  **Intelligent Selection Logic**:
    -   Filter RunPod inventory for GPUs meeting the calculated floor + a "Safe Headroom" buffer.
    -   Prioritize boxes that offer the best balance of VRAM headroom and cost within the user's `--max-price` limit.
3.  **Resilience (Wait & Retry)**:
    -   If no GPU meeting the requirement is available within the price range, the system must enter a "Wait and Retry" loop.
    -   Provide periodic logging of wait status and inventory snapshots.
4.  **Curriculum Integration**:
    -   In `--auto` mode, the script should automatically detect the requirements of the next pending stage from the curriculum metadata.

## Non-Functional Requirements
-   **Sovereign Logic**: The matching logic must be local to the bridge script, not dependent on external sizing APIs.
-   **Logging**: Clear transparency into why a specific GPU was selected (e.g., "Selected A6000: meets 24GB floor + 10GB dataset overhead").

## Acceptance Criteria
-   `runpod_bridge.py` successfully selects a lower-VRAM box for small datasets/models and waits for high-VRAM boxes for larger tasks (like Stage 9).
-   The "Wait & Retry" loop correctly handles "SUPPLY_CONSTRAINT" errors from RunPod.
-   Manual overrides via `--gpu` still take precedence if provided.

## Out of Scope
-   Automated "down-scaling" of training parameters (e.g., auto-reducing batch size to fit a smaller box).
-   Multi-GPU distribution (the matching logic targets single-GPU nodes).
