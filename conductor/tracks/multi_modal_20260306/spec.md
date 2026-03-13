# Specification: Multi-Modal Synthesis

## Objective
Create a unified sensory processing layer that allows Oricli-Alpha to perceive, analyze, and synthesize information from images, audio, and text simultaneously.

## Core Components

1. **The Sensory Router (`sensory_router.py`)**:
   - Detects the type of incoming sensory data (Image, Audio, Video, Text).
   - Routes the data to the appropriate specialized encoder.

2. **Cross-Modal Embedding Space**:
   - Evolve the `embeddings` module to support CLIP-style joint embeddings (Image + Text) and Audio-to-Vector mappings.
   - All sensory inputs are projected into the same high-dimensional space as the `subconscious_field`.

3. **The Multi-Modal Synthesizer**:
   - An expansion of the `cognitive_generator` that can take a "Sensory Pack" (e.g., An image of a circuit + a voice question "Why is this failing?") and produce a reasoned response.

4. **Autonomic Voice Synthesis**:
   - Integration with the `universal_voice_engine` to allow Oricli-Alpha to proactively "speak" her thoughts as an audio stream.

## Technical Architecture
- **Vision**: Integration with local vision-encoders (e.g., LLaVA or smaller CLIP models).
- **Audio**: Non-blocking integration with Whisper (speech-to-text) and a local TTS engine.
- **Unified Graph**: The `dynamic_graph_executor` will include sensory processing nodes as first-class citizens.

## Workflow
1. User uploads an image and asks a question.
2. `sensory_router` encodes the image.
3. `pathway_architect` creates a graph: `VisionEncoder -> ContextMerge -> Reasoning -> Synthesize`.
4. `subconscious_field` provides the current mental bias.
5. Final multi-modal response is generated.
