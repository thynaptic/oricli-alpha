import unittest

from oricli_core.brain.modules.multi_agent_pipeline import MultiAgentPipeline
from oricli_core.brain.modules.synthesis_agent import SynthesisAgentModule
from oricli_core.exceptions import InvalidParameterError


class TestMultiAgentPipelineSmoke(unittest.TestCase):
    def test_unknown_operation_raises_invalid_parameter_error(self) -> None:
        module = MultiAgentPipeline()
        with self.assertRaises(InvalidParameterError):
            module.execute("no_such_operation", {})

    def test_pipeline_runs_with_partial_agent_availability(self) -> None:
        module = MultiAgentPipeline()
        module.initialize()
        result = module.execute("process_query", {"query": "What is a transformer model?"})
        self.assertIsInstance(result, dict)
        self.assertTrue(result.get("success"))
        self.assertIsInstance(result.get("answer"), str)
        self.assertIn("pipeline_stages", result)

    def test_synthesis_agent_compat_alias(self) -> None:
        module = SynthesisAgentModule()
        result = module.execute("process_synthesis", {"query": "x", "documents": []})
        self.assertTrue(result.get("success"))
        self.assertIn("answer", result)
        self.assertIn("synthesis", result)


if __name__ == "__main__":
    unittest.main()

