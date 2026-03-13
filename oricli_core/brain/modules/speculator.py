from __future__ import annotations
"""
Speculator Module - Anticipates future user queries and triggers background execution.
"""

import threading
import logging
from typing import List, Dict, Any, Optional

from oricli_core.brain.base_module import BaseBrainModule, ModuleMetadata
from oricli_core.brain.registry import ModuleRegistry

logger = logging.getLogger(__name__)

class SpeculatorModule(BaseBrainModule):
    """Anticipates future user queries and triggers background execution."""

    def __init__(self) -> None:
        super().__init__()
        self.cog_gen = None
        self.pipeline = None
        self._precog_service = None
        self._ensure_modules()

    def _ensure_modules(self) -> None:
        try:
            self.cog_gen = ModuleRegistry.get_module("cognitive_generator")
            self.pipeline = ModuleRegistry.get_module("agent_pipeline")
            
            from oricli_core.services.precog_service import PreCogService
            self._precog_service = PreCogService()
        except Exception:
            pass

    @property
    def metadata(self) -> ModuleMetadata:
        return ModuleMetadata(
            name="speculator",
            version="1.0.0",
            description="Anticipates follow-up queries and pre-computes answers",
            operations=["speculate"],
            dependencies=[],
            model_required=False,
        )

    def execute(self, operation: str, params: Dict[str, Any]) -> Dict[str, Any]:
        if operation != "speculate":
            return {"success": False, "error": f"Unknown operation: {operation}"}

        history = params.get("conversation_history", [])
        last_input = params.get("last_input", "")
        last_output = params.get("last_output", "")

        # Non-blocking speculation
        thread = threading.Thread(
            target=self._run_speculation,
            args=(history, last_input, last_output),
            daemon=True
        )
        thread.start()

        return {"success": True, "message": "Speculation triggered in background."}

    def _run_speculation(self, history: List[Dict], last_input: str, last_output: str):
        """Analyze history and pre-compute most likely follow-ups."""
        if not self.cog_gen or not self.pipeline or not self._precog_service:
            return

        # 1. Predict 2 most likely follow-up questions
        prediction_prompt = f"""
        CONTEXT:
        User: {last_input}
        OricliAlpha: {last_output}
        
        TASK: Predict the 2 most likely follow-up questions or requests the user might have.
        Output exactly 2 questions, one per line. No other text.
        """

        try:
            res = self.cog_gen.execute("generate_response", {"input": prediction_prompt})
            text = res.get("text", "")
            predicted_queries = [q.strip() for q in text.split("\n") if q.strip() and "?" in q]
            
            for query in predicted_queries[:2]:
                # 2. Speculatively execute the pipeline for each
                print(f"[Speculator] Anticipating: {query}")
                spec_res = self.pipeline.execute("run_pipeline", {
                    "query": query,
                    "speculative": True
                })
                
                if spec_res.get("success"):
                    # 3. Cache the result
                    self._precog_service.cache_speculative_response(query, spec_res)
                    print(f"[Speculator] Pre-computed and cached answer for: {query}")
                    
        except Exception as e:
            logger.error(f"Speculation loop failed: {e}")
