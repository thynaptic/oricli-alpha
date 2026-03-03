import sys
import os
from pathlib import Path
from unittest.mock import MagicMock, patch

# Add project root to path
sys.path.insert(0, os.getcwd())

import scripts.train_curriculum as tc

def test_loop_integration():
    print("Testing curriculum loop integration with --smart-resume...")
    
    # Mock stages
    stages = [
        {"name": "s1", "title": "Stage 1", "dataset": "d1", "epochs": 1, "data_pct": 0.2},
        {"name": "s2", "title": "Stage 2", "dataset": "d2", "epochs": 1, "data_pct": 0.2},
        {"name": "s3", "title": "Stage 3", "dataset": "d3", "epochs": 1, "data_pct": 0.2},
    ]
    
    # Mock Args
    args = MagicMock()
    args.smart_resume = True
    args.target_loss = 0.05
    args.retouch_threshold = 0.15
    args.replay_pct = 0.0
    args.run_root = "/tmp/curriculum_test"
    args.extra_args = []
    args.batch_size = 4
    args.no_gradient_checkpointing = False
    args.elective_base = None
    args.stop_at_loss = 0.05
    args.min_improvement = 0.01
    
    # Mock side effects for _get_stage_performance
    # s1: loss 0.03 (skip)
    # s2: loss 0.10 (retouch)
    # s3: loss 0.20 (full)
    perf_map = {"s1": 0.03, "s2": 0.10, "s3": 0.20}
    
    run_root = Path(args.run_root)
    progress_path = run_root / "progress.json"
    progress = {"stages": []}
    
    with patch("scripts.train_curriculum._get_stage_performance") as mock_perf, \
         patch("scripts.train_curriculum._run_stage") as mock_run, \
         patch("scripts.train_curriculum._write_progress") as mock_write:
        
        mock_perf.side_effect = lambda name, root: perf_map.get(name)
        
        policy = tc.SmartResumePolicy(target_loss=args.target_loss, retouch_threshold=args.retouch_threshold)
        
        for stage in stages:
            mode, data_scale, epoch_scale = policy.decide(mock_perf(stage["name"], run_root))
            
            if mode == "skip":
                print(f"Skipping {stage['name']}")
                continue
            elif mode == "retouch":
                print(f"Retouching {stage['name']}")
                stage["data_pct"] *= data_scale
                
            tc._run_stage(stage, run_root, args.extra_args, progress_path, progress)
            
        # Verify calls
        # s1 should be skipped, s2 and s3 should be run
        self_mock_run_calls = mock_run.call_args_list
        print(f"Total runs: {len(self_mock_run_calls)}")
        assert len(self_mock_run_calls) == 2, "Should have run exactly 2 stages"
        
        # Verify s2 was retouched (data_pct should be 0.1)
        s2_call_args = self_mock_run_calls[0][0] # first call is s2
        assert s2_call_args[0]["name"] == "s2"
        assert s2_call_args[0]["data_pct"] == 0.1, f"s2 data_pct should be 0.1, got {s2_call_args[0]['data_pct']}"
        
        # Verify s3 was full run (data_pct should be 0.2)
        s3_call_args = self_mock_run_calls[1][0] # second call is s3
        assert s3_call_args[0]["name"] == "s3"
        assert s3_call_args[0]["data_pct"] == 0.2
        
    print("Loop integration test PASSED!")

if __name__ == "__main__":
    try:
        test_loop_integration()
    except Exception as e:
        print(f"Test FAILED: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
