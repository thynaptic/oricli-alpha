"""
Model Optimizer Module
DISABLED: This module requires PyTorch-specific optimizations.
JAX/Flax equivalents are not available. This module is disabled in the JAX migration.
"""

from typing import Dict, Any, Optional, List
import sys
from pathlib import Path

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent))

from mavaia_core.brain.base_module import BaseBrainModule, ModuleMetadata

# Module disabled - PyTorch-specific optimizations not available in JAX/Flax
JAX_AVAILABLE = False
TORCH_AVAILABLE = False
BITSANDBYTES_AVAILABLE = False
BitsAndBytesConfig = None

def _lazy_import_bitsandbytes():
    """Lazy import BitsAndBytesConfig only when needed"""
    global BITSANDBYTES_AVAILABLE, BitsAndBytesConfig
    if not BITSANDBYTES_AVAILABLE:
        try:
            from transformers import BitsAndBytesConfig as BBC
            BitsAndBytesConfig = BBC
            BITSANDBYTES_AVAILABLE = True
        except ImportError:
            pass


class ModelOptimizerModule(BaseBrainModule):
    """DISABLED: Model optimization module (requires PyTorch-specific features not available in JAX/Flax)"""

    def __init__(self):
        self.optimized_models: Dict[str, Any] = {}
        self.optimization_configs: Dict[str, Dict[str, Any]] = {}

    @property
    def metadata(self) -> ModuleMetadata:
        return ModuleMetadata(
            name="model_optimizer",
            version="1.0.0",
            description="DISABLED: Model optimization (PyTorch-specific, not available in JAX/Flax)",
            operations=[
                "quantize_model",
                "prune_model",
                "compress_model",
                "optimize_for_device",
                "get_model_size",
                "compare_models",
            ],
            dependencies=["jax", "flax"],
            model_required=False,
        )

    def initialize(self) -> bool:
        """Initialize the module"""
        print("[ModelOptimizerModule] DISABLED: PyTorch-specific optimizations not available in JAX/Flax", file=sys.stderr)
        return False

    def execute(self, operation: str, params: Dict[str, Any]) -> Dict[str, Any]:
        """Execute an optimization operation"""
        return {
            "success": False,
            "error": "ModelOptimizerModule is disabled. PyTorch-specific optimizations (quantization, pruning) are not available in JAX/Flax."
        }

        try:
            if operation == "quantize_model":
                return self._quantize_model(params)
            elif operation == "prune_model":
                return self._prune_model(params)
            elif operation == "compress_model":
                return self._compress_model(params)
            elif operation == "optimize_for_device":
                return self._optimize_for_device(params)
            elif operation == "get_model_size":
                return self._get_model_size(params)
            elif operation == "compare_models":
                return self._compare_models(params)
            else:
                raise ValueError(f"Unknown operation: {operation}")
        except Exception as e:
            return {"success": False, "error": str(e)}

    def _quantize_model(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """
        Quantize a model to reduce size and improve inference speed

        Args:
            model_path: Path to model or model identifier
            quantization_type: "int8", "int4", "dynamic", "static"
            output_path: Optional path to save quantized model
            device: "cpu" or "cuda"

        Returns:
            Dict with optimization results
        """
        model_path = params.get("model_path")
        quantization_type = params.get("quantization_type", "int8")
        output_path = params.get("output_path")
        device = params.get("device", "cpu")

        if not model_path:
            return {"success": False, "error": "model_path required"}

        try:
            # Load model
            model = AutoModel.from_pretrained(model_path)
            model.eval()

            original_size = self._calculate_model_size(model)

            # Apply quantization based on type
            if quantization_type == "int8":
                if BITSANDBYTES_AVAILABLE:
                    # Use BitsAndBytes for INT8 quantization
                    quantization_config = BitsAndBytesConfig(
                        load_in_8bit=True, llm_int8_threshold=6.0
                    )
                    model = AutoModel.from_pretrained(
                        model_path, quantization_config=quantization_config
                    )
                else:
                    # Fallback to PyTorch quantization
                    model = quantization.quantize_dynamic(
                        model, {torch.nn.Linear}, dtype=torch.qint8
                    )

            elif quantization_type == "int4":
                if BITSANDBYTES_AVAILABLE:
                    quantization_config = BitsAndBytesConfig(
                        load_in_4bit=True,
                        bnb_4bit_compute_dtype=torch.float16,
                        bnb_4bit_use_double_quant=True,
                        bnb_4bit_quant_type="nf4",
                    )
                    model = AutoModel.from_pretrained(
                        model_path, quantization_config=quantization_config
                    )
                else:
                    return {
                        "success": False,
                        "error": "INT4 quantization requires bitsandbytes",
                    }

            elif quantization_type == "dynamic":
                model = quantization.quantize_dynamic(
                    model, {torch.nn.Linear, torch.nn.Conv2d}, dtype=torch.qint8
                )

            elif quantization_type == "static":
                # Static quantization requires calibration data
                return {
                    "success": False,
                    "error": "Static quantization requires calibration dataset",
                }

            else:
                return {
                    "success": False,
                    "error": f"Unknown quantization type: {quantization_type}",
                }

            optimized_size = self._calculate_model_size(model)
            compression_ratio = (1 - optimized_size / original_size) * 100

            # Store optimized model
            model_key = f"{model_path}_{quantization_type}"
            self.optimized_models[model_key] = model
            self.optimization_configs[model_key] = {
                "type": "quantization",
                "quantization_type": quantization_type,
                "original_size_mb": original_size,
                "optimized_size_mb": optimized_size,
                "compression_ratio": compression_ratio,
            }

            # Save if output path provided
            if output_path:
                model.save_pretrained(output_path)

            return {
                "success": True,
                "model_key": model_key,
                "original_size_mb": original_size,
                "optimized_size_mb": optimized_size,
                "compression_ratio": compression_ratio,
                "quantization_type": quantization_type,
                "output_path": output_path,
            }

        except Exception as e:
            return {"success": False, "error": f"Quantization failed: {str(e)}"}

    def _prune_model(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """
        Prune a model to remove unnecessary weights

        Args:
            model_path: Path to model
            pruning_ratio: Fraction of weights to prune (0.0-1.0)
            pruning_method: "magnitude", "structured", "unstructured"
            output_path: Optional path to save pruned model

        Returns:
            Dict with pruning results
        """
        model_path = params.get("model_path")
        pruning_ratio = params.get("pruning_ratio", 0.2)
        pruning_method = params.get("pruning_method", "magnitude")
        output_path = params.get("output_path")

        if not model_path:
            return {"success": False, "error": "model_path required"}

        try:
            # Load model
            model = AutoModel.from_pretrained(model_path)
            model.eval()

            original_size = self._calculate_model_size(model)

            # Apply pruning
            if pruning_method == "magnitude":
                # Magnitude-based pruning
                import torch.nn.utils.prune as prune

                for name, module in model.named_modules():
                    if isinstance(module, torch.nn.Linear):
                        prune.l1_unstructured(
                            module, name="weight", amount=pruning_ratio
                        )
                        prune.remove(module, "weight")  # Make pruning permanent

            elif pruning_method == "structured":
                # Structured pruning (removes entire channels/filters)
                import torch.nn.utils.prune as prune

                for name, module in model.named_modules():
                    if isinstance(module, torch.nn.Linear):
                        prune.ln_structured(
                            module, name="weight", amount=pruning_ratio, n=2, dim=0
                        )
                        prune.remove(module, "weight")

            elif pruning_method == "unstructured":
                # Unstructured pruning (removes individual weights)
                import torch.nn.utils.prune as prune

                for name, module in model.named_modules():
                    if isinstance(module, torch.nn.Linear):
                        prune.random_unstructured(
                            module, name="weight", amount=pruning_ratio
                        )
                        prune.remove(module, "weight")

            else:
                return {
                    "success": False,
                    "error": f"Unknown pruning method: {pruning_method}",
                }

            optimized_size = self._calculate_model_size(model)
            compression_ratio = (1 - optimized_size / original_size) * 100

            # Store pruned model
            model_key = f"{model_path}_pruned_{pruning_method}"
            self.optimized_models[model_key] = model
            self.optimization_configs[model_key] = {
                "type": "pruning",
                "pruning_method": pruning_method,
                "pruning_ratio": pruning_ratio,
                "original_size_mb": original_size,
                "optimized_size_mb": optimized_size,
                "compression_ratio": compression_ratio,
            }

            # Save if output path provided
            if output_path:
                model.save_pretrained(output_path)

            return {
                "success": True,
                "model_key": model_key,
                "original_size_mb": original_size,
                "optimized_size_mb": optimized_size,
                "compression_ratio": compression_ratio,
                "pruning_method": pruning_method,
                "pruning_ratio": pruning_ratio,
                "output_path": output_path,
            }

        except Exception as e:
            return {"success": False, "error": f"Pruning failed: {str(e)}"}

    def _compress_model(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """
        Apply multiple compression techniques

        Args:
            model_path: Path to model
            techniques: List of techniques to apply ["quantize", "prune"]
            output_path: Optional path to save compressed model

        Returns:
            Dict with compression results
        """
        model_path = params.get("model_path")
        techniques = params.get("techniques", ["quantize"])
        output_path = params.get("output_path")

        if not model_path:
            return {"success": False, "error": "model_path required"}

        try:
            # Load model
            model = AutoModel.from_pretrained(model_path)
            model.eval()

            original_size = self._calculate_model_size(model)
            current_model = model
            applied_techniques = []

            # Apply techniques in sequence
            for technique in techniques:
                if technique == "quantize":
                    current_model = quantization.quantize_dynamic(
                        current_model, {torch.nn.Linear}, dtype=torch.qint8
                    )
                    applied_techniques.append("quantization")

                elif technique == "prune":
                    import torch.nn.utils.prune as prune

                    pruning_ratio = params.get("pruning_ratio", 0.2)

                    for name, module in current_model.named_modules():
                        if isinstance(module, torch.nn.Linear):
                            prune.l1_unstructured(
                                module, name="weight", amount=pruning_ratio
                            )
                            prune.remove(module, "weight")

                    applied_techniques.append(f"pruning_{pruning_ratio}")

            optimized_size = self._calculate_model_size(current_model)
            compression_ratio = (1 - optimized_size / original_size) * 100

            # Store compressed model
            model_key = f"{model_path}_compressed"
            self.optimized_models[model_key] = current_model
            self.optimization_configs[model_key] = {
                "type": "compression",
                "techniques": applied_techniques,
                "original_size_mb": original_size,
                "optimized_size_mb": optimized_size,
                "compression_ratio": compression_ratio,
            }

            # Save if output path provided
            if output_path:
                current_model.save_pretrained(output_path)

            return {
                "success": True,
                "model_key": model_key,
                "original_size_mb": original_size,
                "optimized_size_mb": optimized_size,
                "compression_ratio": compression_ratio,
                "applied_techniques": applied_techniques,
                "output_path": output_path,
            }

        except Exception as e:
            return {"success": False, "error": f"Compression failed: {str(e)}"}

    def _optimize_for_device(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """
        Optimize model for specific device (CPU, CUDA, MPS)

        Args:
            model_path: Path to model
            device: Target device ("cpu", "cuda", "mps")
            output_path: Optional path to save optimized model

        Returns:
            Dict with optimization results
        """
        model_path = params.get("model_path")
        device = params.get("device", "cpu")
        output_path = params.get("output_path")

        if not model_path:
            return {"success": False, "error": "model_path required"}

        try:
            # Load model
            model = AutoModel.from_pretrained(model_path)
            model.eval()

            # Move to device
            if device == "cuda" and torch.cuda.is_available():
                model = model.to("cuda")
                # Use TensorFloat-32 for faster computation on Ampere GPUs
                torch.backends.cuda.matmul.allow_tf32 = True
            elif (
                device == "mps"
                and hasattr(torch.backends, "mps")
                and torch.backends.mps.is_available()
            ):
                model = model.to("mps")
            else:
                model = model.to("cpu")
                device = "cpu"

            # Apply device-specific optimizations
            if device == "cpu":
                # Use TorchScript for CPU optimization
                try:
                    model = torch.jit.script(model)
                except:
                    # If scripting fails, use tracing
                    try:
                        dummy_input = torch.zeros(1, 128, dtype=torch.long)
                        model = torch.jit.trace(model, dummy_input)
                    except:
                        pass  # Skip optimization if both fail

            # Store optimized model
            model_key = f"{model_path}_{device}_optimized"
            self.optimized_models[model_key] = model
            self.optimization_configs[model_key] = {
                "type": "device_optimization",
                "device": device,
                "torchscript": device == "cpu",
            }

            # Save if output path provided
            if output_path:
                if device == "cpu" and isinstance(model, torch.jit.ScriptModule):
                    torch.jit.save(model, output_path)
                else:
                    model.save_pretrained(output_path)

            return {
                "success": True,
                "model_key": model_key,
                "device": device,
                "torchscript": device == "cpu",
                "output_path": output_path,
            }

        except Exception as e:
            return {"success": False, "error": f"Device optimization failed: {str(e)}"}

    def _get_model_size(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """
        Calculate model size in MB

        Args:
            model_path: Path to model or model_key for cached model

        Returns:
            Dict with size information
        """
        model_path = params.get("model_path")
        model_key = params.get("model_key")

        if model_key and model_key in self.optimized_models:
            model = self.optimized_models[model_key]
        elif model_path:
            try:
                model = AutoModel.from_pretrained(model_path)
            except Exception as e:
                return {"success": False, "error": f"Failed to load model: {str(e)}"}
        else:
            return {"success": False, "error": "model_path or model_key required"}

        size_mb = self._calculate_model_size(model)
        param_count = sum(p.numel() for p in model.parameters())
        trainable_params = sum(p.numel() for p in model.parameters() if p.requires_grad)

        return {
            "success": True,
            "size_mb": size_mb,
            "param_count": param_count,
            "trainable_params": trainable_params,
            "size_gb": size_mb / 1024,
        }

    def _compare_models(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """
        Compare original and optimized models

        Args:
            original_model_path: Path to original model
            optimized_model_key: Key of optimized model in cache

        Returns:
            Dict with comparison results
        """
        original_model_path = params.get("original_model_path")
        optimized_model_key = params.get("optimized_model_key")

        if not original_model_path or not optimized_model_key:
            return {
                "success": False,
                "error": "original_model_path and optimized_model_key required",
            }

        if optimized_model_key not in self.optimized_models:
            return {
                "success": False,
                "error": f"Optimized model not found: {optimized_model_key}",
            }

        try:
            original_model = AutoModel.from_pretrained(original_model_path)
            optimized_model = self.optimized_models[optimized_model_key]

            original_size = self._calculate_model_size(original_model)
            optimized_size = self._calculate_model_size(optimized_model)

            compression_ratio = (1 - optimized_size / original_size) * 100
            size_reduction = original_size - optimized_size

            optimization_info = self.optimization_configs.get(optimized_model_key, {})

            return {
                "success": True,
                "original_size_mb": original_size,
                "optimized_size_mb": optimized_size,
                "size_reduction_mb": size_reduction,
                "compression_ratio": compression_ratio,
                "optimization_type": optimization_info.get("type", "unknown"),
                "optimization_details": optimization_info,
            }

        except Exception as e:
            return {"success": False, "error": f"Comparison failed: {str(e)}"}

    def _calculate_model_size(self, model: Any) -> float:
        """Calculate model size in MB"""
        try:
            param_size = sum(p.numel() * p.element_size() for p in model.parameters())
            buffer_size = sum(b.numel() * b.element_size() for b in model.buffers())
            total_size = param_size + buffer_size
            return total_size / (1024 * 1024)  # Convert to MB
        except:
            # Fallback: estimate from parameter count
            try:
                param_count = sum(p.numel() for p in model.parameters())
                # Assume float32 (4 bytes per parameter)
                return (param_count * 4) / (1024 * 1024)
            except:
                return 0.0
