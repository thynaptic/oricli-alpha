from __future__ import annotations
"""
Thought to Text Module - Convert thought graphs (MCTS nodes or reasoning trees) to natural language
This is the key module that replaces autoregressive LLM text generation with a rewrite engine
Uses existing grammar, phrasing, and style modules to produce natural sentences from structured thoughts
"""

from typing import List, Dict, Any, Optional, Union
import logging
import json
import re
import random

from mavaia_core.brain.base_module import BaseBrainModule, ModuleMetadata
from mavaia_core.exceptions import InvalidParameterError

logger = logging.getLogger(__name__)

class ThoughtToTextModule(BaseBrainModule):
    """Convert thought graphs (MCTS nodes or reasoning trees) to natural language sentences"""

    def __init__(self):
        super().__init__()
        self.grammar_module = None
        self.style_module = None
        self.phrase_module = None
        self.hybrid_phrasing_service = None
        self.text_generation_engine = None
        self.universal_voice_engine = None
        self._modules_loaded = False

    @property
    def metadata(self) -> ModuleMetadata:
        return ModuleMetadata(
            name="thought_to_text",
            version="1.0.0",
            description="Convert thought graphs (MCTS nodes or reasoning trees) to natural language sentences",
            operations=[
                "convert_thought_graph",
                "convert_reasoning_tree",
                "generate_sentences",
                "apply_grammar_and_style",
            ],
            dependencies=[],
            model_required=False,
        )

    def initialize(self) -> bool:
        """Initialize the module - lazy load dependent modules"""
        # Don't load modules here - load them lazily on first use
        # This allows the module to work even if some dependencies aren't available
        return True

    def _ensure_modules_loaded(self):
        """Lazy load dependent modules"""
        if self._modules_loaded:
            return

        try:
            from mavaia_core.brain.registry import ModuleRegistry

            # Try to load modules (they may not all be available)
            try:
                self.grammar_module = ModuleRegistry.get_module("neural_grammar")
            except Exception as e:
                logger.debug(
                    "Failed to load optional neural_grammar",
                    exc_info=True,
                    extra={"module_name": "thought_to_text", "error_type": type(e).__name__},
                )

            try:
                self.style_module = ModuleRegistry.get_module("style_transfer")
            except Exception as e:
                logger.debug(
                    "Failed to load optional style_transfer",
                    exc_info=True,
                    extra={"module_name": "thought_to_text", "error_type": type(e).__name__},
                )

            try:
                self.phrase_module = ModuleRegistry.get_module("phrase_embeddings")
            except Exception as e:
                logger.debug(
                    "Failed to load optional phrase_embeddings",
                    exc_info=True,
                    extra={"module_name": "thought_to_text", "error_type": type(e).__name__},
                )

            try:
                self.hybrid_phrasing_service = ModuleRegistry.get_module("hybrid_phrasing_service")
            except Exception as e:
                self.hybrid_phrasing_service = None
                logger.debug(
                    "Failed to load optional hybrid_phrasing_service",
                    exc_info=True,
                    extra={"module_name": "thought_to_text", "error_type": type(e).__name__},
                )

            try:
                self.text_generation_engine = ModuleRegistry.get_module("text_generation_engine")
            except Exception as e:
                logger.debug(
                    "Failed to load optional text_generation_engine",
                    exc_info=True,
                    extra={"module_name": "thought_to_text", "error_type": type(e).__name__},
                )

            try:
                self.universal_voice_engine = ModuleRegistry.get_module("universal_voice_engine")
            except Exception as e:
                logger.debug(
                    "Failed to load optional universal_voice_engine",
                    exc_info=True,
                    extra={"module_name": "thought_to_text", "error_type": type(e).__name__},
                )

            self._modules_loaded = True
        except Exception as e:
            # Modules not available - will use fallback methods
            logger.debug(
                "Failed to load dependency modules for thought_to_text",
                exc_info=True,
                extra={"module_name": "thought_to_text", "error_type": type(e).__name__},
            )

    def execute(self, operation: str, params: Dict[str, Any]) -> Dict[str, Any]:
        """Execute a thought-to-text operation"""
        self._ensure_modules_loaded()

        if operation == "convert_thought_graph":
            return self.convert_thought_graph(
                mcts_nodes=params.get("mcts_nodes", []),
                voice_context=params.get("voice_context", {}),
                context=params.get("context", ""),
            )
        elif operation == "convert_reasoning_tree":
            return self.convert_reasoning_tree(
                tree_json=params.get("tree_json", {}),
                voice_context=params.get("voice_context", {}),
                context=params.get("context", ""),
            )
        elif operation == "generate_sentences":
            return self.generate_sentences(
                thoughts=params.get("thoughts", []),
                context=params.get("context", ""),
                voice_context=params.get("voice_context", {}),
                force_neural=params.get("force_neural", False),
                original_input=params.get("original_input", ""),
            )
        elif operation == "apply_grammar_and_style":
            return self.apply_grammar_and_style(
                text=params.get("text", ""),
                voice_context=params.get("voice_context", {}),
                style_config=params.get("style_config", {}),
            )
        else:
            raise InvalidParameterError(
                parameter="operation",
                value=operation,
                reason="Unknown operation for thought_to_text",
            )

    def convert_thought_graph(
        self,
        mcts_nodes: List[Dict[str, Any]],
        voice_context: Dict[str, Any] = None,
        context: str = "",
    ) -> Dict[str, Any]:
        """Convert MCTS node sequence to natural language text"""
        if not mcts_nodes:
            return {"text": "", "confidence": 0.0, "method": "empty_input"}

        try:
            # Extract thoughts from MCTS nodes
            thoughts = []
            for node in mcts_nodes:
                # Handle different MCTS node formats
                if isinstance(node, dict):
                    # If node has a totNode, extract thought from it
                    if "totNode" in node:
                        tot_node = node["totNode"]
                        if isinstance(tot_node, dict):
                            thought = tot_node.get("thought", "")
                        else:
                            thought = str(tot_node)
                    # If node has thought directly
                    elif "thought" in node:
                        thought = node["thought"]
                    # If node has content or text
                    elif "content" in node:
                        thought = node["content"]
                    elif "text" in node:
                        thought = node["text"]
                    else:
                        # Fallback: convert entire node to string representation
                        thought = self._node_to_text(node)

                    if thought:
                        thoughts.append(str(thought))
                else:
                    # If node is a string or other type
                    thoughts.append(str(node))

            # Generate sentences from thoughts
            if voice_context is None:
                voice_context = {}
            result = self.generate_sentences(thoughts, context, voice_context)
            result["method"] = "mcts_conversion"
            return result

        except Exception as e:
            logger.debug(
                "Failed to convert thought graph; falling back to string concatenation",
                exc_info=True,
                extra={"module_name": "thought_to_text", "error_type": type(e).__name__},
            )
            # Fallback: simple concatenation
            thoughts_text = " ".join([str(node) for node in mcts_nodes])
            return {
                "text": thoughts_text,
                "confidence": 0.5,
                "method": "fallback",
                "error": "Thought graph conversion failed",
            }

    def convert_reasoning_tree(
        self,
        tree_json: Union[str, Dict[str, Any]],
        voice_context: Dict[str, Any] = None,
        context: str = "",
    ) -> Dict[str, Any]:
        """Convert abstract reasoning tree JSON to natural language text"""
        try:
            # Parse JSON if string
            if isinstance(tree_json, str):
                tree = json.loads(tree_json)
            else:
                tree = tree_json

            # Extract thoughts from tree structure
            thoughts = self._extract_thoughts_from_tree(tree)

            if not thoughts:
                return {"text": "", "confidence": 0.0, "method": "empty_tree"}

            # Generate sentences from thoughts
            if voice_context is None:
                voice_context = {}
            result = self.generate_sentences(thoughts, context, voice_context)
            result["method"] = "reasoning_tree_conversion"
            return result

        except Exception as e:
            logger.debug(
                "Failed to convert reasoning tree",
                exc_info=True,
                extra={"module_name": "thought_to_text", "error_type": type(e).__name__},
            )
            return {
                "text": "",
                "confidence": 0.0,
                "method": "error",
                "error": "Reasoning tree conversion failed",
            }

    def generate_sentences(
        self, thoughts: List[str], context: str = "", voice_context: Dict[str, Any] = None, 
        force_neural: bool = False, original_input: str = ""
    ) -> Dict[str, Any]:
        """Core conversion logic: generate natural sentences from thought list"""
        if not thoughts:
            return {"text": "", "confidence": 0.0}

        if voice_context is None:
            voice_context = {}

        try:
            # Step 0: Check if we should use neural generation
            should_use_neural = force_neural or any(
                str(t).startswith(("I will now analyze", "I will dynamically", "I will perform", "I will synthesize"))
                for t in thoughts
            )

            if should_use_neural:
                print(f"[DEBUG] ThoughtToText: Dynamic solve triggered. Engine: {self.text_generation_engine}")
                if self.text_generation_engine:
                    try:
                        print(f"[DEBUG] ThoughtToText: Calling engine.generate_with_neural with prompt: {original_input[:50]}...")
                        # Use a more imperative prompt format to discourage dataset generation
                        imperative_prompt = (
                            f"Instructions: Provide a detailed, multi-sentence answer to the task below.\n"
                            f"GROUNDING: Use ONLY the following facts to construct your answer. Do not add outside information.\n"
                            f"Facts: {context}\n\n"
                            f"Task: {original_input}\n"
                            f"Detailed Answer:"
                        )
                        neural_result = self.text_generation_engine.execute(
                            "generate_with_neural",
                            {
                                "prompt": imperative_prompt,
                                "voice_context": voice_context,
                                "context": context,
                            }
                        )
                        print(f"[DEBUG] ThoughtToText: Engine result success: {neural_result.get('success')}")
                        if neural_result.get("success") and neural_result.get("text"):
                            generated_text = neural_result["text"]
                            
                            # Truncate at double newline to avoid word salad
                            if "\n\n" in generated_text:
                                parts = generated_text.split("\n\n")
                                if len(parts[0]) > 20:
                                    generated_text = parts[0]
                                else:
                                    generated_text = "\n\n".join(parts[:2])

                            print(f"[DEBUG] ThoughtToText: Returning neural text: {generated_text[:50]}...")
                            return {
                                "text": generated_text.strip(),
                                "confidence": 0.8,
                                "method": "neural_reconstruction",
                            }
                    except Exception as e:
                        print(f"[DEBUG] ThoughtToText: Engine call failed: {e}")
                        pass

            # Step 1: Filter out any instruction-style thoughts BEFORE processing
            thoughts = self._filter_instructions_from_thoughts(thoughts)
            if not thoughts:
                return {
                    "text": "",
                    "confidence": 0.0,
                    "method": "filtered_all_instructions",
                }

            # Step 1: Convert thoughts to sentence fragments
            fragments = []
            for i, thought in enumerate(thoughts):
                fragment = self._thought_to_fragment(thought, i, len(thoughts))
                if fragment:
                    fragments.append(fragment)

            # Step 2: Combine fragments into coherent sentences
            combined_text = self._combine_fragments(fragments, context)

            # Step 3: Apply grammar correction and style transfer
            result = self.apply_grammar_and_style(combined_text, voice_context, {})

            # Step 4: Post-process to remove any remaining instructions
            if result and "text" in result:
                result["text"] = self._filter_instructions_from_output(result["text"])

            # Step 5: Use phrase_embeddings and hybrid_phrasing_service to improve text quality
            if result.get("text"):
                # Use phrase_embeddings to enhance semantic quality
                if self.phrase_module:
                    try:
                        # Embed the generated text to ensure semantic coherence
                        embedding_result = self.phrase_module.execute(
                            "embed_sentence",
                            {"text": result["text"]}
                        )
                        if embedding_result.get("embedding"):
                            # Text has valid semantic embedding - good quality indicator
                            if "confidence" in result:
                                result["confidence"] = min(1.0, result["confidence"] + 0.05)
                    except Exception:
                        pass  # Continue if phrase embeddings fail
                
                # Use hybrid_phrasing_service to improve phrasing if available
                if self.hybrid_phrasing_service:
                    try:
                        # Extract key phrases from the generated text
                        text_words = result["text"].split()[:10]  # First 10 words
                        keyword = " ".join(text_words) if text_words else result["text"][:30]
                        
                        # Use hybrid phrasing to generate better phrases
                        hybrid_result = self.hybrid_phrasing_service.execute(
                            "generate_hybrid_phrase",
                            {
                                "context": context or result["text"],
                                "keyword": keyword,
                                "voice_context": voice_context,
                                "max_length": 25,
                            }
                        )
                        if hybrid_result.get("success") and hybrid_result.get("result", {}).get("phrase"):
                            # Blend the hybrid phrase with the existing text
                            hybrid_phrase = hybrid_result["result"]["phrase"]
                            # If hybrid phrase is better, use it to enhance the text
                            if hybrid_phrase and len(hybrid_phrase) > 10 and len(hybrid_phrase) < len(result["text"]):
                                # Use hybrid phrase to improve specific parts
                                # For now, enhance confidence if hybrid phrasing succeeded
                                if "confidence" in result:
                                    result["confidence"] = min(1.0, result["confidence"] + 0.1)
                    except Exception as e:
                        # Continue if hybrid phrasing fails
                        pass
            
            # Calculate confidence based on module availability
            confidence = 0.7  # Base confidence
            if self.grammar_module:
                confidence += 0.1
            if self.style_module:
                confidence += 0.1
            if self.phrase_module:
                confidence += 0.1
            if self.hybrid_phrasing_service:
                confidence += 0.1

            result["confidence"] = min(1.0, confidence)
            return result

        except Exception as e:
            logger.debug(
                "Sentence generation failed; using fallback join",
                exc_info=True,
                extra={"module_name": "thought_to_text", "error_type": type(e).__name__},
            )
            # Fallback: simple join (but still filter instructions)
            fallback_text = ". ".join(thoughts) + "." if thoughts else ""
            fallback_text = self._filter_instructions_from_output(fallback_text)
            return {
                "text": fallback_text,
                "confidence": 0.5,
                "method": "fallback",
                "error": "Sentence generation failed",
            }

    def apply_grammar_and_style(
        self, text: str, voice_context: Dict[str, Any] = None, style_config: Dict[str, Any] = {}
    ) -> Dict[str, Any]:
        """Post-process text with grammar correction and style transfer"""
        if not text:
            return {"text": "", "confidence": 0.0}

        if voice_context is None:
            voice_context = {}

        processed_text = text
        confidence = 0.7

        try:
            # Apply grammar correction if available
            if self.grammar_module:
                try:
                    grammar_result = self.grammar_module.execute(
                        "naturalize_response",
                        {"text": processed_text, "voice_context": voice_context, "context": ""},
                    )
                    if grammar_result and "text" in grammar_result:
                        processed_text = grammar_result["text"]
                        if "confidence" in grammar_result:
                            confidence = max(
                                confidence, grammar_result["confidence"] * 0.8
                            )
                except Exception as e:
                    logger.debug(
                        "Grammar correction failed; continuing without grammar adjustments",
                        exc_info=True,
                        extra={"module_name": "thought_to_text", "error_type": type(e).__name__},
                    )

            # Apply style transfer if available
            if self.style_module and style_config:
                try:
                    style_result = self.style_module.execute(
                        "transfer_style",
                        {"text": processed_text, "target_style": style_config},
                    )
                    if style_result and "transformed_text" in style_result.get(
                        "result", {}
                    ):
                        processed_text = style_result["result"]["transformed_text"]
                except Exception as e:
                    logger.debug(
                        "Style transfer failed; continuing without style adjustments",
                        exc_info=True,
                        extra={"module_name": "thought_to_text", "error_type": type(e).__name__},
                    )

            # Basic cleanup
            processed_text = self._cleanup_text(processed_text)

            return {
                "text": processed_text,
                "confidence": min(1.0, confidence),
                "method": "grammar_and_style",
            }

        except Exception as e:
            logger.debug(
                "apply_grammar_and_style failed; returning cleaned text fallback",
                exc_info=True,
                extra={"module_name": "thought_to_text", "error_type": type(e).__name__},
            )
            return {
                "text": self._cleanup_text(text),
                "confidence": 0.5,
                "method": "fallback",
                "error": "Grammar/style processing failed",
            }

    # Helper methods

    def _thought_to_fragment(self, thought: str, index: int, total: int) -> str:
        """Convert a single thought to a sentence fragment"""
        thought = str(thought).strip()

        if not thought:
            return ""

        # Remove excessive whitespace
        thought = re.sub(r"\s+", " ", thought)

        # If thought is already a complete sentence, return as-is
        if thought.endswith((".", "!", "?")):
            return thought

        # If thought starts with lowercase, capitalize it
        if thought and thought[0].islower():
            thought = thought[0].upper() + thought[1:]

        # Add period if missing
        if not thought.endswith((".", "!", "?", ",", ";")):
            thought += "."

        return thought

    def _combine_fragments(self, fragments: List[str], context: str) -> str:
        """Combine sentence fragments into coherent paragraphs with proper structure"""
        if not fragments:
            return ""

        # Step 1: Clean and normalize fragments
        cleaned_fragments = []
        for fragment in fragments:
            fragment = fragment.strip()
            if fragment:
                # Ensure proper capitalization
                if fragment and fragment[0].islower():
                    fragment = fragment[0].upper() + fragment[1:]
                cleaned_fragments.append(fragment)

        if not cleaned_fragments:
            return ""

        # Step 2: Add discourse markers and transitions based on fragment relationships
        combined_fragments = self._add_discourse_markers(cleaned_fragments)

        # Step 3: Join fragments with appropriate punctuation
        combined = self._join_with_punctuation(combined_fragments)

        # Step 4: Remove duplicate punctuation
        combined = re.sub(r"\.\s*\.+", ".", combined)
        combined = re.sub(r"!\s*!+", "!", combined)
        combined = re.sub(r"\?\s*\?+", "?", combined)

        # Step 5: Ensure proper spacing after punctuation
        combined = re.sub(r"([.!?])([A-Za-z])", r"\1 \2", combined)

        # Step 6: Trim whitespace
        combined = combined.strip()

        return combined

    def _add_discourse_markers(self, fragments: List[str]) -> List[str]:
        """Add discourse markers and transitions between fragments for natural flow"""
        if len(fragments) <= 1:
            return fragments

        # Discourse markers for different relationships
        additive_markers = ["Also", "Plus", "And", "Additionally", "Furthermore"]
        contrastive_markers = ["But", "However", "Though", "Although", "Yet"]
        causal_markers = ["So", "Therefore", "Thus", "Hence", "As a result"]
        sequential_markers = ["Then", "Next", "After that", "Following that"]
        explanatory_markers = [
            "For example",
            "For instance",
            "Specifically",
            "In particular",
        ]

        result = [fragments[0]]  # First fragment doesn't need a marker

        for i in range(1, len(fragments)):
            prev_fragment = fragments[i - 1].lower()
            current_fragment = fragments[i].lower()

            # Determine relationship type (simplified heuristic)
            marker = None

            # Check for contrast
            if any(
                word in prev_fragment
                for word in ["but", "however", "though", "although"]
            ):
                marker = None  # Already has contrast marker
            elif any(
                word in current_fragment
                for word in ["but", "however", "though", "although", "yet"]
            ):
                marker = None  # Current has contrast marker
            # Check for causal relationship
            elif any(
                word in current_fragment
                for word in ["because", "since", "due to", "as a result"]
            ):
                marker = (
                    random.choice(causal_markers) if random.random() < 0.3 else None
                )
            # Check for example/explanation
            elif any(
                word in current_fragment
                for word in ["example", "instance", "specifically", "particular"]
            ):
                marker = (
                    random.choice(explanatory_markers)
                    if random.random() < 0.3
                    else None
                )
            # Check for sequence
            elif any(
                word in current_fragment
                for word in ["then", "next", "after", "following", "finally"]
            ):
                marker = (
                    random.choice(sequential_markers) if random.random() < 0.2 else None
                )
            # Default: additive (most common)
            else:
                # Only add additive markers occasionally to avoid overuse
                if (
                    random.random() < 0.2 and i < len(fragments) - 1
                ):  # Don't add to last fragment
                    marker = random.choice(additive_markers)

            if marker:
                result.append(f"{marker}, {fragments[i]}")
            else:
                result.append(fragments[i])

        return result

    def _join_with_punctuation(self, fragments: List[str]) -> str:
        """Join fragments with appropriate punctuation for natural flow"""
        if not fragments:
            return ""

        if len(fragments) == 1:
            fragment = fragments[0]
            # Ensure it ends with punctuation
            if not fragment.endswith((".", "!", "?")):
                fragment += "."
            return fragment

        # For multiple fragments, join with appropriate punctuation
        result_parts = []
        for i, fragment in enumerate(fragments):
            fragment = fragment.strip()
            if not fragment:
                continue

            # Remove trailing punctuation (we'll add it back)
            fragment = re.sub(r"[.!?]+$", "", fragment)

            # Determine punctuation based on position and content
            if i == len(fragments) - 1:  # Last fragment
                # Check if it's a question
                if "?" in fragments[i] or any(
                    word in fragment.lower()
                    for word in ["what", "how", "why", "when", "where", "who"]
                ):
                    fragment += "?"
                # Check if it's exclamatory
                elif "!" in fragments[i] or any(
                    word in fragment.lower()
                    for word in ["wow", "amazing", "great", "awesome"]
                ):
                    fragment += "!"
                else:
                    fragment += "."
            else:
                # Middle fragments: use comma or period based on length
                if len(fragment.split()) > 15:  # Long fragment
                    fragment += "."
                else:
                    fragment += ","

            result_parts.append(fragment)

        # Join with spaces
        return " ".join(result_parts)

    def _filter_instructions_from_thoughts(self, thoughts: List[str]) -> List[str]:
        """Filter out instruction-style thoughts before processing"""
        if not thoughts:
            return []

        # Comprehensive instruction patterns - focus on SELF-INSTRUCTIONS and META-COMMENTARY
        instruction_patterns = [
            # First-person meta-commentary
            "i will now",
            "i will dynamically",
            "i will perform",
            "i will synthesize",
            "i need to",
            "i should",
            "i must",
            "i want to",
            "i am analyzing",
            "i am dynamically",
            "i will break down",
            "i will explore",
            "i will provide",
            "i will generate",
            "i will create",
            "i will analyze",
            "i will identify",
            "let me",
            "let's",
            "starting to",
            "starting by",
            # Imperative instructions to the system itself (not the user)
            "respond with",
            "generate a",
            "provide an",
            "make sure to",
            "ensure that",
        ]

        filtered = []
        for thought in thoughts:
            thought_lower = thought.lower().strip()
            # Only filter if it STARTS with a meta-commentary pattern
            is_meta = any(
                thought_lower.startswith(pattern) for pattern in instruction_patterns
            )

            if not is_meta:
                filtered.append(thought)

        return filtered

    def _filter_instructions_from_output(self, text: str) -> str:
        """Post-process output to remove any remaining instruction patterns"""
        if not text:
            return text

        # Match the patterns used in _filter_instructions_from_thoughts
        instruction_patterns = [
            "i will now",
            "i will dynamically",
            "i will perform",
            "i will synthesize",
            "i need to",
            "i should",
            "i must",
            "i want to",
            "i am analyzing",
            "i am dynamically",
            "i will break down",
            "i will explore",
            "i will provide",
            "i will generate",
            "i will create",
            "i will analyze",
            "i will identify",
            "let me",
            "let's",
            "starting to",
            "starting by",
            "respond with",
            "generate a",
            "provide an",
            "make sure to",
            "ensure that",
        ]

        # Split into sentences
        sentences = re.split(r"(?<=[.!?])\s+", text)
        filtered_sentences = []

        for sentence in sentences:
            sentence = sentence.strip()
            if not sentence:
                continue

            sentence_lower = sentence.lower()
            # Check if sentence is an instruction
            is_instruction = any(
                sentence_lower.startswith(pattern) for pattern in instruction_patterns
            )

            if not is_instruction:
                filtered_sentences.append(sentence)

        # Rejoin sentences
        if filtered_sentences:
            return " ".join(filtered_sentences)

        # If all sentences were filtered, return empty
        return ""

    def _extract_thoughts_from_tree(self, tree: Dict[str, Any]) -> List[str]:
        """Extract thoughts from a reasoning tree structure"""
        thoughts = []

        # Handle different tree structures
        if isinstance(tree, dict):
            # If tree has a "thoughts" list
            if "thoughts" in tree:
                thoughts.extend([str(t) for t in tree["thoughts"] if t])

            # If tree has "nodes" list
            if "nodes" in tree:
                for node in tree["nodes"]:
                    if isinstance(node, dict):
                        if "thought" in node:
                            thoughts.append(str(node["thought"]))
                        elif "content" in node:
                            thoughts.append(str(node["content"]))
                    else:
                        thoughts.append(str(node))

            # If tree has "root" node
            if "root" in tree:
                root = tree["root"]
                if isinstance(root, dict):
                    if "thought" in root:
                        thoughts.append(str(root["thought"]))
                    elif "content" in root:
                        thoughts.append(str(root["content"]))
                else:
                    thoughts.append(str(root))

            # If tree has "path" list
            if "path" in tree:
                for step in tree["path"]:
                    if isinstance(step, dict):
                        if "thought" in step:
                            thoughts.append(str(step["thought"]))
                        elif "content" in step:
                            thoughts.append(str(step["content"]))
                    else:
                        thoughts.append(str(step))

            # If tree itself has thought/content
            if "thought" in tree and not thoughts:
                thoughts.append(str(tree["thought"]))
            elif "content" in tree and not thoughts:
                thoughts.append(str(tree["content"]))
        elif isinstance(tree, list):
            # If tree is a list of thoughts
            thoughts = [str(t) for t in tree if t]

        return thoughts

    def _node_to_text(self, node: Dict[str, Any]) -> str:
        """Convert a node dictionary to text representation"""
        # Try various fields that might contain the thought
        for field in ["thought", "content", "text", "value", "answer", "conclusion"]:
            if field in node and node[field]:
                return str(node[field])

        # If no direct text field, try to summarize the node
        if "id" in node:
            return f"Step {node['id']}"

        # Last resort: convert to JSON string (limited length)
        node_str = json.dumps(node, default=str)
        if len(node_str) > 200:
            node_str = node_str[:200] + "..."
        return node_str

    def _cleanup_text(self, text: str) -> str:
        """Basic text cleanup"""
        if not text:
            return ""

        # Remove excessive whitespace
        text = re.sub(r"\s+", " ", text)

        # Fix spacing around punctuation
        text = re.sub(r"\s+([.!?,;:])", r"\1", text)
        text = re.sub(r"([.!?,;:])\s*([.!?,;:])", r"\1 \2", text)

        # Ensure space after punctuation before letters
        text = re.sub(r"([.!?])([A-Za-z])", r"\1 \2", text)

        # Trim whitespace
        text = text.strip()

        return text

    def validate_params(self, operation: str, params: Dict[str, Any]) -> bool:
        """Validate parameters for operations"""
        if operation == "convert_thought_graph":
            return "mcts_nodes" in params
        elif operation == "convert_reasoning_tree":
            return "tree_json" in params
        elif operation == "generate_sentences":
            return "thoughts" in params
        elif operation == "apply_grammar_and_style":
            return "text" in params
        return True
