from __future__ import annotations
"""
COGS Relationship Extractor
Relationship extraction service for COGS - extracts relationships from text/conversations
Converted from Swift COGSRelationshipExtractor.swift
"""

from typing import Any, Dict, List, Optional
import re
import logging
from dataclasses import dataclass, field
from enum import Enum

from mavaia_core.brain.base_module import BaseBrainModule, ModuleMetadata
from mavaia_core.brain.registry import ModuleRegistry
from mavaia_core.exceptions import InvalidParameterError

# Optional imports - models package may not be available
try:
    from models.context_models import ContextObject, ContextRelationship, RelationshipType
except ImportError:
    # Models not available - define minimal types
    ContextObject = None
    ContextRelationship = None
    RelationshipType = None

logger = logging.getLogger(__name__)


class _FallbackRelationshipType(str, Enum):
    RELATED_TO = "related_to"
    CAUSES = "causes"
    PART_OF = "part_of"
    BEFORE = "before"
    SIMILAR_TO = "similar_to"


@dataclass
class _FallbackContextObject:
    id: str
    label: str = ""
    aliases: List[str] = field(default_factory=list)

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "_FallbackContextObject":
        if not isinstance(data, dict):
            return cls(id="unknown", label="", aliases=[])
        obj_id = data.get("id") or data.get("object_id") or data.get("entity_id") or "unknown"
        label = data.get("label") or data.get("name") or ""
        aliases = data.get("aliases") or []
        if not isinstance(obj_id, str):
            obj_id = str(obj_id)
        if not isinstance(label, str):
            label = str(label)
        if not isinstance(aliases, list):
            aliases = []
        aliases = [str(a) for a in aliases if a is not None]
        return cls(id=obj_id, label=label, aliases=aliases)

    def to_dict(self) -> Dict[str, Any]:
        return {"id": self.id, "label": self.label, "aliases": list(self.aliases)}


@dataclass
class _FallbackContextRelationship:
    id: str
    source_id: str
    target_id: str
    relationship_type: str
    properties: Dict[str, Any] = field(default_factory=dict)
    confidence: float = 0.5

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "_FallbackContextRelationship":
        if not isinstance(data, dict):
            data = {}
        rel_id = data.get("id") or data.get("relationship_id") or "unknown"
        source_id = data.get("source_id") or data.get("source") or ""
        target_id = data.get("target_id") or data.get("target") or ""
        rel_type = data.get("relationship_type") or data.get("type") or ""
        props = data.get("properties") or {}
        conf = data.get("confidence", 0.5)
        if not isinstance(rel_id, str):
            rel_id = str(rel_id)
        if not isinstance(source_id, str):
            source_id = str(source_id)
        if not isinstance(target_id, str):
            target_id = str(target_id)
        if not isinstance(rel_type, str):
            rel_type = str(rel_type)
        if not isinstance(props, dict):
            props = {}
        try:
            conf_f = float(conf)
        except (TypeError, ValueError):
            conf_f = 0.5
        return cls(
            id=rel_id,
            source_id=source_id,
            target_id=target_id,
            relationship_type=rel_type,
            properties=props,
            confidence=conf_f,
        )

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "source_id": self.source_id,
            "target_id": self.target_id,
            "relationship_type": self.relationship_type,
            "properties": dict(self.properties),
            "confidence": self.confidence,
        }


_ContextObject = ContextObject or _FallbackContextObject
_ContextRelationship = ContextRelationship or _FallbackContextRelationship
_RelationshipType = RelationshipType or _FallbackRelationshipType


class ExtractedRelationship:
    """Extracted relationship from text"""

    def __init__(
        self,
        relationship: Optional[ContextRelationship],
        source_entity: ContextObject,
        target_entity: ContextObject,
        relationship_type: RelationshipType,
        confidence: float,
        source_text: str,
    ):
        self.relationship = relationship
        self.source_entity = source_entity
        self.target_entity = target_entity
        self.relationship_type = relationship_type
        self.confidence = confidence
        self.source_text = source_text

    def to_dict(self) -> Dict[str, Any]:
        return {
            "relationship": self.relationship.to_dict() if self.relationship and hasattr(self.relationship, "to_dict") else None,
            "source_entity": self.source_entity.to_dict() if hasattr(self.source_entity, "to_dict") else {"id": self.source_entity.id},
            "target_entity": self.target_entity.to_dict() if hasattr(self.target_entity, "to_dict") else {"id": self.target_entity.id},
            "relationship_type": self.relationship_type.value if hasattr(self.relationship_type, "value") else str(self.relationship_type),
            "confidence": self.confidence,
            "source_text": self.source_text,
        }


class COGSRelationshipExtractorModule(BaseBrainModule):
    """Relationship extraction service for COGS"""

    def __init__(self):
        super().__init__()
        self.cogs_engine = None
        self._modules_loaded = False

    @property
    def metadata(self) -> ModuleMetadata:
        return ModuleMetadata(
            name="cogs_relationship_extractor",
            version="1.0.0",
            description="Relationship extraction service for COGS - extracts relationships from text/conversations",
            operations=[
                "extract_relationships",
                "extract_from_text",
                "extract_from_message",
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
            self.cogs_engine = ModuleRegistry.get_module("cogs_engine")

            self._modules_loaded = True
        except Exception as e:
            logger.debug(
                "Error loading cogs_engine dependency",
                exc_info=True,
                extra={"module_name": "cogs_relationship_extractor", "error_type": type(e).__name__},
            )

    def execute(self, operation: str, params: Dict[str, Any]) -> Dict[str, Any]:
        """Execute an operation"""
        self._ensure_modules_loaded()

        if operation == "extract_relationships":
            return self._extract_relationships(params)
        elif operation == "extract_from_text":
            return self._extract_from_text(params)
        elif operation == "extract_from_message":
            return self._extract_from_message(params)
        else:
            raise InvalidParameterError(
                parameter="operation",
                value=operation,
                reason="Unknown operation for cogs_relationship_extractor",
            )

    def _extract_relationships(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """Extract relationships from text given entities"""
        text = params.get("text", "")
        entities_data = params.get("entities", [])
        conversation_id = params.get("conversation_id")
        message_id = params.get("message_id")

        if text is None:
            text = ""
        if entities_data is None:
            entities_data = []
        if not isinstance(text, str):
            raise InvalidParameterError("text", str(type(text).__name__), "text must be a string")
        if not isinstance(entities_data, list):
            raise InvalidParameterError("entities", str(type(entities_data).__name__), "entities must be a list")

        entities: List[_ContextObject] = []
        for e in entities_data:
            if isinstance(e, dict):
                entities.append(_ContextObject.from_dict(e))
            elif hasattr(e, "id"):
                entities.append(e)

        relationships: List[ExtractedRelationship] = []

        # Extract different relationship types
        relationships.extend(self._extract_basic_relationships(text, entities))
        relationships.extend(self._extract_temporal_relationships(text, entities))
        relationships.extend(self._extract_semantic_relationships(text, entities))

        # Create or update relationships
        created_relationships: List[ExtractedRelationship] = []
        for relationship in relationships:
            try:
                if self.cogs_engine:
                    context_rel = self.cogs_engine.execute(
                        "create_relationship",
                        {
                            "source_id": relationship.source_entity.id,
                            "target_id": relationship.target_entity.id,
                            "relationship_type": relationship.relationship_type.value if hasattr(relationship.relationship_type, "value") else str(relationship.relationship_type),
                            "properties": {},
                            "confidence": relationship.confidence,
                        }
                    )
                    if context_rel.get("success"):
                        # Update relationship with created context relationship
                        relationship.relationship = _ContextRelationship.from_dict(context_rel.get("result", {}))
                created_relationships.append(relationship)
            except Exception as e:
                logger.debug(
                    "Failed to create relationship via cogs_engine",
                    exc_info=True,
                    extra={"module_name": "cogs_relationship_extractor", "error_type": type(e).__name__},
                )

        return {
            "success": True,
            "result": {
                "relationships": [r.to_dict() for r in created_relationships],
                "count": len(created_relationships),
            },
        }

    def _extract_from_text(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """Extract relationships from text"""
        return self._extract_relationships(params)

    def _extract_from_message(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """Extract relationships from a message"""
        message_data = params.get("message", {})
        entities_data = params.get("entities", [])
        conversation_id = params.get("conversation_id")

        text = message_data.get("content", "")
        message_id = message_data.get("id")

        return self._extract_relationships({
            "text": text,
            "entities": entities_data,
            "conversation_id": conversation_id,
            "message_id": message_id,
        })

    def _extract_basic_relationships(
        self,
        text: str,
        entities: List[_ContextObject],
    ) -> List[ExtractedRelationship]:
        """Extract basic relationships from text"""
        relationships: List[ExtractedRelationship] = []

        # Pattern: "A is related to B"
        related_pattern = r"\b([A-Za-z]+(?:\s+[A-Za-z]+)*)\s+(is|are)\s+(related|connected|linked)\s+to\s+([A-Za-z]+(?:\s+[A-Za-z]+)*)\b"

        for match in re.finditer(related_pattern, text, re.IGNORECASE):
            source_text = match.group(1)
            target_text = match.group(4)

            source = self._find_entity(source_text, entities)
            target = self._find_entity(target_text, entities)

            if source and target:
                relationships.append(ExtractedRelationship(
                    relationship=None,
                    source_entity=source,
                    target_entity=target,
                    relationship_type=_RelationshipType.RELATED_TO,
                    confidence=0.6,
                    source_text=text,
                ))

        # Pattern: "A causes B"
        causes_pattern = r"\b([A-Za-z]+(?:\s+[A-Za-z]+)*)\s+(causes|leads to|results in)\s+([A-Za-z]+(?:\s+[A-Za-z]+)*)\b"

        for match in re.finditer(causes_pattern, text, re.IGNORECASE):
            source_text = match.group(1)
            target_text = match.group(3)

            source = self._find_entity(source_text, entities)
            target = self._find_entity(target_text, entities)

            if source and target:
                relationships.append(ExtractedRelationship(
                    relationship=None,
                    source_entity=source,
                    target_entity=target,
                    relationship_type=_RelationshipType.CAUSES,
                    confidence=0.7,
                    source_text=text,
                ))

        # Pattern: "A is part of B"
        part_of_pattern = r"\b([A-Za-z]+(?:\s+[A-Za-z]+)*)\s+(is|are)\s+(part|component|member)\s+of\s+([A-Za-z]+(?:\s+[A-Za-z]+)*)\b"

        for match in re.finditer(part_of_pattern, text, re.IGNORECASE):
            source_text = match.group(1)
            target_text = match.group(4)

            source = self._find_entity(source_text, entities)
            target = self._find_entity(target_text, entities)

            if source and target:
                relationships.append(ExtractedRelationship(
                    relationship=None,
                    source_entity=source,
                    target_entity=target,
                    relationship_type=_RelationshipType.PART_OF,
                    confidence=0.7,
                    source_text=text,
                ))

        return relationships

    def _extract_temporal_relationships(
        self,
        text: str,
        entities: List[_ContextObject],
    ) -> List[ExtractedRelationship]:
        """Extract temporal relationships from text"""
        relationships: List[ExtractedRelationship] = []

        # Pattern: "A happened before B"
        before_pattern = r"\b([A-Za-z]+(?:\s+[A-Za-z]+)*)\s+(happened|occurred|took place)\s+before\s+([A-Za-z]+(?:\s+[A-Za-z]+)*)\b"

        for match in re.finditer(before_pattern, text, re.IGNORECASE):
            source_text = match.group(1)
            target_text = match.group(3)

            source = self._find_entity(source_text, entities)
            target = self._find_entity(target_text, entities)

            if source and target:
                relationships.append(ExtractedRelationship(
                    relationship=None,
                    source_entity=source,
                    target_entity=target,
                    relationship_type=_RelationshipType.BEFORE,
                    confidence=0.6,
                    source_text=text,
                ))

        return relationships

    def _extract_semantic_relationships(
        self,
        text: str,
        entities: List[_ContextObject],
    ) -> List[ExtractedRelationship]:
        """Extract semantic relationships from text"""
        relationships: List[ExtractedRelationship] = []

        # Pattern: "A is similar to B"
        similar_pattern = r"\b([A-Za-z]+(?:\s+[A-Za-z]+)*)\s+(is|are)\s+similar\s+to\s+([A-Za-z]+(?:\s+[A-Za-z]+)*)\b"

        for match in re.finditer(similar_pattern, text, re.IGNORECASE):
            source_text = match.group(1)
            target_text = match.group(3)

            source = self._find_entity(source_text, entities)
            target = self._find_entity(target_text, entities)

            if source and target:
                relationships.append(ExtractedRelationship(
                    relationship=None,
                    source_entity=source,
                    target_entity=target,
                    relationship_type=_RelationshipType.SIMILAR_TO,
                    confidence=0.6,
                    source_text=text,
                ))

        return relationships

    def _find_entity(self, text: str, entities: List[_ContextObject]) -> Optional[_ContextObject]:
        """Find entity by label or alias"""
        text_lower = text.lower()
        for entity in entities:
            label = getattr(entity, "label", "") or ""
            if isinstance(label, str) and label.lower() == text_lower:
                return entity
            aliases = getattr(entity, "aliases", []) or []
            if isinstance(aliases, list):
                for alias in aliases:
                    if isinstance(alias, str) and alias.lower() == text_lower:
                        return entity
        return None

