"""
Plan Optimizer Module
Neural network for optimizing execution plans
"""

from typing import Dict, Any, Optional, List
import sys
from pathlib import Path

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
    # Create dummy classes/types when JAX isn't available
    jax = None
    jnp = None
    nn = None
    serialization = None
    optax = None

if JAX_AVAILABLE:

    class PlanScorer(nn.Module):
        """
        Neural network for scoring plan quality
        Evaluates plans based on time, success probability, resource usage
        """

        plan_feature_dim: int = 256
        hidden_dim: int = 128
        dropout: float = 0.1

        @nn.compact
        def __call__(self, plan_features: "jnp.ndarray", training: bool = False) -> Dict[str, "jnp.ndarray"]:
            """
            Score a plan

            Args:
                plan_features: Plan feature vector (batch_size, plan_feature_dim)
                training: Whether in training mode (for dropout)

            Returns:
                Dict with scores
            """
            # Plan feature encoder
            x = nn.Dense(self.hidden_dim)(plan_features)
            x = nn.relu(x)
            x = nn.Dropout(rate=self.dropout, deterministic=not training)(x)
            x = nn.Dense(self.hidden_dim)(x)
            encoded = nn.relu(x)

            # Scoring heads
            estimated_time = nn.relu(nn.Dense(1)(encoded))
            success_probability = nn.sigmoid(nn.Dense(1)(encoded))
            resource_usage = nn.relu(nn.Dense(1)(encoded))
            quality_score = nn.sigmoid(nn.Dense(1)(encoded))

            return {
                "estimated_time": estimated_time,
                "success_probability": success_probability,
                "resource_usage": resource_usage,
                "quality_score": quality_score,
            }


class PlanOptimizerModule(BaseBrainModule):
    """Neural network for optimizing execution plans"""

    def __init__(self):
        self.scorer_params: Optional[Dict[str, Any]] = None
        self.scorer: Optional[PlanScorer] = None
        self.optimizer: Optional[optax.GradientTransformation] = None
        self.opt_state: Optional[Any] = None
        self.is_trained = False
        self.rng = None

    @property
    def metadata(self) -> ModuleMetadata:
        return ModuleMetadata(
            name="plan_optimizer",
            version="1.0.0",
            description="Neural network for optimizing execution plans",
            operations=[
                "score_plan",
                "optimize_plan",
                "compare_plans",
                "train_scorer",
                "load_model",
                "save_model",
            ],
            dependencies=["jax", "flax", "optax"],
            model_required=True,
        )

    def initialize(self) -> bool:
        """Initialize the module"""
        if not JAX_AVAILABLE:
            print("[PlanOptimizerModule] JAX not available", file=sys.stderr)
            return False

        # Initialize RNG
        self.rng = jax.random.PRNGKey(0)

        # Initialize default scorer
        if self.scorer is None:
            self.scorer = PlanScorer()
            # Initialize parameters
            dummy_input = jnp.zeros((1, 256))
            self.rng, init_rng = jax.random.split(self.rng)
            self.scorer_params = self.scorer.init(init_rng, dummy_input, training=False)

        # Initialize optimizer
        if self.optimizer is None:
            self.optimizer = optax.adam(learning_rate=1e-3)
            self.opt_state = self.optimizer.init(self.scorer_params)

        return True

    def execute(self, operation: str, params: Dict[str, Any]) -> Dict[str, Any]:
        """Execute an optimization operation"""
        if not JAX_AVAILABLE:
            return {"success": False, "error": "JAX not available"}

        try:
            if operation == "score_plan":
                return self._score_plan(params)
            elif operation == "optimize_plan":
                return self._optimize_plan(params)
            elif operation == "compare_plans":
                return self._compare_plans(params)
            elif operation == "train_scorer":
                return self._train_scorer(params)
            elif operation == "load_model":
                return self._load_model(params)
            elif operation == "save_model":
                return self._save_model(params)
            else:
                raise ValueError(f"Unknown operation: {operation}")
        except Exception as e:
            return {"success": False, "error": str(e)}

    def _extract_plan_features(self, plan: Dict[str, Any]) -> "jnp.ndarray":
        """
        Extract feature vector from a plan

        Args:
            plan: Plan dictionary with steps, dependencies, etc.

        Returns:
            Feature array
        """
        # Extract features from plan
        num_steps = len(plan.get("steps", []))
        num_dependencies = sum(
            len(step.get("dependsOn", [])) for step in plan.get("steps", [])
        )
        estimated_time = plan.get("estimatedTotalTime", 0.0)
        can_parallel = 1.0 if plan.get("canExecuteInParallel", False) else 0.0

        # Create feature vector (simplified - in production, use more sophisticated features)
        features = jnp.array(
            [
                num_steps / 20.0,  # Normalize
                num_dependencies / 10.0,
                estimated_time / 100.0,
                can_parallel,
                # Add more features as needed
            ]
            + [0.0] * 251,
            dtype=jnp.float32,
        )  # Pad to 256 dimensions

        return features[jnp.newaxis, :]  # Add batch dimension

    def _score_plan(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """
        Score a plan's quality

        Args:
            plan: Plan dictionary

        Returns:
            Dict with scores
        """
        plan = params.get("plan")

        if not plan:
            return {"success": False, "error": "plan required"}

        if self.scorer is None or self.scorer_params is None:
            self.scorer = PlanScorer()
            dummy_input = jnp.zeros((1, 256))
            self.rng, init_rng = jax.random.split(self.rng)
            self.scorer_params = self.scorer.init(init_rng, dummy_input, training=False)

        # Extract features
        plan_features = self._extract_plan_features(plan)

        # Score
        scores = self.scorer.apply(
            {"params": self.scorer_params}, plan_features, training=False
        )

        return {
            "success": True,
            "estimated_time": float(scores["estimated_time"][0, 0]),
            "success_probability": float(scores["success_probability"][0, 0]),
            "resource_usage": float(scores["resource_usage"][0, 0]),
            "quality_score": float(scores["quality_score"][0, 0]),
        }

    def _optimize_plan(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """
        Suggest optimizations for a plan

        Args:
            plan: Plan dictionary

        Returns:
            Dict with optimization suggestions
        """
        plan = params.get("plan")

        if not plan:
            return {"success": False, "error": "plan required"}

        # Score current plan
        current_score = self._score_plan({"plan": plan})

        if not current_score["success"]:
            return current_score

        # Generate optimization suggestions based on scores
        suggestions = []

        if current_score["estimated_time"] > 50.0:
            suggestions.append(
                "Consider parallelizing independent steps to reduce execution time"
            )

        if current_score["success_probability"] < 0.7:
            suggestions.append("Add fallback strategies for critical steps")

        if current_score["resource_usage"] > 0.8:
            suggestions.append("Optimize resource-intensive steps")

        return {
            "success": True,
            "current_scores": current_score,
            "suggestions": suggestions,
            "optimized": len(suggestions) > 0,
        }

    def _compare_plans(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """
        Compare multiple plans and rank them

        Args:
            plans: List of plan dictionaries

        Returns:
            Dict with ranked plans
        """
        plans = params.get("plans", [])

        if not plans:
            return {"success": False, "error": "plans required"}

        # Score all plans
        scored_plans = []
        for i, plan in enumerate(plans):
            score_result = self._score_plan({"plan": plan})
            if score_result["success"]:
                scored_plans.append(
                    {
                        "plan_index": i,
                        "plan": plan,
                        "quality_score": score_result["quality_score"],
                        "estimated_time": score_result["estimated_time"],
                        "success_probability": score_result["success_probability"],
                    }
                )

        # Sort by quality score
        scored_plans.sort(key=lambda x: x["quality_score"], reverse=True)

        return {
            "success": True,
            "ranked_plans": scored_plans,
            "best_plan_index": scored_plans[0]["plan_index"] if scored_plans else None,
        }

    def _train_scorer(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """
        Train the plan scorer on historical data

        Args:
            training_data: List of (plan, actual_time, success, resource_usage) tuples
            epochs: Number of training epochs
            learning_rate: Learning rate

        Returns:
            Dict with training results
        """
        training_data = params.get("training_data", [])
        epochs = params.get("epochs", 20)
        learning_rate = params.get("learning_rate", 1e-3)

        if not training_data:
            return {"success": False, "error": "training_data required"}

        # Initialize scorer if needed
        if self.scorer is None or self.scorer_params is None:
            self.scorer = PlanScorer()
            dummy_input = jnp.zeros((1, 256))
            self.rng, init_rng = jax.random.split(self.rng)
            self.scorer_params = self.scorer.init(init_rng, dummy_input, training=False)

        # Initialize optimizer
        self.optimizer = optax.adam(learning_rate=learning_rate)
        self.opt_state = self.optimizer.init(self.scorer_params)

        # Define loss function
        def loss_fn(params, plan_features, targets):
            """Compute loss for a batch"""
            scores = self.scorer.apply(
                {"params": params}, plan_features, training=True, rngs={"dropout": self.rng}
            )

            # Compute losses
            time_loss = jnp.mean((scores["estimated_time"] - targets["time"]) ** 2)
            success_loss = optax.sigmoid_binary_cross_entropy(
                scores["success_probability"], targets["success"]
            ).mean()
            resource_loss = jnp.mean((scores["resource_usage"] - targets["resource"]) ** 2)

            return time_loss + success_loss + resource_loss

        # Training loop
        for epoch in range(epochs):
            total_loss = 0.0

            for plan, actual_time, success, resource_usage in training_data:
                # Extract features
                plan_features = self._extract_plan_features(plan)

                # Create targets
                targets = {
                    "time": jnp.array([[actual_time]], dtype=jnp.float32),
                    "success": jnp.array([[1.0 if success else 0.0]], dtype=jnp.float32),
                    "resource": jnp.array([[resource_usage]], dtype=jnp.float32),
                }

                # Compute loss and gradients
                loss, grads = jax.value_and_grad(loss_fn)(
                    self.scorer_params, plan_features, targets
                )

                # Update parameters
                updates, self.opt_state = self.optimizer.update(grads, self.opt_state)
                self.scorer_params = optax.apply_updates(self.scorer_params, updates)

                total_loss += float(loss)

            avg_loss = total_loss / len(training_data)
            if epoch % 5 == 0:
                print(
                    f"[PlanOptimizerModule] Epoch {epoch}, Loss: {avg_loss:.4f}",
                    file=sys.stderr,
                )

        self.is_trained = True

        return {"success": True, "epochs": epochs, "final_loss": avg_loss}

    def _load_model(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """Load a trained scorer"""
        model_path = params.get("model_path")

        if not model_path:
            return {"success": False, "error": "model_path required"}

        try:
            with open(model_path, "rb") as f:
                bytes_data = f.read()

            # Deserialize parameters
            self.scorer_params = serialization.from_bytes(self.scorer_params, bytes_data)

            # Initialize scorer if needed
            if self.scorer is None:
                self.scorer = PlanScorer()

            self.is_trained = True

            return {"success": True}
        except Exception as e:
            return {"success": False, "error": f"Failed to load: {str(e)}"}

    def _save_model(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """Save the trained scorer"""
        model_path = params.get("model_path")

        if not model_path:
            return {"success": False, "error": "model_path required"}

        if self.scorer_params is None:
            return {"success": False, "error": "No model to save"}

        try:
            # Serialize parameters
            bytes_output = serialization.to_bytes(self.scorer_params)

            with open(model_path, "wb") as f:
                f.write(bytes_output)

            return {"success": True, "model_path": model_path}
        except Exception as e:
            return {"success": False, "error": f"Failed to save: {str(e)}"}
