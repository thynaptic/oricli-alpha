from __future__ import annotations
"""
Graph Executor Module - Executes dynamic cognitive DAGs asynchronously.
Traverses the graph, handles data dependencies, and aggregates results.
"""

import asyncio
import logging
from typing import List, Dict, Any, Optional

from mavaia_core.brain.base_module import BaseBrainModule, ModuleMetadata
from mavaia_core.brain.registry import ModuleRegistry
from mavaia_core.exceptions import InvalidParameterError

logger = logging.getLogger(__name__)

class GraphExecutorModule(BaseBrainModule):
    """Asynchronous engine for dynamic graph execution."""

    def __init__(self) -> None:
        super().__init__()

    @property
    def metadata(self) -> ModuleMetadata:
        return ModuleMetadata(
            name="graph_executor",
            version="1.0.0",
            description="Asynchronous traversal engine for dynamic cognitive graphs",
            operations=["execute_graph"],
            dependencies=[],
            model_required=False,
        )

    def execute(self, operation: str, params: Dict[str, Any]) -> Dict[str, Any]:
        """Synchronous wrapper for async execution."""
        if operation != "execute_graph":
            raise InvalidParameterError(parameter="operation", value=operation, reason="Unsupported operation")

        graph = params.get("graph", {})
        if not graph:
            return {"success": False, "error": "No graph provided"}

        # Run the async loop
        try:
            loop = asyncio.get_event_loop()
        except RuntimeError:
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)

        result = loop.run_until_complete(self._execute_graph_async(graph, params))
        
        return result

    async def _execute_graph_async(self, graph: Dict[str, Any], global_params: Dict[str, Any]) -> Dict[str, Any]:
        """
        Execute the DAG.
        Nodes with no incoming edges are executed first.
        Independent branches run in parallel.
        """
        nodes = graph.get("nodes", [])
        edges = graph.get("edges", [])
        
        results = {}
        node_tasks = {}
        
        # Helper to find dependencies
        def get_deps(node_id):
            return [e["source"] for e in edges if e["target"] == node_id]

        async def run_node(node):
            node_id = node["id"]
            deps = get_deps(node_id)
            
            # 1. Wait for dependencies to complete
            if deps:
                await asyncio.gather(*(node_tasks[d] for d in deps))
            
            # 2. Collect context from dependencies
            accumulated_context = global_params.get("context", "")
            for d in deps:
                d_res = results.get(d, {})
                if isinstance(d_res, dict):
                    text = d_res.get("text") or d_res.get("response") or d_res.get("answer", "")
                    if text:
                        accumulated_context += f"\n[{d} output]: {text}"

            # 3. Prepare params
            module_name = node["module"]
            op_name = node["operation"]
            node_params = {
                **global_params,
                **node.get("params", {}),
                "context": accumulated_context
            }

            # 4. Execute (ModuleRegistry is synchronous, so we run in executor if needed)
            # but for now, we'll call directly and assume some level of async compatibility
            # or wrap in a thread if it's heavy
            try:
                module = ModuleRegistry.get_module(module_name)
                if module:
                    # In a real async system, we'd use await module.execute_async
                    # For now, we simulate async by running in a thread pool
                    loop = asyncio.get_event_loop()
                    result = await loop.run_in_executor(None, lambda: module.execute(op_name, node_params))
                    results[node_id] = result
                else:
                    results[node_id] = {"success": False, "error": f"Module {module_name} not found"}
            except Exception as e:
                results[node_id] = {"success": False, "error": str(e)}

        # Create tasks for all nodes
        for node in nodes:
            node_tasks[node["id"]] = asyncio.create_task(run_node(node))

        # Wait for all tasks to finish
        await asyncio.gather(*node_tasks.values())

        # Determine final result (usually the last node or a node named 'synthesize')
        final_node_id = "synthesize" if "synthesize" in results else nodes[-1]["id"] if nodes else None
        final_output = results.get(final_node_id, {}) if final_node_id else {"success": False, "error": "Empty graph"}

        return {
            "success": True,
            "final_result": final_output,
            "all_results": results
        }
