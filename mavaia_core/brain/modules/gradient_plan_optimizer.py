"""
Gradient-Based Plan Optimization
Differentiable planning using gradient descent to optimize plan parameters
"""

from typing import Dict, Any, Optional, List, Tuple
from pathlib import Path
import logging

from mavaia_core.brain.base_module import BaseBrainModule, ModuleMetadata
from mavaia_core.exceptions import InvalidParameterError, ModuleInitializationError

logger = logging.getLogger(__name__)

# Optional imports
try:
    import jax
    import jax.numpy as jnp
    import flax.linen as nn
    from flax import serialization
    import optax
    from transformers import FlaxAutoModel, FlaxAutoTokenizer

    JAX_AVAILABLE = True
except ImportError:
    JAX_AVAILABLE = False
    # Create dummy classes/types when JAX isn't available
    jax = None
    jnp = None
    nn = None
    serialization = None
    optax = None
    FlaxAutoModel = None
    FlaxAutoTokenizer = None

if JAX_AVAILABLE:

    class TransformerDecoderLayer(nn.Module):
        """Flax implementation of Transformer Decoder Layer"""
        d_model: int
        nhead: int
        dim_feedforward: int
        dropout: float = 0.1

        @nn.compact
        def __call__(
            self, tgt: "jnp.ndarray", memory: "jnp.ndarray", training: bool = False
        ) -> "jnp.ndarray":
            """Forward pass"""
            # Self-attention
            attn_out = nn.MultiHeadAttention(
                num_heads=self.nhead,
                qkv_features=self.d_model,
                dropout_rate=self.dropout,
                deterministic=not training,
            )(tgt, tgt)
            tgt = tgt + nn.Dropout(rate=self.dropout, deterministic=not training)(attn_out)
            tgt = nn.LayerNorm()(tgt)

            # Cross-attention (attend to memory)
            cross_attn_out = nn.MultiHeadAttention(
                num_heads=self.nhead,
                qkv_features=self.d_model,
                dropout_rate=self.dropout,
                deterministic=not training,
            )(tgt, memory, memory)
            tgt = tgt + nn.Dropout(rate=self.dropout, deterministic=not training)(cross_attn_out)
            tgt = nn.LayerNorm()(tgt)

            # Feed-forward
            ff_out = nn.Dense(self.dim_feedforward)(tgt)
            ff_out = nn.relu(ff_out)
            ff_out = nn.Dropout(rate=self.dropout, deterministic=not training)(ff_out)
            ff_out = nn.Dense(self.d_model)(ff_out)
            tgt = tgt + nn.Dropout(rate=self.dropout, deterministic=not training)(ff_out)
            tgt = nn.LayerNorm()(tgt)

            return tgt

    class DifferentiablePlanner(nn.Module):
        """
        End-to-end differentiable planning network
        Uses soft attention over tools and steps for gradient-based optimization
        """

        tool_embedding_dim: int = 128
        hidden_dim: int = 256
        num_tools: int = 50
        max_steps: int = 10
        dropout: float = 0.1

        @nn.compact
        def __call__(
            self, query_embedding: "jnp.ndarray", tool_ids: Optional["jnp.ndarray"] = None, training: bool = False
        ) -> Dict[str, "jnp.ndarray"]:
            """
            Forward pass through differentiable planner

            Args:
                query_embedding: Query embedding (batch_size, 384)
                tool_ids: Optional tool IDs to consider (batch_size, num_tools)
                training: Whether in training mode

            Returns:
                Dict with plan outputs and attention weights
            """
            batch_size = query_embedding.shape[0]

            # Encode query
            x = nn.Dense(self.hidden_dim)(query_embedding)
            x = nn.relu(x)
            x = nn.Dropout(rate=self.dropout, deterministic=not training)(x)
            query_encoded = nn.Dense(self.hidden_dim)(x)  # (batch_size, hidden_dim)
            query_encoded = query_encoded[:, jnp.newaxis, :]  # (batch_size, 1, hidden_dim)

            # Get tool embeddings
            if tool_ids is None:
                # Use all tools
                tool_ids = jnp.arange(self.num_tools)[jnp.newaxis, :].repeat(batch_size, axis=0)

            # Tool embeddings (learnable)
            tool_embs = nn.Embed(self.num_tools, self.tool_embedding_dim)(tool_ids)  # (batch_size, num_tools, tool_embedding_dim)
            # Project to hidden_dim
            tool_embs = nn.Dense(self.hidden_dim)(tool_embs)  # (batch_size, num_tools, hidden_dim)

            # Soft attention over tools (differentiable selection)
            attended_tools = nn.MultiHeadAttention(
                num_heads=8,
                qkv_features=self.hidden_dim,
                dropout_rate=self.dropout,
                deterministic=not training,
            )(query_encoded, tool_embs, tool_embs)  # (batch_size, 1, hidden_dim)

            # Generate step sequence
            step_ids = jnp.arange(self.max_steps)[jnp.newaxis, :].repeat(batch_size, axis=0)
            step_embs = nn.Embed(self.max_steps, self.hidden_dim)(step_ids)  # (batch_size, max_steps, hidden_dim)

            # Use attended tools as memory for decoder
            memory = jnp.broadcast_to(attended_tools, (batch_size, self.max_steps, self.hidden_dim))

            # Plan steps (transformer decoder)
            planned_steps = step_embs
            for _ in range(3):  # num_layers
                planned_steps = TransformerDecoderLayer(
                    d_model=self.hidden_dim,
                    nhead=8,
                    dim_feedforward=self.hidden_dim * 2,
                    dropout=self.dropout,
                )(planned_steps, memory, training=training)

            # Project to tool space
            x_out = nn.Dense(self.hidden_dim // 2)(planned_steps)
            x_out = nn.relu(x_out)
            x_out = nn.Dropout(rate=self.dropout, deterministic=not training)(x_out)
            step_tool_scores = nn.Dense(self.tool_embedding_dim)(x_out)  # (batch_size, max_steps, tool_embedding_dim)

            # Compute similarity to tools (soft tool assignment)
            tool_similarities = jnp.matmul(
                step_tool_scores, jnp.transpose(tool_embs, (0, 2, 1))
            )  # (batch_size, max_steps, num_tools)
            tool_probs = nn.softmax(tool_similarities, axis=-1)

            # Predict plan quality
            plan_mean = jnp.mean(planned_steps, axis=1)  # (batch_size, hidden_dim)
            x_qual = nn.Dense(self.hidden_dim // 2)(plan_mean)
            x_qual = nn.relu(x_qual)
            x_qual = nn.Dropout(rate=self.dropout, deterministic=not training)(x_qual)
            plan_quality = nn.sigmoid(nn.Dense(1)(x_qual))  # (batch_size, 1)

            return {
                "tool_probabilities": tool_probs,
                "plan_quality": plan_quality,
                "step_embeddings": planned_steps,
            }


class GradientPlanOptimizerModule(BaseBrainModule):
    """Gradient-based plan optimization using differentiable planning"""

    def __init__(self):
        super().__init__()
        self.planner_params: Optional[Dict[str, Any]] = None
        self.planner: Optional[DifferentiablePlanner] = None
        self.optimizer: Optional[optax.GradientTransformation] = None
        self.opt_state: Optional[Any] = None
        self.embedding_model = None
        self.embedding_params = None
        self.tokenizer = None
        self.tool_names: List[str] = []
        self.rng = None

    @property
    def metadata(self) -> ModuleMetadata:
        return ModuleMetadata(
            name="gradient_plan_optimizer",
            version="1.0.0",
            description="Gradient-based plan optimization using differentiable planning",
            operations=[
                "generate_plan",
                "optimize_plan",
                "refine_plan",
                "train_planner",
                "load_model",
                "save_model",
            ],
            dependencies=["jax", "flax", "optax", "transformers"],
            model_required=True,
        )

    def initialize(self) -> bool:
        """Initialize the module"""
        if not JAX_AVAILABLE:
            logger.warning(
                "JAX not available; gradient_plan_optimizer disabled",
                extra={"module_name": "gradient_plan_optimizer"},
            )
            return False

        # Initialize RNG
        self.rng = jax.random.PRNGKey(0)

        return True

    def _ensure_embedding_model_loaded(self):
        """Lazy load embedding model using Flax backend"""
        if self.embedding_model is None or self.tokenizer is None:
            try:
                model_name = "sentence-transformers/all-MiniLM-L6-v2"
                self.tokenizer = FlaxAutoTokenizer.from_pretrained(model_name)
                self.embedding_model = FlaxAutoModel.from_pretrained(model_name)
                self.embedding_params = self.embedding_model.params
            except Exception as e:
                logger.debug(
                    "Failed to load Flax embedding model",
                    exc_info=True,
                    extra={"module_name": "gradient_plan_optimizer", "error_type": type(e).__name__},
                )
                raise ModuleInitializationError(
                    module_name="gradient_plan_optimizer",
                    reason="Failed to load Flax embedding model",
                ) from e

    def _get_embeddings(self, texts: List[str]) -> "jnp.ndarray":
        """Get embeddings for texts using Flax model"""
        self._ensure_embedding_model_loaded()

        inputs = self.tokenizer(texts, return_tensors="jax", padding=True, truncation=True)
        outputs = self.embedding_model(**inputs, params=self.embedding_params)
        return jnp.mean(outputs.last_hidden_state, axis=1)

    def _ensure_planner_loaded(self, num_tools: int = 50):
        """Lazy load planner"""
        if self.planner is None or self.planner_params is None:
            self.planner = DifferentiablePlanner(
                tool_embedding_dim=128,
                hidden_dim=256,
                num_tools=num_tools,
                max_steps=10,
            )
            # Initialize parameters
            dummy_query = jnp.zeros((1, 384))
            self.rng, init_rng = jax.random.split(self.rng)
            self.planner_params = self.planner.init(init_rng, dummy_query, training=False)

    def execute(self, operation: str, params: Dict[str, Any]) -> Dict[str, Any]:
        """Execute an optimization operation"""
        if not JAX_AVAILABLE:
            return {"success": False, "error": "JAX not available"}

        try:
            match operation:
                case "generate_plan":
                    return self._generate_plan(params)
                case "optimize_plan":
                    return self._optimize_plan(params)
                case "refine_plan":
                    return self._refine_plan(params)
                case "train_planner":
                    return self._train_planner(params)
                case "load_model":
                    return self._load_model(params)
                case "save_model":
                    return self._save_model(params)
                case _:
                    raise InvalidParameterError("operation", str(operation), "Unknown operation for gradient_plan_optimizer")
        except Exception as e:
            if isinstance(e, InvalidParameterError):
                return {"success": False, "error": str(e)}
            logger.debug(
                "gradient_plan_optimizer operation failed",
                exc_info=True,
                extra={"module_name": "gradient_plan_optimizer", "operation": str(operation), "error_type": type(e).__name__},
            )
            return {"success": False, "error": "Operation failed"}

    def _generate_plan(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """Generate a plan using differentiable planner"""
        query = params.get("query")
        tool_names = params.get("tool_names", [])

        if not query:
            return {"success": False, "error": "query required"}

        # Update tool names
        if tool_names:
            self.tool_names = tool_names
            num_tools = len(tool_names)
        else:
            num_tools = len(self.tool_names) if self.tool_names else 50

        # Load models
        self._ensure_embedding_model_loaded()
        self._ensure_planner_loaded(num_tools)

        # Get query embedding
        query_emb = self._get_embeddings([query])
        query_emb = query_emb[jnp.newaxis, :]  # Add batch dimension

        # Generate plan
        output = self.planner.apply(
            {"params": self.planner_params}, query_emb, training=False
        )

        # Extract plan
        tool_probs = jnp.asarray(output["tool_probabilities"][0])  # (max_steps, num_tools)
        quality = float(output["plan_quality"][0, 0])

        # Convert to plan structure
        plan_steps = []
        for step_idx in range(tool_probs.shape[0]):
            tool_idx = int(jnp.argmax(tool_probs[step_idx]))
            tool_prob = float(tool_probs[step_idx, tool_idx])

            if tool_prob > 0.1:  # Threshold
                tool_name = (
                    self.tool_names[tool_idx]
                    if tool_idx < len(self.tool_names)
                    else f"tool_{tool_idx}"
                )
                plan_steps.append(
                    {"step": step_idx + 1, "tool": tool_name, "probability": tool_prob}
                )

        return {
            "success": True,
            "plan_steps": plan_steps,
            "quality": quality,
        }

    def _optimize_plan(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """Optimize plan using gradient descent"""
        query = params.get("query")
        target_quality = params.get("target_quality", 0.9)
        max_iterations = params.get("max_iterations", 100)
        convergence_threshold = params.get("convergence_threshold", 0.01)
        tool_names = params.get("tool_names", [])

        if not query:
            return {"success": False, "error": "query required"}

        # Update tool names
        if tool_names:
            self.tool_names = tool_names
            num_tools = len(tool_names)
        else:
            num_tools = len(self.tool_names) if self.tool_names else 50

        # Load models
        self._ensure_embedding_model_loaded()
        self._ensure_planner_loaded(num_tools)

        # Initialize optimizer
        if self.optimizer is None:
            self.optimizer = optax.adam(learning_rate=1e-3)
            self.opt_state = self.optimizer.init(self.planner_params)

        # Get query embedding
        query_emb = self._get_embeddings([query])
        query_emb = query_emb[jnp.newaxis, :]

        # Define loss function
        def loss_fn(params, query_emb, target_quality):
            output = self.planner.apply({"params": params}, query_emb, training=True, rngs={"dropout": self.rng})
            quality = output["plan_quality"]
            loss = jnp.mean((quality - target_quality) ** 2)
            return loss, output

        # Optimize
        best_quality = 0.0
        best_plan = None
        iteration = 0

        for iteration in range(max_iterations):
            # Compute loss and gradients
            (loss, output), grads = jax.value_and_grad(loss_fn, has_aux=True)(
                self.planner_params, query_emb, target_quality
            )

            # Update parameters
            updates, self.opt_state = self.optimizer.update(grads, self.opt_state)
            self.planner_params = optax.apply_updates(self.planner_params, updates)

            quality = float(output["plan_quality"][0, 0])

            # Track best plan
            if quality > best_quality:
                best_quality = quality
                best_plan = output

            # Check convergence
            if abs(quality - target_quality) < convergence_threshold:
                break

        # Extract optimized plan
        tool_probs = jnp.asarray(best_plan["tool_probabilities"][0])

        plan_steps = []
        for step_idx in range(tool_probs.shape[0]):
            tool_idx = int(jnp.argmax(tool_probs[step_idx]))
            tool_prob = float(tool_probs[step_idx, tool_idx])

            if tool_prob > 0.1:
                tool_name = (
                    self.tool_names[tool_idx]
                    if tool_idx < len(self.tool_names)
                    else f"tool_{tool_idx}"
                )
                plan_steps.append(
                    {"step": step_idx + 1, "tool": tool_name, "probability": tool_prob}
                )

        return {
            "success": True,
            "optimized_plan": plan_steps,
            "final_quality": best_quality,
            "iterations": iteration + 1,
            "converged": abs(best_quality - target_quality) < convergence_threshold,
        }

    def _refine_plan(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """Refine an existing plan"""
        query = params.get("query")
        existing_plan = params.get("existing_plan", [])

        if not query:
            return {"success": False, "error": "query required"}

        # Use optimize_plan with existing plan as initialization
        # (Simplified - in production, would use existing plan to initialize)
        return self._optimize_plan(
            {"query": query, "target_quality": 0.95, "max_iterations": 50}
        )

    def _train_planner(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """Train the differentiable planner"""
        training_data = params.get(
            "training_data", []
        )  # List of (query, optimal_plan, quality)
        epochs = params.get("epochs", 20)
        learning_rate = params.get("learning_rate", 1e-3)
        num_tools = params.get("num_tools", 50)

        if not training_data:
            return {"success": False, "error": "training_data required"}

        # Initialize planner
        self._ensure_planner_loaded(num_tools)
        self._ensure_embedding_model_loaded()

        # Initialize optimizer
        self.optimizer = optax.adam(learning_rate=learning_rate)
        self.opt_state = self.optimizer.init(self.planner_params)

        # Define loss function
        def loss_fn(params, query_emb, target_quality):
            output = self.planner.apply({"params": params}, query_emb, training=True, rngs={"dropout": self.rng})
            quality = output["plan_quality"]
            loss = jnp.mean((quality - target_quality) ** 2)
            return loss

        # Training loop
        for epoch in range(epochs):
            total_loss = 0.0

            for query, optimal_plan, target_quality in training_data:
                # Get query embedding
                query_emb = self._get_embeddings([query])
                query_emb = query_emb[jnp.newaxis, :]
                target = jnp.array([[target_quality]], dtype=jnp.float32)

                # Compute loss and gradients
                loss, grads = jax.value_and_grad(loss_fn)(
                    self.planner_params, query_emb, target_quality
                )

                # Update parameters
                updates, self.opt_state = self.optimizer.update(grads, self.opt_state)
                self.planner_params = optax.apply_updates(self.planner_params, updates)

                total_loss += float(loss)

            avg_loss = total_loss / len(training_data)
            if epoch % 5 == 0:
                logger.info(
                    "Gradient plan optimizer training progress",
                    extra={
                        "module_name": "gradient_plan_optimizer",
                        "epoch": epoch,
                        "avg_loss": float(avg_loss),
                    },
                )

        return {"success": True, "epochs": epochs, "final_loss": avg_loss}

    def _load_model(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """Load trained planner"""
        model_path = params.get("model_path")
        num_tools = params.get("num_tools", 50)

        if not model_path:
            return {"success": False, "error": "model_path required"}

        try:
            with open(model_path, "rb") as f:
                bytes_data = f.read()

            # Initialize planner
            self._ensure_planner_loaded(num_tools)

            # Deserialize parameters
            self.planner_params = serialization.from_bytes(self.planner_params, bytes_data)

            # Load metadata if available
            import pickle
            try:
                with open(model_path + ".meta", "rb") as f:
                    metadata = pickle.load(f)
                if "tool_names" in metadata:
                    self.tool_names = metadata["tool_names"]
            except FileNotFoundError:
                pass

            return {"success": True}
        except Exception as e:
            return {"success": False, "error": f"Failed to load: {str(e)}"}

    def _save_model(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """Save trained planner"""
        model_path = params.get("model_path")

        if not model_path:
            return {"success": False, "error": "model_path required"}

        if self.planner_params is None:
            return {"success": False, "error": "Planner not initialized"}

        try:
            # Serialize parameters
            bytes_output = serialization.to_bytes(self.planner_params)

            with open(model_path, "wb") as f:
                f.write(bytes_output)

            # Save metadata
            import pickle
            metadata = {"tool_names": self.tool_names}
            with open(model_path + ".meta", "wb") as f:
                pickle.dump(metadata, f)

            return {"success": True, "model_path": model_path}
        except Exception as e:
            return {"success": False, "error": f"Failed to save: {str(e)}"}
