import pytest
import subprocess
import sys
import json
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent

def test_find_elective_arg_parsing():
    """Verify that --find-elective arguments are accepted."""
    # We use --list-stages to avoid actual execution but trigger arg parsing
    cmd = [
        sys.executable,
        str(REPO_ROOT / "scripts" / "train_curriculum.py"),
        "--find-elective", "python",
        "--auto-select",
        "--list-stages"
    ]
    # This might still try to search live, so we mock DatasetSearch if needed
    # but for a simple arg parsing test, we just check if it crashes on args
    
    result = subprocess.run(cmd, capture_output=True, text=True)
    assert "--find-elective" not in result.stderr
    assert "unrecognized arguments" not in result.stderr

def test_discovery_flow_logic(mocker):
    """Test the logic of injecting a discovered stage."""
    from scripts.train_curriculum import _auto_inject_stage
    from mavaia_core.data.search import SearchResult
    
    res = SearchResult(id="test/ds", name="Test DS", source="huggingface", description="desc")
    stage = _auto_inject_stage(res, base_epochs=2, base_data_pct=0.5)
    
    assert stage["name"] == "discovered_test_ds"
    assert stage["dataset"] == "test/ds"
    assert stage["epochs"] == 2
    assert stage["data_pct"] == 0.5
    assert stage["is_elective"] is True
