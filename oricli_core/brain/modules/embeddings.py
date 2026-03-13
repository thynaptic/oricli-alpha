from __future__ import annotations
"""
Embeddings Module - Generate embeddings using HuggingFace Sentence Transformers
Plug-and-play module that can be easily extended or replaced
"""

from typing import List, Union, Dict, Any
import logging

from oricli_core.brain.base_module import BaseBrainModule, ModuleMetadata
from oricli_core.exceptions import InvalidParameterError

logger = logging.getLogger(__name__)

# Optional import - will fail gracefully if dependencies not available
try:
    import numpy as np
    from sklearn.metrics.pairwise import cosine_similarity
    EMBEDDINGS_AVAILABLE = True
except ImportError:
    EMBEDDINGS_AVAILABLE = False

# Lazy imports to avoid timeout during module discovery
MODEL_MANAGER_AVAILABLE = False
ModelManager = None

def _lazy_import_model_manager():
    """Lazy import ModelManager only when needed"""
    global MODEL_MANAGER_AVAILABLE, ModelManager
    if not MODEL_MANAGER_AVAILABLE:
        try:
            from oricli_core.brain.modules.model_manager import ModelManager as MM
            ModelManager = MM
            MODEL_MANAGER_AVAILABLE = True
        except ImportError:
            pass


class EmbeddingsModule(BaseBrainModule):
    """Generate embeddings using HuggingFace models"""

    def __init__(self, model_name: str = "embedding_small"):
        """Initialize with a registered model name"""
        super().__init__()
        self.model_name = model_name
        self.model = None

    @property
    def metadata(self) -> ModuleMetadata:
        return ModuleMetadata(
            name="embeddings",
            version="1.0.0",
            description="Generate embeddings using HuggingFace Sentence Transformers",
            operations=["generate", "similarity", "batch_generate"],
            dependencies=[
                "numpy",
                "scikit-learn",
                "transformers",
                "jax",
                "flax",
            ],
            model_required=True,
        )

    def initialize(self) -> bool:
        """Lazy load model on first use"""
        # Always return True - model loading happens lazily in _ensure_model_loaded()
        # Even if numpy/sklearn aren't available now, they might be in venv
        # The execute() method will handle missing dependencies gracefully
        return True

    def _ensure_model_loaded(self):
        """Lazy load model"""
        _lazy_import_model_manager()
        if self.model is None and EMBEDDINGS_AVAILABLE and MODEL_MANAGER_AVAILABLE:
            try:
                self.model = ModelManager.get_model(self.model_name)
            except Exception as e:
                logger.debug(
                    "Failed to load embeddings model; using fallback embeddings",
                    exc_info=True,
                    extra={"module_name": "embeddings", "error_type": type(e).__name__},
                )
                # Don't raise - allow module to work without model
                pass

    def _generate_fallback_embedding(self, text: str, dimension: int = 384) -> List[float]:
        """Generate a simple fallback embedding using hash-based features"""
        import hashlib
        import re
        
        # Normalize text
        text_lower = text.lower()
        
        # Extract features
        features = []
        
        # 1. Character n-grams (2-grams and 3-grams)
        for n in [2, 3]:
            for i in range(len(text_lower) - n + 1):
                ngram = text_lower[i:i+n]
                hash_val = int(hashlib.md5(ngram.encode()).hexdigest(), 16)
                features.append(hash_val % 1000)
        
        # 2. Word features
        words = re.findall(r'\w+', text_lower)
        word_count = len(words)
        avg_word_length = sum(len(w) for w in words) / word_count if word_count > 0 else 0
        
        # 3. Character frequency features
        char_counts = {}
        for char in text_lower:
            if char.isalnum():
                char_counts[char] = char_counts.get(char, 0) + 1
        
        # 4. Text statistics
        features.extend([
            len(text),
            word_count,
            int(avg_word_length * 10),
            len(set(words)) if words else 0,
            text.count(' ') / max(len(text), 1),
            text.count('.') / max(len(text), 1),
            text.count('!') / max(len(text), 1),
            text.count('?') / max(len(text), 1),
        ])
        
        # 5. Hash-based features from text chunks
        chunk_size = max(10, len(text) // 20)
        for i in range(0, len(text), chunk_size):
            chunk = text[i:i+chunk_size]
            hash_val = int(hashlib.md5(chunk.encode()).hexdigest(), 16)
            features.append(hash_val % 1000)
        
        # Normalize to target dimension
        while len(features) < dimension:
            features.extend(features[:dimension - len(features)])
        
        # Normalize features to [0, 1] range
        max_val = max(features) if features else 1
        normalized = [f / max_val if max_val > 0 else 0.0 for f in features[:dimension]]
        
        return normalized

    def execute(self, operation: str, params: Dict[str, Any]) -> Dict[str, Any]:
        """Execute an embedding operation"""
        if operation == "generate":
            text = params.get("text", "")
            model_name = params.get("model_name")

            # Handle empty text
            if not text or len(text.strip()) == 0:
                # Return zero embedding for empty text
                fallback_embedding = [0.0] * 384
                return {
                    "embedding": fallback_embedding,
                    "dimension": 384,
                    "model": "fallback",
                    "method": "fallback",
                    "note": "Empty text - using zero embedding",
                }

            # Handle very long text (truncate to reasonable length)
            max_length = 512  # Typical transformer max length
            if len(text) > max_length * 10:  # Very long text
                # Truncate but keep beginning and end
                text = text[:max_length * 5] + " ... " + text[-max_length * 5:]

            # Try to use model if available
            if EMBEDDINGS_AVAILABLE and MODEL_MANAGER_AVAILABLE:
                if model_name:
                    # Switch model if requested
                    self.model_name = model_name
                    self.model = None

                self._ensure_model_loaded()

                if self.model is not None:
                    try:
                        # Truncate text if too long for model
                        if len(text) > max_length * 10:
                            text = text[:max_length * 5]
                        
                        embedding = self.model.encode(text, convert_to_numpy=True)
                        return {
                            "embedding": embedding.tolist(),
                            "dimension": len(embedding),
                            "model": self.model_name,
                            "method": "model",
                        }
                    except Exception as e:
                        # Model encoding failed, use fallback
                        pass

            # Fallback: generate simple embedding
            fallback_embedding = self._generate_fallback_embedding(text, dimension=384)
            return {
                "embedding": fallback_embedding,
                "dimension": 384,
                "model": "fallback",
                "method": "fallback",
            }

        elif operation == "batch_generate":
            texts = params.get("texts", [])
            model_name = params.get("model_name")

            if not texts:
                raise InvalidParameterError(
                    parameter="texts",
                    value=str(texts),
                    reason="Missing required parameter: texts",
                )

            # Try to use model if available
            if EMBEDDINGS_AVAILABLE and MODEL_MANAGER_AVAILABLE:
                if model_name:
                    self.model_name = model_name
                    self.model = None

                self._ensure_model_loaded()

                if self.model is not None:
                    try:
                        embeddings = self.model.encode(texts, convert_to_numpy=True)
                        return {
                            "embeddings": embeddings.tolist(),
                            "count": len(texts),
                            "dimension": (
                                embeddings.shape[1]
                                if len(embeddings.shape) > 1
                                else len(embeddings[0])
                            ),
                            "model": self.model_name,
                            "method": "model",
                        }
                    except Exception:
                        pass

            # Fallback: generate embeddings for each text
            fallback_embeddings = [self._generate_fallback_embedding(text) for text in texts]
            return {
                "embeddings": fallback_embeddings,
                "count": len(texts),
                "dimension": 384,
                "model": "fallback",
                "method": "fallback",
            }

        elif operation == "similarity":
            text1 = params.get("text1", "")
            text2 = params.get("text2", "")
            model_name = params.get("model_name")

            if not text1 or not text2:
                raise InvalidParameterError(
                    parameter="text1/text2",
                    value="",
                    reason="Missing required parameters: text1, text2",
                )

            # Try to use model if available
            if EMBEDDINGS_AVAILABLE and MODEL_MANAGER_AVAILABLE:
                if model_name:
                    self.model_name = model_name
                    self.model = None

                self._ensure_model_loaded()

                if self.model is not None:
                    try:
                        emb1 = np.array(self.model.encode(text1, convert_to_numpy=True)).reshape(
                            1, -1
                        )
                        emb2 = np.array(self.model.encode(text2, convert_to_numpy=True)).reshape(
                            1, -1
                        )

                        similarity = float(cosine_similarity(emb1, emb2)[0][0])

                        return {
                            "similarity": similarity,
                            "text1": text1[:100],  # Truncate for response
                            "text2": text2[:100],
                            "model": self.model_name,
                            "method": "model",
                        }
                    except Exception:
                        pass

            # Fallback: use simple word overlap similarity
            words1 = set(text1.lower().split())
            words2 = set(text2.lower().split())
            if not words1 or not words2:
                similarity = 0.0
            else:
                intersection = len(words1.intersection(words2))
                union = len(words1.union(words2))
                similarity = intersection / union if union > 0 else 0.0

            return {
                "similarity": similarity,
                "text1": text1[:100],
                "text2": text2[:100],
                "model": "fallback",
                "method": "fallback",
            }

        else:
            raise InvalidParameterError(
                parameter="operation",
                value=operation,
                reason="Unknown operation for embeddings",
            )

    def validate_params(self, operation: str, params: Dict[str, Any]) -> bool:
        """Validate parameters for operations"""
        if operation == "generate":
            return "text" in params
        elif operation == "batch_generate":
            return "texts" in params and isinstance(params["texts"], list)
        elif operation == "similarity":
            return "text1" in params and "text2" in params
        return True
