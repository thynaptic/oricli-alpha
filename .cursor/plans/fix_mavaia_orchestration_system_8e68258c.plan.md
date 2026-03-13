---
name: Fix Mavaia Orchestration System
overview: Fix the orchestration system so Mavaia can properly route requests to appropriate brain modules and generate plausible responses instead of returning "1" as a fallback. Implement auto-routing based on input analysis and ensure proper module coordination.
todos:
  - id: fix_1_fallback
    content: Remove hardcoded '1' fallback in advanced_reasoning_solvers.py and replace with proper error handling
    status: completed
  - id: add_intent_detection
    content: Implement intent detection and query classification in cognitive_generator.py
    status: completed
  - id: implement_auto_routing
    content: Add auto-routing logic to select appropriate modules based on input analysis
    status: completed
    dependencies:
      - add_intent_detection
  - id: enhance_module_orchestration
    content: Improve generate_response() to properly orchestrate multiple modules with fallback chain
    status: completed
    dependencies:
      - implement_auto_routing
  - id: fix_personality_fallback
    content: Ensure personality-aware fallback never returns '1' and always provides meaningful responses
    status: completed
  - id: add_validation
    content: Add validation to reject '1' responses at all levels and log errors for debugging
    status: completed
    dependencies:
      - fix_1_fallback
  - id: test_orchestration
    content: Test with various input types to verify proper routing and no "1" responses
    status: completed
    dependencies:
      - enhance_module_orchestration
      - fix_personality_fallback
      - add_validation
---

# Fix Mavaia Orchestration System

## Problem Analysis

Mavaia is currently returning "1" as a fallback response because:

1. The `advanced_reasoning_solvers.py` module has a hardcoded "1" default answer (line 7089)
2. The `cognitive_generator` is not properly orchestrating modules
3. Modules are failing silently and returning invalid responses
4. There's no proper auto-routing mechanism to select appropriate modules based on input

## Solution Architecture

### 1. Fix "1" Fallback Issue

- **File**: `oricli_core/brain/modules/advanced_reasoning_solvers.py`
- Remove hardcoded "1" default answer
- Replace with proper error handling that returns None/empty instead of "1"
- Ensure all fallback paths return meaningful error messages or None

### 2. Implement Auto-Routing System

- **File**: `oricli_core/brain/modules/cognitive_generator.py`
- Add intent detection and query classification
- Implement module selection logic based on input type:
- Reasoning queries → `reasoning`, `chain_of_thought`
- Code questions → `reasoning_code_generator`, `python_code_explanation`
- General conversation → `conversational_orchestrator`, `personality_response`
- Search queries → `web_search`, `world_knowledge`
- Math/logic → `advanced_reasoning_solvers`, `symbolic_solver`
- Add module execution with proper error handling and fallback chain

### 3. Enhance Module Orchestration

- **File**: `oricli_core/brain/modules/cognitive_generator.py`
- Improve `generate_response()` to:
- Analyze input to determine required capabilities
- Route to appropriate modules based on analysis
- Execute modules in proper order (reasoning → generation → enhancement)
- Aggregate results from multiple modules when needed
- Handle module failures gracefully with fallback chain

### 4. Fix Personality-Aware Fallback

- **File**: `oricli_core/brain/modules/cognitive_generator.py`
- Ensure `_generate_personality_aware_fallback()` always returns meaningful responses
- Never return "1" or single digits
- Use conversational templates based on persona
- Include context-aware responses

### 5. Add Module Discovery and Initialization

- **File**: `oricli_core/brain/modules/cognitive_generator.py`
- Ensure all required modules are discovered and loaded
- Add proper initialization checks
- Handle missing modules gracefully with clear error messages

### 6. Improve Error Handling

- **Files**: Multiple module files
- Replace all "1" fallbacks with proper error handling
- Add validation to prevent "1" responses from propagating
- Log errors for debugging while returning user-friendly messages

## Implementation Steps

1. **Remove "1" Fallbacks** (Priority: Critical)

- Fix `advanced_reasoning_solvers.py` line 7089
- Add validation in `cognitive_generator.py` to reject "1" responses
- Check all modules for similar issues

2. **Implement Intent Detection** (Priority: High)

- Add query classification in `cognitive_generator.py`
- Create routing rules based on input patterns
- Map intents to appropriate modules

3. **Enhance Module Routing** (Priority: High)

- Update `generate_response()` to use intent-based routing
- Implement module execution chain with fallbacks
- Add result validation and aggregation

4. **Fix Fallback Chain** (Priority: High)

- Ensure personality-aware fallback never returns "1"
- Add multiple fallback levels with increasing specificity
- Use conversational templates

5. **Add Comprehensive Testing** (Priority: Medium)

- Test with various input types
- Verify no "1" responses are returned
- Ensure proper module routing

## Key Files to Modify

1. `oricli_core/brain/modules/advanced_reasoning_solvers.py` - Remove "1" fallback
2. `oricli_core/brain/modules/cognitive_generator.py` - Add auto-routing and orchestration
3. `oricli_core/brain/modules/chain_of_thought.py` - Ensure no "1" responses (already has checks, verify they work)
4. `oricli_core/brain/modules/unified_interface.py` - Enhance routing if needed

## Success Criteria

- Mavaia never returns "1" as a response
- Input is properly analyzed and routed to appropriate modules
- Multiple modules can be orchestrated for complex queries
- Personality-aware fallbacks provide meaningful responses
- All modules are properly discovered and initialized
- Error handling provides useful feedback without exposing "1"