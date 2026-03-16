"""
Go Bridge Utility for Oricli-Alpha Python Modules

This provides a compatibility layer for remaining Python modules to interact
with the Go-native backbone, replacing the deleted legacy Python services.
"""

import os
import json
import httpx
import logging
import time
from typing import Any, Dict, List, Optional
from dataclasses import dataclass, field

logger = logging.getLogger(__name__)

# --- Compatibility Stubs for Legacy Imports ---

@dataclass
class SwarmMessage:
    topic: str
    payload: Dict[str, Any]
    protocol: str = "cfp"
    sender_id: str = "python_bridge"
    id: str = ""
    timestamp: float = field(default_factory=time.time)

    def to_dict(self):
        return {
            "topic": self.topic,
            "payload": self.payload,
            "protocol": self.protocol,
            "sender_id": self.sender_id,
            "id": self.id,
            "timestamp": self.timestamp
        }

@dataclass
class AgentProfile:
    name: str
    description: str = ""
    allowed_modules: List[str] = field(default_factory=list)
    allowed_operations: Dict[str, List[str]] = field(default_factory=dict)
    system_instructions: str = ""
    model_preference: str = ""

class MessageProtocol:
    CFP = "cfp"
    BID = "bid"
    ACCEPT = "accept"
    REJECT = "reject"
    RESULT = "result"
    ERROR = "error"

class MemoryCategory:
    SEMANTIC = "semantic"
    EPISODIC = "episodic"
    IDENTITY = "identity"
    SKILL = "skill"
    LONG_TERM_STATE = "long_term_state"
    REFLECTION_LOG = "reflection_log"
    VECTOR_INDEX = "vector_index"

class MemoryBridgeError(Exception):
    """Base error for memory bridge"""
    pass

class MemoryBridgeService:
    """Mock for legacy memory service calls"""
    def execute(self, op, params):
        return get_go_service().execute(op, params)

@dataclass
class MemoryBridgeConfig:
    db_path: str
    encryption_key: str
    map_size: int = 512 * 1024 * 1024

class ToolExecutionService:
    """Mock for legacy tool service calls"""
    async def execute_tool(self, name, args):
        return get_go_service().execute(name, args)

# --- Real Logic ---

class GoSwarmBusProxy:
    """Proxy for the Go-native Swarm Bus via HTTP API"""
    def __init__(self, addr: str = "http://localhost:8089"):
        self.addr = addr

    def publish(self, topic: str, payload: Dict[str, Any], protocol: str = "cfp"):
        """Publish a message to the Go Swarm Bus"""
        try:
            with httpx.Client(timeout=10.0) as client:
                client.post(f"{self.addr}/v1/swarm/inject", json={
                    "topic": topic,
                    "payload": payload,
                    "protocol": protocol
                })
        except Exception as e:
            logger.warning(f"Failed to publish to Go Swarm Bus: {e}")

class GoServiceProxy:
    """Generic proxy for Go-native services"""
    def __init__(self, addr: str = "http://localhost:8089"):
        self.addr = addr

    def execute(self, operation: str, params: Dict[str, Any]) -> Dict[str, Any]:
        """Execute an operation on the Go Backbone"""
        try:
            with httpx.Client(timeout=60.0) as client:
                resp = client.post(f"{self.addr}/v1/chat/completions", json={
                    "model": "oricli-swarm",
                    "operation": operation,
                    "params": params
                })
                if resp.status_code == 200:
                    return resp.json()
                return {"success": False, "error": f"Go returned {resp.status_code}"}
        except Exception as e:
            return {"success": False, "error": str(e)}

# --- Singleton Instances ---

_BUS = None
_GO = None
tool_execution_service = ToolExecutionService()

def get_swarm_bus():
    global _BUS
    if _BUS is None:
        _BUS = GoSwarmBusProxy(os.environ.get("ORICLI_GO_ADDR", "http://localhost:8089"))
    return _BUS

def get_go_service():
    global _GO
    if _GO is None:
        _GO = GoServiceProxy(os.environ.get("ORICLI_GO_ADDR", "http://localhost:8089"))
    return _GO

# Aliases
def get_neo4j_service(): return get_go_service()
def get_memory_bridge_service(): return get_go_service()
def get_agent_profile_service(): return get_go_service()
def get_tool_registry(): return get_go_service()
def get_cognitive_generator(): return get_go_service()
def get_neural_text_generator(): return get_go_service()
def get_custom_reasoning_networks(): return get_go_service()
