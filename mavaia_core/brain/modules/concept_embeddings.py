from __future__ import annotations
"""
Concept Embeddings Module - Extended concept embedding system with hierarchies and relationships
Extends base embeddings.py with concept hierarchies, semantic relationships, and domain-specific embeddings
"""

from typing import Dict, Any, List, Optional, Set, Tuple
import json
from pathlib import Path
from collections import defaultdict
import logging

from mavaia_core.brain.base_module import BaseBrainModule, ModuleMetadata
from mavaia_core.exceptions import InvalidParameterError

logger = logging.getLogger(__name__)

# Check for basic dependencies first
try:
    import numpy as np
    from sklearn.metrics.pairwise import cosine_similarity
    NUMPY_AVAILABLE = True
except ImportError:
    NUMPY_AVAILABLE = False

# Lazy import base embeddings module - don't import at module level
EMBEDDINGS_MODULE_AVAILABLE = None
EmbeddingsModule = None

def _lazy_import_embeddings():
    """Lazy import embeddings module only when needed"""
    global EMBEDDINGS_MODULE_AVAILABLE, EmbeddingsModule
    if EMBEDDINGS_MODULE_AVAILABLE is None:
        try:
            from mavaia_core.brain.modules.embeddings import EmbeddingsModule as EM
            EmbeddingsModule = EM
            EMBEDDINGS_MODULE_AVAILABLE = True
        except ImportError:
            EMBEDDINGS_MODULE_AVAILABLE = False
            EmbeddingsModule = None
    return EMBEDDINGS_MODULE_AVAILABLE

# EMBEDDINGS_AVAILABLE should be True if basic deps are available
EMBEDDINGS_AVAILABLE = NUMPY_AVAILABLE


class ConceptEmbeddingsModule(BaseBrainModule):
    """Extended concept embeddings with hierarchies and relationships"""

    def __init__(self):
        super().__init__()
        self.config = None
        self.base_embeddings = None
        self.concept_hierarchies = {}
        self.concept_relationships = {}
        self.domain_embeddings = {}
        # Don't load config in __init__ - do it lazily to avoid blocking imports
        # self._load_config()
        # Don't initialize base embeddings in __init__ - do it lazily in initialize()

    @property
    def metadata(self) -> ModuleMetadata:
        return ModuleMetadata(
            name="concept_embeddings",
            version="1.0.0",
            description="Extended concept embeddings: hierarchies, relationships, domain-specific",
            operations=[
                "embed_concept",
                "find_related",
                "build_hierarchy",
                "semantic_similarity",
                "get_concept_neighbors",
                "find_hyponyms",
                "find_hypernyms",
            ],
            dependencies=["sentence-transformers", "numpy", "scikit-learn"],
            model_required=True,
        )

    def initialize(self) -> bool:
        """Initialize the module"""
        # Load config lazily on first use
        if self.config is None:
            self._load_config()
        # Always return True - dependencies are checked at runtime
        # Packages are installed in venv managed by PythonEnvironmentService
        # Try to initialize base embeddings, but don't fail if it doesn't work
        try:
            self._initialize_base_embeddings()
        except Exception:
            pass  # Module can still work without base embeddings
        return True

    def _load_config(self):
        """Load concept embeddings configuration"""
        config_path = Path(__file__).parent / "concept_embeddings_config.json"
        try:
            if config_path.exists():
                with open(config_path, "r", encoding="utf-8") as f:
                    self.config = json.load(f)
            else:
                # Default config
                self.config = {
                    "concept_relations": {
                        "hyponymy": "is_a_kind_of",
                        "meronymy": "is_a_part_of",
                        "synonymy": "means_the_same_as",
                        "antonymy": "means_the_opposite_of",
                        "causality": "causes",
                        "temporal": "happens_before",
                    },
                    "domains": [
                        "scientific",
                        "technical",
                        "social",
                        "emotional",
                        "abstract",
                    ],
                }
        except Exception as e:
            logger.warning(
                "Failed to load concept_embeddings config; using empty defaults",
                exc_info=True,
                extra={"module_name": "concept_embeddings", "error_type": type(e).__name__},
            )
            self.config = {}

    def _initialize_base_embeddings(self) -> bool:
        """Initialize base embeddings module (optional)"""
        if not _lazy_import_embeddings() or EmbeddingsModule is None:
            return False

        try:
            self.base_embeddings = EmbeddingsModule()
            # initialize() should return True if dependencies are available
            init_result = self.base_embeddings.initialize()
            return init_result
        except Exception as e:
            logger.debug(
                "Failed to initialize base embeddings for concept_embeddings",
                exc_info=True,
                extra={"module_name": "concept_embeddings", "error_type": type(e).__name__},
            )
        return False

    def execute(self, operation: str, params: Dict[str, Any]) -> Dict[str, Any]:
        """Execute a concept embeddings operation"""
        if operation == "embed_concept":
            concept = params.get("concept", "")
            domain = params.get("domain", "general")
            return self.embed_concept(concept, domain)
        elif operation == "find_related":
            concept = params.get("concept", "")
            relation_type = params.get("relation_type", "all")
            limit = params.get("limit", 10)
            return self.find_related(concept, relation_type, limit)
        elif operation == "build_hierarchy":
            concepts = params.get("concepts", [])
            domain = params.get("domain", "general")
            return self.build_hierarchy(concepts, domain)
        elif operation == "semantic_similarity":
            concept1 = params.get("concept1", "")
            concept2 = params.get("concept2", "")
            return self.semantic_similarity(concept1, concept2)
        elif operation == "get_concept_neighbors":
            concept = params.get("concept", "")
            k = params.get("k", 5)
            return self.get_concept_neighbors(concept, k)
        elif operation == "find_hyponyms":
            concept = params.get("concept", "")
            return self.find_hyponyms(concept)
        elif operation == "find_hypernyms":
            concept = params.get("concept", "")
            return self.find_hypernyms(concept)
        else:
            raise InvalidParameterError(
                parameter="operation",
                value=operation,
                reason="Unknown operation for concept_embeddings",
            )

    def embed_concept(self, concept: str, domain: str = "general") -> Dict[str, Any]:
        """Generate embedding for a concept"""
        if not self.base_embeddings:
            return {
                "error": "Base embeddings module not available",
                "embedding": None,
                "concept": concept,
            }

        try:
            result = self.base_embeddings.execute(
                "generate", {"text": concept, "model_name": None}
            )

            embedding = result.get("embedding")

            # Store domain-specific embedding if domain specified
            if domain != "general" and embedding:
                if domain not in self.domain_embeddings:
                    self.domain_embeddings[domain] = {}
                self.domain_embeddings[domain][concept] = embedding

            return {
                "embedding": embedding,
                "dimension": len(embedding) if embedding else 0,
                "concept": concept,
                "domain": domain,
            }
        except Exception as e:
            return {"error": str(e), "embedding": None, "concept": concept}

    def find_related(
        self, concept: str, relation_type: str = "all", limit: int = 10
    ) -> Dict[str, Any]:
        """Find related concepts based on semantic relationships"""
        related = []

        # Check concept relationships
        if concept in self.concept_relationships:
            for relation, targets in self.concept_relationships[concept].items():
                if relation_type == "all" or relation == relation_type:
                    for target, weight in targets:
                        related.append(
                            {
                                "concept": target,
                                "relation": relation,
                                "weight": weight,
                                "type": "explicit",
                            }
                        )

        # Use semantic similarity if embeddings available
        if self.base_embeddings and NUMPY_AVAILABLE:
            try:
                # Get embedding for concept
                embed_result = self.embed_concept(concept)
                if embed_result.get("embedding"):
                    # For now, return similarity-based results
                    # In a full implementation, this would compare against a knowledge base
                    related.append(
                        {
                            "concept": f"semantically_similar_to_{concept}",
                            "relation": "semantic_similarity",
                            "weight": 0.7,
                            "type": "semantic",
                        }
                    )
            except Exception:
                pass

        # Sort by weight and limit
        related.sort(key=lambda x: x.get("weight", 0), reverse=True)
        related = related[:limit]

        return {
            "concept": concept,
            "related": related,
            "count": len(related),
            "relation_type": relation_type,
        }

    def build_hierarchy(
        self, concepts: List[str], domain: str = "general"
    ) -> Dict[str, Any]:
        """Build concept hierarchy from a list of concepts"""
        if not concepts:
            return {"hierarchy": {}, "roots": [], "levels": 0}

        # Generate embeddings for all concepts
        embeddings_map = {}
        for concept in concepts:
            embed_result = self.embed_concept(concept, domain)
            if embed_result.get("embedding"):
                embeddings_map[concept] = embed_result["embedding"]

        # Simple hierarchy building based on semantic similarity
        # In a full implementation, this would use more sophisticated clustering
        hierarchy = {}
        roots = []

        if NUMPY_AVAILABLE and embeddings_map:
            # Find most general concepts (furthest from average)
            if len(embeddings_map) > 1:
                # Simple approach: mark concepts that are similar as siblings
                for concept1, emb1 in embeddings_map.items():
                    if concept1 not in hierarchy:
                        hierarchy[concept1] = {
                            "children": [],
                            "parents": [],
                            "siblings": [],
                            "level": 0,
                        }

                    # Find similar concepts as siblings
                    for concept2, emb2 in embeddings_map.items():
                        if concept1 != concept2:
                            similarity = self._cosine_similarity(emb1, emb2)
                            if similarity > 0.7:  # Threshold for sibling relationship
                                if concept2 not in hierarchy[concept1]["siblings"]:
                                    hierarchy[concept1]["siblings"].append(concept2)

                # Mark concepts with no siblings or few connections as potential roots
                for concept, data in hierarchy.items():
                    if len(data["siblings"]) == 0 or len(data["siblings"]) <= 1:
                        roots.append(concept)
            else:
                roots = list(embeddings_map.keys())
                for concept in roots:
                    hierarchy[concept] = {
                        "children": [],
                        "parents": [],
                        "siblings": [],
                        "level": 0,
                    }

        return {
            "hierarchy": hierarchy,
            "roots": roots if roots else list(concepts[:1]),
            "levels": self._calculate_hierarchy_levels(hierarchy),
            "concept_count": len(concepts),
        }

    def _cosine_similarity(self, vec1: List[float], vec2: List[float]) -> float:
        """Calculate cosine similarity between two vectors"""
        if not NUMPY_AVAILABLE:
            # Simple dot product implementation
            if len(vec1) != len(vec2):
                return 0.0
            dot = sum(a * b for a, b in zip(vec1, vec2))
            norm1 = sum(a * a for a in vec1) ** 0.5
            norm2 = sum(b * b for b in vec2) ** 0.5
            if norm1 == 0 or norm2 == 0:
                return 0.0
            return dot / (norm1 * norm2)

        try:
            vec1_arr = np.array(vec1).reshape(1, -1)
            vec2_arr = np.array(vec2).reshape(1, -1)
            similarity = cosine_similarity(vec1_arr, vec2_arr)[0][0]
            return float(similarity)
        except Exception:
            return 0.0

    def _calculate_hierarchy_levels(self, hierarchy: Dict[str, Any]) -> int:
        """Calculate number of levels in hierarchy"""
        if not hierarchy:
            return 0

        max_level = 0
        for concept, data in hierarchy.items():
            level = data.get("level", 0)
            max_level = max(max_level, level)

        return max_level + 1

    def semantic_similarity(self, concept1: str, concept2: str) -> Dict[str, Any]:
        """Calculate semantic similarity between two concepts"""
        if not self.base_embeddings:
            return {
                "similarity": 0.0,
                "concept1": concept1,
                "concept2": concept2,
                "error": "Base embeddings not available",
            }

        try:
            # Get embeddings
            emb1_result = self.embed_concept(concept1)
            emb2_result = self.embed_concept(concept2)

            emb1 = emb1_result.get("embedding")
            emb2 = emb2_result.get("embedding")

            if not emb1 or not emb2:
                return {
                    "similarity": 0.0,
                    "concept1": concept1,
                    "concept2": concept2,
                    "error": "Failed to generate embeddings",
                }

            similarity = self._cosine_similarity(emb1, emb2)

            return {
                "similarity": similarity,
                "concept1": concept1,
                "concept2": concept2,
                "interpretation": self._interpret_similarity(similarity),
            }
        except Exception as e:
            return {
                "similarity": 0.0,
                "concept1": concept1,
                "concept2": concept2,
                "error": str(e),
            }

    def _interpret_similarity(self, similarity: float) -> str:
        """Interpret similarity score"""
        if similarity >= 0.9:
            return "very_similar"
        elif similarity >= 0.7:
            return "similar"
        elif similarity >= 0.5:
            return "moderately_related"
        elif similarity >= 0.3:
            return "weakly_related"
        else:
            return "unrelated"

    def get_concept_neighbors(self, concept: str, k: int = 5) -> Dict[str, Any]:
        """Get k nearest neighbor concepts"""
        related_result = self.find_related(concept, relation_type="all", limit=k)

        return {
            "concept": concept,
            "neighbors": related_result.get("related", []),
            "count": len(related_result.get("related", [])),
        }

    def find_hyponyms(self, concept: str) -> Dict[str, Any]:
        """Find hyponyms (more specific concepts)"""
        related_result = self.find_related(concept, relation_type="hyponymy", limit=20)
        hyponyms = [
            r["concept"]
            for r in related_result.get("related", [])
            if r.get("relation") == "hyponymy"
        ]

        return {"concept": concept, "hyponyms": hyponyms, "count": len(hyponyms)}

    def find_hypernyms(self, concept: str) -> Dict[str, Any]:
        """Find hypernyms (more general concepts)"""
        # In a full implementation, this would search for concepts where this is a hyponym
        # For now, return related concepts with reverse hyponymy relation
        related_result = self.find_related(concept, relation_type="all", limit=20)
        hypernyms = [
            r["concept"]
            for r in related_result.get("related", [])
            if r.get("relation") in ["hypernymy", "is_a_kind_of"]
        ]

        return {"concept": concept, "hypernyms": hypernyms, "count": len(hypernyms)}

    def add_relationship(
        self, concept1: str, concept2: str, relation_type: str, weight: float = 1.0
    ):
        """Add a relationship between two concepts (for knowledge base building)"""
        if concept1 not in self.concept_relationships:
            self.concept_relationships[concept1] = defaultdict(list)

        self.concept_relationships[concept1][relation_type].append((concept2, weight))

    def validate_params(self, operation: str, params: Dict[str, Any]) -> bool:
        """Validate parameters for operations"""
        if operation == "embed_concept":
            return "concept" in params
        elif operation == "find_related":
            return "concept" in params
        elif operation == "build_hierarchy":
            return "concepts" in params
        elif operation == "semantic_similarity":
            return "concept1" in params and "concept2" in params
        elif operation == "get_concept_neighbors":
            return "concept" in params
        elif operation == "find_hyponyms" or operation == "find_hypernyms":
            return "concept" in params
        return True
