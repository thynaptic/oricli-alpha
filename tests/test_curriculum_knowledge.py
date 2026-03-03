import sys
import os
import unittest
from pathlib import Path

# Add project root to path
sys.path.insert(0, os.getcwd())

from scripts.train_curriculum import _stage_defs

class TestCurriculumKnowledge(unittest.TestCase):
    def test_stage9_presence(self):
        """Verify Stage 9 is present and has the correct multi-dataset configuration"""
        stages = _stage_defs(1, 0.1, False)
        # We now have 9 stages
        self.assertEqual(len(stages), 9)
        
        stage9 = stages[8]
        self.assertEqual(stage9["name"], "knowledge_world_dense")
        self.assertEqual(stage9["title"], "Stage 9: Comprehensive World Knowledge")
        self.assertIsInstance(stage9["dataset"], list)
        self.assertEqual(len(stage9["dataset"]), 3)
        self.assertIn("tau/commonsense_qa", stage9["dataset"])
        self.assertIn("HuggingFaceFW/fineweb-edu", stage9["dataset"])
        self.assertIn("wikimedia/wikipedia:20231101.en", stage9["dataset"])

    def test_sequencing(self):
        """Verify that Stage 9 correctly follows the Stage 8 Alignment Phase"""
        stages = _stage_defs(1, 0.1, False)
        self.assertEqual(stages[7]["name"], "alignment_dpo")
        self.assertEqual(stages[8]["name"], "knowledge_world_dense")

    def test_metadata(self):
        """Verify the 'age' and 'school' metadata for Stage 9"""
        stages = _stage_defs(1, 0.1, False)
        stage9 = stages[8]
        self.assertEqual(stage9["age"], "Age 30")
        self.assertEqual(stage9["school"], "Deep Intelligence Integration")

if __name__ == "__main__":
    unittest.main()
