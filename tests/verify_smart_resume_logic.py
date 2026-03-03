import sys
import os
from pathlib import Path
import unittest
from unittest.mock import MagicMock, patch

# Add project root to path
sys.path.insert(0, os.getcwd())

from scripts.train_curriculum import SmartResumePolicy, _get_stage_performance

class TestSmartResumeManual(unittest.TestCase):
    
    def test_policy_decisions(self):
        """Test the SmartResumePolicy decision logic"""
        # Target 0.05, Retouch < 0.15
        policy = SmartResumePolicy(target_loss=0.05, retouch_threshold=0.15)
        
        # 1. Skip (Loss < 0.05)
        mode, ds, es = policy.decide(0.03)
        self.assertEqual(mode, "skip")
        self.assertEqual(ds, 0.0)
        
        # 2. Retouch (0.05 < Loss < 0.15)
        # Loss 0.10 is exactly middle of (0.05, 0.15)
        # gap = 0.05, span = 0.10 -> scale = 0.5
        mode, ds, es = policy.decide(0.10)
        self.assertEqual(mode, "retouch")
        self.assertAlmostEqual(ds, 0.5)
        
        # Loss 0.06 is close to target
        # gap = 0.01, span = 0.10 -> scale = 0.1
        mode, ds, es = policy.decide(0.06)
        self.assertEqual(mode, "retouch")
        self.assertAlmostEqual(ds, 0.1)
        
        # 3. Full (Loss > 0.15)
        mode, ds, es = policy.decide(0.20)
        self.assertEqual(mode, "full")
        self.assertEqual(ds, 1.0)
        
        # 4. None (No weights)
        mode, ds, es = policy.decide(None)
        self.assertEqual(mode, "full")
        self.assertEqual(ds, 1.0)

    def test_performance_discovery(self):
        """Test that _get_stage_performance finds and parses metrics correctly"""
        # We'll use the existing real data for this test if available
        repo_root = Path(os.getcwd())
        run_root = repo_root / "mavaia_core" / "models" / "neural_text_generator" / "curriculum"
        
        # Mock a stage directory with metrics
        test_dir = repo_root / "test_run_discovery"
        test_dir.mkdir(exist_ok=True)
        try:
            stage_run_dir = test_dir / "tone_stage_20260303_120000"
            stage_run_dir.mkdir(parents=True, exist_ok=True)
            
            # RNN style metrics
            metrics_path = stage_run_dir / "checkpoints" / "char_metrics.jsonl"
            metrics_path.parent.mkdir(exist_ok=True)
            metrics_path.write_text('{"epoch": 1, "logs": {"loss": 0.08}}')
            
            loss = _get_stage_performance("tone_stage", test_dir)
            self.assertEqual(loss, 0.08)
            
            # Transformer style
            ts_path = stage_run_dir / "transformer" / "trainer_state.json"
            ts_path.parent.mkdir(exist_ok=True)
            ts_path.write_text('{"log_history": [{"loss": 0.04, "step": 100}]}')
            
            # Should prefer trainer_state if found later or just parse both
            # Current logic tries trainer_state first
            loss = _get_stage_performance("tone_stage", test_dir)
            self.assertEqual(loss, 0.04)
            
        finally:
            import shutil
            shutil.rmtree(test_dir)

if __name__ == "__main__":
    unittest.main()
