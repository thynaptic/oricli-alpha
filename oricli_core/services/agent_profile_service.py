"""
Agent Profile Service Shim - Reroutes to Go Bridge
"""
from oricli_core.brain.go_bridge import AgentProfileService, AgentProfile

def get_agent_profile_service():
    return AgentProfileService()
