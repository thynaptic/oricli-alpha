#!/usr/bin/env python3
"""
Remote Execution script for Sovereign Goals.
Runs on the RunPod instance to execute steps of a long-horizon plan.
"""

import os
import sys
import argparse
import logging
from pathlib import Path

# Add project root to path
REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT))

from oricli_core.brain.registry import ModuleRegistry

def execute_goal(goal_id):
    print(f"🚀 Initializing Sovereign Goal Execution: {goal_id}")
    
    # 1. Discover modules
    ModuleRegistry.discover_modules()
    
    # 2. Load Long Horizon Planner
    try:
        planner = ModuleRegistry.get_module("long_horizon_planner")
        if not planner:
            print("✗ Failed to load long_horizon_planner.")
            return
    except Exception as e:
        print(f"✗ Error loading planner: {e}")
        return

    # 3. Resume or Create Plan
    # First, try to resume an existing persistent plan
    print(f"  - Attempting to resume plan for {goal_id}...")
    result = planner.execute("resume_plan", {"goal_id": goal_id})
    
    if not result.get("success") and "No persistent plan found" in result.get("error", ""):
        # If no plan exists, we need to find the original goal text from the registry
        print("  - No existing plan found. Finding goal metadata...")
        from oricli_core.services.goal_service import GoalService
        service = GoalService()
        objectives = service.list_objectives()
        goal_meta = next((obj for obj in objectives if obj["id"] == goal_id), None)
        
        if not goal_meta:
            print(f"✗ Goal ID {goal_id} not found in registry.")
            return
            
        print(f"  - Creating new plan for goal: {goal_meta['goal']}")
        result = planner.execute("create_long_plan", {
            "goal": goal_meta["goal"],
            "goal_id": goal_id,
            "use_mcts": True
        })
        
        if result.get("success"):
            plan = {"steps": result.get("steps"), "goal_id": goal_id}
            print(f"  - Plan created with {len(plan['steps'])} steps. Starting execution...")
            result = planner.execute("execute_plan", {"plan": plan, "goal_id": goal_id})

    if result.get("success"):
        print(f"\n✨ Goal {goal_id} pass complete! Progress: {result.get('completion_percentage', 0)*100:.1f}%")
    else:
        print(f"\n✗ Goal {goal_id} execution encountered issues: {result.get('error')}")

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--goal-id", required=True, help="ID of the goal to execute")
    args = parser.parse_args()
    
    execute_goal(args.goal_id)
