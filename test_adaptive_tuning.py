import unittest
from mavaia_core.brain.orchestrator import ModuleOrchestrator
from mavaia_core.brain.metrics import get_metrics_collector
from mavaia_core.brain.base_module import BaseBrainModule, ModuleMetadata
from mavaia_core.brain.registry import ModuleRegistry

class MockFailingModule(BaseBrainModule):
    @property
    def metadata(self):
        return ModuleMetadata(
            name="failing_mod", 
            version="1.0.0", 
            description="Mock", 
            operations=["test_op"],
            dependencies=[]
        )
    def initialize(self): return True
    def execute(self, op, params):
        # The params dictionary should have been updated by the orchestrator
        return {"success": False, "depth": params.get("adaptive_depth", 0)}

class TestAdaptiveTuning(unittest.TestCase):
    def test_orchestrator_tuning(self):
        orch = ModuleOrchestrator()
        metrics = get_metrics_collector()
        metrics.reset()
        
        # 1. Register and mock a failing module (Passing the CLASS, not instance)
        meta = ModuleMetadata(
            name="failing_mod", 
            version="1.0.0", 
            description="Mock", 
            operations=["test_op"],
            dependencies=[]
        )
        ModuleRegistry.register_module("failing_mod", MockFailingModule, meta)
        
        # 2. Simulate 6 failures to trigger tuning threshold (>5 calls, >20% failure)
        for _ in range(6):
            metrics.record_operation("failing_mod", "test_op", 0.1, success=False)
        
        # 3. Compose should now inject adaptive_depth
        params = {}
        # We use a list of module names, orchestrator will load "failing_mod"
        result = orch.compose_modules(["failing_mod"], "test_op", params)
        
        # Check if params was updated (it's passed by reference)
        self.assertIn("adaptive_depth", params)
        self.assertGreater(params["adaptive_depth"], 0)
        
        # Also check the module's own perception of the depth
        self.assertGreater(result["failing_mod"]["depth"], 0)
        print(f"Adaptive depth successfully injected and verified: {params['adaptive_depth']}")

if __name__ == "__main__":
    unittest.main()
