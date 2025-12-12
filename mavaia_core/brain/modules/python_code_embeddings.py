"""
Python Code Embeddings Module

Generate semantic embeddings for Python code.
Provides code-specific embedding generation, similarity detection,
semantic search, and pattern clustering in embedding space.

This module is part of Mavaia's Python LLM capabilities, enabling
semantic understanding of Python code through vector representations.
"""

import ast
import hashlib
import sys
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

from mavaia_core.brain.base_module import BaseBrainModule, ModuleMetadata
from mavaia_core.exceptions import InvalidParameterError

# Lazy imports to avoid timeout during module discovery
# These will be imported when actually needed
HAS_NUMPY = None
HAS_TRANSFORMERS = None
JAX_AVAILABLE = None
MODEL_MANAGER_AVAILABLE = None
FlaxAutoModel = None
FlaxAutoTokenizer = None
ModelManager = None
np = None
cosine_similarity = None
jax = None
jnp = None

def _lazy_import_dependencies():
    """Lazy import of dependencies to avoid timeout during module discovery"""
    global HAS_NUMPY, HAS_TRANSFORMERS, JAX_AVAILABLE, MODEL_MANAGER_AVAILABLE
    global FlaxAutoModel, FlaxAutoTokenizer, ModelManager, np, cosine_similarity, jax, jnp
    
    if HAS_NUMPY is not None:
        return  # Already imported
    
    # Optional imports for advanced embeddings
    try:
        import numpy as np
        from sklearn.metrics.pairwise import cosine_similarity
        HAS_NUMPY = True
    except ImportError:
        HAS_NUMPY = False
        np = None
        cosine_similarity = None
    
    # JAX/Flax required (Python 3.14 compatible)
    try:
        import jax
        import jax.numpy as jnp
        from transformers import FlaxAutoModel, FlaxAutoTokenizer
        JAX_AVAILABLE = True
        HAS_TRANSFORMERS = True
    except ImportError:
        JAX_AVAILABLE = False
        HAS_TRANSFORMERS = False
        FlaxAutoModel = None
        FlaxAutoTokenizer = None
        jax = None
        jnp = None
    
    # Try to import model manager
    try:
        from mavaia_core.brain.modules.model_manager import ModelManager
        MODEL_MANAGER_AVAILABLE = True
    except ImportError:
        MODEL_MANAGER_AVAILABLE = False
        ModelManager = None


class PythonCodeEmbeddingsModule(BaseBrainModule):
    """
    Generate semantic embeddings for Python code.
    
    Provides code-specific embedding generation using:
    - AST-based features
    - Code structure analysis
    - Semantic code models (CodeBERT, GraphCodeBERT if available)
    - Fallback hash-based embeddings
    """

    def __init__(self):
        """Initialize the code embeddings module."""
        super().__init__()
        self._code_model = None
        self._tokenizer = None
        self._embedding_cache: Dict[str, List[float]] = {}

    @property
    def metadata(self) -> ModuleMetadata:
        """Return module metadata."""
        # Lazy import to check dependencies
        _lazy_import_dependencies()
        dependencies = []
        if HAS_NUMPY:
            dependencies.append("numpy")
        if HAS_TRANSFORMERS and JAX_AVAILABLE:
            dependencies.extend(["transformers", "jax", "flax"])
        
        return ModuleMetadata(
            name="python_code_embeddings",
            version="1.0.0",
            description=(
                "Generate semantic embeddings for Python code: "
                "code similarity detection, semantic search, "
                "and pattern clustering in embedding space"
            ),
            operations=[
                "embed_code",
                "similar_code",
                "code_semantic_search",
                "cluster_code_patterns",
                "batch_embed_code",
                "code_similarity",
            ],
            dependencies=dependencies,
            model_required=False,  # Works with fallback if models unavailable
        )

    def initialize(self) -> bool:
        """Initialize the module."""
        # Lazy import dependencies
        _lazy_import_dependencies()
        # Try to load code-specific models if available
        self._load_code_models()
        return True

    def _load_code_models(self) -> None:
        """Load code-specific embedding models if available."""
        # Ensure dependencies are imported
        _lazy_import_dependencies()
        if not HAS_TRANSFORMERS or not JAX_AVAILABLE:
            return
        
        # Try to load CodeBERT or similar code models using Flax
        code_models = [
            "microsoft/codebert-base",
            "microsoft/graphcodebert-base",
        ]
        
        for model_name in code_models:
            try:
                self._tokenizer = FlaxAutoTokenizer.from_pretrained(model_name)
                self._code_model = FlaxAutoModel.from_pretrained(model_name)
                break
            except Exception:
                continue

    def execute(self, operation: str, params: Dict[str, Any]) -> Dict[str, Any]:
        """
        Execute a code embedding operation.
        
        Args:
            operation: Operation name
            params: Operation parameters
            
        Returns:
            Operation result dictionary
            
        Raises:
            ValueError: If operation is unknown
            InvalidParameterError: If parameters are invalid
        """
        if operation == "embed_code":
            code = params.get("code", "")
            if not code:
                raise InvalidParameterError("code", "", "Code cannot be empty")
            return self.embed_code(code)
        
        elif operation == "similar_code":
            query_code = params.get("query_code", "")
            codebase = params.get("codebase", [])
            top_k = params.get("top_k", 5)
            if not query_code:
                raise InvalidParameterError("query_code", "", "Query code cannot be empty")
            if not codebase:
                raise InvalidParameterError("codebase", [], "Codebase cannot be empty")
            return self.similar_code(query_code, codebase, top_k)
        
        elif operation == "code_semantic_search":
            query = params.get("query", "")
            codebase = params.get("codebase", [])
            top_k = params.get("top_k", 5)
            if not query:
                raise InvalidParameterError("query", "", "Query cannot be empty")
            if not codebase:
                raise InvalidParameterError("codebase", [], "Codebase cannot be empty")
            return self.code_semantic_search(query, codebase, top_k)
        
        elif operation == "cluster_code_patterns":
            codebase = params.get("codebase", [])
            n_clusters = params.get("n_clusters", 5)
            if not codebase:
                raise InvalidParameterError("codebase", [], "Codebase cannot be empty")
            return self.cluster_code_patterns(codebase, n_clusters)
        
        elif operation == "batch_embed_code":
            codebase = params.get("codebase", [])
            if not codebase:
                raise InvalidParameterError("codebase", [], "Codebase cannot be empty")
            return self.batch_embed_code(codebase)
        
        elif operation == "code_similarity":
            code1 = params.get("code1", "")
            code2 = params.get("code2", "")
            if not code1:
                raise InvalidParameterError("code1", "", "Code1 cannot be empty")
            if not code2:
                raise InvalidParameterError("code2", "", "Code2 cannot be empty")
            return self.code_similarity(code1, code2)
        
        else:
            raise ValueError(f"Unknown operation: {operation}")

    def embed_code(self, code: str) -> Dict[str, Any]:
        """
        Generate semantic embedding for Python code.
        
        Args:
            code: Python code to embed
            
        Returns:
            Dictionary containing:
            - embedding: Vector embedding
            - dimension: Embedding dimension
            - method: Method used (model, ast, fallback)
            - model: Model name if used
        """
        # Check cache
        code_hash = hashlib.md5(code.encode()).hexdigest()
        if code_hash in self._embedding_cache:
            return {
                "embedding": self._embedding_cache[code_hash],
                "dimension": len(self._embedding_cache[code_hash]),
                "method": "cached",
            }

        # Try code-specific model first
        if self._code_model and self._tokenizer:
            try:
                embedding = self._embed_code_with_model(code)
                self._embedding_cache[code_hash] = embedding
                return {
                    "embedding": embedding,
                    "dimension": len(embedding),
                    "method": "code_model",
                    "model": "codebert",
                }
            except Exception:
                pass  # Fall back to AST-based

        # Try AST-based embedding
        try:
            embedding = self._embed_code_with_ast(code)
            self._embedding_cache[code_hash] = embedding
            return {
                "embedding": embedding,
                "dimension": len(embedding),
                "method": "ast_based",
            }
        except Exception:
            pass

        # Fallback to hash-based
        embedding = self._embed_code_fallback(code)
        self._embedding_cache[code_hash] = embedding
        return {
            "embedding": embedding,
            "dimension": len(embedding),
            "method": "fallback",
        }

    def _embed_code_with_model(self, code: str) -> List[float]:
        """Generate embedding using code-specific model."""
        _lazy_import_dependencies()
        if not self._code_model or not self._tokenizer or not JAX_AVAILABLE:
            raise ValueError("Code model not available")
        
        # Tokenize code
        inputs = self._tokenizer(
            code,
            return_tensors="np",  # NumPy arrays for JAX
            truncation=True,
            max_length=512,
            padding=True,
        )
        
        # Generate embeddings using JAX
        outputs = self._code_model(**inputs)
        # Use [CLS] token embedding or mean pooling
        # Flax models return last_hidden_state as JAX array
        last_hidden_state = outputs.last_hidden_state
        # Get [CLS] token (first token) and convert to list
        embedding = jnp.array(last_hidden_state[0][0]).tolist()
        
        return embedding

    def _embed_code_with_ast(self, code: str) -> List[float]:
        """Generate embedding based on AST structure."""
        try:
            tree = ast.parse(code)
        except SyntaxError:
            raise ValueError("Invalid Python code")

        features = []

        # Extract AST features
        node_types = {}
        for node in ast.walk(tree):
            node_type = type(node).__name__
            node_types[node_type] = node_types.get(node_type, 0) + 1

        # Normalize node type counts
        common_types = [
            "FunctionDef", "ClassDef", "Assign", "Call", "Name",
            "If", "For", "While", "Return", "Import", "ImportFrom",
            "List", "Dict", "Tuple", "Set", "Constant", "BinOp",
            "Compare", "Attribute", "Subscript",
        ]
        
        for node_type in common_types:
            features.append(node_types.get(node_type, 0))

        # Extract structural features
        functions = [n for n in ast.walk(tree) if isinstance(n, ast.FunctionDef)]
        classes = [n for n in ast.walk(tree) if isinstance(n, ast.ClassDef)]
        imports = [n for n in ast.walk(tree) if isinstance(n, (ast.Import, ast.ImportFrom))]

        features.extend([
            len(functions),
            len(classes),
            len(imports),
            len(code.split("\n")),
            len(code),
        ])

        # Extract identifier features
        identifiers = [n.id for n in ast.walk(tree) if isinstance(n, ast.Name)]
        unique_identifiers = len(set(identifiers))
        features.append(unique_identifiers)

        # Extract call features
        calls = [n for n in ast.walk(tree) if isinstance(n, ast.Call)]
        features.append(len(calls))

        # Normalize to fixed dimension (384)
        while len(features) < 384:
            features.extend(features[:384 - len(features)])

        # Normalize features
        max_val = max(features) if features else 1
        normalized = [f / max_val if max_val > 0 else 0.0 for f in features[:384]]

        return normalized

    def _embed_code_fallback(self, code: str) -> List[float]:
        """Generate fallback embedding using hash-based features."""
        # Similar to embeddings module fallback but code-specific
        code_lower = code.lower()
        features = []

        # Character n-grams
        for n in [2, 3, 4]:
            for i in range(len(code_lower) - n + 1):
                ngram = code_lower[i:i+n]
                hash_val = int(hashlib.md5(ngram.encode()).hexdigest(), 16)
                features.append(hash_val % 1000)

        # Code-specific features
        features.extend([
            code.count("def "),
            code.count("class "),
            code.count("import "),
            code.count("from "),
            code.count("("),
            code.count(")"),
            code.count("["),
            code.count("]"),
            code.count("{"),
            code.count("}"),
            len(code.split("\n")),
            len(code),
        ])

        # Normalize to 384 dimensions
        while len(features) < 384:
            features.extend(features[:384 - len(features)])

        max_val = max(features) if features else 1
        normalized = [f / max_val if max_val > 0 else 0.0 for f in features[:384]]

        return normalized

    def similar_code(
        self,
        query_code: str,
        codebase: List[str],
        top_k: int = 5
    ) -> Dict[str, Any]:
        """
        Find similar code in codebase.
        
        Args:
            query_code: Code to find similarities for
            codebase: List of code snippets to search
            top_k: Number of top results to return
            
        Returns:
            Dictionary containing similar code snippets with similarity scores
        """
        # Generate query embedding
        query_result = self.embed_code(query_code)
        query_embedding = query_result["embedding"]

        # Generate embeddings for codebase
        codebase_embeddings = []
        for code in codebase:
            result = self.embed_code(code)
            codebase_embeddings.append(result["embedding"])

        # Calculate similarities
        _lazy_import_dependencies()
        similarities = []
        if HAS_NUMPY:
            query_vec = np.array(query_embedding).reshape(1, -1)
            codebase_matrix = np.array(codebase_embeddings)
            sim_scores = cosine_similarity(query_vec, codebase_matrix)[0]
            
            # Get top k
            top_indices = np.argsort(sim_scores)[::-1][:top_k]
            
            for idx in top_indices:
                similarities.append({
                    "code": codebase[idx],
                    "similarity": float(sim_scores[idx]),
                    "index": int(idx),
                })
        else:
            # Fallback: calculate cosine similarity manually
            for i, code_embedding in enumerate(codebase_embeddings):
                similarity = self._cosine_similarity(query_embedding, code_embedding)
                similarities.append({
                    "code": codebase[i],
                    "similarity": similarity,
                    "index": i,
                })
            # Sort by similarity
            similarities.sort(key=lambda x: x["similarity"], reverse=True)
            similarities = similarities[:top_k]

        return {
            "query_code": query_code,
            "similar_code": similarities,
            "top_k": top_k,
        }

    def code_semantic_search(
        self,
        query: str,
        codebase: List[str],
        top_k: int = 5
    ) -> Dict[str, Any]:
        """
        Semantic search in codebase using natural language query.
        
        Args:
            query: Natural language query
            codebase: List of code snippets to search
            top_k: Number of top results to return
            
        Returns:
            Dictionary containing matching code snippets
        """
        # For now, treat query as code-like and use similar_code
        # In future, could use text-to-code embedding models
        return self.similar_code(query, codebase, top_k)

    def cluster_code_patterns(
        self,
        codebase: List[str],
        n_clusters: int = 5
    ) -> Dict[str, Any]:
        """
        Cluster code patterns in embedding space.
        
        Args:
            codebase: List of code snippets to cluster
            n_clusters: Number of clusters
            
        Returns:
            Dictionary containing cluster assignments and patterns
        """
        # Generate embeddings
        embeddings = []
        for code in codebase:
            result = self.embed_code(code)
            embeddings.append(result["embedding"])

        _lazy_import_dependencies()
        if not HAS_NUMPY:
            return {
                "success": False,
                "error": "numpy required for clustering",
            }

        # Simple k-means clustering
        from sklearn.cluster import KMeans
        
        kmeans = KMeans(n_clusters=n_clusters, random_state=42, n_init=10)
        cluster_labels = kmeans.fit_predict(embeddings)

        # Organize results
        clusters: Dict[int, List[Dict[str, Any]]] = {}
        for i, (code, label) in enumerate(zip(codebase, cluster_labels)):
            if label not in clusters:
                clusters[label] = []
            clusters[label].append({
                "code": code,
                "index": i,
            })

        return {
            "success": True,
            "n_clusters": n_clusters,
            "clusters": clusters,
            "cluster_labels": cluster_labels.tolist(),
        }

    def batch_embed_code(self, codebase: List[str]) -> Dict[str, Any]:
        """
        Generate embeddings for multiple code snippets.
        
        Args:
            codebase: List of code snippets
            
        Returns:
            Dictionary containing embeddings for all code snippets
        """
        embeddings = []
        for code in codebase:
            result = self.embed_code(code)
            embeddings.append({
                "code": code,
                "embedding": result["embedding"],
                "dimension": result["dimension"],
                "method": result.get("method", "unknown"),
            })

        return {
            "embeddings": embeddings,
            "count": len(embeddings),
        }

    def code_similarity(self, code1: str, code2: str) -> Dict[str, Any]:
        """
        Calculate similarity between two code snippets.
        
        Args:
            code1: First code snippet
            code2: Second code snippet
            
        Returns:
            Dictionary containing similarity score and details
        """
        result1 = self.embed_code(code1)
        result2 = self.embed_code(code2)

        embedding1 = result1["embedding"]
        embedding2 = result2["embedding"]

        similarity = self._cosine_similarity(embedding1, embedding2)

        return {
            "code1": code1,
            "code2": code2,
            "similarity": similarity,
            "method1": result1.get("method", "unknown"),
            "method2": result2.get("method", "unknown"),
        }

    def _cosine_similarity(self, vec1: List[float], vec2: List[float]) -> float:
        """Calculate cosine similarity between two vectors."""
        if len(vec1) != len(vec2):
            # Pad or truncate to same length
            min_len = min(len(vec1), len(vec2))
            vec1 = vec1[:min_len]
            vec2 = vec2[:min_len]

        dot_product = sum(a * b for a, b in zip(vec1, vec2))
        magnitude1 = sum(a * a for a in vec1) ** 0.5
        magnitude2 = sum(b * b for b in vec2) ** 0.5

        if magnitude1 == 0 or magnitude2 == 0:
            return 0.0

        return dot_product / (magnitude1 * magnitude2)
