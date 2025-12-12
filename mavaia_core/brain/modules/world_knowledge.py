"""
World Knowledge Module - Hybrid knowledge base (graph + vectors)
Handles knowledge retrieval, validation, fact storage, and semantic search over world knowledge
"""

from collections import defaultdict
from pathlib import Path
from typing import Any, Dict, List, Set, Tuple
import json
import sys

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent))

from mavaia_core.brain.base_module import BaseBrainModule, ModuleMetadata

# Lazy imports to avoid timeout during module discovery
NETWORKX_AVAILABLE = False
nx = None
EMBEDDINGS_AVAILABLE = False
EmbeddingsModule = None
ConceptEmbeddingsModule = None
MEMORY_GRAPH_AVAILABLE = False
MemoryGraph = None

def _lazy_import_world_knowledge_deps():
    """Lazy import world knowledge dependencies only when needed"""
    global NETWORKX_AVAILABLE, nx, EMBEDDINGS_AVAILABLE, EmbeddingsModule, ConceptEmbeddingsModule
    global MEMORY_GRAPH_AVAILABLE, MemoryGraph
    
    if not NETWORKX_AVAILABLE:
        try:
            import networkx as nx_module
            nx = nx_module
            NETWORKX_AVAILABLE = True
        except ImportError:
            pass
    
    if not EMBEDDINGS_AVAILABLE:
        try:
            from embeddings import EmbeddingsModule as EM
            from concept_embeddings import ConceptEmbeddingsModule as CEM
            EmbeddingsModule = EM
            ConceptEmbeddingsModule = CEM
            EMBEDDINGS_AVAILABLE = True
        except ImportError:
            pass
    
    if not MEMORY_GRAPH_AVAILABLE:
        try:
            from memory_graph import MemoryGraph as MG
            MemoryGraph = MG
            MEMORY_GRAPH_AVAILABLE = True
        except ImportError:
            pass


class WorldKnowledgeModule(BaseBrainModule):
    """Hybrid knowledge base combining graph and vector representations"""

    def __init__(self):
        self.config = None
        self.knowledge_graph = None
        self.knowledge_base = {}
        self.embeddings = None
        self.concept_embeddings = None
        self.memory_graph = None
        self._initialized = False
        # Don't load config or initialize components during __init__ to avoid timeout
        # They will be initialized lazily when needed

    @property
    def metadata(self) -> ModuleMetadata:
        return ModuleMetadata(
            name="world_knowledge",
            version="1.0.0",
            description=(
                "Hybrid knowledge base: graph traversal + semantic search, "
                "knowledge graph, fact verification"
            ),
            operations=[
                "query_knowledge",
                "add_knowledge",
                "validate_fact",
                "semantic_search",
                "get_related_facts",
                "find_entities",
                "expand_knowledge_base",
                "retrieve_by_domain",
                "build_knowledge_graph",
                "verify_fact_chain",
                "get_knowledge_path",
            ],
            dependencies=["networkx", "sentence-transformers"],
            model_required=True,
        )

    def initialize(self) -> bool:
        """Initialize the module"""
        if not self._initialized:
            self._load_config()
            self._initialized = self._initialize_components()
        return self._initialized
    
    def _ensure_initialized(self):
        """Ensure module is initialized before use"""
        if not self._initialized:
            self._load_config()
            self._initialized = self._initialize_components()

    def _load_config(self):
        """Load world knowledge configuration"""
        config_path = Path(__file__).parent / "world_knowledge_config.json"
        try:
            if config_path.exists():
                with open(config_path, "r", encoding="utf-8") as f:
                    self.config = json.load(f)
            else:
                self.config = {
                    "knowledge_base_path": "knowledge_base.json",
                    "use_graph": True,
                    "use_vectors": True,
                    "similarity_threshold": 0.7,
                    "max_results": 10,
                }
        except Exception as e:
            print(f"[WorldKnowledgeModule] Failed to load config: {e}", file=sys.stderr)
            self.config = {}

    def _initialize_components(self) -> bool:
        """Initialize knowledge base components"""
        _lazy_import_world_knowledge_deps()
        
        # Initialize graph (lightweight)
        if NETWORKX_AVAILABLE and nx:
            self.knowledge_graph = nx.DiGraph()

        # Don't initialize embeddings or memory_graph here - they're heavy
        # Will initialize lazily when needed in execute methods
        self.embeddings = None
        self.concept_embeddings = None
        self.memory_graph = None
        
        # Don't load knowledge base here - it's heavy, will load on first use
        return True

    def _load_domain_facts(self):
        """Load facts from knowledge domains in config"""
        domains = self.config.get("knowledge_domains", {})
        for domain_name, domain_config in domains.items():
            if not domain_config.get("enabled", True):
                continue

            facts = domain_config.get("facts", [])
            if facts:
                self.expand_knowledge_base(facts, domain_name)

    def execute(self, operation: str, params: Dict[str, Any]) -> Dict[str, Any]:
        """Execute a world knowledge operation"""
        self._ensure_initialized()
        match operation:
            case "query_knowledge":
                query = params.get("query", "")
                query_type = params.get("query_type", "semantic")
                limit = params.get("limit", 10)
                return self.query_knowledge(query, query_type, limit)
            case "add_knowledge":
                fact = params.get("fact", "")
                entities = params.get("entities", [])
                relationships = params.get("relationships", {})
                return self.add_knowledge(fact, entities, relationships)
            case "validate_fact":
                fact = params.get("fact", "")
                context = params.get("context", "")
                return self.validate_fact(fact, context)
            case "semantic_search":
                query = params.get("query", "")
                limit = params.get("limit", 10)
                threshold = params.get("threshold", 0.7)
                return self.semantic_search(query, limit, threshold)
            case "get_related_facts":
                entity = params.get("entity", "")
                depth = params.get("depth", 2)
                return self.get_related_facts(entity, depth)
            case "find_entities":
                text = params.get("text", "")
                return self.find_entities(text)
            case "expand_knowledge_base":
                facts = params.get("facts", [])
                domain = params.get("domain", "general")
                return self.expand_knowledge_base(facts, domain)
            case "retrieve_by_domain":
                domain = params.get("domain", "general")
                query = params.get("query", "")
                limit = params.get("limit", 10)
                return self.retrieve_by_domain(domain, query, limit)
            case "build_knowledge_graph":
                return self.build_knowledge_graph()
            case "verify_fact_chain":
                fact = params.get("fact", "")
                return self.verify_fact_chain(fact)
            case "get_knowledge_path":
                source = params.get("source", "")
                target = params.get("target", "")
                return self.get_knowledge_path(source, target)
            case _:
                raise ValueError(f"Unknown operation: {operation}")

    def query_knowledge(
        self, query: str, query_type: str = "semantic", limit: int = 10
    ) -> Dict[str, Any]:
        """Query knowledge base using graph or semantic search"""
        if not query:
            return {"results": [], "count": 0, "query": query}

        results = []

        if query_type == "semantic" and self.embeddings:
            # Use semantic search
            semantic_result = self.semantic_search(query, limit)
            results = semantic_result.get("results", [])
        elif query_type == "graph":
            # Ensure graph is built
            if not self.knowledge_graph or self.knowledge_graph.number_of_nodes() == 0:
                self.build_knowledge_graph()
            
            if self.knowledge_graph and NETWORKX_AVAILABLE:
                # Use graph traversal
                query_lower = query.lower()
                # Find nodes matching query
                matching_nodes = []
                for node in self.knowledge_graph.nodes(data=True):
                    node_id, node_data = node
                    if (
                        query_lower in str(node_id).lower()
                        or query_lower in str(node_data.get("label", "")).lower()
                    ):
                        matching_nodes.append(
                            {"entity": node_id, "data": node_data, "relevance": 1.0}
                        )
                results = matching_nodes[:limit]
            else:
                # Fallback to text search
                results = []
        else:
            # Fallback: simple text search in knowledge base
            query_lower = query.lower().strip()
            query_words = [w for w in query_lower.split() if len(w) > 2]  # Filter out very short words
            
            for key, value in self.knowledge_base.items():
                fact = value.get("fact", "")
                entities = value.get("entities", [])
                
                # Check if query matches fact, entities, or key
                fact_lower = fact.lower() if fact else ""
                key_lower = key.lower()
                
                # Check for word matches - improved matching
                matches = False
                
                # Exact match in fact or key
                if query_lower in fact_lower or query_lower in key_lower:
                    matches = True
                # Query word appears in fact (word boundary aware)
                elif query_words:
                    for word in query_words:
                        if word in fact_lower:
                            matches = True
                            break
                # Query matches any entity (case-insensitive, partial or exact match)
                if not matches and entities:
                    for entity in entities:
                        entity_lower = str(entity).lower()
                        # Exact match
                        if query_lower == entity_lower:
                            matches = True
                            break
                        # Query is substring of entity or vice versa
                        if query_lower in entity_lower or entity_lower in query_lower:
                            matches = True
                            break
                        # Word-by-word match for multi-word entities
                        if query_words:
                            entity_words = entity_lower.split()
                            if any(qw in entity_words for qw in query_words):
                                matches = True
                                break
                
                if matches:
                    results.append({
                        "key": key,
                        "fact": fact,
                        "entities": entities,
                        "relevance": 0.8,
                    })
                if len(results) >= limit:
                    break

        return {
            "results": results,
            "count": len(results),
            "query": query,
            "query_type": query_type,
        }

    def add_knowledge(
        self,
        fact: str,
        entities: List[str] = None,
        relationships: Dict[str, str] = None,
    ) -> Dict[str, Any]:
        """Add knowledge to the knowledge base"""
        if entities is None:
            entities = []
        if relationships is None:
            relationships = {}

        # Store in knowledge base dict
        fact_id = f"fact_{len(self.knowledge_base)}"
        self.knowledge_base[fact_id] = {
            "fact": fact,
            "entities": entities,
            "relationships": relationships,
            "added_at": str(Path(__file__).stat().st_mtime),  # Simple timestamp
        }

        # Add to graph if available
        if self.knowledge_graph and NETWORKX_AVAILABLE:
            # Add entities as nodes
            for entity in entities:
                if not self.knowledge_graph.has_node(entity):
                    self.knowledge_graph.add_node(entity, label=entity, type="entity")

            # Add fact as node
            self.knowledge_graph.add_node(fact_id, label=fact, type="fact")

            # Add relationships
            for entity in entities:
                self.knowledge_graph.add_edge(entity, fact_id, relationship="describes")

            for source, relation in relationships.items():
                if source in entities:
                    for target in entities:
                        if target != source:
                            self.knowledge_graph.add_edge(
                                source, target, relationship=relation
                            )

        # Optionally add to memory graph
        if self.memory_graph:
            try:
                self.memory_graph.execute(
                    "build_graph",
                    {
                        "processed_memories": json.dumps(
                            {fact_id: {"content": fact, "entities": entities}}
                        )
                    },
                )
            except Exception:
                pass

        return {
            "success": True,
            "fact_id": fact_id,
            "entities_added": len(entities),
            "relationships_added": len(relationships),
        }

    def validate_fact(self, fact: str, context: str = "") -> Dict[str, Any]:
        """Validate a fact against knowledge base"""
        if not fact:
            return {"valid": False, "confidence": 0.0, "reason": "Empty fact"}

        # Simple validation: check if fact contradicts existing knowledge
        fact_lower = fact.lower()
        contradictions = []
        support = []

        # Check against existing knowledge
        for key, value in self.knowledge_base.items():
            stored_fact = value.get("fact", "")
            stored_lower = stored_fact.lower()

            # Check for contradictions (simplified)
            # In a full implementation, this would use more sophisticated logic
            if (
                "not" in fact_lower
                and fact_lower.replace("not", "").strip() in stored_lower
            ):
                contradictions.append(key)
            elif (
                "not" in stored_lower
                and stored_lower.replace("not", "").strip() in fact_lower
            ):
                contradictions.append(key)
            elif fact_lower in stored_lower or stored_lower in fact_lower:
                support.append(key)

        # Calculate confidence
        if contradictions:
            confidence = 0.3
            valid = False
        elif support:
            confidence = 0.7
            valid = True
        else:
            confidence = 0.5  # Unknown
            valid = None

        return {
            "valid": valid,
            "confidence": confidence,
            "contradictions": len(contradictions),
            "supporting_facts": len(support),
            "reason": (
                "contradiction"
                if contradictions
                else "supported" if support else "unknown"
            ),
        }

    def semantic_search(
        self, query: str, limit: int = 10, threshold: float = 0.7
    ) -> Dict[str, Any]:
        """Semantic search over knowledge base using embeddings"""
        if not self.embeddings or not query:
            return {"results": [], "count": 0, "query": query}

        try:
            # Get query embedding
            query_embed_result = self.embeddings.execute("generate", {"text": query})
            query_embedding = query_embed_result.get("embedding")

            if not query_embedding:
                return {"results": [], "count": 0, "query": query}

            # Calculate similarities with stored facts
            similarities = []
            for key, value in self.knowledge_base.items():
                fact = value.get("fact", "")
                if not fact:
                    continue

                # Get fact embedding
                fact_embed_result = self.embeddings.execute("generate", {"text": fact})
                fact_embedding = fact_embed_result.get("embedding")

                if fact_embedding:
                    # Calculate cosine similarity
                    similarity = self._cosine_similarity(
                        query_embedding, fact_embedding
                    )
                    if similarity >= threshold:
                        similarities.append(
                            {
                                "fact_id": key,
                                "fact": fact,
                                "similarity": similarity,
                                "entities": value.get("entities", []),
                            }
                        )

            # Sort by similarity
            similarities.sort(key=lambda x: x["similarity"], reverse=True)
            results = similarities[:limit]

            return {
                "results": results,
                "count": len(results),
                "query": query,
                "threshold": threshold,
            }
        except Exception as e:
            return {"results": [], "count": 0, "query": query, "error": str(e)}

    def _cosine_similarity(self, vec1: List[float], vec2: List[float]) -> float:
        """Calculate cosine similarity"""
        if len(vec1) != len(vec2):
            return 0.0

        dot = sum(a * b for a, b in zip(vec1, vec2))
        norm1 = sum(a * a for a in vec1) ** 0.5
        norm2 = sum(b * b for b in vec2) ** 0.5

        if norm1 == 0 or norm2 == 0:
            return 0.0

        return dot / (norm1 * norm2)

    def get_related_facts(self, entity: str, depth: int = 2) -> Dict[str, Any]:
        """Get facts related to an entity using graph traversal"""
        if not entity:
            return {"entity": entity, "related_facts": [], "count": 0}
        
        # Ensure graph is built
        if not self.knowledge_graph or self.knowledge_graph.number_of_nodes() == 0:
            self.build_knowledge_graph()
        
        # Fallback: search knowledge base if graph is not available
        if not self.knowledge_graph or not NETWORKX_AVAILABLE:
            related_facts = []
            entity_lower = entity.lower()
            for key, value in self.knowledge_base.items():
                fact = value.get("fact", "")
                entities = value.get("entities", [])
                if entity_lower in fact.lower() or any(entity_lower == e.lower() for e in entities):
                    related_facts.append({
                        "fact_id": key,
                        "fact": fact,
                        "entities": entities,
                        "depth": 1,
                    })
            return {
                "entity": entity,
                "related_facts": related_facts[:10],  # Limit results
                "count": len(related_facts),
                "depth": depth,
            }

        related_facts = []

        try:
            if self.knowledge_graph.has_node(entity):
                # Get neighbors at specified depth
                for d in range(1, depth + 1):
                    # Simple BFS traversal
                    visited = set()
                    queue = [(entity, 0)]

                    while queue:
                        current, current_depth = queue.pop(0)
                        if current in visited or current_depth > d:
                            continue
                        visited.add(current)

                        if current_depth == d:
                            node_data = self.knowledge_graph.nodes[current]
                            if node_data.get("type") == "fact":
                                related_facts.append(
                                    {
                                        "fact_id": current,
                                        "fact": node_data.get("label", ""),
                                        "depth": current_depth,
                                    }
                                )
                        else:
                            # Add neighbors
                            for neighbor in self.knowledge_graph.neighbors(current):
                                if neighbor not in visited:
                                    queue.append((neighbor, current_depth + 1))
        except Exception:
            pass

        return {
            "entity": entity,
            "related_facts": related_facts,
            "count": len(related_facts),
            "depth": depth,
        }

    def find_entities(self, text: str) -> Dict[str, Any]:
        """Find entities in text that match knowledge base entities"""
        if not text:
            return {"entities": [], "count": 0}

        text_lower = text.lower()
        found_entities = []

        # Simple entity matching (in full implementation, would use NER)
        for key, value in self.knowledge_base.items():
            entities = value.get("entities", [])
            for entity in entities:
                entity_lower = entity.lower()
                if entity_lower in text_lower:
                    found_entities.append(
                        {
                            "entity": entity,
                            "fact_id": key,
                            "fact": value.get("fact", ""),
                            "context": text,
                        }
                    )

        # Remove duplicates
        seen = set()
        unique_entities = []
        for entity_data in found_entities:
            entity_name = entity_data["entity"]
            if entity_name not in seen:
                seen.add(entity_name)
                unique_entities.append(entity_data)

        return {
            "entities": unique_entities,
            "count": len(unique_entities),
            "text": text,
        }

    def expand_knowledge_base(
        self, facts: List[Dict[str, Any]], domain: str = "general"
    ) -> Dict[str, Any]:
        """Expand knowledge base with structured facts"""
        if not facts:
            return {"added": 0, "domain": domain, "success": False}

        added_count = 0
        for fact_data in facts:
            fact = fact_data.get("fact", "")
            entities = fact_data.get("entities", [])
            relationships = fact_data.get("relationships", {})
            domain_fact = fact_data.get("domain", domain)

            if fact:
                result = self.add_knowledge(fact, entities, relationships)
                if result.get("success"):
                    # Tag with domain
                    fact_id = result.get("fact_id")
                    if fact_id in self.knowledge_base:
                        self.knowledge_base[fact_id]["domain"] = domain_fact
                    added_count += 1

        return {
            "added": added_count,
            "domain": domain,
            "total_facts": len(self.knowledge_base),
            "success": added_count > 0,
        }

    def retrieve_by_domain(
        self, domain: str, query: str = "", limit: int = 10
    ) -> Dict[str, Any]:
        """Retrieve knowledge from a specific domain"""
        domain_facts = []
        for key, value in self.knowledge_base.items():
            fact_domain = value.get("domain", "general")
            if fact_domain == domain:
                if not query or query.lower() in str(value.get("fact", "")).lower():
                    domain_facts.append(
                        {
                            "fact_id": key,
                            "fact": value.get("fact", ""),
                            "entities": value.get("entities", []),
                            "relationships": value.get("relationships", {}),
                        }
                    )

        return {
            "domain": domain,
            "results": domain_facts[:limit],
            "count": len(domain_facts),
            "query": query,
        }

    def build_knowledge_graph(self) -> Dict[str, Any]:
        """Build comprehensive knowledge graph from knowledge base"""
        if not NETWORKX_AVAILABLE or not self.knowledge_graph:
            return {
                "success": False,
                "reason": "NetworkX not available or graph not initialized",
            }

        # Clear existing graph
        self.knowledge_graph.clear()

        # Add all facts and entities from knowledge base
        for fact_id, fact_data in self.knowledge_base.items():
            fact = fact_data.get("fact", "")
            entities = fact_data.get("entities", [])
            relationships = fact_data.get("relationships", {})
            domain = fact_data.get("domain", "general")

            # Add fact node
            self.knowledge_graph.add_node(
                fact_id, label=fact, type="fact", domain=domain
            )

            # Add entity nodes
            for entity in entities:
                if not self.knowledge_graph.has_node(entity):
                    self.knowledge_graph.add_node(
                        entity, label=entity, type="entity"
                    )

                # Link entity to fact
                self.knowledge_graph.add_edge(
                    entity, fact_id, relationship="describes"
                )

            # Add relationships between entities
            for source, relation in relationships.items():
                if source in entities:
                    # Create edges to all other entities in the fact
                    for target in entities:
                        if target != source:
                            # Only add edge if it doesn't exist or update with relationship
                            if not self.knowledge_graph.has_edge(source, target):
                                self.knowledge_graph.add_edge(
                                    source, target, relationship=relation
                                )
                            else:
                                # Update existing edge with relationship
                                self.knowledge_graph[source][target]["relationship"] = relation
                    # Also create reverse edges for bidirectional relationships
                    if relation in ["knows", "works_at", "related_to"]:
                        for target in entities:
                            if target != source:
                                if not self.knowledge_graph.has_edge(target, source):
                                    self.knowledge_graph.add_edge(
                                        target, source, relationship=f"{relation}_reverse"
                                    )

        return {
            "success": True,
            "nodes": self.knowledge_graph.number_of_nodes(),
            "edges": self.knowledge_graph.number_of_edges(),
            "facts": len(self.knowledge_base),
        }

    def verify_fact_chain(self, fact: str) -> Dict[str, Any]:
        """Verify a fact by checking its chain of supporting facts"""
        if not fact:
            return {"verified": False, "chain": [], "confidence": 0.0, "fact": fact, "supporting_facts": []}
        
        # Ensure graph is built
        if not self.knowledge_graph or self.knowledge_graph.number_of_nodes() == 0:
            self.build_knowledge_graph()

        # Find facts that support this fact
        supporting_facts = []
        fact_lower = fact.lower()
        
        # Extract entities from the fact for better matching
        fact_entities = []
        for key, value in self.knowledge_base.items():
            entities = value.get("entities", [])
            for entity in entities:
                if entity.lower() in fact_lower:
                    fact_entities.append(entity)

        for key, value in self.knowledge_base.items():
            stored_fact = value.get("fact", "")
            stored_lower = stored_fact.lower()
            stored_entities = value.get("entities", [])

            # Check if stored fact supports the query fact
            # Match by: fact text similarity, entity overlap, or keyword matching
            text_match = fact_lower in stored_lower or stored_lower in fact_lower
            entity_match = any(e.lower() in fact_lower for e in stored_entities) or any(e.lower() in fact_lower for e in fact_entities)
            keyword_match = any(word in stored_lower for word in fact_lower.split() if len(word) > 3)
            
            if text_match or entity_match or keyword_match:
                supporting_facts.append(
                    {
                        "fact_id": key,
                        "fact": stored_fact,
                        "entities": stored_entities,
                    }
                )

        # Build chain using graph if available
        chain = []
        if self.knowledge_graph and supporting_facts:
            # Find path between supporting facts
            for i, sup_fact in enumerate(supporting_facts[:3]):  # Limit to 3
                entities = sup_fact.get("entities", [])
                if entities:
                    # Try to find path to other supporting facts
                    for other_fact in supporting_facts[i + 1 : i + 2]:
                        other_entities = other_fact.get("entities", [])
                        if other_entities:
                            # Check if entities are connected in graph
                            for entity in entities:
                                for other_entity in other_entities:
                                    if (
                                        self.knowledge_graph.has_node(entity)
                                        and self.knowledge_graph.has_node(other_entity)
                                    ):
                                        try:
                                            if NETWORKX_AVAILABLE and nx is not None:
                                                # nx is imported at module level
                                                path = list(
                                                    nx.shortest_path(
                                                        self.knowledge_graph,
                                                        entity,
                                                        other_entity,
                                                    )
                                                )
                                                if path:
                                                    chain.append(path)
                                        except Exception:
                                            pass

        confidence = min(1.0, len(supporting_facts) * 0.3)

        return {
            "verified": len(supporting_facts) > 0,
            "chain": chain[:5],  # Limit chain length
            "supporting_facts": supporting_facts,
            "confidence": confidence,
            "fact": fact,
        }

    def get_knowledge_path(
        self, source: str, target: str
    ) -> Dict[str, Any]:
        """Get path between two entities in knowledge graph"""
        if not source or not target:
            return {"path": [], "found": False, "length": 0}
        
        # Ensure graph is built
        if not self.knowledge_graph or self.knowledge_graph.number_of_nodes() == 0:
            self.build_knowledge_graph()
        
        # Fallback: simple path finding if graph not available
        if not self.knowledge_graph or not NETWORKX_AVAILABLE:
            # Try to find a path through knowledge base
            source_facts = []
            target_facts = []
            for key, value in self.knowledge_base.items():
                entities = value.get("entities", [])
                if any(source.lower() == e.lower() for e in entities):
                    source_facts.append(key)
                if any(target.lower() == e.lower() for e in entities):
                    target_facts.append(key)
            
            # If both entities appear in same fact, path exists
            for sf in source_facts:
                for tf in target_facts:
                    if sf == tf:
                        return {
                            "path": [{"node": source, "label": source}, {"node": target, "label": target}],
                            "found": True,
                            "length": 1,
                            "source": source,
                            "target": target,
                        }
            
            return {"path": [], "found": False, "length": 0, "reason": "no path found"}

        if not self.knowledge_graph.has_node(source):
            return {"path": [], "found": False, "length": 0, "reason": "source not found"}

        if not self.knowledge_graph.has_node(target):
            return {"path": [], "found": False, "length": 0, "reason": "target not found"}

        try:
            if nx is None:
                import networkx as nx
            
            # Try to find shortest path
            if nx.has_path(self.knowledge_graph, source, target):
                path = list(nx.shortest_path(self.knowledge_graph, source, target))
                path_info = []
                for i, node in enumerate(path):
                    node_data = self.knowledge_graph.nodes[node]
                    path_info.append(
                        {
                            "node": node,
                            "label": node_data.get("label", node),
                            "type": node_data.get("type", "unknown"),
                            "position": i,
                        }
                    )

                return {
                    "path": path_info,
                    "found": True,
                    "length": len(path) - 1,
                    "source": source,
                    "target": target,
                }
            else:
                # Try to find path through intermediate nodes using BFS
                # This handles multi-hop paths like Alice -> Bob -> CompanyX
                from collections import deque
                
                # BFS to find path
                queue = deque([(source, [source])])
                visited = {source}
                max_depth = 5  # Limit search depth
                
                while queue:
                    current, path = queue.popleft()
                    
                    if len(path) > max_depth:
                        continue
                    
                    # Check neighbors
                    for neighbor in self.knowledge_graph.neighbors(current):
                        if neighbor == target:
                            # Found path!
                            full_path = path + [target]
                            path_info = []
                            for i, node in enumerate(full_path):
                                node_data = self.knowledge_graph.nodes[node]
                                path_info.append({
                                    "node": node,
                                    "label": node_data.get("label", node),
                                    "type": node_data.get("type", "unknown"),
                                    "position": i,
                                })
                            return {
                                "path": path_info,
                                "found": True,
                                "length": len(full_path) - 1,
                                "source": source,
                                "target": target,
                            }
                        
                        if neighbor not in visited:
                            visited.add(neighbor)
                            queue.append((neighbor, path + [neighbor]))
                
                # If BFS didn't find a path, try common neighbors as fallback
                source_neighbors = list(self.knowledge_graph.neighbors(source))
                target_neighbors = list(self.knowledge_graph.neighbors(target))
                
                # Check for common neighbors
                common = set(source_neighbors) & set(target_neighbors)
                if common:
                    intermediate = list(common)[0]
                    path_info = [
                        {"node": source, "label": source, "type": "entity", "position": 0},
                        {"node": intermediate, "label": self.knowledge_graph.nodes[intermediate].get("label", intermediate), "type": self.knowledge_graph.nodes[intermediate].get("type", "fact"), "position": 1},
                        {"node": target, "label": target, "type": "entity", "position": 2},
                    ]
                    return {
                        "path": path_info,
                        "found": True,
                        "length": 2,
                        "source": source,
                        "target": target,
                    }
                
                return {
                    "path": [],
                    "found": False,
                    "length": 0,
                    "reason": "no path exists",
                }
        except Exception as e:
            error_str = str(e)
            if "NoPath" in error_str or "no path" in error_str.lower():
                return {
                    "path": [],
                    "found": False,
                    "length": 0,
                    "reason": "no path exists",
                }
            return {"path": [], "found": False, "length": 0, "error": error_str}

    def validate_params(self, operation: str, params: Dict[str, Any]) -> bool:
        """Validate parameters for operations"""
        match operation:
            case "query_knowledge" | "semantic_search":
                return "query" in params
            case "add_knowledge":
                return "fact" in params
            case "validate_fact" | "verify_fact_chain":
                return "fact" in params
            case "get_related_facts":
                return "entity" in params
            case "find_entities":
                return "text" in params
            case "expand_knowledge_base":
                return "facts" in params
            case "retrieve_by_domain":
                return "domain" in params
            case "get_knowledge_path":
                return "source" in params and "target" in params
            case "build_knowledge_graph":
                return True
            case _:
                return True
