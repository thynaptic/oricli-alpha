from __future__ import annotations
"""
Mavaia Cognitive Types - Structured models for internal cognitive state
"""

from typing import Any, Dict, List, Optional, Union
from pydantic import BaseModel, Field
from datetime import datetime


class ThoughtStep(BaseModel):
    """A single step in a reasoning trace"""
    step_id: str = Field(..., description="Unique ID for this reasoning step")
    module: str = Field(..., description="Module that generated this step")
    content: str = Field(..., description="Textual description of the thought")
    confidence: float = Field(default=1.0, ge=0.0, le=1.0, description="Confidence in this step")
    timestamp: datetime = Field(default_factory=datetime.now)
    metadata: Dict[str, Any] = Field(default_factory=dict)


class ContextWindow(BaseModel):
    """Active context for the current generation task"""
    active_tokens: int = Field(default=0, description="Current token count in context")
    max_tokens: int = Field(default=32768, description="Maximum context window size")
    retrieved_snippets: List[Dict[str, Any]] = Field(default_factory=list, description="Relevant memory snippets")
    session_history_depth: int = Field(default=0, description="Number of previous turns included")


class GenerationParameters(BaseModel):
    """Parameters controlling the final text synthesis"""
    temperature: float = Field(default=0.7, ge=0.0, le=2.0)
    top_p: float = Field(default=1.0, ge=0.0, le=1.0)
    max_new_tokens: int = Field(default=1024)
    voice_style: Optional[str] = Field(default=None, description="Identifier for universal voice style")
    stop_sequences: List[str] = Field(default_factory=list)


class CognitiveState(BaseModel):
    """Unified state model for module-to-module communication"""
    state_id: str = Field(..., description="Unique session or task state ID")
    thought_trace: List[ThoughtStep] = Field(default_factory=list, description="Ordered reasoning steps")
    context: ContextWindow = Field(default_factory=ContextWindow)
    params: GenerationParameters = Field(default_factory=GenerationParameters)
    
    # Internal tracking
    current_stage: str = Field(default="initialization", description="Current cognitive stage (reasoning, synthesis, rendering)")
    latency_ms: Dict[str, float] = Field(default_factory=dict, description="Latency breakdown per module/stage")
    metadata: Dict[str, Any] = Field(default_factory=dict)
    
    def add_thought(self, module: str, content: str, confidence: float = 1.0, **metadata) -> None:
        """Helper to append a thought step"""
        import uuid
        step = ThoughtStep(
            step_id=str(uuid.uuid4()),
            module=module,
            content=content,
            confidence=confidence,
            metadata=metadata
        )
        self.thought_trace.append(step)

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for legacy module compatibility if needed"""
        return self.model_dump()
