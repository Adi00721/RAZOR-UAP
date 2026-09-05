import hashlib
import json
import time
from typing import List, Dict, Any, Optional
from pydantic import BaseModel

class AuditEntry(BaseModel):
    index: int
    timestamp: float
    iso_time: str
    trace_id: str
    event_type: str
    actor: str
    payload: Dict[str, Any]
    previous_hash: str
    entry_hash: str

class AuditLedger:
    def __init__(self, storage_path: Optional[str] = None):
        self.storage_path = storage_path
        self.chain: List[AuditEntry] = []
        self._initialize_genesis()

    def _initialize_genesis(self):
        genesis_entry = AuditEntry(
            index=0,
            timestamp=time.time(),
            iso_time=time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
            trace_id="TRC-GENESIS-000",
            event_type="GENESIS_BLOCK",
            actor="SYSTEM_RAZORUAP",
            payload={"message": "RazorUAP Immutable Audit Trail Initialized for Buildathon 2026"},
            previous_hash="0" * 64,
            entry_hash="0000000000000000000000000000000000000000000000000000000000000000"
        )
        self.chain.append(genesis_entry)

    def _compute_hash(self, index: int, timestamp: float, trace_id: str, event_type: str, actor: str, payload: Dict[str, Any], previous_hash: str) -> str:
        serialized = json.dumps({
            "index": index,
            "timestamp": timestamp,
            "trace_id": trace_id,
            "event_type": event_type,
            "actor": actor,
            "payload": payload,
            "previous_hash": previous_hash
        }, sort_keys=True)
        return hashlib.sha256(serialized.encode("utf-8")).hexdigest()

    def record_event(self, trace_id: str, event_type: str, actor: str, payload: Dict[str, Any]) -> AuditEntry:
        last_entry = self.chain[-1]
        new_index = last_entry.index + 1
        now_ts = time.time()
        iso_str = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime(now_ts))
        prev_hash = last_entry.entry_hash

        new_hash = self._compute_hash(
            index=new_index,
            timestamp=now_ts,
            trace_id=trace_id,
            event_type=event_type,
            actor=actor,
            payload=payload,
            previous_hash=prev_hash
        )

        entry = AuditEntry(
            index=new_index,
            timestamp=now_ts,
            iso_time=iso_str,
            trace_id=trace_id,
            event_type=event_type,
            actor=actor,
            payload=payload,
            previous_hash=prev_hash,
            entry_hash=new_hash
        )

        self.chain.append(entry)
        return entry

    def verify_integrity(self) -> Dict[str, Any]:
        """Validates that the entire cryptographic chain is untampered, with explicit Genesis block handling."""
        if not self.chain:
            return {"is_valid": False, "error_at_index": 0, "reason": "Audit ledger chain is empty"}

        # Explicit special-case validation for Genesis Block (#0)
        genesis = self.chain[0]
        if (
            genesis.index != 0 or
            genesis.event_type != "GENESIS_BLOCK" or
            genesis.previous_hash != "0" * 64 or
            genesis.entry_hash != "0" * 64
        ):
            return {
                "is_valid": False,
                "error_at_index": 0,
                "reason": "Corrupted Genesis Block (#0): Invalid index, event_type, or sentinel hash"
            }

        # Validate cryptographic link and hash integrity for all subsequent blocks (#1..N)
        for i in range(1, len(self.chain)):
            curr = self.chain[i]
            prev = self.chain[i - 1]

            if curr.previous_hash != prev.entry_hash:
                return {
                    "is_valid": False,
                    "error_at_index": i,
                    "reason": f"Broken chain link at block {i}: previous_hash mismatch"
                }

            expected_hash = self._compute_hash(
                curr.index, curr.timestamp, curr.trace_id, curr.event_type, curr.actor, curr.payload, curr.previous_hash
            )
            if curr.entry_hash != expected_hash:
                return {
                    "is_valid": False,
                    "error_at_index": i,
                    "reason": f"Corrupted payload hash at block {i}"
                }

        return {
            "is_valid": True,
            "total_blocks": len(self.chain),
            "chain_head": self.chain[-1].entry_hash
        }

    def get_entries(self, trace_id: Optional[str] = None, limit: int = 100) -> List[AuditEntry]:
        if trace_id:
            filtered = [e for e in self.chain if e.trace_id == trace_id]
            return filtered[-limit:]
        return self.chain[-limit:]

audit_ledger = AuditLedger()
