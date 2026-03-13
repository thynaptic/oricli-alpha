---
name: PyTorch to JAX Migration
overview: Migrate from PyTorch to JAX/Flax to resolve Python 3.14 compatibility issues. This involves replacing PyTorch neural network implementations with JAX/Flax equivalents across 7+ modules, updating dependencies, and adapting Transformers library usage to Flax backend.
todos:
  - id: update_dependencies
    content: "Update pyproject.toml: Replace torch with jax, jaxlib, flax, optax. Update transformers to ensure Flax support. Handle sentence-transformers replacement."
    status: pending
  - id: migrate_plan_optimizer
    content: "Migrate plan_optimizer.py: Convert PlanScorer to Flax module, replace torch operations with JAX, update training loop, update model saving/loading."
    status: pending
  - id: migrate_tool_routing
    content: "Migrate tool_routing_model.py: Convert ToolSelectionModel to Flax, replace sentence-transformers with Flax embeddings, update all torch operations."
    status: pending
  - id: migrate_custom_reasoning
    content: "Migrate custom_reasoning_networks.py: Convert all network classes to Flax, replace transformers with Flax backend, update transformer layers."
    status: pending
  - id: migrate_gradient_optimizer
    content: "Migrate gradient_plan_optimizer.py: Convert DifferentiablePlanner to Flax, replace embeddings and transformer layers, update gradient computation."
    status: pending
  - id: migrate_nas
    content: "Migrate neural_architecture_search.py: Update model building to Flax, replace training/evaluation with JAX functional API."
    status: pending
  - id: migrate_rl_agent
    content: "Migrate reinforcement_learning_agent.py: Convert PolicyNetwork and ValueNetwork to Flax, replace distributions with distrax, update PPO algorithm."
    status: pending
  - id: update_model_manager
    content: "Update model_manager.py: Add Flax model loading support, update model initialization for Flax backend."
    status: pending
  - id: update_embeddings
    content: "Update embeddings.py and related modules: Replace sentence-transformers with Flax-based embeddings using transformers Flax backend."
    status: pending
  - id: update_transformers_modules
    content: "Update lora_loader.py, lora_inference.py, style_transfer.py, model_optimizer.py: Switch to Flax backend where possible, add fallbacks."
    status: pending
  - id: test_migration
    content: "Create comprehensive tests: Unit tests for each migrated module, integration tests, performance benchmarks, Python 3.14 compatibility verification."
    status: pending
---

# PyTorch to JAX Migration Plan

## Analysis Summary

**Current State:**

- Python 3.14.0 in use
- PyTorch runtime errors on Python 3.14
- 7+ modules using PyTorch for neural networks:
  - `reinforcement_learning_agent.py` - PPO agent
  - `plan_optimizer.py` - Plan scoring network
  - `tool_routing_model.py` - Tool selection network
  - `custom_reasoning_networks.py` - Multi-step reasoning architectures
  - `gradient_plan_optimizer.py` - Differentiable planner
  - `neural_architecture_search.py` - NAS with PyTorch models
  - `python_code_embeddings.py` - Code embeddings (optional)
- Heavy use of HuggingFace Transformers (PyTorch-based)
- Sentence Transformers for embeddings (PyTorch-only)

**Decision: JAX/Flax**

- JAX has confirmed Python 3.14 support (45-month policy)
- Better performance for research/experimentation
- Flax provides PyTorch-like API
- Transformers library supports Flax backend
- Optax provides optimization (replaces torch.optim)

## Migration Strategy

### Phase 1: Dependency Updates

**Files to modify:**

- `pyproject.toml` - Update ML dependencies

**Changes:**

1. Replace `torch>=2.0.0` with:

   - `jax>=0.4.20`
   - `jaxlib>=0.4.20`
   - `flax>=0.7.0`
   - `optax>=0.1.7`

2. Keep `transformers>=4.30.0` (supports Flax backend)
3. Replace `sentence-transformers` with Flax-compatible alternative:

   - Option A: Use Transformers library with Flax models directly
   - Option B: Use `jax-sentence-transformers` if available
   - Option C: Implement custom embedding using Flax models

### Phase 2: Core Module Migrations

#### 2.1 Plan Optimizer Module

**File:** `oricli_core/brain/modules/plan_optimizer.py`

**Changes:**

- Replace `torch.nn.Module` → `flax.linen.Module`
- Replace `torch.nn.Linear` → `flax.linen.Dense`
- Replace `torch.nn.Sequential` → Flax `nn.Sequential` or custom `@nn.compact`
- Replace `torch.optim.Adam` → `optax.adam`
- Replace `torch.Tensor` → `jax.numpy.ndarray`
- Replace `torch.no_grad()` → `jax.disable_jit()` or remove (JAX is functional)
- Replace `model.eval()` → Remove (JAX uses functional API)
- Replace `model.train()` → Remove (JAX uses functional API)
- Replace `torch.save()`/`torch.load()` → Use `flax.serialization` or `pickle`
- Replace device management (`cuda`, `mps`, `cpu`) → JAX device placement
- Update forward pass to use `@nn.compact` decorator pattern

**Key patterns:**

```python
# PyTorch
class PlanScorer(nn.Module):
    def __init__(self, ...):
        self.encoder = nn.Sequential(...)
    
    def forward(self, x):
        return self.encoder(x)

# Flax
class PlanScorer(nn.Module):
    @nn.compact
    def __call__(self, x):
        x = nn.Dense(128)(x)
        x = nn.relu(x)
        return x
```

#### 2.2 Tool Routing Model

**File:** `oricli_core/brain/modules/tool_routing_model.py`

**Changes:**

- Same core changes as Plan Optimizer
- Replace `sentence_transformers.SentenceTransformer` with Flax-based embedding:
  - Use `transformers.FlaxAutoModel` for embeddings
  - Or implement custom embedding using Flax models
- Update embedding model loading to use Flax backend
- Replace `model.encode()` → Custom embedding function using Flax model

#### 2.3 Reinforcement Learning Agent

**File:** `oricli_core/brain/modules/reinforcement_learning_agent.py`

**Changes:**

- Convert `PolicyNetwork` and `ValueNetwork` to Flax modules
- Replace `torch.distributions` → `jax.scipy.stats` or `distrax`
- Replace `torch.optim.Adam` → `optax.adam`
- Replace PPO loss computation to use JAX operations
- Update action sampling to use JAX random functions
- Replace device management with JAX device placement
- Update state dict saving/loading to Flax serialization

**Additional dependency:** `distrax>=0.4.0` for distributions

#### 2.4 Custom Reasoning Networks

**File:** `oricli_core/brain/modules/custom_reasoning_networks.py`

**Changes:**

- Convert all network classes to Flax:
  - `MultiStepReasoningNetwork`
  - `CausalInferenceModule`
  - `AnalogicalReasoningNetwork`
  - `ReasoningEnsemble`
- Replace `nn.TransformerEncoderLayer` → `flax.linen.TransformerEncoderLayer` or custom implementation
- Replace `nn.MultiheadAttention` → `flax.linen.MultiHeadAttention`
- Update lazy loading to check for JAX/Flax instead of PyTorch
- Replace `transformers.AutoModel` → `transformers.FlaxAutoModel` where used

#### 2.5 Gradient Plan Optimizer

**File:** `oricli_core/brain/modules/gradient_plan_optimizer.py`

**Changes:**

- Convert `DifferentiablePlanner` to Flax module
- Replace `nn.Embedding` → `flax.linen.Embed`
- Replace `nn.TransformerDecoder` → Flax transformer decoder
- Replace `nn.MultiheadAttention` → `flax.linen.MultiHeadAttention`
- Update gradient-based optimization to use JAX `jax.grad` or `optax`
- Replace sentence transformer usage with Flax-based embeddings

#### 2.6 Neural Architecture Search

**File:** `oricli_core/brain/modules/neural_architecture_search.py`

**Changes:**

- Update `build_model_from_candidate()` to build Flax modules
- Replace PyTorch model building with Flax module construction
- Update model evaluation to use JAX functional API
- Replace model training to use Flax training loop
- Update model serialization to Flax format

#### 2.7 Python Code Embeddings

**File:** `oricli_core/brain/modules/python_code_embeddings.py`

**Changes:**

- Make PyTorch usage optional (already has fallback)
- Add JAX/Flax option for code embeddings
- Use `transformers.FlaxAutoModel` for code models if available
- Keep fallback hash-based embeddings

### Phase 3: Supporting Infrastructure

#### 3.1 Model Manager

**File:** `oricli_core/brain/modules/model_manager.py`

**Changes:**

- Add Flax model loading support alongside PyTorch
- Update model loading to detect and use Flax backend
- Add Flax model caching
- Update model initialization to support Flax models

#### 3.2 Embeddings Module

**File:** `oricli_core/brain/modules/embeddings.py`

**Changes:**

- Replace `sentence-transformers` with Flax-based solution
- Use `transformers.FlaxAutoModel` for sentence embeddings
- Implement custom embedding function using Flax models
- Maintain API compatibility

#### 3.3 Other Modules Using Transformers

**Files:**

- `lora_loader.py`
- `lora_inference.py`
- `style_transfer.py`
- `model_optimizer.py`

**Changes:**

- Update to use Flax backend for Transformers where possible
- Add fallback handling for modules that require PyTorch-specific features
- Use `transformers.FlaxAutoModel*` classes

### Phase 4: Testing & Validation

1. **Unit Tests:**

   - Test each migrated module independently
   - Verify model forward passes
   - Verify training loops
   - Verify model saving/loading

2. **Integration Tests:**

   - Test module interactions
   - Test end-to-end workflows
   - Verify performance characteristics

3. **Compatibility Tests:**

   - Test on Python 3.14
   - Verify JAX installation and functionality
   - Test Transformers Flax backend

## Implementation Details

### Key JAX/Flax Patterns

**Module Definition:**

```python
import flax.linen as nn
import jax.numpy as jnp

class MyModule(nn.Module):
    features: int = 128
    
    @nn.compact
    def __call__(self, x):
        x = nn.Dense(self.features)(x)
        x = nn.relu(x)
        return x
```

**Training Loop:**

```python
import optax

optimizer = optax.adam(learning_rate=1e-3)
opt_state = optimizer.init(params)

def loss_fn(params, x, y):
    pred = model.apply({'params': params}, x)
    return jnp.mean((pred - y) ** 2)

grad_fn = jax.grad(loss_fn)
for step in range(epochs):
    grads = grad_fn(params, x, y)
    updates, opt_state = optimizer.update(grads, opt_state)
    params = optax.apply_updates(params, updates)
```

**Model Saving/Loading:**

```python
from flax import serialization

# Save
bytes_output = serialization.to_bytes(params)
with open('model.flax', 'wb') as f:
    f.write(bytes_output)

# Load
with open('model.flax', 'rb') as f:
    params = serialization.from_bytes(params, f.read())
```

### Device Management

JAX handles devices differently:

```python
import jax

# Get default device
device = jax.devices()[0]  # Usually CPU or GPU

# Place computation on device
result = jax.device_put(data, device)

# For multi-device (if needed)
devices = jax.devices()
```

### Transformers Flax Backend

```python
from transformers import FlaxAutoModel, FlaxAutoTokenizer

model = FlaxAutoModel.from_pretrained("model-name")
tokenizer = FlaxAutoTokenizer.from_pretrained("model-name")

# Get embeddings
inputs = tokenizer(text, return_tensors="jax")
outputs = model(**inputs)
embeddings = outputs.last_hidden_state
```

## Migration Order

1. **Dependencies** (pyproject.toml) - Update package requirements
2. **Plan Optimizer** - Simplest module, good starting point
3. **Tool Routing** - Similar complexity, tests embedding integration
4. **Custom Reasoning** - More complex, tests transformer integration
5. **Gradient Plan Optimizer** - Complex differentiable planning
6. **Neural Architecture Search** - Dynamic model building
7. **Reinforcement Learning** - Most complex, requires distribution handling
8. **Supporting Modules** - Embeddings, model manager, etc.

## Risk Mitigation

1. **Backward Compatibility:**

   - Keep PyTorch imports as optional fallback initially
   - Add feature flags to switch between backends
   - Maintain API compatibility

2. **Testing:**

   - Test each module after migration
   - Compare outputs between PyTorch and JAX versions
   - Performance benchmarking

3. **Rollback Plan:**

   - Keep PyTorch code in git history
   - Use feature flags for gradual rollout
   - Maintain both backends temporarily if needed

## Estimated Impact

- **Files to modify:** ~15-20 files
- **Lines of code:** ~3000-4000 lines
- **New dependencies:** JAX, JAXlib, Flax, Optax, Distrax (optional)
- **Breaking changes:** Minimal (internal implementation only)
- **Performance:** Expected improvement, especially for research workloads