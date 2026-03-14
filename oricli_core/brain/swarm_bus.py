from __future__ import annotations
"""
Swarm Bus
Lightweight Pub/Sub messaging system for The Hive.
Facilitates communication between the Broker and Micro-Agents via standard protocols.
"""

import threading
import uuid
import logging
from enum import Enum
from typing import Any, Callable, Dict, List, Optional
from pydantic import BaseModel, Field
import time

logger = logging.getLogger(__name__)

class MessageProtocol(str, Enum):
    """Standard message protocols for The Hive"""
    CFP = "cfp"            # Call for Proposals (Broker -> Agents)
    BID = "bid"            # Bid (Agent -> Broker)
    ACCEPT = "accept"      # Accept Bid (Broker -> Agent)
    REJECT = "reject"      # Reject Bid (Broker -> Agent)
    RESULT = "result"      # Task Result (Agent -> Broker / Blackboard)
    ERROR = "error"        # Execution Error (Agent -> Broker)

class SwarmMessage(BaseModel):
    """Standard message structure for the Swarm Bus"""
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    protocol: MessageProtocol
    topic: str
    sender_id: str
    recipient_id: Optional[str] = None  # None means broadcast
    payload: Dict[str, Any] = Field(default_factory=dict)
    timestamp: float = Field(default_factory=time.time)

class SwarmBus:
    """Thread-safe Pub/Sub message bus for the Swarm"""
    _instance = None
    _lock = threading.Lock()

    def __new__(cls):
        with cls._lock:
            if cls._instance is None:
                cls._instance = super(SwarmBus, cls).__new__(cls)
                cls._instance._initialized = False
            return cls._instance

    def __init__(self):
        if self._initialized:
            return
        
        self._subscribers: Dict[str, List[Callable[[SwarmMessage], None]]] = {}
        self._bus_lock = threading.Lock()
        self._message_history: List[SwarmMessage] = []
        self._initialized = True

    def subscribe(self, topic: str, callback: Callable[[SwarmMessage], None]) -> None:
        """Subscribe to a specific topic"""
        with self._bus_lock:
            if topic not in self._subscribers:
                self._subscribers[topic] = []
            if callback not in self._subscribers[topic]:
                self._subscribers[topic].append(callback)
                logger.debug(f"Added subscriber to topic '{topic}'")

    def unsubscribe(self, topic: str, callback: Callable[[SwarmMessage], None]) -> None:
        """Unsubscribe from a specific topic"""
        with self._bus_lock:
            if topic in self._subscribers and callback in self._subscribers[topic]:
                self._subscribers[topic].remove(callback)
                logger.debug(f"Removed subscriber from topic '{topic}'")

    def publish(self, message: SwarmMessage) -> None:
        """Publish a message to a topic"""
        topic = message.topic
        
        with self._bus_lock:
            self._message_history.append(message)
            # Limit history to prevent memory leak
            if len(self._message_history) > 1000:
                self._message_history.pop(0)
                
            all_subs = []
            
            # Exact match
            if topic in self._subscribers:
                all_subs.extend(self._subscribers[topic])
                
            # Wildcard matches (e.g. 'tasks.bid.*' matches 'tasks.bid.123')
            for sub_topic, callbacks in self._subscribers.items():
                if sub_topic.endswith(".*"):
                    prefix = sub_topic[:-2]
                    if topic.startswith(prefix):
                        for cb in callbacks:
                            if cb not in all_subs:
                                all_subs.append(cb)
                elif sub_topic == "*":
                    for cb in callbacks:
                        if cb not in all_subs:
                            all_subs.append(cb)
        
        # Dispatch in a separate thread to avoid blocking the publisher
        for callback in all_subs:
            try:
                callback(message)
            except Exception as e:
                logger.error(f"Error in SwarmBus subscriber callback: {e}", exc_info=True)

    def get_history(self, limit: int = 100) -> List[SwarmMessage]:
        """Get recent message history"""
        with self._bus_lock:
            return self._message_history[-limit:]

def get_swarm_bus() -> SwarmBus:
    """Get the singleton instance of the SwarmBus"""
    return SwarmBus()
