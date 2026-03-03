import sys
import os
from pathlib import Path
import unittest
from unittest.mock import MagicMock, patch

# Add project root to path
sys.path.insert(0, os.getcwd())

class TestStage9Foundation(unittest.TestCase):
    
    @patch("subprocess.run")
    @patch("scripts.train_curriculum._write_progress")
    def test_stage9_foundation_loading(self, mock_write, mock_run):
        """Test that Stage 9 correctly identifies and loads the Stage 8 weights as foundation"""
        from scripts.train_curriculum import _run_stage
        
        # Stage 9 definition
        stage9 = {
            "name": "knowledge_world_dense",
            "title": "Stage 9: Comprehensive World Knowledge",
            "school": "Graduate",
            "age": "30",
            "dataset": ["ds1", "ds2"],
            "is_elective": False, # Core sequential
            "epochs": 1,
            "data_pct": 0.1
        }
        
        # Progress showing Stage 8 completed
        progress = {
            "stages": [
                {
                    "name": "alignment_dpo", 
                    "is_elective": False, 
                    "status": "completed", 
                    "run_dir": "/models/stage8_final"
                }
            ]
        }
        
        run_root = Path("/tmp/curriculum")
        progress_path = run_root / "progress.json"
        
        _run_stage(stage9, run_root, [], progress_path, progress)
        
        # Get the first subprocess call (the training script)
        args = mock_run.call_args_list[0][0][0]
        
        # Core Sequential should use --continue-training and --run-dir from previous
        # BUT WAIT: My current _run_stage logic only does this for ELECTIVES.
        # Core stages typically rely on the default 'latest_run.txt' or manual resume.
        # SPEC says: "Ensure Stage 9 correctly loads the Stage 8 weights as its foundation."
        
        print(f"Generated Args: {args}")
        
        # If it's a core sequential stage, it should probably ALSO use --continue-training 
        # if there's a previous stage, to ensure we don't start from scratch.
        self.assertIn("--continue-training", args)
        self.assertIn("--run-dir", args)
        self.assertIn("/models/stage8_final", args)

if __name__ == "__main__":
    unittest.main()
