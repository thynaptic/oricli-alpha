from __future__ import annotations
"""
Hive Node
Wraps a BaseBrainModule to act as an independent Micro-Agent on the Swarm Bus.
"""

import threading
import logging
from typing import Any, Dict, Optional

from oricli_core.brain.base_module import BaseBrainModule
from oricli_core.brain.swarm_bus import get_swarm_bus, SwarmMessage, MessageProtocol

logger = logging.getLogger(__name__)

class HiveNode:
    """
    A decentralized micro-agent wrapper for brain modules.
    Listens to the Swarm Bus, bids on tasks, and executes them.
    """
    def __init__(self, module: BaseBrainModule):
        self.module = module
        self.bus = get_swarm_bus()
        from oricli_core.services.agent_profile_service import get_agent_profile_service
        self.profile_service = get_agent_profile_service()
        self.node_id = f"hive_node_{self.module.metadata.name}"
        self._active = False
        
        # We need a reference to the broker to know where to send bids,
        # but for a fully decentralized bus, we can just publish to a 'bids' topic.

    def start(self):
        """Start listening to the Swarm Bus"""
        if self._active:
            return
        self.bus.subscribe("tasks.cfp", self._on_cfp)
        self.bus.subscribe(f"tasks.accept.{self.node_id}", self._on_accept)
        self._active = True
        logger.debug(f"{self.node_id} started listening on Swarm Bus")

    def stop(self):
        """Stop listening to the Swarm Bus"""
        if not self._active:
            return
        self.bus.unsubscribe("tasks.cfp", self._on_cfp)
        self.bus.unsubscribe(f"tasks.accept.{self.node_id}", self._on_accept)
        self._active = False
        logger.debug(f"{self.node_id} stopped listening on Swarm Bus")

    def _on_cfp(self, message: SwarmMessage):
        """Handle Call for Proposals"""
        if not self._active or message.protocol != MessageProtocol.CFP:
            return

        payload = message.payload
        operation = payload.get("operation")
        profile_name = payload.get("profile_name")
        
        # Check if we can handle this operation
        if operation not in self.module.metadata.operations:
            return

        # Profile-aware constraint checking
        if profile_name:
            try:
                profile = self.profile_service.get_profile(profile_name)
                if profile:
                    # Use existing validation logic
                    try:
                        self.profile_service.ensure_allowed(profile, module_name=self.module.metadata.name, operation=operation)
                    except Exception:
                        # Module/Operation blocked by profile
                        return
            except Exception:
                pass

        # Simple bidding logic: confidence based on module health/status, cost based on operation complexity
        confidence = 0.95
        compute_cost = 10  # Arbitrary baseline

        bid_payload = {
            "task_id": payload.get("task_id"),
            "operation": operation,
            "confidence": confidence,
            "compute_cost": compute_cost,
            "capabilities": self.module.metadata.operations,
            "skill_overlays": profile.skill_overlays if profile_name and 'profile' in locals() and profile else []
        }

        bid_message = SwarmMessage(
            protocol=MessageProtocol.BID,
            topic=f"tasks.bid.{payload.get('task_id')}",
            sender_id=self.node_id,
            recipient_id=message.sender_id,
            payload=bid_payload
        )
        
        self.bus.publish(bid_message)

    def _on_accept(self, message: SwarmMessage):
        """Handle accepted bid and execute task"""
        if not self._active or message.protocol != MessageProtocol.ACCEPT:
            return

        payload = message.payload
        task_id = payload.get("task_id")
        operation = payload.get("operation")
        params = payload.get("params", {})

        # Execute the module asynchronously to not block the bus
        threading.Thread(
            target=self._execute_task,
            args=(task_id, operation, params, message.sender_id),
            daemon=True
        ).start()

    def _execute_task(self, task_id: str, operation: str, params: Dict[str, Any], broker_id: str):
        """Execute the module operation and publish the result"""
        try:
            # Adopt skill overlays if present in params (sent by broker from winning bid)
            skill_overlays = params.pop("_skill_overlays", [])
            if skill_overlays:
                try:
                    from oricli_core.brain.registry import ModuleRegistry
                    skill_manager = ModuleRegistry.get_module("skill_manager")
                    if skill_manager:
                        mindsets = []
                        instructions = []
                        for skill_name in skill_overlays:
                            res = skill_manager.execute("get_skill", {"skill_name": skill_name})
                            if res.get("success"):
                                skill = res["skill"]
                                if skill.get("mindset"): mindsets.append(skill["mindset"])
                                if skill.get("instructions"): instructions.append(skill["instructions"])
                        
                        if mindsets or instructions:
                            # Inject into params for the module to use (e.g. cognitive_generator)
                            params["_persona_extension"] = "\n\n".join(mindsets)
                            params["_instruction_extension"] = "\n\n".join(instructions)
                except Exception as e:
                    logger.debug(f"Failed to apply skill overlays: {e}")

            logger.debug(f"{self.node_id} executing {operation} for task {task_id}")
            result = self.module.execute(operation, params)
            
            result_message = SwarmMessage(
                protocol=MessageProtocol.RESULT,
                topic=f"tasks.result.{task_id}",
                sender_id=self.node_id,
                recipient_id=broker_id,
                payload={
                    "task_id": task_id,
                    "result": result
                }
            )
            self.bus.publish(result_message)
        except Exception as e:
            logger.error(f"{self.node_id} failed executing {operation}: {e}", exc_info=True)
            error_message = SwarmMessage(
                protocol=MessageProtocol.ERROR,
                topic=f"tasks.error.{task_id}",
                sender_id=self.node_id,
                recipient_id=broker_id,
                payload={
                    "task_id": task_id,
                    "error": str(e)
                }
            )
            self.bus.publish(error_message)
