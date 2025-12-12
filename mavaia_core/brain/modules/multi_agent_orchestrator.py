"""
Multi Agent Orchestrator - Main orchestrator for multi-agent pipeline execution
Converted from Swift MultiAgentOrchestrator.swift
"""

from typing import Any, Dict, List, Optional, Set
import sys
import time
from pathlib import Path

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent))

from mavaia_core.brain.base_module import BaseBrainModule, ModuleMetadata

# Lazy imports to avoid timeout during module discovery
AgentType = None
DocumentSource = None

def _lazy_import_models():
    """Lazy import models only when needed"""
    global AgentType, DocumentSource
    if AgentType is None:
        try:
            from models.agent_models import AgentType as AT
            from models.retrieval_models import DocumentSource as DS
            AgentType = AT
            DocumentSource = DS
        except ImportError:
            pass


class MultiAgentOrchestratorModule(BaseBrainModule):
    """Main orchestrator for multi-agent pipeline execution"""

    def __init__(self):
        self.search_agent = None
        self.ranking_agent = None
        self.synthesis_agent = None
        self.answer_agent = None
        self.analysis_agent = None
        self.research_agent = None
        self._modules_loaded = False

    @property
    def metadata(self) -> ModuleMetadata:
        return ModuleMetadata(
            name="multi_agent_orchestrator",
            version="1.0.0",
            description="Main orchestrator for multi-agent pipeline execution",
            operations=[
                "orchestrate_agents",
                "coordinate_agents",
                "execute_pipeline",
            ],
            dependencies=[],
            model_required=False,
        )

    def initialize(self) -> bool:
        """Initialize the module"""
        return True

    def _ensure_modules_loaded(self):
        _lazy_import_models()
        """Lazy load dependent modules"""
        if self._modules_loaded:
            return

        try:
            from mavaia_core.brain.registry import ModuleRegistry

            self.search_agent = ModuleRegistry.get_module("search_agent", auto_discover=True, wait_timeout=1.0)
            self.ranking_agent = ModuleRegistry.get_module("ranking_agent", auto_discover=True, wait_timeout=1.0)
            self.synthesis_agent = ModuleRegistry.get_module("synthesis_agent", auto_discover=True, wait_timeout=1.0)
            self.answer_agent = ModuleRegistry.get_module("answer_agent", auto_discover=True, wait_timeout=1.0)
            self.analysis_agent = ModuleRegistry.get_module("analysis_agent", auto_discover=True, wait_timeout=1.0)
            self.research_agent = ModuleRegistry.get_module("research_agent", auto_discover=True, wait_timeout=1.0)

            self._modules_loaded = True
        except Exception as e:
            # Modules not available - will use fallback methods
            pass

    def execute(self, operation: str, params: Dict[str, Any]) -> Dict[str, Any]:
        """Execute an operation"""
        self._ensure_modules_loaded()

        if operation == "orchestrate_agents":
            return self._orchestrate_agents(params)
        elif operation == "coordinate_agents":
            return self._coordinate_agents(params)
        elif operation == "execute_pipeline":
            return self._execute_pipeline(params)
        else:
            raise ValueError(f"Unknown operation: {operation}")

    def _orchestrate_agents(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """Orchestrate agents (alias for execute_pipeline)"""
        return self._execute_pipeline(params)

    def _coordinate_agents(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """Coordinate agents (alias for execute_pipeline)"""
        return self._execute_pipeline(params)

    def _execute_pipeline(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """Execute multi-agent pipeline"""
        query = params.get("query", "")
        # Use string defaults if AgentType/DocumentSource not available
        default_agent_types = ["search", "ranking", "synthesis", "answer"]
        default_sources = ["web", "memory"]
        if AgentType and hasattr(AgentType, 'SEARCH'):
            default_agent_types = [AgentType.SEARCH.value, AgentType.RANKING.value, AgentType.SYNTHESIS.value, AgentType.ANSWER.value]
        if DocumentSource and hasattr(DocumentSource, 'WEB'):
            default_sources = [DocumentSource.WEB.value, DocumentSource.MEMORY.value]
        
        agent_types = params.get("agent_types", default_agent_types)
        sources = params.get("sources", default_sources)

        start_time = time.time()
        all_results = []

        # Execute agents in dependency order
        # Step 1: Search
        search_results = []
        search_value = AgentType.SEARCH.value if AgentType else "search"
        if search_value in agent_types and self.search_agent:
            try:
                result = self.search_agent.execute("search", {
                    "query": query,
                    "sources": sources,
                })
                search_results = result.get("documents", [])
                all_results.append({
                    "agent_type": search_value,
                    "success": True,
                    "output": {"documents": search_results},
                })
            except Exception as e:
                all_results.append({
                    "agent_type": search_value,
                    "success": False,
                    "error": str(e),
                })

        # Step 2: Ranking (depends on search)
        ranked_documents = search_results
        ranking_value = AgentType.RANKING.value if AgentType else "ranking"
        if ranking_value in agent_types and self.ranking_agent and search_results:
            try:
                result = self.ranking_agent.execute("rank", {
                    "documents": search_results,
                    "query": query,
                })
                ranked_documents = result.get("ranked_documents", search_results)
                all_results.append({
                    "agent_type": ranking_value,
                    "success": True,
                    "output": {"ranked_documents": ranked_documents},
                })
            except:
                ranked_documents = search_results

        # Step 3: Synthesis (depends on ranking)
        synthesis_text = ""
        synthesis_value = AgentType.SYNTHESIS.value if AgentType else "synthesis"
        if synthesis_value in agent_types and self.synthesis_agent and ranked_documents:
            try:
                result = self.synthesis_agent.execute("synthesize", {
                    "documents": ranked_documents,
                    "query": query,
                })
                synthesis_text = result.get("synthesis", "")
                all_results.append({
                    "agent_type": synthesis_value,
                    "success": True,
                    "output": {"synthesis": synthesis_text},
                })
            except:
                pass

        # Step 4: Answer (depends on synthesis)
        final_answer = ""
        answer_value = AgentType.ANSWER.value if AgentType else "answer"
        if answer_value in agent_types and self.answer_agent:
            try:
                result = self.answer_agent.execute("answer", {
                    "query": query,
                    "context": synthesis_text,
                    "documents": ranked_documents,
                })
                final_answer = result.get("answer", "")
                all_results.append({
                    "agent_type": answer_value,
                    "success": True,
                    "output": {"answer": final_answer},
                })
            except:
                pass

        execution_time = time.time() - start_time
        success = all(r.get("success", False) for r in all_results if r.get("agent_type") in agent_types)

        return {
            "success": success,
            "query": query,
            "answer": final_answer,
            "documents": ranked_documents,
            "agent_results": all_results,
            "execution_time": execution_time,
        }

