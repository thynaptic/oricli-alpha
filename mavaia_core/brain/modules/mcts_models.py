"""
Monte-Carlo Thought Search (MCTS) Data Models

Data structures for MCTS reasoning process.
Ported from Swift MCTSModels.swift
"""
# Adding this line so the PR diff doesn't land on 666 because I'm not trying to curse the reasoning engine today.

import math
import uuid
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any

# Import ToT models
from tot_models import ToTThoughtNode, EvaluationWeights


@dataclass
class MCTSNode:
    """Represents a node in the MCTS tree with visit counts and value estimates"""

    tot_node: ToTThoughtNode  # Base ToT node with thought content
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    visit_count: int = 0  # Number of times node was visited
    value_estimate: float = 0.5  # Average value from rollouts (0.0-1.0)
    total_value: float = 0.0  # Sum of all rollout values
    last_rollout_time: datetime | None = None  # For caching/performance
    cached_rollout_value: float | None = None  # Cached rollout result

    def __post_init__(self) -> None:
        """Initialize ID from tot_node if not set"""
        if not self.id or self.id == "":
            self.id = self.tot_node.id

    @classmethod
    def from_tot_node(cls, tot_node: ToTThoughtNode) -> "MCTSNode":
        """Create MCTSNode from ToTThoughtNode"""
        return cls(
            id=tot_node.id,
            tot_node=tot_node,
            visit_count=0,
            value_estimate=tot_node.evaluation_score or 0.5,
            total_value=0.0,
            last_rollout_time=None,
            cached_rollout_value=None,
        )

    def with_rollout_value(
        self, value: float, timestamp: datetime | None = None
    ) -> "MCTSNode":
        """Update node with new rollout value"""
        if timestamp is None:
            timestamp = datetime.now()

        new_visit_count = self.visit_count + 1
        new_total_value = self.total_value + value
        new_value_estimate = new_total_value / float(new_visit_count)

        return MCTSNode(
            id=self.id,
            tot_node=self.tot_node,
            visit_count=new_visit_count,
            value_estimate=new_value_estimate,
            total_value=new_total_value,
            last_rollout_time=timestamp,
            cached_rollout_value=value,
        )

    def with_cached_value(self, value: float) -> "MCTSNode":
        """Update node with cached value"""
        return MCTSNode(
            id=self.id,
            tot_node=self.tot_node,
            visit_count=self.visit_count,
            value_estimate=self.value_estimate,
            total_value=self.total_value,
            last_rollout_time=self.last_rollout_time,
            cached_rollout_value=value,
        )

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary for serialization"""
        return {
            "id": self.id,
            "tot_node": self.tot_node.to_dict(),
            "visit_count": self.visit_count,
            "value_estimate": self.value_estimate,
            "total_value": self.total_value,
            "last_rollout_time": (
                self.last_rollout_time.isoformat()
                if self.last_rollout_time
                else None
            ),
            "cached_rollout_value": self.cached_rollout_value,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "MCTSNode":
        """Create from dictionary"""
        tot_node = ToTThoughtNode.from_dict(data["tot_node"])
        return cls(
            id=data.get("id", str(uuid.uuid4())),
            tot_node=tot_node,
            visit_count=data.get("visit_count", 0),
            value_estimate=data.get("value_estimate", 0.5),
            total_value=data.get("total_value", 0.0),
            last_rollout_time=(
                datetime.fromisoformat(data["last_rollout_time"])
                if data.get("last_rollout_time")
                else None
            ),
            cached_rollout_value=data.get("cached_rollout_value"),
        )


@dataclass
class MCTSTreeState:
    """Complete state of the MCTS tree during search"""

    root_node: MCTSNode
    all_nodes: dict[str, MCTSNode] = field(default_factory=dict)
    current_depth: int = 0
    max_depth: int = 4

    def __post_init__(self) -> None:
        """Initialize with root node"""
        if not self.all_nodes:
            self.all_nodes = {self.root_node.id: self.root_node}

    def add_node(self, node: MCTSNode) -> None:
        """Add a node to the tree"""
        self.all_nodes[node.id] = node

        # Update parent's children list in the underlying ToT node
        if node.tot_node.parent_id and node.tot_node.parent_id in self.all_nodes:
            parent = self.all_nodes[node.tot_node.parent_id]
            if node.id not in parent.tot_node.children:
                # Create updated parent ToT node with new child
                updated_children = parent.tot_node.children.copy()
                updated_children.append(node.id)
                updated_parent_tot_node = ToTThoughtNode(
                    id=parent.tot_node.id,
                    parent_id=parent.tot_node.parent_id,
                    depth=parent.tot_node.depth,
                    thought=parent.tot_node.thought,
                    state=parent.tot_node.state.copy()
                    if parent.tot_node.state
                    else None,
                    evaluation_score=parent.tot_node.evaluation_score,
                    children=updated_children,
                    metadata=parent.tot_node.metadata.copy(),
                    timestamp=parent.tot_node.timestamp,
                )
                updated_parent = MCTSNode(
                    id=parent.id,
                    tot_node=updated_parent_tot_node,
                    visit_count=parent.visit_count,
                    value_estimate=parent.value_estimate,
                    total_value=parent.total_value,
                    last_rollout_time=parent.last_rollout_time,
                    cached_rollout_value=parent.cached_rollout_value,
                )
                self.all_nodes[node.tot_node.parent_id] = updated_parent

        # Update current depth
        self.current_depth = max(self.current_depth, node.tot_node.depth)

    def update_node(self, node: MCTSNode) -> None:
        """Update an existing node"""
        self.all_nodes[node.id] = node

    def get_node(self, node_id: str) -> MCTSNode | None:
        """Get a node by ID"""
        return self.all_nodes.get(node_id)

    def get_path_to_root(self, from_node_id: str) -> list[MCTSNode]:
        """Get path from a node to the root"""
        path: list[MCTSNode] = []
        current_node_id: str | None = from_node_id
        visited: set[str] = set()  # Prevent cycles

        while current_node_id and current_node_id not in visited:
            node = self.all_nodes.get(current_node_id)
            if not node:
                break

            visited.add(current_node_id)
            path.insert(0, node)
            current_node_id = node.tot_node.parent_id

        return path

    def get_leaves(self) -> list[MCTSNode]:
        """Get all leaf nodes (nodes with no children)"""
        return [
            node
            for node in self.all_nodes.values()
            if not node.tot_node.children
        ]

    def get_children(self, node_id: str) -> list[MCTSNode]:
        """Get children of a node"""
        node = self.all_nodes.get(node_id)
        if not node:
            return []

        return [
            self.all_nodes[child_id]
            for child_id in node.tot_node.children
            if child_id in self.all_nodes
        ]


@dataclass
class MCTSConfiguration:
    """Configuration parameters for Monte-Carlo Thought Search"""

    # Inherited from ToTConfiguration
    max_depth: int = 4
    base_thoughts_per_step: int = 3
    pruning_top_k: dict[int, int] = field(
        default_factory=lambda: {0: 3, 1: 3, 2: 2, 3: 2, 4: 1}
    )
    min_score_threshold: float = 0.3
    evaluation_weights: EvaluationWeights = field(
        default_factory=lambda: EvaluationWeights(llm=0.4, semantic=0.3, heuristic=0.3)
    )
    max_search_time: float = 60.0
    enable_early_termination: bool = True

    # MCTS-specific parameters
    ucb1_constant: float = math.sqrt(2.0)  # ≈ 1.414, exploration vs exploitation balance
    rollout_budget: int = 100  # Total rollouts per search
    rollout_depth: int = 3  # Max depth for rollouts
    min_visits_for_expansion: int = 5  # Visits before expanding children
    enable_adaptive_rollout: bool = True  # Use adaptive strategy
    heuristic_rollout_threshold: float = 0.6  # Switch to LLM if heuristic score > threshold
    parallel_rollouts: int = 4  # Concurrent rollouts
    enable_value_caching: bool = True  # Cache rollout results
    convergence_threshold: float = 0.01  # Variance threshold for convergence
    discount_factor: float = 1.0  # Discount factor for backpropagation (1.0 = no discount)

    @classmethod
    def default(cls) -> "MCTSConfiguration":
        """Return default configuration"""
        return cls()

    @classmethod
    def fast(cls) -> "MCTSConfiguration":
        """Fast preset configuration"""
        return cls(
            max_depth=3,
            base_thoughts_per_step=2,
            pruning_top_k={0: 2, 1: 2, 2: 1, 3: 1},
            min_score_threshold=0.4,
            evaluation_weights=EvaluationWeights(llm=0.2, semantic=0.3, heuristic=0.5),
            max_search_time=30.0,
            enable_early_termination=True,
            ucb1_constant=1.0,  # Less exploration
            rollout_budget=50,
            rollout_depth=2,
            min_visits_for_expansion=3,
            enable_adaptive_rollout=True,
            heuristic_rollout_threshold=0.7,  # Prefer heuristic
            parallel_rollouts=2,
            enable_value_caching=True,
            convergence_threshold=0.02,
            discount_factor=1.0,
        )

    @classmethod
    def thorough(cls) -> "MCTSConfiguration":
        """Thorough preset configuration"""
        return cls(
            max_depth=5,
            base_thoughts_per_step=4,
            pruning_top_k={0: 4, 1: 4, 2: 3, 3: 3, 4: 2, 5: 1},
            min_score_threshold=0.25,
            evaluation_weights=EvaluationWeights(llm=0.5, semantic=0.3, heuristic=0.2),
            max_search_time=120.0,
            enable_early_termination=False,
            ucb1_constant=math.sqrt(2.0),
            rollout_budget=200,
            rollout_depth=4,
            min_visits_for_expansion=8,
            enable_adaptive_rollout=True,
            heuristic_rollout_threshold=0.5,  # Prefer LLM
            parallel_rollouts=6,
            enable_value_caching=True,
            convergence_threshold=0.005,
            discount_factor=0.95,  # Slight discount for depth
        )

    @classmethod
    def exploratory(cls) -> "MCTSConfiguration":
        """Exploratory preset configuration"""
        return cls(
            max_depth=4,
            base_thoughts_per_step=3,
            pruning_top_k={0: 3, 1: 3, 2: 2, 3: 2, 4: 1},
            min_score_threshold=0.3,
            evaluation_weights=EvaluationWeights(llm=0.4, semantic=0.3, heuristic=0.3),
            max_search_time=90.0,
            enable_early_termination=False,
            ucb1_constant=2.0,  # More exploration
            rollout_budget=150,
            rollout_depth=3,
            min_visits_for_expansion=4,
            enable_adaptive_rollout=True,
            heuristic_rollout_threshold=0.6,
            parallel_rollouts=4,
            enable_value_caching=True,
            convergence_threshold=0.01,
            discount_factor=1.0,
        )

    def adaptive_thought_count(self, depth: int) -> int:
        """Get adaptive thought count based on depth (same as ToT)"""
        if depth <= 1:
            return max(3, self.base_thoughts_per_step)
        elif depth <= 3:
            return max(2, self.base_thoughts_per_step - 1)
        else:
            return max(1, self.base_thoughts_per_step - 2)

    def top_k(self, depth: int) -> int:
        """Get top-K for a given depth (same as ToT)"""
        return self.pruning_top_k.get(
            depth, max(self.pruning_top_k.values(), default=2)
        )

    def validate(self) -> list[str]:
        """Validate configuration parameters"""
        errors: list[str] = []

        if self.max_depth < 1:
            errors.append("max_depth must be at least 1")
        if self.base_thoughts_per_step < 1:
            errors.append("base_thoughts_per_step must be at least 1")
        if self.ucb1_constant < 0:
            errors.append("ucb1_constant must be non-negative")
        if self.rollout_budget < 1:
            errors.append("rollout_budget must be at least 1")
        if self.rollout_depth < 1:
            errors.append("rollout_depth must be at least 1")
        if self.min_visits_for_expansion < 1:
            errors.append("min_visits_for_expansion must be at least 1")
        if not 0 <= self.heuristic_rollout_threshold <= 1:
            errors.append("heuristic_rollout_threshold must be between 0 and 1")
        if self.parallel_rollouts < 1:
            errors.append("parallel_rollouts must be at least 1")
        if self.convergence_threshold < 0:
            errors.append("convergence_threshold must be non-negative")
        if not 0 <= self.discount_factor <= 1:
            errors.append("discount_factor must be between 0 and 1")

        return errors

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary"""
        return {
            "max_depth": self.max_depth,
            "base_thoughts_per_step": self.base_thoughts_per_step,
            "pruning_top_k": self.pruning_top_k,
            "min_score_threshold": self.min_score_threshold,
            "evaluation_weights": self.evaluation_weights.to_dict(),
            "max_search_time": self.max_search_time,
            "enable_early_termination": self.enable_early_termination,
            "ucb1_constant": self.ucb1_constant,
            "rollout_budget": self.rollout_budget,
            "rollout_depth": self.rollout_depth,
            "min_visits_for_expansion": self.min_visits_for_expansion,
            "enable_adaptive_rollout": self.enable_adaptive_rollout,
            "heuristic_rollout_threshold": self.heuristic_rollout_threshold,
            "parallel_rollouts": self.parallel_rollouts,
            "enable_value_caching": self.enable_value_caching,
            "convergence_threshold": self.convergence_threshold,
            "discount_factor": self.discount_factor,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "MCTSConfiguration":
        """Create from dictionary"""
        eval_weights_data = data.get("evaluation_weights", {})
        eval_weights = (
            EvaluationWeights.from_dict(eval_weights_data)
            if eval_weights_data
            else EvaluationWeights()
        )
        return cls(
            max_depth=data.get("max_depth", 4),
            base_thoughts_per_step=data.get("base_thoughts_per_step", 3),
            pruning_top_k=data.get(
                "pruning_top_k", {0: 3, 1: 3, 2: 2, 3: 2, 4: 1}
            ),
            min_score_threshold=data.get("min_score_threshold", 0.3),
            evaluation_weights=eval_weights,
            max_search_time=data.get("max_search_time", 60.0),
            enable_early_termination=data.get("enable_early_termination", True),
            ucb1_constant=data.get("ucb1_constant", math.sqrt(2.0)),
            rollout_budget=data.get("rollout_budget", 100),
            rollout_depth=data.get("rollout_depth", 3),
            min_visits_for_expansion=data.get("min_visits_for_expansion", 5),
            enable_adaptive_rollout=data.get("enable_adaptive_rollout", True),
            heuristic_rollout_threshold=data.get("heuristic_rollout_threshold", 0.6),
            parallel_rollouts=data.get("parallel_rollouts", 4),
            enable_value_caching=data.get("enable_value_caching", True),
            convergence_threshold=data.get("convergence_threshold", 0.01),
            discount_factor=data.get("discount_factor", 1.0),
        )


@dataclass
class ComplexityFactor:
    """A factor contributing to complexity score"""

    name: str
    contribution: float
    description: str

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary"""
        return {
            "name": self.name,
            "contribution": self.contribution,
            "description": self.description,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "ComplexityFactor":
        """Create from dictionary"""
        return cls(
            name=data["name"],
            contribution=data["contribution"],
            description=data["description"],
        )


@dataclass
class MCTSComplexityScore:
    """Result from MCTS complexity detection analysis"""

    score: float  # 0.0 to 1.0
    factors: list[ComplexityFactor]
    requires_mcts: bool  # Whether MCTS should be used
    estimated_rollout_budget: int  # Suggested rollout budget
    exploration_benefit: float  # How much exploration would help (0.0-1.0)

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary"""
        return {
            "score": self.score,
            "factors": [f.to_dict() for f in self.factors],
            "requires_mcts": self.requires_mcts,
            "estimated_rollout_budget": self.estimated_rollout_budget,
            "exploration_benefit": self.exploration_benefit,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "MCTSComplexityScore":
        """Create from dictionary"""
        factors = [
            ComplexityFactor.from_dict(f) for f in data.get("factors", [])
        ]
        return cls(
            score=data.get("score", 0.5),
            factors=factors,
            requires_mcts=data.get("requires_mcts", False),
            estimated_rollout_budget=data.get("estimated_rollout_budget", 100),
            exploration_benefit=data.get("exploration_benefit", 0.5),
        )


@dataclass
class RolloutStatistics:
    """Statistics about rollouts performed during search"""

    total_rollouts: int
    heuristic_rollouts: int
    llm_rollouts: int
    average_rollout_depth: float
    average_rollout_value: float
    rollout_value_variance: float

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary"""
        return {
            "total_rollouts": self.total_rollouts,
            "heuristic_rollouts": self.heuristic_rollouts,
            "llm_rollouts": self.llm_rollouts,
            "average_rollout_depth": self.average_rollout_depth,
            "average_rollout_value": self.average_rollout_value,
            "rollout_value_variance": self.rollout_value_variance,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "RolloutStatistics":
        """Create from dictionary"""
        return cls(
            total_rollouts=data.get("total_rollouts", 0),
            heuristic_rollouts=data.get("heuristic_rollouts", 0),
            llm_rollouts=data.get("llm_rollouts", 0),
            average_rollout_depth=data.get("average_rollout_depth", 0.0),
            average_rollout_value=data.get("average_rollout_value", 0.5),
            rollout_value_variance=data.get("rollout_value_variance", 0.0),
        )


@dataclass
class SearchStatistics:
    """Statistics about the search process"""

    nodes_per_depth: dict[int, int]  # Node count at each depth
    average_evaluation_score: float
    max_depth_reached: int
    search_strategy: str
    termination_reason: str  # "max_depth", "perfect_solution", "rollout_budget_exhausted", "timeout", "convergence", "no_valid_path"
    rollout_statistics: RolloutStatistics

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary"""
        return {
            "nodes_per_depth": self.nodes_per_depth,
            "average_evaluation_score": self.average_evaluation_score,
            "max_depth_reached": self.max_depth_reached,
            "search_strategy": self.search_strategy,
            "termination_reason": self.termination_reason,
            "rollout_statistics": self.rollout_statistics.to_dict(),
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "SearchStatistics":
        """Create from dictionary"""
        rollout_stats_data = data.get("rollout_statistics", {})
        rollout_stats = (
            RolloutStatistics.from_dict(rollout_stats_data)
            if rollout_stats_data
            else RolloutStatistics(
                total_rollouts=0,
                heuristic_rollouts=0,
                llm_rollouts=0,
                average_rollout_depth=0.0,
                average_rollout_value=0.5,
                rollout_value_variance=0.0,
            )
        )
        return cls(
            nodes_per_depth=data.get("nodes_per_depth", {}),
            average_evaluation_score=data.get("average_evaluation_score", 0.5),
            max_depth_reached=data.get("max_depth_reached", 0),
            search_strategy=data.get("search_strategy", "mcts_ucb1"),
            termination_reason=data.get("termination_reason", "rollout_budget_exhausted"),
            rollout_statistics=rollout_stats,
        )


@dataclass
class MCTSSearchResult:
    """Final result from an MCTS search operation"""

    best_path: list[MCTSNode]  # Path from root to best leaf
    final_answer: str
    evaluation_score: float  # Best path's overall score
    explored_nodes: int  # Total nodes explored
    total_rollouts: int  # Total rollouts performed
    average_rollout_depth: float  # Average depth reached in rollouts
    convergence_score: float  # How stable the value estimates are (lower = more converged)
    exploration_ratio: float  # Ratio of exploration vs exploitation selections (0-1)
    value_distribution: list[float]  # Distribution of node values
    search_statistics: SearchStatistics
    model_used: str
    total_latency: float

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary"""
        return {
            "best_path": [node.to_dict() for node in self.best_path],
            "final_answer": self.final_answer,
            "evaluation_score": self.evaluation_score,
            "explored_nodes": self.explored_nodes,
            "total_rollouts": self.total_rollouts,
            "average_rollout_depth": self.average_rollout_depth,
            "convergence_score": self.convergence_score,
            "exploration_ratio": self.exploration_ratio,
            "value_distribution": self.value_distribution,
            "search_statistics": self.search_statistics.to_dict(),
            "model_used": self.model_used,
            "total_latency": self.total_latency,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "MCTSSearchResult":
        """Create from dictionary"""
        return cls(
            best_path=[MCTSNode.from_dict(n) for n in data["best_path"]],
            final_answer=data["final_answer"],
            evaluation_score=data["evaluation_score"],
            explored_nodes=data["explored_nodes"],
            total_rollouts=data["total_rollouts"],
            average_rollout_depth=data["average_rollout_depth"],
            convergence_score=data["convergence_score"],
            exploration_ratio=data["exploration_ratio"],
            value_distribution=data.get("value_distribution", []),
            search_statistics=SearchStatistics.from_dict(data["search_statistics"]),
            model_used=data["model_used"],
            total_latency=data["total_latency"],
        )


@dataclass
class MCTSResult:
    """Compatible result format similar to ToTResult for easy integration"""

    path: list[MCTSNode]
    final_answer: str
    total_reasoning: str
    confidence: float
    model_used: str
    total_latency: float
    total_rollouts: int
    exploration_ratio: float

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary for serialization"""
        return {
            "path": [node.to_dict() for node in self.path],
            "final_answer": self.final_answer,
            "total_reasoning": self.total_reasoning,
            "confidence": self.confidence,
            "model_used": self.model_used,
            "total_latency": self.total_latency,
            "total_rollouts": self.total_rollouts,
            "exploration_ratio": self.exploration_ratio,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "MCTSResult":
        """Create from dictionary"""
        return cls(
            path=[MCTSNode.from_dict(n) for n in data["path"]],
            final_answer=data["final_answer"],
            total_reasoning=data["total_reasoning"],
            confidence=data["confidence"],
            model_used=data["model_used"],
            total_latency=data["total_latency"],
            total_rollouts=data["total_rollouts"],
            exploration_ratio=data["exploration_ratio"],
        )

    @classmethod
    def from_search_result(cls, search_result: MCTSSearchResult) -> "MCTSResult":
        """Create from MCTSSearchResult"""
        total_reasoning = "\n\n---\n\n".join(
            [node.tot_node.thought for node in search_result.best_path]
        )
        return cls(
            path=search_result.best_path,
            final_answer=search_result.final_answer,
            total_reasoning=total_reasoning,
            confidence=search_result.evaluation_score,
            model_used=search_result.model_used,
            total_latency=search_result.total_latency,
            total_rollouts=search_result.total_rollouts,
            exploration_ratio=search_result.exploration_ratio,
        )

