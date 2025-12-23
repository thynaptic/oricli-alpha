import unittest


class TestSweepSmoke(unittest.TestCase):
    def test_unknown_operation_raises(self) -> None:
        from mavaia_core.brain.modules.thought_to_text import ThoughtToTextModule
        from mavaia_core.brain.modules.core_response_service import CoreResponseServiceModule

        t2t = ThoughtToTextModule()
        core = CoreResponseServiceModule()

        with self.assertRaises(Exception):
            t2t.execute("not_a_real_operation", {})

        with self.assertRaises(Exception):
            core.execute("not_a_real_operation", {})


if __name__ == "__main__":
    unittest.main()

