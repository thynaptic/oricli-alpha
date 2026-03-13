#!/usr/bin/env python3
"""
Local Goal Executor.
Executes a specific goal locally using CPU resources.
"""

import os
import sys
import argparse
import logging
from pathlib import Path

# Setup paths
REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT))

from oricli_core.services.goal_service import GoalService
from oricli_core.brain.registry import ModuleRegistry

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(message)s',
    handlers=[
        logging.StreamHandler(sys.stdout)
    ]
)
logger = logging.getLogger("local-executor")

def main():
    parser = argparse.ArgumentParser(description="Execute a goal locally")
    parser.add_argument("--goal-id", required=True, help="ID of the goal to execute")
    args = parser.parse_args()

    goal_service = GoalService()
    
    # Verify goal exists
    objectives = goal_service.list_objectives()
    goal = next((g for g in objectives if g["id"] == args.goal_id), None)
    
    if not goal:
        logger.error(f"Goal {args.goal_id} not found.")
        sys.exit(1)
        
    logger.info(f"Executing goal locally: {goal['goal']}")
    
    # Update status to active
    goal_service.update_objective(args.goal_id, {"status": "active"})
    
    # Load cognitive generator
    ModuleRegistry.discover_modules()
    try:
        cog_gen = ModuleRegistry.get_module("cognitive_generator")
    except Exception as e:
        logger.error(f"Failed to load cognitive_generator: {e}")
        goal_service.update_objective(args.goal_id, {"status": "failed"})
        sys.exit(1)
        
    if not cog_gen:
        logger.error("cognitive_generator module not available.")
        goal_service.update_objective(args.goal_id, {"status": "failed"})
        sys.exit(1)
        
    # Execute goal
    try:
        prompt = f"GOAL: {goal['goal']}\n\nPlease execute this goal to the best of your ability using available local tools and reasoning."
        
        # Add context if available
        if "context" in goal and goal["context"]:
            prompt += f"\n\nCONTEXT:\n{goal['context']}"
            
        res = cog_gen.execute("generate_response", {"input": prompt})
        
        if res.get("success", True):
            logger.info("Goal execution completed successfully.")
            goal_service.update_objective(args.goal_id, {"status": "completed"})
            
            # Save result to a file for reference
            result_file = REPO_ROOT / f"goal_{args.goal_id}_result.txt"
            with open(result_file, "w", encoding="utf-8") as f:
                f.write(res.get("text", "No text output generated."))
            logger.info(f"Result saved to {result_file}")
        else:
            logger.error("Goal execution failed during generation.")
            goal_service.update_objective(args.goal_id, {"status": "failed"})
            
    except Exception as e:
        logger.error(f"Error executing goal: {e}")
        goal_service.update_objective(args.goal_id, {"status": "failed"})
        sys.exit(1)

if __name__ == "__main__":
    main()
