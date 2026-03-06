#!/usr/bin/env python3
"""
Test conflict detection logic in the RFAL Engine.
"""

import sys
import os
from pathlib import Path
from unittest.mock import MagicMock, patch

# Add project root to path
REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT))

from mavaia_core.brain.registry import ModuleRegistry

def test_keyword_conflict():
    """Verify that rejection keywords trigger a conflict."""
    print("Testing keyword conflict detection...")
    
    # Enable heavy modules for registration
    os.environ["MAVAIA_ENABLE_HEAVY_MODULES"] = "true"
    
    rfal = ModuleRegistry.get_module("rfal_engine")
    if not rfal:
        print("✗ Failed to get rfal_engine instance")
        sys.exit(1)
        
    test_cases = [
        ("No, that's wrong.", True),
        ("Actually, I meant something else.", True),
        ("That's correct, thank you!", False),
        ("Stop, this is hallucinating.", True),
        ("Could you reword that?", True),
        ("Great job!", False)
    ]
    
    for text, expected in test_cases:
        params = {
            "user_input": text,
            "last_response": "previous output",
            "prompt": "original query"
        }
        res = rfal.execute("process_feedback", params)
        is_conflict = res.get("is_conflict")
        
        if is_conflict == expected:
            print(f"✓ '{text}' -> is_conflict={is_conflict} (Correct)")
        else:
            print(f"✗ '{text}' -> is_conflict={is_conflict} (Expected {expected})")
            sys.exit(1)

def test_sentiment_conflict():
    """Verify that negative sentiment triggers a conflict."""
    print("\nTesting sentiment conflict detection...")
    
    rfal = ModuleRegistry.get_module("rfal_engine")
    
    # Mock emotional_inference
    mock_ei = MagicMock()
    
    with patch("mavaia_core.brain.registry.ModuleRegistry.get_module") as mock_get:
        def side_effect(name, **kwargs):
            if name == "emotional_inference":
                return mock_ei
            return ModuleRegistry.get_module(name, **kwargs)
        
        mock_get.side_effect = side_effect
        
        # Test 1: Frustrated user
        mock_ei.execute.return_value = {"emotion_score": {"emotion": "frustrated", "confidence": 0.8}}
        res = rfal.execute("process_feedback", {
            "user_input": "I am so tired of this not working.",
            "last_response": "output",
            "prompt": "query"
        })
        if res.get("is_conflict") and "negative_sentiment" in res.get("conflict_signals", []):
            print("✓ Negative sentiment correctly detected as conflict")
        else:
            print(f"✗ Negative sentiment failed to trigger: {res}")
            sys.exit(1)
            
        # Test 2: Happy user
        mock_ei.execute.return_value = {"emotion_score": {"emotion": "happy", "confidence": 0.9}}
        res = rfal.execute("process_feedback", {
            "user_input": "This is amazing!",
            "last_response": "output",
            "prompt": "query"
        })
        if not res.get("is_conflict"):
            print("✓ Positive sentiment correctly ignored")
        else:
            print(f"✗ Positive sentiment incorrectly flagged as conflict: {res}")
            sys.exit(1)

def test_repetition_conflict():
    """Verify that repeating a prompt triggers a conflict."""
    print("\nTesting repetition conflict detection...")
    
    rfal = ModuleRegistry.get_module("rfal_engine")
    
    # Repetitive turn
    history = [
        {"role": "user", "content": "Tell me a joke about Linux."},
        {"role": "assistant", "content": "Why did the penguin cross the road?"}
    ]
    
    res = rfal.execute("process_feedback", {
        "user_input": "tell me a joke about linux", # Re-prompting similar content
        "last_response": "Why did the penguin...",
        "prompt": "Tell me a joke about Linux.",
        "history": history
    })
    
    if res.get("is_conflict") and "task_repetition" in res.get("conflict_signals", []):
        print("✓ Task repetition correctly detected as conflict")
    else:
        print(f"✗ Task repetition failed to trigger: {res}")
        sys.exit(1)

if __name__ == "__main__":
    try:
        test_keyword_conflict()
        test_sentiment_conflict()
        test_repetition_conflict()
        print("\n✨ All Phase 1 Conflict Logic tests passed!")
    except Exception as e:
        print(f"✗ Tests failed with error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
