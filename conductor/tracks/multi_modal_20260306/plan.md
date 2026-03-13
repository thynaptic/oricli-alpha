# Implementation Plan: Multi-Modal Synthesis

## Phase 1: Sensory Infrastructure
- [ ] Implement `oricli_core/brain/modules/sensory_router.py`.
- [ ] Add basic image metadata extraction (dimensions, color profile, simple OCR fallback).
- [ ] Add basic audio metadata extraction (duration, format).

## Phase 2: Multi-Modal Generator
- [ ] Update `oricli_core/brain/modules/cognitive_generator.py` to support `vision_context` and `audio_context`.
- [ ] Implement "Joint Context" synthesis where text and image data are merged for the reasoner.

## Phase 3: Voice Integration
- [ ] Implement the `speak` operation in `cognitive_generator`.
- [ ] Integrate with `universal_voice_engine` to generate proactive audio responses.

## Phase 4: Verification
- [ ] Submit a query with an image path.
- [ ] Verify Oricli-Alpha acknowledges the image and includes its context in her reasoning.
- [ ] Submit a voice-based query and verify the STT -> Synthesis -> TTS loop.
