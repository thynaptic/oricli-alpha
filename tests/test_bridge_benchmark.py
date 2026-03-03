import unittest
from unittest.mock import patch, MagicMock
import sys
import os
from pathlib import Path

# Add project root to path
REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT))

import scripts.runpod_bridge as bridge

class TestBridgeBenchmark(unittest.TestCase):
    
    @patch("scripts.runpod_bridge.subprocess.run")
    def test_remote_benchmark_command(self, mock_run):
        # Test command generation
        bench_args = ["--category", "coding"]
        workdir = "/workspace"
        pod_ip = "1.2.3.4"
        pod_port = 1234
        ssh_key = "key_path"
        
        bridge.remote_benchmark(
            pod_ip, pod_port, ssh_key, bench_args, workdir
        )
        
        # Verify subprocess.run was called with expected command
        self.assertTrue(mock_run.called)
        args, kwargs = mock_run.call_args
        cmd_list = args[0]
        
        # Command should contain cd to workdir and evaluation script
        full_cmd = cmd_list[-1]
        self.assertIn(f"cd {workdir}/mavaia", full_cmd)
        self.assertIn("LiveBench/livebench/evaluate.py", full_cmd)
        self.assertIn("--category coding", full_cmd)

    @patch("scripts.runpod_bridge.subprocess.run")
    def test_get_bench_results_rsync(self, mock_run):
        local_path = Path("/tmp/mavaia_local")
        workdir = "/workspace"
        pod_ip = "1.2.3.4"
        pod_port = 1234
        ssh_key = "key_path"
        
        bridge.get_bench_results(
            pod_ip, pod_port, ssh_key, local_path, workdir
        )
        
        self.assertTrue(mock_run.called)
        args, kwargs = mock_run.call_args
        rsync_cmd = args[0]
        
        self.assertEqual(rsync_cmd[0], "rsync")
        self.assertIn("--include=livebench_results_*.json", rsync_cmd)
        self.assertIn("--include=mavaia_result.json", rsync_cmd)
        self.assertIn("--exclude=*", rsync_cmd)

if __name__ == "__main__":
    unittest.main()
