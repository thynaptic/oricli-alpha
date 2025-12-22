"""
LoRA Inference Module
DISABLED: PEFT library is PyTorch-only. This module is disabled in the JAX migration.
"""

from typing import Dict, Any, Optional, List
import logging

from mavaia_core.brain.base_module import BaseBrainModule, ModuleMetadata
from mavaia_core.exceptions import InvalidParameterError

logger = logging.getLogger(__name__)

# Import loader module - handle import error gracefully
try:
    from mavaia_core.brain.modules.lora_loader import LoRALoaderModule

    LOADER_AVAILABLE = True
except ImportError:
    LOADER_AVAILABLE = False
    LoRALoaderModule = None

# Module disabled - PEFT is PyTorch-only
LORA_INFERENCE_AVAILABLE = False


class LoRAInferenceModule(BaseBrainModule):
    """Perform inference using loaded LoRA adapters"""

    def __init__(self, loader_module: Optional[Any] = None):
        super().__init__()
        # Don't instantiate LoRALoaderModule here - it's heavy, will load lazily
        self.loader = loader_module
        self.generation_pipelines: Dict[str, Any] = {}
        self._loader_initialized = False
    
    def _ensure_loader(self):
        """Lazy load LoRA loader only when needed"""
        if not self._loader_initialized:
            self._loader_initialized = True
            if LOADER_AVAILABLE and LoRALoaderModule and self.loader is None:
                try:
                    self.loader = LoRALoaderModule()
                except Exception:
                    self.loader = None

    @property
    def metadata(self) -> ModuleMetadata:
        return ModuleMetadata(
            name="lora_inference",
            version="1.1.0",
            description="DISABLED: LoRA inference (PEFT is PyTorch-only, not available in JAX/Flax)",
            operations=[
                "generate",
                "generate_with_personality",
                "generate_with_style_transfer",
            ],
            dependencies=["jax", "flax"],
            model_required=True,
        )

    def initialize(self) -> bool:
        """Initialize the module"""
        logger.info(
            "LoRAInferenceModule is disabled (PEFT is PyTorch-only; not available in JAX/Flax)",
            extra={"module_name": "lora_inference"},
        )
        return False

    def execute(self, operation: str, params: Dict[str, Any]) -> Dict[str, Any]:
        """Execute an inference operation"""
        # Module is disabled in this codebase; keep behavior explicit and safe.
        return {
            "success": False,
            "error": "LoRAInferenceModule is disabled. PEFT/PyTorch LoRA inference is not available in JAX/Flax.",
        }

        # Unreachable legacy implementation retained for historical reference.
        if operation == "generate":
            return self._generate(
                prompt=params.get("prompt", ""),
                personality=params.get("personality"),
                max_length=params.get("max_length", 100),
                temperature=params.get("temperature", 0.7),
                top_p=params.get("top_p", 0.9),
                num_return_sequences=params.get("num_return_sequences", 1),
                target_style=params.get("target_style"),
            )
        elif operation == "generate_with_personality":
            return self._generate_with_personality(
                prompt=params.get("prompt", ""),
                personality=params.get("personality"),
                context=params.get("context", ""),
                max_length=params.get("max_length", 150),
                temperature=params.get("temperature", 0.8),
                target_style=params.get("target_style"),
            )
        elif operation == "generate_with_style_transfer":
            return self._generate_with_style_transfer(
                prompt=params.get("prompt", ""),
                personality=params.get("personality"),
                context=params.get("context", ""),
                target_style=params.get("target_style", {}),
                max_length=params.get("max_length", 150),
                temperature=params.get("temperature", 0.8),
            )
        else:
            raise InvalidParameterError(
                parameter="operation",
                value=operation,
                reason="Unknown operation for lora_inference",
            )

    def _get_or_create_pipeline(self, personality: str):
        """Get or create a generation pipeline for a personality"""
        if personality in self.generation_pipelines:
            return self.generation_pipelines[personality]

        self._ensure_loader()
        if not self.loader:
            raise ValueError("LoRA loader not available")

        # Get loaded adapter
        adapter_dict = self.loader.get_loaded_adapter(personality)
        if not adapter_dict:
            raise ValueError(f"Adapter not loaded for personality: {personality}")

        adapter_model = adapter_dict["adapter_model"]
        tokenizer = adapter_dict["tokenizer"]

        # Create pipeline
        pipeline_obj = pipeline(
            "text-generation",
            model=adapter_model,
            tokenizer=tokenizer,
            device=-1 if not torch.cuda.is_available() else 0,
            torch_dtype=torch.float16 if torch.cuda.is_available() else torch.float32,
        )

        self.generation_pipelines[personality] = pipeline_obj
        return pipeline_obj

    def _generate(
        self,
        prompt: str,
        personality: str,
        max_length: int = 100,
        temperature: float = 0.7,
        top_p: float = 0.9,
        num_return_sequences: int = 1,
        target_style: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """Generate text using a loaded LoRA adapter"""
        if not LORA_INFERENCE_AVAILABLE:
            return {"success": False, "error": "Transformers not available"}

        try:
            # Get or create pipeline
            pipeline_obj = self._get_or_create_pipeline(personality)

            # Generate
            outputs = pipeline_obj(
                prompt,
                max_length=max_length,
                temperature=temperature,
                top_p=top_p,
                num_return_sequences=num_return_sequences,
                do_sample=True,
                pad_token_id=pipeline_obj.tokenizer.eos_token_id,
            )

            # Extract generated text
            if num_return_sequences == 1:
                generated_text = outputs[0]["generated_text"]
                # Remove prompt from generated text
                if generated_text.startswith(prompt):
                    generated_text = generated_text[len(prompt) :].strip()

                # Apply style transfer if target_style provided
                if target_style:
                    generated_text = self._apply_style_transfer(
                        generated_text, target_style, personality
                    )

                return {
                    "success": True,
                    "text": generated_text,
                    "personality": personality,
                }
            else:
                texts = []
                for output in outputs:
                    text = output["generated_text"]
                    if text.startswith(prompt):
                        text = text[len(prompt) :].strip()
                    texts.append(text)

                return {"success": True, "texts": texts, "personality": personality}

        except Exception as e:
            return {"success": False, "error": f"Generation failed: {str(e)}"}

    def _generate_with_personality(
        self,
        prompt: str,
        personality: str,
        context: str = "",
        max_length: int = 150,
        temperature: float = 0.8,
        target_style: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """Generate personality-specific response with context"""
        if not LORA_INFERENCE_AVAILABLE:
            return {"success": False, "error": "Transformers not available"}

        try:
            # Build full prompt with context
            full_prompt = prompt
            if context:
                full_prompt = f"{context}\n\n{prompt}"

            # Generate
            result = self._generate(
                prompt=full_prompt,
                personality=personality,
                max_length=max_length,
                temperature=temperature,
                num_return_sequences=1,
                target_style=target_style,
            )

            if result["success"]:
                return {
                    "success": True,
                    "response": result["text"],
                    "personality": personality,
                }
            else:
                return result

        except Exception as e:
            return {
                "success": False,
                "error": f"Personality generation failed: {str(e)}",
            }

    def _generate_with_style_transfer(
        self,
        prompt: str,
        personality: str,
        context: str = "",
        target_style: Dict[str, Any] = {},
        max_length: int = 150,
        temperature: float = 0.8,
    ) -> Dict[str, Any]:
        """Generate personality-specific response with style transfer"""
        # First generate with personality
        result = self._generate_with_personality(
            prompt=prompt,
            personality=personality,
            context=context,
            max_length=max_length,
            temperature=temperature,
            target_style=target_style,
        )

        return result

    def _apply_style_transfer(
        self, text: str, target_style: Dict[str, Any], personality: str
    ) -> str:
        """Apply style transfer to generated text"""
        try:
            # Try to import style transfer module
            from mavaia_core.brain.registry import ModuleRegistry

            style_transfer_module = ModuleRegistry.get_module("style_transfer")

            if style_transfer_module:
                result = style_transfer_module.execute(
                    "preserve_personality",
                    {
                        "text": text,
                        "target_style": target_style,
                        "personality": personality,
                    },
                )

                if result.get("success") and result.get("transformed_text"):
                    return result["transformed_text"]
        except Exception as e:
            logger.debug(
                "Style transfer failed; returning original text",
                exc_info=True,
                extra={"module_name": "lora_inference", "error_type": type(e).__name__},
            )

        # Return original text if style transfer fails
        return text
