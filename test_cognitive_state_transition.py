import unittest
import uuid
import sys
import os
from pathlib import Path

# Add project root to path
sys.path.append(str(Path(__file__).parent))

from oricli_core.brain.modules.state_manager import StateManagerModule
from oricli_core.types.cognitive import CognitiveState, ThoughtStep

class TestCognitiveStateTransition(unittest.TestCase):
    def setUp(self):
        self.state_manager = StateManagerModule()
        self.state_manager.initialize()
        self.state_id = str(uuid.uuid4())

    def test_structured_cognitive_state_lifecycle(self):
        # 1. Create a new cognitive state
        initial_state = CognitiveState(state_id=self.state_id)
        initial_state.add_thought(
            module="mcts_reasoning",
            content="Thinking about the user's request for Python code optimization.",
            confidence=0.95
        )
        
        # 2. Persist it via state_manager
        result = self.state_manager.execute("update_cognitive_state", {
            "state_id": self.state_id,
            "state_data": initial_state
        })
        self.assertTrue(result["updated"])
        
        # 3. Retrieve it
        get_result = self.state_manager.execute("get_cognitive_state", {
            "state_id": self.state_id
        })
        self.assertTrue(get_result["found"])
        
        # 4. Validate contents
        retrieved_dict = get_result["cognitive_state"]
        retrieved_state = CognitiveState.model_validate(retrieved_dict)
        
        self.assertEqual(retrieved_state.state_id, self.state_id)
        self.assertEqual(len(retrieved_state.thought_trace), 1)
        self.assertEqual(retrieved_state.thought_trace[0].module, "mcts_reasoning")
        self.assertEqual(retrieved_state.thought_trace[0].content, "Thinking about the user's request for Python code optimization.")
        
        # 5. Simulate transition to another module
        retrieved_state.add_thought(
            module="text_generation_engine",
            content="Synthesizing the final optimized Python code.",
            confidence=0.98
        )
        retrieved_state.current_stage = "rendering"
        
        # 6. Update state
        update_result = self.state_manager.execute("update_cognitive_state", {
            "state_id": self.state_id,
            "state_data": retrieved_state
        })
        self.assertTrue(update_result["updated"])
        
        # 7. Final check
        final_result = self.state_manager.execute("get_cognitive_state", {
            "state_id": self.state_id
        })
        final_state = CognitiveState.model_validate(final_result["cognitive_state"])
        self.assertEqual(len(final_state.thought_trace), 2)
        self.assertEqual(final_state.current_stage, "rendering")

if __name__ == "__main__":
    unittest.main()
