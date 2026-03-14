from __future__ import annotations

import sys
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT))

from oricli_core.brain.modules.adapter_router_module import AdapterRouterModule
from oricli_core.exceptions import InvalidParameterError


def test_adapter_router_module_noop_succeeds():
    module = AdapterRouterModule()

    result = module.execute("noop", {})

    assert result["success"] is True
    assert result["status"] == "ok"
    assert result["module"] == "adapter_router_module"


def test_adapter_router_module_rejects_unknown_operation():
    module = AdapterRouterModule()

    with pytest.raises(InvalidParameterError):
        module.execute("unknown", {})
