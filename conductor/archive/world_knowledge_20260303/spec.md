# Specification: Stage 9 - Comprehensive World Knowledge

## Overview
Implement "Stage 9: Comprehensive World Knowledge" into the Oricli-Alpha training curriculum. This stage is designed to provide the model with a dense, multi-faceted understanding of the world, spanning historical facts, scientific principles, contemporary culture, and common-sense causal reasoning. Unlike elective LoRAs, this will be a core sequential stage that updates the foundation model's weights.

## Functional Requirements
1.  **Curriculum Integration**: Add Stage 9 to `scripts/train_curriculum.py` as a mandatory sequential stage following Stage 8 (Alignment).
2.  **Multi-Source Data Pipeline**:
    -   **Factual Depth**: Integrate full Wikipedia (or a high-quality slice like WikiText-103/Wikipedia-2022).
    -   **Common Sense**: Integrate ConceptNet-based datasets or CommonSenseQA to improve causal and physical world reasoning.
    -   **Contextual Nuance**: Use FineWeb-Edu or OpenWebText for high-quality, diverse world context.
3.  **Foundation Update**: Configure the training to perform full weight updates (Core Sequential) rather than LoRA adaptation, ensuring the knowledge is deeply embedded.
4.  **Sentinel Integration**: Ensure the Curriculum Sentinel monitors this stage for loss plateaus, specifically tuned for the high-diversity data of Stage 9.

## Non-Functional Requirements
-   **Memory Efficiency**: Utilize gradient checkpointing and optimal batch sizes (as recently implemented) to handle the larger knowledge datasets on standard GPU hardware.
-   **Local-First Verification**: Success metrics must be calculable locally using benchmark sets.

## Acceptance Criteria
-   `scripts/train_curriculum.py --list-stages` shows Stage 9 with the correct title and datasets.
-   The training script correctly sequences Stage 9 after the Alignment phase.
-   Benchmark accuracy on a knowledge-focused evaluation set shows measurable improvement over Stage 8.
-   The foundation model's weights are successfully updated and saved in the curriculum run directory.

## Out of Scope
-   Real-time web search during training (knowledge must be from static datasets).
-   Interactive world-simulations or multi-modal knowledge (text-only for this stage).
