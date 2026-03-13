from __future__ import annotations
"""
Adapter Router Module

Standalone module for dynamically selecting and loading specialized LoRA adapters
based on semantic input analysis. Foundation for the OricliAlpha Model Family.
"""

import json
from typing import Dict, Any, Optional, List
import logging
import time
import threading
from pathlib import Path
from collections import OrderedDict

from oricli_core.brain.base_module import BaseBrainModule, ModuleMetadata
from oricli_core.exceptions import (
    InvalidParameterError,
    ModuleInitializationError,
    ModuleOperationError,
)

logger = logging.getLogger(__name__)

# Lazy imports for heavy ML libraries
torch = None
nn = None
peft = None
PeftModel = None
huggingface_hub = None

def _lazy_import_ml():
    """Lazy import ML libraries only when needed"""
    global torch, nn, peft, PeftModel, huggingface_hub
    if torch is None:
        try:
            import torch as t
            import torch.nn as n
            torch = t
            nn = n
        except ImportError:
            logger.debug("torch not available")
            
    if peft is None:
        try:
            import peft as p
            from peft import PeftModel as PM
            peft = p
            PeftModel = PM
        except ImportError:
            logger.debug("peft not available")

    if huggingface_hub is None:
        try:
            import huggingface_hub as hf
            huggingface_hub = hf
        except ImportError:
            logger.debug("huggingface_hub not available")


class IntentClassifier:
    """Trainable linear classification head for intent mapping."""
    def __init__(self, input_dim: int, num_classes: int):
        _lazy_import_ml()
        if torch is None or nn is None:
            raise ImportError("PyTorch is required for IntentClassifier")
            
        self.model = nn.Sequential(
            nn.Linear(input_dim, 128),
            nn.ReLU(),
            nn.Dropout(0.1),
            nn.Linear(128, num_classes),
            nn.Softmax(dim=1)
        )
        
    def forward(self, x):
        return self.model(x)


class AdapterRouter(BaseBrainModule):
    """
    Module for routing inputs to specific LoRA adapters using semantic classification.
    Supports hybrid storage (Hugging Face Hub and S3).
    """
    
    def __init__(self):
        """Initialize adapter router module."""
        super().__init__()
        self.config = {}
        self._initialized = False
        # Use OrderedDict for LRU adapter management
        self._active_adapters: OrderedDict[str, Dict[str, Any]] = OrderedDict()
        self._routing_table: Dict[str, str] = {} # intent_id -> adapter_id
        self._intent_labels: List[str] = ["general", "math", "coding", "creative", "logic"]
        self._classifier: Optional[Any] = None
        self._embedding_dim = 384 # Default for all-MiniLM-L6-v2
        
        # VRAM Management: Max loaded adapters to keep warm
        self._max_adapters = 3
        self._lock = threading.Lock()
        
    @property
    def metadata(self) -> ModuleMetadata:
        """Return module metadata."""
        return ModuleMetadata(
            name="adapter_router",
            version="1.1.1",
            description="Dynamically routes inputs to specialized LoRA adapters with VRAM safety and async triggers",
            operations=[
                "route_input",
                "async_route",
                "load_adapter",
                "unload_adapter",
                "status",
                "train_router",
                "register_intent",
                "unregister_intent",
                "list_intents",
            ],
            dependencies=["torch", "peft", "huggingface_hub"],
            enabled=True,
            model_required=False,
        )
    
    def initialize(self) -> bool:
        """Initialize the module."""
        # Setup local cache directories
        cache_dir = Path(self.config.get("cache_dir", "models/adapter_cache"))
        cache_dir.mkdir(parents=True, exist_ok=True)
        
        # Load persisted config if available
        self._load_config()
        
        self._max_adapters = int(self.config.get("max_adapters", 3))
        
        # Initialize classifier if torch is available
        try:
            _lazy_import_ml()
            if torch:
                self._classifier = IntentClassifier(
                    self._embedding_dim, 
                    len(self._intent_labels)
                )
                # Load weights if they exist
                weights_path = Path(self.config.get("weights_path", "models/router_weights.pt"))
                if weights_path.exists():
                    # Simplified loading for now
                    pass
        except Exception as e:
            logger.warning(f"Failed to initialize intent classifier: {e}")
        
        self._initialized = True
        return True

    def _load_config(self):
        """Load persistent configuration from JSON."""
        config_path = Path(__file__).parent / "adapter_router_config.json"
        if config_path.exists():
            try:
                with open(config_path, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    self._routing_table = data.get("routing_table", {})
                    self._intent_labels = data.get("intent_labels", self._intent_labels)
                    self.config.update(data.get("config", {}))
                logger.info(f"Loaded AdapterRouter config from {config_path}")
            except Exception as e:
                logger.error(f"Failed to load AdapterRouter config: {e}")

    def _save_config(self):
        """Save configuration to JSON."""
        config_path = Path(__file__).parent / "adapter_router_config.json"
        try:
            data = {
                "routing_table": self._routing_table,
                "intent_labels": self._intent_labels,
                "config": self.config
            }
            with open(config_path, "w", encoding="utf-8") as f:
                json.dump(data, f, indent=2)
            logger.info(f"Saved AdapterRouter config to {config_path}")
        except Exception as e:
            logger.error(f"Failed to save AdapterRouter config: {e}")
    
    def execute(self, operation: str, params: Dict[str, Any]) -> Dict[str, Any]:
        """
        Execute module operation.
        
        Args:
            operation: Operation name
            params: Operation parameters
            
        Returns:
            Operation result dictionary
        """
        if not self._initialized:
            self.initialize()
            
        if operation == "route_input":
            return self._route_input(params)
        elif operation == "async_route":
            return self._async_route(params)
        elif operation == "load_adapter":
            return self._load_adapter(params)
        elif operation == "unload_adapter":
            return self._unload_adapter(params)
        elif operation == "status":
            return self._get_status()
        elif operation == "train_router":
            return self._train_router(params)
        elif operation == "register_intent":
            return self._register_intent(params)
        elif operation == "unregister_intent":
            return self._unregister_intent(params)
        elif operation == "list_intents":
            return self._list_intents()
        else:
            raise ValueError(f"Unknown operation: {operation}")

    def _get_embeddings(self, text: str) -> Optional[List[float]]:
        """Get embeddings from the internal service."""
        from oricli_core.brain.registry import ModuleRegistry
        emb_module = ModuleRegistry.get_module("embeddings")
        if not emb_module:
            logger.warning("Embeddings module not available for routing")
            return None
            
        res = emb_module.execute("generate", {"text": text})
        embedding = res.get("embedding")
        
        # Ensure we return a list of floats
        if isinstance(embedding, list):
            return embedding
        return None

    def _route_input(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """Classify input and suggest best adapter."""
        input_text = params.get("text")
        if not input_text:
            raise InvalidParameterError("Operation 'route_input' requires 'text' parameter")
            
        embedding = self._get_embeddings(input_text)
        
        if not embedding or self._classifier is None:
            # Fallback to base model
            return {
                "success": True,
                "intent": "general",
                "adapter_id": None,
                "confidence": 1.0,
                "metadata": {"info": "Fallback to base due to missing embeddings or classifier"}
            }
            
        _lazy_import_ml()
        with torch.no_grad():
            x = torch.tensor([embedding], dtype=torch.float32)
            probs = self._classifier.forward(x)
            conf, idx = torch.max(probs, dim=1)
            
        intent = self._intent_labels[idx.item()]
        adapter_id = self._routing_table.get(intent)
        
        # Log to experience replay
        self._log_routing_event(input_text, adapter_id, conf.item())
        
        # Auto-load the adapter if requested (Hot-Swap)
        if params.get("apply_routing", False) and adapter_id:
            load_res = self._load_adapter({"adapter_id": adapter_id})
            return {
                "success": True,
                "intent": intent,
                "adapter_id": adapter_id,
                "confidence": conf.item(),
                "applied": load_res.get("success", False),
                "metadata": {"probs": probs.tolist()[0]}
            }
        
        return {
            "success": True,
            "intent": intent,
            "adapter_id": adapter_id,
            "confidence": conf.item(),
            "metadata": {"probs": probs.tolist()[0]}
        }

    def _async_route(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """Trigger routing asynchronously to prep for next task."""
        # Use a thread to avoid blocking the main execution thread
        def task():
            try:
                # We want to get embeddings and intent ready
                self._route_input({**params, "apply_routing": True})
            except Exception as e:
                logger.error(f"Async pre-routing failed: {e}")

        thread = threading.Thread(target=task, daemon=True)
        thread.start()
        
        return {
            "success": True,
            "status": "triggered",
            "message": "Async routing calculation started in background"
        }

    def _register_intent(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """Register a new intent and map it to an adapter."""
        intent = params.get("intent")
        adapter_id = params.get("adapter_id")
        
        if not intent or not adapter_id:
            raise InvalidParameterError("Operation 'register_intent' requires 'intent' and 'adapter_id'")
            
        if intent not in self._intent_labels:
            self._intent_labels.append(intent)
            # Re-initialize classifier with new output dim
            self._classifier = IntentClassifier(self._embedding_dim, len(self._intent_labels))
            
        self._routing_table[intent] = adapter_id
        
        # Persist change
        self._save_config()
        
        return {
            "success": True,
            "intent": intent,
            "adapter_id": adapter_id,
            "total_intents": len(self._intent_labels)
        }

    def _unregister_intent(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """Unregister an intent."""
        intent = params.get("intent")
        if not intent:
            raise InvalidParameterError("Operation 'unregister_intent' requires 'intent'")
            
        if intent in self._routing_table:
            del self._routing_table[intent]
            # Persist change
            self._save_config()
            
        return {"success": True, "intent": intent}

    def _list_intents(self) -> Dict[str, Any]:
        """List all registered intents and their mappings."""
        return {
            "success": True,
            "intents": self._intent_labels,
            "routing_table": self._routing_table
        }

    def _get_base_model_module(self) -> Optional[BaseBrainModule]:
        """Get the neural_text_generator module which holds the base model."""
        from oricli_core.brain.registry import ModuleRegistry
        return ModuleRegistry.get_module("neural_text_generator")

    def _load_adapter(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """Load an adapter from HF or S3 using Hot-Swap set_adapter logic."""
        adapter_id = params.get("adapter_id")
        source = params.get("source", "hf") # "hf" or "s3"
        
        if not adapter_id:
            raise InvalidParameterError("Operation 'load_adapter' requires 'adapter_id'")
            
        with self._lock:
            # 1. PEFT Hot-Swap: Check if already active
            if adapter_id in self._active_adapters:
                # Move to end of OrderedDict (Mark as most recently used)
                self._active_adapters.move_to_end(adapter_id)
                
                # Ensure it's active in the model
                ntg = self._get_base_model_module()
                if ntg and hasattr(ntg, "transformer_model"):
                    base_model = ntg.transformer_model
                    if hasattr(base_model, "set_adapter"):
                        base_model.set_adapter(adapter_id)
                
                return {
                    "success": True,
                    "adapter_id": adapter_id,
                    "status": "active",
                    "info": "Hot-swapped to already loaded adapter"
                }

            _lazy_import_ml()
            ntg = self._get_base_model_module()
            if not ntg:
                raise ModuleOperationError("adapter_router", "Neural text generator module not found")
                
            base_model = getattr(ntg, "transformer_model", None)
            if base_model is None:
                raise ModuleOperationError("adapter_router", "Base transformer model not loaded in NTG")

            # 2. VRAM Management: Ensure capacity before loading new
            self._ensure_adapter_capacity(base_model)

            try:
                # Use PEFT to load adapter
                if PeftModel is None:
                    raise ImportError("PEFT not available")
                    
                if not isinstance(base_model, PeftModel):
                    # Initial wrap of base model
                    base_model = PeftModel.from_pretrained(base_model, adapter_id, adapter_name=adapter_id)
                    ntg.transformer_model = base_model
                else:
                    # Model already a PeftModel, just add new adapter
                    base_model.load_adapter(adapter_id, adapter_name=adapter_id)
                    base_model.set_adapter(adapter_id)
                
                self._active_adapters[adapter_id] = {
                    "source": source,
                    "loaded_at": time.time()
                }
                
                return {
                    "success": True,
                    "adapter_id": adapter_id,
                    "status": "active"
                }
                
            except Exception as e:
                logger.error(f"Failed to load adapter {adapter_id}: {e}")
                return {"success": False, "error": str(e)}

    def _ensure_adapter_capacity(self, base_model: Any):
        """Unload oldest adapters if limit is reached to prevent VRAM Ghosting."""
        while len(self._active_adapters) >= self._max_adapters:
            # Pop the oldest (first) item from OrderedDict
            old_adapter_id, info = self._active_adapters.popitem(last=False)
            
            try:
                if hasattr(base_model, "delete_adapter"):
                    base_model.delete_adapter(old_adapter_id)
                    logger.info(f"Unloaded adapter '{old_adapter_id}' to free VRAM")
                elif hasattr(base_model, "unload_adapter"):
                    # Fallback for older versions
                    base_model.unload_adapter(old_adapter_id)
            except Exception as e:
                logger.warning(f"Could not properly delete adapter '{old_adapter_id}': {e}")

    def _unload_adapter(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """Unload an active adapter or switch to base."""
        adapter_id = params.get("adapter_id")
        
        ntg = self._get_base_model_module()
        if not ntg or not hasattr(ntg, "transformer_model"):
            return {"success": False, "error": "Model not available"}
            
        base_model = ntg.transformer_model
        
        try:
            with self._lock:
                if adapter_id and adapter_id in self._active_adapters:
                    if hasattr(base_model, "delete_adapter"):
                        try:
                            base_model.delete_adapter(adapter_id)
                        except Exception as e:
                            logger.debug(f"Delete adapter failed (normal if already gone): {e}")
                    del self._active_adapters[adapter_id]
                
                # Switch back to base (disable all adapters)
                if hasattr(base_model, "disable_adapter"):
                    # Use context manager or method
                    if callable(base_model.disable_adapter):
                        base_model.disable_adapter()
                elif hasattr(base_model, "set_adapter"):
                    # PEFT fallback: try to set to a non-existent name to disable? 
                    # Better: base_model.base_model.eval() usually works if it's a wrapper
                    pass
                
            return {
                "success": True, 
                "active_adapters": list(self._active_adapters.keys()),
                "info": "Switched to base model (adapters disabled)"
            }
        except Exception as e:
            return {"success": False, "error": str(e)}

    def _get_status(self) -> Dict[str, Any]:
        """Return module status and active adapters."""
        return {
            "success": True,
            "active_adapters": list(self._active_adapters.keys()),
            "max_adapters": self._max_adapters,
            "routing_table": self._routing_table,
            "intents": self._intent_labels,
            "classifier_ready": self._classifier is not None,
            "initialized": self._initialized
        }

    def _train_router(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """Update router weights using supervised feedback."""
        text = params.get("text")
        target_intent = params.get("target_intent")
        learning_rate = params.get("learning_rate", 0.001)
        
        if not text or not target_intent:
            raise InvalidParameterError("Operation 'train_router' requires 'text' and 'target_intent'")
            
        if target_intent not in self._intent_labels:
            raise InvalidParameterError(f"Target intent '{target_intent}' not in registered intents")
            
        embedding = self._get_embeddings(text)
        if not embedding or self._classifier is None:
            return {"success": False, "error": "Embeddings or classifier not available"}
            
        _lazy_import_ml()
        import torch.optim as optim
        import torch.nn as nn
        
        # Prepare data
        x = torch.tensor([embedding], dtype=torch.float32)
        y = torch.tensor([self._intent_labels.index(target_intent)], dtype=torch.long)
        
        # Single training step
        optimizer = optim.Adam(self._classifier.model.parameters(), lr=learning_rate)
        criterion = nn.CrossEntropyLoss()
        
        self._classifier.model.train()
        optimizer.zero_grad()
        output = self._classifier.forward(x)
        loss = criterion(output, y)
        loss.backward()
        optimizer.step()
        self._classifier.model.eval()
        
        # Log to experience replay
        self._log_routing_event(text, target_intent, loss.item())
        
        return {
            "success": True,
            "loss": loss.item(),
            "target_intent": target_intent
        }

    def _get_memory_tool(self) -> Optional[BaseBrainModule]:
        """Get the memory_tool module for experience storage."""
        from oricli_core.brain.registry import ModuleRegistry
        return ModuleRegistry.get_module("memory_tool")

    def _log_routing_event(self, text: str, adapter_id: Optional[str], score: float):
        """Log a routing event to the experience replay buffer."""
        memory = self._get_memory_tool()
        if not memory:
            return
            
        try:
            event = {
                "type": "routing_experience",
                "text": text,
                "adapter_id": adapter_id,
                "score": score,
                "timestamp": time.time()
            }
            # Store in internal experience database via memory tool
            memory.execute("store_item", {
                "item": event,
                "collection": "routing_experiences"
            })
        except Exception as e:
            logger.debug(f"Failed to log routing event: {e}")
