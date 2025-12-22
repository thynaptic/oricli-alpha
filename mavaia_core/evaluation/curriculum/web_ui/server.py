"""
Web UI Server

FastAPI server for curriculum testing web interface.
"""

import asyncio
from pathlib import Path
from typing import Any, Dict, List, Optional

try:
    from fastapi import FastAPI, WebSocket, WebSocketDisconnect
    from fastapi.staticfiles import StaticFiles
    from fastapi.responses import HTMLResponse, FileResponse
    from fastapi.middleware.cors import CORSMiddleware
    FASTAPI_AVAILABLE = True
except ImportError:
    FASTAPI_AVAILABLE = False

from mavaia_core.evaluation.curriculum.executor import TestExecutor
from mavaia_core.evaluation.curriculum.analyzer import ResultAnalyzer
from mavaia_core.evaluation.curriculum.reporter import TestReporter
from mavaia_core.evaluation.curriculum.models import TestConfiguration
from mavaia_core.evaluation.curriculum.selector import CurriculumSelector


def create_app() -> Any:
    """Create FastAPI application"""
    if not FASTAPI_AVAILABLE:
        raise ImportError("fastapi and uvicorn are required. Install with: pip install fastapi uvicorn")
    
    app = FastAPI(title="Mavaia Curriculum Testing Framework")
    
    # CORS
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    
    # Static files
    static_dir = Path(__file__).parent / "static"
    if static_dir.exists():
        app.mount("/static", StaticFiles(directory=str(static_dir)), name="static")
    
    # API routes
    from mavaia_core.evaluation.curriculum.web_ui.api import router
    app.include_router(router)
    
    # Serve index.html
    @app.get("/", response_class=HTMLResponse)
    async def index():
        index_file = static_dir / "index.html"
        if index_file.exists():
            return FileResponse(index_file)
        return "<html><body><h1>Web UI not yet implemented</h1></body></html>"
    
    return app


def start_web_ui(host: str = "0.0.0.0", port: int = 8080) -> None:
    """
    Start web UI server
    
    Args:
        host: Host to bind to
        port: Port to bind to
    """
    if not FASTAPI_AVAILABLE:
        raise ImportError("fastapi and uvicorn are required. Install with: pip install fastapi uvicorn")
    
    import uvicorn
    
    app = create_app()
    
    print(f"Starting Web UI server on http://{host}:{port}")
    uvicorn.run(app, host=host, port=port)


if __name__ == "__main__":
    start_web_ui()

