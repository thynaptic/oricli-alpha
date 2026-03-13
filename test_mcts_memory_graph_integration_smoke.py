import unittest


class TestMctsMemoryGraphIntegrationSmoke(unittest.TestCase):
    def test_memory_graph_recall_memories_exists(self) -> None:
        from oricli_core.brain.modules.memory_graph import MemoryGraph

        mg = MemoryGraph()
        mg.initialize()
        result = mg.execute("recall_memories", {"query": "test", "limit": 3})
        self.assertTrue(result.get("success"))
        self.assertIn("memories", result)
        self.assertIsInstance(result["memories"], list)

    def test_mcts_unknown_operation_raises(self) -> None:
        from oricli_core.brain.modules.mcts_service import MCTSService

        mcts = MCTSService()
        with self.assertRaises(Exception):
            mcts.execute("nope", {})


if __name__ == "__main__":
    unittest.main()

