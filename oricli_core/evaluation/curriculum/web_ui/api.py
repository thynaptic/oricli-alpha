from __future__ import annotations
"""
Web UI API Endpoints

REST API and WebSocket endpoints for curriculum testing.
"""

import asyncio
from pathlib import Path
from typing import Any, Dict, List, Optional

try:
    from fastapi import APIRouter, WebSocket, WebSocketDisconnect, HTTPException
    from pydantic import BaseModel
    FASTAPI_AVAILABLE = True
except ImportError:
    FASTAPI_AVAILABLE = False

from oricli_core.evaluation.curriculum.selector import CurriculumSelector
from oricli_core.evaluation.curriculum.executor import TestExecutor
from oricli_core.evaluation.curriculum.analyzer import ResultAnalyzer
from oricli_core.evaluation.curriculum.reporter import TestReporter
from oricli_core.evaluation.curriculum.models import TestConfiguration


if FASTAPI_AVAILABLE:
    router = APIRouter(prefix="/api", tags=["curriculum"])
    
    # Shared instances
    selector = CurriculumSelector()
    executor = TestExecutor()
    analyzer = ResultAnalyzer()
    reporter = TestReporter()
    
    # Active test sessions
    active_tests: Dict[str, Dict[str, Any]] = {}
    
    @router.get("/curriculum/levels")
    async def get_levels() -> List[str]:
        """Get available education levels"""
        return selector.list_levels()
    
    @router.get("/curriculum/subjects")
    async def get_subjects(level: Optional[str] = None) -> List[str]:
        """Get available subjects"""
        return selector.list_subjects(level)
    
    @router.get("/curriculum/skill-types")
    async def get_skill_types() -> List[str]:
        """Get available skill types"""
        return selector.list_skill_types()
    
    @router.get("/curriculum/difficulty-styles")
    async def get_difficulty_styles() -> List[str]:
        """Get available difficulty styles"""
        return selector.list_difficulty_styles()
    
    class ExecuteTestRequest(BaseModel):
        """Request model for test execution"""
        level: str
        subject: str
        skill_type: str
        difficulty_style: str
        constraints: Optional[Dict[str, Any]] = None
        test_id: Optional[str] = None
    
    @router.post("/tests/execute")
    async def execute_test(request: ExecuteTestRequest) -> Dict[str, Any]:
        """Execute a test"""
        try:
            config = selector.select_curriculum(
                level=request.level,
                subject=request.subject,
                skill_type=request.skill_type,
                difficulty_style=request.difficulty_style,
            )
            
            test_id = f"test_{len(active_tests)}"
            active_tests[test_id] = {"status": "running", "config": config}
            
            # Execute in background
            result = executor.execute_test(config)
            
            active_tests[test_id] = {
                "status": "completed",
                "result": result.to_dict(),
            }
            
            return {
                "test_id": test_id,
                "status": "completed",
                "result": result.to_dict(),
            }
        
        except Exception as e:
            raise HTTPException(status_code=500, detail=str(e))
    
    @router.get("/tests/{test_id}/status")
    async def get_test_status(test_id: str) -> Dict[str, Any]:
        """Get test execution status"""
        if test_id not in active_tests:
            raise HTTPException(status_code=404, detail="Test not found")
        
        return active_tests[test_id]
    
    @router.get("/tests/{test_id}/results")
    async def get_test_results(test_id: str) -> Dict[str, Any]:
        """Get test results"""
        if test_id not in active_tests:
            raise HTTPException(status_code=404, detail="Test not found")
        
        test_data = active_tests[test_id]
        if test_data["status"] != "completed":
            raise HTTPException(status_code=400, detail="Test not completed")
        
        return test_data["result"]
    
    @router.get("/tests/history")
    async def get_test_history() -> List[Dict[str, Any]]:
        """Get historical test runs"""
        # Load from results directory
        results_dir = Path(__file__).parent.parent / "results"
        history = []
        
        for result_file in sorted(results_dir.glob("*.json"), reverse=True)[:20]:
            try:
                import json
                with open(result_file, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    history.append({
                        "file": result_file.name,
                        "timestamp": data.get("timestamp"),
                        "total_tests": data.get("total_tests", 0),
                    })
            except Exception:
                pass
        
        return history
    
    @router.get("/results/{result_id}/trace")
    async def get_reasoning_trace(result_id: str) -> Dict[str, Any]:
        """Get reasoning trace for result"""
        # Load result and return trace
        # (simplified - would load from results directory)
        return {"trace": {}}
    
    @router.get("/results/{result_id}/cognitive-maps")
    async def get_cognitive_maps(result_id: str) -> Dict[str, Any]:
        """Get cognitive maps for result"""
        # Load result and return maps
        # (simplified - would load from results directory)
        return {"weakness_map": {}, "strength_map": {}}
    
    @router.get("/results/compare")
    async def compare_results(result_ids: str) -> Dict[str, Any]:
        """Compare multiple test runs"""
        # Parse result IDs
        ids = result_ids.split(",")
        
        # Load and compare results
        # (simplified)
        return {"comparison": {}}
    
    @router.websocket("/ws/test/{test_id}")
    async def websocket_test_updates(websocket: WebSocket, test_id: str):
        """WebSocket for real-time test updates"""
        await websocket.accept()
        
        try:
            while True:
                # Send updates
                if test_id in active_tests:
                    await websocket.send_json(active_tests[test_id])
                else:
                    await websocket.send_json({"status": "not_found"})
                
                await asyncio.sleep(1)
        
        except WebSocketDisconnect:
            pass

else:
    router = None

