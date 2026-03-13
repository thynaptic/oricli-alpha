#!/usr/bin/env python3
"""
Oricli-Alpha Dream Daemon - Cognitive Consolidation.
Runs during idle periods to find novel connections between memories and facts.
"""

import os
import sys
import json
import time
import random
import logging
from pathlib import Path
from datetime import datetime

# Setup paths
REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT))

from oricli_core.brain.registry import ModuleRegistry
from oricli_core.services.insight_service import InsightService

# Configure logging
LOG_FILE = REPO_ROOT / "dream_daemon.log"
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(message)s',
    handlers=[
        logging.FileHandler(LOG_FILE),
        logging.StreamHandler(sys.stdout)
    ]
)
logger = logging.getLogger("oricli-dream")

class Oricli-AlphaDreamDaemon:
    def __init__(self):
        self.running = True
        self.idle_threshold_seconds = 1800 # 30 minutes
        self.dream_interval_seconds = 300 # 5 minutes between dream cycles
        self.last_activity_time = time.time()
        self.insight_service = InsightService()
        self._ensure_modules()

    def _ensure_modules(self):
        ModuleRegistry.discover_modules()
        try:
            self.cog_gen = ModuleRegistry.get_module("cognitive_generator")
            self.memory = ModuleRegistry.get_module("memory_graph")
        except Exception as e:
            logger.error(f"Failed to load required modules for dreaming: {e}")

    def _get_last_activity(self):
        # In a real system, this would check the API logs or a shared state file
        # For now, we'll check the mtime of the conversation archive if it exists
        archive_path = REPO_ROOT / "oricli_core/data/conversation_history.jsonl"
        if archive_path.exists():
            return archive_path.stat().st_mtime
        return self.last_activity_time

    def _sample_knowledge(self):
        """Sample disparate facts from memory and JIT buffer."""
        facts = []
        
        # 1. Pull from JIT buffer
        jit_path = REPO_ROOT / "oricli_core/data/jit_absorption.jsonl"
        if jit_path.exists():
            with open(jit_path, "r", encoding="utf-8") as f:
                jit_lines = f.readlines()
                if jit_lines:
                    # Pick 2-3 random recent JIT facts
                    samples = random.sample(jit_lines, min(len(jit_lines), 3))
                    for s in samples:
                        data = json.loads(s)
                        facts.append(data.get("response", ""))

        # 2. Pull from Memory Graph (if available)
        if self.memory:
            try:
                # Mocking memory graph search for diverse nodes
                res = self.memory.execute("search", {"query": "*", "limit": 10})
                nodes = res.get("nodes", [])
                if nodes:
                    samples = random.sample(nodes, min(len(nodes), 3))
                    for n in samples:
                        facts.append(n.get("content", ""))
            except Exception:
                pass

        return facts

    def dream_cycle(self):
        """Perform a single consolidation cycle."""
        logger.info("🌙 Entering Dream State: Consolidating knowledge...")
        
        facts = self._sample_knowledge()
        if len(facts) < 2:
            logger.info("Not enough information to dream. Sleeping.")
            return

        # Pick two facts to analogize
        fact_a, fact_b = random.sample(facts, 2)
        
        logger.info(f"Dreaming about the connection between: '{fact_a[:50]}...' AND '{fact_b[:50]}...'")

        dream_prompt = f"""
        ACT AS: Oricli-Alpha's Subconscious (Dream State)
        TASK: Find a novel, high-level correlation or insight between these two disparate pieces of information.
        
        FACT A: {fact_a}
        FACT B: {fact_b}
        
        OUTPUT: 
        1. A concise description of the new 'Insight'.
        2. A score from 0.0 to 1.0 representing the utility/relevance of this connection.
        
        Format as JSON: {{"insight": "...", "score": 0.0}}
        """

        try:
            res = self.cog_gen.execute("generate_response", {"input": dream_prompt})
            text = res.get("text", "")
            
            # Extract JSON
            import re
            json_match = re.search(r"\{.*\}", text, re.DOTALL)
            if json_match:
                data = json.loads(json_match.group(0))
                insight = data.get("insight")
                score = data.get("score", 0.0)
                
                if insight and score > 0.6:
                    id = self.insight_service.record_insight(insight, fact_a, fact_b, score)
                    logger.info(f"✨ Novel Insight Generated [{id}]: Score {score}")
                else:
                    logger.info("Dream resulted in low-confidence noise.")
            else:
                logger.warning("Could not parse dream insights.")
        except Exception as e:
            logger.error(f"Dream cycle failed: {e}")

    def run(self):
        logger.info("Oricli-Alpha Dream Daemon started.")
        while self.running:
            try:
                last_active = self._get_last_activity()
                idle_time = time.time() - last_active
                
                if idle_time >= self.idle_threshold_seconds:
                    self.dream_cycle()
                    time.sleep(self.dream_interval_seconds)
                else:
                    wait_need = int(self.idle_threshold_seconds - idle_time)
                    logger.info(f"System active. Waiting for idle window ({wait_need}s remaining).")
                    time.sleep(min(wait_need, 300))
            except KeyboardInterrupt:
                break
            except Exception as e:
                logger.error(f"Dream loop error: {e}")
                time.sleep(60)

if __name__ == "__main__":
    daemon = Oricli-AlphaDreamDaemon()
    daemon.run()
