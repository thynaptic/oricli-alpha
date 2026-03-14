#!/usr/bin/env python3
"""
Oricli-Alpha Metacog Daemon
Monitors module telemetry and triggers self-modification/refactoring tasks.
The first phase of the Singularity Loop.
"""

import time
import logging
import sys
import os
from pathlib import Path
from typing import Dict, Any, List

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from oricli_core.brain.metrics import get_metrics_collector
from oricli_core.brain.registry import ModuleRegistry
from oricli_core.client import OricliAlphaClient

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s")
logger = logging.getLogger("metacog_daemon")

class MetacogDaemon:
    def __init__(self, interval_seconds: int = 60):
        self.interval = interval_seconds
        self.collector = get_metrics_collector()
        self.client = OricliAlphaClient()
        self._running = False
        
        # Heuristic thresholds
        self.LATENCY_THRESHOLD = 5.0  # Seconds
        self.FAILURE_RATE_THRESHOLD = 0.2  # 20%
        self.MIN_CALLS_FOR_ANALYSIS = 5

    def start(self):
        self._running = True
        logger.info("Metacog Daemon started. Monitoring The Hive...")
        
        while self._running:
            try:
                self.run_analysis()
            except Exception as e:
                logger.error(f"Error in Metacog analysis: {e}", exc_info=True)
            
            time.sleep(self.interval)

    def run_analysis(self):
        summary = self.collector.get_summary()
        modules = summary.get("modules", {})
        
        candidates = []
        for name, metrics in modules.items():
            total_calls = metrics.get("total_calls", 0)
            total_time = metrics.get("total_time", 0.0)
            
            if total_calls < self.MIN_CALLS_FOR_ANALYSIS:
                continue
                
            avg_latency = total_time / total_calls
            
            # Fetch detailed metrics for success rate
            detailed = self.collector.get_module_metrics(name)
            total_failures = sum(op.failure_count for op in detailed.operations.values())
            failure_rate = total_failures / total_calls
            
            logger.debug(f"Module {name}: Latency={avg_latency:.2f}s, Failure Rate={failure_rate:.2%}")
            
            if avg_latency > self.LATENCY_THRESHOLD or failure_rate > self.FAILURE_RATE_THRESHOLD:
                candidates.append({
                    "name": name,
                    "latency": avg_latency,
                    "failure_rate": failure_rate,
                    "total_calls": total_calls
                })

        if candidates:
            logger.info(f"Identified {len(candidates)} candidates for self-modification: {[c['name'] for c in candidates]}")
            for candidate in candidates:
                self.trigger_self_reform(candidate)

    def trigger_self_reform(self, candidate: Dict[str, Any]):
        """
        In Phase 2, this will drop a task onto the Swarm Bus.
        For now, we log the intent and the proposed reform.
        """
        module_name = candidate["name"]
        reason = "latency" if candidate["latency"] > self.LATENCY_THRESHOLD else "failure_rate"
        
        logger.info(f"[SINGULARITY] Triggering self-reform task for '{module_name}' due to high {reason}.")
        
        # Mocking the Swarm Dispatch for now
        # In reality, we'd pull the source code and ask 'self_modification_agent' to refactor it.
        # client.chat.completions.create(model="oricli-swarm", messages=[...])

    def stop(self):
        self._running = False

if __name__ == "__main__":
    daemon = MetacogDaemon()
    daemon.start()
