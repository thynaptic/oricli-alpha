from __future__ import annotations
"""
Phrase Embeddings Module - Multi-level phrase embeddings for hybrid phrasing
Generates word-level, phrase-level, and sentence-level embeddings
Used for semantic similarity search and candidate ranking in hybrid phrasing system
"""

from typing import List, Dict, Any, Optional, Tuple
import re
import logging

from mavaia_core.brain.base_module import BaseBrainModule, ModuleMetadata
from mavaia_core.exceptions import InvalidParameterError

logger = logging.getLogger(__name__)

# Optional import - will fail gracefully if dependencies not available
try:
    import numpy as np
    from sklearn.metrics.pairwise import cosine_similarity
    PHRASE_EMBEDDINGS_AVAILABLE = True
except ImportError:
    PHRASE_EMBEDDINGS_AVAILABLE = False

MODEL_MANAGER_AVAILABLE = False
ModelManager = None

def _lazy_import_model_manager():
    """Lazy import ModelManager only when needed"""
    global MODEL_MANAGER_AVAILABLE, ModelManager
    if not MODEL_MANAGER_AVAILABLE:
        try:
            from mavaia_core.brain.modules.model_manager import ModelManager as MM
            ModelManager = MM
            MODEL_MANAGER_AVAILABLE = True
        except ImportError as e:
            logger.debug(
                "Failed to import ModelManager for phrase_embeddings",
                exc_info=True,
                extra={"module_name": "phrase_embeddings", "error_type": type(e).__name__},
            )


class PhraseEmbeddingsModule(BaseBrainModule):
    """Multi-level phrase embeddings for hybrid phrasing system"""

    def __init__(self, model_name: str = "embedding_small"):
        """Initialize with a registered model name"""
        super().__init__()
        self.model_name = model_name
        self.model = None

    @property
    def metadata(self) -> ModuleMetadata:
        return ModuleMetadata(
            name="phrase_embeddings",
            version="1.0.0",
            description="Multi-level phrase embeddings (word, phrase, sentence) for hybrid phrasing",
            operations=[
                "embed_words",
                "embed_phrases",
                "embed_sentence",
                "find_similar_phrases",
                "rank_candidates",
                "batch_embed_words",
                "batch_embed_phrases",
            ],
            dependencies=[
                "sentence-transformers",
                "numpy",
                "scikit-learn",
                "transformers",
                "torch",
            ],
            model_required=True,
        )

    def initialize(self) -> bool:
        """Lazy load model on first use"""
        # Always return True - model loading happens lazily in _ensure_model_loaded()
        # Even if dependencies aren't available now, they might be in venv
        # The execute() method will handle missing dependencies gracefully
        return True

    def _ensure_model_loaded(self):
        """Lazy load model only when needed"""
        _lazy_import_model_manager()
        if self.model is None and PHRASE_EMBEDDINGS_AVAILABLE and MODEL_MANAGER_AVAILABLE:
            try:
                self.model = ModelManager.get_model(self.model_name)
            except Exception as e:
                logger.debug(
                    "Failed to load embeddings model; continuing without model",
                    exc_info=True,
                    extra={"module_name": "phrase_embeddings", "error_type": type(e).__name__},
                )
                # Don't raise - allow module to work without model
                self.model = None

    def execute(self, operation: str, params: Dict[str, Any]) -> Dict[str, Any]:
        """Execute a phrase embedding operation"""
        if not PHRASE_EMBEDDINGS_AVAILABLE:
            return {
                "error": "Phrase embeddings dependencies not available. Please install: sentence-transformers, numpy, scikit-learn"
            }

        if operation == "embed_words":
            return self._embed_words(
                text=params.get("text", ""), model_name=params.get("model_name")
            )

        elif operation == "embed_phrases":
            return self._embed_phrases(
                text=params.get("text", ""),
                phrase_lengths=params.get("phrase_lengths", [2, 3, 4, 5]),
                model_name=params.get("model_name"),
            )

        elif operation == "embed_sentence":
            return self._embed_sentence(
                text=params.get("text", ""), model_name=params.get("model_name")
            )

        elif operation == "find_similar_phrases":
            return self._find_similar_phrases(
                query_phrase=params.get("query_phrase", ""),
                candidate_phrases=params.get("candidate_phrases", []),
                level=params.get("level", "phrase"),  # "word", "phrase", "sentence"
                top_k=params.get("top_k", 10),
                similarity_threshold=params.get("similarity_threshold", 0.5),
                model_name=params.get("model_name"),
            )

        elif operation == "rank_candidates":
            return self._rank_candidates(
                candidates=params.get("candidates", []),
                context=params.get("context", ""),
                level_weights=params.get(
                    "level_weights", {"word": 0.2, "phrase": 0.4, "sentence": 0.4}
                ),
                model_name=params.get("model_name"),
            )

        elif operation == "batch_embed_words":
            return self._batch_embed_words(
                texts=params.get("texts", []), model_name=params.get("model_name")
            )

        elif operation == "batch_embed_phrases":
            return self._batch_embed_phrases(
                phrases=params.get("phrases", []), model_name=params.get("model_name")
            )

        else:
            raise InvalidParameterError(
                parameter="operation",
                value=operation,
                reason=(
                    "Unknown operation for phrase_embeddings. Supported: embed_words, "
                    "embed_phrases, embed_sentence, find_similar_phrases, rank_candidates, "
                    "batch_embed_words, batch_embed_phrases"
                ),
            )

    def _embed_words(
        self, text: str, model_name: Optional[str] = None
    ) -> Dict[str, Any]:
        """Embed individual words from text (word-level embeddings)"""
        if not text:
            return {"embeddings": [], "words": [], "dimension": 0}

        if model_name:
            self.model_name = model_name
            self.model = None

        self._ensure_model_loaded()
        if self.model is None:
            return {
                "embeddings": [],
                "words": [],
                "dimension": 0,
                "error": "Embedding model is not available",
            }

        # Tokenize into words
        words = self._tokenize_words(text)

        if not words:
            return {"embeddings": [], "words": [], "dimension": 0}

        # Embed each word individually
        embeddings = []
        for word in words:
            embedding = self.model.encode(word, convert_to_numpy=True)
            embeddings.append(embedding.tolist())

        dimension = len(embeddings[0]) if embeddings else 0

        return {
            "embeddings": embeddings,
            "words": words,
            "count": len(words),
            "dimension": dimension,
            "model": self.model_name,
        }

    def _embed_phrases(
        self, text: str, phrase_lengths: List[int], model_name: Optional[str] = None
    ) -> Dict[str, Any]:
        """Extract and embed phrases of specified lengths (phrase-level embeddings)"""
        if not text:
            return {"embeddings": [], "phrases": [], "dimension": 0}

        if model_name:
            self.model_name = model_name
            self.model = None

        self._ensure_model_loaded()
        if self.model is None:
            return {
                "embeddings": [],
                "phrases": [],
                "dimension": 0,
                "error": "Embedding model is not available",
            }

        # Tokenize into words
        words = self._tokenize_words(text)

        if not words:
            return {"embeddings": [], "phrases": [], "dimension": 0}

        # Extract phrases of each length
        phrases = []
        for length in phrase_lengths:
            if length < 1 or length > len(words):
                continue
            for i in range(len(words) - length + 1):
                phrase = " ".join(words[i : i + length])
                phrases.append(phrase)

        if not phrases:
            return {"embeddings": [], "phrases": [], "dimension": 0}

        # Embed all phrases
        embeddings_array = self.model.encode(phrases, convert_to_numpy=True)
        embeddings = embeddings_array.tolist()
        dimension = (
            embeddings_array.shape[1]
            if len(embeddings_array.shape) > 1
            else len(embeddings[0])
        )

        return {
            "embeddings": embeddings,
            "phrases": phrases,
            "count": len(phrases),
            "dimension": dimension,
            "model": self.model_name,
        }

    def _embed_sentence(
        self, text: str, model_name: Optional[str] = None
    ) -> Dict[str, Any]:
        """Embed full sentence/context (sentence-level embedding)"""
        if not text:
            return {"embedding": [], "dimension": 0}

        if model_name:
            self.model_name = model_name
            self.model = None

        self._ensure_model_loaded()
        if self.model is None:
            return {
                "embedding": [],
                "dimension": 0,
                "error": "Embedding model is not available",
            }

        # Embed as single sentence
        embedding = self.model.encode(text, convert_to_numpy=True)

        return {
            "embedding": embedding.tolist(),
            "dimension": len(embedding),
            "model": self.model_name,
        }

    def _find_similar_phrases(
        self,
        query_phrase: str,
        candidate_phrases: List[str],
        level: str = "phrase",
        top_k: int = 10,
        similarity_threshold: float = 0.5,
        model_name: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Find semantically similar phrases using cosine similarity"""
        if not query_phrase or not candidate_phrases:
            return {"similar_phrases": [], "similarities": []}

        if model_name:
            self.model_name = model_name
            self.model = None

        self._ensure_model_loaded()
        if self.model is None:
            return {"similar_phrases": [], "similarities": [], "error": "Embedding model is not available"}

        # Embed query phrase based on level
        if level == "word":
            query_result = self._embed_words(query_phrase, model_name)
            if not query_result.get("embeddings"):
                return {"similar_phrases": [], "similarities": []}
            # Average word embeddings for query
            query_embedding = np.mean(
                np.array(query_result["embeddings"]), axis=0
            ).reshape(1, -1)
        elif level == "sentence":
            query_result = self._embed_sentence(query_phrase, model_name)
            query_embedding = np.array(query_result["embedding"]).reshape(1, -1)
        else:  # phrase level
            query_embedding = np.array(
                self.model.encode(query_phrase, convert_to_numpy=True)
            ).reshape(1, -1)

        # Embed candidate phrases
        candidate_embeddings = self.model.encode(
            candidate_phrases, convert_to_numpy=True
        )

        # Calculate cosine similarities
        similarities = cosine_similarity(query_embedding, candidate_embeddings)[0]

        # Filter by threshold and get top_k
        similar_indices = []
        for i, sim in enumerate(similarities):
            if sim >= similarity_threshold:
                similar_indices.append((i, sim))

        # Sort by similarity (descending)
        similar_indices.sort(key=lambda x: x[1], reverse=True)

        # Get top_k
        top_indices = similar_indices[:top_k]

        similar_phrases = []
        similarity_scores = []
        for idx, sim in top_indices:
            similar_phrases.append(candidate_phrases[idx])
            similarity_scores.append(float(sim))

        return {
            "similar_phrases": similar_phrases,
            "similarities": similarity_scores,
            "count": len(similar_phrases),
            "level": level,
            "threshold": similarity_threshold,
        }

    def _rank_candidates(
        self,
        candidates: List[str],
        context: str,
        level_weights: Dict[str, float],
        model_name: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Rank candidate phrases by multi-level semantic similarity to context"""
        if not candidates or not context:
            return {"ranked_candidates": candidates, "scores": []}

        if model_name:
            self.model_name = model_name
            self.model = None

        self._ensure_model_loaded()
        if self.model is None:
            return {
                "ranked_candidates": candidates,
                "scores": [],
                "detailed_scores": [],
                "count": len(candidates),
                "error": "Embedding model is not available",
            }

        # Get weights
        w_word = level_weights.get("word", 0.2)
        w_phrase = level_weights.get("phrase", 0.4)
        w_sentence = level_weights.get("sentence", 0.4)

        # Normalize weights
        total_weight = w_word + w_phrase + w_sentence
        if total_weight > 0:
            w_word /= total_weight
            w_phrase /= total_weight
            w_sentence /= total_weight

        # Embed context at each level
        context_word_result = self._embed_words(context, model_name)
        context_phrase_result = self._embed_phrases(context, [2, 3, 4, 5], model_name)
        context_sentence_result = self._embed_sentence(context, model_name)

        # Get context embeddings
        context_word_embed = None
        if context_word_result.get("embeddings"):
            context_word_embed = np.mean(
                np.array(context_word_result["embeddings"]), axis=0
            ).reshape(1, -1)

        context_phrase_embed = None
        if context_phrase_result.get("embeddings"):
            # Use average of phrase embeddings
            context_phrase_embed = np.mean(
                np.array(context_phrase_result["embeddings"]), axis=0
            ).reshape(1, -1)

        context_sentence_embed = None
        if context_sentence_result.get("embedding"):
            context_sentence_embed = np.array(context_sentence_result["embedding"]).reshape(1, -1)

        # Score each candidate
        candidate_scores = []

        for candidate in candidates:
            # Word-level similarity
            word_sim = 0.0
            if w_word > 0 and context_word_embed is not None:
                candidate_word_result = self._embed_words(candidate, model_name)
                if candidate_word_result.get("embeddings"):
                    candidate_word_embed = np.mean(
                        np.array(candidate_word_result["embeddings"]), axis=0
                    ).reshape(1, -1)
                    word_sim = float(
                        cosine_similarity(context_word_embed, candidate_word_embed)[0][
                            0
                        ]
                    )

            # Phrase-level similarity
            phrase_sim = 0.0
            if w_phrase > 0 and context_phrase_embed is not None:
                candidate_phrase_result = self._embed_phrases(
                    candidate, [2, 3, 4, 5], model_name
                )
                if candidate_phrase_result.get("embeddings"):
                    candidate_phrase_embed = np.mean(
                        np.array(candidate_phrase_result["embeddings"]), axis=0
                    ).reshape(1, -1)
                    phrase_sim = float(
                        cosine_similarity(context_phrase_embed, candidate_phrase_embed)[
                            0
                        ][0]
                    )

            # Sentence-level similarity
            sentence_sim = 0.0
            if w_sentence > 0 and context_sentence_embed is not None:
                candidate_sentence_embed = np.array(
                    self.model.encode(candidate, convert_to_numpy=True)
                ).reshape(1, -1)
                sentence_sim = float(
                    cosine_similarity(context_sentence_embed, candidate_sentence_embed)[
                        0
                    ][0]
                )

            # Combined multi-level score
            combined_score = (
                (w_word * word_sim)
                + (w_phrase * phrase_sim)
                + (w_sentence * sentence_sim)
            )

            candidate_scores.append(
                {
                    "candidate": candidate,
                    "score": combined_score,
                    "word_similarity": word_sim,
                    "phrase_similarity": phrase_sim,
                    "sentence_similarity": sentence_sim,
                }
            )

        # Sort by score (descending)
        candidate_scores.sort(key=lambda x: x["score"], reverse=True)

        ranked_candidates = [item["candidate"] for item in candidate_scores]
        scores = [item["score"] for item in candidate_scores]
        detailed_scores = [
            {
                "candidate": item["candidate"],
                "total_score": item["score"],
                "word_similarity": item["word_similarity"],
                "phrase_similarity": item["phrase_similarity"],
                "sentence_similarity": item["sentence_similarity"],
            }
            for item in candidate_scores
        ]

        return {
            "ranked_candidates": ranked_candidates,
            "scores": scores,
            "detailed_scores": detailed_scores,
            "count": len(ranked_candidates),
        }

    def _batch_embed_words(
        self, texts: List[str], model_name: Optional[str] = None
    ) -> Dict[str, Any]:
        """Batch embed words from multiple texts"""
        if not texts:
            return {"embeddings": [], "texts": [], "word_counts": []}

        if model_name:
            self.model_name = model_name
            self.model = None

        self._ensure_model_loaded()

        all_embeddings = []
        all_words = []
        word_counts = []

        for text in texts:
            result = self._embed_words(text, model_name)
            all_embeddings.append(result.get("embeddings", []))
            all_words.append(result.get("words", []))
            word_counts.append(result.get("count", 0))

        return {
            "embeddings": all_embeddings,
            "words": all_words,
            "word_counts": word_counts,
            "count": len(texts),
            "model": self.model_name,
        }

    def _batch_embed_phrases(
        self, phrases: List[str], model_name: Optional[str] = None
    ) -> Dict[str, Any]:
        """Batch embed phrases"""
        if not phrases:
            return {"embeddings": [], "phrases": [], "dimension": 0}

        if model_name:
            self.model_name = model_name
            self.model = None

        self._ensure_model_loaded()
        if self.model is None:
            return {"embeddings": [], "phrases": phrases, "dimension": 0, "error": "Embedding model is not available"}

        # Embed all phrases at once
        embeddings_array = self.model.encode(phrases, convert_to_numpy=True)
        embeddings = embeddings_array.tolist()
        dimension = (
            embeddings_array.shape[1]
            if len(embeddings_array.shape) > 1
            else len(embeddings[0])
        )

        return {
            "embeddings": embeddings,
            "phrases": phrases,
            "count": len(phrases),
            "dimension": dimension,
            "model": self.model_name,
        }

    def _tokenize_words(self, text: str) -> List[str]:
        """Tokenize text into words, handling punctuation"""
        # Remove extra whitespace
        text = re.sub(r"\s+", " ", text.strip())

        # Split on whitespace and punctuation boundaries
        words = []
        current_word = ""

        for char in text:
            if char.isalnum() or char in "'-":
                current_word += char
            else:
                if current_word:
                    words.append(current_word.lower())
                    current_word = ""
                # Keep punctuation as separate tokens if meaningful
                if char.strip():
                    words.append(char)

        if current_word:
            words.append(current_word.lower())

        # Filter out empty strings and single punctuation marks that don't add value
        words = [w for w in words if w and (len(w) > 1 or w.isalnum())]

        return words

    def validate_params(self, operation: str, params: Dict[str, Any]) -> bool:
        """Validate parameters for operations"""
        if operation == "embed_words" or operation == "embed_sentence":
            return "text" in params
        elif operation == "embed_phrases":
            return "text" in params
        elif operation == "find_similar_phrases":
            return "query_phrase" in params and "candidate_phrases" in params
        elif operation == "rank_candidates":
            return "candidates" in params and "context" in params
        elif operation == "batch_embed_words":
            return "texts" in params and isinstance(params["texts"], list)
        elif operation == "batch_embed_phrases":
            return "phrases" in params and isinstance(params["phrases"], list)
        return True
