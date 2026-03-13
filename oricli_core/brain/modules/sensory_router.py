from __future__ import annotations
"""
Sensory Router Module - Detects and routes multi-modal sensory inputs.
Handles images, audio, and videos, routing them to specialized encoders.
"""

import os
import logging
from pathlib import Path
from typing import Dict, Any, Optional

from oricli_core.brain.base_module import BaseBrainModule, ModuleMetadata
from oricli_core.exceptions import InvalidParameterError

logger = logging.getLogger(__name__)

class SensoryRouterModule(BaseBrainModule):
    """Detects input type and routes to the correct processing pipeline."""

    def __init__(self) -> None:
        super().__init__()

    @property
    def metadata(self) -> ModuleMetadata:
        return ModuleMetadata(
            name="sensory_router",
            version="1.0.0",
            description="Routes sensory inputs (Image, Audio, Video) to appropriate encoders",
            operations=["route_input", "get_media_info"],
            dependencies=[],
            model_required=False,
        )

    def execute(self, operation: str, params: Dict[str, Any]) -> Dict[str, Any]:
        if operation == "route_input":
            return self._route_input(params)
        elif operation == "get_media_info":
            return self._get_media_info(params)
        else:
            raise InvalidParameterError(parameter="operation", value=operation, reason="Unsupported operation")

    def _route_input(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """Detect file type and determine the target module."""
        file_path = params.get("file_path")
        if not file_path:
            return {"success": False, "error": "file_path required"}

        path = Path(file_path)
        if not path.exists():
            return {"success": False, "error": f"File not found: {file_path}"}

        ext = path.suffix.lower()
        
        # 1. IMAGE ROUTING
        if ext in [".jpg", ".jpeg", ".png", ".webp", ".bmp"]:
            return {
                "success": True,
                "input_type": "image",
                "target_module": "vision_encoder",
                "recommended_op": "encode_image",
                "info": self._get_image_info(path)
            }
            
        # 2. AUDIO ROUTING
        elif ext in [".mp3", ".wav", ".m4a", ".ogg", ".flac"]:
            return {
                "success": True,
                "input_type": "audio",
                "target_module": "whisper_stt",
                "recommended_op": "transcribe",
                "info": self._get_audio_info(path)
            }
            
        # 3. VIDEO ROUTING
        elif ext in [".mp4", ".mov", ".avi", ".mkv"]:
            return {
                "success": True,
                "input_type": "video",
                "target_module": "video_analyst",
                "recommended_op": "analyze_frames"
            }

        return {"success": False, "error": f"Unsupported file type: {ext}"}

    def _get_media_info(self, params: Dict[str, Any]) -> Dict[str, Any]:
        file_path = params.get("file_path")
        if not file_path: return {"success": False}
        path = Path(file_path)
        
        ext = path.suffix.lower()
        if ext in [".jpg", ".jpeg", ".png"]:
            return {"success": True, "info": self._get_image_info(path)}
        elif ext in [".mp3", ".wav"]:
            return {"success": True, "info": self._get_audio_info(path)}
            
        return {"success": False}

    def _get_image_info(self, path: Path) -> Dict[str, Any]:
        """Metadata extraction for images."""
        info = {
            "size_bytes": path.stat().st_size,
            "filename": path.name,
            "extension": path.suffix.lower()
        }
        
        try:
            from PIL import Image
            with Image.open(path) as img:
                info["width"] = img.width
                info["height"] = img.height
                info["format"] = img.format
                info["mode"] = img.mode
        except Exception:
            pass
            
        return info

    def _get_audio_info(self, path: Path) -> Dict[str, Any]:
        """Simple metadata extraction."""
        return {
            "size_bytes": path.stat().st_size,
            "filename": path.name,
            "extension": path.suffix
        }
