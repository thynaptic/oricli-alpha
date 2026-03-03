#!/usr/bin/env python3
"""
Tests for Curriculum Electives (LoRA specialized modes)
"""

import sys
import os
from pathlib import Path
import unittest
from unittest.mock import MagicMock, patch

# Add project root to path
sys.path.insert(0, os.getcwd())

from scripts.train_curriculum import _stage_defs

class TestCurriculumElectives(unittest.TestCase):
    
    def test_elective_categorization_by_index(self):
        """Test that stages are correctly marked as electives using indices"""
        stages = _stage_defs(1, 0.2, False)
        
        # Mocking the logic from main()
        elective_indices = {7, 8} # Coding and Alignment
        
        for i, s in enumerate(stages):
            is_elective = False
            if (i + 1) in elective_indices:
                is_elective = True
            s["is_elective"] = is_elective
            
        self.assertTrue(stages[6]["is_elective"], "Stage 7 should be elective")
        self.assertTrue(stages[7]["is_elective"], "Stage 8 should be elective")
        self.assertFalse(stages[0]["is_elective"], "Stage 1 should NOT be elective")

    def test_elective_categorization_by_name(self):
        """Test that stages are correctly marked as electives using names"""
        stages = _stage_defs(1, 0.2, False)
        
        # Mocking the logic from main()
        elective_names = {"coding", "alignment"}
        
        for i, s in enumerate(stages):
            is_elective = False
            for name in elective_names:
                if name in s["name"].lower() or name in s["title"].lower():
                    is_elective = True
                    break
            s["is_elective"] = is_elective
            
        coding_stage = next(s for s in stages if "coding" in s["name"])
        alignment_stage = next(s for s in stages if "alignment" in s["name"])
        tone_stage = next(s for s in stages if "tone" in s["name"])
        
        self.assertTrue(coding_stage["is_elective"], "Coding stage should be elective")
        self.assertTrue(alignment_stage["is_elective"], "Alignment stage should be elective")
        self.assertFalse(tone_stage["is_elective"], "Tone stage should NOT be elective")

    @patch("subprocess.run")
    @patch("scripts.train_curriculum._write_progress")
    def test_run_stage_elective_logic(self, mock_write, mock_run):
        """Test that _run_stage correctly generates arguments for elective stages"""
        from scripts.train_curriculum import _run_stage
        
        stage = {
            "name": "coding_elective",
            "title": "Stage 6: Coding Phase",
            "school": "Doctoral",
            "age": "27",
            "dataset": "some/dataset",
            "is_elective": True,
            "epochs": 1,
            "data_pct": 0.1
        }
        
        progress = {
            "stages": [
                {"name": "base_stage", "is_elective": False, "status": "completed", "run_dir": "/models/base_run"}
            ]
        }
        
        run_root = Path("/tmp/curriculum")
        progress_path = run_root / "progress.json"
        
        _run_stage(stage, run_root, [], progress_path, progress)
        
        # Verify subprocess call (the first one should be the training script)
        args = mock_run.call_args_list[0][0][0]
        
        # Check for LoRA and adapter name
        self.assertIn("--lora", args)
        self.assertIn("--adapter-name", args)
        self.assertIn("coding_elective", args)
        
        # Check for correct base loading
        self.assertIn("--continue-training", args)
        self.assertIn("--run-dir", args)
        self.assertIn("/models/base_run", args)
        
        # Check for explicit output-dir (preventing base overwrite)
        self.assertIn("--output-dir", args)

    @patch("subprocess.run")
    @patch("scripts.train_curriculum._write_progress")
    def test_run_stage_manual_elective_base(self, mock_write, mock_run):
        """Test that _run_stage respects manual elective base override"""
        from scripts.train_curriculum import _run_stage
        
        stage = {
            "name": "manual_elective",
            "title": "Manual Elective",
            "school": "Extra",
            "age": "N/A",
            "dataset": "some/dataset",
            "is_elective": True,
            "epochs": 1,
            "data_pct": 0.1
        }
        
        progress = {"stages": []}
        run_root = Path("/tmp/curriculum")
        
        # Pass a manual base path
        manual_base = "/models/my_custom_base"
        
        _run_stage(stage, run_root, [], run_root / "prog.json", progress, elective_base=manual_base)
        
        args = mock_run.call_args_list[0][0][0]
        
        # Should use manual base instead of searching progress
        self.assertIn(manual_base, args)
        self.assertIn("--continue-training", args)

if __name__ == "__main__":
    unittest.main()
