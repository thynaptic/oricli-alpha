#!/usr/bin/env python3
"""
OricliAlpha Cognitive Engine - General Purpose Query Interface

This script provides a complete interface to query OricliAlpha using the full
cognitive generator system, which orchestrates ALL modules in oricli_core/brain/modules/
dynamically based on intent detection and module discovery.

Usage:
    python3 test_mona_lisa_query.py [query]
    
    If no query is provided, uses default: "What is sfumato?"
    
    Examples:
        python3 test_mona_lisa_query.py "Why is the sky blue?"
        python3 test_mona_lisa_query.py "Calculate 15 * 23"
        python3 test_mona_lisa_query.py "What is machine learning?"

Features:
1. Full module orchestration via cognitive_generator
2. Dynamic intent detection and routing
3. Automatic module discovery (any new modules are automatically included)
4. Verification layer and reflection loop
5. Trace graph logging of module execution path
6. Comprehensive result analysis

Output includes:
- Intent detection and routing information
- Module execution path (which modules were used)
- Verification results
- Final synthesized answer
- Breakdown of what worked and what didn't
"""

import json
import sys
from pathlib import Path
from typing import Any, Dict

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent))

from oricli_core import OricliAlphaClient


def format_reasoning_trace(result: Dict[str, Any], indent: int = 0) -> str:
    """Format reasoning trace for display"""
    indent_str = "  " * indent
    output = []
    
    # Handle direct result structure (from chain_of_thought)
    if "steps" in result:
        output.append(f"{indent_str}Reasoning Steps:")
        for i, step in enumerate(result["steps"], 1):
            if isinstance(step, dict):
                output.append(f"{indent_str}  Step {i}:")
                if "prompt" in step:
                    output.append(f"{indent_str}    Prompt: {step['prompt'][:200]}...")
                if "reasoning" in step:
                    output.append(f"{indent_str}    Reasoning: {step['reasoning']}")
                if "thought" in step:
                    output.append(f"{indent_str}    Thought: {step['thought']}")
                if "confidence" in step:
                    output.append(f"{indent_str}    Confidence: {step['confidence']}")
            else:
                output.append(f"{indent_str}  Step {i}: {step}")
    
    # Check for total_reasoning
    if "total_reasoning" in result:
        output.append(f"{indent_str}Total Reasoning:")
        output.append(f"{indent_str}  {result['total_reasoning']}")
    
    # Check for reasoning field
    if "reasoning" in result:
        output.append(f"{indent_str}Reasoning:")
        output.append(f"{indent_str}  {result['reasoning']}")
    
    # Extract reasoning steps from nested result structures
    if "result" in result:
        result_data = result["result"]
        
        # Check for CoT steps
        if "steps" in result_data:
            output.append(f"{indent_str}CoT Steps:")
            for i, step in enumerate(result_data["steps"], 1):
                if isinstance(step, dict):
                    output.append(f"{indent_str}  Step {i}:")
                    if "thought" in step:
                        output.append(f"{indent_str}    Thought: {step['thought']}")
                    if "confidence" in step:
                        output.append(f"{indent_str}    Confidence: {step['confidence']}")
                    if "reasoning" in step:
                        output.append(f"{indent_str}    Reasoning: {step['reasoning']}")
                    if "prompt" in step:
                        output.append(f"{indent_str}    Prompt: {step['prompt'][:200]}...")
                else:
                    output.append(f"{indent_str}  Step {i}: {step}")
        
        # Check for total_reasoning
        if "total_reasoning" in result_data:
            output.append(f"{indent_str}Total Reasoning:")
            output.append(f"{indent_str}  {result_data['total_reasoning']}")
        
        # Check for reasoning_result (from orchestrator)
        if "reasoning_result" in result_data:
            reasoning_result = result_data["reasoning_result"]
            if isinstance(reasoning_result, dict):
                reasoning_type = reasoning_result.get("type", "unknown")
                output.append(f"{indent_str}Reasoning Type: {reasoning_type}")
                
                if "result" in reasoning_result:
                    nested_result = reasoning_result["result"]
                    if isinstance(nested_result, dict):
                        if "result" in nested_result:
                            nested_data = nested_result["result"]
                            if "steps" in nested_data:
                                output.append(f"{indent_str}  Steps:")
                                for i, step in enumerate(nested_data["steps"], 1):
                                    if isinstance(step, dict):
                                        output.append(f"{indent_str}    Step {i}:")
                                        if "thought" in step:
                                            output.append(f"{indent_str}      Thought: {step['thought']}")
                                        if "confidence" in step:
                                            output.append(f"{indent_str}      Confidence: {step['confidence']}")
                                        if "reasoning" in step:
                                            output.append(f"{indent_str}      Reasoning: {step['reasoning']}")
                                    else:
                                        output.append(f"{indent_str}    Step {i}: {step}")
                            if "total_reasoning" in nested_data:
                                output.append(f"{indent_str}  Total Reasoning:")
                                output.append(f"{indent_str}    {nested_data['total_reasoning']}")
    
    if not output:
        output.append(f"{indent_str}(No reasoning trace found in result structure)")
        output.append(f"{indent_str}Available keys: {list(result.keys())}")
    
    return "\n".join(output)


def is_placeholder_answer(answer: Any) -> bool:
    """Check if an answer is truly a placeholder or extraction error"""
    if not answer:
        return True
    
    answer_str = str(answer).strip()
    
    # Empty or just whitespace
    if not answer_str:
        return True
    
    # Single digit or very short number (1-99)
    if answer_str.isdigit() and len(answer_str) <= 2:
        return True
    
    # Common placeholder values
    if answer_str.lower() in ["none", "n/a", "null", "undefined", "error", "failed"]:
        return True
    
    # Very short answers that are likely placeholders (less than 10 chars and no meaningful words)
    if len(answer_str) < 10:
        # Check if it's just punctuation or single words that aren't meaningful
        words = answer_str.split()
        if len(words) <= 1 and not any(char.isalpha() for char in answer_str):
            return True
    
    return False


def analyze_what_worked(result: Dict[str, Any]) -> Dict[str, Any]:
    """Analyze what worked and what didn't in the reasoning process"""
    analysis = {
        "worked": [],
        "didnt_work": [],
        "why_didnt_work": [],
        "issues": [],
        "confidence": None,
        "reasoning_method": None,
    }
    
    # Check cognitive_generator result structure
    if result.get("success"):
        analysis["worked"].append("Cognitive generation succeeded")
        
        # Check intent and routing
        intent_info = result.get("intent", {})
        if intent_info:
            intent = intent_info.get("intent", "unknown")
            analysis["worked"].append(f"Intent detected: {intent}")
            routing_method = intent_info.get("routing_method", "unknown")
            analysis["worked"].append(f"Routing method: {routing_method}")
        
        # Check trace graph
        trace_graph = result.get("trace_graph")
        if trace_graph:
            execution_path = trace_graph.get("execution_path", [])
            if execution_path:
                analysis["worked"].append(f"Executed {len(execution_path)} modules")
        
        # Check verification
        verification = result.get("verification", {})
        if verification:
            matches = verification.get("matches_intent", False)
            if matches:
                analysis["worked"].append("Verification passed: output matches intent")
            else:
                analysis["didnt_work"].append("Final output failed intent verification")
                analysis["issues"].append("Verification failed: output doesn't match intent")

                structural = verification.get("structural_checks") or {}
                if isinstance(structural, dict):
                    failed_checks = [k for k, v in structural.items() if v is False]
                    for k in failed_checks:
                        analysis["why_didnt_work"].append(f"Verifier check failed: {k}")

                issues = verification.get("issues", [])
                for issue in issues:
                    analysis["issues"].append(f"Verification issue: {issue}")
                if issues:
                    joined = "; ".join(str(i) for i in issues)
                    analysis["why_didnt_work"].append(f"Verifier issues: {joined}")
        
        # Check structural confidence
        structural_confidence = result.get("structural_confidence", {})
        if structural_confidence:
            conf = structural_confidence.get("confidence", 0.0)
            analysis["confidence"] = conf

        diagnostic = result.get("diagnostic", {})
        if isinstance(diagnostic, dict):
            if diagnostic.get("is_fallback"):
                analysis["didnt_work"].append("Generation fell back to a generic response path")
                analysis["why_didnt_work"].append("Primary generation path did not produce a usable answer; fallback was used")
            gen_method = diagnostic.get("generation_method")
            if gen_method and gen_method != "unknown":
                analysis["worked"].append(f"Generation method: {gen_method}")
            for w in diagnostic.get("warnings", []) or []:
                analysis["issues"].append(f"Warning: {w}")
            for err in diagnostic.get("errors", []) or []:
                analysis["issues"].append(f"Error: {err}")
                analysis["why_didnt_work"].append(f"Error encountered during generation: {err}")
    
    # Check direct result structure (chain_of_thought format)
    if "steps" in result:
        steps = result["steps"]
        if steps:
            analysis["worked"].append(f"Generated {len(steps)} reasoning steps")
            # Check step quality
            for i, step in enumerate(steps, 1):
                if isinstance(step, dict):
                    if step.get("reasoning") or step.get("thought"):
                        analysis["worked"].append(f"Step {i} has reasoning content")
                    else:
                        analysis["didnt_work"].append(f"Step {i} missing reasoning content")
    
    if "confidence" in result:
        analysis["confidence"] = result["confidence"]
    
    if "result" in result:
        result_data = result["result"]
        
        # Extract confidence
        if analysis["confidence"] is None:
            analysis["confidence"] = result_data.get("confidence", None)
        analysis["reasoning_method"] = result_data.get("reasoning_method", None)
        
        # Check for successful reasoning steps
        if "reasoning_result" in result_data:
            reasoning_result = result_data["reasoning_result"]
            if isinstance(reasoning_result, dict) and "result" in reasoning_result:
                nested_result = reasoning_result["result"]
                if isinstance(nested_result, dict) and "result" in nested_result:
                    nested_data = nested_result["result"]
                    if "steps" in nested_data:
                        steps = nested_data["steps"]
                        if steps:
                            analysis["worked"].append(f"Generated {len(steps)} reasoning steps")
                            # Check step quality
                            for i, step in enumerate(steps, 1):
                                if isinstance(step, dict):
                                    if step.get("thought"):
                                        analysis["worked"].append(f"Step {i} has reasoning content")
                                    else:
                                        analysis["didnt_work"].append(f"Step {i} missing reasoning content")
        
        # Check for final answer
        final_answer = result_data.get("answer") or result_data.get("final_answer")
        if final_answer:
            analysis["worked"].append("Generated final answer")
            # Check if answer is meaningful (not a placeholder)
            if is_placeholder_answer(final_answer):
                analysis["issues"].append(f"Final answer appears to be a placeholder: '{final_answer}'")
        else:
            analysis["didnt_work"].append("No final answer generated")
        
        # Check for cascade usage
        if result_data.get("cascade_used"):
            analysis["worked"].append("Model cascading was used to improve confidence")
        
        # Check for verification
        if result_data.get("verification_result"):
            analysis["worked"].append("Self-verification was performed")
    
    # Check direct final_answer field
    if not analysis["worked"] or "Generated final answer" not in str(analysis["worked"]):
        final_answer = result.get("final_answer") or result.get("answer")
        if final_answer:
            analysis["worked"].append("Generated final answer")
            if is_placeholder_answer(final_answer):
                analysis["issues"].append(f"Final answer appears to be a placeholder: '{final_answer}'")
    
    # Check confidence level
    confidence = analysis["confidence"]
    if confidence is not None:
        if confidence >= 0.7:
            analysis["worked"].append(f"High confidence ({confidence:.2f})")
        elif confidence >= 0.5:
            analysis["issues"].append(f"Moderate confidence ({confidence:.2f})")
        else:
            analysis["didnt_work"].append(f"Low confidence ({confidence:.2f})")
    
    if analysis["didnt_work"] and not analysis.get("why_didnt_work"):
        analysis["why_didnt_work"].append("No explicit causal diagnostics were available; review verifier issues, diagnostic warnings, and trace graph.")

    return analysis


def extract_final_answer(result: Dict[str, Any]) -> str | None:
    """
    Extract final answer from various result structures.
    Handles nested structures from different modules.
    """
    # Try direct fields first
    final_answer = (
        result.get("text") or
        result.get("response") or
        result.get("answer") or
        result.get("final_answer") or
        result.get("conclusion")
    )
    
    if final_answer:
        return str(final_answer).strip()
    
    # Try nested result structure
    if "result" in result:
        result_data = result["result"]
        final_answer = (
            result_data.get("text") or
            result_data.get("response") or
            result_data.get("answer") or
            result_data.get("final_answer") or
            result_data.get("conclusion") or
            result_data.get("total_reasoning") or
            result_data.get("reasoning")
        )
        
        if final_answer:
            return str(final_answer).strip()
        
        # Try deeper nesting (chain_of_thought format)
        if "result" in result_data:
            nested = result_data["result"]
            final_answer = (
                nested.get("final_answer") or
                nested.get("answer") or
                nested.get("total_reasoning") or
                nested.get("reasoning")
            )
            if final_answer:
                return str(final_answer).strip()
    
    return None


def display_cognitive_generator_result(result: Dict[str, Any], query: str) -> None:
    """Display results from cognitive_generator.generate_response()"""
    print("=" * 80)
    print("LAYER 1: COGNITIVE GENERATOR OUTPUT")
    print("=" * 80)
    
    # Display intent and routing information
    intent_info = result.get("intent", {})
    if intent_info:
        print(f"Intent: {intent_info.get('intent', 'unknown')}")
        print(f"Confidence: {intent_info.get('confidence', 0.0):.2f}")
        print(f"Routing Method: {intent_info.get('routing_method', 'unknown')}")
        recommended = intent_info.get("recommended_modules", [])
        if recommended:
            print(f"Recommended Modules: {', '.join(recommended[:5])}")
            if len(recommended) > 5:
                print(f"  ... and {len(recommended) - 5} more")
    
    # Display trace graph if available
    trace_graph = result.get("trace_graph")
    if trace_graph:
        execution_path = trace_graph.get("execution_path", [])
        if execution_path:
            print(f"\nModule Execution Path ({len(execution_path)} modules):")
            for i, node_id in enumerate(execution_path[:10], 1):
                print(f"  {i}. {node_id}")
            if len(execution_path) > 10:
                print(f"  ... and {len(execution_path) - 10} more modules")
    
    # Display verification results
    verification = result.get("verification", {})
    if verification:
        matches = verification.get("matches_intent", False)
        confidence = verification.get("confidence", 0.0)
        issues = verification.get("issues", [])
        print(f"\nVerification: {'✓ Matches Intent' if matches else '✗ Does Not Match Intent'}")
        print(f"Confidence: {confidence:.2f}")
        if issues:
            print("Issues:")
            for issue in issues:
                print(f"  ⚠ {issue}")
    
    # Display web verification if present
    web_verification = result.get("web_verification")
    if web_verification:
        verified = web_verification.get("verified", False)
        web_conf = web_verification.get("confidence", 0.0)
        web_issues = web_verification.get("issues", [])
        source_quality = web_verification.get("source_quality", {})
        print(f"\nWeb Content Verification: {'✓ Verified' if verified else '✗ Not Verified'}")
        print(f"Confidence: {web_conf:.2f}")
        if source_quality.get("source_count", 0) > 0:
            print(f"Sources: {source_quality['source_count']}")
            if source_quality.get("has_reputable_source"):
                print("  ✓ Includes reputable sources")
        if web_issues:
            print("Issues:")
            for issue in web_issues:
                print(f"  ⚠ {issue}")
    
    print("\n" + "=" * 80)
    print("LAYER 2: FINAL SYNTHESIZED ANSWER")
    print("=" * 80)
    
    final_answer = extract_final_answer(result)
    if final_answer:
        print(final_answer)
        if is_placeholder_answer(final_answer):
            print("\n⚠ WARNING: Final answer appears to be a placeholder or extraction error.")
    else:
        print("No final answer found in result structure")
        print("\nAvailable keys:", list(result.keys()))
    
    print("\n" + "=" * 80)
    print("LAYER 3: BREAKDOWN - WHAT WORKED AND WHAT DIDN'T")
    print("=" * 80)
    
    analysis = analyze_what_worked(result)
    confidence = analysis.get("confidence")
    if confidence is not None:
        print(f"Confidence: {confidence:.2f}")
    
    print("\nWhat Worked:")
    if analysis["worked"]:
        for item in analysis["worked"]:
            print(f"  ✓ {item}")
    else:
        print("  (None identified)")
    
    print("\nWhat Didn't Work:")
    if analysis["didnt_work"]:
        for item in analysis["didnt_work"]:
            print(f"  ✗ {item}")
    else:
        print("  (None identified)")

    print("\nWhy It Didn't Work:")
    why = analysis.get("why_didnt_work", [])
    if why:
        for item in why:
            print(f"  → {item}")
    else:
        print("  (None identified)")
    
    print("\nIssues/Concerns:")
    if analysis["issues"]:
        for item in analysis["issues"]:
            print(f"  ⚠ {item}")
    else:
        print("  (None identified)")


def main():
    """Main function to execute the query and display results"""
    import sys
    
    # Allow query to be passed as command-line argument, or use default
    if len(sys.argv) > 1:
        query = " ".join(sys.argv[1:])
    else:
        query = "What is sfumato?"
    
    print("=" * 80)
    print("MAVAI COGNITIVE ENGINE - FULL MODULE ORCHESTRATION")
    print("=" * 80)
    print(f"\nQuery: {query}\n")
    
    try:
        # Initialize client
        print("Initializing OricliAlpha client...")
        client = OricliAlphaClient()
        print("Client initialized successfully.\n")
        
        # PRIMARY METHOD: Use cognitive_generator which orchestrates ALL modules
        print("Using cognitive_generator (full module orchestration)...\n")
        try:
            # Use voice_context instead of persona (new universal voice system)
            result = client.brain.cognitive_generator.generate_response(
                input=query,
                context="",
                voice_context={
                    "base_personality": "oricli",
                    "tone": "neutral",
                    "formality_level": 0.5,
                    "technical_level": 0.3,
                    "empathy_level": 0.6,
                    "conversation_topic": "general",
                    "user_history": [],
                    "adaptation_confidence": 0.5,
                }
            )
            
            print("✓ Successfully executed cognitive generation\n")
            display_cognitive_generator_result(result, query)
            
            # Save full result
            output_file = "oricli_result.json"
            with open(output_file, "w") as f:
                json.dump(result, f, indent=2, default=str)
            print(f"\nFull result saved to: {output_file}\n")
            
        except Exception as e:
            print(f"✗ cognitive_generator failed: {e}\n")
            import traceback
            traceback.print_exc()
            print("\nFalling back to chain_of_thought...\n")
            
            # Fallback 1: chain_of_thought
            try:
                result = client.brain.chain_of_thought.execute_cot(
                    query=query,
                    context="",
                    configuration={"max_steps": 5},
                    session_id="oricli_test"
                )
                
                print("✓ Successfully executed chain-of-thought\n")
                
                print("=" * 80)
                print("LAYER 1: RAW INTERNAL REASONING TRACE")
                print("=" * 80)
                print(format_reasoning_trace(result))
                print("\n")
                
                print("=" * 80)
                print("LAYER 2: FINAL SYNTHESIZED ANSWER")
                print("=" * 80)
                final_answer = extract_final_answer(result)
                if final_answer:
                    print(final_answer)
                    if is_placeholder_answer(final_answer):
                        print("\n⚠ WARNING: Final answer appears to be a placeholder or extraction error.")
                else:
                    print("No final answer found")
                    print("\nFull result structure:")
                    print(json.dumps(result, indent=2, default=str))
                print("\n")
                
                print("=" * 80)
                print("LAYER 3: BREAKDOWN - WHAT WORKED AND WHAT DIDN'T")
                print("=" * 80)
                analysis = analyze_what_worked(result)
                print(f"Confidence: {analysis.get('confidence', 'N/A')}")
                print("\nWhat Worked:")
                if analysis["worked"]:
                    for item in analysis["worked"]:
                        print(f"  ✓ {item}")
                else:
                    print("  (None identified)")
                print("\nWhat Didn't Work:")
                if analysis["didnt_work"]:
                    for item in analysis["didnt_work"]:
                        print(f"  ✗ {item}")
                else:
                    print("  (None identified)")

                print("\nWhy It Didn't Work:")
                why = analysis.get("why_didnt_work", [])
                if why:
                    for item in why:
                        print(f"  → {item}")
                else:
                    print("  (None identified)")
                print("\nIssues/Concerns:")
                if analysis["issues"]:
                    for item in analysis["issues"]:
                        print(f"  ⚠ {item}")
                else:
                    print("  (None identified)")
                
                # Save full result
                output_file = "oricli_result.json"
                with open(output_file, "w") as f:
                    json.dump(result, f, indent=2, default=str)
                print(f"\nFull result saved to: {output_file}\n")
                
            except Exception as e2:
                print(f"✗ chain_of_thought also failed: {e2}\n")
                print("No external LLM/chat-completion fallback is permitted in this environment.\n")
                return 1
        
    except Exception as e:
        print(f"Error initializing client: {e}")
        import traceback
        traceback.print_exc()
        return 1
    
    print("=" * 80)
    print("QUERY COMPLETE")
    print("=" * 80)
    return 0


if __name__ == "__main__":
    sys.exit(main())

