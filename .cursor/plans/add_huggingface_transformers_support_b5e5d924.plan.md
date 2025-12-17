---
name: Add HuggingFace Transformers Support
overview: Add production-ready HuggingFace Transformers support to the neural text generator module, supporting both fine-tuning and inference for all text generation models. Integrate with existing data sources and arguments while adding transformer-specific configuration.
todos:
  - id: add_transformers_imports
    content: Add optional imports for transformers, torch, and datasets libraries with availability checks
    status: completed
  - id: update_module_structure
    content: Add transformer_model, transformer_tokenizer, and transformer_config attributes to NeuralTextGeneratorModule class
    status: completed
    dependencies:
      - add_transformers_imports
  - id: add_transformer_training
    content: Implement _train_transformer_model() method with fine-tuning support, time limits, and checkpointing
    status: completed
    dependencies:
      - update_module_structure
  - id: add_transformer_generation
    content: Implement _generate_transformer_text() method with configurable generation parameters
    status: completed
    dependencies:
      - update_module_structure
  - id: update_training_flow
    content: Modify _train_model() to handle transformer model type and integrate with existing flow
    status: completed
    dependencies:
      - add_transformer_training
  - id: update_generation_flow
    content: Modify _generate_text() to support transformer model type
    status: completed
    dependencies:
      - add_transformer_generation
  - id: update_model_persistence
    content: Update _load_model() and _save_model() to handle transformer models
    status: completed
    dependencies:
      - add_transformer_training
  - id: update_config_file
    content: Add transformer_model and transformer generation config sections to neural_text_generator_config.json
    status: completed
  - id: update_training_script
    content: Add --model-name and --transformer-config arguments to train_neural_text_generator.py
    status: completed
    dependencies:
      - update_training_flow
  - id: create_transformer_profiles
    content: Create example training profiles for transformer models (GPT-2, GPT-Neo, comprehensive, all models)
    status: completed
    dependencies:
      - update_config_file
  - id: update_module_metadata
    content: Update module metadata to include transformers in dependencies and operations list
    status: completed
    dependencies:
      - update_module_structure
---

# Add HuggingFace Transformers Support to Neural Text Generator

## Overview

Add HuggingFace Transformers support to the neural text generator module, enabling fine-tuning and inference with all text generation models from HuggingFace Hub. Transformers will integrate alongside existing character/word-level models, sharing data sources and compatible arguments.

## Architecture

### Model Type Integration

- Support `model_type: "transformer"` as a new option alongside "character", "word", and "both"
- Support `transformer_config` parameter for transformer-specific settings
- Allow combinations like `model_type: "both"` with `transformer_config` to train RNN + Transformer models

### Data Flow

```
User Request → NeuralTextGeneratorModule
    ↓
Load Data (existing data sources: Gutenberg, Wikipedia, etc.)
    ↓
Branch: model_type
    ├─ "character" → _train_character_model (existing)
    ├─ "word" → _train_word_model (existing)
    ├─ "transformer" → _train_transformer_model (new)
    └─ "both" → Train multiple models (existing + new)
```

## Implementation Details

### 1. Module Structure Updates

**File: `mavaia_core/brain/modules/neural_text_generator.py`**

#### Add Transformers Dependencies

- Add optional import for `transformers`, `torch`, and `datasets` libraries
- Check availability similar to TensorFlow/NumPy checks
- Add `TRANSFORMERS_AVAILABLE` flag

#### Update Module Class

- Add `self.transformer_model` and `self.transformer_tokenizer` attributes
- Add `self.transformer_config` for model configuration
- Update `metadata` to include transformers in dependencies and description

#### Add Transformer Training Method

- `_train_transformer_model()` method:
  - Accepts: text, epochs, continue_training, time_limit_seconds, overall_start_time, transformer_config
  - Uses existing data loading pipeline (same text preprocessing)
  - Supports fine-tuning with HuggingFace Trainer API
  - Implements time limit checking (same callback pattern as RNN models)
  - Saves checkpoints and model artifacts
  - Returns training results dictionary

#### Add Transformer Generation Method

- `_generate_transformer_text()` method:
  - Accepts: prompt, max_length, temperature, transformer_config
  - Uses model.generate() with configurable parameters
  - Supports top_k, top_p, repetition_penalty (from existing config)
  - Returns generated text with metadata

#### Update Main Training Flow

- Modify `_train_model()` to handle `model_type: "transformer"` or `transformer_config` parameter
- When `model_type: "both"` and `transformer_config` provided, train RNN + Transformer
- Calculate remaining time for transformer model when training multiple models

#### Update Generation Flow

- Modify `_generate_text()` to handle transformer model type
- Support `model_type: "transformer"` in generation operations

#### Update Model Loading/Saving

- `_load_model()`: Load transformer model and tokenizer from saved directory
- `_save_model()`: Save transformer model, tokenizer, and config
- Store models in `{model_dir}/transformer_model/` subdirectory

### 2. Configuration Updates

**File: `mavaia_core/brain/modules/neural_text_generator_config.json`**

Add transformer configuration section:

```json
{
  "transformer_model": {
    "model_name": "gpt2",
    "tokenizer_name": null,
    "max_length": 1024,
    "batch_size": 8,
    "gradient_accumulation_steps": 1,
    "learning_rate": 5e-5,
    "warmup_steps": 100,
    "save_steps": 500,
    "eval_steps": 500,
    "logging_steps": 100,
    "fp16": false,
    "use_cache": true
  },
  "generation": {
    "transformer": {
      "max_length": 500,
      "temperature": 0.7,
      "top_k": 50,
      "top_p": 0.9,
      "repetition_penalty": 1.1,
      "do_sample": true,
      "num_return_sequences": 1
    }
  }
}
```

### 3. Argument Mapping

**Existing Arguments Used for Transformers:**

- `source`: Data source (Gutenberg, Wikipedia, etc.) - **YES**
- `book_ids`: Source-specific IDs - **YES**
- `categories`: Category filters - **YES**
- `max_books`: Max items per source - **YES**
- `max_text_size`: Max text size in characters - **YES**
- `data_percentage`: Percentage of data to use - **YES**
- `epochs`: Number of training epochs - **YES**
- `train_for_minutes/hours`: Time limits - **YES**
- `continue_training`: Resume from checkpoint - **YES**
- `max_length`: Generation length - **YES** (for inference)
- `temperature`: Sampling temperature - **YES** (for inference)

**New Transformer-Specific Arguments:**

- `model_name`: HuggingFace model identifier (e.g., "gpt2", "EleutherAI/gpt-neo-1.3B")
- `tokenizer_name`: Optional tokenizer name (defaults to model_name)
- `transformer_config`: Full transformer configuration dict
- `batch_size`: Training batch size (default from config)
- `gradient_accumulation_steps`: For effective larger batch sizes
- `learning_rate`: Fine-tuning learning rate
- `warmup_steps`: Learning rate warmup steps
- `top_k`: Top-k sampling for generation
- `top_p`: Nucleus sampling for generation
- `repetition_penalty`: Penalty for repetition in generation

### 4. Training Script Updates

**File: `scripts/train_neural_text_generator.py`**

- Add `--model-name` argument for transformer model selection
- Add `--transformer-config` argument for JSON transformer config
- Update argument parsing to handle transformer-specific options
- Update profile loading to support transformer_config in YAML
- Add transformer model validation and availability checks

### 5. Training Profiles

**Directory: `scripts/training_profiles/`**

Create example profiles:

- `transformer_gpt2.yaml`: GPT-2 fine-tuning profile
- `transformer_gpt_neo.yaml`: GPT-Neo fine-tuning profile
- `transformer_comprehensive.yaml`: Multi-source transformer training
- `all_models.yaml`: Train character + word + transformer models

### 6. Error Handling

- Check for transformers library availability
- Validate model names against HuggingFace Hub
- Handle model download failures gracefully
- Provide clear error messages for missing dependencies
- Support offline mode with pre-downloaded models

### 7. Model Storage Structure

```
{model_dir}/
  ├─ character_model_latest.keras
  ├─ word_model_latest.keras
  └─ transformer_model/
      ├─ config.json
      ├─ pytorch_model.bin (or model.safetensors)
      ├─ tokenizer_config.json
      ├─ vocab.json
      ├─ merges.txt (if applicable)
      └─ checkpoints/
          └─ checkpoint-{step}/
```

## Testing Considerations

- Test with GPT-2 (smallest, fastest)
- Test with GPT-Neo models (medium size)
- Test fine-tuning on custom data
- Test inference with various parameters
- Test time limit enforcement during training
- Test model saving/loading
- Test with existing data sources

## Dependencies

Add to requirements (optional, checked at runtime):

- `transformers>=4.30.0`
- `torch>=2.0.0` (or `tensorflow>=2.13.0` for TF models)
- `datasets>=2.12.0` (for data handling)
- `accelerate>=0.20.0` (for distributed training)

## Migration Notes

- Existing models (character/word) continue to work unchanged
- Transformer support is opt-in via model_type or transformer_config
- No breaking changes to existing API
- Backward compatible with existing profiles and configurations