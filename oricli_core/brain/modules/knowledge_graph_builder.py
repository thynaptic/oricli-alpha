from __future__ import annotations
"""
Knowledge Graph Builder Module
Takes unstructured text, extracts entities and relationships, and builds a queryable RDF-like graph.
"""

import json
import time
import logging
from typing import Dict, Any, List, Optional

from oricli_core.brain.base_module import BaseBrainModule, ModuleMetadata
from oricli_core.exceptions import InvalidParameterError, ModuleOperationError

logger = logging.getLogger(__name__)

try:
    import networkx as nx
    NETWORKX_AVAILABLE = True
except ImportError:
    NETWORKX_AVAILABLE = False
    nx = None

class KnowledgeGraphBuilder(BaseBrainModule):
    """Builds and queries knowledge graphs from unstructured text."""

    def __init__(self):
        super().__init__()
        self.graph = None
        self.is_initialized = False

    @property
    def metadata(self) -> ModuleMetadata:
        return ModuleMetadata(
            name="knowledge_graph_builder",
            version="1.0.0",
            description="Extracts entities and relationships from text to build a queryable graph.",
            operations=[
                "build_from_text",
                "query_graph",
                "export_rdf",
            ],
            dependencies=["networkx"],
            model_required=False,
        )

    def initialize(self) -> bool:
        if not NETWORKX_AVAILABLE:
            logger.warning("networkx not available. KnowledgeGraphBuilder will have limited functionality.")
        
        if NETWORKX_AVAILABLE:
            self.graph = nx.MultiDiGraph()
        else:
            self.graph = {} # Fallback dict
            
        self.is_initialized = True
        return True

    def execute(self, operation: str, params: Dict[str, Any]) -> Dict[str, Any]:
        if not self.is_initialized:
            self.initialize()

        if operation == "build_from_text":
            return self._build_from_text(params)
        elif operation == "query_graph":
            return self._query_graph(params)
        elif operation == "export_rdf":
            return self._export_rdf(params)
        else:
            raise InvalidParameterError("operation", operation, "Unknown operation")

    def _build_from_text(self, params: Dict[str, Any]) -> Dict[str, Any]:
        text = params.get("text")
        if not text:
            raise InvalidParameterError("text", str(text), "text is required")
            
        try:
            from oricli_core.brain.registry import ModuleRegistry
            ModuleRegistry.discover_modules()
            cog_gen = ModuleRegistry.get_module("cognitive_generator")
            
            if not cog_gen:
                return {"success": False, "error": "cognitive_generator not available"}
                
            # Use LLM to extract entities and relationships in one go
            prompt = f"""
            Analyze the following text and extract all named entities and the relationships between them.
            Format the output as a strict JSON object with two lists: 'entities' and 'relationships'.
            
            Entities should have: 'id' (string, normalized name), 'label' (string, original name), 'type' (string, e.g., PERSON, ORG, CONCEPT).
            Relationships should have: 'source' (string, entity id), 'target' (string, entity id), 'type' (string, the relationship predicate).
            
            Text:
            {text}
            
            Output JSON only:
            """
            
            res = cog_gen.execute("generate_response", {"input": prompt})
            output_text = res.get("text", "")
            
            import re
            json_match = re.search(r"\{.*\}", output_text, re.DOTALL)
            if not json_match:
                return {"success": False, "error": "Failed to parse JSON from generator"}
                
            data = json.loads(json_match.group(0))
            entities = data.get("entities", [])
            relationships = data.get("relationships", [])
            
            # Add to local graph
            if NETWORKX_AVAILABLE:
                for entity in entities:
                    self.graph.add_node(entity["id"], label=entity.get("label", entity["id"]), type=entity.get("type", "UNKNOWN"))
                    
                for rel in relationships:
                    self.graph.add_edge(rel["source"], rel["target"], relationship=rel.get("type", "related_to"), timestamp=time.time())
            else:
                # Fallback dict implementation
                for entity in entities:
                    self.graph[entity["id"]] = {"label": entity.get("label", entity["id"]), "type": entity.get("type", "UNKNOWN"), "edges": []}
                for rel in relationships:
                    if rel["source"] in self.graph:
                        self.graph[rel["source"]]["edges"].append({
                            "target": rel["target"],
                            "relationship": rel.get("type", "related_to"),
                            "timestamp": time.time()
                        })
            
            # Optionally sync with world_knowledge if available
            world_knowledge = ModuleRegistry.get_module("world_knowledge")
            if world_knowledge:
                for rel in relationships:
                    world_knowledge.execute("add_knowledge", {
                        "fact": f"{rel['source']} is {rel.get('type', 'related to')} {rel['target']}",
                        "entities": [rel["source"], rel["target"]],
                        "relationships": {rel["source"]: rel.get("type", "related_to")}
                    })
                    
            return {
                "success": True,
                "entities_extracted": len(entities),
                "relationships_extracted": len(relationships)
            }
            
        except Exception as e:
            logger.error(f"Error in build_from_text: {e}")
            return {"success": False, "error": str(e)}

    def _query_graph(self, params: Dict[str, Any]) -> Dict[str, Any]:
        entity_id = params.get("entity_id")
        if not entity_id:
            raise InvalidParameterError("entity_id", str(entity_id), "entity_id is required")
            
        if not NETWORKX_AVAILABLE:
            return {"success": False, "error": "networkx required for querying"}
            
        if not self.graph.has_node(entity_id):
            return {"success": True, "neighbors": []}
            
        neighbors = []
        for neighbor in self.graph.neighbors(entity_id):
            # For MultiDiGraph, edges is a dict of dicts
            edge_data = self.graph.get_edge_data(entity_id, neighbor)
            for key, data in edge_data.items():
                neighbors.append({
                    "entity": neighbor,
                    "label": self.graph.nodes[neighbor].get("label", neighbor),
                    "relationship": data.get("relationship", "unknown")
                })
                
        return {"success": True, "neighbors": neighbors}

    def _export_rdf(self, params: Dict[str, Any]) -> Dict[str, Any]:
        if not NETWORKX_AVAILABLE:
            return {"success": False, "error": "networkx required for RDF export"}
            
        triples = []
        for u, v, data in self.graph.edges(data=True):
            triples.append({
                "subject": u,
                "predicate": data.get("relationship", "related_to"),
                "object": v
            })
            
        return {"success": True, "triples": triples}
