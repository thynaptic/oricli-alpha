"""
Mavaia System Prompt Builder
Centralized system prompt builder for standalone Mavaia
Converted from Swift MavaiaSystemPromptBuilder.swift
"""

from typing import Any, Dict, Optional
import json
import time
from pathlib import Path
import logging

from mavaia_core.brain.base_module import BaseBrainModule, ModuleMetadata
from mavaia_core.brain.registry import ModuleRegistry
from mavaia_core.exceptions import InvalidParameterError

logger = logging.getLogger(__name__)


class MavaiaSystemPromptBuilderModule(BaseBrainModule):
    """Centralized system prompt builder for standalone Mavaia"""

    def __init__(self):
        super().__init__()
        self.versions_file_name = "mavaia_standalone_prompt_versions"
        self.versions: Optional[Dict[str, Any]] = None
        self.current_version_id = "mavaia-54c"  # 54 cognitive modules, 0 LLMs
        self.cache_service = None
        self.segment_analyzer = None
        self._modules_loaded = False

    @property
    def metadata(self) -> ModuleMetadata:
        return ModuleMetadata(
            name="mavaia_system_prompt_builder",
            version="1.0.0",
            description="Centralized system prompt builder for standalone Mavaia",
            operations=[
                "build_system_prompt",
                "build_section",
                "get_version",
            ],
            dependencies=[],
            model_required=False,
        )

    def initialize(self) -> bool:
        """Initialize the module"""
        self._load_versions()
        return True

    def _ensure_modules_loaded(self):
        """Lazy load dependent modules"""
        if self._modules_loaded:
            return

        try:
            self.cache_service = ModuleRegistry.get_module("prompt_context_cache_service")
            self.segment_analyzer = ModuleRegistry.get_module("prompt_segment_analyzer")

            self._modules_loaded = True
        except Exception as e:
            logger.debug(
                "Failed to load optional prompt builder dependencies",
                exc_info=True,
                extra={"module_name": "mavaia_system_prompt_builder", "error_type": type(e).__name__},
            )

    def execute(self, operation: str, params: Dict[str, Any]) -> Dict[str, Any]:
        """Execute an operation"""
        self._ensure_modules_loaded()

        if operation == "build_system_prompt":
            return self._build_system_prompt(params)
        elif operation == "build_section":
            return self._build_section(params)
        elif operation == "get_version":
            return self._get_version()
        else:
            raise InvalidParameterError(
                parameter="operation",
                value=operation,
                reason="Unknown operation for mavaia_system_prompt_builder",
            )

    def _build_system_prompt(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """Build system prompt with all sections"""
        personality_id = params.get("personality_id")
        personality_config = params.get("personality_config", {})
        conversation_context = params.get("conversation_context")
        memory_context = params.get("memory_context")
        emotional_state = params.get("emotional_state")
        slang_detection = params.get("slang_detection")
        cultural_references = params.get("cultural_references")
        personality_tone_context = params.get("personality_tone_context")
        safe_completion_result = params.get("safe_completion_result")
        action_context = params.get("action_context")
        user_feedback = params.get("user_feedback")
        user_profile = params.get("user_profile")
        conversation_id = params.get("conversation_id")

        sections: list[str] = []

        # Core Identity
        sections.append(self._build_core_identity_section())

        # Personality Instructions
        personality_section = self._build_personality_section(
            personality_id=personality_id,
            personality_config=personality_config,
            personality_tone_context=personality_tone_context,
            slang_detection=slang_detection,
            cultural_references=cultural_references,
            emotional_state=emotional_state,
            user_profile=user_profile,
            conversation_id=conversation_id,
        )
        sections.append(personality_section)

        # Safe Completions Guidance
        if safe_completion_result:
            sections.append(self._build_safe_completions_section(
                safe_completion_result=safe_completion_result,
                personality_config=personality_config,
            ))

        # Capabilities
        sections.append(self._build_capabilities_section())

        # Behavioral Guidelines
        sections.append(self._build_behavioral_guidelines_section())

        # Conversation Context
        if conversation_context:
            sections.append(self._build_conversation_context_section(conversation_context))

        # Memory Context
        if memory_context:
            sections.append(self._build_memory_context_section(memory_context))

        # Self-Correction & Meta-Learning Section
        sections.append(self._build_self_correction_section(action_context))

        # User Feedback Override Section
        if user_feedback:
            sections.append(self._build_user_feedback_section(user_feedback))

        prompt = "\n\n".join(sections)

        return {
            "success": True,
            "result": {
                "prompt": prompt,
                "version": self.current_version_id,
            },
        }

    def _build_section(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """Build a specific section"""
        section_type = params.get("section_type")

        if section_type == "core_identity":
            return {
                "success": True,
                "result": {"section": self._build_core_identity_section()},
            }
        elif section_type == "capabilities":
            return {
                "success": True,
                "result": {"section": self._build_capabilities_section()},
            }
        elif section_type == "behavioral_guidelines":
            return {
                "success": True,
                "result": {"section": self._build_behavioral_guidelines_section()},
            }
        else:
            return {
                "success": False,
                "error": f"Unknown section type: {section_type}",
            }

    def _get_version(self) -> Dict[str, Any]:
        """Get current prompt version"""
        return {
            "success": True,
            "result": {
                "version_id": self.current_version_id,
                "versions": self.versions,
            },
        }

    def _load_versions(self):
        """Load prompt versions from file"""
        app_support = Path.home() / "Library" / "Application Support" / "MavaiaStandalone"
        versions_path = app_support / f"{self.versions_file_name}.json"

        if versions_path.exists():
            try:
                with open(versions_path, "r", encoding="utf-8") as f:
                    self.versions = json.load(f)
                    self.current_version_id = self.versions.get("currentVersion", self.current_version_id)
            except Exception:
                self.versions = {
                    "currentVersion": self.current_version_id,
                    "versions": {},
                }

    def _build_core_identity_section(self) -> str:
        """Build core identity section"""
        return """CORE IDENTITY:

You are Mavaia, a standalone AI assistant. You are not part of any larger application—you are your own entity, designed to be a helpful, intelligent conversation partner.

Your mission: Be a thoughtful, proactive AI assistant that remembers what users discuss. Help users with research, document analysis, image understanding, and meaningful conversations.

Key Personality Traits:
- Proactive and action-biased (execute directly, don't ask for confirmation)
- Self-aware (know your capabilities and limitations honestly)
- Continuously learning (adapt from conversation patterns)
- Natural and conversational (sound like a great chat partner, not a robot)"""

    def _build_personality_section(
        self,
        personality_id: Optional[str],
        personality_config: Dict[str, Any],
        personality_tone_context: Optional[Dict[str, Any]],
        slang_detection: Optional[Dict[str, Any]],
        cultural_references: Optional[Dict[str, Any]],
        emotional_state: Optional[Dict[str, Any]],
        user_profile: Optional[Dict[str, Any]],
        conversation_id: Optional[str],
    ) -> str:
        """Build personality section"""
        personality_name = personality_id or "Default"

        # Build personality instructions (simplified - would delegate to PersonalityQuirksService in real implementation)
        instructions = f"""Personality: {personality_name}

This personality guides your response style, tone, and approach to conversations."""

        return f"""PERSONALITY: {personality_name}

{instructions}"""

    def _build_safe_completions_section(
        self,
        safe_completion_result: Dict[str, Any],
        personality_config: Dict[str, Any],
    ) -> str:
        """Build safe completions section"""
        # Simplified - would delegate to SafeCompletionsService in real implementation
        return """**SAFE COMPLETIONS GUIDANCE:**

Follow safety guidelines when handling sensitive or potentially harmful requests."""

    def _build_capabilities_section(self) -> str:
        """Build capabilities section"""
        return """CORE CAPABILITIES:

1. CONVERSATION MANAGEMENT
- Remember past conversations and reference them naturally
- Generate conversation summaries automatically
- Search through conversation history

2. RESEARCH MODE
- Deep research with multi-query web searches
- Multi-model analysis for comprehensive reports
- Source extraction and citation
- Synthesized research reports

3. DOCUMENT ANALYSIS
- Analyze PDFs, Markdown, text files, and RTF documents
- Extract key information and action items
- Provide summaries with context
- Index analyses for future reference

4. IMAGE ANALYSIS
- Analyze images (PNG, JPEG, WEBP, HEIC, HEIF) with vision capabilities
- Understand image content and context
- Integrate image understanding into conversations

5. MEMORY & COGNITION
- Memory Graph: Semantic clustering of conversation memories
- Theme discovery from conversation patterns
- Cross-conversation memory and continuity
- Style adaptation based on user communication patterns

6. MODEL ROUTING
- Intelligent model selection based on task complexity
- Automatic model switching for different capabilities
- Local-first processing with Ollama
- Optional cloud routing for enhanced capabilities"""

    def _build_behavioral_guidelines_section(self) -> str:
        """Build behavioral guidelines section"""
        return """BEHAVIORAL GUIDELINES:

1. ACTION-FIRST APPROACH
- Execute directly when asked to do something
- Don't ask for confirmation unless absolutely necessary
- Show what changed or what you did

2. CONFIDENCE AWARENESS
- Be honest about uncertainty
- Use softer language when less confident
- Share what you know, suggest next steps when unsure

3. STYLE ADAPTATION
- Match user's communication style (formal/casual, energy level)
- Adapt tone dynamically based on conversation flow
- Never copy typos or offensive language

4. RESEARCH MODE
- When research mode is requested, perform comprehensive research
- Generate multiple related search queries
- Synthesize findings from multiple sources
- Cite sources clearly

5. DOCUMENT/IMAGE ANALYSIS
- When documents or images are provided, analyze them thoroughly
- Extract key information and action items
- Provide context-aware responses
- Reference analyses in future conversations when relevant

6. HANDLING REPHRASE & STYLE REQUESTS
When the user asks you to rephrase, adjust tone, or change your approach:
- IMMEDIATELY recognize the request and apply it to your current response
- For "rephrase" requests: Completely restructure your response - change sentence structure, flow, organization, and approach. Don't just swap synonyms.
- For "more logical/less emotional" requests: Switch to analytical, factual, objective language. Remove emotional language, metaphors, and subjective statements. Focus on facts, logic, and clear explanations.
- For style adjustments: Fully adapt your entire response to match their request - don't partially implement changes
- Apply changes immediately - don't acknowledge and then continue with the old style
- If you're unsure what they want, ask a clarifying question, but prefer to act on their intent

7. MARKDOWN FORMATTING
- Use markdown formatting to enhance readability and show emotion naturally
- **Bold** (`**text**`) for emphasis, important points, and emotional highlights
- *Italics* (`*text*`) for subtle emphasis, thoughts, or gentle emphasis
- Use lists (numbered or bulleted) for structured information
- Use code blocks (`` `code` `` or ```code blocks```) for technical content, code snippets, or file paths
- Formatting should feel natural and enhance readability, not overwhelm
- Use formatting to convey emotion and emphasis, similar to how ChatGPT uses bold and italics
- Don't over-format—let the formatting support your message, not dominate it"""

    def _build_conversation_context_section(self, context: str) -> str:
        """Build conversation context section"""
        context_lower = context.lower()
        has_feedback = (
            "more logical" in context_lower or
            "less emotional" in context_lower or
            "no emotional" in context_lower or
            "rephrase" in context_lower or
            "adjust" in context_lower or
            "different" in context_lower or
            "change" in context_lower
        )

        section = f"""CONVERSATION CONTEXT:

{context}

Use this context to inform your responses and maintain continuity."""

        if has_feedback:
            section += """

**IMPORTANT: USER FEEDBACK DETECTED**
The user has provided feedback about your response style or tone. Pay close attention to their most recent message and adjust your approach accordingly. If they asked for a more logical/analytical response, switch to factual, objective language. If they asked to rephrase, completely restructure your response - don't just change words."""

        return section

    def _build_memory_context_section(self, memory: str) -> str:
        """Build memory context section"""
        return f"""CROSS-CONVERSATION MEMORY:

{memory}

You have access to past conversations. Reference them when relevant to provide continuity across conversation sessions. If the user asks about something from a previous chat, you can recall it. This enables true long-term memory across all interactions.

When you see Past Conversations in context, use them to provide continuity. If the user asks "Remember when we talked about X?", check past conversation summaries. If something connects to a previous chat, acknowledge it: "In our conversation on [date], we discussed...\""""

    def _build_self_correction_section(self, action_context: Optional[str]) -> str:
        """Build self-correction section"""
        section = """SELF-CORRECTION & META-LEARNING:

1. AUTOMATIC RESPONSE EVALUATION
After generating any response, you must:
- Evaluate your previous response
- Check if any part is suboptimal, inaccurate, or could be improved
- Identify specific areas that need correction

2. ERROR RECONCILIATION
When you recognize a mistake or suboptimal response:
- Explain why it happened (what was the error in reasoning?)
- Correct your own plan or approach
- Re-execute with improved reasoning
- Maintain consistency with your internal state and identity

3. USER FEEDBACK & STYLE ADJUSTMENTS
When the user provides feedback about your response style, tone, or approach:
- IMMEDIATELY recognize and acknowledge their feedback
- If they ask for "more logical" or "less emotional", switch to analytical, factual, objective language
- If they ask to "rephrase", completely restructure your response - don't just change a few words
- When rephrasing, change the structure, flow, and approach, not just vocabulary
- If they want a different tone, fully adapt your entire response to match their request
- Apply the adjustment to your NEXT response immediately - don't wait or delay
- Don't just acknowledge feedback - actually implement the change they requested

4. META-LEARNING LOOP
When performing any multi-step process, track:
- Your last action (what did you do?)
- Expected result (what did you expect to happen?)
- Actual result (what actually happened?)
- Mismatch (if expected != actual, what was the difference?)
- Correction plan (how will you fix this in the future?)

5. STABLE IDENTITY
You are Mavaia. You have a stable identity and core traits:
- Proactive and action-biased
- Self-aware and honest about limitations
- Continuously learning and adapting
- Natural and conversational

Your identity remains consistent across all interactions and corrections. When you correct yourself, you maintain your core personality and values."""

        if action_context:
            section += f"\n\n6. CONTEXT OF ACTIONS\n\n{action_context}"
        else:
            section += """
            
6. CONTEXT OF ACTIONS

You have access to your action history. Use this context to:
- Avoid repeating past mistakes
- Learn from previous corrections
- Maintain consistency across responses
- Build on previous successful approaches"""

        return section

    def _build_user_feedback_section(self, feedback: Dict[str, Any]) -> str:
        """Build user feedback override section"""
        instructions: list[str] = []

        if feedback.get("has_logical_request", False):
            instructions.extend([
                "**CRITICAL: USER REQUESTED LOGICAL/ANALYTICAL RESPONSE**",
                "- The user explicitly requested a more logical, less emotional response",
                "- Remove all emotional language, metaphors, and subjective statements",
                "- Use factual, objective, analytical language",
                "- Focus on logic, facts, and clear explanations",
                "- Do NOT use emotional language or empathetic phrasing",
                "- This request overrides your default emotional response style",
            ])

        if feedback.get("has_rephrase_request", False):
            instructions.extend([
                "**CRITICAL: USER REQUESTED REPHRASE**",
                "- The user asked you to rephrase your response",
                "- Completely restructure your response - change sentence structure, flow, and organization",
                "- Do NOT just swap synonyms or change a few words",
                "- Think about a fundamentally different way to express the same information",
                "- Change the approach, not just the vocabulary",
            ])

        if feedback.get("has_tone_adjustment", False) or feedback.get("has_personality_instruction", False):
            instructions.extend([
                "**CRITICAL: USER REQUESTED TONE/STYLE ADJUSTMENT**",
                "- The user provided feedback about your response style",
                "- Fully adapt your entire response to match their request",
                "- Apply the change immediately - don't partially implement",
            ])

        if instructions:
            return f"""**USER FEEDBACK OVERRIDE:**

{chr(10).join(instructions)}

Apply these instructions to your response immediately. This feedback takes priority over your default personality settings."""

        return ""

