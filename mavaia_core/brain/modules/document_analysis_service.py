from __future__ import annotations
"""
Document Analysis Service - Document analysis service for Aurora
Converted from Swift DocumentAnalysisService.swift
"""

from typing import Any, Dict, List, Optional
import logging

from mavaia_core.brain.base_module import BaseBrainModule, ModuleMetadata
from mavaia_core.brain.registry import ModuleRegistry
from mavaia_core.exceptions import InvalidParameterError

logger = logging.getLogger(__name__)


class DocumentAnalysisServiceModule(BaseBrainModule):
    """Document analysis service"""

    def __init__(self):
        super().__init__()
        self.cognitive_generator = None
        self._modules_loaded = False
        self._max_document_size = 80 * 1024 * 1024  # 80 MB

    @property
    def metadata(self) -> ModuleMetadata:
        return ModuleMetadata(
            name="document_analysis_service",
            version="1.0.0",
            description="Document analysis service for Aurora",
            operations=[
                "analyze_document",
                "extract_content",
                "summarize_document",
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
            self.cognitive_generator = ModuleRegistry.get_module("cognitive_generator")

            self._modules_loaded = True
        except Exception as e:
            logger.debug(
                "Failed to load document_analysis_service dependencies",
                exc_info=True,
                extra={"module_name": "document_analysis_service", "error_type": type(e).__name__},
            )

    def execute(self, operation: str, params: Dict[str, Any]) -> Dict[str, Any]:
        """Execute an operation"""
        self._ensure_modules_loaded()

        if operation == "analyze_document":
            return self._analyze_document(params)
        elif operation == "extract_content":
            return self._extract_content(params)
        elif operation == "summarize_document":
            return self._summarize_document(params)
        else:
            raise InvalidParameterError(
                parameter="operation",
                value=operation,
                reason="Unknown operation for document_analysis_service",
            )

    def _analyze_document(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """Analyze a document"""
        data = params.get("data")  # bytes
        file_name = params.get("file_name", "")
        mime_type = params.get("mime_type", "")
        if file_name is None:
            file_name = ""
        if mime_type is None:
            mime_type = ""
        if data is not None and not isinstance(data, (bytes, bytearray)):
            raise InvalidParameterError(
                parameter="data",
                value=str(type(data).__name__),
                reason="data must be bytes when provided",
            )
        if not isinstance(file_name, str):
            raise InvalidParameterError("file_name", str(type(file_name).__name__), "file_name must be a string")
        if not isinstance(mime_type, str):
            raise InvalidParameterError("mime_type", str(type(mime_type).__name__), "mime_type must be a string")

        # Check size
        if data and len(data) > self._max_document_size:
            return {
                "success": False,
                "error": "Document exceeds maximum size (80 MB)",
            }

        # Extract text
        extracted_text = self._extract_text(data, file_name, mime_type)

        if not extracted_text:
            return {
                "success": False,
                "error": "Text extraction failed",
            }

        # Analyze with cognitive generator
        if self.cognitive_generator:
            try:
                analysis = self.cognitive_generator.execute("analyze_text", {
                    "text": extracted_text,
                    "file_name": file_name,
                })

                return {
                    "success": True,
                    "file_name": file_name,
                    "extracted_text": extracted_text,
                    "summary": analysis.get("summary", ""),
                    "action_items": analysis.get("action_items", []),
                    "key_points": analysis.get("key_points", []),
                    "character_count": len(extracted_text),
                    "page_count": analysis.get("page_count"),
                }
            except Exception as e:
                logger.debug(
                    "Document analysis failed",
                    exc_info=True,
                    extra={"module_name": "document_analysis_service", "error_type": type(e).__name__},
                )
                return {
                    "success": False,
                    "error": "Analysis failed",
                }

        # Fallback: simple analysis
        return {
            "success": True,
            "file_name": file_name,
            "extracted_text": extracted_text,
            "summary": extracted_text[:200] + "..." if len(extracted_text) > 200 else extracted_text,
            "action_items": [],
            "key_points": [],
            "character_count": len(extracted_text),
            "page_count": None,
        }

    def _extract_content(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """Extract content from document"""
        data = params.get("data")
        file_name = params.get("file_name", "")
        mime_type = params.get("mime_type", "")
        if file_name is None:
            file_name = ""
        if mime_type is None:
            mime_type = ""
        if data is not None and not isinstance(data, (bytes, bytearray)):
            raise InvalidParameterError("data", str(type(data).__name__), "data must be bytes when provided")
        if not isinstance(file_name, str):
            raise InvalidParameterError("file_name", str(type(file_name).__name__), "file_name must be a string")
        if not isinstance(mime_type, str):
            raise InvalidParameterError("mime_type", str(type(mime_type).__name__), "mime_type must be a string")

        extracted_text = self._extract_text(data, file_name, mime_type)

        return {
            "success": extracted_text is not None,
            "content": extracted_text or "",
        }

    def _summarize_document(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """Summarize a document"""
        text = params.get("text", "")
        if text is None:
            text = ""
        if not isinstance(text, str):
            raise InvalidParameterError("text", str(type(text).__name__), "text must be a string")

        if self.cognitive_generator:
            try:
                result = self.cognitive_generator.execute("generate_summary", {
                    "content": text,
                    "max_sentences": params.get("max_sentences", 3),
                })
                return {
                    "success": True,
                    "summary": result.get("summary", ""),
                }
            except Exception as e:
                logger.debug(
                    "Document summarization failed",
                    exc_info=True,
                    extra={"module_name": "document_analysis_service", "error_type": type(e).__name__},
                )
                return {
                    "success": False,
                    "error": "Summarization failed",
                }

        # Fallback: simple summary
        return {
            "success": True,
            "summary": text[:200] + "..." if len(text) > 200 else text,
        }

    def _extract_text(self, data: Optional[bytes], file_name: str, mime_type: str) -> Optional[str]:
        """Extract text from document data"""
        if not data:
            return None

        # Handle different file types
        file_ext = file_name.lower().split(".")[-1] if "." in file_name else ""

        if mime_type == "application/pdf" or file_ext == "pdf":
            # PDF extraction (would need PyPDF2 or similar)
            try:
                # Fallback: try to decode as text
                return data.decode("utf-8", errors="ignore")
            except Exception as e:
                logger.debug(
                    "PDF decode failed",
                    exc_info=True,
                    extra={"module_name": "document_analysis_service", "error_type": type(e).__name__},
                )
                return None
        elif file_ext in ["md", "markdown"] or "markdown" in mime_type:
            return data.decode("utf-8", errors="ignore")
        elif "text" in mime_type or file_ext == "txt":
            return data.decode("utf-8", errors="ignore")
        elif file_ext == "rtf" or mime_type == "text/rtf":
            # RTF extraction (simplified)
            return data.decode("utf-8", errors="ignore")
        else:
            # Try UTF-8 as fallback
            try:
                return data.decode("utf-8", errors="ignore")
            except Exception as e:
                logger.debug(
                    "Text decode failed",
                    exc_info=True,
                    extra={"module_name": "document_analysis_service", "error_type": type(e).__name__},
                )
                return None

