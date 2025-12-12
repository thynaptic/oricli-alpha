"""
COGS Engine
Context Object Graph System (COGS) Engine - Main service for managing context objects and relationships
Converted from Swift COGSEngine.swift
"""

from typing import Any, Dict, List, Optional
import sys
from pathlib import Path

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent))

from mavaia_core.brain.base_module import BaseBrainModule, ModuleMetadata

# Optional imports - models package may not be available
try:
from models.context_models import ContextObject, ContextRelationship, EntityType as ContextEntityType
except ImportError:
    # Models not available - define minimal types
    ContextObject = None
    ContextRelationship = None
    ContextEntityType = None


class COGSEngineModule(BaseBrainModule):
    """Main service for managing context objects and relationships"""

    def __init__(self):
        self.embeddings_service = None
        self._modules_loaded = False
        # In-memory storage for entities and relationships
        self._entities: Dict[str, ContextObject] = {}
        self._relationships: List[ContextRelationship] = []

    @property
    def metadata(self) -> ModuleMetadata:
        return ModuleMetadata(
            name="cogs_engine",
            version="1.0.0",
            description="Context Object Graph System (COGS) Engine - Main service for managing context objects and relationships",
            operations=[
                "create_entity",
                "get_entity",
                "find_entities",
                "update_entity",
                "delete_entity",
                "create_relationship",
                "get_relationships",
                "query_graph",
                "build_graph",
                "extract_entities",
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

            self.embeddings_service = ModuleRegistry.get_module("embeddings")

            self._modules_loaded = True
        except Exception as e:
            print(f"Error loading modules: {e}")

    def execute(self, operation: str, params: Dict[str, Any]) -> Dict[str, Any]:
        """Execute an operation"""
        self._ensure_modules_loaded()

        if operation == "create_entity":
            return self._create_entity(params)
        elif operation == "get_entity":
            return self._get_entity(params)
        elif operation == "find_entities":
            return self._find_entities(params)
        elif operation == "update_entity":
            return self._update_entity(params)
        elif operation == "delete_entity":
            return self._delete_entity(params)
        elif operation == "create_relationship":
            return self._create_relationship(params)
        elif operation == "get_relationships":
            return self._get_relationships(params)
        elif operation == "query_graph":
            return self._query_graph(params)
        elif operation == "build_graph":
            return self._build_graph(params)
        elif operation == "extract_entities":
            return self._extract_entities(params)
        else:
            raise ValueError(f"Unknown operation: {operation}")

    def _create_entity(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """Create a new context object"""
        entity_type = params.get("type")
        label = params.get("label", "")
        description = params.get("description")
        properties = params.get("properties", {})
        confidence = params.get("confidence", 0.5)
        aliases = params.get("aliases", [])

        # Generate embedding for the entity
        embedding = []
        if self.embeddings_service:
            try:
                embedding_result = self.embeddings_service.execute(
                    "generate_embeddings",
                    {"text": label + (description or "")}
                )
                embedding = embedding_result.get("result", {}).get("embedding", [])
            except Exception:
                pass

        # Create entity
        entity = ContextObject(
            entity_type=ContextEntityType(entity_type) if entity_type else ContextEntityType.CONCEPT,
            label=label,
            description=description,
            properties=properties,
            confidence=confidence,
            aliases=aliases,
        )

        if embedding:
            entity.embedding = embedding

        # Store entity in memory
        self._entities[entity.id] = entity

        return {
            "success": True,
            "result": entity.to_dict() if hasattr(entity, "to_dict") else {
                "id": entity.id,
                "entity_type": entity.entity_type.value,
                "label": entity.label,
                "description": entity.description,
            },
        }

    def _get_entity(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """Get entity by ID"""
        entity_id = params.get("entity_id")

        if not entity_id:
            return {
                "success": False,
                "error": "entity_id is required",
            }

        entity = self._entities.get(entity_id)
        if not entity:
            return {
                "success": False,
                "error": f"Entity {entity_id} not found",
            }

        return {
            "success": True,
            "result": entity.to_dict() if hasattr(entity, "to_dict") else {
                "id": entity.id,
                "entity_type": entity.entity_type.value,
                "label": entity.label,
                "description": entity.description,
            },
        }

    def _find_entities(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """Find entities by label or alias"""
        query = params.get("query", "").lower()
        entity_type = params.get("type")
        limit = params.get("limit", 20)

        matching_entities = []
        for entity in self._entities.values():
            if entity_type and entity.entity_type.value != entity_type:
                continue
            if query:
                # Match by label or alias
                if query in entity.label.lower():
                    matching_entities.append(entity)
                elif any(query in alias.lower() for alias in entity.aliases):
                    matching_entities.append(entity)
            else:
                matching_entities.append(entity)

        # Limit results
        matching_entities = matching_entities[:limit]

        return {
            "success": True,
            "result": {
                "entities": [e.to_dict() if hasattr(e, "to_dict") else {
                    "id": e.id,
                    "entity_type": e.entity_type.value,
                    "label": e.label,
                    "description": e.description,
                } for e in matching_entities],
                "count": len(matching_entities),
            },
        }

    def _update_entity(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """Update entity"""
        entity_id = params.get("entity_id")

        if not entity_id:
            return {
                "success": False,
                "error": "entity_id is required",
            }

        entity = self._entities.get(entity_id)
        if not entity:
            return {
                "success": False,
                "error": f"Entity {entity_id} not found",
            }

        # Update fields if provided
        if "label" in params:
            entity.label = params["label"]
        if "description" in params:
            entity.description = params["description"]
        if "properties" in params:
            entity.properties.update(params["properties"])
        if "confidence" in params:
            entity.confidence = params["confidence"]
        if "aliases" in params:
            entity.aliases = params["aliases"]

        return {
            "success": True,
            "result": entity.to_dict() if hasattr(entity, "to_dict") else {
                "id": entity.id,
                "entity_type": entity.entity_type.value,
                "label": entity.label,
                "description": entity.description,
            },
        }

    def _delete_entity(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """Delete entity"""
        entity_id = params.get("entity_id")

        if not entity_id:
            return {
                "success": False,
                "error": "entity_id is required",
            }

        if entity_id not in self._entities:
            return {
                "success": False,
                "error": f"Entity {entity_id} not found",
            }

        # Remove entity and its relationships
        del self._entities[entity_id]
        self._relationships = [r for r in self._relationships 
                               if r.source_id != entity_id and r.target_id != entity_id]

        return {
            "success": True,
            "result": {"deleted": entity_id},
        }

    def _create_relationship(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """Create a relationship between entities"""
        source_id = params.get("source_id")
        target_id = params.get("target_id")
        relationship_type = params.get("relationship_type")
        properties = params.get("properties", {})
        confidence = params.get("confidence", 0.5)

        relationship = ContextRelationship(
            source_id=source_id,
            target_id=target_id,
            relationship_type=relationship_type,
            properties=properties,
            confidence=confidence,
        )

        # Store relationship
        self._relationships.append(relationship)

        return {
            "success": True,
            "result": relationship.to_dict() if hasattr(relationship, "to_dict") else {
                "source_id": relationship.source_id,
                "target_id": relationship.target_id,
                "relationship_type": relationship.relationship_type.value if hasattr(relationship.relationship_type, "value") else str(relationship.relationship_type),
            },
        }

    def _get_relationships(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """Get relationships for an entity"""
        entity_id = params.get("entity_id")

        if not entity_id:
            return {
                "success": False,
                "error": "entity_id is required",
            }

        # Find all relationships involving this entity
        relationships = [
            r for r in self._relationships
            if r.source_id == entity_id or r.target_id == entity_id
        ]

        return {
            "success": True,
            "result": {
                "relationships": [r.to_dict() if hasattr(r, "to_dict") else {
                    "source_id": r.source_id,
                    "target_id": r.target_id,
                    "relationship_type": r.relationship_type.value if hasattr(r.relationship_type, "value") else str(r.relationship_type),
                } for r in relationships],
                "count": len(relationships),
            },
        }

    def _query_graph(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """Query the COGS graph"""
        query = params.get("query", "").lower()
        entity_type = params.get("entity_type")
        limit = params.get("limit", 20)

        # Find matching entities
        matching_entities = []
        for entity in self._entities.values():
            if entity_type and entity.entity_type.value != entity_type:
                continue
            if query:
                if query in entity.label.lower() or query in (entity.description or "").lower():
                    matching_entities.append(entity)
            else:
                matching_entities.append(entity)

        matching_entities = matching_entities[:limit]

        # Find relationships for matching entities
        entity_ids = {e.id for e in matching_entities}
        matching_relationships = [
            r for r in self._relationships
            if r.source_id in entity_ids or r.target_id in entity_ids
        ]

        return {
            "success": True,
            "result": {
                "entities": [e.to_dict() if hasattr(e, "to_dict") else {
                    "id": e.id,
                    "entity_type": e.entity_type.value,
                    "label": e.label,
                    "description": e.description,
                } for e in matching_entities],
                "relationships": [r.to_dict() if hasattr(r, "to_dict") else {
                    "source_id": r.source_id,
                    "target_id": r.target_id,
                    "relationship_type": r.relationship_type.value if hasattr(r.relationship_type, "value") else str(r.relationship_type),
                } for r in matching_relationships],
            },
        }

    def _build_graph(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """Build graph from text"""
        text = params.get("text", "")

        # Extract entities and relationships from text
        entities = self._extract_entities_internal(text)
        relationships = []  # Would be extracted from text

        return {
            "success": True,
            "result": {
                "entities": [e.to_dict() if hasattr(e, "to_dict") else {"id": e.id, "label": e.label} for e in entities],
                "relationships": relationships,
            },
        }

    def _extract_entities(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """Extract entities from text"""
        text = params.get("text", "")

        entities = self._extract_entities_internal(text)

        return {
            "success": True,
            "result": {
                "entities": [e.to_dict() if hasattr(e, "to_dict") else {"id": e.id, "label": e.label} for e in entities],
                "count": len(entities),
            },
        }

    def _extract_entities_internal(self, text: str) -> List[ContextObject]:
        """Internal method to extract entities from text"""
        entities = []
        
        # Basic entity extraction using simple heuristics
        # In a production system, this would use a proper NLP entity extraction service
        if not text:
            return entities

        # Try to use entity extraction service if available
        try:
            from module_registry import ModuleRegistry
            entity_extractor = ModuleRegistry.get_module("cogs_relationship_extractor")
            if entity_extractor:
                result = entity_extractor.execute("extract_entities", {"text": text})
                if result.get("success"):
                    extracted = result.get("result", {}).get("entities", [])
                    for entity_data in extracted:
                        entity = ContextObject(
                            entity_type=ContextEntityType(entity_data.get("type", "CONCEPT")),
                            label=entity_data.get("label", ""),
                            description=entity_data.get("description"),
                            properties=entity_data.get("properties", {}),
                            confidence=entity_data.get("confidence", 0.5),
                            aliases=entity_data.get("aliases", []),
                        )
                        entities.append(entity)
                    return entities
        except Exception:
            pass

        # Fallback: simple extraction based on capitalization and common patterns
        words = text.split()
        current_entity = []
        for word in words:
            if word and word[0].isupper() and len(word) > 2:
                current_entity.append(word)
            else:
                if current_entity:
                    label = " ".join(current_entity)
                    if len(label) > 2:
                        entity = ContextObject(
                            entity_type=ContextEntityType.CONCEPT,
                            label=label,
                            description=None,
                            properties={},
                            confidence=0.3,
                            aliases=[],
                        )
                        entities.append(entity)
                    current_entity = []

        return entities

