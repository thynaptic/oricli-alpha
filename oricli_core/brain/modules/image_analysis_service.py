from __future__ import annotations
"""
Image Analysis Service - Image analysis service using vision models
Converted from Swift ImageAnalysisService.swift
"""

from typing import Any, Dict, List, Optional
import logging

from oricli_core.brain.base_module import BaseBrainModule, ModuleMetadata
from oricli_core.brain.registry import ModuleRegistry
from oricli_core.exceptions import InvalidParameterError

logger = logging.getLogger(__name__)


class ImageAnalysisServiceModule(BaseBrainModule):
    """Image analysis service using vision models"""

    def __init__(self):
        super().__init__()
        self.local_vision = None
        self.vision_pipeline = None
        self._modules_loaded = False

    @property
    def metadata(self) -> ModuleMetadata:
        return ModuleMetadata(
            name="image_analysis_service",
            version="1.0.0",
            description="Image analysis service using vision models",
            operations=[
                "analyze_image",
                "describe_image",
            ],
            dependencies=[],
            model_required=False,
        )

    def initialize(self) -> bool:
        """Initialize the module"""
        return True

    def _ensure_modules_loaded(self):
        """Lazy load dependent modules"""
        if self._modules_loaded:
            return

        try:
            self.local_vision = ModuleRegistry.get_module("local_vision_service")
            self.vision_pipeline = ModuleRegistry.get_module("vision_pipeline_service")

            self._modules_loaded = True
        except Exception as e:
            logger.debug(
                "Failed to load dependent vision modules",
                exc_info=True,
                extra={"module_name": "image_analysis_service", "error_type": type(e).__name__},
            )

    def execute(self, operation: str, params: Dict[str, Any]) -> Dict[str, Any]:
        """Execute an operation"""
        self._ensure_modules_loaded()

        if operation == "analyze_image":
            return self._analyze_image(params)
        elif operation == "describe_image":
            return self._describe_image(params)
        else:
            raise InvalidParameterError(
                parameter="operation",
                value=operation,
                reason="Unknown operation for image_analysis_service",
            )

    def _analyze_image(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """Analyze an image from file data"""
        data = params.get("data")  # bytes
        file_name = params.get("file_name", "")

        if file_name is None:
            file_name = ""
        if not isinstance(file_name, str):
            raise InvalidParameterError("file_name", str(type(file_name).__name__), "file_name must be a string")

        if not data:
            return {
                "success": False,
                "error": "Unable to load image",
            }
        if not isinstance(data, (bytes, bytearray)):
            raise InvalidParameterError("data", str(type(data).__name__), "data must be bytes")

        # Determine MIME type from file extension
        file_ext = file_name.lower().split(".")[-1] if "." in file_name else ""
        mime_type_map = {
            "jpg": "image/jpeg",
            "jpeg": "image/jpeg",
            "png": "image/png",
            "gif": "image/gif",
            "webp": "image/webp",
            "heic": "image/heic",
            "heif": "image/heic",
        }
        mime_type = mime_type_map.get(file_ext, "image/jpeg")

        app_context = """
        You are analyzing an image that the user has shared. Provide a detailed, accurate description of what you see in the image.
        Be specific about:
        - Any text, logos, or symbols visible
        - Colors, composition, and visual elements
        - The overall subject and context
        - Any notable details or features
        """

        user_prompt = "Describe this image in detail, including any text, logos, symbols, colors, and visual elements you can see."

        # Step 1: Try local vision service first
        if self.local_vision:
            try:
                result = self.local_vision.execute("analyze_image", {
                    "image_data": data,
                    "user_prompt": user_prompt,
                    "app_context": app_context,
                })

                return {
                    "success": True,
                    "description": result.get("description", ""),
                    "key_elements": result.get("key_elements", []),
                    "context": f"Local model: {result.get('model_used', 'unknown')}",
                }
            except Exception as e:
                logger.debug(
                    "Local vision analysis failed; falling back to pipeline",
                    exc_info=True,
                    extra={"module_name": "image_analysis_service", "error_type": type(e).__name__},
                )

        # Step 2: Use cloud vision pipeline
        if self.vision_pipeline:
            try:
                result = self.vision_pipeline.execute("process_image", {
                    "image_data": data,
                    "user_prompt": user_prompt,
                    "app_context": app_context,
                })

                return {
                    "success": True,
                    "description": result.get("description", ""),
                    "key_elements": result.get("key_elements", []),
                    "context": result.get("context"),
                }
            except Exception as e:
                logger.debug(
                    "Vision pipeline analysis failed",
                    exc_info=True,
                    extra={"module_name": "image_analysis_service", "error_type": type(e).__name__},
                )
                return {
                    "success": False,
                    "error": "Image analysis failed",
                }

        # Fallback: return error
        return {
            "success": False,
            "error": "No vision service available",
        }

    def _describe_image(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """Describe an image (alias for analyze_image)"""
        return self._analyze_image(params)

