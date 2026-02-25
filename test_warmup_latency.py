import unittest
import time
import sys
from pathlib import Path

# Add project root to path
sys.path.append(str(Path(__file__).parent))

from mavaia_core.brain.modules.model_warmup_service import ModelWarmupServiceModule
from mavaia_core.brain.registry import ModuleRegistry

class TestWarmupLatency(unittest.TestCase):
    def setUp(self):
        # Ensure registry is initialized but we'll mock the modules
        ModuleRegistry.discover_modules(background=False)
        self.warmup_service = ModelWarmupServiceModule()
        self.warmup_service.initialize()

    def test_parallel_warmup_execution(self):
        # We want to see if it executes. Since we don't have all real models 
        # in the environment that actually take time, we'll check if it 
        # completes and reports status.
        
        start_time = time.time()
        result = self.warmup_service.execute("warmup_models", {})
        end_time = time.time()
        
        duration = end_time - start_time
        print(f"\nWarmup completed in {duration:.4f} seconds")
        
        self.assertTrue(result["success"])
        self.assertIn("ready_models", result)
        self.assertIn("failed_models", result)
        
        # Check if it's actually reporting readiness
        status = self.warmup_service.execute("check_readiness", {})
        self.assertTrue(status["success"])
        self.assertEqual(status["is_ready"], len(result["ready_models"]) > 0)

if __name__ == "__main__":
    unittest.main()
