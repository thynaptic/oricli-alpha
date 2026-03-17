"""
Tool Registry Shim - Reroutes to Go Bridge
"""
from oricli_core.brain.go_bridge import ToolRegistry, ToolRegistryError

def get_tool_registry():
    return ToolRegistry()
