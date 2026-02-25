from __future__ import annotations
"""
Reinforcement Learning Agent
RL-based agent for optimizing decision-making over time
"""

from typing import Dict, Any, Optional, List, Tuple
import logging

from mavaia_core.brain.base_module import BaseBrainModule, ModuleMetadata
from mavaia_core.exceptions import InvalidParameterError, ModuleInitializationError, ModuleOperationError

logger = logging.getLogger(__name__)

# Optional imports - handle gracefully if dependencies not available
try:
    import numpy as np
    NUMPY_AVAILABLE = True
except ImportError:
    NUMPY_AVAILABLE = False
    np = None

# Optional imports
try:
    import jax
    import jax.numpy as jnp
    import flax.linen as nn
    from flax import serialization
    import optax
    import distrax
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
    distrax = None
    FlaxAutoModel = None
    FlaxAutoTokenizer = None

if JAX_AVAILABLE:

    class PolicyNetwork(nn.Module):
        """
        Policy network for learning optimal actions
        Outputs action probabilities given state
        """

        state_dim: int = 768
        action_dim: int = 50
        hidden_dim: int = 512
        dropout: float = 0.1

        @nn.compact
        def __call__(self, state: "jnp.ndarray", training: bool = False) -> Tuple["jnp.ndarray", "jnp.ndarray"]:
            """
            Forward pass

            Args:
                state: State representation (batch_size, state_dim)
                training: Whether in training mode

            Returns:
                action_probs: Action probabilities (batch_size, action_dim)
                action_log_probs: Log probabilities for training
            """
            # State encoder
            x = nn.Dense(self.hidden_dim)(state)
            x = nn.relu(x)
            x = nn.Dropout(rate=self.dropout, deterministic=not training)(x)
            x = nn.Dense(self.hidden_dim)(x)
            encoded = nn.relu(x)

            # Policy head (outputs action probabilities)
            x_policy = nn.Dense(self.hidden_dim // 2)(encoded)
            x_policy = nn.relu(x_policy)
            x_policy = nn.Dropout(rate=self.dropout, deterministic=not training)(x_policy)
            action_logits = nn.Dense(self.action_dim)(x_policy)
            action_probs = nn.softmax(action_logits, axis=-1)
            action_log_probs = jnp.log(action_probs + 1e-8)  # Avoid log(0)

            return action_probs, action_log_probs

    class ValueNetwork(nn.Module):
        """
        Value network for estimating long-term rewards
        Estimates expected cumulative reward from a state
        """

        state_dim: int = 768
        hidden_dim: int = 512
        dropout: float = 0.1

        @nn.compact
        def __call__(self, state: "jnp.ndarray", training: bool = False) -> "jnp.ndarray":
            """
            Estimate state value

            Args:
                state: State representation (batch_size, state_dim)
                training: Whether in training mode

            Returns:
                value: Estimated value (batch_size, 1)
            """
            # State encoder
            x = nn.Dense(self.hidden_dim)(state)
            x = nn.relu(x)
            x = nn.Dropout(rate=self.dropout, deterministic=not training)(x)
            x = nn.Dense(self.hidden_dim)(x)
            encoded = nn.relu(x)

            # Value head
            x_value = nn.Dense(self.hidden_dim // 2)(encoded)
            x_value = nn.relu(x_value)
            x_value = nn.Dropout(rate=self.dropout, deterministic=not training)(x_value)
            value = nn.Dense(1)(x_value)

            return value

    class PPOAgent:
        """
        Proximal Policy Optimization (PPO) agent
        Trains policy and value networks using PPO algorithm
        """

        def __init__(
            self,
            state_dim: int = 768,
            action_dim: int = 50,
            hidden_dim: int = 512,
            lr: float = 3e-4,
            gamma: float = 0.99,
            eps_clip: float = 0.2,
        ):
            self.state_dim = state_dim
            self.action_dim = action_dim
            self.gamma = gamma
            self.eps_clip = eps_clip

            # Initialize networks
            self.policy = PolicyNetwork(state_dim=state_dim, action_dim=action_dim, hidden_dim=hidden_dim)
            self.value = ValueNetwork(state_dim=state_dim, hidden_dim=hidden_dim)

            # Initialize parameters
            dummy_state = jnp.zeros((1, state_dim))
            self.rng = jax.random.PRNGKey(0)
            self.rng, policy_rng = jax.random.split(self.rng)
            self.policy_params = self.policy.init(policy_rng, dummy_state, training=False)
            self.rng, value_rng = jax.random.split(self.rng)
            self.value_params = self.value.init(value_rng, dummy_state, training=False)

            # Initialize optimizers
            self.policy_optimizer = optax.adam(learning_rate=lr)
            self.value_optimizer = optax.adam(learning_rate=lr)
            self.policy_opt_state = self.policy_optimizer.init(self.policy_params)
            self.value_opt_state = self.value_optimizer.init(self.value_params)

            # Experience buffer
            self.states = []
            self.actions = []
            self.rewards = []
            self.log_probs = []
            self.values = []
            self.dones = []

        def select_action(
            self, state: "jnp.ndarray", deterministic: bool = False, rng: Optional["jax.random.PRNGKey"] = None
        ) -> Tuple[int, "jnp.ndarray", "jnp.ndarray"]:
            """
            Select action and store experience

            Args:
                state: State representation
                deterministic: If True, select deterministically
                rng: Random key for sampling

            Returns:
                action: Selected action
                log_prob: Log probability of action
                value: Estimated value
            """
            if rng is None:
                self.rng, rng = jax.random.split(self.rng)

            # Get action probabilities and value
            action_probs, action_log_probs = self.policy.apply(
                {"params": self.policy_params}, state, training=False
            )
            value = self.value.apply(
                {"params": self.value_params}, state, training=False
            )

            # Select action
            if deterministic:
                action = int(jnp.argmax(action_probs[0]))
                log_prob = action_log_probs[0, action]
            else:
                dist = distrax.Categorical(probs=action_probs[0])
                action = int(dist.sample(seed=rng))
                log_prob = action_log_probs[0, action]

            # Store experience
            self.states.append(state)
            self.actions.append(action)
            self.log_probs.append(log_prob)
            self.values.append(value[0, 0])

            return action, log_prob, value[0, 0]

        def compute_returns(
            self, rewards: List[float], dones: List[bool]
        ) -> "jnp.ndarray":
            """
            Compute discounted returns

            Args:
                rewards: List of rewards
                dones: List of done flags

            Returns:
                returns: Discounted returns
            """
            returns = []
            G = 0.0

            for reward, done in zip(reversed(rewards), reversed(dones)):
                if done:
                    G = 0.0
                G = reward + self.gamma * G
                returns.insert(0, G)

            return jnp.array(returns, dtype=jnp.float32)

        def update(self, epochs: int = 4):
            """
            Update policy and value networks using PPO

            Args:
                epochs: Number of update epochs
            """
            if len(self.states) == 0:
                return

            # Convert to arrays
            states = jnp.concatenate([s for s in self.states], axis=0)
            actions = jnp.array(self.actions)
            old_log_probs = jnp.array(self.log_probs)
            old_values = jnp.array(self.values)

            # Compute returns and advantages
            returns = self.compute_returns(self.rewards, self.dones)
            advantages = returns - old_values
            advantages = (advantages - jnp.mean(advantages)) / (
                jnp.std(advantages) + 1e-8
            )  # Normalize

            # Define loss functions
            def policy_loss_fn(params, states, actions, old_log_probs, advantages):
                action_probs, action_log_probs = self.policy.apply(
                    {"params": params}, states, training=True, rngs={"dropout": self.rng}
                )
                new_log_probs = action_log_probs[jnp.arange(len(actions)), actions]

                # Compute ratio
                ratio = jnp.exp(new_log_probs - old_log_probs)

                # Compute policy loss (PPO clipped objective)
                surr1 = ratio * advantages
                surr2 = (
                    jnp.clip(ratio, 1 - self.eps_clip, 1 + self.eps_clip)
                    * advantages
                )
                loss = -jnp.mean(jnp.minimum(surr1, surr2))
                return loss

            def value_loss_fn(params, states, returns):
                values = self.value.apply(
                    {"params": params}, states, training=True, rngs={"dropout": self.rng}
                )
                values = values.squeeze()
                loss = jnp.mean((values - returns) ** 2)
                return loss

            # Update for multiple epochs
            for epoch in range(epochs):
                # Update policy
                policy_loss, policy_grads = jax.value_and_grad(policy_loss_fn)(
                    self.policy_params, states, actions, old_log_probs, advantages
                )
                policy_updates, self.policy_opt_state = self.policy_optimizer.update(
                    policy_grads, self.policy_opt_state
                )
                self.policy_params = optax.apply_updates(
                    self.policy_params, policy_updates
                )

                # Update value
                value_loss, value_grads = jax.value_and_grad(value_loss_fn)(
                    self.value_params, states, returns
                )
                value_updates, self.value_opt_state = self.value_optimizer.update(
                    value_grads, self.value_opt_state
                )
                self.value_params = optax.apply_updates(
                    self.value_params, value_updates
                )

            # Clear buffer
            self.states = []
            self.actions = []
            self.rewards = []
            self.log_probs = []
            self.values = []
            self.dones = []

        def add_reward(self, reward: float, done: bool = False):
            """Add reward to experience buffer"""
            self.rewards.append(reward)
            self.dones.append(done)


class ReinforcementLearningModule(BaseBrainModule):
    """Reinforcement learning agent for adaptive decision-making"""

    def __init__(self):
        super().__init__()
        self.agent: Optional[PPOAgent] = None
        self.embedding_model = None
        self.embedding_params = None
        self.tokenizer = None
        self.action_names: List[str] = []

    @property
    def metadata(self) -> ModuleMetadata:
        return ModuleMetadata(
            name="reinforcement_learning",
            version="1.0.0",
            description="Reinforcement learning agent for optimizing decision-making",
            operations=[
                "select_action",
                "add_reward",
                "update_policy",
                "get_value",
                "train_episode",
                "load_agent",
                "save_agent",
            ],
            dependencies=["jax", "flax", "optax", "distrax", "transformers"],
            model_required=True,
        )

    def initialize(self) -> bool:
        """Initialize the module"""
        if not NUMPY_AVAILABLE:
            logger.warning(
                "NumPy not available; reinforcement_learning may be unavailable",
                extra={"module_name": "reinforcement_learning"},
            )
            return True  # Can still work with basic fallback

        if not JAX_AVAILABLE:
            logger.warning(
                "JAX not available; reinforcement_learning may be unavailable",
                extra={"module_name": "reinforcement_learning"},
            )
            return True  # Can still work with basic fallback

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
                    "Failed to load Flax embedding model for reinforcement_learning",
                    exc_info=True,
                    extra={"module_name": "reinforcement_learning", "error_type": type(e).__name__},
                )
                raise ModuleInitializationError(
                    module_name="reinforcement_learning",
                    reason="Failed to load required Flax embedding model/tokenizer",
                ) from e

    def _get_embeddings(self, texts: List[str]) -> "jnp.ndarray":
        """Get embeddings for texts using Flax model"""
        self._ensure_embedding_model_loaded()

        # Use Flax model only
        if not isinstance(self.embedding_model, FlaxAutoModel):
            raise ModuleOperationError(
                module_name="reinforcement_learning",
                operation="get_embeddings",
                reason="Only Flax models are supported for embeddings",
            )
        
        inputs = self.tokenizer(
            texts, return_tensors="jax", padding=True, truncation=True
        )
        outputs = self.embedding_model(**inputs, params=self.embedding_params)
        # Mean pooling
        embeddings = jnp.mean(outputs.last_hidden_state, axis=1)
        
        return embeddings

    def execute(self, operation: str, params: Dict[str, Any]) -> Dict[str, Any]:
        """Execute an RL operation"""
        if not NUMPY_AVAILABLE:
            return {"success": False, "error": "NumPy not available"}

        if not JAX_AVAILABLE:
            return {"success": False, "error": "JAX not available"}

        try:
            if operation == "select_action":
                return self._select_action(params)
            elif operation == "add_reward":
                return self._add_reward(params)
            elif operation == "update_policy":
                return self._update_policy(params)
            elif operation == "get_value":
                return self._get_value(params)
            elif operation == "train_episode":
                return self._train_episode(params)
            elif operation == "load_agent":
                return self._load_agent(params)
            elif operation == "save_agent":
                return self._save_agent(params)
            else:
                raise InvalidParameterError(
                    parameter="operation",
                    value=operation,
                    reason="Unknown operation for reinforcement_learning",
                )
        except (InvalidParameterError, ModuleInitializationError, ModuleOperationError):
            raise
        except Exception as e:
            logger.debug(
                "Unhandled reinforcement_learning execution error",
                exc_info=True,
                extra={"module_name": "reinforcement_learning", "operation": str(operation), "error_type": type(e).__name__},
            )
            return {"success": False, "error": "Reinforcement learning operation failed"}

    def _select_action(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """Select action using policy network"""
        state_text = params.get("state_text")
        action_names = params.get("action_names", [])
        deterministic = params.get("deterministic", False)

        if not state_text:
            return {"success": False, "error": "state_text required"}

        # Initialize agent if needed
        if self.agent is None:
            if action_names:
                self.action_names = action_names
            action_dim = len(self.action_names) if self.action_names else 50
            self.agent = PPOAgent(
                state_dim=384,  # all-MiniLM-L6-v2 dimension
                action_dim=action_dim,
            )

        # Get state embedding
        state_emb = self._get_embeddings([state_text])
        state_emb = state_emb[jnp.newaxis, :]  # Add batch dimension

        # Select action
        action, log_prob, value = self.agent.select_action(state_emb, deterministic)

        action_name = (
            self.action_names[action]
            if action < len(self.action_names)
            else f"action_{action}"
        )

        return {
            "success": True,
            "action": action,
            "action_name": action_name,
            "log_probability": float(log_prob),
            "value": float(value),
        }

    def _add_reward(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """Add reward to experience buffer"""
        reward = params.get("reward")
        done = params.get("done", False)

        if reward is None:
            return {"success": False, "error": "reward required"}

        if self.agent is None:
            return {"success": False, "error": "Agent not initialized"}

        self.agent.add_reward(float(reward), done)

        return {"success": True, "reward": reward, "done": done}

    def _update_policy(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """Update policy using collected experience"""
        epochs = params.get("epochs", 4)

        if self.agent is None:
            return {"success": False, "error": "Agent not initialized"}

        self.agent.update(epochs=epochs)

        return {"success": True, "epochs": epochs}

    def _get_value(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """Get estimated value for a state"""
        state_text = params.get("state_text")

        if not state_text:
            return {"success": False, "error": "state_text required"}

        if self.agent is None:
            return {"success": False, "error": "Agent not initialized"}

        # Get state embedding
        state_emb = self._get_embeddings([state_text])
        state_emb = state_emb[jnp.newaxis, :]

        # Get value
        value = self.agent.value.apply(
            {"params": self.agent.value_params}, state_emb, training=False
        )

        return {"success": True, "value": float(value[0, 0])}

    def _train_episode(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """Train agent on a complete episode"""
        episode_data = params.get(
            "episode_data", []
        )  # List of (state, action, reward, done)
        epochs = params.get("epochs", 4)

        if not episode_data:
            return {"success": False, "error": "episode_data required"}

        # Initialize agent if needed
        if self.agent is None:
            action_dim = params.get("action_dim", 50)
            self.agent = PPOAgent(
                state_dim=384, action_dim=action_dim
            )

        # Process episode
        for state_text, action, reward, done in episode_data:
            # Get state embedding
            state_emb = self._get_embeddings([state_text])
            state_emb = state_emb[jnp.newaxis, :]

            # Select action (or use provided action)
            if action is None:
                selected_action, _, _ = self.agent.select_action(state_emb)
            else:
                # Store state and action manually
                self.agent.states.append(state_emb)
                self.agent.actions.append(action)
                # Get log prob for this action
                action_probs, action_log_probs = self.agent.policy.apply(
                    {"params": self.agent.policy_params}, state_emb, training=False
                )
                self.agent.log_probs.append(action_log_probs[0, action])
                # Get value
                value = self.agent.value.apply(
                    {"params": self.agent.value_params}, state_emb, training=False
                )
                self.agent.values.append(value[0, 0])

            # Add reward
            self.agent.add_reward(reward, done)

        # Update policy
        self.agent.update(epochs=epochs)

        return {
            "success": True,
            "episode_length": len(episode_data),
            "total_reward": sum(r for _, _, r, _ in episode_data),
        }

    def _load_agent(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """Load trained agent"""
        agent_path = params.get("agent_path")
        action_dim = params.get("action_dim", 50)

        if not agent_path:
            return {"success": False, "error": "agent_path required"}

        try:
            with open(agent_path, "rb") as f:
                bytes_data = f.read()

            # Initialize agent
            self.agent = PPOAgent(
                state_dim=384, action_dim=action_dim
            )

            # Deserialize parameters
            self.agent.policy_params = serialization.from_bytes(
                self.agent.policy_params, bytes_data
            )

            # Load value params and metadata if available
            import pickle
            try:
                with open(agent_path + ".meta", "rb") as f:
                    metadata = pickle.load(f)
                if "value_params" in metadata:
                    # Deserialize value params
                    value_bytes = metadata["value_params"]
                    self.agent.value_params = serialization.from_bytes(
                        self.agent.value_params, value_bytes
                    )
                if "action_names" in metadata:
                    self.action_names = metadata["action_names"]
            except FileNotFoundError:
                pass

            return {"success": True}
        except Exception as e:
            return {"success": False, "error": f"Failed to load: {str(e)}"}

    def _save_agent(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """Save trained agent"""
        agent_path = params.get("agent_path")

        if not agent_path:
            return {"success": False, "error": "agent_path required"}

        if self.agent is None:
            return {"success": False, "error": "Agent not initialized"}

        try:
            # Serialize policy parameters
            policy_bytes = serialization.to_bytes(self.agent.policy_params)
            value_bytes = serialization.to_bytes(self.agent.value_params)

            with open(agent_path, "wb") as f:
                f.write(policy_bytes)

            # Save metadata
            import pickle
            metadata = {
                "value_params": value_bytes,
                "action_names": self.action_names,
            }
            with open(agent_path + ".meta", "wb") as f:
                pickle.dump(metadata, f)

            return {"success": True, "agent_path": agent_path}
        except Exception as e:
            return {"success": False, "error": f"Failed to save: {str(e)}"}
