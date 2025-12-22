"""
Vision Pipeline Service
Vision pipeline using ONLY Python vision_analysis module (NO Ollama)
Converted from Swift VisionPipelineService.swift
"""

from typing import Any, Dict, List, Optional
import base64
import logging

from mavaia_core.brain.base_module import BaseBrainModule, ModuleMetadata
from mavaia_core.brain.registry import ModuleRegistry
from mavaia_core.exceptions import InvalidParameterError, ModuleOperationError

logger = logging.getLogger(__name__)


class PipelineContext:
    """Pipeline context for tracking processing"""

    def __init__(
        self,
        fallback_triggered: bool = False,
        final_confidence: int = 0,
        processing_path: List[str] = None,
        model_used: str = "",
    ):
        self.fallback_triggered = fallback_triggered
        self.final_confidence = final_confidence
        self.processing_path = processing_path or []
        self.model_used = model_used

    def to_dict(self) -> Dict[str, Any]:
        return {
            "fallback_triggered": self.fallback_triggered,
            "final_confidence": self.final_confidence,
            "processing_path": self.processing_path,
            "model_used": self.model_used,
        }


class VisionPipelineResult:
    """Vision pipeline result"""

    def __init__(
        self,
        tasks: List[str],
        summary: str,
        detected_intent: str,
        insights: List[str],
        final_confidence: int,
        context: PipelineContext,
    ):
        self.tasks = tasks
        self.summary = summary
        self.detected_intent = detected_intent
        self.insights = insights
        self.final_confidence = final_confidence
        self.context = context

    def to_dict(self) -> Dict[str, Any]:
        return {
            "tasks": self.tasks,
            "summary": self.summary,
            "detected_intent": self.detected_intent,
            "insights": self.insights,
            "final_confidence": self.final_confidence,
            "context": self.context.to_dict(),
        }


class VisionPipelineServiceModule(BaseBrainModule):
    """Vision pipeline using ONLY Python vision_analysis module"""

    def __init__(self):
        super().__init__()
        self.python_brain_service = None
        self._modules_loaded = False

    @property
    def metadata(self) -> ModuleMetadata:
        return ModuleMetadata(
            name="vision_pipeline_service",
            version="1.0.0",
            description="Vision pipeline using ONLY Python vision_analysis module (NO Ollama)",
            operations=[
                "process_image",
                "analyze_image",
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
            self.python_brain_service = ModuleRegistry.get_module("python_brain_service")

            self._modules_loaded = True
        except Exception as e:
            logger.debug(
                "Failed to load python_brain_service for vision_pipeline_service",
                exc_info=True,
                extra={"module_name": "vision_pipeline_service", "error_type": type(e).__name__},
            )

    def execute(self, operation: str, params: Dict[str, Any]) -> Dict[str, Any]:
        """Execute an operation"""
        self._ensure_modules_loaded()

        if operation == "process_image":
            return self._process_image(params)
        elif operation == "analyze_image":
            return self._analyze_image(params)
        else:
            raise InvalidParameterError(
                parameter="operation",
                value=operation,
                reason="Unknown operation for vision_pipeline_service",
            )

    def _process_image(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """Process image using Python vision_analysis module"""
        image_data = params.get("image_data")
        mime_type = params.get("mime_type", "image/png")
        user_prompt = params.get("user_prompt")
        app_context = params.get("app_context", "")

        # Initialize pipeline context
        context = PipelineContext()

        # Use Python vision_analysis module ONLY
        result = self._process_local_vision(
            image_data=image_data,
            user_prompt=user_prompt,
            app_context=app_context,
            context=context,
        )

        return {
            "success": True,
            "result": result.to_dict(),
        }

    def _analyze_image(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """Analyze image (alias for process_image)"""
        return self._process_image(params)

    def _process_local_vision(
        self,
        image_data: bytes,
        user_prompt: Optional[str],
        app_context: str,
        context: PipelineContext,
    ) -> VisionPipelineResult:
        """Process image using local vision analysis"""
        # Encode image to base64
        base64_image = base64.b64encode(image_data).decode("utf-8")

        if not self.python_brain_service:
            raise ModuleOperationError(
                module_name="vision_pipeline_service",
                operation="process_image",
                reason="python_brain_service not available",
            )

        # Use Python vision_analysis module ONLY
        try:
            vision_result = self.python_brain_service.execute(
                "execute_operation",
                {
                    "module": "vision_analysis",
                    "operation": "analyze_image",
                    "params": {
                        "image_data": base64_image,
                    },
                }
            )

            if not vision_result.get("success", False):
                raise ModuleOperationError(
                    module_name="vision_pipeline_service",
                    operation="process_image",
                    reason="Vision analysis failed",
                )

            # Get structured thought from vision analysis
            result_data = vision_result.get("result", {})
            structured_thought = result_data.get("structured_thought", {})
            thought_text = structured_thought.get("text", "")

            if not thought_text:
                raise ModuleOperationError(
                    module_name="vision_pipeline_service",
                    operation="process_image",
                    reason="Invalid vision analysis result (missing structured thought text)",
                )

            # Extract classification and labels
            classification = result_data.get("classification", {})
            labels = classification.get("labels", [])

            # Build simple summary from structured thought
            summary = thought_text

            # Extract insights (labels, faces, colors)
            insights: List[str] = []
            if labels:
                label_texts = [l.get("label", "") for l in labels[:3] if l.get("label")]
                if label_texts:
                    insights.append(f"Detected: {', '.join(label_texts)}")

            if structured_thought.get("has_faces", False):
                face_count = structured_thought.get("face_count", 0)
                insights.append(f"Contains {face_count} face{'s' if face_count != 1 else ''}")

            if structured_thought.get("dominant_color"):
                color = structured_thought.get("dominant_color")
                insights.append(f"Dominant color: {color}")

            if not insights:
                insights = ["Image analyzed successfully"]

            # Calculate confidence
            confidence = classification.get("confidence", 50)

            # Update context
            updated_context = PipelineContext(
                fallback_triggered=context.fallback_triggered,
                final_confidence=confidence,
                processing_path=context.processing_path + ["PythonVisionAnalysis"],
                model_used="vision_analysis (TensorFlow)",
            )

            # Return simple result - NO tasks/projects/notes structure
            return VisionPipelineResult(
                tasks=[],  # Empty - we don't extract tasks
                summary=summary,
                detected_intent="image_analysis",  # Simple intent
                insights=insights,
                final_confidence=confidence,
                context=updated_context,
            )

        except Exception as e:
            logger.debug(
                "Vision processing failed",
                exc_info=True,
                extra={"module_name": "vision_pipeline_service", "error_type": type(e).__name__},
            )
            raise ModuleOperationError(
                module_name="vision_pipeline_service",
                operation="process_image",
                reason="Vision processing failed",
            ) from e

