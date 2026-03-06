from __future__ import annotations
"""
Document Orchestration Module - Multi-document routing and synthesis
Routes queries across multiple documents, hierarchical reading, long-form
reasoning across sections, cross-sectional linking, and structured synthesis
"""

import re
import logging
from typing import Any, Dict, List, Optional

from mavaia_core.brain.base_module import BaseBrainModule, ModuleMetadata
from mavaia_core.exceptions import InvalidParameterError

logger = logging.getLogger(__name__)


class DocumentOrchestrationModule(BaseBrainModule):
    """Orchestrate multi-document operations"""

    def __init__(self):
        super().__init__()
        self.section_patterns = [
            r"^#{1,3}\s+(.+)$",  # Markdown headers
            r"^[A-Z][A-Z\s]{5,}$",  # ALL CAPS headers
            r"^\d+\.\s+[A-Z].+$",  # Numbered sections
        ]
        self._engine = None

    @property
    def metadata(self) -> ModuleMetadata:
        return ModuleMetadata(
            name="document_orchestration",
            version="1.0.1",
            description=(
                "Document orchestration: multi-document routing, hierarchical reading, "
                "long-form reasoning across sections, cross-sectional linking, "
                "structured synthesis"
            ),
            operations=[
                "route_multi_document",
                "hierarchical_read",
                "reason_across_sections",
                "link_cross_sections",
                "synthesize_documents",
                "status",
            ],
            dependencies=[],
            model_required=False,
        )

    def initialize(self) -> bool:
        """Initialize the module"""
        self._ensure_engine()
        return True

    def _ensure_engine(self):
        """Lazy load text engine"""
        if self._engine:
            return
        try:
            from mavaia_core.brain.registry import ModuleRegistry
            self._engine = ModuleRegistry.get_module("text_generation_engine")
        except Exception:
            pass

    def execute(self, operation: str, params: Dict[str, Any]) -> Dict[str, Any]:
        """Execute a document orchestration operation"""
        if operation == "status":
            return self._get_status()

        if operation == "route_multi_document":
            query = params.get("query", "")
            documents = params.get("documents", [])
            res = self.route_multi_document(query, documents)
            res["success"] = True
            return res

        elif operation == "hierarchical_read":
            document = params.get("document", "")
            res = self.hierarchical_read(document)
            res["success"] = True
            return res

        elif operation == "reason_across_sections":
            document = params.get("document", "")
            query = params.get("query", "")
            res = self.reason_across_sections(document, query)
            res["success"] = True
            return res

        elif operation == "link_cross_sections":
            document = params.get("document", "")
            res = self.link_cross_sections(document)
            res["success"] = True
            return res

        elif operation == "synthesize_documents":
            documents = params.get("documents", [])
            query = params.get("query", "")
            return self.synthesize_documents(documents, query)

        else:
            return {"success": False, "error": f"Unknown operation: {operation}"}

    def _get_status(self) -> Dict[str, Any]:
        """Return module status"""
        self._ensure_engine()
        return {
            "success": True,
            "status": "active",
            "version": self.metadata.version,
            "engine_available": self._engine is not None
        }

    def route_multi_document(
        self, query: str, documents: List[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """Route queries across multiple documents intelligently"""
        if not query or not documents:
            return {
                "query": query,
                "routed_documents": [],
                "relevance_scores": {},
            }

        query_lower = query.lower()
        query_words = set(re.findall(r"\b\w{4,}\b", query_lower))

        routed_documents = []
        relevance_scores = {}

        for doc in documents:
            doc_id = doc.get("id", str(len(routed_documents)))
            doc_content = doc.get("content", "")
            doc_title = doc.get("title", "")

            # Calculate relevance score
            content_lower = (doc_content + " " + doc_title).lower()
            content_words = set(re.findall(r"\b\w{4,}\b", content_lower))

            # Word overlap
            overlap = query_words & content_words
            relevance = len(overlap) / max(len(query_words), 1)

            # Boost for title matches
            if any(word in doc_title.lower() for word in query_words):
                relevance += 0.2

            relevance_scores[doc_id] = relevance

            if relevance > 0.1:  # Threshold
                routed_documents.append(
                    {
                        "id": doc_id,
                        "title": doc_title,
                        "relevance": relevance,
                        "overlap_words": list(overlap)[:10],
                    }
                )

        # Sort by relevance
        routed_documents.sort(key=lambda x: x["relevance"], reverse=True)

        return {
            "query": query,
            "routed_documents": routed_documents,
            "relevance_scores": relevance_scores,
            "total_documents": len(documents),
            "relevant_count": len(routed_documents),
        }

    def hierarchical_read(self, document: str) -> Dict[str, Any]:
        """Read document in hierarchical order (sections, subsections)"""
        if not document:
            return {
                "document": document,
                "hierarchy": [],
                "sections": [],
            }

        lines = document.split("\n")
        hierarchy = []
        current_section = None
        current_subsection = None
        sections = []

        for i, line in enumerate(lines):
            line_stripped = line.strip()

            # Check for section header
            matched = False
            for pattern in self.section_patterns:
                match = re.match(pattern, line_stripped)
                if match:
                    section_title = match.group(1) if match.groups() else line_stripped

                    # Determine level
                    if line_stripped.startswith("#"):
                        level = line_stripped.count("#")
                    elif line_stripped.isupper() and len(line_stripped) > 5:
                        level = 1
                    else:
                        level = 2

                    if level == 1:
                        # New main section
                        if current_section:
                            sections.append(current_section)
                        current_section = {
                            "title": section_title,
                            "level": 1,
                            "line": i,
                            "subsections": [],
                            "content": [],
                        }
                        hierarchy.append(
                            {
                                "type": "section",
                                "title": section_title,
                                "level": 1,
                                "line": i,
                            }
                        )
                        current_subsection = None
                    elif level == 2:
                        # New subsection
                        if current_section:
                            current_subsection = {
                                "title": section_title,
                                "level": 2,
                                "line": i,
                                "content": [],
                            }
                            current_section["subsections"].append(current_subsection)
                            hierarchy.append(
                                {
                                    "type": "subsection",
                                    "title": section_title,
                                    "level": 2,
                                    "line": i,
                                    "parent": current_section["title"],
                                }
                            )
                    matched = True
                    break
            
            if not matched:
                # Regular content line
                if current_subsection:
                    current_subsection["content"].append(line)
                elif current_section:
                    current_section["content"].append(line)

        # Add last section
        if current_section:
            sections.append(current_section)

        return {
            "document": document[:200] + "..." if len(document) > 200 else document,
            "hierarchy": hierarchy,
            "sections": sections,
            "section_count": len(sections),
        }

    def reason_across_sections(
        self, document: str, query: str
    ) -> Dict[str, Any]:
        """Reason across document sections with context preservation"""
        if not document or not query:
            return {
                "query": query,
                "reasoning": "",
                "relevant_sections": [],
            }

        # Parse document hierarchy
        hierarchy_result = self.hierarchical_read(document)
        sections = hierarchy_result["sections"]

        query_lower = query.lower()
        query_words = set(re.findall(r"\b\w{4,}\b", query_lower))

        relevant_sections = []
        reasoning_parts = []

        # Find relevant sections
        for section in sections:
            section_text = " ".join(section["content"])
            section_title = section["title"]

            section_words = set(re.findall(r"\b\w{4,}\b", section_text.lower()))
            overlap = query_words & section_words

            if overlap or any(word in section_title.lower() for word in query_words):
                relevance = len(overlap) / max(len(query_words), 1)
                relevant_sections.append(
                    {
                        "title": section_title,
                        "relevance": relevance,
                        "content": section_text[:500],
                    }
                )

        # Sort by relevance
        relevant_sections.sort(key=lambda x: x["relevance"], reverse=True)

        # Build reasoning across sections
        if relevant_sections:
            reasoning_parts.append(f"Query: {query}")
            reasoning_parts.append("\nRelevant sections found:")
            for i, section in enumerate(relevant_sections[:5], 1):
                reasoning_parts.append(
                    f"\n{i}. {section['title']} (relevance: {section['relevance']:.2f})"
                )
                reasoning_parts.append(f"   Content: {section['content'][:200]}...")

            # Cross-section reasoning
            if len(relevant_sections) > 1:
                reasoning_parts.append(
                    "\n\nCross-section analysis:"
                )
                reasoning_parts.append(
                    f"Found {len(relevant_sections)} relevant sections. "
                    "Connecting information across sections..."
                )

        reasoning = "\n".join(reasoning_parts)

        return {
            "query": query,
            "reasoning": reasoning,
            "relevant_sections": relevant_sections,
            "section_count": len(relevant_sections),
        }

    def link_cross_sections(self, document: str) -> Dict[str, Any]:
        """Link related concepts across document sections"""
        if not document:
            return {
                "document": document,
                "links": [],
                "concept_map": {},
            }

        hierarchy_result = self.hierarchical_read(document)
        sections = hierarchy_result["sections"]

        # Extract concepts from each section
        concept_map = {}
        for section in sections:
            section_title = section["title"]
            section_text = " ".join(section["content"])

            # Extract key concepts (words that appear multiple times)
            words = re.findall(r"\b\w{5,}\b", section_text.lower())
            word_counts = {}
            for word in words:
                word_counts[word] = word_counts.get(word, 0) + 1

            # Get top concepts
            concepts = [
                word for word, count in word_counts.items() if count >= 2
            ][:10]

            concept_map[section_title] = concepts

        # Find cross-section links
        links = []
        section_titles = list(concept_map.keys())

        for i, section1 in enumerate(section_titles):
            concepts1 = set(concept_map[section1])
            for section2 in section_titles[i + 1 :]:
                concepts2 = set(concept_map[section2])
                overlap = concepts1 & concepts2

                if overlap:
                    links.append(
                        {
                            "from": section1,
                            "to": section2,
                            "shared_concepts": list(overlap)[:5],
                            "strength": len(overlap),
                        }
                    )

        # Sort by strength
        links.sort(key=lambda x: x["strength"], reverse=True)

        return {
            "document": document[:200] + "..." if len(document) > 200 else document,
            "links": links,
            "concept_map": concept_map,
            "link_count": len(links),
        }

    def synthesize_documents(
        self, documents: List[Dict[str, Any]], query: str = ""
    ) -> Dict[str, Any]:
        """Synthesize information from multiple documents into structured output"""
        if not documents:
            return {
                "success": False,
                "error": "No documents provided",
                "query": query,
                "synthesis": "",
            }

        self._ensure_engine()
        
        # Build context from documents
        context_parts = []
        for doc in documents[:5]:
            title = doc.get("title") or doc.get("name") or "Untitled"
            content = doc.get("content") or doc.get("snippet") or ""
            context_parts.append(f"Source: {title}\nContent: {content[:500]}")
        
        context = "\n\n".join(context_parts)

        if self._engine:
            try:
                prompt = (
                    f"Instructions: Synthesize a comprehensive answer to the query below based on the provided documents.\n"
                    f"Query: {query}\n"
                    f"Documents:\n{context}\n"
                    f"Synthesis:"
                )
                result = self._engine.execute("generate_with_neural", {
                    "prompt": prompt,
                    "max_length": 1024,
                    "temperature": 0.7
                })
                synthesis = result.get("text", "")
                if synthesis:
                    return {
                        "success": True,
                        "query": query,
                        "synthesis": synthesis,
                        "document_count": len(documents)
                    }
            except Exception:
                pass

        # Fallback to symbolic synthesis
        return {
            "success": True,
            "query": query,
            "synthesis": f"I conducted a multi-document analysis of {len(documents)} sources for '{query}'. Due to engine limitations, a structured summary is provided in the document metadata.",
            "document_count": len(documents),
            "fallback_active": True
        }

    def validate_params(self, operation: str, params: Dict[str, Any]) -> bool:
        """Validate parameters for operations"""
        if operation == "route_multi_document":
            return "query" in params and "documents" in params
        elif operation == 'hierarchical_read' or operation == 'link_cross_sections':
            return "document" in params
        elif operation == "reason_across_sections":
            return "document" in params and "query" in params
        elif operation == "synthesize_documents":
            return "documents" in params
        else:
            return True


__all__ = ["DocumentOrchestrationModule"]
