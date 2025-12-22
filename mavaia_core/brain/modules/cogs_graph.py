"""
COGS Graph Module - Context Object Graph System operations
Handles entity graph queries, relationship traversal, temporal context, and graph analytics
Uses NetworkX for graph operations (can extend to Neo4j if needed)
"""

import json
from typing import Dict, Any, List, Optional
from collections import defaultdict
from datetime import datetime
import logging

from mavaia_core.brain.base_module import BaseBrainModule, ModuleMetadata
from mavaia_core.exceptions import InvalidParameterError

logger = logging.getLogger(__name__)

# Optional imports
try:
    import networkx as nx

    NETWORKX_AVAILABLE = True
except ImportError:
    NETWORKX_AVAILABLE = False


class COGSGraph(BaseBrainModule):
    """Graph operations for Context Object Graph System"""

    def __init__(self):
        super().__init__()
        self.graph = None  # NetworkX graph
        self.entity_graph = None  # Separate graph for entities
        self.relationship_graph = None  # Separate graph for relationships
        self.is_initialized = False

    @property
    def metadata(self) -> ModuleMetadata:
        return ModuleMetadata(
            name="cogs_graph",
            version="1.0.0",
            description="Context Object Graph System: entity queries, relationship traversal, temporal context, analytics",
            operations=[
                "build_entity_graph",
                "find_entity_relationships",
                "traverse_entity_graph",
                "find_temporal_context",
                "get_entity_centrality",
                "find_entity_path",
                "cluster_entities",
                "get_graph_analytics",
            ],
            dependencies=["networkx"],
            enabled=True,
            model_required=False,
        )

    def initialize(self) -> bool:
        """Initialize graph structures"""
        if not NETWORKX_AVAILABLE:
            logger.debug(
                "networkx not available; cogs_graph will be disabled",
                extra={"module_name": "cogs_graph"},
            )
            self.is_initialized = False
            return False

        self.entity_graph = nx.DiGraph()
        self.relationship_graph = (
            nx.MultiDiGraph()
        )  # MultiDiGraph for multiple relationship types
        self.graph = nx.DiGraph()  # Combined graph
        self.is_initialized = True
        return True

    def execute(self, operation: str, params: Dict[str, Any]) -> Dict[str, Any]:
        """Execute COGS graph operations"""

        if not self.is_initialized:
            self.initialize()
        if not self.is_initialized or not NETWORKX_AVAILABLE:
            return {
                "success": False,
                "error": "Dependency not available: networkx",
                "operation": operation,
            }

        if operation == "build_entity_graph":
            entities_json = params.get("entities", "[]")
            relationships_json = params.get("relationships", "[]")
            return self.build_entity_graph(entities_json, relationships_json)

        elif operation == "find_entity_relationships":
            entity_id = params.get("entity_id", "")
            relationship_type = params.get("relationship_type", None)
            direction = params.get("direction", "both")
            depth = params.get("depth", 2)
            return self.find_entity_relationships(
                entity_id, relationship_type, direction, depth
            )

        elif operation == "traverse_entity_graph":
            start_id = params.get("start_id", "")
            max_hops = params.get("max_hops", 3)
            relationship_filter = params.get("relationship_filter", None)
            return self.traverse_entity_graph(start_id, max_hops, relationship_filter)

        elif operation == "find_temporal_context":
            entity_id = params.get("entity_id", "")
            time_range = params.get("time_range", None)
            return self.find_temporal_context(entity_id, time_range)

        elif operation == "get_entity_centrality":
            entity_id = params.get("entity_id", None)
            centrality_type = params.get("centrality_type", "degree")
            return self.get_entity_centrality(entity_id, centrality_type)

        elif operation == "find_entity_path":
            source_id = params.get("source_id", "")
            target_id = params.get("target_id", "")
            max_hops = params.get("max_hops", 5)
            return self.find_entity_path(source_id, target_id, max_hops)

        elif operation == "cluster_entities":
            entity_ids = params.get("entity_ids", [])
            method = params.get("method", "community")
            return self.cluster_entities(entity_ids, method)

        elif operation == "get_graph_analytics":
            return self.get_graph_analytics()

        else:
            raise InvalidParameterError(
                parameter="operation",
                value=operation,
                reason="Unknown operation for cogs_graph",
            )

    def build_entity_graph(
        self, entities_json: str, relationships_json: str
    ) -> Dict[str, Any]:
        """Build graph from entities and relationships"""
        try:
            entities = (
                json.loads(entities_json)
                if isinstance(entities_json, str)
                else entities_json
            )
            relationships = (
                json.loads(relationships_json)
                if isinstance(relationships_json, str)
                else relationships_json
            )

            # Clear existing graphs
            if self.entity_graph:
                self.entity_graph.clear()
            else:
                self.entity_graph = nx.DiGraph()

            if self.relationship_graph:
                self.relationship_graph.clear()
            else:
                self.relationship_graph = nx.MultiDiGraph()

            if self.graph:
                self.graph.clear()
            else:
                self.graph = nx.DiGraph()

            # Add entities as nodes
            for entity in entities:
                entity_id = entity.get("id", "")
                if entity_id:
                    node_attrs = {
                        "type": entity.get("entityType", "thing"),
                        "label": entity.get("label", ""),
                        "description": entity.get("description", ""),
                        "confidence": entity.get("confidence", 0.5),
                        "lastSeen": entity.get("lastSeen", ""),
                        "createdAt": entity.get("createdAt", ""),
                    }
                    self.entity_graph.add_node(entity_id, **node_attrs)
                    self.graph.add_node(entity_id, **node_attrs)

            # Add relationships as edges
            for rel in relationships:
                source_id = rel.get("sourceEntityId", "")
                target_id = rel.get("targetEntityId", "")
                rel_type = rel.get("relationshipType", "relatedTo")
                strength = rel.get("strength", 0.5)
                confidence = rel.get("confidence", 0.5)
                established_at = rel.get("establishedAt", "")
                is_active = rel.get("isActive", True)

                if source_id and target_id:
                    edge_attrs = {
                        "type": rel_type,
                        "strength": float(strength),
                        "confidence": float(confidence),
                        "establishedAt": established_at,
                        "isActive": is_active,
                    }
                    self.relationship_graph.add_edge(source_id, target_id, **edge_attrs)
                    self.graph.add_edge(source_id, target_id, **edge_attrs)

            return {
                "success": True,
                "result": {
                    "entities_count": self.entity_graph.number_of_nodes(),
                    "relationships_count": self.relationship_graph.number_of_edges(),
                    "message": "Entity graph built successfully",
                },
            }
        except Exception as e:
            return {"success": False, "error": str(e)}

    def find_entity_relationships(
        self,
        entity_id: str,
        relationship_type: Optional[str] = None,
        direction: str = "both",
        depth: int = 2,
    ) -> Dict[str, Any]:
        """Find relationships for an entity"""
        try:
            if not self.graph or entity_id not in self.graph:
                return {
                    "success": True,
                    "result": {
                        "entity_id": entity_id,
                        "relationships": [],
                        "depth": depth,
                    },
                }

            relationships = []
            visited = set()

            def traverse(node_id: str, current_depth: int, path: List[str]):
                if current_depth > depth or node_id in visited:
                    return

                visited.add(node_id)

                # Get neighbors based on direction
                neighbors = []
                if direction in ["outgoing", "both"]:
                    neighbors.extend(self.graph.successors(node_id))
                if direction in ["incoming", "both"]:
                    neighbors.extend(self.graph.predecessors(node_id))

                for neighbor in neighbors:
                    if node_id in self.graph and neighbor in self.graph[node_id]:
                        edge_data = self.graph[node_id][neighbor]
                        rel_type = edge_data.get("type", "relatedTo")

                        # Filter by relationship type if specified
                        if relationship_type and rel_type != relationship_type:
                            continue

                        strength = edge_data.get("strength", 0.5)
                        confidence = edge_data.get("confidence", 0.5)
                        is_active = edge_data.get("isActive", True)

                        relationships.append(
                            {
                                "source": (
                                    node_id if direction != "incoming" else neighbor
                                ),
                                "target": (
                                    neighbor if direction != "incoming" else node_id
                                ),
                                "type": rel_type,
                                "strength": float(strength),
                                "confidence": float(confidence),
                                "isActive": is_active,
                                "depth": current_depth,
                                "path": path + [node_id, neighbor],
                            }
                        )

                        if current_depth < depth:
                            traverse(neighbor, current_depth + 1, path + [node_id])

            traverse(entity_id, 1, [])

            return {
                "success": True,
                "result": {
                    "entity_id": entity_id,
                    "relationships": relationships,
                    "depth": depth,
                    "count": len(relationships),
                },
            }
        except Exception as e:
            return {"success": False, "error": str(e)}

    def traverse_entity_graph(
        self,
        start_id: str,
        max_hops: int = 3,
        relationship_filter: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Traverse entity graph from start node"""
        try:
            if not self.graph or start_id not in self.graph:
                return {
                    "success": True,
                    "result": {"start_id": start_id, "traversed": [], "hops": 0},
                }

            traversed = []
            visited = {start_id}
            queue = [(start_id, 0, [start_id])]

            while queue:
                current_id, hops, path = queue.pop(0)

                if hops >= max_hops:
                    continue

                # Get node data
                if current_id in self.graph:
                    node_data = self.graph.nodes[current_id]
                    traversed.append(
                        {
                            "id": current_id,
                            "type": node_data.get("type", ""),
                            "label": node_data.get("label", ""),
                            "hops": hops,
                            "path": path,
                        }
                    )

                # Explore neighbors
                for neighbor in self.graph.successors(current_id):
                    if neighbor not in visited:
                        # Filter by relationship type if specified
                        if relationship_filter:
                            edge_data = self.graph[current_id][neighbor]
                            if edge_data.get("type") != relationship_filter:
                                continue

                        visited.add(neighbor)
                        queue.append((neighbor, hops + 1, path + [neighbor]))

            return {
                "success": True,
                "result": {
                    "start_id": start_id,
                    "traversed": traversed,
                    "hops": max_hops,
                    "count": len(traversed),
                },
            }
        except Exception as e:
            return {"success": False, "error": str(e)}

    def find_temporal_context(
        self, entity_id: str, time_range: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """Find temporal context for an entity"""
        try:
            if not self.graph or entity_id not in self.graph:
                return {
                    "success": True,
                    "result": {
                        "entity_id": entity_id,
                        "temporal_relationships": [],
                        "time_range": time_range,
                    },
                }

            temporal_relationships = []

            # Get all relationships for this entity
            for neighbor in list(self.graph.successors(entity_id)) + list(
                self.graph.predecessors(entity_id)
            ):
                if entity_id in self.graph and neighbor in self.graph[entity_id]:
                    edge_data = self.graph[entity_id][neighbor]
                    rel_type = edge_data.get("type", "")

                    # Check if it's a temporal relationship
                    temporal_types = [
                        "before",
                        "after",
                        "during",
                        "overlaps",
                        "sameTime",
                    ]
                    if rel_type in temporal_types:
                        established_at = edge_data.get("establishedAt", "")
                        is_active = edge_data.get("isActive", True)

                        temporal_relationships.append(
                            {
                                "source": entity_id,
                                "target": neighbor,
                                "type": rel_type,
                                "establishedAt": established_at,
                                "isActive": is_active,
                            }
                        )

            return {
                "success": True,
                "result": {
                    "entity_id": entity_id,
                    "temporal_relationships": temporal_relationships,
                    "count": len(temporal_relationships),
                },
            }
        except Exception as e:
            return {"success": False, "error": str(e)}

    def get_entity_centrality(
        self, entity_id: Optional[str] = None, centrality_type: str = "degree"
    ) -> Dict[str, Any]:
        """Calculate entity centrality metrics"""
        try:
            if not self.graph:
                return {
                    "success": True,
                    "result": {"centrality": {}, "type": centrality_type},
                }

            if centrality_type == "degree":
                centrality = nx.degree_centrality(self.graph)
            elif centrality_type == "betweenness":
                centrality = nx.betweenness_centrality(self.graph)
            elif centrality_type == "closeness":
                centrality = nx.closeness_centrality(self.graph)
            elif centrality_type == "eigenvector":
                try:
                    centrality = nx.eigenvector_centrality(self.graph)
                except Exception as e:
                    logger.debug(
                        "Eigenvector centrality failed; returning empty centrality",
                        exc_info=True,
                        extra={"module_name": "cogs_graph", "error_type": type(e).__name__},
                    )
                    centrality = {}
            else:
                centrality = nx.degree_centrality(self.graph)

            if entity_id:
                return {
                    "success": True,
                    "result": {
                        "entity_id": entity_id,
                        "centrality": centrality.get(entity_id, 0.0),
                        "type": centrality_type,
                    },
                }
            else:
                # Return top entities by centrality
                sorted_centrality = sorted(
                    centrality.items(), key=lambda x: x[1], reverse=True
                )[:20]
                return {
                    "success": True,
                    "result": {
                        "top_entities": [
                            {"id": k, "centrality": v} for k, v in sorted_centrality
                        ],
                        "type": centrality_type,
                    },
                }
        except Exception as e:
            return {"success": False, "error": str(e)}

    def find_entity_path(
        self, source_id: str, target_id: str, max_hops: int = 5
    ) -> Dict[str, Any]:
        """Find shortest path between two entities"""
        try:
            if (
                not self.graph
                or source_id not in self.graph
                or target_id not in self.graph
            ):
                return {
                    "success": True,
                    "result": {"path_found": False, "path": [], "hops": 0},
                }

            try:
                path = nx.shortest_path(self.graph, source_id, target_id)
                if len(path) - 1 <= max_hops:
                    return {
                        "success": True,
                        "result": {
                            "path_found": True,
                            "path": path,
                            "hops": len(path) - 1,
                        },
                    }
                else:
                    return {
                        "success": True,
                        "result": {
                            "path_found": False,
                            "path": [],
                            "hops": 0,
                            "reason": "Path exceeds max_hops",
                        },
                    }
            except nx.NetworkXNoPath:
                return {
                    "success": True,
                    "result": {
                        "path_found": False,
                        "path": [],
                        "hops": 0,
                        "reason": "No path found",
                    },
                }
        except Exception as e:
            return {"success": False, "error": str(e)}

    def cluster_entities(
        self, entity_ids: List[str], method: str = "community"
    ) -> Dict[str, Any]:
        """Cluster entities using various methods"""
        try:
            if not self.graph or not entity_ids:
                return {"success": True, "result": {"clusters": [], "method": method}}

            # Create subgraph with specified entities
            subgraph = self.graph.subgraph(entity_ids)

            if method == "community":
                try:
                    import community as community_louvain

                    partition = community_louvain.best_partition(
                        subgraph.to_undirected()
                    )
                    clusters = defaultdict(list)
                    for node, cluster_id in partition.items():
                        clusters[cluster_id].append(node)
                    return {
                        "success": True,
                        "result": {
                            "clusters": [
                                {"id": k, "entities": v} for k, v in clusters.items()
                            ],
                            "method": method,
                        },
                    }
                except ImportError:
                    # Fallback to simple connected components
                    clusters = list(nx.connected_components(subgraph.to_undirected()))
                    return {
                        "success": True,
                        "result": {
                            "clusters": [
                                {"id": i, "entities": list(c)}
                                for i, c in enumerate(clusters)
                            ],
                            "method": "connected_components",
                        },
                    }
            else:
                # Use connected components as fallback
                clusters = list(nx.connected_components(subgraph.to_undirected()))
                return {
                    "success": True,
                    "result": {
                        "clusters": [
                            {"id": i, "entities": list(c)}
                            for i, c in enumerate(clusters)
                        ],
                        "method": "connected_components",
                    },
                }
        except Exception as e:
            return {"success": False, "error": str(e)}

    def get_graph_analytics(self) -> Dict[str, Any]:
        """Get comprehensive graph analytics"""
        try:
            if not self.graph:
                return {
                    "success": True,
                    "result": {"nodes": 0, "edges": 0, "density": 0.0, "analytics": {}},
                }

            nodes = self.graph.number_of_nodes()
            edges = self.graph.number_of_edges()
            density = nx.density(self.graph)

            # Calculate basic metrics
            analytics = {
                "nodes": nodes,
                "edges": edges,
                "density": float(density),
                "is_connected": (
                    nx.is_weakly_connected(self.graph) if nodes > 0 else False
                ),
                "average_degree": float(edges * 2 / nodes) if nodes > 0 else 0.0,
            }

            # Try to calculate more advanced metrics
            try:
                if nodes > 0:
                    analytics["average_clustering"] = float(
                        nx.average_clustering(self.graph.to_undirected())
                    )
            except Exception as e:
                logger.debug(
                    "Average clustering calculation failed",
                    exc_info=True,
                    extra={"module_name": "cogs_graph", "error_type": type(e).__name__},
                )

            return {"success": True, "result": analytics}
        except Exception as e:
            return {"success": False, "error": str(e)}
