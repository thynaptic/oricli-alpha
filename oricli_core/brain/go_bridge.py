"""
Go Bridge Utility for Oricli-Alpha Python Modules

This provides a compatibility layer for remaining Python modules to interact
with the Go-native backbone, replacing the deleted legacy Python services.
"""

import os
import json
import httpx
import logging
import time
from typing import Any, Dict, List, Optional, Union
from dataclasses import dataclass, field

logger = logging.getLogger(__name__)

# --- Compatibility Stubs for Legacy Imports ---

@dataclass
class SwarmMessage:
    topic: str
    payload: Dict[str, Any]
    protocol: str = "cfp"
    sender_id: str = "python_bridge"
    id: str = ""
    timestamp: float = field(default_factory=time.time)

    def to_dict(self):
        return {
            "topic": self.topic,
            "payload": self.payload,
            "protocol": self.protocol,
            "sender_id": self.sender_id,
            "id": self.id,
            "timestamp": self.timestamp
        }

@dataclass
class AgentProfile:
    name: str
    description: str = ""
    allowed_modules: List[str] = field(default_factory=list)
    allowed_operations: Dict[str, List[str]] = field(default_factory=dict)
    system_instructions: str = ""
    model_preference: str = ""
    skill_overlays: List[str] = field(default_factory=list)

class MessageProtocol:
    CFP = "cfp"
    BID = "bid"
    ACCEPT = "accept"
    REJECT = "reject"
    RESULT = "result"
    ERROR = "error"

class MemoryCategory:
    SEMANTIC = "semantic"
    EPISODIC = "episodic"
    IDENTITY = "identity"
    SKILL = "skill"
    LONG_TERM_STATE = "long_term_state"
    REFLECTION_LOG = "reflection_log"
    VECTOR_INDEX = "vector_index"

class MemoryBridgeError(Exception):
    """Base error for memory bridge"""
    pass

class ToolRegistryError(Exception):
    """Base error for tool registry"""
    pass

class GoalServiceError(Exception):
    """Base error for goal service"""
    pass

class ToolRegistry:
    """Mock for legacy tool registry calls"""
    def __init__(self):
        self._go = get_go_service()
    def get_tool(self, name):
        return self._go.execute("get_tool", {"name": name})
    def list_tools(self):
        return self._go.execute("list_tools", {})

class Neo4jService:
    """Mock for legacy neo4j service calls"""
    def execute_query(self, query, params=None):
        return get_go_service().execute("graph_query", {"query": query, "params": params or {}})

class GoalService:
    """Mock for legacy goal service calls"""
    def add_objective(self, goal, priority=1, metadata=None):
        res = get_go_service().execute("add_goal", {"goal": goal, "priority": priority, "metadata": metadata or {}})
        return res.get("id")
    def list_objectives(self, status=None):
        res = get_go_service().execute("list_goals", {"status": status})
        return res.get("goals", [])
    def load_plan_state(self, goal_id):
        res = get_go_service().execute("get_goal_status", {"goal_id": goal_id})
        return res.get("plan_state", {})

class AgentProfileService:
    """Mock for legacy agent profile service calls"""
    def list_profiles(self):
        res = get_go_service().execute("list_profiles", {})
        return res.get("profiles", [])
    def get_profile(self, name):
        res = get_go_service().execute("get_profile", {"name": name})
        return res

class SwarmBus:
    """Mock for legacy swarm bus calls"""
    def publish(self, topic, payload, protocol="cfp"):
        get_swarm_bus().publish(topic, payload, protocol)
    def subscribe(self, topic, callback):
        # Subscription from Python to Go bus via HTTP is not supported in this stub
        logger.warning(f"Python subscription to Go Swarm Bus topic '{topic}' is not supported via bridge.")

class MemoryBridgeService:
    """Mock for legacy memory service calls"""
    def execute(self, op, params):
        return get_go_service().execute(op, params)

@dataclass
class MemoryBridgeConfig:
    db_path: str
    encryption_key: str
    map_size: int = 512 * 1024 * 1024

class ToolExecutionService:
    """Mock for legacy tool service calls"""
    async def execute_tool(self, name, args):
        return get_go_service().execute(name, args)

# --- Real Logic ---

class GoSwarmBusProxy:
    """Proxy for the Go-native Swarm Bus via HTTP API"""
    def __init__(self, addr: str = "http://localhost:8089"):
        self.addr = addr

    def publish(self, topic: str, payload: Dict[str, Any], protocol: str = "cfp"):
        """Publish a message to the Go Swarm Bus"""
        try:
            with httpx.Client(timeout=10.0) as client:
                client.post(f"{self.addr}/v1/swarm/inject", json={
                    "topic": topic,
                    "payload": payload,
                    "protocol": protocol
                })
        except Exception as e:
            logger.warning(f"Failed to publish to Go Swarm Bus: {e}")

class GoServiceProxy:
    """Generic proxy for Go-native services"""
    def __init__(self, addr: str = "http://localhost:8089"):
        self.addr = addr

    def execute(self, operation: str, params: Dict[str, Any]) -> Dict[str, Any]:
        """Execute an operation on the Go Backbone"""
        try:
            with httpx.Client(timeout=60.0) as client:
                # Map operation names if needed
                resp = client.post(f"{self.addr}/v1/swarm/run", json={
                    "query": f"internal_op:{operation}",
                    "params": params
                })
                if resp.status_code == 200:
                    return resp.json()
                return {"success": False, "error": f"Go returned {resp.status_code}"}
        except Exception as e:
            return {"success": False, "error": str(e)}

class ModuleRegistry:
    """Mock for legacy module registry calls"""
    def list_modules(self):
        res = get_go_service().execute("list_modules", {})
        return res.get("modules", [])
    def get_metadata(self, name):
        res = get_go_service().execute("get_metadata", {"name": name})
        return res

class ModuleMonitorService:
    """Mock for legacy monitor service calls"""
    def get_module_status(self, name):
        res = get_go_service().execute("get_module_status", {"name": name})
        return res
    def get_all_statuses(self):
        res = get_go_service().execute("get_all_statuses", {})
        return res.get("statuses", {})

class ModuleRecoveryService:
    """Mock for legacy recovery service calls"""
    def recover_module(self, name):
        res = get_go_service().execute("recover_module", {"name": name})
        return res

class ModuleAvailabilityManager:
    """Mock for legacy availability manager calls"""
    def get_module_or_fallback(self, name, operation=None):
        res = get_go_service().execute("get_module_or_fallback", {"name": name, "operation": operation})
        # Note: This might need to return a complex tuple to match Python's expectations
        return res.get("module"), res.get("actual_name"), res.get("is_fallback"), res.get("mapped_operation")

class DegradedModeClassifier:
    """Mock for legacy degraded classifier calls"""
    def get_fallback_module(self, name, operation=None):
        res = get_go_service().execute("get_fallback_module", {"name": name, "operation": operation})
        return res.get("fallback")

class MetricsCollector:
    """Mock for legacy metrics collector calls"""
    def get_all_metrics(self):
        res = get_go_service().execute("get_all_metrics", {})
        return res

class TraceStore:
    """Mock for legacy trace store calls"""
    def list_recent(self, limit=20):
        res = get_go_service().execute("list_recent_traces", {"limit": limit})
        return res

# --- Singleton Instances ---

class BudgetManager:
    """Mock for legacy budget manager calls"""
    def get_balance(self):
        res = get_go_service().execute("get_budget_balance", {})
        return res.get("balance", 0.0)
    def deduct(self, amount, reason="compute"):
        res = get_go_service().execute("deduct_budget", {"amount": amount, "reason": reason})
        return res.get("success", False)
    def add(self, amount, reason="deposit"):
        get_go_service().execute("add_budget", {"amount": amount, "reason": reason})

class InsightService:
    """Mock for legacy insight service calls"""
    def record_insight(self, connection, source_a, source_b, score, metadata=None):
        res = get_go_service().execute("record_insight", {
            "connection": connection, "source_a": source_a, "source_b": source_b,
            "score": score, "metadata": metadata or {}
        })
        return res.get("id")
    def list_untrained_insights(self, min_score=0.7):
        res = get_go_service().execute("list_untrained_insights", {"min_score": min_score})
        return res.get("insights", [])
    def mark_as_trained(self, insight_ids):
        get_go_service().execute("mark_insights_trained", {"ids": insight_ids})

class PreCogService:
    """Mock for legacy precog service calls"""
    def cache_speculative_response(self, query, response):
        get_go_service().execute("cache_precog", {"query": query, "response": response})
    def get_cached_response(self, query):
        res = get_go_service().execute("get_precog", {"query": query})
        return res.get("response")
    def clear(self):
        get_go_service().execute("clear_precog", {})

class AbsorptionService:
    """Mock for legacy absorption service calls"""
    def record_lesson(self, prompt, response, metadata=None):
        res = get_go_service().execute("record_lesson", {"prompt": prompt, "response": response, "metadata": metadata or {}})
        return res.get("success", False)
    def get_buffer_count(self):
        res = get_go_service().execute("get_absorption_count", {})
        return res.get("count", 0)
    def clear_buffer(self):
        get_go_service().execute("clear_absorption", {})

class MultiAgentPipeline:
    """Mock for legacy multi-agent pipeline calls"""
    def process_query(self, query, config=None):
        res = get_go_service().execute("execute_multi_agent_pipeline", {"query": query, "config": config or {}})
        return res
    def execute_pipeline(self, query, config=None):
        return self.process_query(query, config)

class CognitiveReasoningOrchestrator:
    """Mock for legacy cognitive reasoning orchestrator calls"""
    def execute_cognitive_reasoning(self, params):
        query = params.get("query", "")
        context = params.get("context", {})
        res = get_go_service().execute("execute_reasoning_flow", {"query": query, "context": context})
        return {"success": True, "result": res}
    def orchestrate_reasoning(self, params):
        return self.execute_cognitive_reasoning(params)

class ConversationalOrchestrator:
    """Mock for legacy conversational orchestrator calls"""
    def generate_conversational_response(self, params):
        input_text = params.get("input", "")
        context = params.get("context", "")
        persona = params.get("persona", "oricli")
        res = get_go_service().execute("execute_conversational_flow", {"input": input_text, "context": context, "persona": persona})
        return res

class WorldKnowledge:
    """Mock for legacy world knowledge calls"""
    def query_knowledge(self, query, query_type="semantic", limit=10):
        res = get_go_service().execute("query_world_knowledge", {"query": query, "limit": limit})
        return res
    def add_knowledge(self, fact, entities=None, relationships=None, confidence=1.0):
        res = get_go_service().execute("add_world_knowledge", {
            "fact": fact, "entities": entities or [], 
            "relationships": relationships or {}, "confidence": confidence
        })
        return res
    def validate_fact(self, fact, context=""):
        res = get_go_service().execute("validate_world_fact", {"fact": fact, "context": context})
        return res
    def semantic_search(self, query, limit=10, threshold=0.7):
        res = get_go_service().execute("world_semantic_search", {"query": query, "limit": limit, "threshold": threshold})
        return res

class PythonCodeReview:
    """Mock for legacy python code review calls"""
    def review_code(self, code, review_type="comprehensive"):
        res = get_go_service().execute("execute_code_review", {"code": code, "review_type": review_type})
        return res
    def score_code_quality(self, code):
        res = get_go_service().execute("score_code_quality", {"code": code})
        return res

class PythonProjectUnderstanding:
    """Mock for legacy python project understanding calls"""
    def understand_project(self, project):
        res = get_go_service().execute("understand_project", {"project": project})
        return res
    def analyze_cross_file_dependencies(self, project):
        res = get_go_service().execute("analyze_project_dependencies", {"project": project})
        return res

class PythonCodeMetrics:
    """Mock for legacy python code metrics calls"""
    def calculate_metrics(self, code):
        res = get_go_service().execute("calculate_code_metrics", {"code": code})
        return res
    def analyze_complexity(self, code):
        res = get_go_service().execute("analyze_code_complexity", {"code": code})
        return res

class PythonSecurityAnalysis:
    """Mock for legacy python security analysis calls"""
    def analyze_security(self, code):
        res = get_go_service().execute("execute_security_analysis", {"code": code})
        return res
    def detect_vulnerabilities(self, code):
        res = get_go_service().execute("detect_vulnerabilities", {"code": code})
        return res

class PythonDocumentationGenerator:
    """Mock for legacy python documentation generator calls"""
    def generate_docstring(self, code, style="google"):
        res = get_go_service().execute("generate_docstring", {"code": code, "style": style})
        return res
    def generate_readme(self, project):
        res = get_go_service().execute("generate_readme", {"project": project})
        return res
    def explain_code_natural_language(self, code, audience="developer"):
        res = get_go_service().execute("explain_code", {"code": code, "audience": audience})
        return res

class PythonSemanticUnderstanding:
    """Mock for legacy python semantic understanding calls"""
    def analyze_semantics(self, code):
        res = get_go_service().execute("analyze_code_semantics", {"code": code})
        return res
    def analyze_code(self, code):
        return self.analyze_semantics(code)

class ThoughtToText:
    """Mock for legacy thought to text calls"""
    def convert_thought_graph(self, mcts_nodes, voice_context=None, context=""):
        res = get_go_service().execute("convert_thought_graph", {"mcts_nodes": mcts_nodes, "context": context})
        return res
    def convert_reasoning_tree(self, tree_json, voice_context=None, context=""):
        res = get_go_service().execute("convert_reasoning_tree", {"tree": tree_json, "context": context})
        return res

class EmotionalInference:
    """Mock for legacy emotional inference calls"""
    def score_emotional_intent(self, text, context=""):
        res = get_go_service().execute("score_emotional_intent", {"text": text, "context": context})
        return res
    def calculate_warmth_level(self, emotion_score):
        res = get_go_service().execute("calculate_warmth_level", {"score": emotion_score})
        return res
    def tune_empathy(self, text, emotion_score):
        res = get_go_service().execute("tune_empathy", {"text": text, "score": emotion_score})
        return res
    def modulate_response_warmth(self, response, emotion_score):
        res = get_go_service().execute("modulate_response_warmth", {"response": response, "score": emotion_score})
        return res

class PythonRefactoringReasoning:
    """Mock for legacy python refactoring reasoning calls"""
    def suggest_refactorings(self, code, refactoring_type="all"):
        res = get_go_service().execute("suggest_refactorings", {"code": code, "refactoring_type": refactoring_type})
        return res
    def verify_refactoring(self, original, refactored):
        res = get_go_service().execute("verify_refactoring", {"original": original, "refactored": refactored})
        return res

class PythonCodebaseSearch:
    """Mock for legacy python codebase search calls"""
    def search_codebase(self, project, query, search_type="semantic"):
        res = get_go_service().execute("search_codebase", {"project": project, "query": query, "search_type": search_type})
        return res
    def find_usages(self, project, symbol):
        res = get_go_service().execute("search_codebase", {"project": project, "query": symbol, "search_type": "text"})
        return res

class PythonCodeExplanation:
    """Mock for legacy python code explanation calls"""
    def explain_code(self, code, audience="developer", detail_level="medium"):
        res = get_go_service().execute("explain_code", {"code": code, "audience": audience, "detail_level": detail_level})
        return res
    def answer_code_question(self, code, question):
        res = get_go_service().execute("answer_code_question", {"code": code, "question": question})
        return res

class PythonMigrationAssistant:
    """Mock for legacy python migration assistant calls"""
    def plan_migration(self, code, target_version="3.11"):
        res = get_go_service().execute("plan_migration", {"code": code, "target_version": target_version})
        return res
    def migrate_python_version(self, code, from_version="2.7", to_version="3.11"):
        res = get_go_service().execute("migrate_python_version", {"code": code, "from_version": from_version, "to_version": to_version})
        return res
    def migrate_library(self, code, old_lib, new_lib):
        res = get_go_service().execute("migrate_library", {"code": code, "old_lib": old_lib, "new_lib": new_lib})
        return res

class PythonStyleAdaptation:
    """Mock for legacy python style adaptation calls"""
    def detect_style(self, codebase):
        res = get_go_service().execute("detect_code_style", {"codebase": codebase})
        return res
    def adapt_to_style(self, code, target_style):
        res = get_go_service().execute("adapt_to_style", {"code": code, "target_style": target_style})
        return res

class PythonLearningSystem:
    """Mock for legacy python learning system calls"""
    def learn_from_correction(self, original, corrected, context=None):
        res = get_go_service().execute("learn_from_correction", {"original": original, "corrected": corrected, "context": context or {}})
        return res
    def personalize_generation(self, user_preferences):
        res = get_go_service().execute("personalize_generation", {"preferences": user_preferences})
        return res

class PythonCodeMemory:
    """Mock for legacy python code memory calls"""
    def remember_code_pattern(self, pattern, context=None):
        res = get_go_service().execute("remember_code_pattern", {"pattern": pattern, "context": context or {}})
        return res
    def recall_similar_patterns(self, code, top_k=5):
        res = get_go_service().execute("recall_similar_patterns", {"code": code, "limit": top_k})
        return res
    def get_code_idioms(self, language_feature):
        res = get_go_service().execute("get_code_idioms", {"language_feature": language_feature})
        return res

class PythonCodeEmbeddings:
    """Mock for legacy python code embeddings calls"""
    def embed_code(self, code):
        res = get_go_service().execute("embed_code", {"code": code})
        return res
    def similar_code(self, query_code, codebase, top_k=5):
        res = get_go_service().execute("similar_code", {"query_code": query_code, "codebase": codebase, "limit": top_k})
        return res

_BUS = None
_GO = None
tool_execution_service = ToolExecutionService()

def get_swarm_bus():
    global _BUS
    if _BUS is None:
        _BUS = GoSwarmBusProxy(os.environ.get("ORICLI_GO_ADDR", "http://localhost:8089"))
    return _BUS

def get_go_service():
    global _GO
    if _GO is None:
        _GO = GoServiceProxy(os.environ.get("ORICLI_GO_ADDR", "http://localhost:8089"))
    return _GO

# Aliases
def get_neo4j_service(): return Neo4jService()
def get_memory_bridge_service(): return MemoryBridgeService()
def get_agent_profile_service(): return AgentProfileService()
def get_tool_registry(): return ToolRegistry()
def get_cognitive_generator(): return get_go_service()
def get_neural_text_generator(): return get_go_service()
def get_custom_reasoning_networks(): return get_go_service()

def get_availability_manager(): return ModuleAvailabilityManager()
def get_monitor_service(): return ModuleMonitorService()
def get_recovery_service(): return ModuleRecoveryService()
def get_degraded_classifier(): return DegradedModeClassifier()
def get_metrics_collector(): return MetricsCollector()
def get_trace_store(): return TraceStore()
def get_module_registry(): return ModuleRegistry()
