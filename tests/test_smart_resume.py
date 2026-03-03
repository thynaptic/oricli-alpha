import sys
import os
from pathlib import Path
import unittest
import json
import shutil
from unittest.mock import MagicMock, patch

# Add project root to path
sys.path.insert(0, os.getcwd())

from scripts.train_curriculum import SmartResumePolicy, _get_stage_performance, _extract_loss_from_run

class TestSmartResume(unittest.TestCase):
    
    def setUp(self):
        self.test_dir = Path(os.getcwd()) / "tmp_test_smart_resume"
        self.test_dir.mkdir(exist_ok=True)

    def tearDown(self):
        if self.test_dir.exists():
            shutil.rmtree(self.test_dir)

    def test_policy_logic(self):
        """Test the SmartResumePolicy decision matrix"""
        policy = SmartResumePolicy(target_loss=0.05, retouch_threshold=0.15)
        
        # Skip
        mode, ds, es = policy.decide(0.02)
        self.assertEqual(mode, "skip")
        
        # Retouch
        mode, ds, es = policy.decide(0.10)
        self.assertEqual(mode, "retouch")
        self.assertAlmostEqual(ds, 0.5) # middle of 0.05 and 0.15
        
        # Full
        mode, ds, es = policy.decide(0.25)
        self.assertEqual(mode, "full")
        self.assertEqual(ds, 1.0)
        
        # No metrics
        mode, ds, es = policy.decide(None)
        self.assertEqual(mode, "full")

    def test_performance_extraction_rnn(self):
        """Test extraction from RNN metrics format (logs.loss)"""
        run_dir = self.test_dir / "run_rnn"
        run_dir.mkdir(parents=True)
        metrics_path = run_dir / "checkpoints" / "char_metrics.jsonl"
        metrics_path.parent.mkdir()
        metrics_path.write_text('{"epoch": 1, "logs": {"loss": 0.12}}\n')
        
        loss = _extract_loss_from_run(run_dir)
        self.assertEqual(loss, 0.12)

    def test_performance_extraction_hf(self):
        """Test extraction from HF Trainer format (trainer_state.json)"""
        run_dir = self.test_dir / "run_hf"
        run_dir.mkdir(parents=True)
        ts_path = run_dir / "transformer" / "trainer_state.json"
        ts_path.parent.mkdir()
        ts_path.write_text('{"log_history": [{"loss": 0.08, "step": 50}, {"loss": 0.06, "step": 100}]}')
        
        loss = _extract_loss_from_run(run_dir)
        self.assertEqual(loss, 0.06)

    def test_global_discovery(self):
        """Test that _get_stage_performance finds the latest run among many"""
        sname = "stage_x"
        # Create two runs, one older, one newer
        run1 = self.test_dir / f"{sname}_20260101_000000"
        run1.mkdir()
        (run1 / "stage_metrics.jsonl").write_text('{"loss": 0.5}')
        
        # Artificial delay to ensure different mtimes if needed, 
        # but let's just use different timestamps in name too
        run2 = self.test_dir / f"{sname}_20260303_000000"
        run2.mkdir()
        (run2 / "stage_metrics.jsonl").write_text('{"loss": 0.02}')
        
        loss = _get_stage_performance(sname, self.test_dir)
        self.assertEqual(loss, 0.02)

if __name__ == "__main__":
    unittest.main()
