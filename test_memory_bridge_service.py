import tempfile
import unittest
from pathlib import Path


class TestMemoryBridgeService(unittest.TestCase):
    def _deps_available(self) -> bool:
        try:
            import lmdb  # noqa: F401
            from cryptography.hazmat.primitives.ciphers.aead import AESGCM  # noqa: F401
        except Exception:
            return False
        return True

    def setUp(self) -> None:
        if not self._deps_available():
            self.skipTest("lmdb/cryptography not available")

    def test_put_get_list_delete_roundtrip(self) -> None:
        from mavaia_core.services.memory_bridge_service import (
            MemoryBridgeConfig,
            MemoryBridgeService,
            MemoryCategory,
        )

        with tempfile.TemporaryDirectory() as td:
            cfg = MemoryBridgeConfig(
                lmdb_path=Path(td) / "memory.lmdb",
                map_size_mb=32,
                enable_vector_index=False,
                encryption_key=b"\x11" * 32,
            )
            svc = MemoryBridgeService(cfg)
            svc.initialize()
            try:
                svc.put(
                    MemoryCategory.SEMANTIC,
                    "user:preferences",
                    {"likes": ["coffee"], "timezone": "UTC"},
                    metadata={"source": "unit_test"},
                )

                obj = svc.get(MemoryCategory.SEMANTIC, "user:preferences")
                self.assertIsInstance(obj, dict)
                self.assertEqual(obj["category"], "semantic")
                self.assertEqual(obj["id"], "user:preferences")
                self.assertEqual(obj["data"]["timezone"], "UTC")
                self.assertEqual(obj["metadata"]["source"], "unit_test")

                ids = svc.list_ids(MemoryCategory.SEMANTIC, prefix="user:")
                self.assertIn("user:preferences", ids)

                deleted = svc.delete(MemoryCategory.SEMANTIC, "user:preferences")
                self.assertTrue(deleted)
                self.assertIsNone(svc.get(MemoryCategory.SEMANTIC, "user:preferences"))
            finally:
                svc.close()

    def test_reflection_log_append_and_read(self) -> None:
        from mavaia_core.services.memory_bridge_service import MemoryBridgeConfig, MemoryBridgeService

        with tempfile.TemporaryDirectory() as td:
            cfg = MemoryBridgeConfig(
                lmdb_path=Path(td) / "memory.lmdb",
                map_size_mb=32,
                enable_vector_index=False,
                encryption_key=b"\x22" * 32,
            )
            svc = MemoryBridgeService(cfg)
            svc.initialize()
            try:
                k1 = svc.append_reflection_log("session_1", {"note": "first"})
                k2 = svc.append_reflection_log("session_1", {"note": "second"})
                self.assertNotEqual(k1, k2)

                items = svc.read_reflection_log("session_1", limit=10)
                self.assertGreaterEqual(len(items), 2)
                notes = [it["entry"]["note"] for it in items]
                self.assertIn("first", notes)
                self.assertIn("second", notes)
            finally:
                svc.close()

    def test_tamper_detection_fails_decrypt(self) -> None:
        from mavaia_core.services.memory_bridge_service import (
            MemoryBridgeConfig,
            MemoryBridgeService,
            MemoryCategory,
            MemoryBridgeOperationError,
        )

        with tempfile.TemporaryDirectory() as td:
            cfg = MemoryBridgeConfig(
                lmdb_path=Path(td) / "memory.lmdb",
                map_size_mb=32,
                enable_vector_index=False,
                encryption_key=b"\x33" * 32,
            )
            svc = MemoryBridgeService(cfg)
            svc.initialize()
            try:
                svc.put(MemoryCategory.IDENTITY, "system:info", {"name": "mavaia"})

                # Corrupt a byte in the ciphertext directly in LMDB.
                key = b"system:info"
                with svc._env.begin(write=True, db=svc._dbs[MemoryCategory.IDENTITY]) as txn:  # type: ignore[attr-defined]
                    raw = txn.get(key)
                    self.assertIsNotNone(raw)
                    corrupted = bytearray(raw)
                    corrupted[-1] ^= 0x01
                    txn.put(key, bytes(corrupted))

                with self.assertRaises(MemoryBridgeOperationError):
                    svc.get(MemoryCategory.IDENTITY, "system:info")
            finally:
                svc.close()


if __name__ == "__main__":
    unittest.main()

