"""
Model Manager - Abstraction layer for HuggingFace models
Allows easy switching of transformers/embeddings/models without code changes
Uses JAX/Flax backend (Python 3.14 compatible)
"""

from typing import Optional, Dict, Any, List
from dataclasses import dataclass
import os

# Optional imports - will fail gracefully if HuggingFace not installed
try:
    from huggingface_hub import hf_hub_download, snapshot_download
    from transformers import (
        AutoTokenizer,
        AutoModel,
        AutoModelForSequenceClassification,
        FlaxAutoModel,
        FlaxAutoTokenizer,
    )

    HUGGINGFACE_AVAILABLE = True
except ImportError:
    HUGGINGFACE_AVAILABLE = False

# JAX/Flax required (Python 3.14 compatible)
try:
    import jax
    import jax.numpy as jnp
    JAX_AVAILABLE = True
except ImportError:
    JAX_AVAILABLE = False
    raise ImportError("JAX is required. Install with: pip install jax jaxlib flax")


@dataclass
class ModelConfig:
    """Configuration for a model"""

    model_id: str  # HuggingFace model ID
    model_type: str  # "embedding", "classifier", "generator", "reasoning"
    cache_dir: Optional[str] = None
    device: str = "cpu"  # Device (ignored for JAX, which handles devices automatically)
    revision: Optional[str] = None  # Git revision/tag
    backend: str = "flax"  # Always use Flax backend


def _get_embeddings_from_flax_model(model, tokenizer, texts: List[str]) -> jnp.ndarray:
    """Get embeddings from Flax model using mean pooling"""
    inputs = tokenizer(
        texts, return_tensors="jax", padding=True, truncation=True
    )
    outputs = model(**inputs)
    # Mean pooling over sequence dimension
    embeddings = jnp.mean(outputs.last_hidden_state, axis=1)
    return embeddings


class ModelManager:
    """Manages loading and caching of HuggingFace models"""

    _instances: Dict[str, Any] = {}
    _configs: Dict[str, ModelConfig] = {}

    @classmethod
    def register_model(cls, name: str, config: ModelConfig):
        """Register a model configuration"""
        cls._configs[name] = config

    @classmethod
    def get_model(cls, name: str, force_reload: bool = False):
        """Get or load a model by name"""
        if not HUGGINGFACE_AVAILABLE:
            raise ImportError(
                "HuggingFace libraries not available. Please install: huggingface-hub, transformers"
            )

        if name not in cls._configs:
            raise ValueError(f"Model '{name}' not registered")

        config = cls._configs[name]

        if name in cls._instances and not force_reload:
            return cls._instances[name]

        model = cls._load_model(config)
        cls._instances[name] = model
        return model

    @classmethod
    def _load_model(cls, config: ModelConfig):
        """Load a model based on its type using Flax backend"""
        if not JAX_AVAILABLE:
            raise ImportError("JAX is required. Install with: pip install jax jaxlib flax")

        if config.model_type == "embedding":
            # Use Flax backend for embeddings
            tokenizer = FlaxAutoTokenizer.from_pretrained(
                config.model_id, cache_dir=config.cache_dir, revision=config.revision
            )
            model = FlaxAutoModel.from_pretrained(
                config.model_id, cache_dir=config.cache_dir, revision=config.revision
            )
            # Create a wrapper that mimics sentence-transformers API
            class FlaxEmbeddingWrapper:
                def __init__(self, model, tokenizer, model_id):
                    self.model = model
                    self.tokenizer = tokenizer
                    self.model_id = model_id
                    self.params = model.params

                def encode(self, texts, convert_to_numpy=True, **kwargs):
                    if isinstance(texts, str):
                        texts = [texts]
                    embeddings = _get_embeddings_from_flax_model(
                        self.model, self.tokenizer, texts
                    )
                    if convert_to_numpy:
                        return jnp.asarray(embeddings)
                    return embeddings

            return FlaxEmbeddingWrapper(model, tokenizer, config.model_id)

        elif config.model_type == "classifier":
            tokenizer = FlaxAutoTokenizer.from_pretrained(
                config.model_id, cache_dir=config.cache_dir, revision=config.revision
            )
            # Note: Flax doesn't have AutoModelForSequenceClassification
            # Use regular AutoModel and add classification head if needed
            model = FlaxAutoModel.from_pretrained(
                config.model_id, cache_dir=config.cache_dir, revision=config.revision
            )
            return {"tokenizer": tokenizer, "model": model, "backend": "flax"}

        elif config.model_type == "generator":
            tokenizer = FlaxAutoTokenizer.from_pretrained(
                config.model_id, cache_dir=config.cache_dir, revision=config.revision
            )
            model = FlaxAutoModel.from_pretrained(
                config.model_id, cache_dir=config.cache_dir, revision=config.revision
            )
            return {"tokenizer": tokenizer, "model": model, "backend": "flax"}
        else:
            raise ValueError(f"Unknown model type: {config.model_type}")

    @classmethod
    def clear_cache(cls, name: Optional[str] = None):
        """Clear model cache"""
        if name:
            cls._instances.pop(name, None)
        else:
            cls._instances.clear()


# Default model configurations
DEFAULT_MODELS = {
    "embedding_small": ModelConfig(
        model_id="sentence-transformers/all-MiniLM-L6-v2",
        model_type="embedding",
        device="cpu",
        backend="flax",
    ),
    "embedding_large": ModelConfig(
        model_id="sentence-transformers/all-mpnet-base-v2",
        model_type="embedding",
        device="cpu",
        backend="auto",
    ),
    "classifier_general": ModelConfig(
        model_id="distilbert-base-uncased", model_type="classifier", device="cpu", backend="auto"
    ),
    "reasoning_small": ModelConfig(
        model_id="microsoft/DialoGPT-small", model_type="generator", device="cpu", backend="auto"
    ),
    "grammar_model_small": ModelConfig(
        model_id="distilgpt2", model_type="generator", device="cpu", backend="auto"
    ),
    "grammar_model_medium": ModelConfig(
        model_id="gpt2", model_type="generator", device="cpu", backend="auto"
    ),
    "grammar_model_large": ModelConfig(
        model_id="gpt2-medium", model_type="generator", device="cpu", backend="auto"
    ),
}

# Register default models
for name, config in DEFAULT_MODELS.items():
    ModelManager.register_model(name, config)
