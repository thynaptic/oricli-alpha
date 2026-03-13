# ARC Induction-Transduction Ensemble System Implementation Plan

Based on: "Combining Induction and Transduction for Abstract Reasoning" (arxiv:2411.02272)

## Paper Summary

The paper demonstrates that:

1. **Induction** (program synthesis) excels at precise computations and composing multiple concepts
2. **Transduction** (neural direct prediction) succeeds on fuzzier perceptual concepts
3. **Ensemble** of both approaches approaches human-level performance on ARC
4. Neural models trained on synthetic Python program solutions can learn both approaches
5. Data augmentation and test-time training significantly improve transduction performance

## Architecture Overview

### Current State

Mavaia already has:

- ✅ ARC pattern extraction and transformation detection
- ✅ Program synthesis capabilities (`reasoning_code_generator`)
- ✅ Multi-example learning for ARC tasks
- ✅ Transformation inference and rule generalization

### What We're Adding

1. **Neural Transduction Model** - Direct grid-to-grid prediction
2. **Enhanced Induction** - Neural-guided program synthesis
3. **Data Augmentation Pipeline** - For transduction training and inference
4. **Reranking System** - Aggregating multiple predictions
5. **Test-Time Training** - Fine-tuning at inference
6. **Ensemble Framework** - Combining induction and transduction
7. **Synthetic Data Generator** - Creating training data from existing solutions

## Implementation Details

### 1. Neural Transduction Model

**File**: `oricli_core/brain/modules/arc_transduction_model.py`

**Purpose**: Direct neural prediction of output grids from training input-output pairs

**Operations**:

- `predict_transduction(train_examples, test_input)` - Direct prediction
- `train_transduction(train_data)` - Fine-tune model
- `test_time_tune(task_examples)` - Test-time fine-tuning

**Architecture**:

- Transformer-based encoder-decoder or CNN-based architecture
- Input: Training examples (x_train, y_train) + test input (x_test)
- Output: Predicted test output (y_test)
- Uses grid embeddings and attention mechanisms

**Key Methods**:

```python
class ARCTransductionModel:
    def __init__(self):
        # Neural model for direct grid prediction
        self.model = None  # Transformer or CNN architecture
        self.embedding_dim = 256
        self.grid_encoder = None  # Encodes grids to embeddings
        
    def encode_grid(self, grid: np.ndarray) -> np.ndarray:
        """Encode grid to embedding representation"""
        pass
    
    def predict(self, train_examples: List[Tuple], test_input: np.ndarray) -> np.ndarray:
        """Directly predict test output without program synthesis"""
        pass
    
    def train_on_batch(self, batch: List[Tuple]) -> Dict[str, float]:
        """Train model on batch of examples"""
        pass
```

### 2. Enhanced Induction (Program Synthesis)

**File**: `oricli_core/brain/modules/custom_reasoning_networks.py` (enhance existing)

**Enhancements**:

- Add neural guidance to program synthesis
- Generate Python functions that solve ARC tasks
- Use LLM or neural model to generate program code
- Execute programs and validate against training examples

**New Methods**:

```python
def _synthesize_program_inductive(
    self, 
    train_examples: List[Tuple[np.ndarray, np.ndarray]]
) -> str:
    """
    Synthesize Python program that solves ARC task from examples.
    Uses neural model or LLM to generate code.
    """
    pass

def _execute_program_on_test(
    self, 
    program_code: str, 
    test_input: np.ndarray
) -> np.ndarray:
    """Execute synthesized program on test input"""
    pass
```

### 3. Data Augmentation Pipeline

**File**: `oricli_core/brain/modules/arc_data_augmentation.py`

**Transformations**:

1. **Transposition**: `T_t(x) = x^T` (flip rows/columns)
2. **Color Permutation**: Random permutation of color values (0-9)
3. **Rotation**: 90°, 180°, 270° rotations
4. **Inverse transformations**: Apply T^-1 to predictions

**Operations**:

- `augment_task(task)` - Apply transformations to ARC task
- `apply_inverse_transform(prediction, transform)` - Revert transformation
- `generate_augmented_predictions(model, task, transforms)` - Get predictions for each transformation

**Key Methods**:

```python
class ARCDataAugmentation:
    def transpose_task(self, task: ARCTask) -> ARCTask:
        """Apply transposition transformation"""
        pass
    
    def permute_colors(self, task: ARCTask, permutation: Dict[int, int]) -> ARCTask:
        """Apply color permutation"""
        pass
    
    def rotate_task(self, task: ARCTask, degrees: int) -> ARCTask:
        """Rotate task by degrees"""
        pass
    
    def generate_transformations(self) -> List[Callable]:
        """Generate list of transformation functions"""
        pass
```

### 4. Reranking System

**File**: `oricli_core/brain/modules/arc_reranking.py`

**Purpose**: Aggregate and rank predictions from multiple transformations

**Method**:

- For each transformation T, get beam search predictions
- Score each candidate: `s_T(y) = model_score(T(y) | T(x_train), T(y_train))`
- Aggregate by frequency and average score
- Rank: frequency first, then average score

**Operations**:

- `rerank_predictions(predictions, scores)` - Aggregate and rank
- `compute_frequency_scores(candidates)` - Count appearances
- `compute_average_scores(candidates, scores)` - Average beam scores

**Key Methods**:

```python
class ARCReranking:
    def rerank(
        self,
        candidates: List[np.ndarray],
        scores: Dict[str, float],
        frequency_priority: bool = True
    ) -> List[Tuple[np.ndarray, float]]:
        """
        Rerank candidates by frequency and average score.
        Returns sorted list of (candidate, score) tuples.
        """
        pass
    
    def aggregate_across_transformations(
        self,
        transformation_results: Dict[str, List[Tuple[np.ndarray, float]]]
    ) -> List[Tuple[np.ndarray, float]]:
        """Aggregate results from multiple transformations"""
        pass
```

### 5. Test-Time Training

**File**: `oricli_core/brain/modules/arc_test_time_training.py`

**Purpose**: Fine-tune transduction model at test time using augmented examples

**Method**:

- Use test task training examples as pseudo-training data
- For each training example, treat it as a "fake test case"
- Apply data augmentation
- Train model to predict the selected example from others
- Does not require ground truth test output

**Operations**:

- `test_time_train(model, task, iterations)` - Fine-tune on task
- `create_pseudo_tasks(task, augmentation_fn)` - Generate augmented tasks
- `compute_test_time_loss(model, pseudo_task)` - Compute training loss

**Key Methods**:

```python
class ARCTestTimeTraining:
    def create_pseudo_tasks(
        self,
        task: ARCTask,
        augmentation_fn: Callable,
        n_augmentations: int = 10
    ) -> List[ARCTask]:
        """
        Create pseudo-training tasks by treating each example as test case.
        """
        pass
    
    def test_time_train(
        self,
        model: ARCTransductionModel,
        task: ARCTask,
        epochs: int = 3,
        learning_rate: float = 2e-4
    ) -> ARCTransductionModel:
        """Fine-tune model on task at test time"""
        pass
```

### 6. Ensemble System

**File**: `oricli_core/brain/modules/arc_ensemble.py`

**Purpose**: Combine induction and transduction predictions intelligently

**Strategy**:

1. Try induction first (program synthesis)
2. If induction fails or times out, use transduction
3. Can also ensemble both predictions using voting or confidence weighting
4. Use induction for precise/computational tasks
5. Use transduction for perceptual/fuzzy tasks

**Operations**:

- `ensemble_predict(task, compute_budget)` - Combined prediction
- `select_method(task, characteristics)` - Choose best method
- `combine_predictions(inductive_pred, transductive_pred)` - Merge results

**Key Methods**:

```python
class ARCEnsemble:
    def __init__(self, induction_model, transduction_model):
        self.induction = induction_model
        self.transduction = transduction_model
    
    def predict(
        self,
        task: ARCTask,
        max_induction_attempts: int = 1,
        fallback_to_transduction: bool = True
    ) -> Dict[str, Any]:
        """
        Ensemble prediction: try induction first, fallback to transduction.
        """
        pass
    
    def combine_predictions(
        self,
        inductive_pred: np.ndarray,
        transductive_pred: np.ndarray,
        method: str = "confidence_weighted"
    ) -> np.ndarray:
        """Combine predictions from both methods"""
        pass
```

### 7. Synthetic Data Generator

**File**: `oricli_core/brain/modules/arc_synthetic_data.py`

**Purpose**: Generate synthetic ARC problems from existing Python solutions

**Method** (from paper):

1. Start with 100-160 program solutions for ARC training tasks
2. For each program f, create probabilistic input generator
3. Generate input-output pairs by executing f on sampled inputs
4. Creates 400k+ synthetic problems

**Operations**:

- `generate_from_program(program_code, n_examples)` - Generate examples
- `sample_inputs(program, n_samples)` - Sample appropriate inputs
- `execute_program(program, inputs)` - Execute to get outputs
- `create_synthetic_task(examples)` - Format as ARC task

**Key Methods**:

```python
class ARCSyntheticDataGenerator:
    def generate_from_program(
        self,
        program_code: str,
        n_examples: int = 5,
        input_generator: Optional[Callable] = None
    ) -> ARCTask:
        """
        Generate synthetic ARC task from Python program.
        Creates appropriate input grids and executes program.
        """
        pass
    
    def sample_inputs(
        self,
        program_code: str,
        n_samples: int,
        constraints: Optional[Dict] = None
    ) -> List[np.ndarray]:
        """Sample appropriate input grids for program"""
        pass
    
    def expand_task_collection(
        self,
        base_tasks: List[ARCTask],
        expansion_factor: int = 10
    ) -> List[ARCTask]:
        """Create variations of existing tasks"""
        pass
```

### 8. Model Training Infrastructure

**File**: `oricli_core/brain/modules/arc_model_training.py`

**Purpose**: Training pipeline for induction and transduction models

**Hyperparameters** (from paper):

**Induction (LLM fine-tuning)**:

- LoRA rank: 64, alpha: 64
- Learning rate: 2e-4
- Batch size: 8 per device, 8 devices
- Epochs: 3
- Full fine-tune (last 230k): lr 1e-5, batch 16, epochs 2

**Transduction**:

- Learning rate: 1e-5
- Weight decay: 1e-2
- Batch size: 8 per device
- Epochs: 2-3
- Beam search: width 3-40

**Test-Time Training**:

- LoRA rank: 64, alpha: 64
- Learning rate: 2e-4
- Batch size: 2 per device
- Epochs: 3

**Operations**:

- `train_induction_model(data_path, output_path)` - Train program synthesis
- `train_transduction_model(data_path, output_path)` - Train direct prediction
- `fine_tune_on_task(model, task)` - Test-time fine-tuning

## Integration Points

### Module: `custom_reasoning_networks.py`

Add new operation to `execute()`:

```python
case "solve_arc_ensemble":
    return self._solve_arc_ensemble(params)
```

Method:

```python
def _solve_arc_ensemble(self, params: Dict[str, Any]) -> Dict[str, Any]:
    """
    Solve ARC task using ensemble of induction and transduction.
    
    Args:
        train_examples: List of (input_grid, output_grid) tuples
        test_input: Test input grid
        method: "auto", "induction", "transduction", "ensemble"
        use_augmentation: Whether to use data augmentation
        use_test_time_training: Whether to use test-time training
        
    Returns:
        Dictionary with predicted output and metadata
    """
    pass
```

## Testing Strategy

1. **Unit Tests**:

   - Test each component individually
   - Test transformations and inverses
   - Test reranking logic

2. **Integration Tests**:

   - Test full ensemble pipeline
   - Test with real ARC tasks
   - Test fallback mechanisms

3. **Evaluation**:

   - Compare induction vs transduction on ARC test set
   - Measure ensemble improvements
   - Evaluate augmentation impact

## Success Metrics

- **Induction accuracy**: Measure program synthesis success rate
- **Transduction accuracy**: Measure direct prediction accuracy
- **Ensemble accuracy**: Combined performance
- **Coverage**: Problems solved by each method
- **Complementarity**: Overlap vs unique solutions

## Implementation Order

1. **Phase 1**: Synthetic data generator (foundation)
2. **Phase 2**: Data augmentation pipeline
3. **Phase 3**: Neural transduction model
4. **Phase 4**: Enhanced induction (program synthesis)
5. **Phase 5**: Reranking system
6. **Phase 6**: Test-time training
7. **Phase 7**: Ensemble framework
8. **Phase 8**: Training infrastructure and fine-tuning

## References

- Paper: https://arxiv.org/pdf/2411.02272
- ARC Dataset: https://github.com/fchollet/ARC
- Implementation details from paper sections 2-3 and appendices E-G