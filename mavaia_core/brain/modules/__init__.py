"""
Brain Modules Package - Plug-and-play intelligence modules

Module discovery: Auto-discovers all modules on import

This package automatically discovers and registers all brain modules when imported.
New modules (like lora_loader.py and lora_inference.py) are automatically discovered
and made available without manual registration.

Features:
- Automatic module discovery via ModuleRegistry
- Plug-and-play architecture - just add a new .py file
- No code changes needed to add new modules
- Modules are discovered and initialized on package import
"""

import sys
import os
from pathlib import Path

# Ensure this directory is in the path for relative imports
_current_dir = Path(__file__).parent
if str(_current_dir) not in sys.path:
    sys.path.insert(0, str(_current_dir))

from mavaia_core.brain.registry import ModuleRegistry

# Lazy discovery - modules are discovered on first get_module() call
# This avoids verbose logging and unnecessary work on import
# Modules are automatically discovered when first needed via get_module()
#
# Available modules include:
# - lora_loader.py (LoRA adapter loading)
# - lora_inference.py (LoRA inference)
# - personality_response.py (Personality generation)
# - reasoning.py (Reasoning tasks)
# - embeddings.py (Embedding generation)
# - model_optimizer.py (PyTorch model optimization: quantization, pruning, compression)
# - tool_routing_model.py (Neural network for learned tool selection and routing)
# - plan_optimizer.py (Neural network for plan optimization and scoring)
# - custom_reasoning_networks.py (Custom neural architectures for specialized reasoning)
# - reinforcement_learning_agent.py (RL agent for adaptive decision-making)
# - gradient_plan_optimizer.py (Gradient-based plan optimization using differentiable planning)
# - neural_architecture_search.py (Neural Architecture Search for automatic architecture discovery)
# - And any other modules that inherit from BaseBrainModule
#
# Note: discover_modules() is no longer called on import to reduce startup overhead

__all__ = ["ModuleRegistry"]
