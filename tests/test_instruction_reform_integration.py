import unittest
import sys
import os
from mavaia_core.brain.registry import ModuleRegistry

class TestInstructionReformIntegration(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        # Ensure modules are discovered
        ModuleRegistry.discover_modules(verbose=False)
        cls.cog_gen = ModuleRegistry.get_module("cognitive_generator")
        cls.cog_gen.initialize()

    def test_instruction_bypass_routing(self):
        # A prompt that should trigger the hard bypass
        prompt = "please convert this table to json: <table><tr><td>val</td></tr></table>"
        
        result = self.cog_gen.execute(
            operation="generate_response",
            params={
                "input": prompt,
                "context": "Benchmarking data analysis.",
            }
        )
        
        if result.get("diagnostic", {}).get("generation_method") != "instruction_following_bypass":
            from pprint import pprint
            print("\nDEBUG RESULT:")
            pprint(result)

        self.assertTrue(result.get("success"), f"Generation failed: {result.get('error')}")
        
        # Verify it used the bypass method
        diagnostic = result.get("diagnostic", {})
        self.assertEqual(diagnostic.get("generation_method"), "instruction_following_bypass")
        self.assertTrue(diagnostic.get("high_precision_task"))
        self.assertIn("json", diagnostic.get("matched_keywords", []))

    def test_standard_conversational_routing(self):
        # A standard conversational prompt that should NOT trigger the bypass
        prompt = "Hello Mavaia, how are you today?"
        
        result = self.cog_gen.execute(
            operation="generate_response",
            params={
                "input": prompt,
            }
        )
        
        self.assertTrue(result.get("success"))
        
        # Verify it did NOT use the bypass method
        diagnostic = result.get("diagnostic", {})
        self.assertNotEqual(diagnostic.get("generation_method"), "instruction_following_bypass")
        self.assertFalse(diagnostic.get("high_precision_task", False))

if __name__ == "__main__":
    # Add project root to path
    sys.path.insert(0, os.path.abspath(os.getcwd()))
    unittest.main()
