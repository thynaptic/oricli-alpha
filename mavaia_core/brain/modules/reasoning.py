from __future__ import annotations
"""
Reasoning Module - Symbolic and structured reasoning engine
Plug-and-play module for analytical, creative, strategic, diagnostic, and comparative reasoning
No LLM dependencies - uses structured reasoning patterns and symbolic methods
"""

import logging
from typing import Any, Dict, List, Optional
import re

from mavaia_core.brain.base_module import BaseBrainModule, ModuleMetadata
from mavaia_core.exceptions import InvalidParameterError

logger = logging.getLogger(__name__)


class ReasoningModule(BaseBrainModule):
    """Perform reasoning tasks using structured patterns and symbolic methods"""
    
    def __init__(self):
        super().__init__()
    
    @property
    def metadata(self) -> ModuleMetadata:
        return ModuleMetadata(
            name="reasoning",
            version="3.0.0",
            description=(
                "Symbolic and structured reasoning engine: deeper chains, "
                "multi-step problem solving, causal reasoning, analogical reasoning, "
                "branching reasoning graphs, strategy selection, self-evaluation, "
                "contradiction detection"
            ),
            operations=[
                "reason",
                "analyze",
                "compare",
                "multi_step_solve",
                "causal_reasoning",
                "analogical_reasoning",
                "deep_analysis",
                "create_reasoning_graph",
                "branch_reasoning",
                "select_strategy",
                "evaluate_reasoning",
                "detect_contradictions",
                "resolve_contradictions",
            ],
            dependencies=[],
            model_required=False,
        )
    
    def initialize(self) -> bool:
        """Initialize the module"""
        return True
    
    def execute(self, operation: str, params: Dict[str, Any]) -> Dict[str, Any]:
        """Execute a reasoning operation"""
        if operation == 'reason' or operation == 'analyze':
            query = params.get("query", "")
            context = params.get("context", [])
            reasoning_type = params.get("reasoning_type", "analytical")

            if not isinstance(query, str) or not query.strip():
                raise InvalidParameterError("query", str(query), "Missing required parameter: query")

            context_list = self._normalize_context(context)
            # Use structured reasoning patterns
            reasoning_text = self._structured_reasoning(
                query, context_list, str(reasoning_type or "analytical")
            )

            return {
                "success": True,
                "reasoning": reasoning_text,
                "conclusion": self._extract_conclusion(reasoning_text),
                "confidence": self._estimate_confidence(reasoning_text),
                "reasoning_steps": self._extract_steps(reasoning_text),
                "reasoning_type": str(reasoning_type or "analytical"),
                "method": "structured_reasoning",
            }

        elif operation == "compare":
            item1 = params.get("item1", "")
            item2 = params.get("item2", "")
            context = params.get("context", [])

            if not isinstance(item1, str) or not item1.strip():
                raise InvalidParameterError("item1", str(item1), "Missing required parameter: item1")
            if not isinstance(item2, str) or not item2.strip():
                raise InvalidParameterError("item2", str(item2), "Missing required parameter: item2")

            query = f"Compare: {item1} vs {item2}"
            return self.execute(
                "reason",
                {
                    "query": query,
                    "context": context,
                    "reasoning_type": "comparative",
                },
            )

        elif operation == "multi_step_solve":
            problem = params.get("problem", "")
            steps = params.get("steps", 5)
            context = params.get("context", [])
            return self.multi_step_solve(problem, steps, context)

        elif operation == "causal_reasoning":
            event = params.get("event", "")
            context = params.get("context", [])
            return self.causal_reasoning(event, context)

        elif operation == "analogical_reasoning":
            source = params.get("source", "")
            target = params.get("target", "")
            context = params.get("context", [])
            return self.analogical_reasoning(source, target, context)

        elif operation == "deep_analysis":
            query = params.get("query", "")
            depth = params.get("depth", 3)
            context = params.get("context", [])
            return self.deep_analysis(query, depth, context)

        elif operation == "create_reasoning_graph":
            query = params.get("query", "")
            context = params.get("context", [])
            return self.create_reasoning_graph(query, context)

        elif operation == "branch_reasoning":
            query = params.get("query", "")
            branches = params.get("branches", 3)
            context = params.get("context", [])
            return self.branch_reasoning(query, branches, context)

        elif operation == "select_strategy":
            problem = params.get("problem", "")
            problem_type = params.get("problem_type")
            context = params.get("context", [])
            return self.select_strategy(problem, problem_type, context)

        elif operation == "evaluate_reasoning":
            reasoning = params.get("reasoning", "")
            reasoning_steps = params.get("reasoning_steps", [])
            return self.evaluate_reasoning(reasoning, reasoning_steps)

        elif operation == "detect_contradictions":
            reasoning_steps = params.get("reasoning_steps", [])
            return self.detect_contradictions(reasoning_steps)

        elif operation == "resolve_contradictions":
            contradictions = params.get("contradictions", [])
            reasoning_steps = params.get("reasoning_steps", [])
            return self.resolve_contradictions(contradictions, reasoning_steps)

        else:
            raise InvalidParameterError(
                parameter="operation",
                value=operation,
                reason="Unknown operation for reasoning",
            )

    def _normalize_context(self, context: Any) -> List[str]:
        """Normalize context to a list[str] for internal reasoning utilities."""
        if context is None:
            return []
        if isinstance(context, str):
            ctx = context.strip()
            return [ctx] if ctx else []
        if isinstance(context, list):
            out: list[str] = []
            for item in context:
                if item is None:
                    continue
                if isinstance(item, str):
                    s = item.strip()
                    if s:
                        out.append(s)
                else:
                    # Best-effort stringification; keep non-empty.
                    s = str(item).strip()
                    if s:
                        out.append(s)
            return out
        # Unknown type; stringify safely.
        s = str(context).strip()
        return [s] if s else []
    
    def _build_reasoning_prompt(
        self, query: str, context: List[str], reasoning_type: str
    ) -> str:
        """Build a prompt based on reasoning type"""
        prompts = {
            "analytical": f"Analyze the following query step by step: {query}",
            "creative": f"Think creatively about: {query}",
            "strategic": f"Develop a strategic approach for: {query}",
            "diagnostic": f"Diagnose the problem in: {query}",
            "comparative": f"Compare and contrast: {query}",
        }
        
        base_prompt = prompts.get(reasoning_type, prompts["analytical"])
        
        if context:
            context_text = "\n".join(f"- {c}" for c in context)
            return f"{base_prompt}\n\nContext:\n{context_text}\n\nReasoning:"
        
        return f"{base_prompt}\n\nReasoning:"
    
    def _extract_conclusion(self, reasoning: str) -> str:
        """Extract conclusion from reasoning text"""
        if not reasoning:
            return ""
        lines = reasoning.strip().split("\n")
        return lines[-1] if lines else reasoning[:200]
    
    def _estimate_confidence(self, reasoning: str) -> float:
        """Estimate confidence based on reasoning quality"""
        if not reasoning:
            return 0.0
        
        reasoning_lower = reasoning.lower()
        if len(reasoning) > 100 and "therefore" in reasoning_lower:
            return 0.8
        elif len(reasoning) > 50:
            return 0.6
        else:
            return 0.4
    
    def _extract_steps(self, reasoning: str) -> List[str]:
        """Extract reasoning steps"""
        if not reasoning:
            return []
        lines = [line.strip() for line in reasoning.split("\n") if line.strip()]
        return lines[:10]  # Return first 10 steps
    
    def _structured_reasoning(
        self, query: str, context: List[str], reasoning_type: str
    ) -> str:
        """Fallback reasoning when model is not available"""
        # Extract key information from query
        query_lower = query.lower()
        
        # Try to identify if it's a multiple choice question
        if "choices:" in query_lower or any(
            opt in query_lower for opt in ["a)", "b)", "c)", "d)"]
        ):
            # This is a multiple choice question - analyze options
            reasoning = f"Analyzing multiple choice question:\n{query}\n\n"
            reasoning += "Step 1: Identify the key question being asked.\n"
            reasoning += "Step 2: Evaluate each choice against the question.\n"
            reasoning += "Step 3: Eliminate clearly incorrect options.\n"
            reasoning += (
                "Step 4: Select the most accurate answer based on domain knowledge.\n"
            )
        else:
            # Generate multiple reasoning steps for better thought generation
            # Generate actual reasoning instead of meta-reasoning
            # Use context if available, otherwise generate actual answer
            if context and len(context) > 0:
                # Use context to generate actual reasoning
                context_summary = " ".join([c[:200] for c in context[:3] if c])
                reasoning = f"Based on the available information: {context_summary[:300]}"
            else:
                # Don't call cognitive_generator from here - it would create infinite recursion
                # cognitive_generator already orchestrates reasoning module, so calling it back
                # would create a loop. Instead, return empty and let the CoT process handle it
                # or use context if available
                reasoning = ""
        
        if context and reasoning:
            context_text = "\n".join(f"- {c[:100]}" for c in context[:3])
            reasoning += f". Context considered: {context_text}"
        
        return reasoning
    
    def multi_step_solve(
        self, problem: str, steps: int = 5, context: List[str] = None
    ) -> Dict[str, Any]:
        """Solve a problem using multi-step reasoning"""
        if not problem:
            return {
                "solution": "",
                "steps": [],
                "confidence": 0.0,
                "error": "No problem provided",
            }

        if context is None:
            context = []

        # Break down problem into sub-problems
        sub_problems = self._identify_sub_problems(problem)
        reasoning_steps = []

        # Solve each sub-problem
        for i, sub_problem in enumerate(sub_problems[:steps], 1):
            step_reasoning = self._solve_sub_problem(sub_problem, context)
            reasoning_steps.append(
                {
                    "step": i,
                    "sub_problem": sub_problem,
                    "reasoning": step_reasoning,
                    "solution": self._extract_conclusion(step_reasoning),
                }
            )

        # Synthesize final solution
        final_solution = self._synthesize_solution(reasoning_steps, problem)

        return {
            "problem": problem,
            "solution": final_solution,
            "steps": reasoning_steps,
            "sub_problems_identified": len(sub_problems),
            "confidence": self._estimate_confidence(final_solution),
        }

    def causal_reasoning(
        self, event: str, context: List[str] = None
    ) -> Dict[str, Any]:
        """Perform causal reasoning to identify causes and effects"""
        if not event:
            return {
                "event": "",
                "causes": [],
                "effects": [],
                "causal_chain": [],
                "confidence": 0.0,
            }

        if context is None:
            context = []

        # Identify potential causes
        causes = self._identify_causes(event, context)

        # Identify potential effects
        effects = self._identify_effects(event, context)

        # Build causal chain
        causal_chain = self._build_causal_chain(causes, event, effects)

        return {
            "event": event,
            "causes": causes,
            "effects": effects,
            "causal_chain": causal_chain,
            "confidence": min(0.9, 0.5 + len(causes) * 0.1 + len(effects) * 0.1),
        }

    def analogical_reasoning(
        self, source: str, target: str, context: List[str] = None
    ) -> Dict[str, Any]:
        """Perform analogical reasoning by mapping from source to target"""
        if not source or not target:
            return {
                "source": source,
                "target": target,
                "mapping": {},
                "analogy": "",
                "confidence": 0.0,
            }

        if context is None:
            context = []

        # Identify similarities
        similarities = self._find_similarities(source, target)

        # Identify differences
        differences = self._find_differences(source, target)

        # Create mapping
        mapping = self._create_analogical_mapping(source, target, similarities)

        # Generate analogy explanation
        analogy = self._generate_analogy_explanation(
            source, target, similarities, differences
        )

        return {
            "source": source,
            "target": target,
            "similarities": similarities,
            "differences": differences,
            "mapping": mapping,
            "analogy": analogy,
            "confidence": min(0.9, 0.5 + len(similarities) * 0.1),
        }

    def deep_analysis(
        self, query: str, depth: int = 3, context: List[str] = None
    ) -> Dict[str, Any]:
        """Perform deep analysis with multiple layers of reasoning"""
        if not query:
            return {
                "query": "",
                "analysis": "",
                "layers": [],
                "insights": [],
                "confidence": 0.0,
            }

        if context is None:
            context = []

        layers = []
        current_query = query

        # Build reasoning layers
        for layer_num in range(1, depth + 1):
            layer_analysis = self._analyze_layer(current_query, layer_num, context)
            layers.append(
                {
                    "layer": layer_num,
                    "query": current_query,
                    "analysis": layer_analysis,
                    "insights": self._extract_insights(layer_analysis),
                }
            )

            # Use insights to refine query for next layer
            if layer_num < depth:
                current_query = self._refine_query_for_next_layer(
                    current_query, layer_analysis
                )

        # Synthesize final analysis
        final_analysis = self._synthesize_deep_analysis(layers, query)

        return {
            "query": query,
            "analysis": final_analysis,
            "layers": layers,
            "insights": self._extract_all_insights(layers),
            "depth": depth,
            "confidence": min(0.95, 0.6 + depth * 0.1),
        }

    def _identify_sub_problems(self, problem: str) -> List[str]:
        """Break down a problem into sub-problems"""
        # Simple heuristic: look for conjunctions and question words
        sub_problems = []

        # Split by common conjunctions
        conjunctions = [" and ", " or ", " but ", " then ", " also "]
        parts = [problem]
        for conj in conjunctions:
            new_parts = []
            for part in parts:
                new_parts.extend(part.split(conj))
            parts = new_parts

        # Filter and clean
        for part in parts:
            part = part.strip()
            if len(part) > 10:  # Meaningful sub-problem
                sub_problems.append(part)

        # If no sub-problems found, return the original problem
        if not sub_problems:
            sub_problems = [problem]

        return sub_problems[:5]  # Limit to 5 sub-problems

    def _solve_sub_problem(self, sub_problem: str, context: List[str]) -> str:
        """Solve a single sub-problem"""
        # Use structured reasoning for each sub-problem
        return self._structured_reasoning(sub_problem, context, "analytical")

    def _synthesize_solution(
        self, reasoning_steps: List[Dict[str, Any]], original_problem: str
    ) -> str:
        """Synthesize a final solution from reasoning steps"""
        if not reasoning_steps:
            return "Unable to synthesize solution from empty reasoning steps."

        solutions = [step.get("solution", "") for step in reasoning_steps]
        solutions = [s for s in solutions if s]

        if not solutions:
            return "No clear solution emerged from the reasoning steps."

        # Combine solutions
        combined = ". ".join(solutions)
        return f"Based on the analysis: {combined}"

    def _identify_causes(self, event: str, context: List[str]) -> List[str]:
        """Identify potential causes of an event"""
        causes = []

        # Look for causal keywords
        causal_patterns = [
            r"because\s+(.+?)(?:\.|$)",
            r"due\s+to\s+(.+?)(?:\.|$)",
            r"caused\s+by\s+(.+?)(?:\.|$)",
            r"result\s+of\s+(.+?)(?:\.|$)",
        ]

        event_lower = event.lower()
        for pattern in causal_patterns:
            matches = re.findall(pattern, event_lower, re.IGNORECASE)
            causes.extend(matches)

        # If no explicit causes found, infer from context
        if not causes:
            # Simple inference: look for related events in context
            for ctx in context:
                if any(word in ctx.lower() for word in event.lower().split()[:3]):
                    causes.append(f"Related context: {ctx[:100]}")

        return causes[:5]  # Limit to 5 causes

    def _identify_effects(self, event: str, context: List[str]) -> List[str]:
        """Identify potential effects of an event"""
        effects = []

        # Look for effect keywords
        effect_patterns = [
            r"leads?\s+to\s+(.+?)(?:\.|$)",
            r"results?\s+in\s+(.+?)(?:\.|$)",
            r"causes?\s+(.+?)(?:\.|$)",
            r"therefore\s+(.+?)(?:\.|$)",
        ]

        event_lower = event.lower()
        for pattern in effect_patterns:
            matches = re.findall(pattern, event_lower, re.IGNORECASE)
            effects.extend(matches)

        # If no explicit effects found, infer potential effects
        if not effects:
            # Simple inference based on event type
            if "increase" in event_lower:
                effects.append("Potential increase in related metrics")
            elif "decrease" in event_lower:
                effects.append("Potential decrease in related metrics")
            elif "change" in event_lower:
                effects.append("Potential change in system state")

        return effects[:5]  # Limit to 5 effects

    def _build_causal_chain(
        self, causes: List[str], event: str, effects: List[str]
    ) -> List[Dict[str, Any]]:
        """Build a causal chain from causes through event to effects"""
        chain = []

        # Add causes
        for i, cause in enumerate(causes, 1):
            chain.append({"position": i, "type": "cause", "description": cause})

        # Add event
        chain.append({"position": len(chain) + 1, "type": "event", "description": event})

        # Add effects
        for i, effect in enumerate(effects, 1):
            chain.append(
                {
                    "position": len(chain) + 1,
                    "type": "effect",
                    "description": effect,
                }
            )

        return chain

    def _find_similarities(self, source: str, target: str) -> List[str]:
        """Find similarities between source and target"""
        similarities = []

        # Extract key words from both
        source_words = set(re.findall(r"\b\w{4,}\b", source.lower()))
        target_words = set(re.findall(r"\b\w{4,}\b", target.lower()))

        # Find common words
        common_words = source_words & target_words
        if common_words:
            similarities.append(f"Shared concepts: {', '.join(list(common_words)[:5])}")

        # Check for similar structures
        if len(source.split()) > 5 and len(target.split()) > 5:
            similarities.append("Both involve complex structures")

        return similarities

    def _find_differences(self, source: str, target: str) -> List[str]:
        """Find differences between source and target"""
        differences = []

        # Extract unique words
        source_words = set(re.findall(r"\b\w{4,}\b", source.lower()))
        target_words = set(re.findall(r"\b\w{4,}\b", target.lower()))

        # Find unique to source
        unique_source = source_words - target_words
        if unique_source:
            differences.append(
                f"Unique to source: {', '.join(list(unique_source)[:3])}"
            )

        # Find unique to target
        unique_target = target_words - source_words
        if unique_target:
            differences.append(
                f"Unique to target: {', '.join(list(unique_target)[:3])}"
            )

        return differences

    def _create_analogical_mapping(
        self, source: str, target: str, similarities: List[str]
    ) -> Dict[str, str]:
        """Create a mapping from source to target"""
        mapping = {}

        # Simple mapping based on word positions
        source_words = source.split()
        target_words = target.split()

        # Map similar words
        for i, source_word in enumerate(source_words[:10]):
            if i < len(target_words):
                mapping[source_word] = target_words[i]

        return mapping

    def _generate_analogy_explanation(
        self,
        source: str,
        target: str,
        similarities: List[str],
        differences: List[str],
    ) -> str:
        """Generate an explanation of the analogy"""
        explanation = f"Analogy: {source} is similar to {target}"

        if similarities:
            explanation += f" because they share: {', '.join(similarities[:2])}"

        if differences:
            explanation += f", but differ in: {', '.join(differences[:2])}"

        return explanation

    def _analyze_layer(
        self, query: str, layer_num: int, context: List[str]
    ) -> str:
        """Analyze a single layer of depth"""
        if layer_num == 1:
            # Surface level analysis
            return self._structured_reasoning(query, context, "analytical")
        elif layer_num == 2:
            # Deeper analysis
            return (
                f"Deeper analysis of: {query}. "
                "Examining underlying patterns and relationships."
            )
        else:
            # Deepest analysis
            return (
                f"Deepest analysis of: {query}. "
                "Exploring fundamental principles and root causes."
            )

    def _extract_insights(self, analysis: str) -> List[str]:
        """Extract insights from analysis text"""
        insights = []

        # Look for key phrases
        insight_patterns = [
            r"important\s+(.+?)(?:\.|$)",
            r"key\s+(.+?)(?:\.|$)",
            r"crucial\s+(.+?)(?:\.|$)",
            r"significant\s+(.+?)(?:\.|$)",
        ]

        for pattern in insight_patterns:
            matches = re.findall(pattern, analysis.lower(), re.IGNORECASE)
            insights.extend(matches)

        # If no insights found, extract sentences
        if not insights:
            sentences = re.split(r"[.!?]+", analysis)
            insights = [s.strip() for s in sentences if len(s.strip()) > 20][:3]

        return insights[:5]

    def _refine_query_for_next_layer(self, query: str, analysis: str) -> str:
        """Refine query for next layer of analysis"""
        # Extract key concepts from analysis
        key_words = re.findall(r"\b\w{5,}\b", analysis.lower())
        if key_words:
            return f"{query} (focusing on: {', '.join(key_words[:3])})"
        return query

    def _synthesize_deep_analysis(
        self, layers: List[Dict[str, Any]], original_query: str
    ) -> str:
        """Synthesize final analysis from all layers"""
        if not layers:
            return "No analysis layers to synthesize."

        # Combine insights from all layers
        all_insights = self._extract_all_insights(layers)

        synthesis = f"Deep analysis of: {original_query}\n\n"
        synthesis += "Key insights across layers:\n"
        for i, insight in enumerate(all_insights[:5], 1):
            synthesis += f"{i}. {insight}\n"

        return synthesis

    def _extract_all_insights(
        self, layers: List[Dict[str, Any]]
    ) -> List[str]:
        """Extract all insights from all layers"""
        all_insights = []
        for layer in layers:
            insights = layer.get("insights", [])
            all_insights.extend(insights)
        return all_insights

    def create_reasoning_graph(
        self, query: str, context: List[str] = None
    ) -> Dict[str, Any]:
        """Create a branching reasoning graph for a query"""
        if context is None:
            context = []

        # Create initial node
        nodes = [
            {
                "id": "root",
                "type": "initial",
                "content": query,
                "reasoning": self._structured_reasoning(query, context, "analytical"),
                "children": [],
            }
        ]

        # Generate branches
        branches = self._generate_reasoning_branches(query, context)
        for i, branch in enumerate(branches[:5]):  # Limit to 5 branches
            branch_id = f"branch_{i}"
            branch_node = {
                "id": branch_id,
                "type": "branch",
                "content": branch["content"],
                "reasoning": branch["reasoning"],
                "children": [],
                "parent": "root",
            }
            nodes.append(branch_node)
            nodes[0]["children"].append(branch_id)

        return {
            "query": query,
            "graph": {
                "nodes": nodes,
                "edges": self._build_graph_edges(nodes),
            },
            "node_count": len(nodes),
        }

    def _generate_reasoning_branches(
        self, query: str, context: List[str]
    ) -> List[Dict[str, Any]]:
        """Generate alternative reasoning branches"""
        branches = []

        # Different reasoning approaches
        approaches = ["analytical", "creative", "strategic", "diagnostic"]

        for approach in approaches:
            reasoning = self._structured_reasoning(query, context, approach)
            branches.append(
                {
                    "approach": approach,
                    "content": f"{approach.capitalize()} approach to: {query}",
                    "reasoning": reasoning,
                }
            )

        return branches

    def _build_graph_edges(
        self, nodes: List[Dict[str, Any]]
    ) -> List[Dict[str, Any]]:
        """Build edges between graph nodes"""
        edges = []
        for node in nodes:
            if "children" in node:
                for child_id in node["children"]:
                    edges.append(
                        {
                            "from": node["id"],
                            "to": child_id,
                            "type": "reasoning",
                        }
                    )
        return edges

    def branch_reasoning(
        self, query: str, branches: int = 3, context: List[str] = None
    ) -> Dict[str, Any]:
        """Create multiple parallel reasoning branches"""
        if context is None:
            context = []

        branch_results = []
        approaches = ["analytical", "creative", "strategic", "diagnostic", "comparative"]

        for i, approach in enumerate(approaches[:branches]):
            reasoning = self._structured_reasoning(query, context, approach)
            conclusion = self._extract_conclusion(reasoning)
            confidence = self._estimate_confidence(reasoning)

            branch_results.append(
                {
                    "branch_id": i,
                    "approach": approach,
                    "reasoning": reasoning,
                    "conclusion": conclusion,
                    "confidence": confidence,
                }
            )

        # Select best branch
        best_branch = max(branch_results, key=lambda b: b["confidence"])

        return {
            "query": query,
            "branches": branch_results,
            "best_branch": best_branch,
            "branch_count": len(branch_results),
        }

    def select_strategy(
        self, problem: str, problem_type: Optional[str] = None, context: List[str] = None
    ) -> Dict[str, Any]:
        """Select optimal reasoning strategy based on problem type"""
        if context is None:
            context = []

        # Detect problem type if not provided
        if not problem_type:
            problem_type = self._detect_problem_type(problem)

        # Strategy mapping
        strategy_map = {
            "mathematical": "analytical",
            "logical": "analytical",
            "creative": "creative",
            "planning": "strategic",
            "diagnostic": "diagnostic",
            "comparison": "comparative",
            "causal": "analytical",
            "analogical": "creative",
        }

        selected_strategy = strategy_map.get(problem_type, "analytical")

        # Generate reasoning with selected strategy
        reasoning = self._structured_reasoning(problem, context, selected_strategy)

        return {
            "problem": problem,
            "problem_type": problem_type,
            "selected_strategy": selected_strategy,
            "reasoning": reasoning,
            "confidence": self._estimate_confidence(reasoning),
        }

    def _detect_problem_type(self, problem: str) -> str:
        """Detect problem type from problem text"""
        problem_lower = problem.lower()

        if any(word in problem_lower for word in ["calculate", "solve", "equation", "formula"]):
            return "mathematical"
        elif any(word in problem_lower for word in ["compare", "difference", "similar"]):
            return "comparison"
        elif any(word in problem_lower for word in ["plan", "strategy", "approach"]):
            return "planning"
        elif any(word in problem_lower for word in ["why", "cause", "effect", "because"]):
            return "causal"
        elif any(word in problem_lower for word in ["like", "similar to", "analogy"]):
            return "analogical"
        elif any(word in problem_lower for word in ["diagnose", "problem", "issue", "wrong"]):
            return "diagnostic"
        elif any(word in problem_lower for word in ["creative", "imagine", "design"]):
            return "creative"
        else:
            return "logical"

    def evaluate_reasoning(
        self, reasoning: str, reasoning_steps: List[str]
    ) -> Dict[str, Any]:
        """Evaluate quality of reasoning"""
        if not reasoning and not reasoning_steps:
            return {
                "quality_score": 0.0,
                "issues": ["No reasoning provided"],
                "strengths": [],
            }

        quality_score = 0.5  # Base score
        issues = []
        strengths = []

        # Check reasoning length
        reasoning_text = reasoning or " ".join(reasoning_steps)
        if len(reasoning_text) > 100:
            quality_score += 0.1
            strengths.append("Detailed reasoning")
        else:
            issues.append("Reasoning too brief")

        # Check for logical connectors
        logical_words = ["therefore", "because", "since", "thus", "hence", "consequently"]
        has_logical_connectors = any(word in reasoning_text.lower() for word in logical_words)
        if has_logical_connectors:
            quality_score += 0.1
            strengths.append("Uses logical connectors")
        else:
            issues.append("Missing logical connectors")

        # Check for multiple steps
        if len(reasoning_steps) >= 3:
            quality_score += 0.1
            strengths.append("Multi-step reasoning")
        elif len(reasoning_steps) < 2:
            issues.append("Insufficient reasoning steps")

        # Check for conclusion
        if "conclusion" in reasoning_text.lower() or "therefore" in reasoning_text.lower():
            quality_score += 0.1
            strengths.append("Has clear conclusion")
        else:
            issues.append("Missing clear conclusion")

        # Normalize score
        quality_score = min(1.0, max(0.0, quality_score))

        return {
            "quality_score": quality_score,
            "issues": issues,
            "strengths": strengths,
            "evaluation": "high" if quality_score > 0.7 else "medium" if quality_score > 0.4 else "low",
        }

    def detect_contradictions(
        self, reasoning_steps: List[str]
    ) -> Dict[str, Any]:
        """Detect contradictions in reasoning steps"""
        if not reasoning_steps or len(reasoning_steps) < 2:
            return {
                "contradictions": [],
                "contradiction_count": 0,
            }

        contradictions = []

        # Check for opposing statements
        positive_words = ["yes", "true", "correct", "right", "agree", "support"]
        negative_words = ["no", "false", "incorrect", "wrong", "disagree", "oppose"]

        for i, step1 in enumerate(reasoning_steps):
            step1_lower = step1.lower()
            for j, step2 in enumerate(reasoning_steps[i + 1 :], i + 1):
                step2_lower = step2.lower()

                # Check for direct contradictions
                has_positive = any(word in step1_lower for word in positive_words)
                has_negative = any(word in step2_lower for word in negative_words)

                if has_positive and has_negative:
                    # Check if they refer to similar concepts
                    step1_words = set(re.findall(r"\b\w{4,}\b", step1_lower))
                    step2_words = set(re.findall(r"\b\w{4,}\b", step2_lower))
                    overlap = step1_words & step2_words

                    if len(overlap) >= 2:  # Significant overlap
                        contradictions.append(
                            {
                                "step1_index": i,
                                "step1": step1,
                                "step2_index": j,
                                "step2": step2,
                                "type": "direct_contradiction",
                                "overlap": list(overlap),
                            }
                        )

        return {
            "contradictions": contradictions,
            "contradiction_count": len(contradictions),
        }

    def resolve_contradictions(
        self, contradictions: List[Dict[str, Any]], reasoning_steps: List[str]
    ) -> Dict[str, Any]:
        """Resolve contradictions in reasoning"""
        if not contradictions:
            return {
                "resolved": True,
                "resolved_contradictions": [],
                "updated_reasoning_steps": reasoning_steps,
            }

        resolved_contradictions = []
        updated_steps = reasoning_steps.copy()

        for contradiction in contradictions:
            step1_idx = contradiction["step1_index"]
            step2_idx = contradiction["step2_index"]

            # Resolution strategy: keep the more recent step or the one with more context
            if step2_idx > step1_idx:
                # Remove or modify step1
                updated_steps[step1_idx] = f"[Modified] {updated_steps[step1_idx]}"
                resolved_contradictions.append(
                    {
                        "contradiction": contradiction,
                        "resolution": "kept_later_step",
                        "modified_step": step1_idx,
                    }
                )
            else:
                # Remove or modify step2
                updated_steps[step2_idx] = f"[Modified] {updated_steps[step2_idx]}"
                resolved_contradictions.append(
                    {
                        "contradiction": contradiction,
                        "resolution": "kept_earlier_step",
                        "modified_step": step2_idx,
                    }
                )

        return {
            "resolved": True,
            "resolved_contradictions": resolved_contradictions,
            "updated_reasoning_steps": updated_steps,
            "resolution_count": len(resolved_contradictions),
        }
    
    def validate_params(self, operation: str, params: Dict[str, Any]) -> bool:
        """Validate parameters for operations"""
        if operation == 'reason' or operation == 'analyze':
            return "query" in params
        elif operation == "compare":
            return "item1" in params and "item2" in params
        elif operation == "multi_step_solve":
            return "problem" in params
        elif operation == "causal_reasoning":
            return "event" in params
        elif operation == "analogical_reasoning":
            return "source" in params and "target" in params
        elif operation == "deep_analysis":
            return "query" in params
        else:
            return True
