"""
Memory Processor Module - Pandas-based data processing
Handles data cleaning, deduplication, clustering, pattern finding, and relevance scoring
"""

from __future__ import annotations

from collections import Counter
from datetime import datetime, timedelta
from typing import Any, Dict, List
import json
import math
import re
import logging

# Optional imports - handle gracefully if dependencies not available
try:
    import numpy as np
    import pandas as pd
    from sklearn.cluster import DBSCAN, KMeans
    from sklearn.feature_extraction.text import TfidfVectorizer
    from sklearn.preprocessing import StandardScaler
    MEMORY_PROCESSOR_AVAILABLE = True
except ImportError:
    MEMORY_PROCESSOR_AVAILABLE = False
    np = None
    pd = None
    DBSCAN = None
    KMeans = None
    TfidfVectorizer = None
    StandardScaler = None

from mavaia_core.brain.base_module import BaseBrainModule, ModuleMetadata
from mavaia_core.exceptions import InvalidParameterError

logger = logging.getLogger(__name__)


class MemoryProcessor(BaseBrainModule):
    """Processes memory data using Pandas for cleaning, clustering, and pattern finding"""

    @property
    def metadata(self) -> ModuleMetadata:
        return ModuleMetadata(
            name="memory_processor",
            version="1.0.0",
            description=(
                "Processes memory data using Pandas: cleaning, deduplication, "
                "clustering, pattern finding"
            ),
            operations=[
                "process_memories",
                "clean_and_deduplicate",
                "cluster_memories",
                "extract_patterns",
                "detect_outliers",
                "extract_tags",
                "score_relevance",
                "export_for_neo4j",
                "semantic_cluster_memories",
                "calculate_priority_scores",
                "apply_forgetting_curve",
                "build_recency_weighted_context",
            ],
            dependencies=["pandas", "numpy", "scikit-learn"],
            enabled=True,
            model_required=False,
        )

    def initialize(self) -> bool:
        """Initialize the module"""
        if not MEMORY_PROCESSOR_AVAILABLE:
            logger.warning(
                "Optional dependencies not available (numpy/pandas/scikit-learn); memory_processor will be disabled",
                extra={"module_name": "memory_processor"},
            )
        return True  # Always return True - execute() will handle missing dependencies

    def execute(self, operation: str, params: Dict[str, Any]) -> Dict[str, Any]:
        """Execute memory processing operations"""
        if not MEMORY_PROCESSOR_AVAILABLE:
            return {
                "success": False,
                "error": "Dependencies not available (numpy/pandas/scikit-learn)",
                "operation": operation,
            }
        match operation:
            case "process_memories":
                memories_json = params.get("memories_json", "[]")
                return self.process_memories(memories_json)
            case "clean_and_deduplicate":
                memories_json = params.get("memories_json", "[]")
                return self.clean_and_deduplicate(memories_json)
            case "cluster_memories":
                memories_json = params.get("memories_json", "[]")
                method = params.get("method", "kmeans")
                n_clusters = params.get("n_clusters", 5)
                return self.cluster_memories(memories_json, method, n_clusters)
            case "extract_patterns":
                memories_json = params.get("memories_json", "[]")
                return self.extract_patterns(memories_json)
            case "detect_outliers":
                memories_json = params.get("memories_json", "[]")
                return self.detect_outliers(memories_json)
            case "extract_tags":
                memories_json = params.get("memories_json", "[]")
                return self.extract_tags(memories_json)
            case "score_relevance":
                memories_json = params.get("memories_json", "[]")
                query = params.get("query", "")
                return self.score_relevance(memories_json, query)
            case "export_for_neo4j":
                memories_json = params.get("memories_json", "[]")
                return self.export_for_neo4j(memories_json)
            case "semantic_cluster_memories":
                memories_json = params.get("memories_json", "[]")
                return self.semantic_cluster_memories(memories_json)
            case "calculate_priority_scores":
                memories_json = params.get("memories_json", "[]")
                return self.calculate_priority_scores(memories_json)
            case "apply_forgetting_curve":
                memories_json = params.get("memories_json", "[]")
                return self.apply_forgetting_curve(memories_json)
            case "build_recency_weighted_context":
                memories_json = params.get("memories_json", "[]")
                query = params.get("query", "")
                max_memories = params.get("max_memories", 10)
                return self.build_recency_weighted_context(memories_json, query, max_memories)
            case _:
                raise InvalidParameterError(
                    parameter="operation",
                    value=operation,
                    reason="Unknown operation for memory_processor",
                )

    def process_memories(self, memories_json: str) -> Dict[str, Any]:
        """Main processing pipeline: clean, deduplicate, cluster, extract patterns"""
        try:
            memories = (
                json.loads(memories_json)
                if isinstance(memories_json, str)
                else memories_json
            )
            df = pd.DataFrame(memories)

            if df.empty:
                return {
                    "success": True,
                    "result": {
                        "processed_count": 0,
                        "cleaned_count": 0,
                        "clusters": [],
                        "patterns": {},
                    },
                }

            # Clean and deduplicate
            df_cleaned = self._clean_dataframe(df)
            df_deduped = self._deduplicate(df_cleaned)

            # Cluster
            clusters = self._cluster_dataframe(df_deduped)

            # Extract patterns
            patterns = self._extract_patterns_from_df(df_deduped)

            # Extract tags
            df_tagged = self._extract_tags_from_df(df_deduped)

            # Convert back to dict
            processed = df_tagged.to_dict("records")

            return {
                "success": True,
                "result": {
                    "processed_count": len(processed),
                    "cleaned_count": len(df_deduped),
                    "clusters": clusters,
                    "patterns": patterns,
                    "memories": processed,
                },
            }
        except Exception as e:
            return {"success": False, "error": str(e)}

    def clean_and_deduplicate(self, memories_json: str) -> Dict[str, Any]:
        """Clean and deduplicate memories"""
        try:
            memories = (
                json.loads(memories_json)
                if isinstance(memories_json, str)
                else memories_json
            )
            df = pd.DataFrame(memories)

            df_cleaned = self._clean_dataframe(df)
            df_deduped = self._deduplicate(df_cleaned)

            return {
                "success": True,
                "result": {
                    "original_count": len(df),
                    "cleaned_count": len(df_deduped),
                    "removed_count": len(df) - len(df_deduped),
                    "memories": df_deduped.to_dict("records"),
                },
            }
        except Exception as e:
            return {"success": False, "error": str(e)}

    def cluster_memories(
        self, memories_json: str, method: str = "kmeans", n_clusters: int = 5
    ) -> Dict[str, Any]:
        """Cluster memories using K-means or DBSCAN"""
        try:
            memories = (
                json.loads(memories_json)
                if isinstance(memories_json, str)
                else memories_json
            )
            df = pd.DataFrame(memories)

            clusters = self._cluster_dataframe(df, method, n_clusters)

            return {
                "success": True,
                "result": {
                    "method": method,
                    "n_clusters": len(clusters),
                    "clusters": clusters,
                },
            }
        except Exception as e:
            return {"success": False, "error": str(e)}

    def extract_patterns(self, memories_json: str) -> Dict[str, Any]:
        """Extract statistical patterns from memories"""
        try:
            memories = (
                json.loads(memories_json)
                if isinstance(memories_json, str)
                else memories_json
            )
            df = pd.DataFrame(memories)

            patterns = self._extract_patterns_from_df(df)

            return {"success": True, "result": patterns}
        except Exception as e:
            return {"success": False, "error": str(e)}

    def detect_outliers(self, memories_json: str) -> Dict[str, Any]:
        """Detect outlier memories"""
        try:
            memories = (
                json.loads(memories_json)
                if isinstance(memories_json, str)
                else memories_json
            )
            df = pd.DataFrame(memories)

            outliers = self._detect_outliers_in_df(df)

            return {
                "success": True,
                "result": {"outlier_count": len(outliers), "outliers": outliers},
            }
        except Exception as e:
            return {"success": False, "error": str(e)}

    def extract_tags(self, memories_json: str) -> Dict[str, Any]:
        """Extract and assign tags to memories"""
        try:
            memories = (
                json.loads(memories_json)
                if isinstance(memories_json, str)
                else memories_json
            )
            df = pd.DataFrame(memories)

            df_tagged = self._extract_tags_from_df(df)

            return {
                "success": True,
                "result": {
                    "tagged_count": len(df_tagged),
                    "memories": df_tagged.to_dict("records"),
                },
            }
        except Exception as e:
            return {"success": False, "error": str(e)}

    def score_relevance(self, memories_json: str, query: str = "") -> Dict[str, Any]:
        """Score memories by relevance to a query"""
        try:
            memories = (
                json.loads(memories_json)
                if isinstance(memories_json, str)
                else memories_json
            )
            df = pd.DataFrame(memories)

            if query:
                df_scored = self._score_relevance_to_query(df, query)
            else:
                # Score by importance and recency
                df_scored = self._score_by_importance_recency(df)

            # Sort by score
            df_scored = df_scored.sort_values("relevance_score", ascending=False)

            return {
                "success": True,
                "result": {
                    "scored_count": len(df_scored),
                    "memories": df_scored.to_dict("records"),
                },
            }
        except Exception as e:
            return {"success": False, "error": str(e)}

    def export_for_neo4j(self, memories_json: str) -> Dict[str, Any]:
        """Export processed memories in format suitable for Neo4j"""
        try:
            memories = (
                json.loads(memories_json)
                if isinstance(memories_json, str)
                else memories_json
            )
            df = pd.DataFrame(memories)

            # Prepare nodes (memories)
            nodes = []
            for _, row in df.iterrows():
                node = {
                    "id": row.get("id", ""),
                    "type": row.get("type", "memory"),
                    "content": row.get("content", ""),
                    "importance": row.get("importance", 0.5),
                    "tags": row.get("tags", []),
                    "keywords": row.get("keywords", []),
                }
                nodes.append(node)

            # Prepare relationships (based on keywords/tags similarity)
            relationships = self._generate_relationships(df)

            return {
                "success": True,
                "result": {"nodes": nodes, "relationships": relationships},
            }
        except Exception as e:
            return {"success": False, "error": str(e)}

    # Private helper methods

    def _clean_dataframe(self, df: pd.DataFrame) -> pd.DataFrame:
        """Clean the dataframe"""
        df = df.copy()

        # Remove rows with empty content
        df = df[df["content"].notna() & (df["content"].str.strip() != "")]

        # Clean content (remove extra whitespace)
        if "content" in df.columns:
            df["content"] = df["content"].str.strip()
            df["content"] = df["content"].str.replace(r"\s+", " ", regex=True)

        # Fill missing values
        df["importance"] = df["importance"].fillna(0.5)
        df["tags"] = (
            df["tags"].fillna("").apply(lambda x: x if isinstance(x, list) else [])
        )
        df["keywords"] = (
            df["keywords"].fillna("").apply(lambda x: x if isinstance(x, list) else [])
        )

        return df

    def _deduplicate(self, df: pd.DataFrame) -> pd.DataFrame:
        """Remove duplicate memories"""
        # Deduplicate by content similarity
        df = df.copy()

        # Simple deduplication: exact content match
        df = df.drop_duplicates(subset=["content"], keep="first")

        # More sophisticated: similarity-based (would need embeddings)
        # For now, just exact match

        return df

    def _cluster_dataframe(
        self, df: pd.DataFrame, method: str = "kmeans", n_clusters: int = 5
    ) -> List[Dict[str, Any]]:
        """Cluster memories"""
        if len(df) < n_clusters:
            n_clusters = max(1, len(df))

        try:
            # Create feature vectors from content
            vectorizer = TfidfVectorizer(max_features=100, stop_words="english")
            content_texts = df["content"].fillna("").astype(str)
            X = vectorizer.fit_transform(content_texts)

            if method == "kmeans":
                clusterer = KMeans(n_clusters=n_clusters, random_state=42, n_init=10)
                labels = clusterer.fit_predict(X)
            elif method == "dbscan":
                clusterer = DBSCAN(eps=0.5, min_samples=2)
                labels = clusterer.fit_predict(X)
            else:
                labels = [0] * len(df)

            # Group by cluster
            df["cluster"] = labels
            clusters = []

            for cluster_id in set(labels):
                if cluster_id == -1:  # DBSCAN noise
                    continue
                cluster_memories = df[df["cluster"] == cluster_id]
                clusters.append(
                    {
                        "cluster_id": int(cluster_id),
                        "size": len(cluster_memories),
                        "memory_ids": (
                            cluster_memories["id"].tolist()
                            if "id" in cluster_memories.columns
                            else []
                        ),
                    }
                )

            return clusters
        except Exception as e:
            # Fallback: return single cluster
            return [
                {
                    "cluster_id": 0,
                    "size": len(df),
                    "memory_ids": df["id"].tolist() if "id" in df.columns else [],
                }
            ]

    def _extract_patterns_from_df(self, df: pd.DataFrame) -> Dict[str, Any]:
        """Extract statistical patterns"""
        patterns = {}

        # Type distribution
        if "type" in df.columns:
            patterns["type_distribution"] = df["type"].value_counts().to_dict()

        # Importance statistics
        if "importance" in df.columns:
            patterns["importance_stats"] = {
                "mean": float(df["importance"].mean()),
                "std": float(df["importance"].std()),
                "min": float(df["importance"].min()),
                "max": float(df["importance"].max()),
            }

        # Most common keywords
        if "keywords" in df.columns:
            all_keywords = []
            for keywords in df["keywords"]:
                if isinstance(keywords, list):
                    all_keywords.extend(keywords)
            patterns["top_keywords"] = dict(Counter(all_keywords).most_common(10))

        # Most common tags
        if "tags" in df.columns:
            all_tags = []
            for tags in df["tags"]:
                if isinstance(tags, list):
                    all_tags.extend(tags)
            patterns["top_tags"] = dict(Counter(all_tags).most_common(10))

        return patterns

    def _detect_outliers_in_df(self, df: pd.DataFrame) -> List[Dict[str, Any]]:
        """Detect outlier memories"""
        outliers = []

        if "importance" in df.columns and len(df) > 1:
            # Use IQR method
            Q1 = df["importance"].quantile(0.25)
            Q3 = df["importance"].quantile(0.75)
            IQR = Q3 - Q1
            lower_bound = Q1 - 1.5 * IQR
            upper_bound = Q3 + 1.5 * IQR

            outlier_df = df[
                (df["importance"] < lower_bound) | (df["importance"] > upper_bound)
            ]

            for _, row in outlier_df.iterrows():
                outliers.append(
                    {
                        "id": row.get("id", ""),
                        "importance": float(row["importance"]),
                        "reason": "importance_outlier",
                    }
                )

        return outliers

    def _extract_tags_from_df(self, df: pd.DataFrame) -> pd.DataFrame:
        """Extract and assign tags to memories"""
        df = df.copy()

        # If tags already exist, keep them
        if "tags" not in df.columns:
            df["tags"] = [[] for _ in range(len(df))]

        # Extract tags from content if missing
        for idx, row in df.iterrows():
            tags = row.get("tags", [])
            if not tags or len(tags) == 0:
                # Simple tag extraction: use keywords or extract from content
                content = str(row.get("content", ""))
                # Extract potential tags (capitalized words, short phrases)
                words = re.findall(r"\b[A-Z][a-z]+\b", content)
                tags = list(set(words[:5]))  # Limit to 5 tags
                df.at[idx, "tags"] = tags

        return df

    def _score_relevance_to_query(self, df: pd.DataFrame, query: str) -> pd.DataFrame:
        """Score memories by relevance to query"""
        df = df.copy()

        query_lower = query.lower()
        scores = []

        for _, row in df.iterrows():
            score = 0.0
            content = str(row.get("content", "")).lower()

            # Exact match
            if query_lower in content:
                score += 0.5

            # Keyword matches
            query_words = query_lower.split()
            matches = sum(1 for word in query_words if word in content)
            score += (matches / len(query_words)) * 0.3 if query_words else 0

            # Tag/keyword matches
            tags = row.get("tags", [])
            keywords = row.get("keywords", [])
            all_terms = [str(t).lower() for t in tags + keywords]
            tag_matches = sum(1 for word in query_words if word in all_terms)
            score += (tag_matches / len(query_words)) * 0.2 if query_words else 0

            scores.append(score)

        df["relevance_score"] = scores
        return df

    def _score_by_importance_recency(self, df: pd.DataFrame) -> pd.DataFrame:
        """Score by importance and recency"""
        df = df.copy()

        # Normalize importance (0-1)
        if "importance" in df.columns:
            importance_scores = df["importance"].fillna(0.5)
        else:
            importance_scores = pd.Series([0.5] * len(df))

        # Recency score (if lastAccessed exists)
        if "lastAccessed" in df.columns:
            # Convert to datetime if needed
            try:
                last_accessed = pd.to_datetime(df["lastAccessed"])
                now = pd.Timestamp.now()
                days_ago = (now - last_accessed).dt.days
                recency_scores = 1.0 / (1.0 + days_ago / 30.0)  # Decay over 30 days
            except:
                recency_scores = pd.Series([0.5] * len(df))
        else:
            recency_scores = pd.Series([0.5] * len(df))

        # Combined score
        df["relevance_score"] = importance_scores * 0.6 + recency_scores * 0.4

        return df

    def _generate_relationships(self, df: pd.DataFrame) -> List[Dict[str, Any]]:
        """Generate relationships between memories based on similarity"""
        relationships = []

        # Simple relationship: memories with shared keywords/tags
        for i, row1 in df.iterrows():
            id1 = row1.get("id", "")
            tags1 = set(row1.get("tags", []))
            keywords1 = set(row1.get("keywords", []))

            for j, row2 in df.iterrows():
                if i >= j:  # Avoid duplicates
                    continue

                id2 = row2.get("id", "")
                tags2 = set(row2.get("tags", []))
                keywords2 = set(row2.get("keywords", []))

                # Calculate similarity
                shared_tags = len(tags1 & tags2)
                shared_keywords = len(keywords1 & keywords2)

                if shared_tags > 0 or shared_keywords > 0:
                    strength = (shared_tags * 0.5 + shared_keywords * 0.3) / 10.0
                    strength = min(1.0, strength)

                    relationships.append(
                        {
                            "source": id1,
                            "target": id2,
                            "type": "related",
                            "strength": float(strength),
                        }
                    )

        return relationships

    def semantic_cluster_memories(self, memories_json: str) -> Dict[str, Any]:
        """Semantic clustering of memories using embeddings and similarity"""
        try:
            memories = (
                json.loads(memories_json)
                if isinstance(memories_json, str)
                else memories_json
            )
            df = pd.DataFrame(memories)

            if df.empty:
                return {
                    "success": True,
                    "result": {"clusters": [], "cluster_count": 0},
                }

            # Use TF-IDF for semantic similarity
            vectorizer = TfidfVectorizer(max_features=100, stop_words="english")
            content_texts = df["content"].fillna("").astype(str)
            tfidf_matrix = vectorizer.fit_transform(content_texts)

            # Use DBSCAN for semantic clustering (better for unknown cluster count)
            clustering = DBSCAN(eps=0.3, min_samples=2, metric="cosine")
            cluster_labels = clustering.fit_predict(tfidf_matrix.toarray())

            df["semantic_cluster"] = cluster_labels

            # Group by cluster
            clusters = []
            for cluster_id in set(cluster_labels):
                if cluster_id == -1:  # Noise points
                    continue
                cluster_memories = df[df["semantic_cluster"] == cluster_id]
                clusters.append(
                    {
                        "cluster_id": int(cluster_id),
                        "size": len(cluster_memories),
                        "memories": cluster_memories.to_dict("records"),
                        "themes": self._extract_cluster_themes(cluster_memories),
                    }
                )

            return {
                "success": True,
                "result": {
                    "clusters": clusters,
                    "cluster_count": len(clusters),
                    "noise_count": int((cluster_labels == -1).sum()),
                },
            }
        except Exception as e:
            return {"success": False, "error": str(e)}

    def calculate_priority_scores(
        self, memories_json: str
    ) -> Dict[str, Any]:
        """Calculate priority scores for memories based on importance,
        recency, and access frequency"""
        try:
            memories = (
                json.loads(memories_json)
                if isinstance(memories_json, str)
                else memories_json
            )
            df = pd.DataFrame(memories)

            if df.empty:
                return {
                    "success": True,
                    "result": {"memories": [], "scored_count": 0},
                }

            # Importance score (0-1)
            importance_scores = df["importance"].fillna(0.5).clip(0, 1)

            # Recency score (0-1) - more recent = higher score
            if "lastAccessed" in df.columns:
                try:
                    last_accessed = pd.to_datetime(df["lastAccessed"])
                    now = pd.Timestamp.now()
                    days_ago = (now - last_accessed).dt.days
                    recency_scores = 1.0 / (1.0 + days_ago / 7.0)  # Decay over 7 days
                except Exception:
                    recency_scores = pd.Series([0.5] * len(df))
            else:
                recency_scores = pd.Series([0.5] * len(df))

            # Access frequency score (0-1)
            if "accessCount" in df.columns:
                access_counts = df["accessCount"].fillna(0)
                max_access = access_counts.max() if access_counts.max() > 0 else 1
                frequency_scores = (access_counts / max_access).clip(0, 1)
            else:
                frequency_scores = pd.Series([0.5] * len(df))

            # Combined priority score (weighted)
            priority_scores = (
                importance_scores * 0.4
                + recency_scores * 0.35
                + frequency_scores * 0.25
            )

            df["priority_score"] = priority_scores
            df = df.sort_values("priority_score", ascending=False)

            return {
                "success": True,
                "result": {
                    "memories": df.to_dict("records"),
                    "scored_count": len(df),
                    "avg_priority": float(priority_scores.mean()),
                },
            }
        except Exception as e:
            return {"success": False, "error": str(e)}

    def apply_forgetting_curve(self, memories_json: str) -> Dict[str, Any]:
        """Apply Ebbinghaus forgetting curve to memory retention scores"""
        try:
            memories = (
                json.loads(memories_json)
                if isinstance(memories_json, str)
                else memories_json
            )
            df = pd.DataFrame(memories)

            if df.empty:
                return {
                    "success": True,
                    "result": {"memories": [], "retention_scores": []},
                }

            # Ebbinghaus forgetting curve: R = e^(-t/S)
            # where R = retention, t = time since encoding, S = strength
            retention_scores = []

            for _, row in df.iterrows():
                # Get time since encoding
                if "createdAt" in row and pd.notna(row["createdAt"]):
                    try:
                        created_at = pd.to_datetime(row["createdAt"])
                        now = pd.Timestamp.now()
                        hours_ago = (now - created_at).total_seconds() / 3600
                    except Exception:
                        hours_ago = 24  # Default to 24 hours
                else:
                    hours_ago = 24

                # Memory strength based on importance and access frequency
                importance = float(row.get("importance", 0.5))
                access_count = float(row.get("accessCount", 0))
                strength = importance * 0.7 + min(access_count / 10.0, 1.0) * 0.3

                # Apply forgetting curve
                # S parameter: stronger memories decay slower
                # Base decay rate: 24 hours for 50% retention
                s_parameter = 24.0 * (1.0 + strength * 2.0)  # Stronger = slower decay
                retention = math.exp(-hours_ago / s_parameter)

                retention_scores.append({
                    "memory_id": row.get("id", ""),
                    "retention_score": float(retention),
                    "hours_since_encoding": float(hours_ago),
                    "memory_strength": float(strength),
                })

            df["retention_score"] = [r["retention_score"] for r in retention_scores]
            df = df.sort_values("retention_score", ascending=False)

            return {
                "success": True,
                "result": {
                    "memories": df.to_dict("records"),
                    "retention_scores": retention_scores,
                    "avg_retention": float(df["retention_score"].mean()),
                },
            }
        except Exception as e:
            return {"success": False, "error": str(e)}

    def build_recency_weighted_context(
        self, memories_json: str, query: str = "", max_memories: int = 10
    ) -> Dict[str, Any]:
        """Build context from memories weighted by recency, relevance, and retention"""
        try:
            memories = (
                json.loads(memories_json)
                if isinstance(memories_json, str)
                else memories_json
            )
            df = pd.DataFrame(memories)

            if df.empty:
                return {
                    "success": True,
                    "result": {
                        "context": "",
                        "selected_memories": [],
                        "selected_count": 0,
                    },
                }

            # Calculate relevance scores if query provided
            if query:
                df = self._score_relevance_to_query(df, query)
            else:
                df = self._score_by_importance_recency(df)

            # Apply forgetting curve
            retention_result = self.apply_forgetting_curve(
                df.to_dict("records")
            )
            if retention_result["success"]:
                retention_df = pd.DataFrame(retention_result["result"]["memories"])
                if "retention_score" in retention_df.columns:
                    df["retention_score"] = retention_df["retention_score"]
                else:
                    df["retention_score"] = 0.5
            else:
                df["retention_score"] = 0.5

            # Combined weighted score
            relevance = df.get("relevance_score", pd.Series([0.5] * len(df)))
            retention = df.get("retention_score", pd.Series([0.5] * len(df)))
            priority = df.get("priority_score", pd.Series([0.5] * len(df)))

            # Weighted combination: relevance (40%), retention (35%), priority (25%)
            combined_score = (
                relevance * 0.4 + retention * 0.35 + priority * 0.25
            )

            df["combined_score"] = combined_score
            df = df.sort_values("combined_score", ascending=False)

            # Select top memories
            selected = df.head(max_memories)

            # Build context string
            context_parts = []
            for _, row in selected.iterrows():
                content = str(row.get("content", ""))
                if content:
                    context_parts.append(content)

            context = "\n".join(context_parts)

            return {
                "success": True,
                "result": {
                    "context": context,
                    "selected_memories": selected.to_dict("records"),
                    "selected_count": len(selected),
                    "avg_score": float(combined_score.mean()),
                },
            }
        except Exception as e:
            return {"success": False, "error": str(e)}

    def _extract_cluster_themes(self, cluster_df: pd.DataFrame) -> List[str]:
        """Extract common themes from a cluster of memories"""
        if cluster_df.empty:
            return []

        # Extract keywords from all memories in cluster
        all_keywords = []
        for _, row in cluster_df.iterrows():
            keywords = row.get("keywords", [])
            if isinstance(keywords, list):
                all_keywords.extend(keywords)
            tags = row.get("tags", [])
            if isinstance(tags, list):
                all_keywords.extend(tags)

        # Count frequency
        keyword_counts = Counter(str(k).lower() for k in all_keywords)

        # Return top 5 themes
        return [word for word, _ in keyword_counts.most_common(5)]
