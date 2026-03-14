from __future__ import annotations
"""
OricliAlpha Core Types - OpenAI-compatible request/response models
"""

from typing import Any, Dict, List, Optional, Union
from pydantic import BaseModel, Field, field_validator


def extract_text_from_content(content: Union[str, List[Dict[str, Any]]]) -> str:
    """
    Extract text content from OpenAI-compatible message content.
    
    Supports both formats:
    - String: "hello" -> "hello"
    - Multimodal array: [{"type": "text", "text": "hello"}] -> "hello"
    
    Args:
        content: Message content in string or multimodal format
        
    Returns:
        Extracted text string
        
    Raises:
        ValueError: If content format is invalid
    """
    if isinstance(content, str):
        return content
    
    if isinstance(content, list):
        # Extract text from multimodal content array
        text_parts = []
        for item in content:
            if not isinstance(item, dict):
                raise ValueError(f"Invalid content item type: {type(item).__name__}")
            
            item_type = item.get("type", "")
            if item_type == "text":
                text_parts.append(item.get("text", ""))
            elif item_type in ("image_url", "image"):
                # For now, we only support text. Image support can be added later.
                # Store a placeholder or description for image content
                image_url = item.get("image_url", item.get("url", ""))
                if isinstance(image_url, dict):
                    image_url = image_url.get("url", "")
                if image_url:
                    text_parts.append(f"[Image: {image_url}]")
            else:
                # Unknown type, skip or handle gracefully
                continue
        
        return "".join(text_parts)
    
    raise ValueError(f"Invalid content type: {type(content).__name__}")


class ChatMessage(BaseModel):
    """OpenAI-compatible chat message"""
    role: str = Field(..., description="Message role: system, user, assistant")
    content: Union[str, List[Dict[str, Any]]] = Field(
        ..., 
        description="Message content (string or multimodal content array)"
    )
    
    @field_validator('content', mode='before')
    @classmethod
    def validate_content(cls, v: Any) -> Union[str, List[Dict[str, Any]]]:
        """Validate content accepts both string and multimodal formats"""
        if isinstance(v, (str, list)):
            return v
        raise ValueError(f"Content must be a string or list, got {type(v).__name__}")
    
    def get_text_content(self) -> str:
        """
        Extract text content from message.
        
        Returns:
            Text content as string
        """
        return extract_text_from_content(self.content)


class ChatCompletionRequest(BaseModel):
    """OpenAI-compatible chat completion request"""
    model: str = Field(default="oricli-cognitive", description="Model identifier")
    messages: List[ChatMessage] = Field(..., description="Conversation messages")
    temperature: Optional[float] = Field(default=0.7, ge=0.0, le=2.0, description="Sampling temperature")
    max_tokens: Optional[int] = Field(default=None, ge=1, description="Maximum tokens to generate")
    stream: Optional[bool] = Field(default=False, description="Stream responses")
    top_p: Optional[float] = Field(default=1.0, ge=0.0, le=1.0, description="Nucleus sampling parameter")
    frequency_penalty: Optional[float] = Field(default=0.0, ge=-2.0, le=2.0, description="Frequency penalty")
    presence_penalty: Optional[float] = Field(default=0.0, ge=-2.0, le=2.0, description="Presence penalty")
    stop: Optional[Union[str, List[str]]] = Field(default=None, description="Stop sequences")
    user: Optional[str] = Field(default=None, description="User identifier")
    
    # OricliAlpha-specific extensions
    personality_id: Optional[str] = Field(default=None, description="Personality identifier")
    use_memory: Optional[bool] = Field(default=True, description="Use conversation memory")
    use_reasoning: Optional[bool] = Field(default=True, description="Use reasoning layer")
    
    # Tool calling support
    tools: Optional[List["ToolDefinition"]] = Field(default=None, description="Available tools for tool calling")
    tool_choice: Optional[str] = Field(default=None, description="Tool choice mode: 'auto', 'required', 'none', or tool name")


class ChatCompletionChoice(BaseModel):
    """Chat completion choice"""
    index: int = Field(..., description="Choice index")
    message: ChatMessage = Field(..., description="Generated message")
    finish_reason: Optional[str] = Field(default="stop", description="Finish reason")


class ChatCompletionUsage(BaseModel):
    """Token usage information"""
    prompt_tokens: int = Field(default=0, description="Prompt tokens")
    completion_tokens: int = Field(default=0, description="Completion tokens")
    total_tokens: int = Field(default=0, description="Total tokens")


class URLContextMetadata(BaseModel):
    """URL context metadata for tracking URL retrieval status"""
    url: str = Field(..., description="URL that was fetched")
    status: str = Field(..., description="Retrieval status: SUCCESS, CACHED, FAILED, or UNSUPPORTED")
    content_type: Optional[str] = Field(default=None, description="Content type (e.g., text/html)")
    size_bytes: int = Field(default=0, description="Content size in bytes")
    retrieval_method: str = Field(..., description="Retrieval method: cache or live")
    error: Optional[str] = Field(default=None, description="Error message if status is FAILED or UNSUPPORTED")


class ChatCompletionResponse(BaseModel):
    """OpenAI-compatible chat completion response"""
    id: str = Field(..., description="Response ID")
    object: str = Field(default="chat.completion", description="Object type")
    created: int = Field(..., description="Unix timestamp")
    model: str = Field(..., description="Model identifier")
    choices: List[ChatCompletionChoice] = Field(..., description="Completion choices")
    usage: Optional[ChatCompletionUsage] = Field(default=None, description="Token usage")
    
    # OricliAlpha-specific extensions
    reasoning_steps: Optional[List[str]] = Field(default=None, description="Reasoning steps")
    confidence: Optional[float] = Field(default=None, description="Confidence score")
    metadata: Optional[Dict[str, Any]] = Field(default=None, description="Additional metadata")
    url_context_metadata: Optional[List[URLContextMetadata]] = Field(
        default=None,
        description="URL context metadata for URLs fetched during this request"
    )


class EmbeddingRequest(BaseModel):
    """OpenAI-compatible embedding request"""
    input: Union[str, List[str]] = Field(..., description="Input text(s) to embed")
    model: str = Field(default="oricli-embeddings", description="Embedding model identifier")
    user: Optional[str] = Field(default=None, description="User identifier")


class EmbeddingData(BaseModel):
    """Embedding data"""
    object: str = Field(default="embedding", description="Object type")
    embedding: List[float] = Field(..., description="Embedding vector")
    index: int = Field(..., description="Index in batch")


class EmbeddingUsage(BaseModel):
    """Embedding usage information"""
    prompt_tokens: int = Field(default=0, description="Prompt tokens")
    total_tokens: int = Field(default=0, description="Total tokens")


class EmbeddingResponse(BaseModel):
    """OpenAI-compatible embedding response"""
    object: str = Field(default="list", description="Object type")
    data: List[EmbeddingData] = Field(..., description="Embedding data")
    model: str = Field(..., description="Model identifier")
    usage: Optional[EmbeddingUsage] = Field(default=None, description="Token usage")


class ModelInfo(BaseModel):
    """Model information"""
    id: str = Field(..., description="Model identifier")
    object: str = Field(default="model", description="Object type")
    created: int = Field(..., description="Unix timestamp")
    owned_by: str = Field(default="oricli", description="Owner")
    permission: List[Dict[str, Any]] = Field(default_factory=list, description="Permissions")
    root: Optional[str] = Field(default=None, description="Root model")
    parent: Optional[str] = Field(default=None, description="Parent model")


class ModelsListResponse(BaseModel):
    """Models list response"""
    object: str = Field(default="list", description="Object type")
    data: List[ModelInfo] = Field(..., description="List of models")


class ResourceLimitsRequest(BaseModel):
    """Resource limits for code execution"""
    cpu_cores: Optional[float] = Field(default=None, ge=0.1, le=4.0, description="CPU cores")
    memory_mb: Optional[int] = Field(default=None, ge=64, le=2048, description="Memory in MB")
    disk_mb: Optional[int] = Field(default=None, ge=10, le=1024, description="Disk space in MB")
    timeout_seconds: Optional[int] = Field(default=None, ge=1, le=120, description="Timeout in seconds")


class CodeExecutionRequest(BaseModel):
    """Code execution request"""
    session_id: Optional[str] = Field(default=None, description="Session ID for persistent execution")
    command: Optional[str] = Field(default=None, description="Bash command to execute")
    code: Optional[str] = Field(default=None, description="Python or Node.js code to execute")
    language: str = Field(default="bash", description="Language: bash, python, or node")
    operation: str = Field(
        default="execute",
        description="Operation: execute, read_file, write_file, list_files, delete_file",
    )
    file_path: Optional[str] = Field(default=None, description="File path for file operations")
    content: Optional[str] = Field(default=None, description="File content for write operations")
    directory: Optional[str] = Field(default=None, description="Directory path for list_files operation")
    resource_limits: Optional[ResourceLimitsRequest] = Field(
        default=None, description="Resource limits override"
    )
    
    @field_validator('language')
    @classmethod
    def validate_language(cls, v: str) -> str:
        """Validate language parameter"""
        if v not in ('bash', 'python', 'node'):
            raise ValueError(f"Language must be 'bash', 'python', or 'node', got '{v}'")
        return v
    
    @field_validator('operation')
    @classmethod
    def validate_operation(cls, v: str) -> str:
        """Validate operation parameter"""
        valid_ops = ('execute', 'read_file', 'write_file', 'list_files', 'delete_file')
        if v not in valid_ops:
            raise ValueError(f"Operation must be one of {valid_ops}, got '{v}'")
        return v


class ResourceUsageResponse(BaseModel):
    """Resource usage information"""
    cpu_percent: float = Field(default=0.0, description="CPU usage percentage")
    memory_mb: float = Field(default=0.0, description="Memory used in MB")
    disk_mb: float = Field(default=0.0, description="Disk space used in MB")
    execution_time: float = Field(..., description="Execution time in seconds")


class CodeExecutionResponse(BaseModel):
    """Code execution response"""
    session_id: str = Field(..., description="Session ID")
    success: bool = Field(..., description="Whether execution succeeded")
    stdout: Optional[str] = Field(default=None, description="Standard output")
    stderr: Optional[str] = Field(default=None, description="Standard error")
    exit_code: Optional[int] = Field(default=None, description="Exit code")
    file_content: Optional[str] = Field(default=None, description="File content (for read_file)")
    files: Optional[List[str]] = Field(default=None, description="File list (for list_files)")
    file_path: Optional[str] = Field(default=None, description="File path (for file operations)")
    directory: Optional[str] = Field(default=None, description="Directory (for list_files)")
    execution_time: float = Field(..., description="Execution time in seconds")
    resource_usage: ResourceUsageResponse = Field(..., description="Resource usage information")


# Tool Calling Models

class ToolParameter(BaseModel):
    """Tool parameter definition (JSON Schema compatible)"""
    type: str = Field(..., description="Parameter type: string, number, integer, boolean, object, array")
    description: Optional[str] = Field(default=None, description="Parameter description")
    enum: Optional[List[Any]] = Field(default=None, description="Enum values")
    default: Optional[Any] = Field(default=None, description="Default value")
    required: Optional[bool] = Field(default=False, description="Whether parameter is required")
    properties: Optional[Dict[str, "ToolParameter"]] = Field(default=None, description="Object properties")
    items: Optional["ToolParameter"] = Field(default=None, description="Array item type")
    minimum: Optional[float] = Field(default=None, description="Minimum value (for numbers)")
    maximum: Optional[float] = Field(default=None, description="Maximum value (for numbers)")


class ToolDefinition(BaseModel):
    """Tool definition for tool calling"""
    name: str = Field(..., description="Tool name")
    description: str = Field(..., description="Tool description")
    parameters: Dict[str, ToolParameter] = Field(default_factory=dict, description="Tool parameters (JSON Schema)")
    allowed_callers: List[str] = Field(
        default=["direct"],
        description="Allowed callers: 'direct' and/or 'code_execution_20250825'"
    )
    result_format: str = Field(
        default="json",
        description="Result format: 'json' or 'native'"
    )
    defer_loading: Optional[bool] = Field(
        default=False,
        description="If true, tool definition is deferred and will be loaded on-demand via tool search"
    )
    
    @field_validator('allowed_callers')
    @classmethod
    def validate_allowed_callers(cls, v: List[str]) -> List[str]:
        """Validate allowed_callers"""
        valid_callers = {"direct", "code_execution_20250825"}
        for caller in v:
            if caller not in valid_callers:
                raise ValueError(f"Invalid caller: {caller}. Must be one of {valid_callers}")
        return v
    
    @field_validator('result_format')
    @classmethod
    def validate_result_format(cls, v: str) -> str:
        """Validate result_format"""
        if v not in ("json", "native"):
            raise ValueError(f"result_format must be 'json' or 'native', got '{v}'")
        return v


class ToolUse(BaseModel):
    """Tool use block"""
    id: str = Field(..., description="Tool use ID")
    type: str = Field(default="tool_use", description="Block type")
    name: str = Field(..., description="Tool name")
    input: Dict[str, Any] = Field(..., description="Tool input parameters")
    caller: Optional[str] = Field(default=None, description="Caller type: 'direct' or 'code_execution_20250825'")


class ToolResult(BaseModel):
    """Tool result block"""
    tool_use_id: str = Field(..., description="Tool use ID this result corresponds to")
    type: str = Field(default="tool_result", description="Block type")
    content: Union[str, Dict[str, Any], List[Any]] = Field(..., description="Tool result content")
    is_error: bool = Field(default=False, description="Whether result is an error")


class ToolInvocationRequest(BaseModel):
    """Tool invocation request"""
    tool_name: str = Field(..., description="Tool name to invoke")
    input: Dict[str, Any] = Field(..., description="Tool input parameters")
    caller: str = Field(default="direct", description="Caller type")


class ToolInvocationResponse(BaseModel):
    """Tool invocation response"""
    success: bool = Field(..., description="Whether invocation succeeded")
    result: Optional[Any] = Field(default=None, description="Tool result")
    error: Optional[str] = Field(default=None, description="Error message if failed")


# Web Fetch Models

class WebFetchRequest(BaseModel):
    """Web fetch request"""
    url: str = Field(..., description="URL to fetch (must be explicitly provided)")
    explicitly_provided: bool = Field(default=True, description="Whether URL was explicitly provided")
    enable_citations: bool = Field(default=True, description="Enable citation generation")
    allowed_domains: Optional[List[str]] = Field(default=None, description="Allowed domains (allowlist)")
    blocked_domains: Optional[List[str]] = Field(default=None, description="Blocked domains")
    max_content_tokens: Optional[int] = Field(default=100000, description="Maximum content tokens")


class WebFetchMultipleRequest(BaseModel):
    """Web fetch multiple URLs request"""
    urls: List[str] = Field(..., description="List of URLs to fetch")
    explicitly_provided: bool = Field(default=True, description="Whether URLs were explicitly provided")
    enable_citations: bool = Field(default=True, description="Enable citation generation")
    max_uses: int = Field(default=10, description="Maximum number of URLs to fetch")
    allowed_domains: Optional[List[str]] = Field(default=None, description="Allowed domains (allowlist)")
    blocked_domains: Optional[List[str]] = Field(default=None, description="Blocked domains")
    max_content_tokens: Optional[int] = Field(default=100000, description="Maximum content tokens")


class WebFetchResponse(BaseModel):
    """Web fetch response"""
    success: bool = Field(..., description="Whether fetch succeeded")
    url: Optional[str] = Field(default=None, description="Fetched URL")
    content: Optional[str] = Field(default=None, description="Fetched content")
    title: Optional[str] = Field(default=None, description="Page title")
    description: Optional[str] = Field(default=None, description="Page description")
    author: Optional[str] = Field(default=None, description="Page author")
    content_type: Optional[str] = Field(default=None, description="Content type: html or pdf")
    content_length: Optional[int] = Field(default=None, description="Content length in characters")
    citation: Optional[str] = Field(default=None, description="Citation string")
    metadata: Optional[Dict[str, Any]] = Field(default=None, description="Additional metadata")
    error: Optional[str] = Field(default=None, description="Error message if failed")
    error_code: Optional[str] = Field(default=None, description="Error code if failed")


# Python LLM Request/Response Models

class PythonUnderstandRequest(BaseModel):
    """Request for Python semantic understanding"""
    code: str = Field(..., description="Python code to analyze")
    analysis_type: Optional[str] = Field(default="full", description="Type of analysis: full, semantic, types, dependencies")


class PythonUnderstandResponse(BaseModel):
    """Response from Python semantic understanding"""
    success: bool = Field(..., description="Whether analysis succeeded")
    semantic_analysis: Optional[Dict[str, Any]] = Field(default=None, description="Semantic analysis results")
    type_inference: Optional[Dict[str, Any]] = Field(default=None, description="Type inference results")
    dependency_graph: Optional[Dict[str, Any]] = Field(default=None, description="Dependency graph")
    call_graph: Optional[Dict[str, Any]] = Field(default=None, description="Call graph")
    error: Optional[str] = Field(default=None, description="Error message if failed")


class PythonGenerateRequest(BaseModel):
    """Request for Python code generation"""
    requirements: str = Field(..., description="Requirements for code generation")
    context: Optional[Dict[str, Any]] = Field(default=None, description="Additional context")
    style: Optional[str] = Field(default="pep8", description="Code style preference")
    reasoning_method: Optional[str] = Field(default="cot", description="Reasoning method: cot, tot, mcts")


class PythonGenerateResponse(BaseModel):
    """Response from Python code generation"""
    success: bool = Field(..., description="Whether generation succeeded")
    code: Optional[str] = Field(default=None, description="Generated code")
    explanation: Optional[str] = Field(default=None, description="Explanation of generated code")
    reasoning_steps: Optional[List[Dict[str, Any]]] = Field(default=None, description="Reasoning steps")
    verification: Optional[Dict[str, Any]] = Field(default=None, description="Verification results")
    error: Optional[str] = Field(default=None, description="Error message if failed")


class PythonReasonRequest(BaseModel):
    """Request for Python code reasoning"""
    code: str = Field(..., description="Python code to reason about")
    query: str = Field(..., description="Reasoning query")
    reasoning_type: Optional[str] = Field(default="behavior", description="Type of reasoning: behavior, optimization, correctness")


class PythonReasonResponse(BaseModel):
    """Response from Python code reasoning"""
    success: bool = Field(..., description="Whether reasoning succeeded")
    result: Optional[Dict[str, Any]] = Field(default=None, description="Reasoning results")
    error: Optional[str] = Field(default=None, description="Error message if failed")


class PythonCompleteRequest(BaseModel):
    """Request for Python code completion"""
    partial_code: str = Field(..., description="Partial code to complete")
    context: Optional[Dict[str, Any]] = Field(default=None, description="Additional context")
    style: Optional[str] = Field(default=None, description="Code style preference")


class PythonCompleteResponse(BaseModel):
    """Response from Python code completion"""
    success: bool = Field(..., description="Whether completion succeeded")
    completion: Optional[str] = Field(default=None, description="Completed code")
    explanation: Optional[str] = Field(default=None, description="Explanation of completion")
    error: Optional[str] = Field(default=None, description="Error message if failed")


class PythonEmbedRequest(BaseModel):
    """Request for Python code embedding"""
    code: str = Field(..., description="Python code to embed")


class PythonEmbedResponse(BaseModel):
    """Response from Python code embedding"""
    success: bool = Field(..., description="Whether embedding succeeded")
    embedding: Optional[List[float]] = Field(default=None, description="Code embedding vector")
    dimension: Optional[int] = Field(default=None, description="Embedding dimension")
    method: Optional[str] = Field(default=None, description="Method used for embedding")
    error: Optional[str] = Field(default=None, description="Error message if failed")


class PythonTestGenerationRequest(BaseModel):
    """Request for Python test generation"""
    code: str = Field(..., description="Python code to generate tests for")
    test_type: Optional[str] = Field(default="all", description="Type of tests: all, unit, edge_case, property")


class PythonTestGenerationResponse(BaseModel):
    """Response from Python test generation"""
    success: bool = Field(..., description="Whether test generation succeeded")
    test_suite: Optional[str] = Field(default=None, description="Generated test suite code")
    test_cases: Optional[List[Dict[str, Any]]] = Field(default=None, description="Identified test cases")
    error: Optional[str] = Field(default=None, description="Error message if failed")


# Sovereign Goal Models

class GoalCreateRequest(BaseModel):
    """Request to create a new sovereign goal"""
    goal: str = Field(..., description="High-level objective description")
    priority: int = Field(default=1, ge=1, le=5, description="Priority level (1-5)")
    metadata: Optional[Dict[str, Any]] = Field(default=None, description="Additional goal metadata")


class GoalResponse(BaseModel):
    """Sovereign goal information"""
    id: str = Field(..., description="Goal unique identifier")
    goal: str = Field(..., description="Objective description")
    priority: int = Field(..., description="Priority level")
    status: str = Field(..., description="Current status: pending, active, completed, failed, paused")
    progress: float = Field(..., description="Progress percentage (0.0-100.0)")
    created_at: str = Field(..., description="Creation timestamp")
    updated_at: str = Field(..., description="Last update timestamp")
    metadata: Dict[str, Any] = Field(default_factory=dict, description="Metadata")


class GoalListResponse(BaseModel):
    """List of sovereign goals"""
    goals: List[GoalResponse] = Field(..., description="List of goals")
    count: int = Field(..., description="Total number of goals")


class GoalStatusResponse(BaseModel):
    """Detailed status of a sovereign goal"""
    goal: GoalResponse = Field(..., description="Goal information")
    plan_state: Optional[Dict[str, Any]] = Field(default=None, description="Detailed execution plan state")


# Hive Swarm Models

class SwarmRunRequest(BaseModel):
    """Request to trigger a collaborative swarm session"""
    query: str = Field(..., description="The problem or query to solve via swarm deliberation")
    max_rounds: int = Field(default=3, ge=1, le=10, description="Maximum number of deliberation rounds")
    participants: Optional[List[str]] = Field(default=None, description="List of participant profiles to include")
    consensus_policy: str = Field(default="weighted_vote", description="Policy for reaching consensus: weighted_vote, majority, verifier_wins, merge_top")


class SwarmSessionResponse(BaseModel):
    """Swarm session information"""
    session_id: str = Field(..., description="Session identifier")
    query: str = Field(..., description="Original query")
    status: str = Field(..., description="Current status: active, completed, failed")
    participants: List[Dict[str, Any]] = Field(..., description="List of participants")
    created_at: str = Field(..., description="Creation timestamp")
    updated_at: str = Field(..., description="Last update timestamp")


class SwarmSessionDetailResponse(SwarmSessionResponse):
    """Detailed swarm session information with blackboard state"""
    shared_state: Dict[str, Any] = Field(..., description="Shared blackboard state")
    message_log: List[Dict[str, Any]] = Field(..., description="Full message log of deliberation")
    contributions: List[Dict[str, Any]] = Field(..., description="Agent contributions")
    reviews: List[Dict[str, Any]] = Field(..., description="Agent peer reviews")
    rounds: List[Dict[str, Any]] = Field(..., description="Round-by-round state")
    final_consensus: Optional[Dict[str, Any]] = Field(default=None, description="Final synthesized answer")


# Knowledge Graph Models

class KnowledgeExtractRequest(BaseModel):
    """Request to extract entities and relationships from text"""
    text: str = Field(..., description="Unstructured text to process")
    domain: Optional[str] = Field(default=None, description="Optional domain context for extraction")


class KnowledgeQueryRequest(BaseModel):
    """Request to query the knowledge graph"""
    entity_id: Optional[str] = Field(default=None, description="Entity to query")
    query_string: Optional[str] = Field(default=None, description="Natural language or structured query")
    depth: int = Field(default=1, ge=1, le=5, description="Traversal depth")


class KnowledgeResponse(BaseModel):
    """Knowledge graph query result"""
    success: bool = Field(..., description="Whether operation succeeded")
    nodes: Optional[List[Dict[str, Any]]] = Field(default=None, description="Graph nodes")
    edges: Optional[List[Dict[str, Any]]] = Field(default=None, description="Graph edges")
    rdf: Optional[str] = Field(default=None, description="RDF representation (if requested)")
    error: Optional[str] = Field(default=None, description="Error message if failed")

# Skill Models

class SkillCreateRequest(BaseModel):
    """Request to create a new skill"""
    skill_name: str = Field(..., description="Name of the skill (filename without .ori)")
    description: str = Field(default="", description="Description of the skill")
    triggers: List[str] = Field(default_factory=list, description="List of trigger phrases")
    requires_tools: List[str] = Field(default_factory=list, description="List of required tools")
    mindset: str = Field(default="", description="The persona/mindset block")
    instructions: str = Field(default="", description="The specific instructions block")

class SkillUpdateRequest(SkillCreateRequest):
    """Request to update an existing skill"""
    pass

class SkillResponse(BaseModel):
    """Details of a single skill"""
    skill_name: str = Field(..., description="Name of the skill")
    description: str = Field(default="", description="Description of the skill")
    triggers: List[str] = Field(default_factory=list, description="List of trigger phrases")
    requires_tools: List[str] = Field(default_factory=list, description="List of required tools")
    mindset: str = Field(default="", description="The persona/mindset block")
    instructions: str = Field(default="", description="The specific instructions block")

class SkillListResponse(BaseModel):
    """List of all available skills"""
    success: bool = Field(..., description="Whether operation succeeded")
    skills: List[SkillResponse] = Field(default_factory=list, description="List of skills")

