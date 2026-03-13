#!/usr/bin/env python3
"""
Verification script for the Knowledge Graph Builder module.
"""

import sys
import os
import json
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from oricli_core.brain.registry import ModuleRegistry

def main():
    print("Initializing Module Registry...")
    ModuleRegistry.discover_modules()
    
    kg_builder = ModuleRegistry.get_module("knowledge_graph_builder")
    if not kg_builder:
        print("Failed to load knowledge_graph_builder module.")
        return
        
    print("Knowledge Graph Builder module loaded successfully.")
    
    # Test text
    text = """
    Albert Einstein was a theoretical physicist who developed the theory of relativity. 
    He was born in Ulm, Germany. Einstein worked at the Institute for Advanced Study in Princeton.
    """
    
    print(f"\nProcessing text:\n{text}")
    
    # 1. Build from text
    print("\n1. Building graph from text...")
    # We mock the cognitive_generator response for testing if it's not fully functional
    # In a real run, this would call the actual LLM
    
    # Let's see if we can run the real one
    cog_gen = ModuleRegistry.get_module("cognitive_generator")
    if cog_gen:
        print("Using real cognitive_generator...")
        res = kg_builder.execute("build_from_text", {"text": text})
        print(f"Build result: {res}")
    else:
        print("cognitive_generator not found, skipping real extraction test.")
        
    # 2. Add some manual nodes/edges to test query and export
    print("\n2. Adding manual nodes for query/export testing...")
    if kg_builder.graph is not None and hasattr(kg_builder.graph, "add_node"):
        kg_builder.graph.add_node("Albert_Einstein", label="Albert Einstein", type="PERSON")
        kg_builder.graph.add_node("Theory_of_Relativity", label="Theory of Relativity", type="CONCEPT")
        kg_builder.graph.add_node("Ulm", label="Ulm", type="LOCATION")
        
        kg_builder.graph.add_edge("Albert_Einstein", "Theory_of_Relativity", relationship="developed")
        kg_builder.graph.add_edge("Albert_Einstein", "Ulm", relationship="born_in")
        
        # 3. Query Graph
        print("\n3. Querying graph for 'Albert_Einstein'...")
        query_res = kg_builder.execute("query_graph", {"entity_id": "Albert_Einstein"})
        print(json.dumps(query_res, indent=2))
        
        # 4. Export RDF
        print("\n4. Exporting RDF...")
        rdf_res = kg_builder.execute("export_rdf", {})
        print(json.dumps(rdf_res, indent=2))
    else:
        print("NetworkX graph not available, skipping query/export tests.")

if __name__ == "__main__":
    main()
