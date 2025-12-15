---
name: Universal Voice and Text Generation
overview: Implement a universal voice/tone system that adapts contextually (no personalities) and a comprehensive text generation pipeline that produces full responses with sentence-level control, building on existing hybrid_phrasing and phrase_embeddings modules.
todos:
  - id: create_universal_voice_engine
    content: Create universal_voice_engine.py module with tone detection, voice adaptation, and voice profile management
    status: completed
  - id: create_text_generation_engine
    content: Create text_generation_engine.py module with full response generation and sentence-level control
    status: completed
    dependencies:
      - create_universal_voice_engine
  - id: update_hybrid_phrasing
    content: Update hybrid_phrasing_service.py to remove personality_id requirement and add voice_context support
    status: completed
    dependencies:
      - create_universal_voice_engine
  - id: update_thought_to_text
    content: Update thought_to_text.py to use voice_context instead of persona and integrate text_generation_engine
    status: completed
    dependencies:
      - create_text_generation_engine
  - id: update_cognitive_generator
    content: Update cognitive_generator.py to use voice_context and integrate text_generation_engine
    status: completed
    dependencies:
      - create_text_generation_engine
  - id: update_core_response_service
    content: Update core_response_service.py to detect tone and build voice_context for downstream modules
    status: completed
    dependencies:
      - create_universal_voice_engine
  - id: deprecate_personality_modules
    content: Add deprecation warnings to all personality modules and update their metadata
    status: completed
  - id: test_integration
    content: Test tone detection, text generation, and integration with existing modules
    status: completed
    dependencies:
      - update_core_response_service
      - update_cognitive_generator
      - update_thought_to_text
---

# Universal Voice and Text Generation Implementation Plan

## Overview

Replace the personality-based system with a universal voice that adapts contextually, and implement comprehensive text generation capabilities. The system will have a Mavaia base personality (curious, helpful, clear) that adapts based on conversation context, user history, and topic.

## Architecture

### Current State

- **Text Generation**: `thought_to_text` converts reasoning to text, but lacks full response generation
- **Phrasing**: `hybrid_phrasing_service` generates phrases but requires `personality_id`
- **Personalities**: Multiple personality modules exist (personality_response, personality_adaptation_service, etc.)
- **Tone**: No unified tone/voice system

### Target State

- **Universal Voice Engine**: Single adaptive voice system
- **Text Generation Engine**: Full response generation with sentence-level control
- **Tone Adaptation**: Context-based tone modulation (no personalities)
- **Integration**: Seamless integration with existing reasoning and phrasing modules

## Implementation Components

### 1. Universal Voice Engine Module

**File**: `mavaia_core/brain/modules/universal_voice_engine.py`

**Purpose**: Single adaptive voice system that modulates tone based on context

**Operations**:

- `detect_tone_cues`: Analyze user input and conversation context to detect tone preferences
- `adapt_voice`: Apply tone adaptation to text based on detected cues
- `get_voice_profile`: Get current voice configuration for a user/session
- `update_voice_profile`: Update voice profile based on interaction history
- `apply_voice_style`: Apply voice style to generated text

**Key Features**:

- Context-based tone detection (formal/casual/technical/empathetic)
- Conversation topic analysis
- User interaction history tracking
- Mavaia base personality (curious, helpful, clear) as foundation
- Real-time tone adaptation

**Dependencies**:

- `phrase_embeddings` (for semantic analysis)
- `hybrid_phrasing_service` (for phrase generation)
- Conversation history/memory modules

### 2. Text Generation Engine Module

**File**: `mavaia_core/brain/modules/text_generation_engine.py`

**Purpose**: Generate complete responses from reasoning results with sentence-level control

**Operations**:

- `generate_full_response`: Generate complete response from reasoning thoughts
- `generate_sentence`: Generate individual sentence with coherence
- `enhance_phrasing`: Enhance phrasing using hybrid_phrasing_service
- `apply_voice_style`: Apply universal voice to generated text
- `ensure_coherence`: Ensure sentence-to-sentence coherence

**Key Features**:

- Full response generation from reasoning results
- Sentence-by-sentence generation with coherence
- Integration with hybrid_phrasing_service for phrase-level enhancement
- Integration with universal_voice_engine for tone adaptation
- Discourse marker insertion for natural flow
- Grammar and style correction

**Dependencies**:

- `universal_voice_engine`
- `hybrid_phrasing_service`
- `phrase_embeddings`
- `thought_to_text` (for initial conversion)
- `neural_grammar` (for grammar correction)

### 3. Update Hybrid Phrasing Service

**File**: `mavaia_core/brain/modules/hybrid_phrasing_service.py`

**Changes**:

- Remove `personality_id` requirement
- Add `voice_context` parameter instead
- Integrate with `universal_voice_engine` for tone-aware phrase generation
- Update `_generate_hybrid_phrase` to use voice context instead of personality_id

**Key Changes**:

```python
# Before: requires personality_id
def _generate_hybrid_phrase(self, params: Dict[str, Any]) -> Dict[str, Any]:
    personality_id = params.get("personality_id")  # Required
    
# After: uses voice_context
def _generate_hybrid_phrase(self, params: Dict[str, Any]) -> Dict[str, Any]:
    voice_context = params.get("voice_context", {})  # Optional, defaults to base
```

### 4. Update Thought-to-Text Module

**File**: `mavaia_core/brain/modules/thought_to_text.py`

**Changes**:

- Replace `persona` parameter with `voice_context`
- Integrate with `text_generation_engine` for enhanced generation
- Remove personality_module dependency
- Add universal_voice_engine integration

**Key Changes**:

- Update `generate_sentences` to use `voice_context` instead of `persona`
- Integrate with `text_generation_engine` for full response generation
- Remove personality_response module dependency

### 5. Update Cognitive Generator

**File**: `mavaia_core/brain/modules/cognitive_generator.py`

**Changes**:

- Replace `persona`/`personality` parameters with `voice_context`
- Integrate `text_generation_engine` for response generation
- Remove personality_response module dependency
- Add universal_voice_engine for tone adaptation

**Key Changes**:

- Update `generate_response` to use `text_generation_engine`
- Pass `voice_context` instead of `persona` to downstream modules
- Remove personality_response module loading

### 6. Update Core Response Service

**File**: `mavaia_core/brain/modules/core_response_service.py`

**Changes**:

- Replace `persona` parameter with `voice_context`
- Integrate tone detection from user input
- Pass voice context to cognitive_generator

**Key Changes**:

- Detect tone from user input and conversation context
- Build `voice_context` dictionary instead of passing `persona`
- Update all calls to cognitive_generator to use `voice_context`

### 7. Deprecate Personality Modules

**Files to deprecate** (mark as deprecated, don't remove yet):

- `mavaia_core/brain/modules/personality_response.py`
- `mavaia_core/brain/modules/personality_adaptation_service.py`
- `mavaia_core/brain/modules/personality_quirks_service.py`
- `mavaia_core/brain/modules/personality_builder_service.py`
- `mavaia_core/brain/modules/personality_configuration_loader.py`
- `mavaia_core/brain/modules/personality_builder_storage_service.py`

**Action**: Add deprecation warnings and update module metadata to indicate deprecated status

## Data Flow

```
User Input
    ↓
Core Response Service
    ↓ (detect tone from input + context)
Universal Voice Engine (detect_tone_cues)
    ↓ (build voice_context)
Cognitive Generator
    ↓ (generate reasoning)
Text Generation Engine
    ↓ (generate full response)
    ├─→ Thought-to-Text (convert thoughts)
    ├─→ Hybrid Phrasing Service (enhance phrases)
    ├─→ Universal Voice Engine (apply tone)
    └─→ Neural Grammar (correct grammar)
    ↓
Final Response Text
```

## Voice Context Structure

```python
voice_context = {
    "base_personality": "mavaia",  # Always mavaia base
    "tone": "neutral",  # neutral, formal, casual, technical, empathetic, etc.
    "formality_level": 0.5,  # 0.0 (casual) to 1.0 (formal)
    "technical_level": 0.3,  # 0.0 (simple) to 1.0 (technical)
    "empathy_level": 0.6,  # 0.0 (neutral) to 1.0 (empathetic)
    "conversation_topic": "general",  # general, technical, creative, etc.
    "user_history": [],  # Recent interaction patterns
    "adaptation_confidence": 0.8  # Confidence in tone detection
}
```

## Implementation Steps

1. **Create Universal Voice Engine** (`universal_voice_engine.py`)

   - Implement tone detection from context
   - Implement voice adaptation logic
   - Integrate with phrase_embeddings for semantic analysis

2. **Create Text Generation Engine** (`text_generation_engine.py`)

   - Implement full response generation
   - Implement sentence-by-sentence generation
   - Integrate with existing modules (hybrid_phrasing, thought_to_text)

3. **Update Hybrid Phrasing Service**

   - Remove personality_id requirement
   - Add voice_context support
   - Update all operations

4. **Update Thought-to-Text Module**

   - Replace persona with voice_context
   - Integrate text_generation_engine
   - Remove personality dependencies

5. **Update Cognitive Generator**

   - Replace persona/personality with voice_context
   - Integrate text_generation_engine
   - Remove personality_response dependency

6. **Update Core Response Service**

   - Add tone detection
   - Build voice_context
   - Update all downstream calls

7. **Deprecate Personality Modules**

   - Add deprecation warnings
   - Update metadata

8. **Testing & Integration**

   - Test tone detection accuracy
   - Test text generation quality
   - Test integration with existing modules
   - Verify backward compatibility where needed

## Key Design Decisions

1. **No Personality IDs**: Completely remove personality_id from the system
2. **Context-Based Adaptation**: Tone adapts from conversation context, not predefined personalities
3. **Mavaia Base**: All responses start from Mavaia base personality (curious, helpful, clear)
4. **Gradual Adaptation**: Voice adapts gradually based on conversation history
5. **Backward Compatibility**: Maintain API compatibility where possible during transition

## Files to Create

- `mavaia_core/brain/modules/universal_voice_engine.py` (new)
- `mavaia_core/brain/modules/text_generation_engine.py` (new)

## Files to Modify

- `mavaia_core/brain/modules/hybrid_phrasing_service.py`
- `mavaia_core/brain/modules/thought_to_text.py`
- `mavaia_core/brain/modules/cognitive_generator.py`
- `mavaia_core/brain/modules/core_response_service.py`

## Files to Deprecate

- `mavaia_core/brain/modules/personality_response.py`
- `mavaia_core/brain/modules/personality_adaptation_service.py`
- `mavaia_core/brain/modules/personality_quirks_service.py`
- `mavaia_core/brain/modules/personality_builder_service.py`
- `mavaia_core/brain/modules/personality_configuration_loader.py`
- `mavaia_core/brain/modules/personality_builder_storage_service.py`