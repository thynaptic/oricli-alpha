"""
Tool Routing Model
Neural network for learned tool selection and routing based on query characteristics
"""

from typing import Dict, Any, Optional, List, Tuple
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

    class ToolSelectionModel(nn.Module):
        """
        Neural network for predicting which tools to use for a given query
        """

        input_dim: int = 384  # Embedding dimension
        hidden_dim: int = 256
        num_tools: int = 50
        dropout: float = 0.1

        @nn.compact
        def __call__(
            self, query_embeddings: "jnp.ndarray", training: bool = False
        ) -> Tuple["jnp.ndarray", "jnp.ndarray", "jnp.ndarray"]:
            """
            Forward pass

            Args:
                query_embeddings: Query embeddings (batch_size, input_dim)
                training: Whether in training mode (for dropout)

            Returns:
                tool_probs: Tool selection probabilities (batch_size, num_tools)
                ordering_probs: Tool ordering probabilities (batch_size, num_tools)
                confidence: Confidence scores (batch_size, 1)
            """
            # Query encoder
            x = nn.Dense(self.hidden_dim)(query_embeddings)
            x = nn.relu(x)
            x = nn.Dropout(rate=self.dropout, deterministic=not training)(x)
            x = nn.Dense(self.hidden_dim)(x)
            encoded = nn.relu(x)

            # Tool selection head (binary classification per tool)
            x_tool = nn.Dense(self.hidden_dim // 2)(encoded)
            x_tool = nn.relu(x_tool)
            x_tool = nn.Dropout(rate=self.dropout, deterministic=not training)(x_tool)
            tool_probs = nn.sigmoid(nn.Dense(self.num_tools)(x_tool))

            # Tool ordering head (predicts execution order)
            x_order = nn.Dense(self.hidden_dim // 2)(encoded)
            x_order = nn.relu(x_order)
            x_order = nn.Dropout(rate=self.dropout, deterministic=not training)(x_order)
            ordering_probs = nn.softmax(nn.Dense(self.num_tools)(x_order), axis=-1)

            # Confidence scorer
            x_conf = nn.Dense(self.hidden_dim // 4)(encoded)
            x_conf = nn.relu(x_conf)
            confidence = nn.sigmoid(nn.Dense(1)(x_conf))

            return tool_probs, ordering_probs, confidence


class ToolRoutingModule(BaseBrainModule):
    """Neural network-based tool selection and routing"""

    def __init__(self):
        self.model_params: Optional[Dict[str, Any]] = None
        self.model: Optional[ToolSelectionModel] = None
        self.tokenizer: Optional[Any] = None
        self.embedding_model: Optional[Any] = None
        self.embedding_params: Optional[Dict[str, Any]] = None
        self.tool_names: List[str] = []
        self.is_trained = False
        self.optimizer: Optional[optax.GradientTransformation] = None
        self.opt_state: Optional[Any] = None
        self.rng = None

    @property
    def metadata(self) -> ModuleMetadata:
        return ModuleMetadata(
            name="tool_routing",
            version="1.0.0",
            description="Neural network for learned tool selection and routing",
            operations=[
                "predict_tools",
                "predict_ordering",
                "score_confidence",
                "train_model",
                "load_model",
                "save_model",
            ],
            dependencies=["jax", "flax", "optax", "transformers"],
            model_required=True,
        )

    def initialize(self) -> bool:
        """Initialize the module"""
        if not JAX_AVAILABLE:
            print("[ToolRoutingModule] JAX not available", file=sys.stderr)
            return False

        # Initialize RNG
        self.rng = jax.random.PRNGKey(0)

        return True

    def execute(self, operation: str, params: Dict[str, Any]) -> Dict[str, Any]:
        """Execute a routing operation"""
        if not JAX_AVAILABLE:
            return {"success": False, "error": "JAX not available"}

        try:
            if operation == "predict_tools":
                return self._predict_tools(params)
            elif operation == "predict_ordering":
                return self._predict_ordering(params)
            elif operation == "score_confidence":
                return self._score_confidence(params)
            elif operation == "train_model":
                return self._train_model(params)
            elif operation == "load_model":
                return self._load_model(params)
            elif operation == "save_model":
                return self._save_model(params)
            else:
                raise ValueError(f"Unknown operation: {operation}")
        except Exception as e:
            return {"success": False, "error": str(e)}

    def _ensure_embedding_model_loaded(self):
        """Lazy load embedding model using Flax backend"""
        if self.embedding_model is None or self.tokenizer is None:
            try:
                # Use FlaxAutoModel for embeddings (all-MiniLM-L6-v2 equivalent)
                # Using a model that has Flax support
                model_name = "sentence-transformers/all-MiniLM-L6-v2"
                
                # Try to load Flax model, fallback to PyTorch if needed
                try:
                    self.tokenizer = FlaxAutoTokenizer.from_pretrained(model_name)
                    self.embedding_model = FlaxAutoModel.from_pretrained(model_name)
                    self.embedding_params = self.embedding_model.params
                except Exception:
                    # Fallback: use transformers with JAX conversion
                    from transformers import AutoTokenizer, AutoModel
                    self.tokenizer = AutoTokenizer.from_pretrained(model_name)
                    pt_model = AutoModel.from_pretrained(model_name)
                    # Convert PyTorch model to JAX (simplified - in production use proper conversion)
                    # For now, we'll use a workaround with mean pooling
                    self.embedding_model = pt_model
                    self.embedding_params = None
                    
            except Exception as e:
                print(
                    f"[ToolRoutingModule] Failed to load embedding model: {e}",
                    file=sys.stderr,
                )
                raise

    def _get_embeddings(self, texts: List[str]) -> "jnp.ndarray":
        """Get embeddings for texts using Flax model"""
        self._ensure_embedding_model_loaded()
        
        if isinstance(self.embedding_model, FlaxAutoModel):
            # Use Flax model
            inputs = self.tokenizer(
                texts, return_tensors="jax", padding=True, truncation=True
            )
            outputs = self.embedding_model(**inputs, params=self.embedding_params)
            # Mean pooling
            embeddings = jnp.mean(outputs.last_hidden_state, axis=1)
        else:
            # Fallback: use PyTorch model and convert to JAX
            inputs = self.tokenizer(
                texts, return_tensors="pt", padding=True, truncation=True
            )
            with jax.default_device(jax.devices()[0]):
                outputs = self.embedding_model(**inputs)
                # Mean pooling
                embeddings_pt = outputs.last_hidden_state.mean(dim=1)
                # Convert to JAX array
                embeddings = jnp.array(embeddings_pt.detach().cpu().numpy())
        
        return embeddings

    def _ensure_model_loaded(self):
        """Lazy load routing model"""
        if self.model is None or self.model_params is None:
            # Initialize default model if not trained
            if not self.is_trained:
                # Get tool count from registry or default
                num_tools = len(self.tool_names) if self.tool_names else 50
                self.model = ToolSelectionModel(
                    input_dim=384,  # all-MiniLM-L6-v2 dimension
                    hidden_dim=256,
                    num_tools=num_tools,
                )
                # Initialize parameters
                dummy_input = jnp.zeros((1, 384))
                self.rng, init_rng = jax.random.split(self.rng)
                self.model_params = self.model.init(init_rng, dummy_input, training=False)
            else:
                raise ValueError("Model not loaded. Call load_model first.")

    def _predict_tools(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """
        Predict which tools to use for a query

        Args:
            query: User query string
            tool_names: List of available tool names
            threshold: Probability threshold for tool selection (default: 0.5)

        Returns:
            Dict with predicted tools and probabilities
        """
        query = params.get("query")
        tool_names = params.get("tool_names", [])
        threshold = params.get("threshold", 0.5)

        if not query:
            return {"success": False, "error": "query required"}

        # Update tool names if provided
        if tool_names:
            self.tool_names = tool_names
            # Reinitialize model if tool count changed
            if self.model and self.model.num_tools != len(tool_names):
                num_tools = len(tool_names)
                self.model = ToolSelectionModel(
                    input_dim=384, hidden_dim=256, num_tools=num_tools
                )
                dummy_input = jnp.zeros((1, 384))
                self.rng, init_rng = jax.random.split(self.rng)
                self.model_params = self.model.init(init_rng, dummy_input, training=False)

        # Load models if needed
        self._ensure_model_loaded()

        # Get query embedding
        query_embedding = self._get_embeddings([query])
        query_embedding = query_embedding[jnp.newaxis, :]  # Add batch dimension

        # Predict
        tool_probs, ordering_probs, confidence = self.model.apply(
            {"params": self.model_params}, query_embedding, training=False
        )

        # Extract predictions
        tool_probs_np = jnp.asarray(tool_probs[0])
        confidence_score = float(confidence[0, 0])

        # Select tools above threshold
        selected_tools = []
        for i, prob in enumerate(tool_probs_np):
            if prob >= threshold and i < len(self.tool_names):
                selected_tools.append(
                    {"tool": self.tool_names[i], "probability": float(prob)}
                )

        # Sort by probability
        selected_tools.sort(key=lambda x: x["probability"], reverse=True)

        return {
            "success": True,
            "selected_tools": selected_tools,
            "all_probabilities": {
                name: float(prob)
                for name, prob in zip(self.tool_names, tool_probs_np)
                if prob > 0.1
            },
            "confidence": confidence_score,
        }

    def _predict_ordering(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """
        Predict optimal execution order for tools

        Args:
            query: User query string
            tool_names: List of tools to order

        Returns:
            Dict with suggested execution order
        """
        query = params.get("query")
        tool_names = params.get("tool_names", [])

        if not query:
            return {"success": False, "error": "query required"}

        if not tool_names:
            return {"success": False, "error": "tool_names required"}

        # Load models if needed
        self._ensure_model_loaded()

        # Get query embedding
        query_embedding = self._get_embeddings([query])
        query_embedding = query_embedding[jnp.newaxis, :]

        # Predict
        tool_probs, ordering_probs, confidence = self.model.apply(
            {"params": self.model_params}, query_embedding, training=False
        )

        # Extract ordering
        ordering_probs_np = jnp.asarray(ordering_probs[0])

        # Map to tool names and sort
        tool_order = [
            (tool_names[i], float(ordering_probs_np[i]))
            for i in range(min(len(tool_names), len(ordering_probs_np)))
        ]
        tool_order.sort(key=lambda x: x[1], reverse=True)

        return {
            "success": True,
            "ordered_tools": [tool for tool, _ in tool_order],
            "ordering_scores": {tool: score for tool, score in tool_order},
            "confidence": float(confidence[0, 0]),
        }

    def _score_confidence(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """
        Score confidence for a tool combination

        Args:
            query: User query string
            tool_names: List of tools to score

        Returns:
            Dict with confidence score
        """
        query = params.get("query")
        tool_names = params.get("tool_names", [])

        if not query:
            return {"success": False, "error": "query required"}

        # Load models if needed
        self._ensure_model_loaded()

        # Get query embedding
        query_embedding = self._get_embeddings([query])
        query_embedding = query_embedding[jnp.newaxis, :]

        # Predict
        tool_probs, ordering_probs, confidence = self.model.apply(
            {"params": self.model_params}, query_embedding, training=False
        )

        confidence_score = float(confidence[0, 0])

        return {
            "success": True,
            "confidence": confidence_score,
            "interpretation": self._interpret_confidence(confidence_score),
        }

    def _interpret_confidence(self, score: float) -> str:
        """Interpret confidence score"""
        if score >= 0.8:
            return "high"
        elif score >= 0.5:
            return "medium"
        else:
            return "low"

    def _train_model(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """
        Train the routing model on historical data

        Args:
            training_data: List of (query, selected_tools, success) tuples
            epochs: Number of training epochs
            learning_rate: Learning rate
            batch_size: Batch size

        Returns:
            Dict with training results
        """
        training_data = params.get("training_data", [])
        epochs = params.get("epochs", 10)
        learning_rate = params.get("learning_rate", 1e-3)
        batch_size = params.get("batch_size", 32)

        if not training_data:
            return {"success": False, "error": "training_data required"}

        # Load embedding model
        self._ensure_embedding_model_loaded()

        # Initialize model if needed
        if self.model is None or self.model_params is None:
            # Infer number of tools from training data
            all_tools = set()
            for _, tools, _ in training_data:
                all_tools.update(tools)
            num_tools = len(all_tools)
            self.tool_names = sorted(list(all_tools))

            self.model = ToolSelectionModel(
                input_dim=384, hidden_dim=256, num_tools=num_tools
            )
            dummy_input = jnp.zeros((1, 384))
            self.rng, init_rng = jax.random.split(self.rng)
            self.model_params = self.model.init(init_rng, dummy_input, training=False)

        # Initialize optimizer
        self.optimizer = optax.adam(learning_rate=learning_rate)
        self.opt_state = self.optimizer.init(self.model_params)

        # Define loss function
        def loss_fn(params, query_embeddings, targets):
            """Compute loss for a batch"""
            tool_probs, _, _ = self.model.apply(
                {"params": params},
                query_embeddings,
                training=True,
                rngs={"dropout": self.rng},
            )
            # Binary cross-entropy loss
            loss = optax.sigmoid_binary_cross_entropy(tool_probs, targets).mean()
            return loss

        # Training loop
        for epoch in range(epochs):
            total_loss = 0.0

            # Simple batching
            for i in range(0, len(training_data), batch_size):
                batch = training_data[i : i + batch_size]

                # Encode queries
                queries = [item[0] for item in batch]
                query_embeddings = self._get_embeddings(queries)

                # Create targets (one-hot for selected tools)
                targets = jnp.zeros((len(batch), self.model.num_tools))
                for j, (_, tools, _) in enumerate(batch):
                    for tool in tools:
                        if tool in self.tool_names:
                            idx = self.tool_names.index(tool)
                            targets = targets.at[j, idx].set(1.0)

                # Compute loss and gradients
                loss, grads = jax.value_and_grad(loss_fn)(
                    self.model_params, query_embeddings, targets
                )

                # Update parameters
                updates, self.opt_state = self.optimizer.update(grads, self.opt_state)
                self.model_params = optax.apply_updates(self.model_params, updates)

                total_loss += float(loss)

            avg_loss = total_loss / (len(training_data) // batch_size + 1)
            if epoch % 5 == 0:
                print(
                    f"[ToolRoutingModule] Epoch {epoch}, Loss: {avg_loss:.4f}",
                    file=sys.stderr,
                )

        self.is_trained = True

        return {
            "success": True,
            "epochs": epochs,
            "final_loss": avg_loss,
            "num_tools": self.model.num_tools,
        }

    def _load_model(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """
        Load a trained model

        Args:
            model_path: Path to saved model
            tool_names: List of tool names (must match model)

        Returns:
            Dict with load result
        """
        model_path = params.get("model_path")
        tool_names = params.get("tool_names", [])

        if not model_path:
            return {"success": False, "error": "model_path required"}

        try:
            with open(model_path, "rb") as f:
                bytes_data = f.read()

            # Load metadata if available
            import pickle
            try:
                with open(model_path + ".meta", "rb") as f:
                    metadata = pickle.load(f)
                num_tools = metadata.get("num_tools", len(tool_names) if tool_names else 50)
                input_dim = metadata.get("input_dim", 384)
                hidden_dim = metadata.get("hidden_dim", 256)
                self.tool_names = metadata.get("tool_names", tool_names)
            except FileNotFoundError:
                # Fallback to defaults
                num_tools = len(tool_names) if tool_names else 50
                input_dim = 384
                hidden_dim = 256
                self.tool_names = tool_names

            # Reconstruct model
            self.model = ToolSelectionModel(
                input_dim=input_dim,
                hidden_dim=hidden_dim,
                num_tools=num_tools,
            )
            dummy_input = jnp.zeros((1, input_dim))
            self.rng, init_rng = jax.random.split(self.rng)
            temp_params = self.model.init(init_rng, dummy_input, training=False)

            # Deserialize parameters
            self.model_params = serialization.from_bytes(temp_params, bytes_data)
            self.is_trained = True

            return {
                "success": True,
                "num_tools": num_tools,
                "tool_names": self.tool_names,
            }

        except Exception as e:
            return {"success": False, "error": f"Failed to load model: {str(e)}"}

    def _save_model(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """
        Save the trained model

        Args:
            model_path: Path to save model

        Returns:
            Dict with save result
        """
        model_path = params.get("model_path")

        if not model_path:
            return {"success": False, "error": "model_path required"}

        if self.model_params is None:
            return {"success": False, "error": "No model to save"}

        try:
            # Serialize parameters
            bytes_output = serialization.to_bytes(self.model_params)

            with open(model_path, "wb") as f:
                f.write(bytes_output)

            # Save metadata
            import pickle
            metadata = {
                "num_tools": self.model.num_tools,
                "input_dim": self.model.input_dim,
                "hidden_dim": self.model.hidden_dim,
                "tool_names": self.tool_names,
            }
            with open(model_path + ".meta", "wb") as f:
                pickle.dump(metadata, f)

            return {
                "success": True,
                "model_path": model_path,
                "num_tools": self.model.num_tools,
            }

        except Exception as e:
            return {"success": False, "error": f"Failed to save model: {str(e)}"}
