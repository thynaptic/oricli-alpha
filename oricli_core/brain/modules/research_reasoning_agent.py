from __future__ import annotations
"""
Research Reasoning Agent - Orchestrates multi-step reasoning for research mode
Converted from Swift ResearchReasoningAgent.swift
"""

from typing import Any, Dict, List, Optional
import logging

from oricli_core.brain.base_module import BaseBrainModule, ModuleMetadata
from oricli_core.brain.registry import ModuleRegistry
from oricli_core.exceptions import InvalidParameterError

logger = logging.getLogger(__name__)


class ResearchReasoningAgentModule(BaseBrainModule):
    """Orchestrates multi-step reasoning for research mode"""

    def __init__(self):
        super().__init__()
        self.web_search = None
        self.cognitive_generator = None
        self._modules_loaded = False

    @property
    def metadata(self) -> ModuleMetadata:
        return ModuleMetadata(
            name="research_reasoning_agent",
            version="1.0.0",
            description="Orchestrates multi-step reasoning for research mode",
            operations=[
                "conduct_research",
                "synthesize_research",
                "perform_research_with_reasoning",
            ],
            dependencies=[],
            model_required=False,
        )

    def initialize(self) -> bool:
        """Initialize the module"""
        return True

    def _ensure_modules_loaded(self):
        """Lazy load dependent modules"""
        if self._modules_loaded:
            return

        try:
            self.web_search = ModuleRegistry.get_module("web_scraper")
            self.cognitive_generator = ModuleRegistry.get_module("cognitive_generator")

            self._modules_loaded = True
        except Exception as e:
            # Modules not available - will use fallback methods
            logger.debug(
                "Failed to load one or more optional research_reasoning_agent dependencies",
                exc_info=True,
                extra={"module_name": "research_reasoning_agent", "error_type": type(e).__name__},
            )

    def execute(self, operation: str, params: Dict[str, Any]) -> Dict[str, Any]:
        """Execute an operation"""
        self._ensure_modules_loaded()

        if operation == "conduct_research":
            return self._conduct_research(params)
        elif operation == "synthesize_research":
            return self._synthesize_research(params)
        elif operation == "perform_research_with_reasoning":
            return self._perform_research_with_reasoning(params)
        else:
            raise InvalidParameterError(
                parameter="operation",
                value=operation,
                reason="Unknown operation for research_reasoning_agent",
            )

    def _conduct_research(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """Conduct research on a query"""
        query = params.get("query", "")
        max_results = params.get("max_results", 10)

        if not isinstance(query, str) or not query.strip():
            raise InvalidParameterError("query", str(query), "query must be a non-empty string")

        if not self.web_search:
            return {
                "success": False,
                "error": "Web search service not available",
                "results": [],
            }

        try:
            result = self.web_search.execute("search", {
                "query": query,
                "max_results": max_results,
            })

            return {
                "success": True,
                "results": result.get("results", []),
                "query": query,
            }
        except Exception as e:
            logger.debug(
                "Web search execution failed",
                exc_info=True,
                extra={"module_name": "research_reasoning_agent", "error_type": type(e).__name__},
            )
            return {
                "success": False,
                "error": "Web search failed",
                "results": [],
            }

    def _synthesize_research(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """Synthesize research results"""
        query = params.get("query", "")
        results = params.get("results", [])

        if not self.cognitive_generator:
            return {
                "success": False,
                "error": "Cognitive generator not available",
                "synthesis": "",
            }

        # Build synthesis prompt
        results_text = "\n\n".join([
            f"Source: {r.get('title', 'Unknown')}\n{r.get('snippet', '')}"
            for r in results[:10]  # Limit to 10 results
        ])

        synthesis_prompt = f"""
        Research Query: {query}
        
        Research Results:
        {results_text}
        
        Please synthesize these research results into a comprehensive answer to the query.
        Include key findings, important details, and cite sources where relevant.
        """

        try:
            result = self.cognitive_generator.execute("generate_response", {
                "input": synthesis_prompt,
                "context": "You are a research assistant synthesizing information from multiple sources.",
            })

            return {
                "success": True,
                "synthesis": result.get("text", ""),
                "sources": [r.get("url", "") for r in results],
            }
        except Exception as e:
            logger.debug(
                "Research synthesis failed",
                exc_info=True,
                extra={"module_name": "research_reasoning_agent", "error_type": type(e).__name__},
            )
            return {
                "success": False,
                "error": "Synthesis failed",
                "synthesis": "",
            }

    def _perform_research_with_reasoning(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """Perform research with multi-step reasoning"""
        query = params.get("query", "")
        if not isinstance(query, str) or not query.strip():
            raise InvalidParameterError("query", str(query), "query must be a non-empty string")
        max_passes = min(max(params.get("max_passes", 5), 2), 7)  # Enforce 2-7 range

        passes = []
        all_sources = []
        seen_urls = set()
        accumulated_context = ""

        # Pass 1: Query Decomposition
        if self.cognitive_generator:
            try:
                decomposition = self.cognitive_generator.execute("decompose_query", {
                    "query": query,
                })
                sub_questions = decomposition.get("sub_questions", [query])
            except Exception as e:
                logger.debug(
                    "Query decomposition failed; using original query",
                    exc_info=True,
                    extra={"module_name": "research_reasoning_agent", "error_type": type(e).__name__},
                )
                sub_questions = [query]
        else:
            sub_questions = [query]

        # Perform initial searches
        for sub_question in sub_questions[:5]:  # Limit to 5 sub-questions
            if self.web_search:
                try:
                    search_result = self.web_search.execute("search", {
                        "query": sub_question,
                        "max_results": 5,
                    })
                    for item in search_result.get("results", []):
                        url = item.get("url", "")
                        if url and url not in seen_urls:
                            seen_urls.add(url)
                            all_sources.append(item)
                except Exception as e:
                    logger.debug(
                        "Search sub-question failed; continuing",
                        exc_info=True,
                        extra={"module_name": "research_reasoning_agent", "error_type": type(e).__name__},
                    )

        # Create first pass
        passes.append({
            "pass_number": 1,
            "sub_questions": sub_questions,
            "search_queries": sub_questions,
            "search_results": all_sources[:10],
            "analysis": None,
            "decision": "continue",
            "confidence": 0.7,
        })

        # Additional passes (simplified)
        for pass_num in range(2, max_passes + 1):
            # In full implementation, would do deeper reasoning
            # For now, just synthesize what we have
            if pass_num == max_passes:
                # Final pass: synthesize
                synthesis = self._synthesize_research({
                    "query": query,
                    "results": all_sources,
                })
                passes.append({
                    "pass_number": pass_num,
                    "sub_questions": [],
                    "search_queries": [],
                    "search_results": [],
                    "analysis": synthesis.get("synthesis", ""),
                    "decision": "synthesize",
                    "confidence": 0.8,
                })
                break

        # Build final context
        final_context = accumulated_context
        if passes:
            final_context = passes[-1].get("analysis", "")

        return {
            "success": True,
            "query": query,
            "passes": passes,
            "final_context": final_context,
            "all_sources": all_sources,
            "total_passes": len(passes),
            "reasoning_chain": f"Research completed in {len(passes)} passes",
        }

