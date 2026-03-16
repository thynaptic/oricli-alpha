from __future__ import annotations
"""
Formal Verification Bridge Module

Translates Python code into a formal proof language (Lean 4) and attempts
to formally verify its correctness (e.g., termination, bounds checking, functional equivalence).
"""

import logging
import re
from typing import Dict, Any

from oricli_core.brain.base_module import BaseBrainModule, ModuleMetadata
from oricli_core.exceptions import InvalidParameterError

logger = logging.getLogger(__name__)

class FormalVerificationBridge(BaseBrainModule):
    """Translates code to Lean 4 and verifies proofs."""

    def __init__(self):
        super().__init__()
        self.is_initialized = False

    @property
    def metadata(self) -> ModuleMetadata:
        return ModuleMetadata(
            name="formal_verification_bridge",
            version="1.0.0",
            description="Translates code to Lean 4 and attempts formal verification.",
            operations=[
                "translate_to_lean",
                "verify_proof",
                "formalize_and_verify"
            ],
            dependencies=[],
            model_required=False,
        )

    def initialize(self) -> bool:
        self.is_initialized = True
        return True

    def execute(self, operation: str, params: Dict[str, Any]) -> Dict[str, Any]:
        if not self.is_initialized:
            self.initialize()

        if operation == "translate_to_lean":
            return self._translate_to_lean(params)
        elif operation == "verify_proof":
            return self._verify_proof(params)
        elif operation == "formalize_and_verify":
            return self._formalize_and_verify(params)
        else:
            raise InvalidParameterError("operation", operation, "Unknown operation")

    def _translate_to_lean(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """Translate Python source code to Lean 4 def + theorem + tactic proof via LLM.
        Returns dict with success, lean_code (on success), or error (on failure).
        """
        source_code = params.get("source_code")
        if not source_code:
            raise InvalidParameterError("source_code", str(source_code), "source_code is required")
            
        try:
            from oricli_core.brain.registry import ModuleRegistry
            ModuleRegistry.discover_modules()
            cog_gen = ModuleRegistry.get_module("cognitive_generator")
            
            if not cog_gen:
                return {"success": False, "error": "cognitive_generator not available"}
                
            prompt = f"""
            Translate the following Python code into a Lean 4 `def`.
            Then, write a formal specification (theorem) for what the function is supposed to do.
            Finally, write the Lean 4 tactic proof to prove the theorem.
            
            Python Code:
            ```python
            {source_code}
            ```
            
            CRITICAL INSTRUCTIONS:
            - Output ONLY the Lean 4 code.
            - Do NOT include any conversational text, greetings, or explanations.
            - Do NOT include your thought process.
            - The output must start with ```lean and end with ```.
            - The Lean code should be self-contained and ready to be compiled.
            """
            
            # Prefer direct ollama to avoid cognitive_generator system prompt (which can cause code-only tasks to return filler).
            ollama = ModuleRegistry.get_module("ollama_provider")
            if ollama:
                system_prompt = "You are a strict code generator. Output ONLY valid Lean 4 code inside a markdown block. No explanations. Start with ```lean and end with ```."
                res = ollama.execute("generate", {
                    "prompt": system_prompt + "\n\n" + prompt,
                    "temperature": 0.1,
                    "max_tokens": 1000
                })
                output_text = res.get("text", "") if res.get("success") else ""
                if not output_text and not res.get("success"):
                    return {"success": False, "error": res.get("error", "Ollama generation failed or timed out")}
            else:
                res = cog_gen.execute("generate_response", {
                    "input": prompt,
                    "temperature": 0.1,
                    "timeout": 120
                })
                output_text = res.get("text", "")

            # Extract code block (accept ```lean or ```lean4)
            code_match = re.search(r"```(?:lean|lean4)?\s*\n(.*?)```", output_text, re.DOTALL)
            lean_code = (code_match.group(1).strip() if code_match else output_text.strip()) if output_text else ""
            if not lean_code or len(lean_code) < 10:
                return {
                    "success": False,
                    "error": "Model returned no valid Lean code (empty or too short). Try again or use a model that follows code-only instructions.",
                    "lean_code": ""
                }
            return {
                "success": True,
                "lean_code": lean_code
            }
            
        except Exception as e:
            logger.error(f"Error in translate_to_lean: {e}")
            return {"success": False, "error": str(e)}

    def _verify_proof(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """Verify Lean 4 code: run lean compiler in sandbox if available, else LLM semantic check.
        Returns dict with success, verification_status, method, and optional error/output.
        """
        lean_code = params.get("lean_code") or ""
        if not lean_code or not lean_code.strip():
            return {
                "success": False,
                "verification_status": "Skipped",
                "error": "lean_code is required and must be non-empty.",
                "method": "none"
            }
            
        try:
            from oricli_core.brain.registry import ModuleRegistry
            sandbox = ModuleRegistry.get_module("shell_sandbox_service")
            cog_gen = ModuleRegistry.get_module("cognitive_generator")
            
            # Try to run lean via sandbox if available (quoted delimiter => no expansion of body)
            if sandbox:
                delimiter = "__LEAN_VERIFY_EOF__"
                if delimiter in lean_code:
                    logger.warning("Lean code contains heredoc delimiter; verification may be unreliable")
                check_script = f"""
                source $HOME/.elan/env
                if command -v lean >/dev/null 2>&1; then
                    cat << '{delimiter}' > test_proof.lean
{lean_code}
{delimiter}
                    lean test_proof.lean
                    exit $?
                else
                    echo "LEAN_NOT_INSTALLED"
                    exit 127
                fi
                """
                
                sb_res = sandbox.execute("execute_safe_command", {"command": check_script, "timeout": 15})
                
                if sb_res.get("success") and "LEAN_NOT_INSTALLED" not in sb_res.get("output", ""):
                    # Lean is installed and ran
                    exit_code = sb_res.get("exit_code", 1)
                    if exit_code == 0:
                        return {
                            "success": True,
                            "verification_status": "Proven",
                            "method": "lean_compiler",
                            "output": sb_res.get("output", "")
                        }
                    else:
                        return {
                            "success": False,
                            "verification_status": "Failed",
                            "method": "lean_compiler",
                            "error": sb_res.get("output", "")
                        }
                        
            # Fallback: LLM Strict Semantic Check
            if cog_gen:
                prompt = f"""
                You are a strict Lean 4 compiler and formal verification engine.
                Analyze the following Lean 4 code and proof.
                Determine if the proof is logically sound and mathematically valid.
                
                Lean Code:
                ```lean
                {lean_code}
                ```
                
                If the proof is completely valid, respond with exactly: "VERIFICATION_STATUS: PROVEN"
                If there are logical holes, syntax errors, or unproven goals, respond with "VERIFICATION_STATUS: FAILED" followed by a detailed explanation of the error.
                """
                
                res = cog_gen.execute("generate_response", {
                    "input": prompt,
                    "temperature": 0.1,
                    "timeout": 120
                })
                output_text = res.get("text", "") or ""
                if not output_text:
                    return {
                        "success": False,
                        "verification_status": "Failed",
                        "method": "llm_semantic_check",
                        "error": "LLM verification returned no response (timeout or empty)."
                    }
                if "VERIFICATION_STATUS: PROVEN" in output_text:
                    return {
                        "success": True,
                        "verification_status": "LLM-Verified",
                        "method": "llm_semantic_check",
                        "output": output_text
                    }
                else:
                    return {
                        "success": False,
                        "verification_status": "Failed",
                        "method": "llm_semantic_check",
                        "error": output_text
                    }
                    
            return {"success": False, "error": "No verification method available"}
            
        except Exception as e:
            logger.error(f"Error in verify_proof: {e}")
            return {"success": False, "error": str(e)}

    def _formalize_and_verify(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """Full pipeline: translate source_code to Lean, then verify; retry with fix on failure.
        Returns dict with success, verification_status, method, lean_code, attempts.
        """
        source_code = params.get("source_code")
        if not source_code:
            raise InvalidParameterError("source_code", str(source_code), "source_code is required")
            
        max_retries = params.get("max_retries", 1)
        
        # Initial translation
        trans_res = self._translate_to_lean({"source_code": source_code})
        if not trans_res.get("success"):
            return trans_res
            
        lean_code = trans_res.get("lean_code")
        
        # Verification loop
        for attempt in range(max_retries + 1):
            ver_res = self._verify_proof({"lean_code": lean_code})
            
            if ver_res.get("success"):
                return {
                    "success": True,
                    "verification_status": ver_res.get("verification_status"),
                    "method": ver_res.get("method"),
                    "lean_code": lean_code,
                    "attempts": attempt + 1
                }
                
            # If failed and we have retries left, try to fix it
            if attempt < max_retries:
                try:
                    from oricli_core.brain.registry import ModuleRegistry
                    cog_gen = ModuleRegistry.get_module("cognitive_generator")
                    
                    if cog_gen:
                        error_msg = ver_res.get("error", "Unknown error")
                        fix_prompt = f"""
                        The following Lean 4 proof failed verification.
                        
                        Original Code:
                        ```lean
                        {lean_code}
                        ```
                        
                        Error:
                        {error_msg}
                        
                        Please fix the Lean 4 code and proof.
                        
                        CRITICAL INSTRUCTIONS:
                        - Output ONLY the corrected Lean 4 code.
                        - Do NOT include any conversational text, greetings, or explanations.
                        - Do NOT include your thought process.
                        - The output must start with ```lean and end with ```.
                        """
                        
                        ollama = ModuleRegistry.get_module("ollama_provider")
                        if ollama:
                            fix_res = ollama.execute("generate", {
                                "prompt": fix_prompt,
                                "temperature": 0.1,
                                "max_tokens": 1000
                            })
                            output_text = fix_res.get("text", "") if fix_res.get("success") else ""
                        else:
                            fix_res = cog_gen.execute("generate_response", {"input": fix_prompt})
                            output_text = fix_res.get("text", "")
                        code_match = re.search(r"```(?:lean|lean4)?\s*\n(.*?)```", output_text or "", re.DOTALL)
                        new_lean = (code_match.group(1).strip() if code_match else (output_text or "").strip())
                        if new_lean and len(new_lean) >= 10:
                            lean_code = new_lean
                except Exception as e:
                    logger.error(f"Error during proof fix attempt: {e}")
                    
        # If we exhausted retries and still failed
        return {
            "success": False,
            "verification_status": "Failed",
            "error": ver_res.get("error"),
            "lean_code": lean_code,
            "attempts": max_retries + 1
        }
