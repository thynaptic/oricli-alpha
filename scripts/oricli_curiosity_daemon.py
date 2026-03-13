#!/usr/bin/env python3
"""
OricliAlpha Curiosity Daemon - Active Inference & Epistemic Foraging.
Runs during idle periods to find knowledge gaps and test hypotheses.
"""

import os
import sys
import json
import time
import random
import logging
from pathlib import Path

# Setup paths
REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT))

from oricli_core.brain.registry import ModuleRegistry

# Configure logging
LOG_FILE = REPO_ROOT / "curiosity_daemon.log"
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(message)s',
    handlers=[
        logging.FileHandler(LOG_FILE),
        logging.StreamHandler(sys.stdout)
    ]
)
logger = logging.getLogger("oricli-curiosity")

class OricliAlphaCuriosityDaemon:
    def __init__(self):
        self.running = True
        self.idle_threshold_seconds = 1800  # 30 minutes
        self.curiosity_interval_seconds = 300  # 5 minutes between cycles
        self.last_activity_time = time.time()
        self._ensure_modules()

    def _ensure_modules(self):
        ModuleRegistry.discover_modules()
        try:
            self.cog_gen = ModuleRegistry.get_module("cognitive_generator")
            self.world_knowledge = ModuleRegistry.get_module("world_knowledge")
            self.sandbox = ModuleRegistry.get_module("shell_sandbox_service")
            self.web_search = ModuleRegistry.get_module("web_search")
        except Exception as e:
            logger.error(f"Failed to load required modules for curiosity: {e}")

    def _get_last_activity(self):
        # In a real system, this would check the API logs or a shared state file
        archive_path = REPO_ROOT / "oricli_core/data/conversation_history.jsonl"
        if archive_path.exists():
            return archive_path.stat().st_mtime
        return self.last_activity_time

    def _epistemic_foraging(self):
        """Find gaps in world knowledge and research them."""
        logger.info("🔍 Starting Epistemic Foraging...")
        if not self.world_knowledge or not self.cog_gen or not self.web_search:
            logger.warning("Missing required modules for foraging.")
            return

        try:
            # 1. Get gaps
            res = self.world_knowledge.execute("get_knowledge_gaps", {"limit": 3})
            gaps = res.get("gaps", [])
            
            if not gaps:
                logger.info("No significant knowledge gaps found.")
                return
                
            # Pick a random gap
            gap = random.choice(gaps)
            logger.info(f"Identified gap: {gap}")
            
            source = gap.get("source")
            target = gap.get("target")
            
            if not source or not target:
                return
                
            # 2. Formulate research query
            query_prompt = f"Formulate a single, precise web search query to find the relationship or connection between '{source}' and '{target}'."
            query_res = self.cog_gen.execute("generate_response", {"input": query_prompt})
            search_query = query_res.get("text", "").strip().strip('"\'')
            
            logger.info(f"Researching: {search_query}")
            
            # 3. Search the web
            search_results = self.web_search.execute("search", {"query": search_query, "limit": 3})
            results_text = json.dumps(search_results.get("results", []), indent=2)
            
            # 4. Synthesize new fact
            synth_prompt = f"""
            Based on the following search results, synthesize a concise factual statement explaining the relationship between '{source}' and '{target}'.
            If the results do not show a clear relationship, state that they are unrelated.
            
            Search Results:
            {results_text}
            
            Output a JSON object: {{"fact": "...", "relationship": "...", "confidence": 0.0 to 1.0}}
            """
            
            synth_res = self.cog_gen.execute("generate_response", {"input": synth_prompt})
            text = synth_res.get("text", "")
            
            import re
            json_match = re.search(r"\{.*\}", text, re.DOTALL)
            if json_match:
                data = json.loads(json_match.group(0))
                fact = data.get("fact")
                rel = data.get("relationship", "related_to")
                conf = data.get("confidence", 0.5)
                
                if fact and conf > 0.6:
                    logger.info(f"Synthesized new fact: {fact} (Confidence: {conf})")
                    self.world_knowledge.execute("add_knowledge", {
                        "fact": fact,
                        "entities": [source, target],
                        "relationships": {source: rel},
                        "confidence": conf
                    })
                else:
                    logger.info("Could not synthesize a high-confidence fact.")
            
        except Exception as e:
            logger.error(f"Epistemic foraging failed: {e}")

    def _hypothesis_testing(self):
        """Generate a hypothesis, write code to test it, and learn from the result."""
        logger.info("🧪 Starting Hypothesis Testing...")
        if not self.cog_gen or not self.sandbox or not self.world_knowledge:
            logger.warning("Missing required modules for hypothesis testing.")
            return

        try:
            # 1. Generate hypothesis and script
            hyp_prompt = """
            Generate a simple, testable hypothesis about Python behavior, math, or system performance.
            Then, write a short Python script to test this hypothesis. The script should print the result clearly.
            
            Output a JSON object:
            {
                "hypothesis": "...",
                "script": "print('Hello World')"
            }
            """
            
            hyp_res = self.cog_gen.execute("generate_response", {"input": hyp_prompt})
            text = hyp_res.get("text", "")
            
            import re
            json_match = re.search(r"\{.*\}", text, re.DOTALL)
            if not json_match:
                logger.info("Could not parse hypothesis JSON.")
                return
                
            data = json.loads(json_match.group(0))
            hypothesis = data.get("hypothesis")
            script = data.get("script")
            
            if not hypothesis or not script:
                return
                
            logger.info(f"Testing hypothesis: {hypothesis}")
            
            # 2. Execute script
            exec_res = self.sandbox.execute("execute_python_script", {"script_content": script, "timeout": 15})
            
            success = exec_res.get("success", False)
            stdout = exec_res.get("stdout", "")
            stderr = exec_res.get("stderr", "")
            
            # 3. Synthesize conclusion
            conc_prompt = f"""
            Hypothesis: {hypothesis}
            Script Execution Success: {success}
            Stdout: {stdout}
            Stderr: {stderr}
            
            Did the execution prove or disprove the hypothesis? Synthesize a concise factual conclusion.
            Output a JSON object: {{"conclusion": "...", "confidence": 0.0 to 1.0}}
            """
            
            conc_res = self.cog_gen.execute("generate_response", {"input": conc_prompt})
            conc_text = conc_res.get("text", "")
            
            conc_match = re.search(r"\{.*\}", conc_text, re.DOTALL)
            if conc_match:
                conc_data = json.loads(conc_match.group(0))
                conclusion = conc_data.get("conclusion")
                conf = conc_data.get("confidence", 0.8)
                
                if conclusion:
                    logger.info(f"Conclusion: {conclusion} (Confidence: {conf})")
                    self.world_knowledge.execute("add_knowledge", {
                        "fact": conclusion,
                        "entities": ["Python", "Hypothesis Testing"],
                        "confidence": conf
                    })
                    
        except Exception as e:
            logger.error(f"Hypothesis testing failed: {e}")

    def run(self):
        logger.info("OricliAlpha Curiosity Daemon started.")
        while self.running:
            try:
                last_active = self._get_last_activity()
                idle_time = time.time() - last_active
                
                if idle_time >= self.idle_threshold_seconds:
                    # Randomly choose between foraging and testing
                    if random.random() < 0.5:
                        self._epistemic_foraging()
                    else:
                        self._hypothesis_testing()
                        
                    time.sleep(self.curiosity_interval_seconds)
                else:
                    wait_need = int(self.idle_threshold_seconds - idle_time)
                    logger.info(f"System active. Waiting for idle window ({wait_need}s remaining).")
                    time.sleep(min(wait_need, 300))
            except KeyboardInterrupt:
                break
            except Exception as e:
                logger.error(f"Curiosity loop error: {e}")
                time.sleep(60)

if __name__ == "__main__":
    daemon = OricliAlphaCuriosityDaemon()
    daemon.run()
