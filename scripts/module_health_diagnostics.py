#!/usr/bin/env python3
"""
Module Health Diagnostics Script
Scans all brain modules and validates their adherence to the BaseBrainModule API.
"""

import os
import sys
from pathlib import Path
import traceback
from typing import Dict, Any, List

# Add project root to path
REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT))

from mavaia_core.brain.registry import ModuleRegistry
from mavaia_core.brain.base_module import BaseBrainModule

def run_diagnostics() -> Dict[str, Any]:
    """Run comprehensive diagnostics on all discovered modules."""
    print("🧠 Starting Mavaia Module Health Diagnostics...")
    
    # Ensure heavy modules are enabled for full discovery if possible
    os.environ["MAVAIA_ENABLE_HEAVY_MODULES"] = "true"
    
    discovery_result = ModuleRegistry.discover_modules(verbose=False)
    if not discovery_result:
        print("❌ Discovery failed or no modules found.")
        return {"success": False, "error": "Discovery failed"}
        
    discovered, failed = discovery_result
    print(f"📡 Discovered {discovered} modules ({failed} failed to import).")
    
    module_names = ModuleRegistry.list_modules()
    reports = []
    
    for name in module_names:
        report = {
            "module": name,
            "inheritance": False,
            "metadata_valid": False,
            "initialize_exists": False,
            "execute_exists": False,
            "status_op_valid": "N/A",
            "errors": []
        }
        
        try:
            # 1. Get Instance (this triggers initialize() in Registry.get_module)
            instance = ModuleRegistry.get_module(name)
            if not instance:
                report["errors"].append("Failed to retrieve instance from registry")
                reports.append(report)
                continue
                
            # 2. Check Inheritance
            report["inheritance"] = isinstance(instance, BaseBrainModule)
            
            # 3. Check Metadata
            try:
                meta = instance.metadata
                if meta and meta.name == name:
                    report["metadata_valid"] = True
                else:
                    report["errors"].append(f"Metadata name mismatch: {meta.name if meta else 'None'} vs {name}")
            except Exception as e:
                report["errors"].append(f"Metadata access failed: {e}")
                
            # 4. Check Methods
            report["initialize_exists"] = hasattr(instance, "initialize")
            report["execute_exists"] = hasattr(instance, "execute")
            
            # 5. Check 'status' operation if listed
            if report["metadata_valid"] and "status" in instance.metadata.operations:
                try:
                    res = instance.execute("status", {})
                    if isinstance(res, dict) and "success" in res:
                        report["status_op_valid"] = "PASS"
                    else:
                        report["status_op_valid"] = "FAIL (No success key or not a dict)"
                        report["errors"].append(f"Status op returned invalid format: {res}")
                except Exception as e:
                    report["status_op_valid"] = f"FAIL ({e})"
                    report["errors"].append(f"Status op execution failed: {e}")
                    
        except Exception as e:
            report["errors"].append(f"Unexpected error during audit: {e}")
            
        reports.append(report)
        
    # Summarize
    passed = [r for r in reports if not r["errors"]]
    failed_audit = [r for r in reports if r["errors"]]
    
    print("\n--- Diagnostic Summary ---")
    print(f"✅ Passed: {len(passed)}")
    print(f"❌ Failed: {len(failed_audit)}")
    
    if failed_audit:
        print("\n--- Failure Details ---")
        for r in failed_audit:
            print(f"\nModule: {r['module']}")
            for err in r["errors"]:
                print(f"  - {err}")
                
    return {
        "success": len(failed_audit) == 0,
        "total": len(reports),
        "passed": len(passed),
        "failed": len(failed_audit),
        "reports": reports
    }

if __name__ == "__main__":
    result = run_diagnostics()
    sys.exit(0 if result["success"] else 1)
