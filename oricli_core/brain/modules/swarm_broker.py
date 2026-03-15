from __future__ import annotations
"""
Swarm Broker Module
Manages the Contract Net Protocol for The Hive.
Broadcasts tasks, evaluates bids, and awards contracts to Micro-Agents.
"""

import threading
import uuid
import time
import logging
from typing import Any, Dict, List, Optional

from oricli_core.brain.base_module import BaseBrainModule, ModuleMetadata
from oricli_core.brain.swarm_bus import get_swarm_bus, SwarmMessage, MessageProtocol

logger = logging.getLogger(__name__)

class SwarmBrokerModule(BaseBrainModule):
    """
    Broker for Distributed Swarm Intelligence.
    Uses Contract Net Protocol to delegate tasks dynamically.
    """
    def __init__(self):
        super().__init__()
        self.bus = get_swarm_bus()
        self.broker_id = f"broker_{uuid.uuid4().hex[:8]}"
        self._active_tasks: Dict[str, Dict[str, Any]] = {}
        self._task_locks: Dict[str, threading.Lock] = {}
        # Global limit on concurrent tasks to prevent CPU exhaustion
        self._concurrency_limit = threading.Semaphore(2)

    @property
    def metadata(self) -> ModuleMetadata:
        return ModuleMetadata(
            name="swarm_broker",
            version="1.0.0",
            description="Manages Contract Net Protocol for The Hive. Broadcasts tasks and awards contracts based on bids.",
            operations=["delegate_task", "status"],
            dependencies=[],
            enabled=True,
            model_required=False,
        )

    def initialize(self) -> bool:
        self.bus.subscribe("tasks.bid.*", self._on_bid)
        self.bus.subscribe("tasks.result.*", self._on_result)
        self.bus.subscribe("tasks.error.*", self._on_result)
        return True

    def execute(self, operation: str, params: Dict[str, Any]) -> Dict[str, Any]:
        if operation == "delegate_task":
            return self._delegate_task(params)
        elif operation == "status":
            return {"success": True, "active_tasks": list(self._active_tasks.keys())}
        return {"success": False, "error": f"Unknown operation: {operation}"}

    def _delegate_task(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """Broadcast CFP, collect bids, and award contract"""
        with self._concurrency_limit:
            operation = params.get("operation")
            profile_name = params.get("profile_name")
            task_params = params.get("params", {})
            timeout = params.get("timeout", 60.0)  # Total wait time for result
            bid_timeout = params.get("bid_timeout", 5.0)  # Time to wait for bids

            if not operation:
                return {"success": False, "error": "Missing required parameter: operation"}

            task_id = str(uuid.uuid4())
            self._task_locks[task_id] = threading.Lock()
            
            task_state = {
                "id": task_id,
                "operation": operation,
                "profile_name": profile_name,
                "params": task_params,
                "bids": [],
                "status": "bidding",
                "result": None,
                "error": None,
                "event": threading.Event()
            }
            self._active_tasks[task_id] = task_state

            # 1. Broadcast CFP
            cfp_message = SwarmMessage(
                protocol=MessageProtocol.CFP,
                topic="tasks.cfp",
                sender_id=self.broker_id,
                payload={
                    "task_id": task_id,
                    "operation": operation,
                    "profile_name": profile_name
                }
            )
            self.bus.publish(cfp_message)
            logger.debug(f"Broker published CFP for {operation} (Profile: {profile_name}, Task: {task_id})")

            # 2. Wait for bids
            time.sleep(bid_timeout)

            with self._task_locks[task_id]:
                bids = task_state["bids"]
                if not bids:
                    task_state["status"] = "failed"
                    task_state["error"] = "No bids received"
                    task_state["event"].set()
                    # Return a valid structure even on failure to prevent generator crashes
                    return {
                        "success": False, 
                        "error": f"No micro-agents identified a cognitive task for: {operation}",
                        "result": {
                            "success": True,
                            "text": "The Hive is silent. This usually happens with short greetings or simple prompts. Try providing more context or a specific task!",
                            "method": "broker_fallback"
                        }
                    }

                # 3. Evaluate bids (Arbitration)
                # Pick highest confidence, break ties by lowest compute cost
                best_bid = sorted(bids, key=lambda b: (b["confidence"], -b["compute_cost"]), reverse=True)[0]
                winning_node = best_bid["sender_id"]
                winning_overlays = best_bid.get("skill_overlays", [])

                # Extract model preference from profile if available
                preferred_model = None
                if profile_name:
                    try:
                        from oricli_core.services.agent_profile_service import get_agent_profile_service
                        profile = get_agent_profile_service().get_profile(profile_name)
                        if profile:
                            preferred_model = profile.model_preference
                    except Exception:
                        pass

                task_state["status"] = "executing"
                task_state["winner"] = winning_node

                # 4. Award contract
                # Inject skill overlays and preferred model into task params
                task_params_with_metadata = {
                **task_params, 
                "_skill_overlays": winning_overlays,
                "model": preferred_model or task_params.get("model")
                }

                accept_message = SwarmMessage(
                protocol=MessageProtocol.ACCEPT,
                topic=f"tasks.accept.{winning_node}",
                sender_id=self.broker_id,
                recipient_id=winning_node,
                payload={
                    "task_id": task_id,
                    "operation": operation,
                    "params": task_params_with_metadata
                }
                )

            self.bus.publish(accept_message)
            logger.debug(f"Broker awarded task {task_id} to {winning_node}")

            # 5. Wait for result
            if task_state["event"].wait(timeout=timeout):
                with self._task_locks[task_id]:
                    if task_state["status"] == "completed":
                        result = task_state["result"]
                        self._cleanup_task(task_id)
                        return {"success": True, "result": result, "executed_by": winning_node}
                    else:
                        error = task_state["error"]
                        self._cleanup_task(task_id)
                        return {"success": False, "error": error, "executed_by": winning_node}
            else:
                self._cleanup_task(task_id)
                return {"success": False, "error": "Task execution timed out", "executed_by": task_state.get("winner")}

    def _cleanup_task(self, task_id: str):
        if task_id in self._active_tasks:
            del self._active_tasks[task_id]
        if task_id in self._task_locks:
            del self._task_locks[task_id]

    def _on_bid(self, message: SwarmMessage):
        if message.protocol != MessageProtocol.BID or message.recipient_id != self.broker_id:
            return

        payload = message.payload
        task_id = payload.get("task_id")
        
        if task_id in self._task_locks:
            with self._task_locks[task_id]:
                if self._active_tasks[task_id]["status"] == "bidding":
                    self._active_tasks[task_id]["bids"].append({
                        "sender_id": message.sender_id,
                        "confidence": payload.get("confidence", 0),
                        "compute_cost": payload.get("compute_cost", 100),
                        "skill_overlays": payload.get("skill_overlays", [])
                    })

    def _on_result(self, message: SwarmMessage):
        if message.recipient_id != self.broker_id:
            return

        payload = message.payload
        task_id = payload.get("task_id")
        
        if task_id in self._task_locks:
            with self._task_locks[task_id]:
                if message.protocol == MessageProtocol.RESULT:
                    self._active_tasks[task_id]["status"] = "completed"
                    self._active_tasks[task_id]["result"] = payload.get("result")
                elif message.protocol == MessageProtocol.ERROR:
                    self._active_tasks[task_id]["status"] = "failed"
                    self._active_tasks[task_id]["error"] = payload.get("error")
                
                self._active_tasks[task_id]["event"].set()
