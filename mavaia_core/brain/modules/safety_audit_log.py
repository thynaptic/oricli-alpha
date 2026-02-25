from __future__ import annotations
"""
Safety Audit Log - Immutable audit log system for all safety decisions
Provides tamper-proof logging for forensic analysis
"""

from typing import Any, Dict, List, Optional
import json
import hashlib
import time
from pathlib import Path
from dataclasses import dataclass, field, asdict

from mavaia_core.brain.base_module import BaseBrainModule, ModuleMetadata
from mavaia_core.exceptions import InvalidParameterError


@dataclass
class ServiceResult:
    """Service result for audit log"""
    service_id: str
    service_name: str
    detected: bool
    action: str
    severity: str
    confidence: float
    detected_patterns: List[str]
    duration: float
    success: bool
    error: Optional[str] = None


@dataclass
class FinalDecision:
    """Final decision for audit log"""
    action: str
    severity: str
    confidence: float
    service_id: str
    service_name: str
    replacement_response: Optional[str] = None


@dataclass
class AuditContext:
    """Audit context (privacy-preserving)"""
    conversation_id: Optional[str] = None
    message_id: Optional[str] = None
    timestamp: float = field(default_factory=time.time)
    metadata_keys: List[str] = field(default_factory=list)


@dataclass
class SafetyAuditLogEntry:
    """Immutable audit log entry"""
    id: str
    timestamp: float
    check_type: str  # "preCheck" or "postCheck"
    input_hash: str  # SHA256 hash of input
    input_length: int
    normalized_input: Optional[str] = None
    service_results: List[ServiceResult] = field(default_factory=list)
    final_decision: Optional[FinalDecision] = None
    context: Optional[AuditContext] = None
    metadata: Dict[str, str] = field(default_factory=dict)
    entry_hash: str = ""  # SHA256 hash of entire entry


class SafetyAuditLogModule(BaseBrainModule):
    """Immutable audit log manager"""

    def __init__(self):
        super().__init__()
        self.log_entries: List[SafetyAuditLogEntry] = []
        self.max_in_memory_entries = 1000
        self.log_directory = Path.home() / ".mavaia" / "SafetyAuditLogs"
        self.log_directory.mkdir(parents=True, exist_ok=True)

    @property
    def metadata(self) -> ModuleMetadata:
        return ModuleMetadata(
            name="safety_audit_log",
            version="1.0.0",
            description=(
                "Immutable audit log: tamper-proof logging for all safety decisions, "
                "forensic analysis, privacy-preserving context storage"
            ),
            operations=[
                "log_safety_decision",
                "get_recent_entries",
                "get_entry_by_id",
                "verify_entry_integrity",
            ],
            dependencies=[],
            model_required=False,
        )

    def initialize(self) -> bool:
        """Initialize the module"""
        # Load recent entries from disk
        self._load_recent_entries()
        return True

    def execute(self, operation: str, params: Dict[str, Any]) -> Dict[str, Any]:
        """Execute an audit log operation"""
        if operation == "log_safety_decision":
            check_type = params.get("check_type", "")
            input_text = params.get("input", "")
            normalized_input = params.get("normalized_input")
            service_results = params.get("service_results", [])
            final_decision = params.get("final_decision", {})
            context = params.get("context", {})
            entry = self.log_safety_decision(
                check_type, input_text, normalized_input, service_results, final_decision, context
            )
            return {"success": True, "entry_id": entry.id}
        elif operation == "get_recent_entries":
            limit = params.get("limit", 10)
            entries = self.get_recent_entries(limit)
            return {"success": True, "entries": [self._entry_to_dict(e) for e in entries]}
        elif operation == "get_entry_by_id":
            entry_id = params.get("entry_id", "")
            entry = self.get_entry_by_id(entry_id)
            if entry:
                return {"success": True, "entry": self._entry_to_dict(entry)}
            return {"success": False, "error": "Entry not found"}
        elif operation == "verify_entry_integrity":
            entry_id = params.get("entry_id", "")
            is_valid = self.verify_entry_integrity(entry_id)
            return {"success": True, "is_valid": is_valid}
        else:
            raise InvalidParameterError(
                parameter="operation",
                value=operation,
                reason="Unknown operation for safety_audit_log",
            )

    def log_safety_decision(
        self,
        check_type: str,
        input_text: str,
        normalized_input: Optional[str],
        service_results: List[Dict[str, Any]],
        final_decision: Dict[str, Any],
        context: Dict[str, Any],
    ) -> SafetyAuditLogEntry:
        """Log a safety check decision"""
        entry_id = f"entry_{int(time.time() * 1000)}"
        timestamp = time.time()

        # Hash the input for privacy
        input_hash = hashlib.sha256(input_text.encode("utf-8")).hexdigest()

        # Create audit context (privacy-preserving)
        audit_context = AuditContext(
            conversation_id=context.get("conversation_id"),
            message_id=context.get("message_id"),
            timestamp=context.get("timestamp", timestamp),
            metadata_keys=list(context.get("metadata", {}).keys()),
        )

        # Convert service results
        service_result_objects = [
            ServiceResult(**result) for result in service_results
        ]

        # Convert final decision
        final_decision_obj = FinalDecision(**final_decision) if final_decision else None

        # Create entry
        entry = SafetyAuditLogEntry(
            id=entry_id,
            timestamp=timestamp,
            check_type=check_type,
            input_hash=input_hash,
            input_length=len(input_text),
            normalized_input=normalized_input,
            service_results=service_result_objects,
            final_decision=final_decision_obj,
            context=audit_context,
            metadata={},
            entry_hash="",  # Will calculate below
        )

        # Calculate entry hash (tamper detection)
        entry_hash = self._calculate_entry_hash(entry)
        entry.entry_hash = entry_hash

        # Add to in-memory log
        self.log_entries.append(entry)

        # Trim if too large
        if len(self.log_entries) > self.max_in_memory_entries:
            entries_to_save = self.log_entries[: -self.max_in_memory_entries]
            self.log_entries = self.log_entries[-self.max_in_memory_entries :]
            self._save_entries_to_disk(entries_to_save)

        # Save critical entries immediately
        if final_decision_obj and final_decision_obj.action in ("hardStop", "escalation"):
            self._save_entry_to_disk(entry)

        return entry

    def get_recent_entries(self, limit: int = 10) -> List[SafetyAuditLogEntry]:
        """Get recent audit log entries"""
        return self.log_entries[-limit:] if self.log_entries else []

    def get_entry_by_id(self, entry_id: str) -> Optional[SafetyAuditLogEntry]:
        """Get entry by ID"""
        for entry in self.log_entries:
            if entry.id == entry_id:
                return entry
        return None

    def verify_entry_integrity(self, entry_id: str) -> bool:
        """Verify entry hasn't been tampered with"""
        entry = self.get_entry_by_id(entry_id)
        if not entry:
            return False

        # Recalculate hash
        expected_hash = self._calculate_entry_hash(entry)
        return entry.entry_hash == expected_hash

    def _calculate_entry_hash(self, entry: SafetyAuditLogEntry) -> str:
        """Calculate SHA256 hash of entry (for tamper detection)"""
        # Create a copy without the hash field
        entry_dict = {
            "id": entry.id,
            "timestamp": entry.timestamp,
            "check_type": entry.check_type,
            "input_hash": entry.input_hash,
            "input_length": entry.input_length,
            "normalized_input": entry.normalized_input,
            "service_results": [asdict(sr) for sr in entry.service_results],
            "final_decision": asdict(entry.final_decision) if entry.final_decision else None,
            "context": asdict(entry.context) if entry.context else None,
            "metadata": entry.metadata,
        }

        entry_json = json.dumps(entry_dict, sort_keys=True)
        return hashlib.sha256(entry_json.encode("utf-8")).hexdigest()

    def _save_entry_to_disk(self, entry: SafetyAuditLogEntry):
        """Save entry to disk"""
        log_file = self.log_directory / f"safety_audit_{int(entry.timestamp)}.json"
        with open(log_file, "w") as f:
            json.dump(self._entry_to_dict(entry), f, indent=2)

    def _save_entries_to_disk(self, entries: List[SafetyAuditLogEntry]):
        """Save multiple entries to disk"""
        for entry in entries:
            self._save_entry_to_disk(entry)

    def _load_recent_entries(self):
        """Load recent entries from disk"""
        # Load most recent log files
        log_files = sorted(self.log_directory.glob("safety_audit_*.json"), reverse=True)
        for log_file in log_files[:10]:  # Load last 10 files
            try:
                with open(log_file, "r") as f:
                    entry_dict = json.load(f)
                    entry = self._dict_to_entry(entry_dict)
                    self.log_entries.append(entry)
            except Exception:
                continue

    def _entry_to_dict(self, entry: SafetyAuditLogEntry) -> Dict[str, Any]:
        """Convert entry to dictionary"""
        return {
            "id": entry.id,
            "timestamp": entry.timestamp,
            "check_type": entry.check_type,
            "input_hash": entry.input_hash,
            "input_length": entry.input_length,
            "normalized_input": entry.normalized_input,
            "service_results": [asdict(sr) for sr in entry.service_results],
            "final_decision": asdict(entry.final_decision) if entry.final_decision else None,
            "context": asdict(entry.context) if entry.context else None,
            "metadata": entry.metadata,
            "entry_hash": entry.entry_hash,
        }

    def _dict_to_entry(self, entry_dict: Dict[str, Any]) -> SafetyAuditLogEntry:
        """Convert dictionary to entry"""
        return SafetyAuditLogEntry(
            id=entry_dict["id"],
            timestamp=entry_dict["timestamp"],
            check_type=entry_dict["check_type"],
            input_hash=entry_dict["input_hash"],
            input_length=entry_dict["input_length"],
            normalized_input=entry_dict.get("normalized_input"),
            service_results=[
                ServiceResult(**sr) for sr in entry_dict.get("service_results", [])
            ],
            final_decision=FinalDecision(**entry_dict["final_decision"])
            if entry_dict.get("final_decision")
            else None,
            context=AuditContext(**entry_dict["context"]) if entry_dict.get("context") else None,
            metadata=entry_dict.get("metadata", {}),
            entry_hash=entry_dict.get("entry_hash", ""),
        )

