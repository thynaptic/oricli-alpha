"""
COGS Relationship Extractor
Relationship extraction service for COGS - extracts relationships from text/conversations
Converted from Swift COGSRelationshipExtractor.swift
"""

from typing import Any, Dict, List, Optional
import sys
import re
from pathlib import Path

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent))

from mavaia_core.brain.base_module import BaseBrainModule, ModuleMetadata

# Optional imports - models package may not be available
try:
    from models.context_models import ContextObject, ContextRelationship, RelationshipType
except ImportError:
    # Models not available - define minimal types
    ContextObject = None
    ContextRelationship = None
    RelationshipType = None


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
            from module_registry import ModuleRegistry

            self.cogs_engine = ModuleRegistry.get_module("cogs_engine")

            self._modules_loaded = True
        except Exception as e:
            print(f"Error loading modules: {e}")

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
            raise ValueError(f"Unknown operation: {operation}")

    def _extract_relationships(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """Extract relationships from text given entities"""
        text = params.get("text", "")
        entities_data = params.get("entities", [])
        conversation_id = params.get("conversation_id")
        message_id = params.get("message_id")

        entities = [
            ContextObject.from_dict(e) if isinstance(e, dict) else e
            for e in entities_data
        ]

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
                        relationship.relationship = ContextRelationship.from_dict(context_rel.get("result", {}))
                created_relationships.append(relationship)
            except Exception as e:
                print(f"Failed to create relationship: {e}")

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
        entities: List[ContextObject],
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
                    relationship_type=RelationshipType.RELATED_TO,
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
                    relationship_type=RelationshipType.CAUSES,
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
                    relationship_type=RelationshipType.PART_OF,
                    confidence=0.7,
                    source_text=text,
                ))

        return relationships

    def _extract_temporal_relationships(
        self,
        text: str,
        entities: List[ContextObject],
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
                    relationship_type=RelationshipType.BEFORE,
                    confidence=0.6,
                    source_text=text,
                ))

        return relationships

    def _extract_semantic_relationships(
        self,
        text: str,
        entities: List[ContextObject],
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
                    relationship_type=RelationshipType.SIMILAR_TO,
                    confidence=0.6,
                    source_text=text,
                ))

        return relationships

    def _find_entity(self, text: str, entities: List[ContextObject]) -> Optional[ContextObject]:
        """Find entity by label or alias"""
        text_lower = text.lower()
        for entity in entities:
            if entity.label.lower() == text_lower:
                return entity
            for alias in entity.aliases:
                if alias.lower() == text_lower:
                    return entity
        return None

