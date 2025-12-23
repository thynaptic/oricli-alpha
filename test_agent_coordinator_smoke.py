import unittest

from mavaia_core.brain.modules.agent_coordinator import AgentCoordinatorModule, AgentType


class TestAgentCoordinatorSmoke(unittest.TestCase):
    def test_execute_search_then_ranking(self) -> None:
        module = AgentCoordinatorModule()
        module.initialize()

        search_task = {
            "id": "t1",
            "agent_type": AgentType.SEARCH,
            "query": "transformer model attention",
            "context": {"limit": 3, "sources": ["web", "memory"]},
            "dependencies": [],
            "priority": 0,
        }
        search_result = module.execute("execute_task", {"task": search_task, "previous_results": []})
        self.assertTrue(search_result.get("success"))
        out1 = search_result["result"]["output"]
        self.assertIsInstance(out1, dict)
        self.assertIsInstance(out1.get("documents"), list)

        ranking_task = {
            "id": "t2",
            "agent_type": AgentType.RANKING,
            "query": "transformer model attention",
            "context": {},
            "dependencies": ["t1"],
            "priority": 0,
        }
        ranking_result = module.execute(
            "execute_task",
            {"task": ranking_task, "previous_results": [search_result["result"]]},
        )
        self.assertTrue(ranking_result.get("success"))
        out2 = ranking_result["result"]["output"]
        self.assertIsInstance(out2, dict)
        ranked = out2.get("rankedDocuments") or out2.get("ranked_documents")
        self.assertIsInstance(ranked, list)


if __name__ == "__main__":
    unittest.main()

