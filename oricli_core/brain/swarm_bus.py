"""
Swarm Bus Bridge for Oricli-Alpha

This module provides compatibility by exporting Swarm Bus components from go_bridge.
"""

from oricli_core.brain.go_bridge import (
    get_swarm_bus,
    SwarmMessage,
    MessageProtocol,
    SwarmBus,
    GoSwarmBusProxy
)
