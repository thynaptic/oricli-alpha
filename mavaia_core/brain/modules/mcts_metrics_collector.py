"""
Monte-Carlo Thought Search Metrics Collector

Collects MCTS specific metrics.
Tracks rollout performance, UCB1 patterns, convergence, and search efficiency.
Ported from Swift MCTSMetricsCollector.swift
"""

from typing import Any
from datetime import datetime
from collections import deque
import logging

from mavaia_core.brain.base_module import BaseBrainModule, ModuleMetadata
from mavaia_core.exceptions import InvalidParameterError, ModuleOperationError

logger = logging.getLogger(__name__)

# Lazy import to avoid timeout during module discovery
MCTSSearchResult = None

def _lazy_import_mcts_models():
    """Lazy import MCTS models only when needed"""
    global MCTSSearchResult
    if MCTSSearchResult is None:
        try:
            from mavaia_core.brain.modules.mcts_models import MCTSSearchResult as MSR
            MCTSSearchResult = MSR
        except ImportError:
            pass


class MCTSMetricsCollector(BaseBrainModule):
    """
    Collects Monte-Carlo Thought Search specific metrics.
    Tracks rollout performance, UCB1 patterns, convergence, and search efficiency.
    """

    def __init__(self) -> None:
        """Initialize the module"""
        super().__init__()
        self._metrics: list[dict[str, Any]] = []
        self._max_metrics = 1000

    @property
    def metadata(self) -> ModuleMetadata:
        return ModuleMetadata(
            name="mcts_metrics_collector",
            version="1.0.0",
            description="Collects MCTS specific metrics",
            operations=[
                "record_mcts_search",
                "get_all_metrics",
                "get_metrics_for_session",
                "get_recent_metrics",
                "get_aggregate_statistics",
                "get_performance_trends",
                "clear_metrics",
                "clear_old_metrics",
            ],
            dependencies=[],
            enabled=True,
            model_required=False,
        )

    def initialize(self) -> bool:
        """Initialize the module"""
        return True

    def execute(self, operation: str, params: dict[str, Any]) -> dict[str, Any]:
        """
        Execute metrics collection operations.

        Supported operations:
        - record_mcts_search: Record MCTS search metrics
        - get_all_metrics: Get all metrics
        - get_metrics_for_session: Get metrics for a specific session
        - get_recent_metrics: Get recent metrics
        - get_aggregate_statistics: Get aggregate statistics
        - get_performance_trends: Get performance trends
        - clear_metrics: Clear all metrics
        - clear_old_metrics: Clear old metrics
        """
        _lazy_import_mcts_models()
        if operation == "record_mcts_search":
            return self._record_mcts_search(params)
        elif operation == "get_all_metrics":
            return self._get_all_metrics(params)
        elif operation == "get_metrics_for_session":
            return self._get_metrics_for_session(params)
        elif operation == "get_recent_metrics":
            return self._get_recent_metrics(params)
        elif operation == "get_aggregate_statistics":
            return self._get_aggregate_statistics(params)
        elif operation == "get_performance_trends":
            return self._get_performance_trends(params)
        elif operation == "clear_metrics":
            return self._clear_metrics(params)
        elif operation == "clear_old_metrics":
            return self._clear_old_metrics(params)
        else:
            raise InvalidParameterError(
                parameter="operation",
                value=operation,
                reason="Unknown operation for mcts_metrics_collector",
            )

    def _record_mcts_search(self, params: dict[str, Any]) -> dict[str, Any]:
        """
        Record MCTS search metrics from a search result.

        Args:
            params: Dictionary with:
                - session_id (str, optional): Session identifier
                - query (str): The query
                - search_result (dict): MCTSSearchResult as dict
                - rollout_latencies (list[float], optional): Rollout latencies
                - exploration_selections (int): Exploration selections count
                - exploitation_selections (int): Exploitation selections count

        Returns:
            Dictionary with recorded status
        """
        import uuid

        session_id = params.get("session_id", str(uuid.uuid4()))
        query = params.get("query", "")
        search_result_dict = params.get("search_result", {})

        if not search_result_dict:
            raise InvalidParameterError(
                parameter="search_result",
                value=str(type(search_result_dict).__name__),
                reason="search_result parameter is required",
            )

        if MCTSSearchResult is None:
            raise ModuleOperationError(
                module_name="mcts_metrics_collector",
                operation="record_mcts_search",
                reason="MCTSSearchResult type is not available (import failed)",
            )

        search_result = MCTSSearchResult.from_dict(search_result_dict)
        rollout_latencies = params.get("rollout_latencies", [])
        exploration_selections = params.get("exploration_selections", 0)
        exploitation_selections = params.get("exploitation_selections", 0)

        metrics = {
            "session_id": session_id,
            "timestamp": datetime.now().isoformat(),
            "query": query,
            "total_rollouts": search_result.total_rollouts,
            "heuristic_rollouts": search_result.search_statistics.rollout_statistics.heuristic_rollouts,
            "llm_rollouts": search_result.search_statistics.rollout_statistics.llm_rollouts,
            "average_rollout_depth": search_result.average_rollout_depth,
            "average_rollout_value": search_result.search_statistics.rollout_statistics.average_rollout_value,
            "rollout_value_variance": search_result.search_statistics.rollout_statistics.rollout_value_variance,
            "rollout_latencies": rollout_latencies,
            "average_rollout_latency": (
                sum(rollout_latencies) / len(rollout_latencies)
                if rollout_latencies
                else 0.0
            ),
            "exploration_selections": exploration_selections,
            "exploitation_selections": exploitation_selections,
            "exploration_ratio": search_result.exploration_ratio,
            "convergence_score": search_result.convergence_score,
            "nodes_explored": search_result.explored_nodes,
            "nodes_per_depth": search_result.search_statistics.nodes_per_depth,
            "value_distribution": search_result.value_distribution,
            "ucb1_constant": 0.0,  # Would need to be passed from configuration
            "termination_reason": search_result.search_statistics.termination_reason,
            "total_latency": search_result.total_latency,
            "final_value_estimate": search_result.evaluation_score,
            "path_length": len(search_result.best_path),
            "model_used": search_result.model_used,
        }

        self._metrics.append(metrics)

        # Trim to max size
        if len(self._metrics) > self._max_metrics:
            self._metrics = self._metrics[-self._max_metrics :]

        return {"recorded": True, "session_id": session_id}

    def _get_all_metrics(self, params: dict[str, Any]) -> dict[str, Any]:
        """Get all metrics"""
        return {"metrics": self._metrics}

    def _get_metrics_for_session(self, params: dict[str, Any]) -> dict[str, Any]:
        """Get metrics for a specific session"""
        session_id = params.get("session_id")
        if not session_id:
            raise InvalidParameterError(
                parameter="session_id",
                value=str(session_id),
                reason="session_id parameter is required",
            )

        metric = next(
            (m for m in self._metrics if m["session_id"] == session_id), None
        )
        return {"metric": metric}

    def _get_recent_metrics(self, params: dict[str, Any]) -> dict[str, Any]:
        """Get recent metrics (last N)"""
        count = params.get("count", 100)
        recent = self._metrics[-count:] if self._metrics else []
        return {"metrics": recent}

    def _get_aggregate_statistics(self, params: dict[str, Any]) -> dict[str, Any]:
        """Calculate aggregate statistics from all metrics"""
        if not self._metrics:
            return {}

        total_searches = len(self._metrics)
        total_rollouts = sum(m["total_rollouts"] for m in self._metrics)
        average_rollouts = total_rollouts / total_searches
        average_exploration_ratio = (
            sum(m["exploration_ratio"] for m in self._metrics) / total_searches
        )
        average_convergence_score = (
            sum(m["convergence_score"] for m in self._metrics) / total_searches
        )
        average_rollout_value = (
            sum(m["average_rollout_value"] for m in self._metrics) / total_searches
        )
        average_latency = sum(m["total_latency"] for m in self._metrics) / total_searches
        average_path_length = (
            sum(m["path_length"] for m in self._metrics) / total_searches
        )

        # Termination reason distribution
        termination_reasons: dict[str, int] = {}
        for metric in self._metrics:
            reason = metric["termination_reason"]
            termination_reasons[reason] = termination_reasons.get(reason, 0) + 1

        # Rollout type distribution
        total_heuristic_rollouts = sum(m["heuristic_rollouts"] for m in self._metrics)
        total_llm_rollouts = sum(m["llm_rollouts"] for m in self._metrics)
        heuristic_ratio = (
            total_heuristic_rollouts / total_rollouts if total_rollouts > 0 else 0.0
        )
        llm_ratio = total_llm_rollouts / total_rollouts if total_rollouts > 0 else 0.0

        return {
            "total_searches": total_searches,
            "total_rollouts": total_rollouts,
            "average_rollouts_per_search": average_rollouts,
            "average_exploration_ratio": average_exploration_ratio,
            "average_convergence_score": average_convergence_score,
            "average_rollout_value": average_rollout_value,
            "average_latency_seconds": average_latency,
            "average_path_length": average_path_length,
            "heuristic_rollout_ratio": heuristic_ratio,
            "llm_rollout_ratio": llm_ratio,
            "termination_reason_distribution": termination_reasons,
        }

    def _get_performance_trends(
        self, params: dict[str, Any]
    ) -> dict[str, list[float]]:
        """Get performance trends over time"""
        window_size = params.get("window_size", 10)

        if len(self._metrics) < window_size:
            return {}

        recent_metrics = self._metrics[-window_size:]

        return {
            "rollouts": [float(m["total_rollouts"]) for m in recent_metrics],
            "exploration_ratio": [float(m["exploration_ratio"]) for m in recent_metrics],
            "convergence_score": [
                float(m["convergence_score"]) for m in recent_metrics
            ],
            "rollout_value": [float(m["average_rollout_value"]) for m in recent_metrics],
            "latency": [float(m["total_latency"]) for m in recent_metrics],
        }

    def _clear_metrics(self, params: dict[str, Any]) -> dict[str, Any]:
        """Clear all metrics"""
        count = len(self._metrics)
        self._metrics.clear()
        return {"cleared_count": count}

    def _clear_old_metrics(self, params: dict[str, Any]) -> dict[str, Any]:
        """Clear metrics older than specified days"""
        from datetime import timedelta

        older_than_days = params.get("older_than_days", 7)
        cutoff_date = datetime.now() - timedelta(days=older_than_days)

        initial_count = len(self._metrics)
        self._metrics = [
            m
            for m in self._metrics
            if datetime.fromisoformat(m["timestamp"]) > cutoff_date
        ]
        removed_count = initial_count - len(self._metrics)

        return {"removed_count": removed_count}

