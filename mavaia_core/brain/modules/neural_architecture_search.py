"""
Neural Architecture Search (NAS)
Automatically discover optimal architectures for specific tasks
"""

from typing import Dict, Any, Optional, List, Tuple
import sys
from pathlib import Path
import random
import copy

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent))

from mavaia_core.brain.base_module import BaseBrainModule, ModuleMetadata

# Optional imports
try:
    import jax
    import jax.numpy as jnp
    import flax.linen as nn
    from flax import serialization
    import optax

    JAX_AVAILABLE = True
except ImportError:
    JAX_AVAILABLE = False
    jax = None
    jnp = None
    nn = None
    serialization = None
    optax = None


class ArchitectureCandidate:
    """Represents a candidate architecture"""

    def __init__(
        self,
        num_layers: int,
        hidden_dim: int,
        num_heads: int,
        dropout: float,
        activation: str = "relu",
    ):
        self.num_layers = num_layers
        self.hidden_dim = hidden_dim
        self.num_heads = num_heads
        self.dropout = dropout
        self.activation = activation
        self.performance_score: float = 0.0
        self.model_params: Optional[Dict[str, Any]] = None

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary"""
        return {
            "num_layers": self.num_layers,
            "hidden_dim": self.hidden_dim,
            "num_heads": self.num_heads,
            "dropout": self.dropout,
            "activation": self.activation,
            "performance_score": self.performance_score,
        }


class SearchSpace:
    """Defines the architecture search space"""

    def __init__(
        self,
        num_layers_range: Tuple[int, int] = (1, 6),
        hidden_dim_options: List[int] = [128, 256, 512, 768],
        num_heads_options: List[int] = [4, 8, 16],
        dropout_range: Tuple[float, float] = (0.0, 0.3),
        activation_options: List[str] = ["relu", "gelu", "tanh"],
    ):
        self.num_layers_range = num_layers_range
        self.hidden_dim_options = hidden_dim_options
        self.num_heads_options = num_heads_options
        self.dropout_range = dropout_range
        self.activation_options = activation_options

    def sample_candidate(self) -> ArchitectureCandidate:
        """Sample a random architecture candidate"""
        num_layers = random.randint(*self.num_layers_range)
        hidden_dim = random.choice(self.hidden_dim_options)
        num_heads = random.choice(self.num_heads_options)
        dropout = random.uniform(*self.dropout_range)
        activation = random.choice(self.activation_options)

        return ArchitectureCandidate(
            num_layers=num_layers,
            hidden_dim=hidden_dim,
            num_heads=num_heads,
            dropout=dropout,
            activation=activation,
        )

    def mutate_candidate(
        self, candidate: ArchitectureCandidate, mutation_rate: float = 0.3
    ) -> ArchitectureCandidate:
        """Mutate a candidate architecture"""
        new_candidate = copy.deepcopy(candidate)

        if random.random() < mutation_rate:
            new_candidate.num_layers = random.randint(*self.num_layers_range)
        if random.random() < mutation_rate:
            new_candidate.hidden_dim = random.choice(self.hidden_dim_options)
        if random.random() < mutation_rate:
            new_candidate.num_heads = random.choice(self.num_heads_options)
        if random.random() < mutation_rate:
            new_candidate.dropout = random.uniform(*self.dropout_range)
        if random.random() < mutation_rate:
            new_candidate.activation = random.choice(self.activation_options)

        return new_candidate


# Only define Flax-based classes if JAX is available
if JAX_AVAILABLE and nn is not None:
    class TransformerEncoderLayer(nn.Module):
        """Flax implementation of Transformer Encoder Layer"""
        d_model: int
        nhead: int
        dim_feedforward: int
        dropout: float = 0.1
        activation: str = "relu"

        @nn.compact
        def __call__(self, x: "jnp.ndarray", training: bool = False) -> "jnp.ndarray":
            """Forward pass"""
            # Self-attention
            attn_out = nn.MultiHeadAttention(
                num_heads=self.nhead,
                qkv_features=self.d_model,
                dropout_rate=self.dropout,
                deterministic=not training,
            )(x, x)
            x = x + nn.Dropout(rate=self.dropout, deterministic=not training)(attn_out)
            x = nn.LayerNorm()(x)

            # Feed-forward
            ff_out = nn.Dense(self.dim_feedforward)(x)
            if self.activation == "relu":
                ff_out = nn.relu(ff_out)
            elif self.activation == "gelu":
                ff_out = nn.gelu(ff_out)
            elif self.activation == "tanh":
                ff_out = nn.tanh(ff_out)
            ff_out = nn.Dropout(rate=self.dropout, deterministic=not training)(ff_out)
            ff_out = nn.Dense(self.d_model)(ff_out)
            x = x + nn.Dropout(rate=self.dropout, deterministic=not training)(ff_out)
            x = nn.LayerNorm()(x)

            return x

    class CandidateModel(nn.Module):
        """Flax model built from architecture candidate"""
        candidate: ArchitectureCandidate
        input_dim: int
        output_dim: int

        @nn.compact
        def __call__(self, x: "jnp.ndarray", training: bool = False) -> "jnp.ndarray":
            """Forward pass"""
            # Input projection
            x = nn.Dense(self.candidate.hidden_dim)(x)

            # Transformer layers
            for _ in range(self.candidate.num_layers):
                x = TransformerEncoderLayer(
                    d_model=self.candidate.hidden_dim,
                    nhead=self.candidate.num_heads,
                    dim_feedforward=self.candidate.hidden_dim * 2,
                    dropout=self.candidate.dropout,
                    activation=self.candidate.activation,
                )(x, training=training)

            # Average pooling
            x = jnp.mean(x, axis=1)  # (batch_size, hidden_dim)

            # Output projection
            x = nn.Dense(self.output_dim)(x)
            return x
else:
    # Define stub classes when JAX is not available
    class TransformerEncoderLayer:
        def __init__(self, *args, **kwargs):
            raise ImportError("JAX and Flax are required for TransformerEncoderLayer")
    
    class CandidateModel:
        def __init__(self, *args, **kwargs):
            raise ImportError("JAX and Flax are required for CandidateModel")


def build_model_from_candidate(
    candidate: ArchitectureCandidate, input_dim: int, output_dim: int
) -> CandidateModel:
    """Build a Flax model from architecture candidate"""
    if not JAX_AVAILABLE:
        raise ImportError("JAX and Flax are required for build_model_from_candidate")
    return CandidateModel(candidate=candidate, input_dim=input_dim, output_dim=output_dim)


class EvolutionaryNAS:
    """
    Evolutionary Neural Architecture Search
    Uses evolutionary algorithms to search for optimal architectures
    """

    def __init__(
        self,
        search_space: SearchSpace,
        population_size: int = 20,
        elite_size: int = 5,
        mutation_rate: float = 0.3,
        crossover_rate: float = 0.5,
    ):
        self.search_space = search_space
        self.population_size = population_size
        self.elite_size = elite_size
        self.mutation_rate = mutation_rate
        self.crossover_rate = crossover_rate
        self.population: List[ArchitectureCandidate] = []
        self.generation = 0
        self.rng = None
        if JAX_AVAILABLE:
            self.rng = jax.random.PRNGKey(0)

    def initialize_population(self):
        """Initialize random population"""
        self.population = [
            self.search_space.sample_candidate() for _ in range(self.population_size)
        ]

    def evaluate_candidate(
        self,
        candidate: ArchitectureCandidate,
        input_dim: int,
        output_dim: int,
        train_data: List[Tuple["jnp.ndarray", "jnp.ndarray"]],
        eval_data: List[Tuple["jnp.ndarray", "jnp.ndarray"]],
        epochs: int = 5,
    ) -> float:
        """
        Evaluate a candidate architecture

        Returns:
            Performance score (higher is better)
        """
        if not JAX_AVAILABLE:
            return 0.0

        try:
            # Build model
            model = build_model_from_candidate(candidate, input_dim, output_dim)

            # Initialize parameters
            dummy_input = jnp.zeros((1, input_dim))
            self.rng, init_rng = jax.random.split(self.rng)
            params = model.init(init_rng, dummy_input, training=False)

            # Initialize optimizer
            optimizer = optax.adam(learning_rate=1e-3)
            opt_state = optimizer.init(params)

            # Define loss function
            def loss_fn(params, x, y):
                pred = model.apply({"params": params}, x, training=True, rngs={"dropout": self.rng})
                return jnp.mean((pred - y) ** 2)

            # Quick training
            for epoch in range(epochs):
                for x, y in train_data:
                    # Ensure correct shape
                    if len(x.shape) == 1:
                        x = x[jnp.newaxis, :]
                    if len(y.shape) == 1:
                        y = y[jnp.newaxis, :]

                    # Compute loss and gradients
                    loss, grads = jax.value_and_grad(loss_fn)(params, x, y)

                    # Update parameters
                    updates, opt_state = optimizer.update(grads, opt_state)
                    params = optax.apply_updates(params, updates)

            # Evaluate
            total_loss = 0.0
            for x, y in eval_data:
                # Ensure correct shape
                if len(x.shape) == 1:
                    x = x[jnp.newaxis, :]
                if len(y.shape) == 1:
                    y = y[jnp.newaxis, :]

                pred = model.apply({"params": params}, x, training=False)
                loss = jnp.mean((pred - y) ** 2)
                total_loss += float(loss)

            # Performance score (inverse of loss, normalized)
            avg_loss = total_loss / len(eval_data)
            score = 1.0 / (1.0 + avg_loss)  # Higher score = better

            candidate.performance_score = score
            candidate.model_params = params

            return score

        except Exception as e:
            print(f"[EvolutionaryNAS] Evaluation failed: {e}", file=sys.stderr)
            return 0.0

    def select_parents(self) -> Tuple[ArchitectureCandidate, ArchitectureCandidate]:
        """Select parents for crossover (tournament selection)"""
        tournament_size = 3
        tournament = random.sample(
            self.population, min(tournament_size, len(self.population))
        )
        tournament.sort(key=lambda c: c.performance_score, reverse=True)
        parent1 = tournament[0]

        tournament = random.sample(
            self.population, min(tournament_size, len(self.population))
        )
        tournament.sort(key=lambda c: c.performance_score, reverse=True)
        parent2 = tournament[0]

        return parent1, parent2

    def crossover(
        self, parent1: ArchitectureCandidate, parent2: ArchitectureCandidate
    ) -> ArchitectureCandidate:
        """Crossover two parents to create offspring"""
        # Uniform crossover
        child = ArchitectureCandidate(
            num_layers=(
                parent1.num_layers if random.random() < 0.5 else parent2.num_layers
            ),
            hidden_dim=(
                parent1.hidden_dim if random.random() < 0.5 else parent2.hidden_dim
            ),
            num_heads=parent1.num_heads if random.random() < 0.5 else parent2.num_heads,
            dropout=(parent1.dropout + parent2.dropout) / 2.0,  # Average
            activation=(
                parent1.activation if random.random() < 0.5 else parent2.activation
            ),
        )
        return child

    def evolve(
        self,
        input_dim: int,
        output_dim: int,
        train_data: List[Tuple["jnp.ndarray", "jnp.ndarray"]],
        eval_data: List[Tuple["jnp.ndarray", "jnp.ndarray"]],
        generations: int = 10,
        epochs_per_candidate: int = 5,
    ) -> ArchitectureCandidate:
        """
        Evolve population to find optimal architecture

        Returns:
            Best architecture candidate
        """
        # Initialize population
        if not self.population:
            self.initialize_population()

        # Evaluate initial population
        print(f"[EvolutionaryNAS] Evaluating initial population...", file=sys.stderr)
        for candidate in self.population:
            if candidate.performance_score == 0.0:
                self.evaluate_candidate(
                    candidate,
                    input_dim,
                    output_dim,
                    train_data,
                    eval_data,
                    epochs_per_candidate,
                )

        # Evolve
        for generation in range(generations):
            self.generation = generation + 1

            # Sort by performance
            self.population.sort(key=lambda c: c.performance_score, reverse=True)

            # Keep elite
            new_population = self.population[: self.elite_size].copy()

            # Generate offspring
            while len(new_population) < self.population_size:
                if random.random() < self.crossover_rate:
                    # Crossover
                    parent1, parent2 = self.select_parents()
                    child = self.crossover(parent1, parent2)
                else:
                    # Mutation
                    parent = random.choice(self.population[: self.elite_size])
                    child = self.search_space.mutate_candidate(
                        parent, self.mutation_rate
                    )

                # Evaluate child
                score = self.evaluate_candidate(
                    child,
                    input_dim,
                    output_dim,
                    train_data,
                    eval_data,
                    epochs_per_candidate,
                )

                new_population.append(child)

            self.population = new_population

            # Report
            best_score = max(c.performance_score for c in self.population)
            avg_score = sum(c.performance_score for c in self.population) / len(
                self.population
            )
            print(
                f"[EvolutionaryNAS] Generation {self.generation}: Best={best_score:.4f}, Avg={avg_score:.4f}",
                file=sys.stderr,
            )

        # Return best candidate
        self.population.sort(key=lambda c: c.performance_score, reverse=True)
        return self.population[0]


class NeuralArchitectureSearchModule(BaseBrainModule):
    """Neural Architecture Search for automatic architecture discovery"""

    def __init__(self):
        self.search_space: Optional[SearchSpace] = None
        self.nas: Optional[EvolutionaryNAS] = None
        self.best_architecture: Optional[ArchitectureCandidate] = None

    @property
    def metadata(self) -> ModuleMetadata:
        return ModuleMetadata(
            name="neural_architecture_search",
            version="1.0.0",
            description="Neural Architecture Search for automatic architecture discovery",
            operations=[
                "define_search_space",
                "search_architecture",
                "evaluate_architecture",
                "get_best_architecture",
                "save_architecture",
                "load_architecture",
            ],
            dependencies=["jax", "flax", "optax"],
            model_required=False,
        )

    def initialize(self) -> bool:
        """Initialize the module"""
        if not JAX_AVAILABLE:
            print(
                "[NeuralArchitectureSearchModule] JAX not available",
                file=sys.stderr,
            )
            return False

        # Default search space
        self.search_space = SearchSpace()
        self.nas = EvolutionaryNAS(self.search_space)

        return True

    def execute(self, operation: str, params: Dict[str, Any]) -> Dict[str, Any]:
        """Execute a NAS operation"""
        if not JAX_AVAILABLE:
            return {"success": False, "error": "JAX not available"}

        try:
            if operation == "define_search_space":
                return self._define_search_space(params)
            elif operation == "search_architecture":
                return self._search_architecture(params)
            elif operation == "evaluate_architecture":
                return self._evaluate_architecture(params)
            elif operation == "get_best_architecture":
                return self._get_best_architecture(params)
            elif operation == "save_architecture":
                return self._save_architecture(params)
            elif operation == "load_architecture":
                return self._load_architecture(params)
            else:
                raise ValueError(f"Unknown operation: {operation}")
        except Exception as e:
            return {"success": False, "error": str(e)}

    def _define_search_space(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """Define architecture search space"""
        self.search_space = SearchSpace(
            num_layers_range=tuple(params.get("num_layers_range", [1, 6])),
            hidden_dim_options=params.get("hidden_dim_options", [128, 256, 512, 768]),
            num_heads_options=params.get("num_heads_options", [4, 8, 16]),
            dropout_range=tuple(params.get("dropout_range", [0.0, 0.3])),
            activation_options=params.get(
                "activation_options", ["relu", "gelu", "tanh"]
            ),
        )

        self.nas = EvolutionaryNAS(self.search_space)

        return {"success": True, "search_space": "defined"}

    def _search_architecture(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """Search for optimal architecture"""
        input_dim = params.get("input_dim")
        output_dim = params.get("output_dim")
        train_data = params.get("train_data", [])
        eval_data = params.get("eval_data", [])
        generations = params.get("generations", 10)
        population_size = params.get("population_size", 20)
        epochs_per_candidate = params.get("epochs_per_candidate", 5)

        if not input_dim or not output_dim:
            return {"success": False, "error": "input_dim and output_dim required"}

        if not train_data or not eval_data:
            return {"success": False, "error": "train_data and eval_data required"}

        # Update NAS parameters
        if self.nas:
            self.nas.population_size = population_size

        # Convert data to JAX arrays if needed
        train_arrays = [
            (jnp.array(x, dtype=jnp.float32), jnp.array(y, dtype=jnp.float32))
            for x, y in train_data
        ]
        eval_arrays = [
            (jnp.array(x, dtype=jnp.float32), jnp.array(y, dtype=jnp.float32))
            for x, y in eval_data
        ]

        # Search
        best = self.nas.evolve(
            input_dim=input_dim,
            output_dim=output_dim,
            train_data=train_arrays,
            eval_data=eval_arrays,
            generations=generations,
            epochs_per_candidate=epochs_per_candidate,
        )

        self.best_architecture = best

        return {
            "success": True,
            "best_architecture": best.to_dict(),
            "performance_score": best.performance_score,
        }

    def _evaluate_architecture(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """Evaluate a specific architecture"""
        architecture = params.get("architecture")
        input_dim = params.get("input_dim")
        output_dim = params.get("output_dim")
        train_data = params.get("train_data", [])
        eval_data = params.get("eval_data", [])

        if not architecture:
            return {"success": False, "error": "architecture required"}

        # Create candidate
        candidate = ArchitectureCandidate(
            num_layers=architecture.get("num_layers", 3),
            hidden_dim=architecture.get("hidden_dim", 256),
            num_heads=architecture.get("num_heads", 8),
            dropout=architecture.get("dropout", 0.1),
            activation=architecture.get("activation", "relu"),
        )

        # Convert data
        train_arrays = [
            (jnp.array(x, dtype=jnp.float32), jnp.array(y, dtype=jnp.float32))
            for x, y in train_data
        ]
        eval_arrays = [
            (jnp.array(x, dtype=jnp.float32), jnp.array(y, dtype=jnp.float32))
            for x, y in eval_data
        ]

        # Evaluate
        score = self.nas.evaluate_candidate(
            candidate, input_dim, output_dim, train_arrays, eval_arrays, epochs=10
        )

        return {
            "success": True,
            "performance_score": score,
            "architecture": candidate.to_dict(),
        }

    def _get_best_architecture(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """Get the best found architecture"""
        if not self.best_architecture:
            return {"success": False, "error": "No architecture found yet"}

        return {
            "success": True,
            "architecture": self.best_architecture.to_dict(),
            "performance_score": self.best_architecture.performance_score,
        }

    def _save_architecture(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """Save architecture configuration"""
        import json

        save_path = params.get("save_path")

        if not save_path:
            return {"success": False, "error": "save_path required"}

        if not self.best_architecture:
            return {"success": False, "error": "No architecture to save"}

        try:
            with open(save_path, "w") as f:
                json.dump(self.best_architecture.to_dict(), f, indent=2)

            return {"success": True, "save_path": save_path}
        except Exception as e:
            return {"success": False, "error": f"Failed to save: {str(e)}"}

    def _load_architecture(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """Load architecture configuration"""
        import json

        load_path = params.get("load_path")

        if not load_path:
            return {"success": False, "error": "load_path required"}

        try:
            with open(load_path, "r") as f:
                arch_dict = json.load(f)

            self.best_architecture = ArchitectureCandidate(
                num_layers=arch_dict["num_layers"],
                hidden_dim=arch_dict["hidden_dim"],
                num_heads=arch_dict["num_heads"],
                dropout=arch_dict["dropout"],
                activation=arch_dict["activation"],
            )
            self.best_architecture.performance_score = arch_dict.get(
                "performance_score", 0.0
            )

            return {"success": True, "architecture": self.best_architecture.to_dict()}
        except Exception as e:
            return {"success": False, "error": f"Failed to load: {str(e)}"}
