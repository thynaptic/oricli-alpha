from __future__ import annotations
"""
Neo4j Service - Connection management and Cypher execution for Oricli-Alpha
"""

import os
import logging
from typing import Any, Dict, List, Optional
import threading

try:
    from neo4j import GraphDatabase, Driver
    NEO4J_AVAILABLE = True
except ImportError:
    NEO4J_AVAILABLE = False
    Driver = Any

logger = logging.getLogger(__name__)

class Neo4jService:
    """Manages Neo4j connections and provides high-level graph operations"""
    
    _instance = None
    _lock = threading.Lock()

    def __new__(cls):
        with cls._lock:
            if cls._instance is None:
                cls._instance = super(Neo4jService, cls).__new__(cls)
                cls._instance._initialized = False
            return cls._instance

    def __init__(self):
        if self._initialized:
            return
            
        self.uri = os.environ.get("NEO4J_URI", "bolt://localhost:7687")
        self.user = os.environ.get("NEO4J_USER", "neo4j")
        self.password = os.environ.get("NEO4J_PASSWORD", "password")
        self.driver: Optional[Driver] = None
        
        if NEO4J_AVAILABLE:
            try:
                self.driver = GraphDatabase.driver(self.uri, auth=(self.user, self.password))
                # Test connection
                self.driver.verify_connectivity()
                logger.info(f"Neo4j connected successfully at {self.uri}")
            except Exception as e:
                logger.warning(f"Failed to connect to Neo4j: {e}")
                self.driver = None
        else:
            logger.warning("neo4j-driver not installed. Neo4j operations will be unavailable.")
            
        self._initialized = True

    def close(self):
        """Close the driver connection"""
        if self.driver:
            self.driver.close()

    def execute_query(self, query: str, parameters: Optional[Dict[str, Any]] = None) -> List[Dict[str, Any]]:
        """Execute a Cypher query and return results as a list of dictionaries"""
        if not self.driver:
            return []
            
        try:
            with self.driver.session() as session:
                result = session.run(query, parameters or {})
                return [dict(record) for record in result]
        except Exception as e:
            logger.error(f"Error executing Neo4j query: {e}")
            return []

    def add_node(self, label: str, properties: Dict[str, Any]) -> bool:
        """Add or update a node"""
        if not self.driver:
            return False
            
        # Ensure node has an ID
        if "id" not in properties:
            return False
            
        query = f"MERGE (n:{label} {{id: $id}}) SET n += $props RETURN n"
        params = {"id": properties["id"], "props": properties}
        
        return len(self.execute_query(query, params)) > 0

    def add_relationship(
        self, 
        source_id: str, 
        target_id: str, 
        rel_type: str, 
        properties: Optional[Dict[str, Any]] = None
    ) -> bool:
        """Add or update a relationship between two nodes"""
        if not self.driver:
            return False
            
        query = (
            f"MATCH (a {{id: $source_id}}), (b {{id: $target_id}}) "
            f"MERGE (a)-[r:{rel_type}]->(b) "
            f"SET r += $props "
            f"RETURN r"
        )
        params = {
            "source_id": source_id,
            "target_id": target_id,
            "props": properties or {}
        }
        
        return len(self.execute_query(query, params)) > 0

    def find_path(self, start_id: str, end_id: str, max_depth: int = 3) -> List[Dict[str, Any]]:
        """Find the shortest path between two nodes"""
        if not self.driver:
            return []
            
        query = (
            f"MATCH (start {{id: $start_id}}), (end {{id: $end_id}}), "
            f"p = shortestPath((start)-[*..{max_depth}]->(end)) "
            f"RETURN p"
        )
        params = {"start_id": start_id, "end_id": end_id}
        
        return self.execute_query(query, params)

    def get_neighbors(self, node_id: str, depth: int = 1) -> List[Dict[str, Any]]:
        """Get neighbors of a node up to a certain depth"""
        if not self.driver:
            return []
            
        query = (
            f"MATCH (n {{id: $node_id}})-[r*..{depth}]-(m) "
            f"RETURN m, r"
        )
        params = {"node_id": node_id}
        
        return self.execute_query(query, params)

def get_neo4j_service() -> Neo4jService:
    """Helper to get singleton instance"""
    return Neo4jService()
