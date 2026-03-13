import unittest
import json
import shutil
from pathlib import Path
from oricli_core.evaluation.livebench_parser import LiveBenchResultParser

class TestLiveBenchResultParser(unittest.TestCase):
    def setUp(self):
        self.test_dir = Path("tests/test_livebench_data")
        self.test_dir.mkdir(parents=True, exist_ok=True)
        self.parser = LiveBenchResultParser(verbose=True)

    def tearDown(self):
        if self.test_dir.exists():
            shutil.rmtree(self.test_dir)

    def create_mock_judgment(self, category: str, task: str, passed_count: int, total_count: int):
        judgment_dir = self.test_dir / "data" / "live_bench" / category / "model_judgment"
        judgment_dir.mkdir(parents=True, exist_ok=True)
        
        file_path = judgment_dir / "ground_truth_judgment.jsonl"
        with open(file_path, "w") as f:
            for i in range(total_count):
                score = 1 if i < passed_count else 0
                entry = {
                    "model": "oricli",
                    "score": score,
                    "task": f"{task}_{i}",
                    "category": category,
                    "question_id": f"q_{category}_{task}_{i}"
                }
                f.write(json.dumps(entry) + "\n")

    def test_parse_results(self):
        # Create mock results: 
        # Reasoning: 8/10 (80%)
        # Coding: 4/10 (40%) -> GAP
        self.create_mock_judgment("reasoning", "reasoning_task", 8, 10)
        self.create_mock_judgment("coding", "coding_task", 4, 10)

        summary = self.parser.parse_results(self.test_dir / "data")
        
        self.assertEqual(summary["overall"]["total"], 20)
        self.assertEqual(summary["overall"]["passed"], 12)
        
        self.assertEqual(summary["categories"]["reasoning"]["total"], 10)
        self.assertEqual(summary["categories"]["reasoning"]["passed"], 8)
        
        self.assertEqual(summary["categories"]["coding"]["total"], 10)
        self.assertEqual(summary["categories"]["coding"]["passed"], 4)

    def test_knowledge_gaps(self):
        self.create_mock_judgment("reasoning", "reasoning_task", 8, 10)
        self.create_mock_judgment("coding", "coding_task", 4, 10)

        summary = self.parser.parse_results(self.test_dir / "data")
        gaps = self.parser.get_knowledge_gaps(summary)
        
        self.assertEqual(len(gaps), 1)
        self.assertEqual(gaps[0]["category"], "coding")
        self.assertEqual(gaps[0]["stage"], "Stage 7: Coding")

    def test_empty_dir(self):
        summary = self.parser.parse_results(Path("non_existent_dir"))
        self.assertEqual(summary["overall"]["total"], 0)

if __name__ == "__main__":
    unittest.main()
