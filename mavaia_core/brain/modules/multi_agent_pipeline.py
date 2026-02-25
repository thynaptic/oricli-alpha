"""
Multi-Agent Pipeline Orchestrator - Perplexity Multi-Agent Pipeline

Coordinates all agents in the pipeline: Query Agent, Retriever Agent,
Reranker Agent, Synthesis Agent, and Verifier Agent.
Part of the Perplexity Multi-Agent Pipeline implementation.
"""

from __future__ import annotations

import logging
from typing import Any, Dict, Optional
import time

from mavaia_core.brain.base_module import BaseBrainModule, ModuleMetadata
from mavaia_core.exceptions import InvalidParameterError

logger = logging.getLogger(__name__)


class MultiAgentPipeline(BaseBrainModule):
    """
    Multi-Agent Pipeline Orchestrator.
    
    Coordinates the execution of all agents in the pipeline:
    1. Query Agent: Normalize and analyze query
    2. Retriever Agent: Fetch candidate documents
    3. Reranker Agent: Score and rank documents
    4. Synthesis Agent: Compile coherent answer
    5. Verifier Agent: Fact-check and validate
    """

    def __init__(self):
        """Initialize the Multi-Agent Pipeline"""
        super().__init__()
        self._query_agent = None
        self._retriever_agent = None
        self._reranker_agent = None
        self._synthesis_agent = None
        self._verifier_agent = None

    @property
    def metadata(self) -> ModuleMetadata:
        return ModuleMetadata(
            name="multi_agent_pipeline",
            version="1.0.0",
            description=(
                "Multi-Agent Pipeline Orchestrator: Coordinates Query, Retriever, "
                "Reranker, Synthesis, and Verifier agents for information retrieval "
                "and processing"
            ),
            operations=[
                "process_query",
                "execute_pipeline",
                "handle_feedback",
                "optimize_pipeline",
            ],
            dependencies=[],
            enabled=True,
            model_required=False,
        )

    def initialize(self) -> bool:
        """Initialize all agent modules"""
        try:
            from mavaia_core.brain.registry import ModuleRegistry

            # Load all agent modules
            try:
                self._query_agent = ModuleRegistry.get_module("query_agent")
            except Exception as e:
                logger.debug(
                    "Failed to load query_agent",
                    exc_info=True,
                    extra={"module_name": "multi_agent_pipeline", "dependency": "query_agent", "error_type": type(e).__name__},
                )

            try:
                self._retriever_agent = ModuleRegistry.get_module("retriever_agent")
            except Exception as e:
                logger.debug(
                    "Failed to load retriever_agent",
                    exc_info=True,
                    extra={"module_name": "multi_agent_pipeline", "dependency": "retriever_agent", "error_type": type(e).__name__},
                )

            try:
                self._reranker_agent = ModuleRegistry.get_module("reranker_agent")
            except Exception as e:
                logger.debug(
                    "Failed to load reranker_agent",
                    exc_info=True,
                    extra={"module_name": "multi_agent_pipeline", "dependency": "reranker_agent", "error_type": type(e).__name__},
                )

            try:
                self._synthesis_agent = ModuleRegistry.get_module("synthesis_agent")
            except Exception as e:
                logger.debug(
                    "Failed to load synthesis_agent",
                    exc_info=True,
                    extra={"module_name": "multi_agent_pipeline", "dependency": "synthesis_agent", "error_type": type(e).__name__},
                )

            try:
                self._verifier_agent = ModuleRegistry.get_module("verifier_agent")
            except Exception as e:
                logger.debug(
                    "Failed to load verifier_agent",
                    exc_info=True,
                    extra={"module_name": "multi_agent_pipeline", "dependency": "verifier_agent", "error_type": type(e).__name__},
                )

            return True
        except Exception as e:
            logger.debug(
                "ModuleRegistry not available; multi_agent_pipeline will run with partial availability",
                exc_info=True,
                extra={"module_name": "multi_agent_pipeline", "error_type": type(e).__name__},
            )
            return True  # Can work with partial agent availability

    def execute(self, operation: str, params: Dict[str, Any]) -> Dict[str, Any]:
        """
        Execute Multi-Agent Pipeline operations.

        Supported operations:
        - process_query: Main entry point for query processing
        - execute_pipeline: Execute full pipeline workflow
        - handle_feedback: Process verification feedback and iterate
        - optimize_pipeline: Dynamic pipeline optimization
        """
        if operation == "process_query":
            query = params.get("query", "")
            config = params.get("config", {})
            return self.process_query(query, config)
        elif operation == "execute_pipeline":
            query = params.get("query", "")
            config = params.get("config", {})
            return self.execute_pipeline(query, config)
        elif operation == "handle_feedback":
            pipeline_result = params.get("pipeline_result", {})
            feedback = params.get("feedback", {})
            return self.handle_feedback(pipeline_result, feedback)
        elif operation == "optimize_pipeline":
            config = params.get("config", {})
            return self.optimize_pipeline(config)
        else:
            raise InvalidParameterError(
                parameter="operation",
                value=operation,
                reason="Unknown operation for multi_agent_pipeline",
            )

    def process_query(
        self, query: str, config: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Main entry point for query processing through the pipeline.

        Args:
            query: User query string
            config: Optional pipeline configuration

        Returns:
            Dictionary with complete pipeline results
        """
        if not query:
            return {
                "success": False,
                "error": "Empty query",
            }

        if config is None:
            config = {}

        # Execute full pipeline
        return self.execute_pipeline(query, config)

    def execute_pipeline(
        self, query: str, config: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Execute full pipeline workflow.

        Args:
            query: User query string
            config: Optional pipeline configuration

        Returns:
            Dictionary with complete pipeline results
        """
        if not query:
            return {
                "success": False,
                "error": "Empty query",
            }

        if config is None:
            config = {}

        start_time = time.time()
        pipeline_stages = {}
        errors = []

        # Stage 1: Query Agent - Normalize and analyze query
        query_result = {}
        if self._query_agent:
            try:
                query_result = self._query_agent.execute(
                    "process_query",
                    {"query": query}
                )
                pipeline_stages["query_processing"] = {
                    "success": True,
                    "result": query_result,
                }
            except Exception as e:
                logger.debug(
                    "Query agent stage failed; continuing with original query",
                    exc_info=True,
                    extra={"module_name": "multi_agent_pipeline", "stage": "query_processing", "dependency": "query_agent", "error_type": type(e).__name__},
                )
                error_msg = "Query Agent error"
                errors.append(error_msg)
                pipeline_stages["query_processing"] = {
                    "success": False,
                    "error": error_msg,
                }
                # Continue with original query
                query_result = {"normalized": {"normalized": query}}
        else:
            # Fallback: use original query
            query_result = {"normalized": {"normalized": query}}
            pipeline_stages["query_processing"] = {
                "success": False,
                "error": "Query Agent not available",
            }

        # Extract normalized query
        normalized_data = query_result.get("normalized", {})
        normalized_query = normalized_data.get("normalized", query)

        # Extract search queries
        search_queries_data = query_result.get("search_queries", {})
        search_queries = search_queries_data.get("queries", [])
        if not search_queries:
            search_queries = [{"query": normalized_query, "type": "original", "priority": 1}]

        # Stage 2: Retriever Agent - Fetch candidate documents
        retrieval_result = {}
        if self._retriever_agent:
            try:
                retrieval_limit = config.get("retrieval_limit", 20)
                retrieval_result = self._retriever_agent.execute(
                    "process_retrieval",
                    {
                        "query": normalized_query,
                        "limit": retrieval_limit,
                    }
                )
                pipeline_stages["retrieval"] = {
                    "success": True,
                    "result": retrieval_result,
                }
            except Exception as e:
                logger.debug(
                    "Retriever agent stage failed; continuing with empty documents",
                    exc_info=True,
                    extra={"module_name": "multi_agent_pipeline", "stage": "retrieval", "dependency": "retriever_agent", "error_type": type(e).__name__},
                )
                error_msg = "Retriever Agent error"
                errors.append(error_msg)
                pipeline_stages["retrieval"] = {
                    "success": False,
                    "error": error_msg,
                }
                retrieval_result = {"documents": [], "count": 0}
        else:
            pipeline_stages["retrieval"] = {
                "success": False,
                "error": "Retriever Agent not available",
            }
            retrieval_result = {"documents": [], "count": 0}

        documents = retrieval_result.get("documents", [])

        # Stage 3: Reranker Agent - Score and rank documents
        rerank_result = {}
        if self._reranker_agent and documents:
            try:
                top_k = config.get("top_k", 10)
                rerank_result = self._reranker_agent.execute(
                    "process_reranking",
                    {
                        "documents": documents,
                        "query": normalized_query,
                        "top_k": top_k,
                    }
                )
                pipeline_stages["reranking"] = {
                    "success": True,
                    "result": rerank_result,
                }
            except Exception as e:
                logger.debug(
                    "Reranker agent stage failed; continuing with unreranked documents",
                    exc_info=True,
                    extra={"module_name": "multi_agent_pipeline", "stage": "reranking", "dependency": "reranker_agent", "error_type": type(e).__name__},
                )
                error_msg = "Reranker Agent error"
                errors.append(error_msg)
                pipeline_stages["reranking"] = {
                    "success": False,
                    "error": error_msg,
                }
                # Use original documents
                rerank_result = {"documents": documents, "count": len(documents)}
        else:
            pipeline_stages["reranking"] = {
                "success": False,
                "error": "Reranker Agent not available or no documents",
            }
            rerank_result = {"documents": documents, "count": len(documents)}

        ranked_documents = rerank_result.get("documents", [])

        # Stage 4: Synthesis Agent - Compile coherent answer
        synthesis_result = {}
        if self._synthesis_agent and ranked_documents:
            try:
                synthesis_result = self._synthesis_agent.execute(
                    "synthesize",
                    {
                        "documents": ranked_documents,
                        "query": normalized_query,
                    }
                )
                pipeline_stages["synthesis"] = {
                    "success": True,
                    "result": synthesis_result,
                }
            except Exception as e:
                logger.debug(
                    "Synthesis agent stage failed; continuing with fallback answer",
                    exc_info=True,
                    extra={"module_name": "multi_agent_pipeline", "stage": "synthesis", "dependency": "synthesis_agent", "error_type": type(e).__name__},
                )
                error_msg = "Synthesis Agent error"
                errors.append(error_msg)
                pipeline_stages["synthesis"] = {
                    "success": False,
                    "error": error_msg,
                }
                # Fallback: simple answer
                synthesis_result = {
                    "answer": "Unable to synthesize answer from available documents.",
                    "confidence": 0.0,
                }
        else:
            pipeline_stages["synthesis"] = {
                "success": False,
                "error": "Synthesis Agent not available or no documents",
            }
            synthesis_result = {
                "answer": "No information available to answer the query.",
                "confidence": 0.0,
            }

        answer = synthesis_result.get("answer", "")
        information = synthesis_result.get("information", {})

        # Stage 5: Verifier Agent - Fact-check and validate
        verification_result = {}
        if self._verifier_agent and answer:
            try:
                verification_result = self._verifier_agent.execute(
                    "process_verification",
                    {
                        "answer": answer,
                        "documents": ranked_documents,
                        "information": information,
                    }
                )
                pipeline_stages["verification"] = {
                    "success": True,
                    "result": verification_result,
                }
            except Exception as e:
                logger.debug(
                    "Verifier agent stage failed; continuing with default confidence",
                    exc_info=True,
                    extra={"module_name": "multi_agent_pipeline", "stage": "verification", "dependency": "verifier_agent", "error_type": type(e).__name__},
                )
                error_msg = "Verifier Agent error"
                errors.append(error_msg)
                pipeline_stages["verification"] = {
                    "success": False,
                    "error": error_msg,
                }
                verification_result = {
                    "overall_confidence": 0.5,
                    "fact_verification": {},
                }
        else:
            pipeline_stages["verification"] = {
                "success": False,
                "error": "Verifier Agent not available or no answer",
            }
            verification_result = {
                "overall_confidence": 0.5,
                "fact_verification": {},
            }

        # Calculate overall confidence
        synthesis_confidence = synthesis_result.get("confidence", 0.0)
        verification_confidence = verification_result.get("overall_confidence", 0.5)
        overall_confidence = (synthesis_confidence * 0.6 + verification_confidence * 0.4)

        execution_time = time.time() - start_time

        return {
            "success": True,
            "query": query,
            "normalized_query": normalized_query,
            "answer": answer,
            "confidence": overall_confidence,
            "citations": information.get("citations", []),
            "metadata": {
                "execution_time": execution_time,
                "document_count": len(ranked_documents),
                "synthesis_confidence": synthesis_confidence,
                "verification_confidence": verification_confidence,
                "errors": errors,
                "stages_completed": len([s for s in pipeline_stages.values() if s.get("success")]),
                "total_stages": len(pipeline_stages),
            },
            "pipeline_stages": pipeline_stages,
            "verification": verification_result,
        }

    def handle_feedback(
        self, pipeline_result: Dict[str, Any], feedback: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Process verification feedback and iterate if needed.

        Args:
            pipeline_result: Previous pipeline execution result
            feedback: User or system feedback

        Returns:
            Dictionary with updated results or iteration plan
        """
        if not pipeline_result:
            return {
                "success": False,
                "error": "No pipeline result provided",
            }

        feedback_type = feedback.get("type", "general")
        feedback_content = feedback.get("content", "")

        # Check if iteration is needed
        needs_iteration = False
        iteration_reason = ""

        if feedback_type == "low_confidence":
            confidence = pipeline_result.get("confidence", 0.0)
            if confidence < 0.5:
                needs_iteration = True
                iteration_reason = "Low confidence score"
        elif feedback_type == "verification_failure":
            verification = pipeline_result.get("verification", {})
            fact_verification = verification.get("fact_verification", {})
            contradictions = fact_verification.get("contradictions", [])
            if contradictions:
                needs_iteration = True
                iteration_reason = "Contradictions found in verification"

        if needs_iteration:
            # Re-execute pipeline with adjusted parameters
            original_query = pipeline_result.get("query", "")
            config = {
                "retrieval_limit": 30,  # Retrieve more documents
                "top_k": 15,  # Consider more documents
            }

            return {
                "needs_iteration": True,
                "reason": iteration_reason,
                "iteration_config": config,
                "suggested_action": "Re-execute pipeline with adjusted parameters",
            }
        else:
            return {
                "needs_iteration": False,
                "reason": "No iteration needed",
                "feedback_processed": True,
            }

    def optimize_pipeline(self, config: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """
        Dynamic pipeline optimization.

        Args:
            config: Pipeline configuration to optimize

        Returns:
            Dictionary with optimization recommendations
        """
        if config is None:
            config = {}

        recommendations = []

        # Check agent availability
        agents_status = {
            "query_agent": self._query_agent is not None,
            "retriever_agent": self._retriever_agent is not None,
            "reranker_agent": self._reranker_agent is not None,
            "synthesis_agent": self._synthesis_agent is not None,
            "verifier_agent": self._verifier_agent is not None,
        }

        missing_agents = [name for name, available in agents_status.items() if not available]
        if missing_agents:
            recommendations.append({
                "type": "missing_agents",
                "agents": missing_agents,
                "impact": "high",
                "suggestion": f"Load missing agents: {', '.join(missing_agents)}",
            })

        # Check configuration parameters
        retrieval_limit = config.get("retrieval_limit", 20)
        if retrieval_limit < 10:
            recommendations.append({
                "type": "low_retrieval_limit",
                "current": retrieval_limit,
                "suggestion": "Increase retrieval_limit to at least 20 for better recall",
            })

        top_k = config.get("top_k", 10)
        if top_k < 5:
            recommendations.append({
                "type": "low_top_k",
                "current": top_k,
                "suggestion": "Increase top_k to at least 5 for better answer quality",
            })

        return {
            "optimized": len(recommendations) == 0,
            "recommendations": recommendations,
            "agents_status": agents_status,
            "config": config,
        }

    def validate_params(self, operation: str, params: Dict[str, Any]) -> bool:
        """Validate parameters for operations"""
        if operation == 'process_query' or operation == 'execute_pipeline':
            return "query" in params
        elif operation == "handle_feedback":
            return "pipeline_result" in params and "feedback" in params
        elif operation == "optimize_pipeline":
            return True  # Config is optional
        else:
            return True

