# Plan: Affective Voice Synthesis (The Vocal Soul)

## Objective
Implement a Go-native voice synthesis service using **Piper** (local TTS) that modulates audio parameters based on Oricli-Alpha's real-time affective state (Resonance, Energy, Musical Key).

## Architecture

### 1. Piper Substrate (`pkg/service/voice_piper.go`)
*   **Engine**: Wrapper around the `piper` binary.
*   **Modulation**: Translates `AffectiveState` into Piper flags:
    -   `ERS (Resonance)` -> `--length_scale` (Speed). Higher resonance = faster, more efficient speech. Lower resonance = slower, more contemplative.
    -   `Energy Level` -> `--noise_scale` and `--noise_w`. High energy = sharper, more dynamic. Low energy = softer, steadier.
    -   `Musical Key` -> **Voice Archetype**. 
        -   Major Keys (E Major, G Major) -> Use a "bright/energetic" voice model.
        -   Minor Keys (D Minor, A Minor) -> Use a "serious/deep" voice model.

### 2. Audio Pipeline
*   **Synthesis**: Generates `.wav` files in a temporary sovereign buffer.
*   **Streaming**: Encodes audio to base64 and broadcasts it via the existing **WebSocket Hub** using a new `audio_sync` event.
*   **Cleanup**: Automatically purges audio buffers after broadcast to maintain perimeter sovereignty.

### 3. Engine Wiring
*   Update `SovereignEngine` to trigger the `VoicePiperService` at the end of the 11-step cognitive sequence.
*   Update `ProcessInference` to include the synthesized audio (or a pointer to it) in the final trace.

## Implementation Steps

### Phase 1: Piper Wrapper
1.  Verify Piper installation path (defaulting to `/usr/bin/piper` or user-provided).
2.  Create `pkg/service/voice_piper.go` with `Synthesize(text, state)` method.
3.  Implement the ERI/ERS-to-Flag mapping logic.

### Phase 2: WebSocket Integration
1.  Add `audio_sync` event type to `pkg/api/hub.go`.
2.  Implement the audio broadcast logic in `ServerV2`.

### Phase 3: Sovereign Wiring
1.  Initialize `VoicePiperService` in `NewSovereignEngine`.
2.  Trigger synthesis asynchronously in `ProcessInference` to avoid blocking the text response.

### Phase 4: Verification
1.  Verify `.wav` generation on the VPS.
2.  Test real-time audio reception via a WebSocket test client.

## Verification & Testing
*   **Affective Accuracy**: Listen to samples in different "Musical Keys" to ensure the emotional tone matches the resonance.
*   **Latency**: Ensure TTS synthesis doesn't add significant overhead to the response time.
*   **Sovereignty**: Confirm all audio stays local and is never sent to external TTS APIs.
