"""
LoRA Adapter Loader Module
DISABLED: PEFT library is PyTorch-only. This module is disabled in the JAX migration.
"""

from typing import Dict, Any, Optional
import os
import sys
from pathlib import Path
import json

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent))

from mavaia_core.brain.base_module import BaseBrainModule, ModuleMetadata

# Module disabled - PEFT is PyTorch-only
LORA_LOADER_AVAILABLE = False


class LoRALoaderModule(BaseBrainModule):
    """Load and manage LoRA adapters for personality switching"""

    def __init__(self):
        self.loaded_adapters: Dict[str, Dict[str, Any]] = {}
        self.base_models: Dict[str, Any] = {}

    @property
    def metadata(self) -> ModuleMetadata:
        return ModuleMetadata(
            name="lora_loader",
            version="1.0.0",
            description="DISABLED: LoRA adapter loading (PEFT is PyTorch-only, not available in JAX/Flax)",
            operations=[
                "load_adapter",
                "unload_adapter",
                "list_loaded",
                "validate_adapter",
            ],
            dependencies=["jax", "flax"],
            model_required=True,
        )

    def initialize(self) -> bool:
        """Initialize the module"""
        print("[LoRALoaderModule] DISABLED: PEFT is PyTorch-only, not available in JAX/Flax", file=sys.stderr)
        return False

    def execute(self, operation: str, params: Dict[str, Any]) -> Dict[str, Any]:
        """Execute a LoRA loader operation"""
        if operation == "load_adapter":
            return self._load_adapter(
                adapter_path=params.get("adapter_path"),
                base_model=params.get("base_model"),
                personality=params.get("personality"),
            )
        elif operation == "unload_adapter":
            return self._unload_adapter(personality=params.get("personality"))
        elif operation == "list_loaded":
            return self._list_loaded()
        elif operation == "validate_adapter":
            return self._validate_adapter(adapter_path=params.get("adapter_path"))
        else:
            raise ValueError(f"Unknown operation: {operation}")

    def _load_adapter(
        self, adapter_path: str, base_model: str, personality: str
    ) -> Dict[str, Any]:
        """Load a LoRA adapter"""
        if not LORA_LOADER_AVAILABLE:
            return {"success": False, "error": "PEFT library not available"}

        # Check if already loaded
        if personality in self.loaded_adapters:
            return {
                "success": True,
                "message": f"Adapter for {personality} already loaded",
                "personality": personality,
            }

        try:
            # Validate adapter path
            adapter_path_obj = Path(adapter_path)
            if not adapter_path_obj.exists():
                return {
                    "success": False,
                    "error": f"Adapter path does not exist: {adapter_path}",
                }

            adapter_config_path = adapter_path_obj / "adapter_config.json"
            adapter_model_path = adapter_path_obj / "adapter_model.bin"

            if not adapter_config_path.exists() or not adapter_model_path.exists():
                return {
                    "success": False,
                    "error": "Invalid adapter structure (missing adapter_config.json or adapter_model.bin)",
                }

            # Load base model if not already loaded
            if base_model not in self.base_models:
                print(f"[LoRALoaderModule] Loading base model: {base_model}")
                try:
                    tokenizer = AutoTokenizer.from_pretrained(
                        base_model, trust_remote_code=True
                    )
                    model = AutoModelForCausalLM.from_pretrained(
                        base_model,
                        trust_remote_code=True,
                        device_map="auto" if torch.cuda.is_available() else None,
                        torch_dtype=(
                            torch.float16
                            if torch.cuda.is_available()
                            else torch.float32
                        ),
                    )

                    self.base_models[base_model] = {
                        "model": model,
                        "tokenizer": tokenizer,
                    }
                    print(f"[LoRALoaderModule] Base model loaded: {base_model}")
                except Exception as e:
                    return {
                        "success": False,
                        "error": f"Failed to load base model: {str(e)}",
                    }

            # Load LoRA adapter
            print(f"[LoRALoaderModule] Loading LoRA adapter from: {adapter_path}")
            base_model_dict = self.base_models[base_model]
            base_model_obj = base_model_dict["model"]

            # Load adapter
            adapter_model = PeftModel.from_pretrained(
                base_model_obj,
                adapter_path,
                device_map="auto" if torch.cuda.is_available() else None,
            )

            # Store loaded adapter
            self.loaded_adapters[personality] = {
                "adapter_model": adapter_model,
                "tokenizer": base_model_dict["tokenizer"],
                "base_model": base_model,
                "adapter_path": adapter_path,
            }

            print(
                f"[LoRALoaderModule] ✅ Adapter loaded for personality: {personality}"
            )

            return {
                "success": True,
                "personality": personality,
                "base_model": base_model,
                "adapter_path": adapter_path,
            }

        except Exception as e:
            return {"success": False, "error": f"Failed to load adapter: {str(e)}"}

    def _unload_adapter(self, personality: str) -> Dict[str, Any]:
        """Unload a LoRA adapter"""
        if personality not in self.loaded_adapters:
            return {"success": False, "error": f"Adapter for {personality} not loaded"}

        try:
            # Remove from loaded adapters
            del self.loaded_adapters[personality]

            # Note: We don't unload base models as they might be shared
            # In production, implement reference counting for base models

            print(f"[LoRALoaderModule] Unloaded adapter for {personality}")

            return {"success": True, "personality": personality}
        except Exception as e:
            return {"success": False, "error": f"Failed to unload adapter: {str(e)}"}

    def _list_loaded(self) -> Dict[str, Any]:
        """List all loaded adapters"""
        personalities = list(self.loaded_adapters.keys())
        return {
            "success": True,
            "loaded_adapters": personalities,
            "count": len(personalities),
        }

    def _validate_adapter(self, adapter_path: str) -> Dict[str, Any]:
        """Validate an adapter path"""
        try:
            adapter_path_obj = Path(adapter_path)
            if not adapter_path_obj.exists():
                return {
                    "success": False,
                    "valid": False,
                    "error": "Path does not exist",
                }

            adapter_config_path = adapter_path_obj / "adapter_config.json"
            adapter_model_path = adapter_path_obj / "adapter_model.bin"

            if not adapter_config_path.exists():
                return {
                    "success": False,
                    "valid": False,
                    "error": "Missing adapter_config.json",
                }

            if not adapter_model_path.exists():
                return {
                    "success": False,
                    "valid": False,
                    "error": "Missing adapter_model.bin",
                }

            # Try to load config
            try:
                with open(adapter_config_path, "r") as f:
                    config = json.load(f)

                base_model = config.get("base_model_name_or_path", "unknown")

                return {
                    "success": True,
                    "valid": True,
                    "base_model": base_model,
                    "config": config,
                }
            except Exception as e:
                return {
                    "success": False,
                    "valid": False,
                    "error": f"Failed to read config: {str(e)}",
                }

        except Exception as e:
            return {"success": False, "valid": False, "error": str(e)}

    def get_loaded_adapter(self, personality: str) -> Optional[Dict[str, Any]]:
        """Get a loaded adapter (internal use)"""
        return self.loaded_adapters.get(personality)
