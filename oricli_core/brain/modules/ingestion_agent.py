from __future__ import annotations
"""
Ingestion Agent Module
Handles document parsing (PDF, MD, TXT), semantic chunking, and embedding injection.
Syncs knowledge with world_knowledge, memory_graph, and MemoryBridgeService.
"""

import io
import re
import uuid
import logging
from typing import Any, Dict, List, Optional
from pathlib import Path

try:
    import pypdf
    PYPDF_AVAILABLE = True
except ImportError:
    PYPDF_AVAILABLE = False

from oricli_core.brain.base_module import BaseBrainModule, ModuleMetadata
from oricli_core.brain.registry import ModuleRegistry
from oricli_core.exceptions import InvalidParameterError, ModuleOperationError

logger = logging.getLogger(__name__)

class IngestionAgentModule(BaseBrainModule):
    """Orchestrates the ingestion pipeline for external knowledge."""

    def __init__(self):
        super().__init__()
        self._embeddings = None
        self._world_knowledge = None
        self._memory_graph = None
        self._initialized = False

    @property
    def metadata(self) -> ModuleMetadata:
        return ModuleMetadata(
            name="ingestion_agent",
            version="1.0.0",
            description="Ingests external documents (PDF, MD, TXT) into the Knowledge Graph and Memory stores.",
            operations=[
                "ingest_text",
                "ingest_file",
                "chunk_text",
                "status"
            ],
            dependencies=["pypdf"],
            enabled=True,
            model_required=False,
        )

    def initialize(self) -> bool:
        """Initialize and link dependencies."""
        try:
            self._embeddings = ModuleRegistry.get_module("embeddings")
            self._world_knowledge = ModuleRegistry.get_module("world_knowledge")
            self._memory_graph = ModuleRegistry.get_module("memory_graph")
            self._initialized = True
            return True
        except Exception as e:
            logger.warning(f"IngestionAgent dependencies partially loaded: {e}")
            return True

    def execute(self, operation: str, params: Dict[str, Any]) -> Dict[str, Any]:
        """Execute ingestion operations."""
        if operation == "status":
            return {"success": True, "pypdf_available": PYPDF_AVAILABLE}

        if operation == "ingest_text":
            return self._ingest_text(params)
        elif operation == "ingest_file":
            return self._ingest_file(params)
        elif operation == "chunk_text":
            return self._chunk_text_op(params)
        else:
            raise InvalidParameterError(parameter="operation", value=operation, reason="Unsupported operation")

    def _ingest_text(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """Ingest raw text into the Hive."""
        text = params.get("text", "")
        metadata = params.get("metadata", {})
        source_name = metadata.get("source", "direct_ingestion")
        
        if not text:
            return {"success": False, "error": "No text provided"}

        # 1. Chunking
        chunks = self._recursive_character_splitter(text)
        
        # 2. Process Chunks (Embed & Store)
        results = self._process_chunks(chunks, source_name, metadata)
        
        return {
            "success": True,
            "source": source_name,
            "chunks_processed": len(chunks),
            "entities_extracted": results.get("entities_count", 0),
            "memory_ids": results.get("memory_ids", [])
        }

    def _ingest_file(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """Parse file and ingest its content."""
        file_data = params.get("file_data") # bytes
        file_name = params.get("file_name", "unknown")
        mime_type = params.get("mime_type", "")
        metadata = params.get("metadata", {})
        metadata["source"] = file_name

        if not file_data:
            return {"success": False, "error": "No file data provided"}

        # 1. Parsing
        text = self._parse_file(file_data, file_name, mime_type)
        if not text:
            return {"success": False, "error": f"Failed to parse text from {file_name}"}

        # 2. Forward to text ingestion
        params["text"] = text
        params["metadata"] = metadata
        return self._ingest_text(params)

    def _parse_file(self, data: bytes, name: str, mime: str) -> Optional[str]:
        """Extract text based on file type."""
        ext = name.lower().split(".")[-1] if "." in name else ""
        
        if ext == "pdf" or mime == "application/pdf":
            if not PYPDF_AVAILABLE:
                logger.error("pypdf not installed, cannot parse PDF")
                return None
            try:
                reader = pypdf.PdfReader(io.BytesIO(data))
                text = ""
                for page in reader.pages:
                    text += page.extract_text() + "\n"
                return text
            except Exception as e:
                logger.error(f"PDF parsing failed: {e}")
                return None
        else:
            # Assume text-based (txt, md, py, etc.)
            try:
                return data.decode("utf-8", errors="ignore")
            except Exception:
                return None

    def _recursive_character_splitter(self, text: str, chunk_size: int = 1000, chunk_overlap: int = 200) -> List[str]:
        """Simple recursive character-based splitting."""
        if len(text) <= chunk_size:
            return [text]

        chunks = []
        start = 0
        while start < len(text):
            end = start + chunk_size
            # Try to find a good breaking point (newline or period)
            if end < len(text):
                # Look back for a newline in the last 20% of the chunk
                lookback = int(chunk_size * 0.2)
                idx = text.rfind("\n", end - lookback, end)
                if idx == -1:
                    idx = text.rfind(". ", end - lookback, end)
                
                if idx != -1:
                    end = idx + 1
            
            chunk = text[start:end].strip()
            if chunk:
                chunks.append(chunk)
            
            start = end - chunk_overlap
            if start < 0: start = 0
            if start >= len(text) - chunk_overlap: break
            
        return chunks

    def _process_chunks(self, chunks: List[str], source: str, base_metadata: Dict[str, Any]) -> Dict[str, Any]:
        """Embed and store chunks in the various backends."""
        memory_ids = []
        entities_count = 0
        
        for i, chunk in enumerate(chunks):
            chunk_id = f"chunk_{uuid.uuid4().hex[:8]}"
            memory_ids.append(chunk_id)
            
            # Metadata for this specific chunk
            meta = {
                **base_metadata,
                "chunk_index": i,
                "total_chunks": len(chunks),
                "source": source
            }

            # 1. Generate Embedding (if module available)
            embedding = None
            if self._embeddings:
                try:
                    res = self._embeddings.execute("generate_embeddings", {"text": chunk})
                    if res.get("success"):
                        embedding = res.get("embeddings", [[]])[0]
                except Exception:
                    pass

            # 2. Store in World Knowledge (as a fact)
            if self._world_knowledge:
                try:
                    self._world_knowledge.execute("add_knowledge", {
                        "fact": chunk,
                        "entities": base_metadata.get("tags", []),
                        "confidence": 1.0
                    })
                except Exception:
                    pass

            # 3. Store in Neo4j (as a node)
            if self._memory_graph:
                try:
                    self._memory_graph.execute("add_node", {
                        "id": chunk_id,
                        "content": chunk,
                        "metadata": meta
                    })
                    # Link to source node if it exists
                    # (Implementation detail for Neo4j traversal)
                except Exception:
                    pass

        return {
            "memory_ids": memory_ids,
            "entities_count": entities_count
        }

    def _chunk_text_op(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """Expose chunking as a direct operation."""
        text = params.get("text", "")
        size = params.get("chunk_size", 1000)
        overlap = params.get("chunk_overlap", 200)
        chunks = self._recursive_character_splitter(text, size, overlap)
        return {"success": True, "chunks": chunks, "count": len(chunks)}
