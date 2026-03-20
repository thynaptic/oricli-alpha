# Plan: Sovereign Profile Extensions (.ori)

## Objective
Implement a "Profile" extension system for Oricli-Alpha, similar to Gemini-CLI extensions. These profiles will be hot-swappable `.ori` files that encapsulate personality, rules, instructions, and skills, allowing external API consumers to instantly reconfigure the system's "Soul" per request.

## 1. The Profile Format (`[name]_profile.ori`)
A new `.ori` format that unifies all sovereign pillars:
```text
@profile_name: research_lead
@description: High-fidelity research and synthesis specialist.
@archetype: mentor
@sass_factor: 0.2
@energy: moderate

<instructions>
- Prioritize cited sources and cross-verification.
- Use a formal, objective tone with minimal emotive descriptors.
- Structure all outputs with a "Strategic Findings" summary.
</instructions>

<rules>
- deny: causal_chat on sensitive topics
- prefer: hybrid_rag_engine for all queries
</rules>

<skills>
- data_analysis
- technical_writing
</skills>
```

## 2. Profile Registry (`pkg/cognition/profiles.go`)
Implement a Go-native registry that:
*   **Discovers**: Scans `oricli_core/profiles/*.ori` at startup.
*   **Parses**: Implements an `.ori` parser that extracts tags and XML-style sections.
*   **Hot-Swaps**: Watches the directory for changes and reloads profiles dynamically.
*   **Retrieves**: Provides a `GetProfile(name)` method for the engine.

## 3. Sovereign Engine Integration (`pkg/cognition/sovereign.go`)
Update the `SovereignEngine` to:
*   Hold an `ActiveProfile` pointer.
*   Override default personality and instructions when a profile is selected.
*   Allow the `PromptBuilder` to inject profile-specific directives.

## 4. API & External Access (`pkg/api/server_v2.go`)
*   Update `ChatCompletionRequest` to include a `Profile` field.
*   In `handleChatCompletions`, lookup the requested profile and apply it to the `SovEngine` for that specific inference pass.

## Implementation Steps

### Phase 1: Registry & Parsing
1. Create `pkg/cognition/profiles.go` with the `Profile` struct and `.ori` parser.
2. Implement directory watching for hot-swapping.

### Phase 2: Engine Integration
1. Update `SovereignEngine` to support dynamic profile switching.
2. Update `PromptBuilder` to incorporate profile-specific instructions.

### Phase 3: API & Verification
1. Update API models and handler to support the `profile` parameter.
2. Create a test `research_profile.ori` and verify the switch via curl.

## Verification & Testing
*   **Build Check**: Ensure the backbone compiles with the new registry.
*   **Hot-Swap Test**: Modify a profile file and verify the logs show a reload.
*   **API Test**: Call the API with `{"profile": "research_lead"}` and verify the response tone matches the profile.
