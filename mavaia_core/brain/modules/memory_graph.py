from __future__ import annotations
"""
Memory Graph Module - Neo4j-based graph operations
Handles entity linking, relationship mapping, multi-hop reasoning, and memory traversal
Uses in-memory Neo4j graph (rebuilt on startup)
"""

import json
import logging
from typing import Dict, Any, List, Optional
from collections import defaultdict

from mavaia_core.brain.base_module import BaseBrainModule, ModuleMetadata
from mavaia_core.exceptions import InvalidParameterError

logger = logging.getLogger(__name__)

# Optional imports - will fail gracefully if dependencies not available
try:
    from neo4j import GraphDatabase
    import networkx as nx

    NEO4J_AVAILABLE = True
except ImportError:
    NEO4J_AVAILABLE = False
    # Fallback: use NetworkX only if available
    try:
        import networkx as nx

        NETWORKX_AVAILABLE = True
    except ImportError:
        NETWORKX_AVAILABLE = False


class MemoryGraph(BaseBrainModule):
    """Graph operations for memory relationships using Neo4j"""

    def __init__(self):
        self.driver = None
        self.graph = None  # NetworkX fallback graph
        self.is_initialized = False

    @property
    def metadata(self) -> ModuleMetadata:
        return ModuleMetadata(
            name="memory_graph",
            version="1.0.0",
            description="Graph operations for memory relationships: entity linking, multi-hop reasoning, traversal",
            operations=[
                "build_graph",
                "recall_memories",
                "find_relationships",
                "multi_hop_reasoning",
                "traverse_memory",
                "cluster_context",
                "find_similar_contexts",
                "get_graph_stats",
                "add_node",
                "get_node",
            ],
            dependencies=["neo4j", "networkx"],
            enabled=True,
            model_required=False,
        )

    def initialize(self) -> bool:
        """Initialize Neo4j driver (in-memory)"""
        try:
            # Use NetworkX as primary (simpler for in-memory)
            if NETWORKX_AVAILABLE:
                self.graph = nx.DiGraph()
                self.is_initialized = True
                return True
            # Fallback to Neo4j if NetworkX not available but Neo4j is
            elif NEO4J_AVAILABLE:
                # For in-memory, use NetworkX-style graph
                # Neo4j doesn't have pure in-memory mode without a server
                # So we'll use a simple dict-based graph structure
                self.graph = {}  # Simple dict-based graph
                self.is_initialized = True
                return True
            else:
                # Even without graph libraries, use simple dict-based graph
                # Module can still function with basic operations
                self.graph = {}  # Simple dict-based graph
                self.is_initialized = True
                return True
        except Exception as e:
            logger.warning(
                "MemoryGraph initialization failed; falling back to dict-based graph",
                exc_info=True,
                extra={"module_name": "memory_graph", "error_type": type(e).__name__},
            )
            # Fallback: use simple dict even if everything fails
            self.graph = {}
            self.is_initialized = True
            return True

    def execute(self, operation: str, params: Dict[str, Any]) -> Dict[str, Any]:
        """Execute graph operations"""

        if not self.is_initialized:
            self.initialize()

        if operation == "build_graph":
            processed_memories = params.get("processed_memories", "{}")
            return self.build_graph(processed_memories)

        elif operation == "find_relationships":
            memory_id = params.get("memory_id", "")
            depth = params.get("depth", 2)
            return self.find_relationships(memory_id, depth)

        elif operation == "multi_hop_reasoning":
            start_id = params.get("start_id", "")
            target_concept = params.get("target_concept", "")
            return self.multi_hop_reasoning(start_id, target_concept)

        elif operation == "traverse_memory":
            start_id = params.get("start_id", "")
            max_hops = params.get("max_hops", 3)
            return self.traverse_memory(start_id, max_hops)

        elif operation == "cluster_context":
            memory_ids = params.get("memory_ids", [])
            return self.cluster_context(memory_ids)

        elif operation == "find_similar_contexts":
            query = params.get("query", "")
            limit = params.get("limit", 10)
            return self.find_similar_contexts(query, limit)

        elif operation == "get_graph_stats":
            return self.get_graph_stats()

        elif operation == "add_node":
            node_id = params.get("node_id", "")
            node_data = params.get("node_data", {})
            return self.add_node(node_id, node_data)

        elif operation == "get_node":
            node_id = params.get("node_id", "")
            return self.get_node(node_id)

        elif operation == "recall_memories":
            query = params.get("query", "")
            limit = params.get("limit", 5)
            return self.recall_memories(query=query, limit=limit)

        else:
            raise InvalidParameterError(
                parameter="operation",
                value=operation,
                reason="Unknown operation for memory_graph",
            )

    def recall_memories(self, query: str, limit: int = 5) -> Dict[str, Any]:
        """
        Recall memories relevant to a query from the in-memory graph.

        This is a lightweight heuristic retrieval used by other modules (e.g., MCTS).
        """
        if not isinstance(query, str) or not query.strip():
            return {"success": True, "memories": []}
        try:
            limit_i = int(limit)
        except Exception as e:
            raise InvalidParameterError("limit", str(limit), "limit must be an int") from e
        if limit_i < 1:
            return {"success": True, "memories": []}

        tokens = {t for t in query.lower().split() if len(t) >= 3}
        if not tokens:
            return {"success": True, "memories": []}

        # Gather candidate nodes
        candidates: list[dict[str, Any]] = []
        if NETWORKX_AVAILABLE and isinstance(self.graph, nx.DiGraph):
            for node_id, data in self.graph.nodes(data=True):
                content = str(data.get("content", "") or "")
                summary = str(data.get("summary", "") or "")
                text = (content + " " + summary).lower()
                score = sum(1 for t in tokens if t in text)
                if score > 0:
                    candidates.append({"id": node_id, **data, "_score": score})
        elif isinstance(self.graph, dict):
            for node_id, data in self.graph.items():
                if not isinstance(data, dict):
                    continue
                content = str(data.get("content", "") or "")
                summary = str(data.get("summary", "") or "")
                text = (content + " " + summary).lower()
                score = sum(1 for t in tokens if t in text)
                if score > 0:
                    candidates.append({"id": node_id, **data, "_score": score})

        candidates.sort(key=lambda x: int(x.get("_score", 0)), reverse=True)
        memories = [{k: v for k, v in c.items() if k != "_score"} for c in candidates[:limit_i]]
        return {"success": True, "memories": memories}

    def build_graph(self, processed_memories: str) -> Dict[str, Any]:
        """Build graph from processed memories"""
        try:
            if not self.is_initialized:
                self.initialize()

            data = (
                json.loads(processed_memories)
                if isinstance(processed_memories, str)
                else processed_memories
            )

            nodes = data.get("nodes", [])
            relationships = data.get("relationships", [])

            # Clear existing graph
            if self.graph:
                if NETWORKX_AVAILABLE and isinstance(self.graph, nx.DiGraph):
                    self.graph.clear()
                elif isinstance(self.graph, dict):
                    self.graph.clear()
            else:
                if NETWORKX_AVAILABLE:
                    self.graph = nx.DiGraph()
                else:
                    self.graph = {}

            # Add nodes (memories)
            for node in nodes:
                node_id = node.get("id", "")
                if node_id:
                    if NETWORKX_AVAILABLE and isinstance(self.graph, nx.DiGraph):
                        self.graph.add_node(node_id, **node)
                    elif isinstance(self.graph, dict):
                        self.graph[node_id] = dict(node)

            # Add relationships (edges)
            for rel in relationships:
                source = rel.get("source", "")
                target = rel.get("target", "")
                rel_type = rel.get("type", "related")
                strength = rel.get("strength", 1.0)

                if source and target:
                    if NETWORKX_AVAILABLE and isinstance(self.graph, nx.DiGraph):
                        self.graph.add_edge(
                            source, target, type=rel_type, strength=strength
                        )
                    elif isinstance(self.graph, dict):
                        # For dict-based graph, store edges as nested structure
                        if source not in self.graph:
                            self.graph[source] = {"edges": []}
                        if "edges" not in self.graph[source]:
                            self.graph[source]["edges"] = []
                        self.graph[source]["edges"].append({
                            "target": target,
                            "type": rel_type,
                            "strength": strength
                        })

            # Calculate stats based on graph type
            if NETWORKX_AVAILABLE and isinstance(self.graph, nx.DiGraph):
                nodes_count = self.graph.number_of_nodes()
                edges_count = self.graph.number_of_edges()
            elif isinstance(self.graph, dict):
                nodes_count = len(self.graph)
                edges_count = sum(
                    len(node_data.get("edges", [])) 
                    for node_data in self.graph.values() 
                    if isinstance(node_data, dict)
                )
            else:
                nodes_count = 0
                edges_count = 0
            
            return {
                "success": True,
                "result": {
                    "nodes_count": nodes_count,
                    "edges_count": edges_count,
                    "message": "Graph built successfully",
                },
            }
        except Exception as e:
            return {"success": False, "error": str(e)}

    def find_relationships(self, memory_id: str, depth: int = 2) -> Dict[str, Any]:
        """Find relationships for a memory up to specified depth"""
        try:
            if not self.graph or memory_id not in self.graph:
                return {
                    "success": True,
                    "result": {
                        "memory_id": memory_id,
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

                # Get neighbors
                if node_id in self.graph:
                    for neighbor in self.graph.successors(node_id):
                        edge_data = self.graph[node_id][neighbor]
                        rel_type = edge_data.get("type", "related")
                        strength = edge_data.get("strength", 1.0)

                        relationships.append(
                            {
                                "source": node_id,
                                "target": neighbor,
                                "type": rel_type,
                                "strength": float(strength),
                                "depth": current_depth,
                                "path": path + [node_id, neighbor],
                            }
                        )

                        if current_depth < depth:
                            traverse(neighbor, current_depth + 1, path + [node_id])

            traverse(memory_id, 1, [])

            return {
                "success": True,
                "result": {
                    "memory_id": memory_id,
                    "relationships": relationships,
                    "depth": depth,
                    "count": len(relationships),
                },
            }
        except Exception as e:
            return {"success": False, "error": str(e)}

    def multi_hop_reasoning(self, start_id: str, target_concept: str) -> Dict[str, Any]:
        """Find reasoning path from start memory to target concept"""
        try:
            if not self.graph or start_id not in self.graph:
                return {
                    "success": True,
                    "result": {
                        "path_found": False,
                        "path": [],
                        "reasoning": "Start memory not found in graph",
                    },
                }

            # Use BFS to find path to nodes containing target concept
            queue = [(start_id, [start_id])]
            visited = {start_id}
            max_hops = 5

            while queue:
                current_id, path = queue.pop(0)

                if len(path) > max_hops:
                    continue

                # Check if current node contains target concept
                if current_id in self.graph:
                    node_data = self.graph.nodes[current_id]
                    content = str(node_data.get("content", "")).lower()
                    keywords = [str(k).lower() for k in node_data.get("keywords", [])]

                    if (
                        target_concept.lower() in content
                        or target_concept.lower() in keywords
                    ):
                        return {
                            "success": True,
                            "result": {
                                "path_found": True,
                                "path": path,
                                "hops": len(path) - 1,
                                "target_node": current_id,
                            },
                        }

                # Explore neighbors
                if current_id in self.graph:
                    for neighbor in self.graph.successors(current_id):
                        if neighbor not in visited:
                            visited.add(neighbor)
                            queue.append((neighbor, path + [neighbor]))

            return {
                "success": True,
                "result": {
                    "path_found": False,
                    "path": [],
                    "reasoning": "No path found to target concept",
                },
            }
        except Exception as e:
            return {"success": False, "error": str(e)}

    def traverse_memory(self, start_id: str, max_hops: int = 3) -> Dict[str, Any]:
        """Traverse memory graph from start node"""
        try:
            if not self.graph or start_id not in self.graph:
                return {"success": True, "result": {"traversed": [], "count": 0}}

            traversed = []
            visited = set()

            def dfs(node_id: str, depth: int, path: List[str]):
                if depth > max_hops or node_id in visited:
                    return

                visited.add(node_id)

                if node_id in self.graph:
                    node_data = self.graph.nodes[node_id]
                    traversed.append(
                        {
                            "id": node_id,
                            "type": node_data.get("type", "memory"),
                            "content": node_data.get("content", "")[:100],  # Truncate
                            "depth": depth,
                            "path": path + [node_id],
                        }
                    )

                    if depth < max_hops:
                        for neighbor in self.graph.successors(node_id):
                            dfs(neighbor, depth + 1, path + [node_id])

            dfs(start_id, 0, [])

            return {
                "success": True,
                "result": {"traversed": traversed, "count": len(traversed)},
            }
        except Exception as e:
            return {"success": False, "error": str(e)}

    def cluster_context(self, memory_ids: List[str]) -> Dict[str, Any]:
        """Cluster memories by context (connected components)"""
        try:
            if not self.graph:
                return {"success": True, "result": {"clusters": [], "count": 0}}

            # Find connected components containing the specified memory IDs
            clusters = []
            processed = set()

            for memory_id in memory_ids:
                if memory_id in processed or memory_id not in self.graph:
                    continue

                # Find all nodes reachable from this memory
                component = set()
                queue = [memory_id]

                while queue:
                    node = queue.pop(0)
                    if node in component:
                        continue

                    component.add(node)
                    processed.add(node)

                    # Add neighbors
                    if node in self.graph:
                        for neighbor in list(self.graph.successors(node)) + list(
                            self.graph.predecessors(node)
                        ):
                            if neighbor not in component:
                                queue.append(neighbor)

                if component:
                    clusters.append(
                        {
                            "cluster_id": len(clusters),
                            "memory_ids": list(component),
                            "size": len(component),
                        }
                    )

            return {
                "success": True,
                "result": {"clusters": clusters, "count": len(clusters)},
            }
        except Exception as e:
            return {"success": False, "error": str(e)}

    def find_similar_contexts(self, query: str, limit: int = 10) -> Dict[str, Any]:
        """Find memories with similar context to query"""
        try:
            if not self.graph:
                return {"success": True, "result": {"similar": [], "count": 0}}

            query_lower = query.lower()
            query_words = set(query_lower.split())

            similar = []

            for node_id, node_data in self.graph.nodes(data=True):
                content = str(node_data.get("content", "")).lower()
                keywords = [str(k).lower() for k in node_data.get("keywords", [])]
                tags = [str(t).lower() for t in node_data.get("tags", [])]

                # Calculate similarity
                content_words = set(content.split())
                all_terms = content_words | set(keywords) | set(tags)

                overlap = len(query_words & all_terms)
                if overlap > 0:
                    similarity = overlap / len(query_words) if query_words else 0

                    similar.append(
                        {
                            "id": node_id,
                            "type": node_data.get("type", "memory"),
                            "content": node_data.get("content", "")[:200],
                            "similarity": float(similarity),
                            "importance": float(node_data.get("importance", 0.5)),
                        }
                    )

            # Sort by similarity and importance
            similar.sort(key=lambda x: (x["similarity"], x["importance"]), reverse=True)

            return {
                "success": True,
                "result": {"similar": similar[:limit], "count": len(similar[:limit])},
            }
        except Exception as e:
            return {"success": False, "error": str(e)}

    def get_graph_stats(self) -> Dict[str, Any]:
        """Get graph statistics"""
        try:
            if not self.graph:
                return {
                    "success": True,
                    "result": {"nodes": 0, "edges": 0, "density": 0.0},
                }

            if NETWORKX_AVAILABLE and isinstance(self.graph, nx.DiGraph):
                nodes = self.graph.number_of_nodes()
                edges = self.graph.number_of_edges()

                # Calculate density
                if nodes > 1:
                    max_edges = nodes * (nodes - 1)
                    density = edges / max_edges if max_edges > 0 else 0.0
                else:
                    density = 0.0

                # Find most connected nodes
                if nodes > 0:
                    degrees = dict(self.graph.degree())
                    top_nodes = sorted(degrees.items(), key=lambda x: x[1], reverse=True)[
                        :5
                    ]
                    top_connected = [
                        {"id": node_id, "degree": degree} for node_id, degree in top_nodes
                    ]
                else:
                    top_connected = []
            elif isinstance(self.graph, dict):
                # Dict-based graph
                nodes = len(self.graph)
                edges = sum(
                    len(node_data.get("edges", [])) 
                    for node_data in self.graph.values() 
                    if isinstance(node_data, dict)
                )

                # Calculate density
                if nodes > 1:
                    max_edges = nodes * (nodes - 1)
                    density = edges / max_edges if max_edges > 0 else 0.0
                else:
                    density = 0.0

                # Find most connected nodes
                if nodes > 0:
                    node_degrees = []
                    for node_id, node_data in self.graph.items():
                        if isinstance(node_data, dict):
                            degree = len(node_data.get("edges", []))
                        else:
                            degree = 0
                        node_degrees.append((node_id, degree))
                    top_nodes = sorted(node_degrees, key=lambda x: x[1], reverse=True)[:5]
                    top_connected = [
                        {"id": node_id, "degree": degree} for node_id, degree in top_nodes
                    ]
                else:
                    top_connected = []
            else:
                nodes = 0
                edges = 0
                density = 0.0
                top_connected = []

            return {
                "success": True,
                "result": {
                    "nodes": nodes,
                    "edges": edges,
                    "density": float(density),
                    "top_connected": top_connected,
                },
            }
        except Exception as e:
            return {"success": False, "error": str(e)}

    def add_node(self, node_id: str, node_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Add a node to the memory graph
        
        Args:
            node_id: Unique identifier for the node
            node_data: Data associated with the node
            
        Returns:
            Dictionary with success status
        """
        try:
            if not node_id:
                return {"success": False, "error": "node_id cannot be empty"}
            
            if not self.is_initialized:
                self.initialize()
            
            # Initialize graph if needed
            if not self.graph:
                if NETWORKX_AVAILABLE:
                    self.graph = nx.DiGraph()
                else:
                    self.graph = {}  # Use dict-based graph
            
            # Add node based on graph type
            if NETWORKX_AVAILABLE and isinstance(self.graph, nx.DiGraph):
                # Merge node_data with node_id
                node_attrs = dict(node_data)
                node_attrs["id"] = node_id
                self.graph.add_node(node_id, **node_attrs)
            else:
                # Dict-based graph
                node_attrs = dict(node_data)
                node_attrs["id"] = node_id
                self.graph[node_id] = node_attrs
            
            # If Neo4j is available, also add there
            if self.driver:
                with self.driver.session() as session:
                    session.run(
                        "MERGE (n:Memory {id: $node_id}) SET n += $node_data",
                        node_id=node_id,
                        node_data=node_data
                    )
            
            return {"success": True, "node_id": node_id}
        except Exception as e:
            return {"success": False, "error": str(e)}
    
    def get_node(self, node_id: str) -> Dict[str, Any]:
        """
        Get a node from the memory graph
        
        Args:
            node_id: Identifier of the node to retrieve
            
        Returns:
            Dictionary with node data or error
        """
        try:
            if not node_id:
                return {"success": False, "error": "node_id cannot be empty"}
            
            if not self.is_initialized:
                self.initialize()
            
            # Try NetworkX graph first
            if self.graph:
                if NETWORKX_AVAILABLE and isinstance(self.graph, nx.DiGraph):
                    if node_id in self.graph:
                        node_data = dict(self.graph.nodes[node_id])
                        return {"success": True, "node_data": node_data}
                elif isinstance(self.graph, dict):
                    # Dict-based graph
                    if node_id in self.graph:
                        node_data = dict(self.graph[node_id])
                        return {"success": True, "node_data": node_data}
            
            # Try Neo4j if available
            if self.driver:
                with self.driver.session() as session:
                    result = session.run(
                        "MATCH (n:Memory {id: $node_id}) RETURN n",
                        node_id=node_id
                    )
                    record = result.single()
                    if record:
                        node = record["n"]
                        node_data = dict(node)
                        return {"success": True, "node_data": node_data}
            
            return {"success": False, "error": f"Node {node_id} not found"}
        except Exception as e:
            return {"success": False, "error": str(e)}
    
    def cleanup(self):
        """Cleanup resources"""
        if self.driver:
            self.driver.close()
        if self.graph:
            self.graph.clear()
