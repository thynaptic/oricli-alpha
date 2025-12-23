import unittest


class TestCognitiveTraceDiagnostics(unittest.TestCase):
    def test_trace_pipeline_and_redaction(self) -> None:
        from mavaia_core.brain.modules.cognitive_trace_diagnostics import (
            CognitiveTraceDiagnosticsModule,
        )

        tracer = CognitiveTraceDiagnosticsModule()

        result = tracer.execute(
            "trace_pipeline",
            {
                "trace_id": "unit_test_trace",
                "stop_on_error": True,
                "steps": [
                    {
                        "module": "query_complexity",
                        "operation": "analyze_complexity",
                        "params": {"query": "Explain why the sky is blue."},
                    },
                    {
                        "module": "query_complexity",
                        "operation": "analyze_complexity",
                        "params": {"query": "test", "api_key": "SUPER_SECRET"},
                        "allow_failure": True,
                        "is_fallback": True,
                    },
                ],
            },
        )

        self.assertTrue(result.get("success"))
        trace = result.get("trace")
        self.assertIsInstance(trace, dict)
        self.assertEqual(trace.get("trace_id"), "unit_test_trace")
        self.assertEqual(trace.get("path_length"), 2)
        self.assertIn("steps", trace)
        steps = trace["steps"]
        self.assertEqual(len(steps), 2)

        # Ensure redaction occurs for sensitive keys
        params_summary = steps[1].get("params_summary", {})
        self.assertEqual(params_summary.get("api_key"), "***REDACTED***")

    def test_trace_pipeline_nonfatal_missing_module(self) -> None:
        from mavaia_core.brain.modules.cognitive_trace_diagnostics import (
            CognitiveTraceDiagnosticsModule,
        )

        tracer = CognitiveTraceDiagnosticsModule()
        result = tracer.execute(
            "trace_pipeline",
            {
                "stop_on_error": False,
                "steps": [
                    {
                        "module": "this_module_does_not_exist",
                        "operation": "nope",
                        "params": {"x": 1},
                        "allow_failure": True,
                    }
                ],
            },
        )

        self.assertTrue(result.get("success"))
        trace = result["trace"]
        self.assertEqual(trace["path_length"], 1)
        self.assertFalse(trace["steps"][0]["success"])
        self.assertEqual(trace["steps"][0]["error_type"], "ModuleNotFoundError")


if __name__ == "__main__":
    unittest.main()

