"""
Text Generation Engine Module
Generate complete responses from reasoning results with sentence-level control
Integrates with hybrid_phrasing_service, universal_voice_engine, and thought_to_text
"""

from typing import Any, Dict, List, Optional
import re
import logging

from mavaia_core.brain.base_module import BaseBrainModule, ModuleMetadata
from mavaia_core.brain.registry import ModuleRegistry
from mavaia_core.exceptions import InvalidParameterError

logger = logging.getLogger(__name__)


class TextGenerationEngineModule(BaseBrainModule):
    """Generate complete responses from reasoning results with sentence-level control"""

    def __init__(self):
        super().__init__()
        self.universal_voice_engine = None
        self.hybrid_phrasing_service = None
        self.phrase_embeddings = None
        self.thought_to_text = None
        self.neural_grammar = None
        self.neural_text_generator = None
        self._modules_loaded = False

    @property
    def metadata(self) -> ModuleMetadata:
        return ModuleMetadata(
            name="text_generation_engine",
            version="1.0.0",
            description="Generate complete responses from reasoning results with sentence-level control",
            operations=[
                "generate_full_response",
                "generate_sentence",
                "enhance_phrasing",
                "apply_voice_style",
                "ensure_coherence",
                "generate_with_neural",
            ],
            dependencies=[],
            model_required=False,
        )

    def initialize(self) -> bool:
        """Initialize the module"""
        return True

    def _ensure_modules_loaded(self):
        """Lazy load dependent modules"""
        if self._modules_loaded:
            return

        try:
            try:
                self.universal_voice_engine = ModuleRegistry.get_module(
                    "universal_voice_engine"
                )
            except Exception:
                pass

            try:
                self.hybrid_phrasing_service = ModuleRegistry.get_module(
                    "hybrid_phrasing_service"
                )
            except Exception:
                pass

            try:
                self.phrase_embeddings = ModuleRegistry.get_module("phrase_embeddings")
            except Exception:
                pass

            try:
                self.thought_to_text = ModuleRegistry.get_module("thought_to_text")
            except Exception:
                pass

            try:
                self.neural_grammar = ModuleRegistry.get_module("neural_grammar")
            except Exception:
                pass

            try:
                self.neural_text_generator = ModuleRegistry.get_module(
                    "neural_text_generator"
                )
            except Exception:
                pass

            self._modules_loaded = True
        except Exception as e:
            logger.debug(
                "Failed to load one or more text_generation_engine dependencies",
                exc_info=True,
                extra={"module_name": "text_generation_engine", "error_type": type(e).__name__},
            )

    def execute(self, operation: str, params: Dict[str, Any]) -> Dict[str, Any]:
        """Execute an operation"""
        self._ensure_modules_loaded()

        if operation == "generate_full_response":
            return self._generate_full_response(params)
        elif operation == "generate_sentence":
            return self._generate_sentence(params)
        elif operation == "enhance_phrasing":
            return self._enhance_phrasing(params)
        elif operation == "apply_voice_style":
            return self._apply_voice_style(params)
        elif operation == "ensure_coherence":
            return self._ensure_coherence(params)
        elif operation == "generate_with_neural":
            return self._generate_with_neural(params)
        else:
            raise InvalidParameterError(
                parameter="operation",
                value=operation,
                reason="Unknown operation for text_generation_engine",
            )

    def _generate_full_response(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """
        Generate complete response from reasoning thoughts
        
        Args:
            params:
                - thoughts: List of reasoning thoughts/strings
                - mcts_nodes: Optional MCTS nodes (alternative to thoughts)
                - reasoning_tree: Optional reasoning tree (alternative to thoughts)
                - voice_context: Voice context from universal_voice_engine
                - context: Additional context
                - original_input: Original user input
        
        Returns:
            Dictionary with generated text and metadata
        """
        thoughts = params.get("thoughts", [])
        mcts_nodes = params.get("mcts_nodes", [])
        reasoning_tree = params.get("reasoning_tree")
        voice_context = params.get("voice_context", {})
        context = params.get("context", "")
        original_input = params.get("original_input", "")

        # Extract thoughts from various formats
        if mcts_nodes:
            # Convert MCTS nodes to thoughts using thought_to_text
            if self.thought_to_text:
                try:
                    result = self.thought_to_text.execute(
                        "convert_thought_graph",
                        {
                            "mcts_nodes": mcts_nodes,
                            "voice_context": voice_context,
                            "context": context,
                        },
                    )
                    initial_text = result.get("text", "")
                    if initial_text:
                        thoughts = [initial_text]
                except Exception:
                    pass

        if reasoning_tree and not thoughts:
            # Convert reasoning tree to thoughts
            if self.thought_to_text:
                try:
                    result = self.thought_to_text.execute(
                        "convert_reasoning_tree",
                        {
                            "tree_json": reasoning_tree,
                            "voice_context": voice_context,
                            "context": context,
                        },
                    )
                    initial_text = result.get("text", "")
                    if initial_text:
                        thoughts = [initial_text]
                except Exception:
                    pass

        if not thoughts:
            return {
                "success": False,
                "error": "No thoughts provided",
                "text": "",
                "confidence": 0.0,
            }

        # Step 1: Convert thoughts to initial text
        initial_text = ""
        if self.thought_to_text:
            try:
                result = self.thought_to_text.execute(
                    "generate_sentences",
                    {
                        "thoughts": thoughts,
                        "voice_context": voice_context,
                        "context": context,
                    },
                )
                initial_text = result.get("text", "")
            except Exception as e:
                logger.debug(
                    "thought_to_text failed; using fallback join",
                    exc_info=True,
                    extra={"module_name": "text_generation_engine", "error_type": type(e).__name__},
                )
                # Fallback: simple join
                initial_text = ". ".join(str(t) for t in thoughts) + "."

        if not initial_text:
            # Final fallback
            initial_text = ". ".join(str(t) for t in thoughts) + "."

        # Step 2: Enhance phrasing using hybrid_phrasing_service
        enhanced_text = self._enhance_text_phrasing(initial_text, voice_context, context)

        # Step 3: Generate sentence-by-sentence with coherence
        sentences = self._split_into_sentences(enhanced_text)
        coherent_sentences = []
        
        for i, sentence in enumerate(sentences):
            if sentence.strip():
                # Generate/refine individual sentence
                sentence_result = self._generate_sentence({
                    "sentence": sentence,
                    "previous_sentences": coherent_sentences,
                    "voice_context": voice_context,
                    "context": context,
                })
                refined_sentence = sentence_result.get("sentence", sentence)
                coherent_sentences.append(refined_sentence)

        # Step 4: Ensure coherence between sentences
        coherent_text = self._ensure_sentence_coherence(
            coherent_sentences, voice_context
        )

        # Step 5: Apply voice style
        final_text = self._apply_voice_to_text(coherent_text, voice_context)

        # Step 6: Grammar correction
        if self.neural_grammar:
            try:
                grammar_result = self.neural_grammar.execute(
                    "naturalize_response",
                    {
                        "text": final_text,
                        "voice_context": voice_context,
                        "context": context,
                    },
                )
                if grammar_result and grammar_result.get("text"):
                    final_text = grammar_result["text"]
            except Exception:
                pass  # Continue if grammar correction fails

        # Calculate confidence
        confidence = self._calculate_confidence(
            initial_text, final_text, len(thoughts), voice_context
        )

        return {
            "success": True,
            "text": final_text,
            "confidence": confidence,
            "method": "full_response_generation",
            "metadata": {
                "initial_length": len(initial_text),
                "final_length": len(final_text),
                "sentence_count": len(coherent_sentences),
                "thought_count": len(thoughts),
            },
        }

    def _generate_sentence(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """
        Generate individual sentence with coherence
        
        Args:
            params:
                - sentence: Sentence text to generate/refine
                - previous_sentences: List of previous sentences for coherence
                - voice_context: Voice context
                - context: Additional context
        
        Returns:
            Dictionary with generated sentence
        """
        sentence = params.get("sentence", "")
        previous_sentences = params.get("previous_sentences", [])
        voice_context = params.get("voice_context", {})
        context = params.get("context", "")

        if not sentence:
            return {"success": False, "error": "No sentence provided", "sentence": ""}

        refined_sentence = sentence.strip()

        # Add discourse markers if needed
        if previous_sentences:
            refined_sentence = self._add_discourse_marker_if_needed(
                refined_sentence, previous_sentences[-1], voice_context
            )

        # Enhance phrasing for this sentence
        if self.hybrid_phrasing_service:
            try:
                # Extract key phrase from sentence
                words = refined_sentence.split()[:8]  # First 8 words
                keyword = " ".join(words) if words else refined_sentence[:30]

                phrase_result = self.hybrid_phrasing_service.execute(
                    "generate_hybrid_phrase",
                    {
                        "context": context or refined_sentence,
                        "keyword": keyword,
                        "voice_context": voice_context,
                        "max_length": len(refined_sentence.split()) + 5,
                    },
                )
                if phrase_result.get("success") and phrase_result.get("result", {}).get("phrase"):
                    # Blend phrase if it improves the sentence
                    hybrid_phrase = phrase_result["result"]["phrase"]
                    if len(hybrid_phrase) > 10 and self._is_phrase_improvement(
                        hybrid_phrase, refined_sentence
                    ):
                        # Use hybrid phrase to enhance parts of sentence
                        refined_sentence = self._blend_phrase(
                            refined_sentence, hybrid_phrase
                        )
            except Exception:
                pass  # Continue if phrasing enhancement fails

        # Ensure proper capitalization and punctuation
        refined_sentence = self._normalize_sentence(refined_sentence)

        return {
            "success": True,
            "sentence": refined_sentence,
            "confidence": 0.8,
        }

    def _enhance_phrasing(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """Enhance phrasing using hybrid_phrasing_service"""
        text = params.get("text", "")
        voice_context = params.get("voice_context", {})
        context = params.get("context", "")

        if not text:
            return {"success": False, "error": "No text provided", "text": ""}

        enhanced = self._enhance_text_phrasing(text, voice_context, context)

        return {
            "success": True,
            "text": enhanced,
            "original_length": len(text),
            "enhanced_length": len(enhanced),
        }

    def _apply_voice_style(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """Apply universal voice to generated text"""
        text = params.get("text", "")
        voice_context = params.get("voice_context", {})

        if not text:
            return {"success": False, "error": "No text provided", "text": ""}

        adapted_text = self._apply_voice_to_text(text, voice_context)

        return {
            "success": True,
            "text": adapted_text,
        }

    def _ensure_coherence(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """Ensure sentence-to-sentence coherence"""
        sentences = params.get("sentences", [])
        voice_context = params.get("voice_context", {})

        if not sentences:
            return {"success": False, "error": "No sentences provided", "text": ""}

        coherent_text = self._ensure_sentence_coherence(sentences, voice_context)

        return {
            "success": True,
            "text": coherent_text,
            "sentence_count": len(sentences),
        }

    # Helper methods

    def _enhance_text_phrasing(
        self, text: str, voice_context: Dict[str, Any], context: str
    ) -> str:
        """Enhance phrasing throughout the text"""
        if not self.hybrid_phrasing_service:
            return text

        # Split into sentences
        sentences = self._split_into_sentences(text)
        enhanced_sentences = []

        for sentence in sentences:
            if not sentence.strip():
                continue

            try:
                # Extract key phrase
                words = sentence.split()[:6]
                keyword = " ".join(words) if words else sentence[:25]

                phrase_result = self.hybrid_phrasing_service.execute(
                    "generate_hybrid_phrase",
                    {
                        "context": context or sentence,
                        "keyword": keyword,
                        "voice_context": voice_context,
                        "max_length": len(sentence.split()) + 3,
                    },
                )

                if phrase_result.get("success") and phrase_result.get("result", {}).get("phrase"):
                    hybrid_phrase = phrase_result["result"]["phrase"]
                    # Use hybrid phrase if it's an improvement
                    if self._is_phrase_improvement(hybrid_phrase, sentence):
                        enhanced_sentences.append(hybrid_phrase)
                    else:
                        enhanced_sentences.append(sentence)
                else:
                    enhanced_sentences.append(sentence)
            except Exception:
                enhanced_sentences.append(sentence)

        return " ".join(enhanced_sentences)

    def _split_into_sentences(self, text: str) -> List[str]:
        """Split text into sentences"""
        if not text:
            return []

        # Split on sentence boundaries
        sentences = re.split(r'[.!?]+', text)
        # Filter out empty sentences
        sentences = [s.strip() for s in sentences if s.strip()]

        return sentences

    def _ensure_sentence_coherence(
        self, sentences: List[str], voice_context: Dict[str, Any]
    ) -> str:
        """Ensure coherence between sentences"""
        if not sentences:
            return ""

        if len(sentences) == 1:
            return sentences[0]

        coherent = [sentences[0]]  # First sentence doesn't need a marker

        for i in range(1, len(sentences)):
            prev_sentence = sentences[i - 1]
            current_sentence = sentences[i]

            # Add discourse marker if needed
            marked_sentence = self._add_discourse_marker_if_needed(
                current_sentence, prev_sentence, voice_context
            )
            coherent.append(marked_sentence)

        return " ".join(coherent)

    def _add_discourse_marker_if_needed(
        self, sentence: str, previous_sentence: str, voice_context: Dict[str, Any]
    ) -> str:
        """Add discourse marker if needed for coherence"""
        # Check if sentence already has a discourse marker
        discourse_markers = [
            "also", "furthermore", "moreover", "additionally",
            "however", "but", "although", "though", "yet",
            "therefore", "thus", "hence", "consequently",
            "for example", "for instance", "specifically",
            "then", "next", "after that", "finally",
        ]

        sentence_lower = sentence.lower()
        if any(marker in sentence_lower for marker in discourse_markers):
            return sentence  # Already has a marker

        # Determine if marker is needed based on content
        prev_lower = previous_sentence.lower()
        curr_lower = sentence_lower

        # Check for contrast
        contrast_words = ["but", "however", "although", "though", "yet", "despite"]
        if any(word in curr_lower for word in contrast_words):
            return sentence  # Already indicates contrast

        # Check for causal relationship
        causal_words = ["because", "since", "due to", "as a result", "therefore"]
        if any(word in curr_lower for word in causal_words):
            return sentence  # Already indicates causality

        # Check for example/explanation
        example_words = ["example", "instance", "specifically", "particular"]
        if any(word in curr_lower for word in example_words):
            return sentence  # Already indicates example

        # Default: no marker needed for most cases
        # The sentence structure itself provides coherence
        return sentence

    def _apply_voice_to_text(
        self, text: str, voice_context: Dict[str, Any]
    ) -> str:
        """Apply voice style to text using universal_voice_engine"""
        if not self.universal_voice_engine:
            return text

        try:
            result = self.universal_voice_engine.execute(
                "apply_voice_style",
                {"text": text, "voice_context": voice_context},
            )
            if result.get("success"):
                return result.get("text", text)
        except Exception:
            pass  # Return original if voice application fails

        return text

    def _is_phrase_improvement(self, hybrid_phrase: str, original: str) -> bool:
        """Determine if hybrid phrase is an improvement over original"""
        # Simple heuristic: prefer longer, more complete phrases
        if len(hybrid_phrase) < len(original) * 0.5:
            return False  # Too short

        if len(hybrid_phrase) > len(original) * 2:
            return False  # Too long

        # Prefer phrases with proper sentence structure
        if not hybrid_phrase[0].isupper():
            return False  # Should start with capital

        return True

    def _blend_phrase(self, original: str, hybrid_phrase: str) -> str:
        """Blend hybrid phrase with original sentence"""
        # For now, use hybrid phrase if it's better
        # Future: could do more sophisticated blending
        if self._is_phrase_improvement(hybrid_phrase, original):
            return hybrid_phrase
        return original

    def _normalize_sentence(self, sentence: str) -> str:
        """Normalize sentence capitalization and punctuation"""
        if not sentence:
            return sentence

        sentence = sentence.strip()

        # Ensure starts with capital
        if sentence and sentence[0].islower():
            sentence = sentence[0].upper() + sentence[1:]

        # Ensure ends with punctuation
        if sentence and not sentence[-1] in ".!?":
            sentence += "."

        return sentence

    def _calculate_confidence(
        self,
        initial_text: str,
        final_text: str,
        thought_count: int,
        voice_context: Dict[str, Any],
    ) -> float:
        """Calculate confidence in generated text"""
        base_confidence = 0.7

        # Increase confidence if text was enhanced
        if len(final_text) > len(initial_text) * 0.8:
            base_confidence += 0.1

        # Increase confidence if multiple thoughts were synthesized
        if thought_count > 1:
            base_confidence += min(0.1, thought_count * 0.02)

        # Increase confidence if voice context is well-defined
        if voice_context.get("adaptation_confidence", 0) > 0.7:
            base_confidence += 0.1

        return min(1.0, base_confidence)

    def _generate_with_neural(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """
        Generate text using neural model as primary method
        
        Args:
            params:
                - prompt: Starting prompt/text
                - voice_context: Voice context for style adaptation
                - max_length: Maximum generation length
                - temperature: Sampling temperature
        
        Returns:
            Generated text
        """
        if not self.neural_text_generator:
            return {
                "success": False,
                "error": "Neural text generator not available",
                "text": "",
            }

        prompt = params.get("prompt", "")
        voice_context = params.get("voice_context", {})
        max_length = params.get("max_length", 500)
        temperature = params.get("temperature", 0.7)

        try:
            result = self.neural_text_generator.execute(
                "generate_text",
                {
                    "prompt": prompt,
                    "max_length": max_length,
                    "temperature": temperature,
                    "voice_context": voice_context,
                },
            )

            if result.get("success"):
                generated_text = result.get("text", "")
                
                # Apply voice style if available
                if self.universal_voice_engine:
                    try:
                        voice_result = self.universal_voice_engine.execute(
                            "apply_voice_style",
                            {"text": generated_text, "voice_context": voice_context},
                        )
                        if voice_result.get("success"):
                            generated_text = voice_result.get("text", generated_text)
                    except Exception:
                        pass

                return {
                    "success": True,
                    "text": generated_text,
                    "method": "neural",
                    "confidence": 0.8,
                }
            else:
                return {
                    "success": False,
                    "error": result.get("error", "Neural generation failed"),
                    "text": "",
                }
        except Exception as e:
            return {
                "success": False,
                "error": f"Neural generation error: {str(e)}",
                "text": "",
            }

