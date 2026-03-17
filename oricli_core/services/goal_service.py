"""
Goal Service Shim - Reroutes to Go Bridge
"""
from oricli_core.brain.go_bridge import GoalService, GoalServiceError

def get_goal_service():
    return GoalService()
