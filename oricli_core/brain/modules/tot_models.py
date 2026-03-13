from __future__ import annotations
"""
Tree-of-Thought Data Models

Data structures for Tree-of-Thought reasoning process.
Ported from Swift TreeOfThoughtModels.swift
"""

import uuid
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any


@dataclass
class ToTThoughtNode:
    """Represents a single thought node in the Tree-of-Thought structure"""

    thought: str  # The actual thought/reasoning text
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    parent_id: str | None = None
    depth: int = 0
    state: dict[str, Any] | None = None
    evaluation_score: float | None = None
    children: list[str] = field(default_factory=list)
    metadata: dict[str, str] = field(default_factory=dict)
    timestamp: datetime = field(default_factory=datetime.now)

    def with_evaluation_score(self, score: float | None) -> "ToTThoughtNode":
        """Create a copy with updated evaluation score"""
        return ToTThoughtNode(
            id=self.id,
            parent_id=self.parent_id,
            depth=self.depth,
            thought=self.thought,
            state=self.state.copy() if self.state else None,
            evaluation_score=score,
            children=self.children.copy(),
            metadata=self.metadata.copy(),
            timestamp=self.timestamp,
        )

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary for serialization"""
        return {
            "id": self.id,
            "parent_id": self.parent_id,
            "depth": self.depth,
            "thought": self.thought,
            "state": self.state,
            "evaluation_score": self.evaluation_score,
            "children": self.children,
            "metadata": self.metadata,
            "timestamp": self.timestamp.isoformat(),
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "ToTThoughtNode":
        """Create from dictionary"""
        return cls(
            id=data.get("id", str(uuid.uuid4())),
            parent_id=data.get("parent_id"),
            depth=data.get("depth", 0),
            thought=data["thought"],
            state=data.get("state"),
            evaluation_score=data.get("evaluation_score"),
            children=data.get("children", []),
            metadata=data.get("metadata", {}),
            timestamp=datetime.fromisoformat(data["timestamp"])
            if "timestamp" in data and data["timestamp"]
            else datetime.now(),
        )


@dataclass
class ToTTreeState:
    """Complete state of the Tree-of-Thought structure during search"""

    root_node: ToTThoughtNode
    all_nodes: dict[str, ToTThoughtNode] = field(default_factory=dict)
    current_depth: int = 0
    max_depth: int = 8

    def __post_init__(self) -> None:
        """Initialize with root node"""
        if not self.all_nodes:
            self.all_nodes = {self.root_node.id: self.root_node}

    def add_node(self, node: ToTThoughtNode) -> None:
        """Add a node to the tree"""
        self.all_nodes[node.id] = node

        # Update parent's children list
        if node.parent_id and node.parent_id in self.all_nodes:
            parent = self.all_nodes[node.parent_id]
            if node.id not in parent.children:
                # Create updated parent with new child
                updated_children = parent.children.copy()
                updated_children.append(node.id)
                parent = ToTThoughtNode(
                    id=parent.id,
                    parent_id=parent.parent_id,
                    depth=parent.depth,
                    thought=parent.thought,
                    state=parent.state.copy() if parent.state else None,
                    evaluation_score=parent.evaluation_score,
                    children=updated_children,
                    metadata=parent.metadata.copy(),
                    timestamp=parent.timestamp,
                )
                self.all_nodes[node.parent_id] = parent

        # Update current depth
        self.current_depth = max(self.current_depth, node.depth)

    def update_node(self, node: ToTThoughtNode) -> None:
        """Update an existing node"""
        self.all_nodes[node.id] = node

    def get_node(self, node_id: str) -> ToTThoughtNode | None:
        """Get a node by ID"""
        return self.all_nodes.get(node_id)

    def get_path_to_root(self, from_node_id: str) -> list[ToTThoughtNode]:
        """Get path from a node to the root"""
        path: list[ToTThoughtNode] = []
        current_node_id: str | None = from_node_id
        visited: set[str] = set()  # Prevent cycles

        while current_node_id and current_node_id not in visited:
            node = self.all_nodes.get(current_node_id)
            if not node:
                break

            visited.add(current_node_id)
            path.insert(0, node)
            current_node_id = node.parent_id

        return path

    def get_leaves(self) -> list[ToTThoughtNode]:
        """Get all leaf nodes (nodes with no children)"""
        return [
            node
            for node in self.all_nodes.values()
            if not node.children
        ]


@dataclass
class EvaluationWeights:
    """Weights for hybrid evaluation approach"""

    llm: float = 0.4  # LLM-based scoring weight (0.0-1.0)
    semantic: float = 0.3  # Semantic similarity weight (0.0-1.0)
    heuristic: float = 0.3  # Heuristic metrics weight (0.0-1.0)

    def __post_init__(self) -> None:
        """Normalize weights to sum to 1.0"""
        total = self.llm + self.semantic + self.heuristic
        if total > 0:
            self.llm = self.llm / total
            self.semantic = self.semantic / total
            self.heuristic = self.heuristic / total
        else:
            self.llm = 1.0 / 3.0
            self.semantic = 1.0 / 3.0
            self.heuristic = 1.0 / 3.0

    def to_dict(self) -> dict[str, float]:
        """Convert to dictionary"""
        return {
            "llm": self.llm,
            "semantic": self.semantic,
            "heuristic": self.heuristic,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "EvaluationWeights":
        """Create from dictionary"""
        return cls(
            llm=data.get("llm", 0.4),
            semantic=data.get("semantic", 0.3),
            heuristic=data.get("heuristic", 0.3),
        )


@dataclass
class ToTConfiguration:
    """Configuration parameters for Tree-of-Thought processing"""

    max_depth: int = 8
    base_thoughts_per_step: int = 5
    pruning_top_k: dict[int, int] = field(
        default_factory=lambda: {0: 5, 1: 5, 2: 4, 3: 4, 4: 3, 5: 3, 6: 2, 7: 2, 8: 1}
    )
    min_score_threshold: float = 0.2
    evaluation_weights: EvaluationWeights = field(
        default_factory=lambda: EvaluationWeights(llm=0.5, semantic=0.3, heuristic=0.2)
    )
    search_strategy: str = "best_first"  # "best_first", "breadth_first", "depth_first"
    max_search_time: float = 120.0
    enable_early_termination: bool = True

    @classmethod
    def default(cls) -> "ToTConfiguration":
        """Return default configuration"""
        return cls()

    def adaptive_thought_count(self, depth: int) -> int:
        """Get adaptive thought count based on depth"""
        if depth <= 1:
            # Broader exploration at early levels
            return max(3, self.base_thoughts_per_step)
        elif depth <= 3:
            # Focused refinement
            return max(2, self.base_thoughts_per_step - 1)
        else:
            # Deep specialization
            return max(1, self.base_thoughts_per_step - 2)

    def top_k(self, depth: int) -> int:
        """Get top-K for a given depth"""
        return self.pruning_top_k.get(depth, max(self.pruning_top_k.values(), default=2))

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary"""
        return {
            "max_depth": self.max_depth,
            "base_thoughts_per_step": self.base_thoughts_per_step,
            "pruning_top_k": self.pruning_top_k,
            "min_score_threshold": self.min_score_threshold,
            "evaluation_weights": self.evaluation_weights.to_dict(),
            "search_strategy": self.search_strategy,
            "max_search_time": self.max_search_time,
            "enable_early_termination": self.enable_early_termination,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "ToTConfiguration":
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
            pruning_top_k=data.get("pruning_top_k", {0: 3, 1: 3, 2: 2, 3: 2, 4: 1}),
            min_score_threshold=data.get("min_score_threshold", 0.3),
            evaluation_weights=eval_weights,
            search_strategy=data.get("search_strategy", "best_first"),
            max_search_time=data.get("max_search_time", 60.0),
            enable_early_termination=data.get("enable_early_termination", True),
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
class ToTComplexityScore:
    """Result from Tree-of-Thought complexity detection analysis"""

    score: float  # 0.0 to 1.0
    factors: list[ComplexityFactor]
    requires_tot: bool  # Whether ToT should be used
    requires_cot: bool  # Whether CoT would be sufficient
    estimated_timeout_multiplier: float

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary"""
        return {
            "score": self.score,
            "factors": [f.to_dict() for f in self.factors],
            "requires_tot": self.requires_tot,
            "requires_cot": self.requires_cot,
            "estimated_timeout_multiplier": self.estimated_timeout_multiplier,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "ToTComplexityScore":
        """Create from dictionary"""
        factors = [ComplexityFactor.from_dict(f) for f in data.get("factors", [])]
        return cls(
            score=data.get("score", 0.5),
            factors=factors,
            requires_tot=data.get("requires_tot", False),
            requires_cot=data.get("requires_cot", False),
            estimated_timeout_multiplier=data.get("estimated_timeout_multiplier", 1.0),
        )


@dataclass
class ToTSearchResult:
    """Final result from a Tree-of-Thought search operation"""

    best_path: list[ToTThoughtNode]  # Path from root to best leaf
    final_answer: str
    evaluation_score: float  # Best path's overall score
    explored_nodes: int  # Total nodes explored
    pruned_nodes: int  # Total nodes pruned
    search_statistics: "SearchStatistics"
    model_used: str
    total_latency: float

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary"""
        return {
            "best_path": [node.to_dict() for node in self.best_path],
            "final_answer": self.final_answer,
            "evaluation_score": self.evaluation_score,
            "explored_nodes": self.explored_nodes,
            "pruned_nodes": self.pruned_nodes,
            "search_statistics": self.search_statistics.to_dict(),
            "model_used": self.model_used,
            "total_latency": self.total_latency,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "ToTSearchResult":
        """Create from dictionary"""
        return cls(
            best_path=[ToTThoughtNode.from_dict(n) for n in data["best_path"]],
            final_answer=data["final_answer"],
            evaluation_score=data["evaluation_score"],
            explored_nodes=data["explored_nodes"],
            pruned_nodes=data["pruned_nodes"],
            search_statistics=SearchStatistics.from_dict(data["search_statistics"]),
            model_used=data["model_used"],
            total_latency=data["total_latency"],
        )


@dataclass
class SearchStatistics:
    """Statistics about the search process"""

    nodes_per_depth: dict[int, int]  # Node count at each depth
    average_evaluation_score: float
    max_depth_reached: int
    search_strategy: str
    termination_reason: str  # "max_depth", "perfect_solution", "queue_exhausted", "timeout", "no_valid_path"

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary"""
        return {
            "nodes_per_depth": self.nodes_per_depth,
            "average_evaluation_score": self.average_evaluation_score,
            "max_depth_reached": self.max_depth_reached,
            "search_strategy": self.search_strategy,
            "termination_reason": self.termination_reason,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "SearchStatistics":
        """Create from dictionary"""
        return cls(
            nodes_per_depth=data.get("nodes_per_depth", {}),
            average_evaluation_score=data.get("average_evaluation_score", 0.5),
            max_depth_reached=data.get("max_depth_reached", 0),
            search_strategy=data.get("search_strategy", "best_first"),
            termination_reason=data.get("termination_reason", "queue_exhausted"),
        )


@dataclass
class ToTResult:
    """Compatible result format similar to CoTResult for easy integration"""

    path: list[ToTThoughtNode]
    final_answer: str
    total_reasoning: str
    confidence: float
    model_used: str
    total_latency: float

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary for serialization"""
        return {
            "path": [node.to_dict() for node in self.path],
            "final_answer": self.final_answer,
            "total_reasoning": self.total_reasoning,
            "confidence": self.confidence,
            "model_used": self.model_used,
            "total_latency": self.total_latency,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "ToTResult":
        """Create from dictionary"""
        return cls(
            path=[ToTThoughtNode.from_dict(n) for n in data["path"]],
            final_answer=data["final_answer"],
            total_reasoning=data["total_reasoning"],
            confidence=data["confidence"],
            model_used=data["model_used"],
            total_latency=data["total_latency"],
        )

    @classmethod
    def from_search_result(cls, search_result: ToTSearchResult) -> "ToTResult":
        """Create from ToTSearchResult"""
        total_reasoning = "\n\n---\n\n".join([node.thought for node in search_result.best_path])
        return cls(
            path=search_result.best_path,
            final_answer=search_result.final_answer,
            total_reasoning=total_reasoning,
            confidence=search_result.evaluation_score,
            model_used=search_result.model_used,
            total_latency=search_result.total_latency,
        )

