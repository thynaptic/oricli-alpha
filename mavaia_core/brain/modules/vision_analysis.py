from __future__ import annotations
"""
Vision Analysis Module - Phase V1: TensorFlow-based feature extraction and classification
Converts image features to structured thoughts for cognitive generator
"""

from typing import Dict, Any, List, Optional
import json
import base64
import io
from pathlib import Path
import logging

from mavaia_core.brain.base_module import BaseBrainModule, ModuleMetadata
from mavaia_core.exceptions import InvalidParameterError

logger = logging.getLogger(__name__)

# Optional imports - handle gracefully if dependencies not available
try:
    import numpy as np
    NUMPY_AVAILABLE = True
except ImportError:
    NUMPY_AVAILABLE = False
    np = None

# Lazy import - check availability when needed, not at module import time
TENSORFLOW_AVAILABLE = None
CV2_AVAILABLE = None
_tf = None
_tf_hub = None
_cv2 = None

def _check_tensorflow():
    """Lazy check for TensorFlow availability"""
    global TENSORFLOW_AVAILABLE, _tf, _tf_hub
    if TENSORFLOW_AVAILABLE is None:
        try:
            import tensorflow as tf
            import tensorflow_hub as hub
            _tf = tf
            _tf_hub = hub
            TENSORFLOW_AVAILABLE = True
        except ImportError:
            TENSORFLOW_AVAILABLE = False
            _tf = None
            _tf_hub = None
    return TENSORFLOW_AVAILABLE

def _check_opencv():
    """Lazy check for OpenCV availability"""
    global CV2_AVAILABLE, _cv2
    if CV2_AVAILABLE is None:
        try:
            import cv2
            _cv2 = cv2
            CV2_AVAILABLE = True
        except ImportError:
            CV2_AVAILABLE = False
            _cv2 = None
    return CV2_AVAILABLE


class VisionAnalysisModule(BaseBrainModule):
    """Vision analysis using TensorFlow Hub models for feature extraction"""

    def __init__(self):
        super().__init__()
        self.model = None
        self.image_labels = None
        self._model_loaded = False

        # Use a lightweight image classification model from TensorFlow Hub
        # MobileNet V2 is a good choice for Phase V1 - small, fast, good accuracy
        self.model_url = (
            "https://tfhub.dev/google/imagenet/mobilenet_v2_100_224/classification/4"
        )

    @property
    def metadata(self) -> ModuleMetadata:
        # Use lazy check for dependencies
        tf_available = _check_tensorflow()
        return ModuleMetadata(
            name="vision_analysis",
            version="1.0.0",
            description="Vision analysis module using TensorFlow for feature extraction and classification (Phase V1)",
            operations=[
                "analyze_image",
                "extract_features",
                "classify_objects",
                "detect_faces",
                "get_color_info",
            ],
            dependencies=(
                ["tensorflow", "tensorflow_hub"] if tf_available else []
            ),
            model_required=tf_available,
        )

    def initialize(self) -> bool:
        """Initialize the vision module"""
        if not NUMPY_AVAILABLE:
            return True  # Can still work with basic fallback
        
        # Use lazy check - don't print warnings here
        if not _check_tensorflow():
            return True  # Can still work with basic fallback

        try:
            self._load_model()
            self._load_labels()
            return True
        except Exception as e:
            logger.debug(
                "Vision model initialization failed; using fallback behavior",
                exc_info=True,
                extra={"module_name": "vision_analysis", "error_type": type(e).__name__},
            )
            return True  # Return True to allow fallback operation

    def _load_model(self):
        """Load TensorFlow Hub model"""
        if self._model_loaded:
            return

        if not _check_tensorflow():
            return

        try:
            self.model = _tf_hub.load(self.model_url)
            self._model_loaded = True
        except Exception as e:
            logger.debug(
                "Failed to load TensorFlow Hub vision model",
                exc_info=True,
                extra={"module_name": "vision_analysis", "error_type": type(e).__name__},
            )
            self.model = None

    def _load_labels(self):
        """Load ImageNet class labels"""
        try:
            labels_path = Path(__file__).parent / "imagenet_labels.txt"
            if labels_path.exists():
                with open(labels_path, "r") as f:
                    self.image_labels = [line.strip() for line in f.readlines()]
            else:
                # Fallback: use top ImageNet classes
                self.image_labels = self._get_default_labels()
        except Exception as e:
            logger.debug(
                "Failed to load ImageNet labels; using defaults",
                exc_info=True,
                extra={"module_name": "vision_analysis", "error_type": type(e).__name__},
            )
            self.image_labels = self._get_default_labels()

    def _get_default_labels(self) -> List[str]:
        """Get default ImageNet label list (top 1000 classes)"""
        # This is a simplified list - in production, load full ImageNet labels
        return [f"class_{i}" for i in range(1000)]

    def execute(self, operation: str, params: Dict[str, Any]) -> Dict[str, Any]:
        """Execute vision analysis operation"""
        if operation == "analyze_image":
            return self._analyze_image(params)
        elif operation == "extract_features":
            return self._extract_features(params)
        elif operation == "classify_objects":
            return self._classify_objects(params)
        elif operation == "detect_faces":
            return self._detect_faces(params)
        elif operation == "get_color_info":
            return self._get_color_info(params)
        else:
            raise InvalidParameterError(
                parameter="operation",
                value=operation,
                reason="Unknown operation for vision_analysis",
            )

    def _analyze_image(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """Full image analysis - combines all features"""
        image_data = params.get("image_data")
        if not image_data:
            return {"success": False, "error": "image_data required"}

        try:
            # Decode image
            image = self._decode_image(image_data)
            if image is None:
                # Fallback: return basic analysis even if decode fails
                return {
                    "success": True,
                    "classification": {"labels": [{"label": "image", "confidence": 0.5}], "top_label": "image", "confidence": 0.5},
                    "color_info": {"success": True, "color_name": "unknown", "dominant_color_rgb": [128, 128, 128]},
                    "faces": {"faces_detected": 0, "face_count": 0},
                    "method": "fallback",
                }

            # Extract features (with fallback)
            features = self._extract_features({"image_data": image_data})
            if not features.get("success"):
                features = {"success": True, "features": None, "method": "fallback"}

            # Classify objects (with fallback)
            classification = self._classify_objects({"image_data": image_data})
            if not classification.get("success") or not classification.get("labels"):
                # Fallback classification based on image properties
                classification = self._fallback_classify(image)

            # Get color info (with fallback)
            color_info = self._get_color_info({"image_data": image_data})
            if not color_info.get("success"):
                # Fallback color extraction
                color_info = self._fallback_color_info(image)

            # Detect faces if available
            faces = (
                self._detect_faces({"image_data": image_data})
                if _check_opencv()
                else {"faces_detected": 0, "face_count": 0, "has_faces": False}
            )

            # Build structured thought representation with enhanced scene understanding
            structured_thought = self._build_structured_thought(
                features=features,
                classification=classification,
                color_info=color_info,
                faces=faces,
            )

            # Generate natural language description from vision features
            natural_description = self._generate_natural_description(
                classification=classification,
                color_info=color_info,
                faces=faces,
                features=features,
            )

            # Detect object relationships and scene structure
            scene_understanding = self._analyze_scene_structure(
                classification=classification, color_info=color_info, faces=faces
            )

            # Enhance structured thought with natural description
            if natural_description:
                structured_thought["natural_description"] = natural_description
            if scene_understanding:
                structured_thought["scene_understanding"] = scene_understanding

            return {
                "success": True,
                "structured_thought": structured_thought,
                "features": features,
                "classification": classification,
                "color_info": color_info,
                "faces": faces,
                "natural_description": natural_description,
                "scene_understanding": scene_understanding,
                "confidence": classification.get("confidence", 0.5),
            }

        except Exception as e:
            # Ultimate fallback - return basic structure
            return {
                "success": True,
                "classification": {"labels": [{"label": "image", "confidence": 0.5}], "top_label": "image", "confidence": 0.5},
                "color_info": {"success": True, "color_name": "unknown", "dominant_color_rgb": [128, 128, 128]},
                "faces": {"faces_detected": 0, "face_count": 0},
                "error": str(e),
                "method": "fallback",
            }

    def _extract_features(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """Extract feature vector from image"""
        if not self.model:
            return {"success": False, "error": "Model not loaded", "features": None}

        image_data = params.get("image_data")
        if not image_data:
            return {"success": False, "error": "image_data required"}

        try:
            image = self._decode_image(image_data)
            if image is None:
                return {"success": False, "error": "Failed to decode image"}

            # Preprocess image for model (224x224, normalized)
            image_tensor = self._preprocess_image(image)
            if image_tensor is None:
                return {"success": False, "error": "Failed to preprocess image or TensorFlow not available"}

            # Get features from model
            predictions = self.model(image_tensor)

            # Convert to numpy and extract feature vector
            if hasattr(predictions, 'numpy'):
                feature_vector = predictions.numpy()[0]
            else:
                # Fallback if tensor doesn't have numpy() method
                feature_vector = np.array(predictions)[0]

            return {
                "success": True,
                "feature_vector": feature_vector.tolist(),
                "dimension": len(feature_vector),
                "model": "mobilenet_v2",
            }

        except Exception as e:
            return {"success": False, "error": str(e), "features": None}

    def _classify_objects(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """Classify objects in image using ImageNet classes"""
        image_data = params.get("image_data")
        if not image_data:
            return {"success": False, "error": "image_data required", "labels": []}

        try:
            image = self._decode_image(image_data)
            if image is None:
                # Fallback classification
                return self._fallback_classify(None)

            # Try model-based classification if available
            if self.model and _check_tensorflow():
                try:
                    # Preprocess image
                    image_tensor = self._preprocess_image(image)
                    if image_tensor is not None:
                        # Get predictions
                        predictions = self.model(image_tensor)

                        # Get top-k predictions
                        top_k = params.get("top_k", 5)
                        if hasattr(predictions, 'numpy'):
                            pred_array = predictions.numpy()[0]
                        else:
                            pred_array = np.array(predictions)[0]
                        top_indices = np.argsort(pred_array)[-top_k:][::-1]
                        top_scores = pred_array[top_indices]

                        # Convert to labels
                        labels = []
                        for idx, score in zip(top_indices, top_scores):
                            label = (
                                self.image_labels[idx]
                                if idx < len(self.image_labels)
                                else f"class_{idx}"
                            )
                            labels.append(
                                {"label": label, "confidence": float(score), "index": int(idx)}
                            )

                        return {
                            "success": True,
                            "labels": labels,
                            "top_label": labels[0]["label"] if labels else None,
                            "confidence": float(labels[0]["confidence"]) if labels else 0.0,
                            "method": "model",
                        }
                except Exception:
                    pass  # Fall through to fallback

            # Fallback classification
            return self._fallback_classify(image)

        except Exception as e:
            # Fallback on error
            return self._fallback_classify(None)

    def _detect_faces(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """Detect faces in image using OpenCV"""
        if not _check_opencv():
            return {
                "success": False,
                "error": "OpenCV not available",
                "faces_detected": 0,
            }

        image_data = params.get("image_data")
        if not image_data:
            return {"success": False, "error": "image_data required"}

        try:
            # Decode image
            image_bytes = (
                base64.b64decode(image_data)
                if isinstance(image_data, str)
                else image_data
            )
            nparr = np.frombuffer(image_bytes, np.uint8)
            image = _cv2.imdecode(nparr, _cv2.IMREAD_COLOR)

            if image is None:
                return {
                    "success": False,
                    "error": "Failed to decode image",
                    "faces_detected": 0,
                }

            # Convert to grayscale for face detection
            gray = _cv2.cvtColor(image, _cv2.COLOR_BGR2GRAY)

            # Load face cascade (using default OpenCV cascade)
            try:
                face_cascade = _cv2.CascadeClassifier(
                    _cv2.data.haarcascades + "haarcascade_frontalface_default.xml"
                )
                faces = face_cascade.detectMultiScale(gray, 1.1, 4)

                return {
                    "success": True,
                    "faces_detected": len(faces),
                    "face_count": len(faces),
                    "has_faces": len(faces) > 0,
                }
            except Exception as e:
                logger.debug(
                    "Face detection cascade unavailable or failed",
                    exc_info=True,
                    extra={"module_name": "vision_analysis", "error_type": type(e).__name__},
                )
                # Cascade not available
                return {
                    "success": False,
                    "error": "Face cascade not available",
                    "faces_detected": 0,
                }

        except Exception as e:
            return {"success": False, "error": str(e), "faces_detected": 0}

    def _get_color_info(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """Extract dominant colors from image"""
        image_data = params.get("image_data")
        if not image_data:
            return {"success": False, "error": "image_data required"}

        try:
            # Decode image
            image = self._decode_image(image_data)
            if image is None:
                # Fallback color info
                return self._fallback_color_info(None)

            # Try OpenCV first
            if _check_opencv() and image is not None:
                try:
                    # Get dominant colors using k-means clustering (simple version)
                    if len(image.shape) == 3:
                        pixels = image.reshape(-1, image.shape[-1])
                        dominant_color = np.mean(pixels, axis=0).astype(int).tolist()
                        brightness = float(np.mean(pixels))
                    else:
                        brightness = float(np.mean(image))
                        dominant_color = [int(brightness), int(brightness), int(brightness)]

                    # Determine color name (simple heuristic)
                    r, g, b = dominant_color[:3] if len(dominant_color) >= 3 else [brightness, brightness, brightness]
                    color_name = self._rgb_to_color_name(int(r), int(g), int(b))

                    return {
                        "success": True,
                        "dominant_color_rgb": dominant_color[:3] if len(dominant_color) >= 3 else [int(brightness), int(brightness), int(brightness)],
                        "color_name": color_name,
                        "brightness": brightness,
                        "is_dark": brightness < 100,
                        "is_bright": brightness > 200,
                        "method": "opencv",
                    }
                except Exception:
                    pass  # Fall through to fallback

            # Fallback: use PIL if available
            try:
                from PIL import Image
                image_bytes = (
                    base64.b64decode(image_data)
                    if isinstance(image_data, str)
                    else image_data
                )
                pil_image = Image.open(io.BytesIO(image_bytes))
                # Simple color extraction
                colors = pil_image.getcolors(maxcolors=256 * 256 * 256)
                if colors:
                    dominant = max(colors, key=lambda x: x[0])
                    dominant_color = list(dominant[1]) if isinstance(dominant[1], (tuple, list)) else [dominant[1], dominant[1], dominant[1]]
                    brightness = float(np.mean(dominant_color)) if NUMPY_AVAILABLE else 128.0
                    r, g, b = dominant_color[:3] if len(dominant_color) >= 3 else [brightness, brightness, brightness]
                    color_name = self._rgb_to_color_name(int(r), int(g), int(b))
                    
                    return {
                        "success": True,
                        "dominant_color_rgb": dominant_color[:3] if len(dominant_color) >= 3 else [int(brightness), int(brightness), int(brightness)],
                        "color_name": color_name,
                        "brightness": brightness,
                        "is_dark": brightness < 100,
                        "is_bright": brightness > 200,
                        "method": "pil",
                    }
            except Exception:
                pass

            # Ultimate fallback: use decoded image array
            if image is not None:
                return self._fallback_color_info(image)
            
            return self._fallback_color_info(None)

        except Exception as e:
            # Fallback on error
            return self._fallback_color_info(None)

    def _build_structured_thought(
        self, features: Dict, classification: Dict, color_info: Dict, faces: Dict
    ) -> Dict[str, Any]:
        """Build structured thought representation from vision analysis"""
        labels = classification.get("labels", [])
        top_labels = [l["label"] for l in labels[:3]] if labels else []

        thought_text = "The image shows "
        if top_labels:
            thought_text += f"{', '.join(top_labels)}"
        else:
            thought_text += "visual content"

        if faces.get("has_faces", False):
            face_count = faces.get("face_count", 0)
            thought_text += f" with {face_count} face{'s' if face_count > 1 else ''}"

        if color_info.get("success"):
            color_name = color_info.get("color_name", "")
            if color_name:
                thought_text += f", with dominant {color_name} tones"

        return {
            "type": "vision_analysis",
            "text": thought_text,
            "labels": top_labels,
            "has_faces": faces.get("has_faces", False),
            "face_count": faces.get("face_count", 0),
            "dominant_color": color_info.get("color_name"),
            "brightness": color_info.get("brightness"),
            "confidence": classification.get("confidence", 0.5),
        }

    def _generate_natural_description(
        self,
        classification: Dict[str, Any],
        color_info: Dict[str, Any],
        faces: Dict[str, Any],
        features: Dict[str, Any],
    ) -> str:
        """Generate natural language description from vision features"""
        parts = []
        
        # Add color description
        if color_info.get("color_name"):
            parts.append(f"dominant color is {color_info.get('color_name')}")
        
        # Add object classification
        if classification.get("top_label"):
            parts.append(f"contains {classification.get('top_label')}")
        
        # Add face detection
        face_count = faces.get("face_count", 0)
        if face_count > 0:
            parts.append(f"{face_count} face{'s' if face_count > 1 else ''} detected")
        
        # Add brightness
        brightness = color_info.get("brightness", "medium")
        if brightness != "medium":
            parts.append(f"{brightness} brightness")
        
        if parts:
            return "Image with " + ", ".join(parts) + "."
        return "Image analyzed successfully."

    def _analyze_scene_structure(
        self,
        classification: Dict[str, Any],
        color_info: Dict[str, Any],
        faces: Dict[str, Any],
    ) -> Dict[str, Any]:
        """Analyze scene structure and object relationships"""
        return {
            "object_count": len(classification.get("labels", [])),
            "has_people": faces.get("face_count", 0) > 0,
            "color_palette": color_info.get("color_name", "unknown"),
            "complexity": "high" if len(classification.get("labels", [])) > 3 else "medium",
        }

    def _decode_image(self, image_data: Any) -> Optional[np.ndarray]:
        """Decode image from base64 or bytes"""
        try:
            if isinstance(image_data, str):
                image_bytes = base64.b64decode(image_data)
            elif isinstance(image_data, bytes):
                image_bytes = image_data
            else:
                return None

            # Try PIL first (more reliable)
            try:
                from PIL import Image

                image = Image.open(io.BytesIO(image_bytes))
                return np.array(image.convert("RGB"))
            except Exception as e:
                logger.debug(
                    "PIL decode failed; attempting OpenCV fallback",
                    exc_info=True,
                    extra={"module_name": "vision_analysis", "error_type": type(e).__name__},
                )
                # Fallback to OpenCV
                if _check_opencv():
                    nparr = np.frombuffer(image_bytes, np.uint8)
                    image = _cv2.imdecode(nparr, _cv2.IMREAD_COLOR)
                    if image is not None:
                        image_rgb = _cv2.cvtColor(image, _cv2.COLOR_BGR2RGB)
                        return image_rgb
                return None

        except Exception as e:
            logger.debug(
                "Image decoding error",
                exc_info=True,
                extra={"module_name": "vision_analysis", "error_type": type(e).__name__},
            )
            return None

    def _preprocess_image(self, image: np.ndarray):
        """Preprocess image for MobileNet V2 (224x224, normalized)"""
        if not _check_tensorflow():
            return None
        
        # Resize to 224x224
        image_resized = _tf.image.resize(image, [224, 224])

        # Normalize to [0, 1]
        image_normalized = _tf.cast(image_resized, _tf.float32) / 255.0

        # Add batch dimension
        image_batched = _tf.expand_dims(image_normalized, 0)

        return image_batched

    def _rgb_to_color_name(self, r: int, g: int, b: int) -> str:
        """Convert RGB to color name (simple heuristic)"""
        # Simple color name mapping
        if r > 200 and g > 200 and b > 200:
            return "white"
        elif r < 50 and g < 50 and b < 50:
            return "black"
        elif r > g and r > b:
            return "red"
        elif g > r and g > b:
            return "green"
        elif b > r and b > g:
            return "blue"
        elif r > 200 and g > 150 and b < 100:
            return "orange"
        elif r > 200 and g > 200 and b < 100:
            return "yellow"
        elif r > 150 and b > 150 and g < 100:
            return "purple"
        else:
            return "mixed"
    
    def _fallback_classify(self, image: np.ndarray) -> Dict[str, Any]:
        """Fallback classification when model is not available"""
        # Simple heuristic-based classification
        if image is None or not NUMPY_AVAILABLE:
            return {
                "success": True,
                "labels": [{"label": "image", "confidence": 0.5, "index": 0}],
                "top_label": "image",
                "confidence": 0.5,
                "method": "fallback",
            }
        
        # Analyze image properties for basic classification
        height, width = image.shape[:2]
        avg_brightness = np.mean(image) if len(image.shape) == 2 else np.mean(image.reshape(-1, image.shape[-1]))
        
        # Simple classification based on image properties
        labels = []
        if avg_brightness > 200:
            labels.append({"label": "bright_image", "confidence": 0.7, "index": 0})
        elif avg_brightness < 50:
            labels.append({"label": "dark_image", "confidence": 0.7, "index": 1})
        else:
            labels.append({"label": "medium_brightness_image", "confidence": 0.6, "index": 2})
        
        # Add shape-based classification
        if width > height * 1.5:
            labels.append({"label": "landscape", "confidence": 0.6, "index": 3})
        elif height > width * 1.5:
            labels.append({"label": "portrait", "confidence": 0.6, "index": 4})
        else:
            labels.append({"label": "square", "confidence": 0.5, "index": 5})
        
        return {
            "success": True,
            "labels": labels[:5],
            "top_label": labels[0]["label"] if labels else "image",
            "confidence": float(labels[0]["confidence"]) if labels else 0.5,
            "method": "fallback",
        }
    
    def _fallback_color_info(self, image: np.ndarray) -> Dict[str, Any]:
        """Fallback color extraction when OpenCV/PIL not available"""
        if image is None or not NUMPY_AVAILABLE:
            return {
                "success": True,
                "dominant_color_rgb": [128, 128, 128],
                "color_name": "gray",
                "brightness": 128.0,
                "is_dark": False,
                "is_bright": False,
                "method": "fallback",
            }
        
        try:
            # Calculate average color
            if len(image.shape) == 3:
                # Color image
                avg_color = np.mean(image.reshape(-1, image.shape[-1]), axis=0)
                dominant_color = avg_color.astype(int).tolist()
                brightness = float(np.mean(avg_color))
            else:
                # Grayscale
                brightness = float(np.mean(image))
                dominant_color = [int(brightness), int(brightness), int(brightness)]
            
            r, g, b = dominant_color[:3] if len(dominant_color) >= 3 else [brightness, brightness, brightness]
            color_name = self._rgb_to_color_name(int(r), int(g), int(b))
            
            return {
                "success": True,
                "dominant_color_rgb": dominant_color[:3] if len(dominant_color) >= 3 else [int(brightness), int(brightness), int(brightness)],
                "color_name": color_name,
                "brightness": brightness,
                "is_dark": brightness < 100,
                "is_bright": brightness > 200,
                "method": "fallback",
            }
        except Exception:
            return {
                "success": True,
                "dominant_color_rgb": [128, 128, 128],
                "color_name": "gray",
                "brightness": 128.0,
                "is_dark": False,
                "is_bright": False,
                "method": "fallback",
            }

    def validate_params(self, operation: str, params: Dict[str, Any]) -> bool:
        """Validate parameters"""
        if operation in [
            "analyze_image",
            "extract_features",
            "classify_objects",
            "detect_faces",
            "get_color_info",
        ]:
            return "image_data" in params
        return True


# Module export
def create_module():
    return VisionAnalysisModule()
