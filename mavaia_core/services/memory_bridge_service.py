"""
MemoryBridgeService (memory.mavaia)

A platform-agnostic, encrypted memory store intended to be shared across runtimes.

This Python implementation uses:
- LMDB for fast local key-value storage
- AES-GCM for authenticated encryption of all values

Memory categories supported:
- semantic (facts, preferences)
- episodic (interactions, events)
- identity (system knowledge)
- skill (learned procedures)
- long_term_state
- reflection_log
- vector_index (optional, local)
"""

from __future__ import annotations

import base64
import json
import logging
import os
import threading
import time
import uuid
from dataclasses import dataclass
from enum import Enum
from pathlib import Path
from typing import Any, Optional

from mavaia_core.exceptions import InvalidParameterError, MavaiaError

logger = logging.getLogger(__name__)


class MemoryBridgeError(MavaiaError):
    """Base exception for memory bridge errors."""


class MemoryBridgeDependencyError(MemoryBridgeError):
    """Raised when required optional dependencies are missing."""


class MemoryBridgeConfigError(MemoryBridgeError):
    """Raised when MemoryBridgeService configuration is invalid."""


class MemoryBridgeOperationError(MemoryBridgeError):
    """Raised when an LMDB/encryption operation fails."""


class MemoryCategory(str, Enum):
    """Supported memory categories."""

    SEMANTIC = "semantic"
    EPISODIC = "episodic"
    IDENTITY = "identity"
    SKILL = "skill"
    LONG_TERM_STATE = "long_term_state"
    REFLECTION_LOG = "reflection_log"
    VECTOR_INDEX = "vector_index"


@dataclass(frozen=True)
class MemoryBridgeConfig:
    """
    Configuration for MemoryBridgeService.

    Attributes:
        lmdb_path: Directory path for the LMDB environment (created if missing).
        map_size_mb: LMDB map size in MB.
        enable_vector_index: Whether vector index DB is enabled.
        encryption_key: Raw 32-byte key for AES-256-GCM.
        max_dbs: Maximum number of named databases in the environment.
    """

    lmdb_path: Path
    map_size_mb: int = 512
    enable_vector_index: bool = False
    encryption_key: bytes = b""
    max_dbs: int = 16

    @classmethod
    def from_env(cls) -> "MemoryBridgeConfig":
        """
        Build config from environment variables.

        Environment variables:
        - MAVAIA_MEMORY_LMDB_PATH (default: ./.mavaia/memory.lmdb)
        - MAVAIA_MEMORY_LMDB_MAP_SIZE_MB (default: 512)
        - MAVAIA_MEMORY_ENABLE_VECTOR_INDEX (default: false)
        - MAVAIA_MEMORY_ENCRYPTION_KEY (required; base64url/standard-base64/hex)
        - MAVAIA_MEMORY_LMDB_MAX_DBS (default: 16)
        """
        path_str = os.getenv("MAVAIA_MEMORY_LMDB_PATH", str(Path(".mavaia") / "memory.lmdb"))
        map_size_mb_str = os.getenv("MAVAIA_MEMORY_LMDB_MAP_SIZE_MB", "512")
        enable_vector_str = os.getenv("MAVAIA_MEMORY_ENABLE_VECTOR_INDEX", "false")
        max_dbs_str = os.getenv("MAVAIA_MEMORY_LMDB_MAX_DBS", "16")
        key_str = os.getenv("MAVAIA_MEMORY_ENCRYPTION_KEY", "").strip()

        try:
            map_size_mb = int(map_size_mb_str)
        except ValueError as e:
            raise InvalidParameterError(
                parameter="MAVAIA_MEMORY_LMDB_MAP_SIZE_MB",
                value=map_size_mb_str,
                reason="Must be an integer (megabytes).",
            ) from e
        if map_size_mb <= 0:
            raise InvalidParameterError(
                parameter="MAVAIA_MEMORY_LMDB_MAP_SIZE_MB",
                value=map_size_mb_str,
                reason="Must be a positive integer (megabytes).",
            )

        try:
            max_dbs = int(max_dbs_str)
        except ValueError as e:
            raise InvalidParameterError(
                parameter="MAVAIA_MEMORY_LMDB_MAX_DBS",
                value=max_dbs_str,
                reason="Must be an integer.",
            ) from e
        if max_dbs < 8:
            raise InvalidParameterError(
                parameter="MAVAIA_MEMORY_LMDB_MAX_DBS",
                value=max_dbs_str,
                reason="Must be >= 8.",
            )

        enable_vector = enable_vector_str.strip().lower() in ("true", "1", "yes", "y", "on")
        key = _parse_encryption_key(key_str)

        return cls(
            lmdb_path=Path(path_str),
            map_size_mb=map_size_mb,
            enable_vector_index=enable_vector,
            encryption_key=key,
            max_dbs=max_dbs,
        )


def _parse_encryption_key(key_str: str) -> bytes:
    """
    Parse an encryption key string into raw 32 bytes for AES-256-GCM.

    Accepted formats:
    - base64 / base64url (recommended): 32 bytes when decoded
    - hex: 64 hex chars -> 32 bytes (prefix "hex:" optional)

    Raises:
        MemoryBridgeConfigError: If missing or invalid.
    """
    if not key_str:
        raise MemoryBridgeConfigError(
            "MAVAIA_MEMORY_ENCRYPTION_KEY is required for encrypted memory storage",
            context={"parameter": "MAVAIA_MEMORY_ENCRYPTION_KEY"},
        )

    raw: bytes
    normalized = key_str
    if normalized.lower().startswith("hex:"):
        normalized = normalized[4:].strip()

    # Hex (64 chars)
    hex_chars = "0123456789abcdefABCDEF"
    if len(normalized) == 64 and all(c in hex_chars for c in normalized):
        raw = bytes.fromhex(normalized)
    else:
        # Base64 / base64url
        b64 = normalized
        # Add padding if missing
        padding = "=" * ((4 - (len(b64) % 4)) % 4)
        b64_padded = b64 + padding
        try:
            raw = base64.urlsafe_b64decode(b64_padded.encode("utf-8"))
        except Exception as e:
            raise MemoryBridgeConfigError(
                "Invalid MAVAIA_MEMORY_ENCRYPTION_KEY: expected base64url/base64 or 64-char hex",
                context={"parameter": "MAVAIA_MEMORY_ENCRYPTION_KEY"},
            ) from e

    if len(raw) != 32:
        raise MemoryBridgeConfigError(
            "Invalid MAVAIA_MEMORY_ENCRYPTION_KEY length: must decode to 32 bytes (AES-256-GCM)",
            context={"decoded_len": str(len(raw))},
        )
    return raw


class MemoryBridgeService:
    """
    Encrypted LMDB-backed memory store.

    Design notes:
    - All values are encrypted and authenticated (AES-GCM).
    - Keys remain plaintext (to allow listing and prefix scans).
    - Each category uses its own LMDB named database for isolation.
    - Vector index is optional and uses brute-force cosine similarity search.
    """

    _ENC_VERSION = 1
    _NONCE_SIZE = 12  # AESGCM standard nonce size

    def __init__(self, config: MemoryBridgeConfig):
        self.config = config
        self._lock = threading.RLock()
        self._env = None
        self._dbs: dict[MemoryCategory, Any] = {}
        self._aesgcm = None

    def initialize(self) -> None:
        """
        Initialize LMDB environment and crypto.

        Raises:
            MemoryBridgeDependencyError: If `lmdb` or `cryptography` is missing.
            MemoryBridgeConfigError: If config is invalid.
        """
        try:
            import lmdb  # type: ignore
        except ImportError as e:
            raise MemoryBridgeDependencyError(
                "Missing dependency: lmdb (install with `pip install lmdb`)",
                context={"dependency": "lmdb"},
            ) from e

        try:
            from cryptography.hazmat.primitives.ciphers.aead import AESGCM  # type: ignore
        except ImportError as e:
            raise MemoryBridgeDependencyError(
                "Missing dependency: cryptography (install with `pip install cryptography`)",
                context={"dependency": "cryptography"},
            ) from e

        if not isinstance(self.config.lmdb_path, Path):
            raise MemoryBridgeConfigError("lmdb_path must be a pathlib.Path")

        if self.config.map_size_mb <= 0:
            raise MemoryBridgeConfigError(
                "map_size_mb must be positive", context={"map_size_mb": str(self.config.map_size_mb)}
            )

        if len(self.config.encryption_key) != 32:
            raise MemoryBridgeConfigError(
                "encryption_key must be 32 bytes", context={"len": str(len(self.config.encryption_key))}
            )

        with self._lock:
            if self._env is not None:
                return

            self.config.lmdb_path.mkdir(parents=True, exist_ok=True)
            map_size_bytes = int(self.config.map_size_mb) * 1024 * 1024

            self._env = lmdb.open(
                str(self.config.lmdb_path),
                map_size=map_size_bytes,
                max_dbs=self.config.max_dbs,
                subdir=True,
                lock=True,
                readahead=True,
                metasync=True,
                sync=True,
            )

            # Create named DBs. Always create the core categories; vector index optional.
            self._dbs = {
                MemoryCategory.SEMANTIC: self._env.open_db(b"semantic", create=True),
                MemoryCategory.EPISODIC: self._env.open_db(b"episodic", create=True),
                MemoryCategory.IDENTITY: self._env.open_db(b"identity", create=True),
                MemoryCategory.SKILL: self._env.open_db(b"skill", create=True),
                MemoryCategory.LONG_TERM_STATE: self._env.open_db(b"long_term_state", create=True),
                MemoryCategory.REFLECTION_LOG: self._env.open_db(b"reflection_log", create=True),
            }
            if self.config.enable_vector_index:
                self._dbs[MemoryCategory.VECTOR_INDEX] = self._env.open_db(b"vector_index", create=True)

            self._aesgcm = AESGCM(self.config.encryption_key)

            logger.info(
                "MemoryBridgeService initialized",
                extra={
                    "lmdb_path": str(self.config.lmdb_path),
                    "map_size_mb": self.config.map_size_mb,
                    "enable_vector_index": self.config.enable_vector_index,
                },
            )

    def close(self) -> None:
        """Close LMDB environment."""
        with self._lock:
            if self._env is not None:
                try:
                    self._env.close()
                finally:
                    self._env = None
                    self._dbs = {}
                    self._aesgcm = None

    def health_check(self) -> dict[str, Any]:
        """Return a simple health summary for monitoring/debugging."""
        with self._lock:
            initialized = self._env is not None and self._aesgcm is not None
            return {
                "initialized": initialized,
                "lmdb_path": str(self.config.lmdb_path),
                "map_size_mb": self.config.map_size_mb,
                "enable_vector_index": self.config.enable_vector_index,
                "categories": [c.value for c in self._dbs.keys()],
                "encryption": {"scheme": "AES-256-GCM", "version": self._ENC_VERSION},
            }

    def put(
        self,
        category: MemoryCategory,
        memory_id: str,
        data: dict[str, Any],
        *,
        metadata: Optional[dict[str, Any]] = None,
    ) -> None:
        """
        Store/overwrite a memory record in a category.

        Args:
            category: Memory category.
            memory_id: Unique key within category.
            data: JSON-serializable record payload.
            metadata: Optional metadata dictionary.
        """
        self._require_initialized()
        _validate_identifier("memory_id", memory_id)

        now = time.time()
        envelope = {
            "schema_version": 1,
            "category": category.value,
            "id": memory_id,
            "data": data,
            "metadata": metadata or {},
            "updated_at": now,
        }
        key = memory_id.encode("utf-8")
        value = self._encrypt_json(envelope, aad=self._aad(category, memory_id))

        with self._lock:
            db = self._get_db(category)
            try:
                with self._env.begin(write=True, db=db) as txn:
                    txn.put(key, value)
            except Exception as e:
                raise MemoryBridgeOperationError(
                    "Failed to write memory record",
                    context={"category": category.value, "id": memory_id},
                ) from e

    def get(self, category: MemoryCategory, memory_id: str) -> Optional[dict[str, Any]]:
        """Load a memory record; returns None if not found."""
        self._require_initialized()
        _validate_identifier("memory_id", memory_id)

        key = memory_id.encode("utf-8")
        with self._lock:
            db = self._get_db(category)
            try:
                with self._env.begin(write=False, db=db) as txn:
                    raw = txn.get(key)
            except Exception as e:
                raise MemoryBridgeOperationError(
                    "Failed to read memory record",
                    context={"category": category.value, "id": memory_id},
                ) from e

        if raw is None:
            return None

        try:
            obj = self._decrypt_json(raw, aad=self._aad(category, memory_id))
        except Exception as e:
            raise MemoryBridgeOperationError(
                "Failed to decrypt memory record",
                context={"category": category.value, "id": memory_id},
            ) from e

        return obj

    def delete(self, category: MemoryCategory, memory_id: str) -> bool:
        """Delete a memory record; returns True if something was deleted."""
        self._require_initialized()
        _validate_identifier("memory_id", memory_id)
        key = memory_id.encode("utf-8")

        with self._lock:
            db = self._get_db(category)
            try:
                with self._env.begin(write=True, db=db) as txn:
                    existed = txn.delete(key)
                return bool(existed)
            except Exception as e:
                raise MemoryBridgeOperationError(
                    "Failed to delete memory record",
                    context={"category": category.value, "id": memory_id},
                ) from e

    def list_ids(
        self,
        category: MemoryCategory,
        *,
        limit: Optional[int] = None,
        prefix: str | None = None,
    ) -> list[str]:
        """
        List record IDs in a category (optionally prefix-filtered).

        Note: This does not decrypt records.
        """
        self._require_initialized()
        if limit is not None and limit <= 0:
            raise InvalidParameterError(parameter="limit", value=str(limit), reason="Must be > 0")

        prefix_b = prefix.encode("utf-8") if prefix is not None else None
        results: list[str] = []

        with self._lock:
            db = self._get_db(category)
            try:
                with self._env.begin(write=False, db=db) as txn:
                    with txn.cursor() as cur:
                        if prefix_b is not None:
                            if not cur.set_range(prefix_b):
                                return []
                            for k, _v in cur:
                                if not k.startswith(prefix_b):
                                    break
                                results.append(k.decode("utf-8"))
                                if limit is not None and len(results) >= limit:
                                    break
                        else:
                            for k, _v in cur:
                                results.append(k.decode("utf-8"))
                                if limit is not None and len(results) >= limit:
                                    break
            except Exception as e:
                raise MemoryBridgeOperationError(
                    "Failed to list IDs",
                    context={"category": category.value, "limit": str(limit), "prefix": str(prefix)},
                ) from e

        return results

    def append_reflection_log(
        self,
        log_id: str,
        entry: dict[str, Any],
        *,
        timestamp: float | None = None,
    ) -> str:
        """
        Append an entry to a reflection log stream.

        Stored as separate items under the REFLECTION_LOG DB using a sortable key.

        Returns:
            The generated item key (useful for audit trails).
        """
        self._require_initialized()
        _validate_identifier("log_id", log_id)

        ts = float(timestamp if timestamp is not None else time.time())
        item_id = uuid.uuid4().hex
        item_key = f"{log_id}:{ts:.6f}:{item_id}"

        envelope = {
            "schema_version": 1,
            "category": MemoryCategory.REFLECTION_LOG.value,
            "log_id": log_id,
            "item_key": item_key,
            "timestamp": ts,
            "entry": entry,
        }
        value = self._encrypt_json(envelope, aad=self._aad(MemoryCategory.REFLECTION_LOG, item_key))

        with self._lock:
            db = self._get_db(MemoryCategory.REFLECTION_LOG)
            try:
                with self._env.begin(write=True, db=db) as txn:
                    txn.put(item_key.encode("utf-8"), value)
            except Exception as e:
                raise MemoryBridgeOperationError(
                    "Failed to append reflection log entry",
                    context={"log_id": log_id},
                ) from e

        return item_key

    def read_reflection_log(
        self,
        log_id: str,
        *,
        limit: int = 100,
    ) -> list[dict[str, Any]]:
        """Read up to `limit` reflection log entries for a log stream."""
        self._require_initialized()
        _validate_identifier("log_id", log_id)
        if limit <= 0:
            raise InvalidParameterError(parameter="limit", value=str(limit), reason="Must be > 0")

        prefix = f"{log_id}:".encode("utf-8")
        out: list[dict[str, Any]] = []

        with self._lock:
            db = self._get_db(MemoryCategory.REFLECTION_LOG)
            try:
                with self._env.begin(write=False, db=db) as txn:
                    with txn.cursor() as cur:
                        if not cur.set_range(prefix):
                            return []
                        for k, v in cur:
                            if not k.startswith(prefix):
                                break
                            key_str = k.decode("utf-8")
                            obj = self._decrypt_json(v, aad=self._aad(MemoryCategory.REFLECTION_LOG, key_str))
                            out.append(obj)
                            if len(out) >= limit:
                                break
            except Exception as e:
                raise MemoryBridgeOperationError(
                    "Failed to read reflection log",
                    context={"log_id": log_id},
                ) from e

        return out

    def upsert_vector(
        self,
        vector_id: str,
        vector: list[float],
        *,
        metadata: Optional[dict[str, Any]] = None,
    ) -> None:
        """
        Insert/update a vector in the local vector index.

        Requires enable_vector_index=True.
        """
        self._require_initialized()
        if not self.config.enable_vector_index:
            raise MemoryBridgeConfigError(
                "Vector index is disabled (set MAVAIA_MEMORY_ENABLE_VECTOR_INDEX=true)",
                context={"enable_vector_index": "false"},
            )

        _validate_identifier("vector_id", vector_id)
        if not isinstance(vector, list) or not vector:
            raise InvalidParameterError(parameter="vector", value=str(type(vector)), reason="Must be a non-empty list[float]")
        if any(not isinstance(x, (int, float)) for x in vector):
            raise InvalidParameterError(parameter="vector", value="(non-float elements)", reason="All elements must be int/float")

        envelope = {
            "schema_version": 1,
            "category": MemoryCategory.VECTOR_INDEX.value,
            "id": vector_id,
            "vector": [float(x) for x in vector],
            "metadata": metadata or {},
            "updated_at": time.time(),
        }
        key = vector_id.encode("utf-8")
        value = self._encrypt_json(envelope, aad=self._aad(MemoryCategory.VECTOR_INDEX, vector_id))

        with self._lock:
            db = self._get_db(MemoryCategory.VECTOR_INDEX)
            try:
                with self._env.begin(write=True, db=db) as txn:
                    txn.put(key, value)
            except Exception as e:
                raise MemoryBridgeOperationError(
                    "Failed to upsert vector",
                    context={"vector_id": vector_id},
                ) from e

    def vector_search(
        self,
        query_vector: list[float],
        *,
        top_k: int = 10,
        min_score: float = 0.0,
    ) -> list[dict[str, Any]]:
        """
        Brute-force cosine similarity search over locally stored vectors.

        Returns:
            List of {"id": str, "score": float, "metadata": dict}.
        """
        self._require_initialized()
        if not self.config.enable_vector_index:
            raise MemoryBridgeConfigError(
                "Vector index is disabled (set MAVAIA_MEMORY_ENABLE_VECTOR_INDEX=true)",
                context={"enable_vector_index": "false"},
            )
        if top_k <= 0:
            raise InvalidParameterError(parameter="top_k", value=str(top_k), reason="Must be > 0")
        if not isinstance(min_score, (int, float)) or float(min_score) < -1.0 or float(min_score) > 1.0:
            raise InvalidParameterError(parameter="min_score", value=str(min_score), reason="Must be between -1.0 and 1.0")

        if not isinstance(query_vector, list) or not query_vector:
            raise InvalidParameterError(parameter="query_vector", value=str(type(query_vector)), reason="Must be a non-empty list[float]")
        if any(not isinstance(x, (int, float)) for x in query_vector):
            raise InvalidParameterError(parameter="query_vector", value="(non-float elements)", reason="All elements must be int/float")
        q = [float(x) for x in query_vector]

        try:
            import numpy as np  # type: ignore
            use_numpy = True
        except Exception:
            np = None
            use_numpy = False

        scored: list[tuple[str, float, dict[str, Any]]] = []
        with self._lock:
            db = self._get_db(MemoryCategory.VECTOR_INDEX)
            try:
                with self._env.begin(write=False, db=db) as txn:
                    with txn.cursor() as cur:
                        for k, v in cur:
                            vector_id = k.decode("utf-8")
                            obj = self._decrypt_json(
                                v, aad=self._aad(MemoryCategory.VECTOR_INDEX, vector_id)
                            )
                            vec = obj.get("vector")
                            if not isinstance(vec, list) or len(vec) != len(q):
                                continue
                            score = _cosine_similarity(q, vec, use_numpy=use_numpy, np=np)
                            if score >= float(min_score):
                                scored.append((vector_id, float(score), obj.get("metadata") or {}))
            except Exception as e:
                raise MemoryBridgeOperationError("Vector search failed") from e

        scored.sort(key=lambda t: t[1], reverse=True)
        scored = scored[:top_k]
        return [{"id": vid, "score": score, "metadata": md} for vid, score, md in scored]

    # ---- internals ----

    def _require_initialized(self) -> None:
        if self._env is None or self._aesgcm is None:
            raise MemoryBridgeConfigError(
                "MemoryBridgeService is not initialized (call initialize())",
                context={"operation": "initialize_required"},
            )

    def _get_db(self, category: MemoryCategory):
        if category not in self._dbs:
            raise MemoryBridgeConfigError(
                "Unsupported or disabled category",
                context={"category": category.value, "enable_vector_index": str(self.config.enable_vector_index)},
            )
        return self._dbs[category]

    def _aad(self, category: MemoryCategory, memory_id: str) -> bytes:
        # Prevent record swapping across keys/categories.
        return f"{category.value}:{memory_id}".encode("utf-8")

    def _encrypt_json(self, obj: dict[str, Any], *, aad: bytes) -> bytes:
        payload = json.dumps(obj, ensure_ascii=False, separators=(",", ":"), default=str).encode("utf-8")
        nonce = os.urandom(self._NONCE_SIZE)
        ciphertext = self._aesgcm.encrypt(nonce, payload, aad)
        # Format: [version_byte][nonce][ciphertext]
        return bytes([self._ENC_VERSION]) + nonce + ciphertext

    def _decrypt_json(self, blob: bytes, *, aad: bytes) -> dict[str, Any]:
        if not blob or len(blob) < 1 + self._NONCE_SIZE + 16:
            raise MemoryBridgeOperationError("Invalid ciphertext blob", context={"len": str(len(blob) if blob else 0)})
        ver = blob[0]
        if ver != self._ENC_VERSION:
            raise MemoryBridgeOperationError(
                "Unsupported encryption version", context={"version": str(ver), "expected": str(self._ENC_VERSION)}
            )
        nonce = blob[1 : 1 + self._NONCE_SIZE]
        ciphertext = blob[1 + self._NONCE_SIZE :]
        plaintext = self._aesgcm.decrypt(nonce, ciphertext, aad)
        obj = json.loads(plaintext.decode("utf-8"))
        if not isinstance(obj, dict):
            raise MemoryBridgeOperationError("Decrypted payload is not an object")
        return obj


def _validate_identifier(parameter: str, value: str) -> None:
    if not isinstance(value, str) or not value.strip():
        raise InvalidParameterError(parameter=parameter, value=str(value), reason="Must be a non-empty string")
    if len(value) > 512:
        raise InvalidParameterError(parameter=parameter, value=f"len={len(value)}", reason="Too long (max 512 chars)")
    # Prevent embedded NULLs that can cause issues in some runtimes/tools
    if "\x00" in value:
        raise InvalidParameterError(parameter=parameter, value="contains NUL", reason="Must not contain NUL bytes")


def _cosine_similarity(
    v1: list[float],
    v2: list[float],
    *,
    use_numpy: bool,
    np: Any,
) -> float:
    if len(v1) != len(v2) or not v1:
        return 0.0

    if use_numpy:
        a = np.asarray(v1, dtype=float)
        b = np.asarray(v2, dtype=float)
        denom = float(np.linalg.norm(a) * np.linalg.norm(b))
        if denom == 0.0:
            return 0.0
        return float(np.dot(a, b) / denom)

    dot = 0.0
    norm1 = 0.0
    norm2 = 0.0
    for x, y in zip(v1, v2):
        dot += float(x) * float(y)
        norm1 += float(x) * float(x)
        norm2 += float(y) * float(y)
    if norm1 == 0.0 or norm2 == 0.0:
        return 0.0
    return dot / ((norm1**0.5) * (norm2**0.5))

