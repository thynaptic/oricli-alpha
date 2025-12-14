---
name: Enhance Reasoning Capabilities
overview: Transform the custom_reasoning_networks module from placeholder-based responses to actual reasoning by integrating existing reasoning modules, adding puzzle-solving logic, implementing smart routing, and enhancing neural reasoning capabilities.
todos:
  - id: integrate_reasoning_modules
    content: Integrate existing reasoning modules (reasoning, chain_of_thought, logical_deduction) into custom_reasoning_networks.py using ModuleRegistry
    status: completed
  - id: enhance_text_generation
    content: Enhance _generate_text_from_embeddings() to call actual reasoning modules and use their results instead of placeholder responses
    status: completed
    dependencies:
      - integrate_reasoning_modules
  - id: improve_multi_step
    content: Improve _multi_step_reasoning() to use reasoning.multi_step_solve() before generating text, combining symbolic and neural reasoning
    status: completed
    dependencies:
      - integrate_reasoning_modules
  - id: create_puzzle_parser
    content: Create _parse_puzzle_constraints() method to extract entities, relationships, and constraints from puzzle text
    status: completed
  - id: integrate_symbolic_solver
    content: Add _solve_puzzle_with_solver() method to use symbolic_solver module for constraint satisfaction problems
    status: completed
    dependencies:
      - create_puzzle_parser
  - id: zebra_puzzle_solver
    content: Implement _solve_zebra_puzzle() method with constraint parsing, Z3 solving, and LiveBench-formatted output
    status: completed
    dependencies:
      - integrate_symbolic_solver
  - id: task_type_detection
    content: Add _detect_reasoning_type() method to classify tasks (puzzle, math, logical_deduction, etc.) and recommend reasoning approach
    status: completed
  - id: smart_routing
    content: Implement smart routing in execute() method to route tasks to appropriate reasoning methods based on task type
    status: completed
    dependencies:
      - task_type_detection
      - zebra_puzzle_solver
  - id: hybrid_reasoning
    content: Add _hybrid_reasoning() method to combine neural embeddings with symbolic reasoning for better results
    status: completed
    dependencies:
      - improve_multi_step
---

# Strategic Plan: Enhance Reasoning Capabilities

## Current State Analysis

The `custom_reasoning_networks.py` module is failing at 9% (13/200 tests) because:

- **Zebra puzzles**: 50 failures - returning placeholder numbers instead of solving
- **General reasoning**: Not performing actual logical reasoning, just generating heuristic-based responses
- **Neural-only approach**: Using embeddings but not leveraging symbolic reasoning capabilities
- **No integration**: Not utilizing existing powerful reasoning modules in the codebase

## Strategic Approach

### Phase 1: Enhance General Reasoning (Priority 1)

**Goal**: Improve the core reasoning pipeline to handle general reasoning tasks better.

#### 1.1 Integrate Existing Reasoning Modules

- **File**: `mavaia_core/brain/modules/custom_reasoning_networks.py`
- **Action**: Add module registry integration to access:
- `reasoning` module for structured reasoning
- `chain_of_thought` module for multi-step reasoning
- `logical_deduction` module for formal logic
- **Implementation**: 
- Add lazy imports of `ModuleRegistry` in `__init__`
- Create `_get_reasoning_module()` helper method
- Route appropriate operations to specialized modules

#### 1.2 Enhance Text Generation with Real Reasoning

- **File**: `mavaia_core/brain/modules/custom_reasoning_networks.py`
- **Method**: `_generate_text_from_embeddings()`
- **Action**: 
- Instead of placeholder responses, call actual reasoning modules
- Use reasoning results to inform text generation
- Extract conclusions and key insights from reasoning outputs
- Format responses based on reasoning type and task requirements

#### 1.3 Improve Multi-Step Reasoning Pipeline

- **File**: `mavaia_core/brain/modules/custom_reasoning_networks.py`
- **Method**: `_multi_step_reasoning()`
- **Action**:
- Before generating text, attempt to solve using `reasoning.multi_step_solve()`
- Use neural embeddings to guide reasoning, not replace it
- Combine symbolic reasoning results with neural insights
- Return structured reasoning steps along with final answer

### Phase 2: Add Puzzle-Solving Capabilities (Priority 2)

**Goal**: Solve constraint satisfaction problems like zebra puzzles.

#### 2.1 Create Puzzle Parser

- **File**: `mavaia_core/brain/modules/custom_reasoning_networks.py`
- **Method**: `_parse_puzzle_constraints()`
- **Action**:
- Parse puzzle text to extract entities, relationships, and constraints
- Identify puzzle type (zebra, web_of_lies, etc.)
- Extract constraint statements (e.g., "The person in the red house drinks coffee")
- Convert to structured constraint format

#### 2.2 Integrate Symbolic Solver for Puzzles

- **File**: `mavaia_core/brain/modules/custom_reasoning_networks.py`
- **Method**: `_solve_puzzle_with_solver()`
- **Action**:
- Use `symbolic_solver` module for constraint satisfaction
- Convert parsed constraints to Z3/PySAT format
- Solve constraint satisfaction problem
- Extract solution and format for LiveBench evaluation

#### 2.3 Zebra Puzzle Specific Solver

- **File**: `mavaia_core/brain/modules/custom_reasoning_networks.py`
- **Method**: `_solve_zebra_puzzle()`
- **Action**:
- Parse zebra puzzle constraints (houses, colors, nationalities, drinks, pets)
- Create constraint satisfaction problem
- Use symbolic solver to find valid assignment
- Extract answers to specific questions (who, what, where)
- Format as `<solution>answer1, answer2, answer3</solution>`

### Phase 3: Implement Smart Routing (Priority 3)

**Goal**: Route tasks to the most appropriate reasoning method.

#### 3.1 Task Type Detection

- **File**: `mavaia_core/brain/modules/custom_reasoning_networks.py`
- **Method**: `_detect_reasoning_type()`
- **Action**:
- Analyze task type and question content
- Classify as: puzzle, math, logical_deduction, multi_step, causal, analogical
- Return recommended reasoning approach

#### 3.2 Routing Logic

- **File**: `mavaia_core/brain/modules/custom_reasoning_networks.py`
- **Method**: `execute()` - enhance routing
- **Action**:
- Detect reasoning type
- Route to appropriate method:
- `zebra_puzzle` → `_solve_zebra_puzzle()`
- `web_of_lies` → `_solve_puzzle_with_solver()`
- `math` → `_solve_math_problem()`
- `logical_deduction` → `logical_deduction` module
- `multi_step` → `chain_of_thought` module
- `general` → enhanced `_multi_step_reasoning()`

#### 3.3 Fallback Chain

- **File**: `mavaia_core/brain/modules/custom_reasoning_networks.py`
- **Action**: Implement fallback if primary method fails:

1. Try specialized solver
2. Try general reasoning module
3. Try neural reasoning
4. Return structured error with reasoning attempt

### Phase 4: Enhance Neural Reasoning (Priority 4)

**Goal**: Improve the neural components to work better with symbolic reasoning.

#### 4.1 Better Embedding Usage

- **File**: `mavaia_core/brain/modules/custom_reasoning_networks.py`
- **Method**: `_get_embeddings()`
- **Action**:
- Use embeddings to extract key concepts and relationships
- Identify entities and their attributes
- Guide constraint extraction for puzzles
- Inform reasoning module selection

#### 4.2 Hybrid Reasoning

- **File**: `mavaia_core/brain/modules/custom_reasoning_networks.py`
- **Method**: `_hybrid_reasoning()`
- **Action**:
- Combine neural embeddings with symbolic reasoning
- Use embeddings to identify relevant information
- Use symbolic reasoning to derive conclusions
- Synthesize results into coherent response

## Implementation Details

### Key Files to Modify

1. **`mavaia_core/brain/modules/custom_reasoning_networks.py`**

- Add module registry integration
- Add puzzle parsing and solving methods
- Enhance `_generate_text_from_embeddings()` to use real reasoning
- Add routing logic in `execute()`
- Add constraint satisfaction problem solving

2. **`mavaia_core/evaluation/categories/livebench_tests.py`** (if needed)

- Ensure task information is properly passed to modules
- Verify response formatting matches LiveBench expectations

### Dependencies

- Existing modules: `reasoning`, `symbolic_solver`, `chain_of_thought`, `logical_deduction`
- External: `z3-solver` (for constraint satisfaction), `python-sat` (for SAT solving)

### Testing Strategy

1. Test zebra puzzle solving with actual constraints
2. Test general reasoning tasks with various question types
3. Test routing logic for different task types
4. Verify LiveBench score improvements

## Success Metrics

- **Zebra puzzle score**: Increase from 0% to >50% (target: solve at least 25/50)
- **Overall reasoning score**: Increase from 9% to >30% (target: 60+ passed tests)
- **Response quality**: Responses should contain actual reasoning, not placeholders
- **Puzzle solving**: Should solve constraint satisfaction problems correctly

## Implementation Order

1. **Phase 1.1**: Integrate existing reasoning modules (foundation)
2. **Phase 1.2**: Enhance text generation with real reasoning (immediate impact)
3. **Phase 1.3**: Improve multi-step reasoning pipeline
4. **Phase 2.1-2.2**: Add puzzle parsing and symbolic solver integration
5. **Phase 2.3**: Zebra puzzle specific solver
6. **Phase 3**: Implement smart routing
7. **Phase 4**: Enhance neural reasoning (if time permits)

## Notes

- This is a significant enhancement that transforms the module from placeholder-based to actual reasoning
- The hybrid approach leverages existing powerful modules rather than rebuilding from scratch
- Puzzle-solving is a secondary priority but will have high impact on LiveBench scores
- Smart routing ensures we use the right tool for the right job