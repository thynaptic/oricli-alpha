import unittest
from oricli_core.brain.modules.oricli_system_prompt_builder import Oricli-AlphaSystemPromptBuilderModule

class TestOricli-AlphaSystemPromptBuilder(unittest.TestCase):
    def setUp(self):
        self.module = Oricli-AlphaSystemPromptBuilderModule()
        self.module.initialize()

    def test_standard_prompt(self):
        # Test building standard prompt
        params = {
            "personality_id": "Oricli-Alpha",
            "task_execution": False
        }
        result = self.module.execute("build_system_prompt", params)
        self.assertTrue(result["success"])
        prompt = result["result"]["prompt"]
        
        self.assertIn("CORE IDENTITY:", prompt)
        self.assertIn("helpful, intelligent conversation partner", prompt)
        self.assertIn("PERSONALITY: Oricli-Alpha", prompt)
        self.assertIn("CORE CAPABILITIES:", prompt)
        self.assertIn("BEHAVIORAL GUIDELINES:", prompt)

    def test_task_execution_prompt(self):
        # Test building high-precision task prompt
        params = {
            "personality_id": "Oricli-Alpha",
            "task_execution": True
        }
        result = self.module.execute("build_system_prompt", params)
        self.assertTrue(result["success"])
        prompt = result["result"]["prompt"]
        
        self.assertIn("CORE IDENTITY: TASK EXECUTION MODE", prompt)
        self.assertIn("ZERO FILLER", prompt)
        self.assertIn("RAW OUTPUT ONLY", prompt)
        self.assertIn("STRICT ADHERENCE", prompt)
        
        # Identity and general guidelines should be suppressed
        self.assertNotIn("helpful, intelligent conversation partner", prompt)
        self.assertNotIn("PERSONALITY: Oricli-Alpha", prompt)
        self.assertNotIn("CORE CAPABILITIES:", prompt)
        self.assertNotIn("BEHAVIORAL GUIDELINES:", prompt)

    def test_build_task_execution_section(self):
        # Test building just the task section
        params = {"section_type": "task_execution"}
        result = self.module.execute("build_section", params)
        self.assertTrue(result["success"])
        section = result["result"]["section"]
        self.assertIn("TASK EXECUTION MODE", section)
        self.assertIn("CRITICAL CONSTRAINTS", section)

if __name__ == "__main__":
    unittest.main()
