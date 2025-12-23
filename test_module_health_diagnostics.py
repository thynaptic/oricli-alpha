import unittest


class TestModuleHealthDiagnostics(unittest.TestCase):
    def test_scan_modules_basic(self) -> None:
        from mavaia_core.brain.modules.module_health_diagnostics import (
            ModuleHealthDiagnosticsModule,
        )

        mod = ModuleHealthDiagnosticsModule()
        result = mod.execute(
            "scan_modules",
            {"include_subdirs": False, "max_modules": 50, "import_timeout_s": 2.0},
        )

        self.assertTrue(result.get("success"))
        report = result.get("result", {})
        self.assertIn("entries", report)
        entries = report["entries"]
        self.assertIsInstance(entries, list)
        self.assertGreater(len(entries), 0)

        # Basic integrity: at least one import should succeed under short timeouts.
        self.assertTrue(any(bool(e.get("import_ok")) for e in entries if isinstance(e, dict)))

    def test_scan_module_file_invalid(self) -> None:
        from mavaia_core.brain.modules.module_health_diagnostics import (
            ModuleHealthDiagnosticsModule,
        )

        mod = ModuleHealthDiagnosticsModule()
        with self.assertRaises(Exception):
            mod.execute("scan_module_file", {"path": "/workspace/does_not_exist.py"})


if __name__ == "__main__":
    unittest.main()

