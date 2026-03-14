from __future__ import annotations
"""
OricliAlpha Core Embedded HTTP Server
FastAPI-based server that can run standalone
"""

import os
import socket
import sys
from typing import Optional, List, Dict, Any
from pathlib import Path

# Check for required dependencies
try:
    import uvicorn
except ImportError:
    print(
        "Error: uvicorn is not installed. Install dependencies with: pip install -e .",
        file=sys.stderr
    )
    sys.exit(1)

try:
    from fastapi import FastAPI, HTTPException, Request, Header, Response
    from fastapi.middleware.cors import CORSMiddleware
    from fastapi.responses import JSONResponse
    from fastapi.exceptions import RequestValidationError
    from fastapi import status
except ImportError:
    print(
        "Error: fastapi is not installed. Install dependencies with: pip install -e .",
        file=sys.stderr
    )
    sys.exit(1)

from oricli_core.api.openai_compatible import OpenAICompatibleAPI
from oricli_core.client import OricliAlphaClient
from oricli_core.brain.metrics import get_metrics_collector
from oricli_core.brain.health import get_health_checker
from oricli_core.system_identifier import SYSTEM_ID, SYSTEM_ID_FULL
from oricli_core.services.goal_service import GoalService
from oricli_core.services.swarm_blackboard_service import get_swarm_blackboard_service
from oricli_core.types.models import (
    ChatMessage,
    ChatCompletionRequest,
    ChatCompletionResponse,
    EmbeddingRequest,
    EmbeddingResponse,
    ModelsListResponse,
    CodeExecutionRequest,
    CodeExecutionResponse,
    ResourceLimitsRequest,
    ResourceUsageResponse,
    ToolDefinition,
    ToolInvocationRequest,
    ToolInvocationResponse,
    WebFetchRequest,
    WebFetchResponse,
    PythonUnderstandRequest,
    PythonUnderstandResponse,
    PythonGenerateRequest,
    PythonGenerateResponse,
    PythonReasonRequest,
    PythonReasonResponse,
    PythonCompleteRequest,
    PythonCompleteResponse,
    PythonEmbedRequest,
    PythonEmbedResponse,
    PythonTestGenerationRequest,
    PythonTestGenerationResponse,
    GoalCreateRequest,
    GoalResponse,
    GoalListResponse,
    GoalStatusResponse,
    SwarmRunRequest,
    SwarmSessionResponse,
    SwarmSessionDetailResponse,
    KnowledgeExtractRequest,
    KnowledgeQueryRequest,
    KnowledgeResponse,
    SkillCreateRequest,
    SkillUpdateRequest,
    SkillResponse,
    SkillListResponse,
)


def _register_builtin_tools() -> None:
    """Register built-in tools (web_fetch, etc.) with the tool registry."""
    try:
        from oricli_core.services.tool_registry import ToolRegistry
        from oricli_core.brain.registry import ModuleRegistry
        
        # Modules should already be discovered by create_app, but ensure they are
        if not ModuleRegistry._discovered:
            ModuleRegistry.discover_modules(background=False, verbose=False)
        
        tool_registry = ToolRegistry()
        
        # Register web_fetch tool if module is available
        web_fetch_module = ModuleRegistry.get_module("web_fetch")
        if web_fetch_module:
            def web_fetch_handler(url: str, **kwargs) -> Dict[str, Any]:
                """Handler for web_fetch tool."""
                result = web_fetch_module.execute("fetch_url", {"url": url, **kwargs})
                if result.get("success"):
                    # Return content in tool result format
                    return {
                        "content": result.get("content", ""),
                        "title": result.get("title"),
                        "citation": result.get("citation"),
                        "metadata": result.get("metadata", {}),
                    }
                else:
                    # Return error
                    raise Exception(result.get("error", "Unknown error"))
            
            # Check if already registered
            existing_tool = tool_registry.get_tool("web_fetch")
            if not existing_tool:
                tool_registry.register_tool(
                    name="web_fetch",
                    description="Fetch content from web pages and PDF documents. Only URLs explicitly provided by the user can be fetched.",
                    parameters={
                        "url": {
                            "type": "string",
                            "description": "URL to fetch (must be explicitly provided)",
                            "required": True,
                        },
                        "explicitly_provided": {
                            "type": "boolean",
                            "description": "Whether URL was explicitly provided",
                            "default": True,
                        },
                        "enable_citations": {
                            "type": "boolean",
                            "description": "Enable citation generation",
                            "default": True,
                        },
                    },
                    handler=web_fetch_handler,
                    allowed_callers=["direct", "code_execution_20250825"],
                    result_format="json",
                )
        
        # Register tool_search_tool_regex_20251119 if module is available
        tool_search_module = ModuleRegistry.get_module("tool_search")
        if tool_search_module:
            def tool_search_regex_handler(query: str, limit: int = 10, search_deferred_only: bool = False) -> Dict[str, Any]:
                """Handler for tool_search_tool_regex_20251119."""
                result = tool_search_module.execute("search_regex", {
                    "query": query,
                    "limit": limit,
                    "search_deferred_only": search_deferred_only,
                })
                if result.get("success"):
                    return {
                        "matches": result.get("matches", []),
                        "count": result.get("count", 0),
                    }
                else:
                    raise Exception(result.get("error", "Unknown error"))
            
            # Check if already registered
            existing_tool = tool_registry.get_tool("tool_search_tool_regex_20251119")
            if not existing_tool:
                tool_registry.register_tool(
                    name="tool_search_tool_regex_20251119",
                    description="Search for tools using a regex pattern. Returns tool references that match the pattern.",
                    parameters={
                        "query": {
                            "type": "string",
                            "description": "Regex pattern to search for in tool names, descriptions, and parameters",
                            "required": True,
                        },
                        "limit": {
                            "type": "integer",
                            "description": "Maximum number of results to return",
                            "default": 10,
                            "minimum": 1,
                            "maximum": 100,
                        },
                        "search_deferred_only": {
                            "type": "boolean",
                            "description": "If true, only search deferred tools",
                            "default": False,
                        },
                    },
                    handler=tool_search_regex_handler,
                    allowed_callers=["direct", "code_execution_20250825"],
                    result_format="json",
                )
            
            def tool_search_bm25_handler(query: str, limit: int = 10, search_deferred_only: bool = False) -> Dict[str, Any]:
                """Handler for tool_search_tool_bm25_20251119."""
                result = tool_search_module.execute("search_bm25", {
                    "query": query,
                    "limit": limit,
                    "search_deferred_only": search_deferred_only,
                })
                if result.get("success"):
                    return {
                        "matches": result.get("matches", []),
                        "count": result.get("count", 0),
                    }
                else:
                    raise Exception(result.get("error", "Unknown error"))
            
            # Check if already registered
            existing_tool = tool_registry.get_tool("tool_search_tool_bm25_20251119")
            if not existing_tool:
                tool_registry.register_tool(
                    name="tool_search_tool_bm25_20251119",
                    description="Search for tools using BM25 ranking algorithm. Returns tool references ranked by relevance.",
                    parameters={
                        "query": {
                            "type": "string",
                            "description": "Search query string to find relevant tools",
                            "required": True,
                        },
                        "limit": {
                            "type": "integer",
                            "description": "Maximum number of results to return",
                            "default": 10,
                            "minimum": 1,
                            "maximum": 100,
                        },
                        "search_deferred_only": {
                            "type": "boolean",
                            "description": "If true, only search deferred tools",
                            "default": False,
                        },
                    },
                    handler=tool_search_bm25_handler,
                    allowed_callers=["direct", "code_execution_20250825"],
                    result_format="json",
                )
        
        # Register web_search_20250305 if module is available
        web_search_module = ModuleRegistry.get_module("web_search")
        if web_search_module:
            def web_search_handler(
                query: str,
                max_results: int = 10,
                allowed_domains: Optional[List[str]] = None,
                blocked_domains: Optional[List[str]] = None,
                user_location: Optional[str] = None,
            ) -> Dict[str, Any]:
                """Handler for web_search_20250305."""
                result = web_search_module.execute("search_web", {
                    "query": query,
                    "max_results": max_results,
                    "allowed_domains": allowed_domains,
                    "blocked_domains": blocked_domains,
                    "user_location": user_location,
                })
                if result.get("success"):
                    return {
                        "type": result.get("type", "web_search_tool_result"),
                        "results": result.get("results", []),
                        "count": result.get("count", 0),
                    }
                else:
                    raise Exception(result.get("error", "Unknown error"))
            
            # Check if already registered
            existing_tool = tool_registry.get_tool("web_search_20250305")
            if not existing_tool:
                tool_registry.register_tool(
                    name="web_search_20250305",
                    description="Search the web for information. Returns search results with encrypted content references for citations.",
                    parameters={
                        "query": {
                            "type": "string",
                            "description": "Search query string",
                            "required": True,
                        },
                        "max_results": {
                            "type": "integer",
                            "description": "Maximum number of search results to return",
                            "default": 10,
                            "minimum": 1,
                            "maximum": 50,
                        },
                        "allowed_domains": {
                            "type": "array",
                            "items": {"type": "string"},
                            "description": "Optional list of allowed domains. If provided, only results from these domains will be returned.",
                        },
                        "blocked_domains": {
                            "type": "array",
                            "items": {"type": "string"},
                            "description": "Optional list of blocked domains. Results from these domains will be excluded.",
                        },
                        "user_location": {
                            "type": "string",
                            "description": "Optional ISO country code for localizing search results (e.g., 'us', 'uk', 'de')",
                        },
                    },
                    handler=web_search_handler,
                    allowed_callers=["direct", "code_execution_20250825"],
                    result_format="json",
                )
        
        # Register url_context tool if module is available
        url_context_module = ModuleRegistry.get_module("url_context")
        if url_context_module:
            def url_context_handler(
                urls: List[str],
                use_cache: bool = True,
            ) -> Dict[str, Any]:
                """Handler for url_context tool."""
                result = url_context_module.execute("fetch_url_context", {
                    "urls": urls,
                    "use_cache": use_cache,
                })
                if result.get("success"):
                    return {
                        "results": result.get("results", []),
                        "url_context_metadata": result.get("url_context_metadata", []),
                        "count": result.get("count", 0),
                    }
                else:
                    raise Exception(result.get("error", "Unknown error"))
            
            # Check if already registered
            existing_tool = tool_registry.get_tool("url_context")
            if not existing_tool:
                tool_registry.register_tool(
                    name="url_context",
                    description="Fetch content from URLs for context. Supports caching and returns metadata about retrieval status.",
                    parameters={
                        "urls": {
                            "type": "array",
                            "items": {"type": "string"},
                            "description": "List of URLs to fetch (up to 20 URLs)",
                            "required": True,
                        },
                        "use_cache": {
                            "type": "boolean",
                            "description": "Whether to use cached content if available",
                            "default": True,
                        },
                    },
                    handler=url_context_handler,
                    allowed_callers=["direct", "code_execution_20250825"],
                    result_format="json",
                )
    except Exception:
        # Silently fail if registration fails (module may not be available)
        pass


def create_app(
    modules_dir: Optional[Path] = None,
    api_key: Optional[str] = None,
    enable_cors: bool = True,
    cors_origins: Optional[List[str]] = None,
    require_auth: bool = False
) -> FastAPI:
    """
    Create FastAPI application
    
    Args:
        modules_dir: Optional path to brain_modules directory
        api_key: Optional API key for authentication (defaults to MAVAIA_API_KEY env var)
        enable_cors: Enable CORS middleware
        cors_origins: List of allowed CORS origins (defaults to ["*"] if enable_cors is True)
        require_auth: Whether to require authentication (defaults to False)
    
    Returns:
        FastAPI application instance
    """
    # Force unbuffered stderr
    import sys
    if hasattr(sys.stderr, 'reconfigure'):
        sys.stderr.reconfigure(line_buffering=True)
    
    # Discover modules synchronously BEFORE creating the app
    # This ensures all modules are loaded and available when the server starts
    from oricli_core.brain.registry import ModuleRegistry
    if modules_dir:
        ModuleRegistry.set_modules_dir(modules_dir)
    print("[Server] Discovering modules synchronously...", file=sys.stderr, flush=True)
    ModuleRegistry.discover_modules(background=False, verbose=False)
    print(f"[Server] Module discovery complete. Found {len(ModuleRegistry.list_modules())} modules.", file=sys.stderr, flush=True)
    
    # Get API key from parameter or environment variable
    actual_api_key = api_key or os.getenv("MAVAIA_API_KEY")
    actual_require_auth = require_auth or os.getenv("MAVAIA_REQUIRE_AUTH", "false").lower() == "true"
    
    # Use lifespan context manager for startup/shutdown
    from contextlib import asynccontextmanager
    
    @asynccontextmanager
    async def lifespan_context(app):
        """Lifespan context manager for startup/shutdown"""
        # Startup
        try:
            sys.stderr.write("[DEBUG] Lifespan startup triggered\n")
            sys.stderr.flush()
            
            # Initialize module availability manager
            try:
                from oricli_core.brain.availability import get_availability_manager
                availability_manager = get_availability_manager()
                availability_manager.initialize(start_warmup=True, start_monitoring=True)
                sys.stderr.write("[DEBUG] Module availability manager initialized\n")
                sys.stderr.flush()
            except Exception as e:
                sys.stderr.write(f"[WARNING] Failed to initialize availability manager: {e}\n")
                sys.stderr.flush()
            
            # Register built-in tools (modules already discovered in create_app)
            _register_builtin_tools()
            sys.stderr.write("[DEBUG] Lifespan startup completed\n")
            sys.stderr.flush()
        except Exception as e:
            sys.stderr.write(f"[ERROR] Lifespan startup failed: {e}\n")
            import traceback
            traceback.print_exc(file=sys.stderr)
            sys.stderr.flush()
        yield
        # Shutdown
        try:
            from oricli_core.brain.availability import get_availability_manager
            availability_manager = get_availability_manager()
            availability_manager.shutdown()
        except Exception:
            pass
        sys.stderr.write("[DEBUG] Lifespan shutdown\n")
        sys.stderr.flush()
    
    try:
        sys.stderr.write("[DEBUG] Creating FastAPI app...\n")
        sys.stderr.flush()
        app = FastAPI(
            title="OricliAlpha Core API",
            description=f"OricliAlpha Core - OpenAI-compatible API for OricliAlpha capabilities (System: {SYSTEM_ID_FULL()})",
            version="1.0.0",
            docs_url="/docs",
            redoc_url="/redoc",
            lifespan=lifespan_context,
        )
        sys.stderr.write("[DEBUG] FastAPI app created\n")
        sys.stderr.flush()
    except Exception as e:
        sys.stderr.write(f"[ERROR] Failed to create FastAPI app: {e}\n")
        import traceback
        traceback.print_exc(file=sys.stderr)
        sys.stderr.flush()
        raise
    
    # Store configuration for lazy initialization
    app.state.modules_dir = modules_dir
    app.state.api_key = actual_api_key
    app.state.require_auth = actual_require_auth
    app.state._client = None
    app.state._api = None
    
    def get_client():
        """Lazy client initialization"""
        if app.state._client is None:
            try:
                print("[DEBUG] Initializing OricliAlphaClient...", file=sys.stderr)
                sys.stderr.flush()
                app.state._client = OricliAlphaClient(modules_dir=app.state.modules_dir)
                print("[DEBUG] OricliAlphaClient initialized", file=sys.stderr)
                sys.stderr.flush()
            except Exception as e:
                print(f"[ERROR] Failed to initialize OricliAlphaClient: {e}", file=sys.stderr)
                import traceback
                traceback.print_exc(file=sys.stderr)
                sys.stderr.flush()
                raise
        return app.state._client
    
    def get_api():
        """Lazy API initialization"""
        if app.state._api is None:
            try:
                sys.stderr.write("[DEBUG] Initializing OpenAICompatibleAPI...\n")
                sys.stderr.flush()
                app.state._api = OpenAICompatibleAPI(
                    get_client(),
                    api_key=app.state.api_key,
                    require_auth=app.state.require_auth
                )
                sys.stderr.write("[DEBUG] OpenAICompatibleAPI initialized\n")
                sys.stderr.flush()
            except Exception as e:
                sys.stderr.write(f"[ERROR] Failed to initialize OpenAICompatibleAPI: {e}\n")
                import traceback
                traceback.print_exc(file=sys.stderr)
                sys.stderr.flush()
                raise
        return app.state._api
    
    app.state.get_client = get_client
    app.state.get_api = get_api
    
    # Add CORS middleware
    if enable_cors:
        # Default to allowing all origins if not specified
        allowed_origins = cors_origins if cors_origins is not None else ["*"]
        
        # If specific origins are provided, don't allow credentials with wildcard
        allow_credentials = "*" not in allowed_origins
        
        app.add_middleware(
            CORSMiddleware,
            allow_origins=allowed_origins,
            allow_credentials=allow_credentials,
            allow_methods=["*"],
            allow_headers=["*"],
        )
    
    # Add exception handler for validation errors to see what's wrong
    @app.exception_handler(RequestValidationError)
    async def validation_exception_handler(request: Request, exc: RequestValidationError):
        """Handle validation errors with detailed logging"""
        import json
        sys.stderr.write(f"[ERROR] Validation error on {request.url.path}\n")
        sys.stderr.write(f"[ERROR] Method: {request.method}\n")
        try:
            body = await request.body()
            sys.stderr.write(f"[ERROR] Request body: {body.decode('utf-8')}\n")
        except Exception:
            pass
        sys.stderr.write(f"[ERROR] Validation errors: {exc.errors()}\n")
        sys.stderr.flush()
        
        return JSONResponse(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            content={
                "detail": exc.errors(),
                "body": exc.body
            }
        )
    
    # Root endpoint - redirect to docs
    @app.get("/")
    async def root():
        """Root endpoint - redirects to API documentation"""
        from fastapi.responses import RedirectResponse
        return RedirectResponse(url="/docs")
    
    # Health check endpoint
    @app.get("/health")
    async def health():
        """Health check endpoint"""
        return {
            "status": "healthy",
            "service": "oricli-core",
            "version": "1.0.0",
            "system_id": SYSTEM_ID,
            "system_id_full": SYSTEM_ID_FULL()
        }
    
    # OpenAI-compatible endpoints
    @app.post("/v1/chat/completions", response_model=ChatCompletionResponse)
    async def chat_completions(
        request: ChatCompletionRequest,
        response: Response,
        authorization: Optional[str] = None,
    ):
        """OpenAI-compatible chat completions endpoint"""
        result = await app.state.get_api().chat_completions(request, authorization)
        try:
            trace_id = None
            if hasattr(result, "metadata") and isinstance(result.metadata, dict):
                trace_id = result.metadata.get("trace_id")
            if trace_id:
                response.headers["X-OricliAlpha-Trace-Id"] = str(trace_id)
        except Exception:
            pass
        return result
    
    @app.post("/v1/embeddings", response_model=EmbeddingResponse)
    async def embeddings(
        request: EmbeddingRequest,
        authorization: Optional[str] = None
    ):
        """OpenAI-compatible embeddings endpoint"""
        return await app.state.get_api().embeddings(request, authorization)
    
    @app.get("/v1/models", response_model=ModelsListResponse)
    async def models(authorization: Optional[str] = None):
        """OpenAI-compatible models listing endpoint"""
        return await app.state.get_api().models(authorization)
    
    # --- Oricli-Alpha Native API Endpoints ---
    
    # Sovereign Goals
    @app.post("/v1/goals", response_model=GoalResponse)
    async def create_goal(
        request: GoalCreateRequest,
        authorization: Optional[str] = Header(None, alias="Authorization")
    ):
        """Create a new sovereign goal"""
        app.state.get_api().verify_api_key(authorization)
        goal_service = GoalService()
        goal_id = goal_service.add_objective(
            goal=request.goal,
            priority=request.priority,
            metadata=request.metadata
        )
        objectives = goal_service.list_objectives()
        for obj in objectives:
            if obj["id"] == goal_id:
                return GoalResponse(**obj)
        raise HTTPException(status_code=500, detail="Failed to retrieve created goal")

    @app.get("/v1/goals", response_model=GoalListResponse)
    async def list_goals(
        status: Optional[str] = None,
        authorization: Optional[str] = Header(None, alias="Authorization")
    ):
        """List sovereign goals"""
        app.state.get_api().verify_api_key(authorization)
        goal_service = GoalService()
        goals = goal_service.list_objectives(status=status)
        return GoalListResponse(
            goals=[GoalResponse(**g) for g in goals],
            count=len(goals)
        )

    @app.get("/v1/goals/{goal_id}", response_model=GoalStatusResponse)
    async def get_goal_status(
        goal_id: str,
        authorization: Optional[str] = Header(None, alias="Authorization")
    ):
        """Get detailed status of a sovereign goal"""
        app.state.get_api().verify_api_key(authorization)
        goal_service = GoalService()
        objectives = goal_service.list_objectives()
        goal_data = next((obj for obj in objectives if obj["id"] == goal_id), None)
        if not goal_data:
            raise HTTPException(status_code=404, detail=f"Goal {goal_id} not found")
        
        plan_state = goal_service.load_plan_state(goal_id)
        return GoalStatusResponse(
            goal=GoalResponse(**goal_data),
            plan_state=plan_state
        )

    # Hive Swarm
    @app.post("/v1/swarm/run", response_model=SwarmSessionResponse)
    async def run_swarm(
        request: SwarmRunRequest,
        authorization: Optional[str] = Header(None, alias="Authorization")
    ):
        """Trigger a collaborative swarm session"""
        app.state.get_api().verify_api_key(authorization)
        
        from oricli_core.brain.registry import ModuleRegistry
        swarm_coordinator = ModuleRegistry.get_module("swarm_coordinator")
        if not swarm_coordinator:
            raise HTTPException(status_code=503, detail="swarm_coordinator module unavailable")
        
        # Swarm coordinator handles the session creation via SwarmBlackboardService
        result = swarm_coordinator.execute("coordinate_task", {
            "query": request.query,
            "round_limit": request.max_rounds,
            "participants": request.participants,
            "consensus_policy": request.consensus_policy
        })
        
        if not result.get("success"):
            raise HTTPException(status_code=500, detail=result.get("error", "Swarm execution failed"))
        
        session_id = result.get("session_id")
        blackboard = get_swarm_blackboard_service()
        session = blackboard.load_session(session_id)
        if not session:
            raise HTTPException(status_code=500, detail="Failed to load created swarm session")
            
        return SwarmSessionResponse(**session)

    @app.get("/v1/swarm/sessions/{session_id}", response_model=SwarmSessionDetailResponse)
    async def get_swarm_session(
        session_id: str,
        authorization: Optional[str] = Header(None, alias="Authorization")
    ):
        """Get detailed swarm session state"""
        app.state.get_api().verify_api_key(authorization)
        blackboard = get_swarm_blackboard_service()
        session = blackboard.load_session(session_id)
        if not session:
            raise HTTPException(status_code=404, detail=f"Swarm session {session_id} not found")
        return SwarmSessionDetailResponse(**session)

    # Knowledge Graph
    @app.post("/v1/knowledge/extract", response_model=KnowledgeResponse)
    async def knowledge_extract(
        request: KnowledgeExtractRequest,
        authorization: Optional[str] = Header(None, alias="Authorization")
    ):
        """Extract entities and relationships from text"""
        app.state.get_api().verify_api_key(authorization)
        from oricli_core.brain.registry import ModuleRegistry
        kg_builder = ModuleRegistry.get_module("knowledge_graph_builder")
        if not kg_builder:
            raise HTTPException(status_code=503, detail="knowledge_graph_builder module unavailable")
            
        result = kg_builder.execute("build_from_text", {
            "text": request.text,
            "domain": request.domain
        })
        return KnowledgeResponse(**result)

    @app.post("/v1/knowledge/query", response_model=KnowledgeResponse)
    async def knowledge_query(
        request: KnowledgeQueryRequest,
        authorization: Optional[str] = Header(None, alias="Authorization")
    ):
        """Query the knowledge graph"""
        app.state.get_api().verify_api_key(authorization)
        from oricli_core.brain.registry import ModuleRegistry
        kg_builder = ModuleRegistry.get_module("knowledge_graph_builder")
        if not kg_builder:
            raise HTTPException(status_code=503, detail="knowledge_graph_builder module unavailable")
            
        if request.entity_id:
            result = kg_builder.execute("query_graph", {
                "entity_id": request.entity_id,
                "depth": request.depth
            })
        else:
            # If no entity_id, we can't search directly yet, return error or empty
            raise HTTPException(status_code=400, detail="entity_id is required for query")
        return KnowledgeResponse(**result)

    # --- Skills API ---
    @app.get("/v1/skills", response_model=SkillListResponse)
    async def list_skills(authorization: Optional[str] = Header(None, alias="Authorization")):
        """List all available skills"""
        app.state.get_api().verify_api_key(authorization)
        from oricli_core.brain.registry import ModuleRegistry
        skill_manager = ModuleRegistry.get_module("skill_manager")
        if not skill_manager:
            raise HTTPException(status_code=503, detail="skill_manager module unavailable")
            
        result = skill_manager.execute("list_skills", {})
        return SkillListResponse(**result)

    @app.get("/v1/skills/{skill_name}", response_model=SkillResponse)
    async def get_skill(
        skill_name: str,
        authorization: Optional[str] = Header(None, alias="Authorization")
    ):
        """Retrieve details of a specific skill"""
        app.state.get_api().verify_api_key(authorization)
        from oricli_core.brain.registry import ModuleRegistry
        skill_manager = ModuleRegistry.get_module("skill_manager")
        if not skill_manager:
            raise HTTPException(status_code=503, detail="skill_manager module unavailable")
            
        result = skill_manager.execute("get_skill", {"skill_name": skill_name})
        if not result.get("success"):
            raise HTTPException(status_code=404, detail=result.get("error", "Skill not found"))
        return SkillResponse(**result.get("skill", {}))

    @app.post("/v1/skills", response_model=SkillResponse)
    async def create_skill(
        request: SkillCreateRequest,
        authorization: Optional[str] = Header(None, alias="Authorization")
    ):
        """Create a new skill"""
        app.state.get_api().verify_api_key(authorization)
        from oricli_core.brain.registry import ModuleRegistry
        skill_manager = ModuleRegistry.get_module("skill_manager")
        if not skill_manager:
            raise HTTPException(status_code=503, detail="skill_manager module unavailable")
            
        result = skill_manager.execute("create_skill", request.dict())
        if not result.get("success"):
            raise HTTPException(status_code=400, detail=result.get("error", "Failed to create skill"))
        return SkillResponse(**result.get("skill", {}))

    @app.put("/v1/skills/{skill_name}", response_model=SkillResponse)
    async def update_skill(
        skill_name: str,
        request: SkillUpdateRequest,
        authorization: Optional[str] = Header(None, alias="Authorization")
    ):
        """Update an existing skill"""
        app.state.get_api().verify_api_key(authorization)
        from oricli_core.brain.registry import ModuleRegistry
        skill_manager = ModuleRegistry.get_module("skill_manager")
        if not skill_manager:
            raise HTTPException(status_code=503, detail="skill_manager module unavailable")
            
        req_dict = request.dict()
        if req_dict.get("skill_name") != skill_name:
            req_dict["skill_name"] = skill_name
            
        result = skill_manager.execute("update_skill", req_dict)
        if not result.get("success"):
            raise HTTPException(status_code=400, detail=result.get("error", "Failed to update skill"))
        return SkillResponse(**result.get("skill", {}))

    @app.delete("/v1/skills/{skill_name}")
    async def delete_skill(
        skill_name: str,
        authorization: Optional[str] = Header(None, alias="Authorization")
    ):
        """Delete a skill"""
        app.state.get_api().verify_api_key(authorization)
        from oricli_core.brain.registry import ModuleRegistry
        skill_manager = ModuleRegistry.get_module("skill_manager")
        if not skill_manager:
            raise HTTPException(status_code=503, detail="skill_manager module unavailable")
            
        result = skill_manager.execute("delete_skill", {"skill_name": skill_name})
        if not result.get("success"):
            raise HTTPException(status_code=404, detail=result.get("error", "Failed to delete skill"))
        return {"success": True, "message": result.get("message")}

    # --- Ollama-style API Aliases ---

    @app.post("/api/generate")
    async def ollama_generate(
        request: Dict[str, Any],
        authorization: Optional[str] = Header(None, alias="Authorization")
    ):
        """Ollama-style generation alias"""
        # Map Ollama 'prompt' to Oricli chat completion
        prompt = request.get("prompt")
        if not prompt:
            raise HTTPException(status_code=400, detail="Missing 'prompt' in request")
            
        chat_req = ChatCompletionRequest(
            model=request.get("model", "oricli-cognitive"),
            messages=[ChatMessage(role="user", content=prompt)],
            stream=request.get("stream", False)
        )
        
        # Reuse existing chat_completions logic
        return await app.state.get_api().chat_completions(chat_req, authorization)

    @app.post("/api/chat")
    async def ollama_chat(
        request: ChatCompletionRequest,
        response: Response,
        authorization: Optional[str] = Header(None, alias="Authorization")
    ):
        """Ollama-style chat alias"""
        return await chat_completions(request, response, authorization)

    @app.get("/api/tags")
    async def ollama_tags(authorization: Optional[str] = Header(None, alias="Authorization")):
        """Ollama-style tags (models) alias"""
        models_resp = await models(authorization)
        return {"models": models_resp.data}

    @app.post("/api/show")
    async def ollama_show(
        request: Dict[str, Any],
        authorization: Optional[str] = Header(None, alias="Authorization")
    ):
        """Ollama-style show model alias"""
        name = request.get("name")
        if not name:
            raise HTTPException(status_code=400, detail="Missing 'name' in request")
            
        # Strip 'oricli-' prefix if present
        module_name = name[7:] if name.startswith("oricli-") else name
        
        from oricli_core.brain.registry import ModuleRegistry
        metadata = ModuleRegistry.get_metadata(module_name)
        if not metadata:
            raise HTTPException(status_code=404, detail=f"Module/Model {name} not found")
            
        return {
            "name": name,
            "details": {
                "parent_model": "",
                "format": "oricli-module",
                "family": "oricli",
                "parameter_size": "N/A",
                "quantization_level": "N/A"
            },
            "modelfile": f"# Oricli-Alpha Module: {metadata.name}\n{metadata.description}",
            "parameters": metadata.operations,
            "template": ""
        }
    
    # Module discovery endpoint (OricliAlpha-specific)
    @app.get("/v1/modules")
    async def list_modules():
        """List available brain modules"""
        from oricli_core.brain.registry import ModuleRegistry
        
        modules = []
        for module_name in ModuleRegistry.list_modules():
            metadata = ModuleRegistry.get_metadata(module_name)
            if metadata:
                modules.append({
                    "name": metadata.name,
                    "version": metadata.version,
                    "description": metadata.description,
                    "operations": metadata.operations,
                    "enabled": metadata.enabled,
                    "model_required": metadata.model_required,
                })
        
        return {"modules": modules}
    
    # Metrics endpoint (OricliAlpha-specific)
    @app.get("/v1/metrics")
    async def get_metrics():
        """Get module metrics"""
        try:
            collector = get_metrics_collector()
            return {
                "summary": collector.get_summary(),
                "metrics": collector.export_metrics()
            }
        except Exception as e:
            raise HTTPException(
                status_code=500,
                detail=f"Error retrieving metrics: {str(e)}"
            )

    def _require_introspection_auth(authorization: Optional[str]) -> None:
        # Safe-by-default: introspection always requires auth unless explicitly disabled.
        require_auth = os.getenv("MAVAIA_INTROSPECTION_REQUIRE_AUTH", "true").lower() == "true"
        if not require_auth:
            return

        api_key = os.getenv("MAVAIA_API_KEY") or getattr(app.state.get_api(), "api_key", None)
        if not api_key:
            raise HTTPException(status_code=503, detail="Introspection auth required but MAVAIA_API_KEY is not configured")

        if not authorization or not authorization.startswith("Bearer "):
            raise HTTPException(status_code=401, detail="Authorization required")

        provided = authorization[7:].strip()
        if not provided or provided != api_key:
            raise HTTPException(status_code=401, detail="Invalid API key")

    @app.get("/v1/introspection")
    async def introspection_root(
        authorization: Optional[str] = Header(None, alias="Authorization"),
    ):
        _require_introspection_auth(authorization)
        from oricli_core.brain.introspection import get_trace_store

        return {
            "capabilities": get_trace_store().capabilities(),
            "endpoints": [
                "/v1/introspection/traces",
                "/v1/introspection/traces/{trace_id}",
                "/v1/introspection/router",
                "/v1/introspection/diagnostics/modules",
            ],
        }

    @app.get("/v1/introspection/traces")
    async def introspection_traces(
        limit: int = 20,
        authorization: Optional[str] = Header(None, alias="Authorization"),
    ):
        _require_introspection_auth(authorization)
        from oricli_core.brain.introspection import get_trace_store

        return get_trace_store().list_recent(limit)

    @app.get("/v1/introspection/traces/{trace_id}")
    async def introspection_trace(
        trace_id: str,
        authorization: Optional[str] = Header(None, alias="Authorization"),
    ):
        _require_introspection_auth(authorization)
        from oricli_core.brain.introspection import get_trace_store

        t = get_trace_store().get(trace_id)
        if not t:
            raise HTTPException(status_code=404, detail="Trace not found")
        return t

    @app.get("/v1/introspection/router")
    async def introspection_router(
        authorization: Optional[str] = Header(None, alias="Authorization"),
    ):
        _require_introspection_auth(authorization)
        from oricli_core.brain.registry import ModuleRegistry

        cg = ModuleRegistry.get_module("cognitive_generator")
        if not cg:
            raise HTTPException(status_code=503, detail="cognitive_generator module unavailable")

        return {
            "routing_statistics": cg.get_routing_statistics(),
            "router_state": cg.get_router_state(),
        }

    @app.get("/v1/introspection/diagnostics/modules")
    async def introspection_module_diagnostics(
        max_modules: int = 250,
        import_timeout_s: float = 8.0,
        authorization: Optional[str] = Header(None, alias="Authorization"),
    ):
        _require_introspection_auth(authorization)
        from oricli_core.brain.registry import ModuleRegistry

        diag = ModuleRegistry.get_module("module_health_diagnostics")
        if not diag:
            raise HTTPException(status_code=503, detail="module_health_diagnostics unavailable")

        return diag.execute(
            "scan_modules",
            {
                "include_subdirs": True,
                "max_modules": max_modules,
                "import_timeout_s": import_timeout_s,
                "include_tracebacks": False,
            },
        )
    
    # Health check endpoint (OricliAlpha-specific)
    @app.get("/v1/health/modules")
    async def get_module_health():
        """Get health status of all modules with fallback info"""
        try:
            from oricli_core.brain.availability import get_availability_manager
            availability_manager = get_availability_manager()
            system_status = availability_manager.get_availability_status()
            health_checker = get_health_checker()
            summary = health_checker.get_health_summary()
            
            # Enhance summary with availability manager info
            summary["availability"] = {
                "total_modules": system_status.total_modules,
                "available_modules": system_status.available_modules,
                "degraded_modules": system_status.degraded_modules,
                "offline_modules": system_status.offline_modules,
                "warmed_modules": system_status.warmed_modules,
                "modules_with_fallbacks": system_status.modules_with_fallbacks,
                "timestamp": system_status.timestamp.isoformat()
            }
            
            return summary
        except Exception as e:
            raise HTTPException(
                status_code=500,
                detail=f"Error checking module health: {str(e)}"
            )
    
    @app.get("/v1/health/modules/{module_name}")
    async def get_module_health_detail(module_name: str):
        """Get detailed health status for a specific module"""
        try:
            from oricli_core.brain.availability import get_availability_manager
            from oricli_core.brain.monitor import get_monitor_service
            from oricli_core.brain.degraded_classifier import get_degraded_classifier
            
            availability_manager = get_availability_manager()
            monitor_service = get_monitor_service()
            classifier = get_degraded_classifier()
            health_checker = get_health_checker()
            
            # Get health check
            health_check = health_checker.check_module_health(module_name)
            
            # Get module status from monitor
            module_status = monitor_service.get_module_status(module_name) if monitor_service else None
            
            # Get degradation classification
            degradation = None
            if module_status and module_status.state in ("degraded", "offline"):
                degradation = classifier.classify_degradation(
                    module_name,
                    health_check=health_check,
                    module_status=module_status
                )
            
            # Get fallback info
            fallback_module = classifier.get_fallback_module(module_name) if classifier else None
            
            return {
                "module_name": health_check.module_name,
                "status": health_check.status.value,
                "message": health_check.message,
                "timestamp": health_check.timestamp.isoformat(),
                "checks": health_check.checks,
                "details": health_check.details,
                "monitor_status": {
                    "state": module_status.state.value if module_status else "unknown",
                    "response_time": module_status.response_time if module_status else None,
                    "degradation_reason": module_status.degradation_reason if module_status else None,
                } if module_status else None,
                "degradation": {
                    "type": degradation.degradation_type.value,
                    "reason": degradation.reason,
                    "details": degradation.details
                } if degradation else None,
                "fallback_available": fallback_module is not None,
                "fallback_module": fallback_module
            }
        except Exception as e:
            raise HTTPException(
                status_code=500,
                detail=f"Error checking module health: {str(e)}"
            )
    
    @app.get("/warmup/status")
    async def get_warmup_status():
        """Get warmup status for all modules"""
        try:
            from oricli_core.brain.warmup import get_warmup_service
            warmup_service = get_warmup_service()
            status = warmup_service.get_warmup_status()
            
            return {
                "warmup_status": {
                    name: {
                        "status": result.status.value,
                        "duration": result.duration,
                        "error": result.error,
                        "test_passed": result.test_passed,
                        "details": result.details
                    }
                    for name, result in status.items()
                }
            }
        except Exception as e:
            raise HTTPException(
                status_code=500,
                detail=f"Error getting warmup status: {str(e)}"
            )
    
    @app.post("/warmup/{module_name}")
    async def force_warmup(module_name: str):
        """Force warmup of a module"""
        try:
            from oricli_core.brain.availability import get_availability_manager
            availability_manager = get_availability_manager()
            success = availability_manager.force_warmup(module_name)
            
            return {
                "module_name": module_name,
                "success": success
            }
        except Exception as e:
            raise HTTPException(
                status_code=500,
                detail=f"Error forcing warmup: {str(e)}"
            )
    
    @app.post("/recovery/{module_name}")
    async def force_recovery(module_name: str):
        """Force recovery of a module"""
        try:
            from oricli_core.brain.recovery import get_recovery_service
            recovery_service = get_recovery_service()
            attempt = recovery_service.recover_module(module_name)
            
            return {
                "module_name": module_name,
                "attempt_number": attempt.attempt_number,
                "status": attempt.status.value,
                "duration": attempt.duration,
                "error": attempt.error,
                "details": attempt.details
            }
        except Exception as e:
            raise HTTPException(
                status_code=500,
                detail=f"Error forcing recovery: {str(e)}"
            )
    
    @app.get("/fallback/mappings")
    async def get_fallback_mappings():
        """Get all fallback mappings"""
        try:
            from oricli_core.brain.degraded_classifier import get_degraded_classifier
            classifier = get_degraded_classifier()
            
            # Get mappings (we need to access the internal _fallback_mappings)
            # For now, return a message indicating mappings are configured
            return {
                "mappings_configured": True,
                "message": "Fallback mappings are configured via DegradedModeClassifier"
            }
        except Exception as e:
            raise HTTPException(
                status_code=500,
                detail=f"Error getting fallback mappings: {str(e)}"
            )
    
    @app.post("/fallback/mappings")
    async def register_fallback_mapping(request: Dict[str, Any]):
        """Register custom fallback mapping"""
        try:
            from oricli_core.brain.availability import get_availability_manager
            availability_manager = get_availability_manager()
            
            primary = request.get("primary")
            fallbacks = request.get("fallbacks", [])
            
            if not primary or not fallbacks:
                raise HTTPException(
                    status_code=400,
                    detail="Missing 'primary' or 'fallbacks' in request"
                )
            
            availability_manager.register_fallback_mapping(primary, fallbacks)
            
            return {
                "success": True,
                "primary": primary,
                "fallbacks": fallbacks
            }
        except Exception as e:
            raise HTTPException(
                status_code=500,
                detail=f"Error registering fallback mapping: {str(e)}"
            )
    
    @app.get("/fallback/stats")
    async def get_fallback_stats():
        """Get fallback usage statistics"""
        try:
            from oricli_core.brain.availability import get_availability_manager
            availability_manager = get_availability_manager()
            stats = availability_manager.get_fallback_usage_stats()
            
            return {
                "fallback_stats": stats
            }
        except Exception as e:
            raise HTTPException(
                status_code=500,
                detail=f"Error getting fallback stats: {str(e)}"
            )
    
    @app.get("/debug/modules")
    async def debug_modules():
        """Debug endpoint to check module discovery status"""
        try:
            from oricli_core.brain.registry import ModuleRegistry
            import os
            from pathlib import Path
            
            # Get discovery status
            discovered = ModuleRegistry._discovered
            discovering = ModuleRegistry._discovering
            available_modules = ModuleRegistry.list_modules()
            
            # Check if cognitive_generator is in the list
            cog_available = "cognitive_generator" in available_modules
            
            # Try to get the module to see what error we get
            cog_error = None
            try:
                ModuleRegistry.get_module("cognitive_generator", auto_discover=False)
            except Exception as e:
                cog_error = str(e)
            
            # Check modules directory
            modules_dir = ModuleRegistry.get_modules_dir()
            cog_file_exists = False
            if modules_dir:
                cog_file = modules_dir / "cognitive_generator.py"
                cog_file_exists = cog_file.exists()
            
            return {
                "discovery_status": {
                    "discovered": discovered,
                    "discovering": discovering,
                    "total_modules": len(available_modules),
                    "modules": available_modules[:20]  # First 20 modules
                },
                "cognitive_generator": {
                    "in_list": cog_available,
                    "file_exists": cog_file_exists,
                    "modules_dir": str(modules_dir) if modules_dir else None,
                    "error": cog_error
                }
            }
        except Exception as e:
            raise HTTPException(
                status_code=500,
                detail=f"Error in debug endpoint: {str(e)}"
            )
    
    @app.get("/modules/status")
    async def get_all_modules_status():
        """Get status of all modules - check if all are online"""
        try:
            from oricli_core.brain.availability import get_availability_manager
            availability_manager = get_availability_manager()
            
            all_online, details = availability_manager.are_all_modules_online()
            
            return {
                "all_modules_online": all_online,
                "status": "healthy" if all_online else "degraded",
                "details": details,
                "ensure_all_online": availability_manager._ensure_all_online
            }
        except Exception as e:
            raise HTTPException(
                status_code=500,
                detail=f"Error getting modules status: {str(e)}"
            )
    
    # Code execution endpoint (OricliAlpha-specific)
    @app.post("/v1/code_execution", response_model=CodeExecutionResponse)
    async def code_execution(
        request: CodeExecutionRequest,
        authorization: Optional[str] = Header(None, alias="Authorization")
    ):
        """Execute code in a secure sandbox"""
        # Verify API key
        try:
            app.state.get_api().verify_api_key(authorization)
        except Exception as e:
            raise HTTPException(
                status_code=401,
                detail=f"Authentication failed: {str(e)}"
            )
        
        try:
            from oricli_core.brain.registry import ModuleRegistry
            from oricli_core.services.sandbox.resource_limits import ResourceLimits
            
            # Get code execution module
            module = ModuleRegistry.get_module("code_execution")
            if not module:
                raise HTTPException(
                    status_code=503,
                    detail="Code execution module is not available"
                )
            
            # Convert request to module parameters
            params = {
                "session_id": request.session_id,
            }
            
            # Determine operation
            operation = None
            if request.operation == "execute":
                if request.language == "bash":
                    operation = "execute_command"
                    params["command"] = request.command
                elif request.language == "python":
                    operation = "execute_python"
                    params["code"] = request.code
                elif request.language == "node":
                    operation = "execute_node"
                    params["code"] = request.code
                else:
                    raise HTTPException(
                        status_code=400,
                        detail=f"Invalid language for execute operation: {request.language}"
                    )
            elif request.operation == "read_file":
                operation = "read_file"
                params["file_path"] = request.file_path
            elif request.operation == "write_file":
                operation = "write_file"
                params["file_path"] = request.file_path
                params["content"] = request.content
            elif request.operation == "list_files":
                operation = "list_files"
                params["directory"] = request.directory or "."
            elif request.operation == "delete_file":
                operation = "delete_file"
                params["file_path"] = request.file_path
            else:
                raise HTTPException(
                    status_code=400,
                    detail=f"Invalid operation: {request.operation}"
                )
            
            # Add resource limits if provided
            if request.resource_limits:
                params["resource_limits"] = {
                    "cpu_cores": request.resource_limits.cpu_cores,
                    "memory_mb": request.resource_limits.memory_mb,
                    "disk_mb": request.resource_limits.disk_mb,
                    "timeout_seconds": request.resource_limits.timeout_seconds,
                }
            
            # Validate required parameters
            if operation in ("execute_command",) and not params.get("command"):
                raise HTTPException(
                    status_code=400,
                    detail="Command is required for execute_command operation"
                )
            if operation in ("execute_python", "execute_node") and not params.get("code"):
                raise HTTPException(
                    status_code=400,
                    detail="Code is required for Python/Node.js execution"
                )
            if operation in ("read_file", "write_file", "delete_file") and not params.get("file_path"):
                raise HTTPException(
                    status_code=400,
                    detail="File path is required for file operations"
                )
            if operation == "write_file" and params.get("content") is None:
                raise HTTPException(
                    status_code=400,
                    detail="Content is required for write_file operation"
                )
            
            # Execute module operation
            result = module.execute(operation, params)
            
            # Convert result to response model
            resource_usage_data = result.get("resource_usage", {})
            resource_usage = ResourceUsageResponse(
                cpu_percent=resource_usage_data.get("cpu_percent", 0.0),
                memory_mb=resource_usage_data.get("memory_mb", 0.0),
                disk_mb=resource_usage_data.get("disk_mb", 0.0),
                execution_time=result.get("execution_time", 0.0),
            )
            
            return CodeExecutionResponse(
                session_id=result.get("session_id", ""),
                success=result.get("success", False),
                stdout=result.get("stdout"),
                stderr=result.get("stderr"),
                exit_code=result.get("exit_code"),
                file_content=result.get("file_content"),
                files=result.get("files"),
                file_path=result.get("file_path"),
                directory=result.get("directory"),
                execution_time=result.get("execution_time", 0.0),
                resource_usage=resource_usage,
            )
        except HTTPException:
            raise
        except Exception as e:
            raise HTTPException(
                status_code=500,
                detail=f"Code execution failed: {str(e)}"
            )
    
    # Tool registry endpoints (OricliAlpha-specific)
    @app.post("/v1/tools/register")
    async def register_tool(
        tool_def: ToolDefinition,
        authorization: Optional[str] = Header(None, alias="Authorization")
    ):
        """Register a tool for programmatic calling"""
        try:
            app.state.get_api().verify_api_key(authorization)
        except Exception as e:
            raise HTTPException(
                status_code=401,
                detail=f"Authentication failed: {str(e)}"
            )
        
        try:
            from oricli_core.brain.registry import ModuleRegistry
            from oricli_core.services.tool_registry import ToolRegistry
            
            tool_registry = ToolRegistry()
            
            # Get handler module and operation (from tool definition metadata)
            # For now, we require handler_module and handler_operation in parameters
            handler_module = tool_def.parameters.get("_handler_module", {}).get("default")
            handler_operation = tool_def.parameters.get("_handler_operation", {}).get("default")
            
            if not handler_module or not handler_operation:
                raise HTTPException(
                    status_code=400,
                    detail="Tool must specify handler_module and handler_operation in parameters"
                )
            
            module = ModuleRegistry.get_module(handler_module)
            if not module:
                raise HTTPException(
                    status_code=404,
                    detail=f"Module '{handler_module}' not found"
                )
            
            def tool_handler(**kwargs):
                return module.execute(handler_operation, kwargs)
            
            # Convert ToolDefinition to registry format
            tool_registry.register_tool(
                name=tool_def.name,
                description=tool_def.description,
                parameters={k: v.dict() if hasattr(v, 'dict') else v 
                           for k, v in tool_def.parameters.items() 
                           if not k.startswith('_')},
                handler=tool_handler,
                allowed_callers=tool_def.allowed_callers,
                result_format=tool_def.result_format,
            )
            
            return {"success": True, "tool_name": tool_def.name}
        except HTTPException:
            raise
        except Exception as e:
            raise HTTPException(
                status_code=500,
                detail=f"Tool registration failed: {str(e)}"
            )
    
    @app.get("/v1/tools")
    async def list_tools(
        caller: Optional[str] = None,
        authorization: Optional[str] = Header(None, alias="Authorization")
    ):
        """List all registered tools"""
        try:
            app.state.get_api().verify_api_key(authorization)
        except Exception as e:
            raise HTTPException(
                status_code=401,
                detail=f"Authentication failed: {str(e)}"
            )
        
        try:
            from oricli_core.services.tool_registry import ToolRegistry
            
            tool_registry = ToolRegistry()
            tools = tool_registry.list_tools(caller=caller)
            
            return {
                "tools": tools,
                "count": len(tools),
            }
        except Exception as e:
            raise HTTPException(
                status_code=500,
                detail=f"Failed to list tools: {str(e)}"
            )
    
    @app.post("/v1/tools/invoke", response_model=ToolInvocationResponse)
    async def invoke_tool(
        request: ToolInvocationRequest,
        authorization: Optional[str] = Header(None, alias="Authorization")
    ):
        """Invoke a tool directly"""
        try:
            app.state.get_api().verify_api_key(authorization)
        except Exception as e:
            raise HTTPException(
                status_code=401,
                detail=f"Authentication failed: {str(e)}"
            )
        
        try:
            from oricli_core.services.tool_registry import ToolRegistry, ToolRegistryError
            
            tool_registry = ToolRegistry()
            
            result = tool_registry.invoke_tool(
                tool_name=request.tool_name,
                input_params=request.input,
                caller=request.caller,
            )
            
            return ToolInvocationResponse(
                success=True,
                result=result,
            )
        except ToolRegistryError as e:
            return ToolInvocationResponse(
                success=False,
                error=str(e),
            )
        except Exception as e:
            raise HTTPException(
                status_code=500,
                detail=f"Tool invocation failed: {str(e)}"
            )
    
    @app.post("/v1/code_execution/with_tools")
    async def code_execution_with_tools(
        request: Dict[str, Any],
        authorization: Optional[str] = Header(None, alias="Authorization")
    ):
        """Execute code with programmatic tool calling enabled"""
        try:
            app.state.get_api().verify_api_key(authorization)
        except Exception as e:
            raise HTTPException(
                status_code=401,
                detail=f"Authentication failed: {str(e)}"
            )
        
        try:
            from oricli_core.brain.registry import ModuleRegistry
            
            module = ModuleRegistry.get_module("programmatic_tool_calling")
            if not module:
                raise HTTPException(
                    status_code=503,
                    detail="Programmatic tool calling module is not available"
                )
            
            result = module.execute("execute_with_tools", request)
            
            return result
        except HTTPException:
            raise
        except Exception as e:
            raise HTTPException(
                status_code=500,
                detail=f"Code execution with tools failed: {str(e)}"
            )
    
    # Web fetch endpoint (OricliAlpha-specific)
    @app.post("/v1/web_fetch", response_model=WebFetchResponse)
    async def web_fetch(
        request: WebFetchRequest,
        authorization: Optional[str] = Header(None, alias="Authorization")
    ):
        """Fetch content from a web page or PDF"""
        try:
            app.state.get_api().verify_api_key(authorization)
        except Exception as e:
            raise HTTPException(
                status_code=401,
                detail=f"Authentication failed: {str(e)}"
            )
        
        try:
            from oricli_core.brain.registry import ModuleRegistry
            
            module = ModuleRegistry.get_module("web_fetch")
            if not module:
                raise HTTPException(
                    status_code=503,
                    detail="Web fetch module is not available"
                )
            
            result = module.execute("fetch_url", request.dict())
            
            return WebFetchResponse(**result)
        except HTTPException:
            raise
        except Exception as e:
            raise HTTPException(
                status_code=500,
                detail=f"Web fetch failed: {str(e)}"
            )
    
    # Python LLM endpoints (OricliAlpha-specific)
    @app.post("/v1/python/understand", response_model=PythonUnderstandResponse)
    async def python_understand(
        request: PythonUnderstandRequest,
        authorization: Optional[str] = Header(None, alias="Authorization")
    ):
        """Perform semantic understanding of Python code"""
        try:
            app.state.get_api().verify_api_key(authorization)
        except Exception as e:
            raise HTTPException(
                status_code=401,
                detail=f"Authentication failed: {str(e)}"
            )
        
        try:
            from oricli_core.brain.registry import ModuleRegistry
            
            module = ModuleRegistry.get_module("python_semantic_understanding")
            if not module:
                raise HTTPException(
                    status_code=503,
                    detail="Python semantic understanding module is not available"
                )
            
            result = module.execute("analyze_semantics", {"code": request.code})
            
            if not result.get("success"):
                return PythonUnderstandResponse(
                    success=False,
                    error=result.get("error", "Analysis failed")
                )
            
            return PythonUnderstandResponse(
                success=True,
                semantic_analysis=result,
                type_inference=result.get("types"),
                dependency_graph=result.get("dependencies"),
                call_graph=result.get("call_graph"),
            )
        except HTTPException:
            raise
        except Exception as e:
            raise HTTPException(
                status_code=500,
                detail=f"Python understanding failed: {str(e)}"
            )
    
    @app.post("/v1/python/generate", response_model=PythonGenerateResponse)
    async def python_generate(
        request: PythonGenerateRequest,
        authorization: Optional[str] = Header(None, alias="Authorization")
    ):
        """Generate Python code through reasoning"""
        try:
            app.state.get_api().verify_api_key(authorization)
        except Exception as e:
            raise HTTPException(
                status_code=401,
                detail=f"Authentication failed: {str(e)}"
            )
        
        try:
            from oricli_core.brain.registry import ModuleRegistry
            
            module = ModuleRegistry.get_module("reasoning_code_generator")
            if not module:
                raise HTTPException(
                    status_code=503,
                    detail="Reasoning code generator module is not available"
                )
            
            reasoning_method = request.reasoning_method or "cot"
            
            result = module.execute("generate_code_reasoning", {
                "requirements": request.requirements,
                "reasoning_method": reasoning_method,
            })
            
            if not result.get("success"):
                return PythonGenerateResponse(
                    success=False,
                    error=result.get("error", "Code generation failed")
                )
            
            return PythonGenerateResponse(
                success=True,
                code=result.get("code", ""),
                explanation=result.get("explanation", ""),
                reasoning_steps=result.get("reasoning_steps", []),
                verification=result.get("verification", {}),
            )
        except HTTPException:
            raise
        except Exception as e:
            raise HTTPException(
                status_code=500,
                detail=f"Python generation failed: {str(e)}"
            )
    
    @app.post("/v1/python/reason", response_model=PythonReasonResponse)
    async def python_reason(
        request: PythonReasonRequest,
        authorization: Optional[str] = Header(None, alias="Authorization")
    ):
        """Reason about Python code"""
        try:
            app.state.get_api().verify_api_key(authorization)
        except Exception as e:
            raise HTTPException(
                status_code=401,
                detail=f"Authentication failed: {str(e)}"
            )
        
        try:
            from oricli_core.brain.registry import ModuleRegistry
            
            reasoning_type = request.reasoning_type or "behavior"
            
            if reasoning_type == "behavior":
                module = ModuleRegistry.get_module("program_behavior_reasoning")
                if not module:
                    raise HTTPException(
                        status_code=503,
                        detail="Program behavior reasoning module is not available"
                    )
                
                # Use predict_execution for behavior reasoning
                result = module.execute("predict_execution", {
                    "code": request.code,
                    "inputs": {},
                })
                
                return PythonReasonResponse(
                    success=result.get("success", False),
                    result=result,
                )
            
            elif reasoning_type == "optimization":
                module = ModuleRegistry.get_module("code_optimization_reasoning")
                if not module:
                    raise HTTPException(
                        status_code=503,
                        detail="Code optimization reasoning module is not available"
                    )
                
                result = module.execute("identify_optimizations", {
                    "code": request.code,
                })
                
                return PythonReasonResponse(
                    success=result.get("success", False),
                    result=result,
                )
            
            else:
                return PythonReasonResponse(
                    success=False,
                    error=f"Unknown reasoning type: {reasoning_type}"
                )
        except HTTPException:
            raise
        except Exception as e:
            raise HTTPException(
                status_code=500,
                detail=f"Python reasoning failed: {str(e)}"
            )
    
    @app.post("/v1/python/complete", response_model=PythonCompleteResponse)
    async def python_complete(
        request: PythonCompleteRequest,
        authorization: Optional[str] = Header(None, alias="Authorization")
    ):
        """Complete Python code with context awareness"""
        try:
            app.state.get_api().verify_api_key(authorization)
        except Exception as e:
            raise HTTPException(
                status_code=401,
                detail=f"Authentication failed: {str(e)}"
            )
        
        try:
            from oricli_core.brain.registry import ModuleRegistry
            
            module = ModuleRegistry.get_module("reasoning_code_completion")
            if not module:
                raise HTTPException(
                    status_code=503,
                    detail="Reasoning code completion module is not available"
                )
            
            result = module.execute("complete_code_reasoning", {
                "partial_code": request.partial_code,
                "context": request.context or {},
            })
            
            if not result.get("success"):
                return PythonCompleteResponse(
                    success=False,
                    error=result.get("error", "Code completion failed")
                )
            
            return PythonCompleteResponse(
                success=True,
                completion=result.get("completion", ""),
                explanation=result.get("explanation", ""),
            )
        except HTTPException:
            raise
        except Exception as e:
            raise HTTPException(
                status_code=500,
                detail=f"Python completion failed: {str(e)}"
            )
    
    @app.post("/v1/python/embed", response_model=PythonEmbedResponse)
    async def python_embed(
        request: PythonEmbedRequest,
        authorization: Optional[str] = Header(None, alias="Authorization")
    ):
        """Generate semantic embedding for Python code"""
        try:
            app.state.get_api().verify_api_key(authorization)
        except Exception as e:
            raise HTTPException(
                status_code=401,
                detail=f"Authentication failed: {str(e)}"
            )
        
        try:
            from oricli_core.brain.registry import ModuleRegistry
            
            module = ModuleRegistry.get_module("python_code_embeddings")
            if not module:
                raise HTTPException(
                    status_code=503,
                    detail="Python code embeddings module is not available"
                )
            
            result = module.execute("embed_code", {"code": request.code})
            
            if not result.get("embedding"):
                return PythonEmbedResponse(
                    success=False,
                    error="Failed to generate embedding"
                )
            
            return PythonEmbedResponse(
                success=True,
                embedding=result.get("embedding"),
                dimension=result.get("dimension"),
                method=result.get("method"),
            )
        except HTTPException:
            raise
        except Exception as e:
            raise HTTPException(
                status_code=500,
                detail=f"Python embedding failed: {str(e)}"
            )
    
    @app.post("/v1/python/test", response_model=PythonTestGenerationResponse)
    async def python_test_generation(
        request: PythonTestGenerationRequest,
        authorization: Optional[str] = Header(None, alias="Authorization")
    ):
        """Generate tests for Python code"""
        try:
            app.state.get_api().verify_api_key(authorization)
        except Exception as e:
            raise HTTPException(
                status_code=401,
                detail=f"Authentication failed: {str(e)}"
            )
        
        try:
            from oricli_core.brain.registry import ModuleRegistry
            
            module = ModuleRegistry.get_module("test_generation_reasoning")
            if not module:
                raise HTTPException(
                    status_code=503,
                    detail="Test generation reasoning module is not available"
                )
            
            test_type = request.test_type or "all"
            
            if test_type == "edge_case":
                result = module.execute("generate_edge_case_tests", {
                    "code": request.code,
                })
            elif test_type == "property":
                result = module.execute("generate_property_tests", {
                    "code": request.code,
                })
            else:
                result = module.execute("generate_tests", {
                    "code": request.code,
                })
            
            if not result.get("success"):
                return PythonTestGenerationResponse(
                    success=False,
                    error=result.get("error", "Test generation failed")
                )
            
            return PythonTestGenerationResponse(
                success=True,
                test_suite=result.get("test_suite", ""),
                test_cases=result.get("test_cases", []),
            )
        except HTTPException:
            raise
        except Exception as e:
            raise HTTPException(
                status_code=500,
                detail=f"Python test generation failed: {str(e)}"
            )
    
    # Error handlers
    @app.exception_handler(HTTPException)
    async def http_exception_handler(request, exc):
        """Handle HTTP exceptions"""
        return JSONResponse(
            status_code=exc.status_code,
            content={
                "error": {
                    "message": exc.detail,
                    "type": "invalid_request_error",
                    "code": exc.status_code
                }
            }
        )
    
    @app.exception_handler(Exception)
    async def general_exception_handler(request, exc):
        """Handle general exceptions"""
        return JSONResponse(
            status_code=500,
            content={
                "error": {
                    "message": str(exc),
                    "type": "server_error",
                    "code": 500
                }
            }
        )
    
    return app


def find_available_port(host: str, start_port: int, max_attempts: int = 100) -> int:
    """
    Find an available port starting from start_port
    
    Args:
        host: Host to bind to
        start_port: Starting port number
        max_attempts: Maximum number of ports to try
    
    Returns:
        Available port number
    """
    for port in range(start_port, start_port + max_attempts):
        try:
            with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
                s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
                s.bind((host, port))
                return port
        except OSError:
            continue
    raise RuntimeError(f"Could not find available port in range {start_port}-{start_port + max_attempts - 1}")


def run_server(
    host: str = "0.0.0.0",
    port: int = 8000,
    modules_dir: Optional[Path] = None,
    api_key: Optional[str] = None,
    reload: bool = False,
    log_level: str = "info",
    auto_port: bool = True,
    enable_cors: bool = True,
    cors_origins: Optional[List[str]] = None,
    require_auth: bool = False
):
    """
    Run the embedded HTTP server
    
    Args:
        host: Server host
        port: Server port (starting port if auto_port is True)
        modules_dir: Optional path to brain_modules directory
        api_key: Optional API key for authentication
        reload: Enable auto-reload (for development)
        log_level: Logging level
        auto_port: Automatically find available port if requested port is in use
        enable_cors: Enable CORS middleware
        cors_origins: List of allowed CORS origins
        require_auth: Whether to require authentication
    """
    # Force stderr to be unbuffered
    import sys
    sys.stderr.reconfigure(line_buffering=True) if hasattr(sys.stderr, 'reconfigure') else None
    
    try:
        print("[DEBUG] Starting create_app()...", file=sys.stderr, flush=True)
        app = create_app(
            modules_dir=modules_dir,
            api_key=api_key,
            enable_cors=enable_cors,
            cors_origins=cors_origins,
            require_auth=require_auth
        )
        print(f"[DEBUG] App created successfully with {len(app.routes)} routes", file=sys.stderr, flush=True)
    except Exception as e:
        print(f"[ERROR] Failed to create app: {e}", file=sys.stderr, flush=True)
        import traceback
        traceback.print_exc(file=sys.stderr)
        sys.stderr.flush()
        raise
    
    # Auto-detect available port if requested
    actual_port = port
    if auto_port:
        try:
            actual_port = find_available_port(host, port)
            if actual_port != port:
                print(f"Port {port} is in use, using port {actual_port} instead", file=sys.stderr)
        except RuntimeError as e:
            print(f"Error finding available port: {e}", file=sys.stderr)
            raise
    
    print(f"Starting OricliAlpha API server on {host}:{actual_port}", file=sys.stderr, flush=True)
    print(f"API documentation available at http://{host}:{actual_port}/docs", file=sys.stderr, flush=True)
    
    try:
        print(f"[DEBUG] Starting uvicorn server on {host}:{actual_port}", file=sys.stderr, flush=True)
        print(f"[DEBUG] App has {len(app.routes)} routes registered", file=sys.stderr, flush=True)
        print(f"[DEBUG] Creating uvicorn config...", file=sys.stderr, flush=True)
        
        # Use explicit Server configuration for better control
        import uvicorn
        config = uvicorn.Config(
            app,
            host=host,
            port=actual_port,
            reload=reload,
            log_level=log_level,
            access_log=True,
        )
        
        print(f"[DEBUG] Creating uvicorn Server instance...", file=sys.stderr, flush=True)
        server = uvicorn.Server(config)
        
        print(f"[DEBUG] Starting server.run()...", file=sys.stderr, flush=True)
        # This will block until server stops
        server.run()
    except KeyboardInterrupt:
        print("\nShutting down server...", file=sys.stderr)
    except OSError as e:
        if "Address already in use" in str(e):
            print(f"\nError: Port {actual_port} is already in use.", file=sys.stderr)
            print(f"Try using a different port: --port {actual_port + 1}", file=sys.stderr)
        else:
            print(f"\nError starting server: {e}", file=sys.stderr)
        raise
    except Exception as e:
        print(f"\nError starting server: {e}", file=sys.stderr)
        import traceback
        traceback.print_exc()
        raise


def main():
    """Main entry point for CLI"""
    import argparse
    
    parser = argparse.ArgumentParser(description="OricliAlpha Core API Server")
    parser.add_argument("--host", default="0.0.0.0", help="Server host")
    parser.add_argument("--port", type=int, default=8000, help="Server port (starting port if auto-port is enabled)")
    parser.add_argument("--modules-dir", type=str, help="Path to brain_modules directory")
    parser.add_argument("--api-key", type=str, help="API key for authentication")
    parser.add_argument("--reload", action="store_true", help="Enable auto-reload")
    parser.add_argument("--log-level", default="info", help="Logging level")
    parser.add_argument("--no-auto-port", action="store_true", help="Disable automatic port selection (fail if port is in use)")
    parser.add_argument("--no-cors", action="store_true", help="Disable CORS middleware")
    parser.add_argument("--cors-origins", type=str, nargs="+", help="Allowed CORS origins (space-separated)")
    parser.add_argument("--require-auth", action="store_true", help="Require API key authentication for all requests")
    
    args = parser.parse_args()
    
    modules_dir = Path(args.modules_dir) if args.modules_dir else None
    
    run_server(
        host=args.host,
        port=args.port,
        modules_dir=modules_dir,
        api_key=args.api_key,
        reload=args.reload,
        log_level=args.log_level,
        auto_port=not args.no_auto_port,
        enable_cors=not args.no_cors,
        cors_origins=args.cors_origins,
        require_auth=args.require_auth,
    )


if __name__ == "__main__":
    main()

