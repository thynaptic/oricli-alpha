"""
Mavaia Core Embedded HTTP Server
FastAPI-based server that can run standalone
"""

import os
import socket
import sys
from typing import Optional, List
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
    from fastapi import FastAPI, HTTPException, Request, Header
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

from mavaia_core.api.openai_compatible import OpenAICompatibleAPI
from mavaia_core.client import MavaiaClient
from mavaia_core.brain.metrics import get_metrics_collector
from mavaia_core.brain.health import get_health_checker
from mavaia_core.system_identifier import SYSTEM_ID, SYSTEM_ID_FULL
from mavaia_core.types.models import (
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
)


def _register_builtin_tools() -> None:
    """Register built-in tools (web_fetch, etc.) with the tool registry."""
    try:
        from mavaia_core.services.tool_registry import ToolRegistry
        from mavaia_core.brain.registry import ModuleRegistry
        
        # Ensure modules are discovered
        ModuleRegistry.discover_modules()
        
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
    
    # Get API key from parameter or environment variable
    actual_api_key = api_key or os.getenv("MAVAIA_API_KEY")
    actual_require_auth = require_auth or os.getenv("MAVAIA_REQUIRE_AUTH", "false").lower() == "true"
    
    # Use lifespan context manager for startup/shutdown
    from contextlib import asynccontextmanager
    
    @asynccontextmanager
    async def lifespan_context():
        """Lifespan context manager for startup/shutdown"""
        # Startup
        try:
            sys.stderr.write("[DEBUG] Lifespan startup triggered\n")
            sys.stderr.flush()
            # Register built-in tools after modules are discovered
            # This will happen lazily when modules are first accessed
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
        sys.stderr.write("[DEBUG] Lifespan shutdown\n")
        sys.stderr.flush()
    
    try:
        sys.stderr.write("[DEBUG] Creating FastAPI app...\n")
        sys.stderr.flush()
        app = FastAPI(
            title="Mavaia Core API",
            description=f"Mavaia Core - OpenAI-compatible API for Mavaia capabilities (System: {SYSTEM_ID_FULL()})",
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
                print("[DEBUG] Initializing MavaiaClient...", file=sys.stderr)
                sys.stderr.flush()
                app.state._client = MavaiaClient(modules_dir=app.state.modules_dir)
                print("[DEBUG] MavaiaClient initialized", file=sys.stderr)
                sys.stderr.flush()
            except Exception as e:
                print(f"[ERROR] Failed to initialize MavaiaClient: {e}", file=sys.stderr)
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
            "service": "mavaia-core",
            "version": "1.0.0",
            "system_id": SYSTEM_ID,
            "system_id_full": SYSTEM_ID_FULL()
        }
    
    # OpenAI-compatible endpoints
    @app.post("/v1/chat/completions", response_model=ChatCompletionResponse)
    async def chat_completions(
        request: ChatCompletionRequest,
        authorization: Optional[str] = None
    ):
        """OpenAI-compatible chat completions endpoint"""
        return await app.state.get_api().chat_completions(request, authorization)
    
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
    
    # Module discovery endpoint (Mavaia-specific)
    @app.get("/v1/modules")
    async def list_modules():
        """List available brain modules"""
        from mavaia_core.brain.registry import ModuleRegistry
        
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
    
    # Metrics endpoint (Mavaia-specific)
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
    
    # Health check endpoint (Mavaia-specific)
    @app.get("/v1/health/modules")
    async def get_module_health():
        """Get health status of all modules"""
        try:
            health_checker = get_health_checker()
            summary = health_checker.get_health_summary()
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
            health_checker = get_health_checker()
            health_check = health_checker.check_module_health(module_name)
            return {
                "module_name": health_check.module_name,
                "status": health_check.status.value,
                "message": health_check.message,
                "timestamp": health_check.timestamp.isoformat(),
                "checks": health_check.checks,
                "details": health_check.details
            }
        except Exception as e:
            raise HTTPException(
                status_code=500,
                detail=f"Error checking module health: {str(e)}"
            )
    
    # Code execution endpoint (Mavaia-specific)
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
            from mavaia_core.brain.registry import ModuleRegistry
            from mavaia_core.services.sandbox.resource_limits import ResourceLimits
            
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
    
    # Tool registry endpoints (Mavaia-specific)
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
            from mavaia_core.brain.registry import ModuleRegistry
            from mavaia_core.services.tool_registry import ToolRegistry
            
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
            from mavaia_core.services.tool_registry import ToolRegistry
            
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
            from mavaia_core.services.tool_registry import ToolRegistry, ToolRegistryError
            
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
            from mavaia_core.brain.registry import ModuleRegistry
            
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
    
    # Web fetch endpoint (Mavaia-specific)
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
            from mavaia_core.brain.registry import ModuleRegistry
            
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
    
    # Python LLM endpoints (Mavaia-specific)
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
            from mavaia_core.brain.registry import ModuleRegistry
            
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
            from mavaia_core.brain.registry import ModuleRegistry
            
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
            from mavaia_core.brain.registry import ModuleRegistry
            
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
            from mavaia_core.brain.registry import ModuleRegistry
            
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
            from mavaia_core.brain.registry import ModuleRegistry
            
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
            from mavaia_core.brain.registry import ModuleRegistry
            
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
    
    print(f"Starting Mavaia API server on {host}:{actual_port}", file=sys.stderr, flush=True)
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
    
    parser = argparse.ArgumentParser(description="Mavaia Core API Server")
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

