#!/usr/bin/env python3
"""
OricliAlpha Goal Submission Utility.
Add new high-level objectives to the Sovereign Goal registry.
"""

import os
import sys
import argparse
from pathlib import Path

# Add project root to path
REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT))

from oricli_core.services.goal_service import GoalService

def main():
    parser = argparse.ArgumentParser(description="OricliAlpha Sovereign Goal Submission")
    parser.add_argument("goal", type=str, help="The high-level objective text")
    parser.add_argument("--priority", type=int, default=1, help="Priority level (1-5, higher is more urgent)")
    parser.add_argument("--list", action="store_true", help="List all current objectives")
    
    args = parser.parse_args()
    service = GoalService()

    if args.list:
        print("\n📊 Current Sovereign Goals:")
        print("-" * 60)
        objectives = service.list_objectives()
        if not objectives:
            print("No goals registered.")
        else:
            for obj in objectives:
                status_color = "🟢" if obj["status"] == "completed" else "🟡" if obj["status"] == "active" else "⚪"
                print(f"{status_color} [{obj['id']}] (Priority: {obj['priority']}) Progress: {obj['progress']*100:.1f}%")
                print(f"    Goal: {obj['goal']}")
                print(f"    Status: {obj['status']}")
                print("-" * 60)
        return

    if not args.goal:
        print("✗ Error: Goal text is required.")
        return

    goal_id = service.add_objective(args.goal, priority=args.priority)
    print(f"\n🚀 Sovereign Goal Registered Successfully!")
    print(f"Goal ID: {goal_id}")
    print(f"Goal: {args.goal}")
    print(f"Priority: {args.priority}")
    print("\nThe Sovereign Goal Daemon will pick this up for orchestration shortly.")

if __name__ == "__main__":
    main()
