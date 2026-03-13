---
name: ARC Reasoning System
overview: Implement a fully functional, production-grade ARC (Abstraction and Reasoning Corpus) solving system with advanced pattern extractors, transformation detectors, rule inference engines, and multi-example learning capabilities.
todos:
  - id: pattern_extractors
    content: "Implement enhanced pattern extractors: shape detection, color analysis, adjacency detection, repetition detection (enhance existing), geometry analysis"
    status: completed
  - id: transformation_detectors
    content: "Implement complete transformation detectors: advanced rotation, advanced reflection, translation, advanced scaling, advanced color mapping, grid expansion, object duplication, pattern continuation"
    status: completed
  - id: rule_inference
    content: "Implement robust rule inference engines: fill rules, extension rules, repetition rules, transformation consistency"
    status: completed
    dependencies:
      - pattern_extractors
      - transformation_detectors
  - id: multi_example_learning
    content: "Implement multi-example transformation inference: example analyzer, transformation generalizer, test grid solver, enhanced ARC task solver"
    status: completed
    dependencies:
      - pattern_extractors
      - transformation_detectors
      - rule_inference
  - id: grid_parsing
    content: "Implement grid parsing and format handling: parse from text, validate grids, handle both JSON and text formats"
    status: completed
  - id: integration
    content: "Integrate all components: enhance existing methods, replace with new implementations, update execute() routing"
    status: completed
    dependencies:
      - pattern_extractors
      - transformation_detectors
      - rule_inference
      - multi_example_learning
      - grid_parsing
  - id: testing
    content: "Create comprehensive tests: unit tests for each component, integration tests, end-to-end tests with real ARC problems"
    status: completed
    dependencies:
      - integration
---

# ARC Reasoning System Implementation Plan

## Overview

Enhance the existing ARC solving infrastructure in `custom_reasoning_networks.py` with production-grade pattern extraction, transformation detection, rule inference, and multi-example learning. The implementation will handle both JSON grid arrays and text descriptions.

## Architecture

The system will be organized into four main components:

1. **Pattern Extractors** - Detect shapes, colors, adjacency, repetition, geometry
2. **Transformation Detectors** - Identify rotations, reflections, translations, scaling, color mappings, grid expansions, object duplication, pattern continuation
3. **Rule Inference Engines** - Infer rules for filling cells, extending patterns, repeating sequences, applying transformations
4. **Multi-Example Learner** - Generalize from input→output pairs and apply to test grids

## Implementation Details

### 1. Enhanced Pattern Extractors

**File**: `oricli_core/brain/modules/custom_reasoning_networks.py`

#### 1.1 Shape Detection (`_detect_shapes`)

- Detect connected components using flood fill
- Classify shapes: rectangles, lines, circles, polygons, irregular shapes
- Extract shape properties: bounding box, area, perimeter, centroid
- Handle overlapping and nested shapes
- Return: List of shape dictionaries with type, bounds, cells, properties

#### 1.2 Color Analysis (`_analyze_colors`)

- Extract all unique colors in grid
- Detect color patterns (gradients, alternations, groupings)
- Identify color relationships (complementary, sequential, categorical)
- Map color distributions across grid
- Return: Color analysis dictionary with sets, patterns, relationships

#### 1.3 Adjacency Detection (`_detect_adjacency`)

- Build adjacency graphs for all non-zero cells
- Detect connected regions (4-connected, 8-connected)
- Identify neighbor relationships (immediate, diagonal, distant)
- Calculate distances between objects
- Return: Adjacency graph and region maps

#### 1.4 Repetition Detection (`_detect_repetition`)

- Find repeating patterns (horizontal, vertical, diagonal, tiled)
- Detect sequences and progressions
- Identify periodic structures
- Handle irregular repetitions
- Return: List of repetition patterns with type, period, extent

#### 1.5 Geometry Analysis (`_analyze_geometry`)

- Detect symmetry (horizontal, vertical, rotational, diagonal)
- Analyze alignment (rows, columns, diagonals)
- Calculate spacing and gaps
- Identify geometric relationships (parallel, perpendicular, collinear)
- Return: Geometry analysis with symmetry axes, alignments, relationships

### 2. Complete Transformation Detectors

**File**: `oricli_core/brain/modules/custom_reasoning_networks.py`

#### 2.1 Enhanced Rotation Detection (`_detect_rotation_advanced`)

- Detect rotations: 90°, 180°, 270°, and arbitrary angles
- Handle rotation around different centers
- Detect partial rotations (sub-grid rotations)
- Return: Rotation transformation with angle, center, affected regions

#### 2.2 Enhanced Reflection Detection (`_detect_reflection_advanced`)

- Detect horizontal, vertical, diagonal reflections
- Handle reflections across arbitrary axes
- Detect partial reflections
- Return: Reflection transformation with axis, affected regions

#### 2.3 Translation Detection (`_detect_translation`)

- Detect shifts and moves (horizontal, vertical, diagonal)
- Handle multiple simultaneous translations
- Detect translation patterns
- Return: Translation transformation with direction, distance, objects

#### 2.4 Enhanced Scaling Detection (`_detect_scaling_advanced`)

- Detect uniform and non-uniform scaling
- Handle scaling around different centers
- Detect partial scaling (sub-grid scaling)
- Return: Scaling transformation with factors, center, affected regions

#### 2.5 Color Mapping Detection (`_detect_color_mapping_advanced`)

- Detect direct color mappings
- Infer pattern-based mappings (arithmetic, modulo, lookup tables)
- Handle conditional color mappings
- Detect color transformations (inversion, shifts, gradients)
- Return: Color mapping with type, mapping function, conditions

#### 2.6 Grid Expansion Detection (`_detect_grid_expansion`)

- Detect size changes (grow, shrink, pad, crop)
- Identify expansion patterns (uniform, directional, selective)
- Detect padding strategies (zeros, borders, patterns)
- Return: Expansion transformation with type, dimensions, padding

#### 2.7 Object Duplication Detection (`_detect_duplication`)

- Detect copying and tiling operations
- Identify duplication patterns (grid, sequence, random)
- Handle transformations during duplication
- Return: Duplication transformation with source, pattern, count

#### 2.8 Pattern Continuation Detection (`_detect_continuation`)

- Detect pattern extensions (linear, exponential, periodic)
- Identify continuation directions (horizontal, vertical, diagonal)
- Handle complex continuation rules
- Return: Continuation transformation with pattern, direction, rule

### 3. Robust Rule Inference Engines

**File**: `oricli_core/brain/modules/custom_reasoning_networks.py`

#### 3.1 Fill Empty Cells Engine (`_infer_fill_rules`)

- Infer fill patterns from examples
- Detect fill strategies (color, pattern, shape-based)
- Handle conditional filling
- Apply fills consistently across examples
- Return: Fill rules with strategy, pattern, conditions

#### 3.2 Extend Patterns Engine (`_infer_extension_rules`)

- Infer extension patterns (linear, geometric, periodic)
- Detect extension directions and rules
- Handle multi-directional extensions
- Apply extensions consistently
- Return: Extension rules with pattern, direction, rule function

#### 3.3 Repeat Sequences Engine (`_infer_repetition_rules`)

- Infer repetition patterns from examples
- Detect repetition types (tile, sequence, transform-repeat)
- Handle nested repetitions
- Apply repetitions consistently
- Return: Repetition rules with pattern, type, count, transform

#### 3.4 Transformation Consistency Engine (`_infer_transformation_consistency`)

- Analyze transformations across multiple examples
- Identify consistent transformation patterns
- Handle transformation sequences
- Apply transformations in correct order
- Return: Transformation sequence with order, consistency score

### 4. Multi-Example Transformation Inference

**File**: `oricli_core/brain/modules/custom_reasoning_networks.py`

#### 4.1 Example Analyzer (`_analyze_examples`)

- Process multiple input→output pairs
- Extract common patterns across examples
- Identify consistent transformations
- Detect conflicting examples
- Return: Analysis with common patterns, transformations, conflicts

#### 4.2 Transformation Generalizer (`_generalize_transformations`)

- Generalize transformations from examples
- Build transformation models
- Handle transformation combinations
- Prioritize transformations by consistency
- Return: Generalized transformation model

#### 4.3 Test Grid Solver (`_solve_test_grid`)

- Apply generalized transformations to test input
- Handle multiple candidate solutions
- Validate solutions against learned patterns
- Return: Predicted output grid with confidence

#### 4.4 Enhanced ARC Task Solver (`_solve_arc_task_enhanced`)

- Integrate all components
- Process multiple examples
- Generalize rules and transformations
- Solve test grids
- Return: Solution with predicted output, reasoning, confidence

### 5. Enhanced Grid Parsing and Format Handling

**File**: `oricli_core/brain/modules/custom_reasoning_networks.py`

#### 5.1 Grid Parser (`_parse_grid_from_text`)

- Parse grids from text descriptions
- Handle multiple formats (JSON, arrays, visual representations)
- Validate grid structure
- Return: Parsed grid array

#### 5.2 Grid Validator (`_validate_grid`)

- Validate grid structure and values
- Check for consistency
- Handle edge cases
- Return: Validation result with errors/warnings

## Key Methods to Enhance/Replace

1. **`_extract_arc_patterns`** - Enhance with new pattern extractors
2. **`_detect_arc_transformations`** - Replace with comprehensive transformation detectors
3. **`_infer_arc_rules`** - Enhance with robust rule inference
4. **`_solve_arc_task`** - Replace with enhanced multi-example solver
5. **`_apply_arc_transformations`** - Enhance to handle all transformation types

## New Methods to Add

- `_detect_shapes()` - Shape detection
- `_analyze_colors()` - Color analysis
- `_detect_adjacency()` - Adjacency detection
- `_detect_repetition()` - Repetition detection (enhance existing)
- `_analyze_geometry()` - Geometry analysis
- `_detect_rotation_advanced()` - Advanced rotation detection
- `_detect_reflection_advanced()` - Advanced reflection detection
- `_detect_translation()` - Translation detection
- `_detect_scaling_advanced()` - Advanced scaling detection
- `_detect_color_mapping_advanced()` - Advanced color mapping
- `_detect_grid_expansion()` - Grid expansion detection
- `_detect_duplication()` - Object duplication detection
- `_detect_continuation()` - Pattern continuation detection
- `_infer_fill_rules()` - Fill rules inference
- `_infer_extension_rules()` - Extension rules inference
- `_infer_repetition_rules()` - Repetition rules inference
- `_infer_transformation_consistency()` - Transformation consistency
- `_analyze_examples()` - Multi-example analysis
- `_generalize_transformations()` - Transformation generalization
- `_solve_test_grid()` - Test grid solving
- `_solve_arc_task_enhanced()` - Enhanced ARC task solver
- `_parse_grid_from_text()` - Grid parsing from text
- `_validate_grid()` - Grid validation

## Testing Strategy

1. Unit tests for each pattern extractor
2. Unit tests for each transformation detector
3. Unit tests for rule inference engines
4. Integration tests for multi-example learning
5. End-to-end tests with real ARC problems
6. Performance benchmarks

## Success Criteria

1. All pattern extractors detect patterns correctly
2. All transformation types are detected accurately
3. Rules are inferred correctly from examples
4. Multi-example learning generalizes properly
5. Test grids are solved with high accuracy
6. Handles both JSON and text input formats
7. Production-grade error handling and validation
8. Comprehensive logging and debugging support