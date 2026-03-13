#!/usr/bin/env python3
"""
Test asynchronous loop integration of RFAL in Oricli-AlphaClient.
"""

import sys
import os
import time
from pathlib import Path
from unittest.mock import MagicMock, patch

# Add project root to path
REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT))

from oricli_core.client import Oricli-AlphaClient
from oricli_core.types.models import ChatCompletionRequest, ChatMessage

def test_async_rfal_trigger():
    """Verify that Oricli-AlphaClient triggers RFAL in the background on user correction."""
    print("Testing async RFAL trigger in Oricli-AlphaClient...")
    
    # Enable heavy modules for registration
    os.environ["MAVAIA_ENABLE_HEAVY_MODULES"] = "true"
    
    client = Oricli-AlphaClient()
    
    # Mock the RFAL engine
    mock_rfal = MagicMock()
    
    # Mock cognitive_generator to avoid real generation
    mock_cog = MagicMock()
    mock_cog.execute.return_value = {
        "success": True, 
        "text": "new response",
        "usage": {"prompt_tokens": 10, "completion_tokens": 10, "total_tokens": 20}
    }
    
    with patch("oricli_core.brain.registry.ModuleRegistry.get_module") as mock_get:
        def side_effect(name, **kwargs):
            if name == "rfal_engine":
                return mock_rfal
            if name == "cognitive_generator":
                return mock_cog
            return None
            
        mock_get.side_effect = side_effect
        
        # Scenario: User correcting the assistant
        # Prompt history:
        # 1. User: "Hello"
        # 2. Assistant: "Hi!"
        # 3. User: "Actually, I wanted to say bye." (The correction)
        
        messages = [
            {"role": "user", "content": "Hello"},
            {"role": "assistant", "content": "Hi!"},
            {"role": "user", "content": "Actually, I wanted to say bye."}
        ]
        
        start_time = time.time()
        
        # Trigger chat completion
        # This should immediately return while RFAL runs in background
        res = client.chat.completions.create(
            messages=messages,
            model="oricli-cognitive"
        )
        
        elapsed = time.time() - start_time
        print(f"✓ Chat completion returned in {elapsed:.4f}s")
        
        # Verify immediate response
        if res.choices[0].message.content == "new response":
            print("✓ Correct response returned from mock")
        else:
            print(f"✗ Unexpected response: {res}")
            sys.exit(1)
            
        # Give background thread a moment
        time.sleep(0.5)
        
        # Verify RFAL was called
        if mock_rfal.execute.called:
            args, kwargs = mock_rfal.execute.call_args
            op = args[0]
            params = args[1]
            if op == "process_feedback":
                print(f"✓ RFAL 'process_feedback' was triggered in background")
                if params.get("user_input") == "Actually, I wanted to say bye.":
                    print("✓ Correct feedback data passed to RFAL")
                else:
                    print(f"✗ Incorrect feedback data: {params}")
                    sys.exit(1)
            else:
                print(f"✗ Unexpected RFAL operation: {op}")
                sys.exit(1)
        else:
            print("✗ RFAL was NOT triggered")
            sys.exit(1)

if __name__ == "__main__":
    try:
        test_async_rfal_trigger()
        print("\n✨ Phase 3 Loop Integration tests passed!")
    except Exception as e:
        print(f"✗ Tests failed with error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
