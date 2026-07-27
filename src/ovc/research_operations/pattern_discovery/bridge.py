from __future__ import annotations

import json
import os
import secrets
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Mapping, Protocol

from ovc.research_operations.canonical import canonical_json_bytes, canonical_sha256

from .models import PatternDiscoveryError, parse_utc
from .review import EVIDENCE_CLASSES


class EvidenceBridgeError(PatternDiscoveryError):
    pass


class OperatorSigner(Protocol):
    algorithm: str
    operator_id: str

    def sign(self, payload: bytes) -> str: ...


@dataclass(frozen=True)
class AppendRequest:
    append_request_id: str
    operator_id: str
    session_id: str
    nonce: str
    expected_sequence_number: int
    candidate_window_id: str
    candidate_fingerprint_hash: str
    source_release_ids: tuple[str, ...]
    source_record_ids: tuple[str, ...]
    admissible_cutoff: str
    record_class: str
    record_body: Mapping[str, Any]
    requested_at: str
    ui_build_hash: str
    operation_mode: str = "LIVE_PROSPECTIVE"

    @property
    def record_body_hash(self) -> str:
        return canonical_sha256(dict(self.record_body))

    def canonical_payload(self) -> dict[str, Any]:
        return {
            "append_request_id": self.append_request_id,
            "operator_id": self.operator_id,
            "session_id": self.session_id,
            "nonce": self.nonce,
            "expected_sequence_number": self.expected_sequence_number,
            "candidate_window_id": self.candidate_window_id,
            "candidate_fingerprint_hash": self.candidate_fingerprint_hash,
            "source_release_ids": sorted(self.source_release_ids),
            "source_record_ids": sorted(self.source_record_ids),
            "admissible_cutoff": self.admissible_cutoff,
            "record_class": self.record_class,
            "record_body_hash": self.record_body_hash,
            "requested_at": self.requested_at,
            "ui_build_hash": self.ui_build_hash,
            "operation_mode": self.operation_mode,
        }


class SourceResolver:
    def __init__(self, candidates: Mapping[str, Mapping[str, Any]], fingerprints: Mapping[str, Mapping[str, Any]]) -> None:
        self.candidates = candidates
        self.fingerprints = fingerprints

    def resolve(self, candidate_window_id: str, fingerprint_id: str) -> dict[str, Any]:
        candidate = self.candidates.get(candidate_window_id)
        fingerprint = self.fingerprints.get(fingerprint_id)
        if not candidate or not fingerprint:
            raise EvidenceBridgeError("immutable candidate or fingerprint source is unresolved")
        if fingerprint.get("candidate_window_id") != candidate_window_id:
            raise EvidenceBridgeError("candidate/fingerprint mismatch")
        source_release_ids = sorted({
            str(candidate.get("source_release_id") or ""),
            str(fingerprint.get("source_release_id") or ""),
        } - {""})
        source_record_ids = sorted(set(str(item) for item in candidate.get("source_c2_record_ids", ()) if item))
        if not source_release_ids or not source_record_ids:
            raise EvidenceBridgeError("source lineage is incomplete")
        return {
            "candidate_window_id": candidate_window_id,
            "candidate_fingerprint_hash": canonical_sha256(dict(fingerprint)),
            "source_release_ids": source_release_ids,
            "source_record_ids": source_record_ids,
            "admissible_cutoff": candidate.get("trigger_first_valid_at"),
            "operation_mode": candidate.get("operation_mode"),
        }


class LocalEvidenceBridge:
    """Candidate local-loopback evidence service.

    Canonical writes are disabled until an operator gate activates the bridge. In
    candidate mode, tests may commit non-canonical transaction envelopes to an
    isolated temporary root to verify validation, idempotency and atomicity.
    """

    def __init__(
        self,
        root: str | Path,
        *,
        signer: OperatorSigner,
        service_build_hash: str,
        write_authority: bool = False,
        candidate_test_mode: bool = False,
    ) -> None:
        if signer.algorithm != "ED25519":
            raise EvidenceBridgeError("operator signer must declare ED25519")
        self.root = Path(root)
        self.signer = signer
        self.service_build_hash = service_build_hash
        self.write_authority = write_authority
        self.candidate_test_mode = candidate_test_mode
        self.transactions = self.root / "transactions"
        self.requests = self.root / "requests"
        self.session_token = secrets.token_urlsafe(24)

    def _request_path(self, request_id: str) -> Path:
        return self.requests / f"{request_id}.json"

    def _transaction_path(self, sequence: int, request_id: str) -> Path:
        return self.transactions / f"{sequence:012d}-{request_id}.json"

    def _existing_requests(self) -> list[dict[str, Any]]:
        if not self.requests.exists():
            return []
        return [json.loads(path.read_text(encoding="utf-8")) for path in sorted(self.requests.glob("*.json"))]

    def _current_sequence(self) -> int:
        if not self.transactions.exists():
            return 0
        sequences = [int(path.name.split("-", 1)[0]) for path in self.transactions.glob("*.json")]
        return max(sequences, default=0)

    def status(self, append_request_id: str) -> dict[str, Any] | None:
        path = self._request_path(append_request_id)
        return json.loads(path.read_text(encoding="utf-8")) if path.exists() else None

    def submit(self, request: AppendRequest, *, session_token: str, freeze_confirmed: bool) -> dict[str, Any]:
        if session_token != self.session_token:
            raise EvidenceBridgeError("invalid local session token")
        if not freeze_confirmed:
            raise EvidenceBridgeError("explicit freeze confirmation is required")
        existing = self.status(request.append_request_id)
        if existing:
            if existing.get("request_hash") != canonical_sha256(request.canonical_payload()):
                raise EvidenceBridgeError("append_request_id reused with different payload")
            return existing
        body_hash_matches = [item for item in self._existing_requests() if item.get("record_body_hash") == request.record_body_hash]
        if body_hash_matches:
            raise EvidenceBridgeError("same evidence body cannot be resubmitted under a new request ID")
        if not self.write_authority and not self.candidate_test_mode:
            raise EvidenceBridgeError("OPERATOR_GATE_REQUIRED: evidence bridge write authority is disabled")
        result = self._validate(request)
        if result is not None:
            return self._persist_request_result(request, "REJECTED", rejection_reason=result)
        return self._commit_transaction(request)

    def _validate(self, request: AppendRequest) -> str | None:
        if request.operator_id != self.signer.operator_id:
            return "UNKNOWN_OPERATOR"
        if request.record_class not in EVIDENCE_CLASSES:
            return "UNKNOWN_RECORD_CLASS"
        if request.operation_mode != "LIVE_PROSPECTIVE":
            return "REPLAY_OR_FIXTURE_CONTAMINATION"
        if request.expected_sequence_number != self._current_sequence() + 1:
            return "UNEXPECTED_SEQUENCE"
        if not request.nonce or any(item.get("nonce") == request.nonce for item in self._existing_requests()):
            return "DUPLICATE_NONCE"
        if not request.source_release_ids or not request.source_record_ids:
            return "MISSING_SOURCE_LINEAGE"
        try:
            if parse_utc(request.admissible_cutoff) > parse_utc(request.requested_at):
                return "INADMISSIBLE_CUTOFF"
        except PatternDiscoveryError:
            return "INVALID_TIMESTAMP"
        forbidden = {"probability", "exposure", "trade", "trading", "execution", "risk", "position"}
        body_keys = {str(key).lower() for key in request.record_body.keys()}
        if body_keys & forbidden:
            return "PROHIBITED_EXPOSURE_FIELD"
        return None

    def _persist_request_result(self, request: AppendRequest, status: str, *, rejection_reason: str | None = None) -> dict[str, Any]:
        self.requests.mkdir(parents=True, exist_ok=True)
        result = {
            "append_request_id": request.append_request_id,
            "status": status,
            "request_hash": canonical_sha256(request.canonical_payload()),
            "record_body_hash": request.record_body_hash,
            "nonce": request.nonce,
            "rejection_reason": rejection_reason,
        }
        self._atomic_write(self._request_path(request.append_request_id), result)
        return result

    def _commit_transaction(self, request: AppendRequest) -> dict[str, Any]:
        sequence = self._current_sequence() + 1
        previous_hash = "GENESIS"
        existing = sorted(self.transactions.glob("*.json")) if self.transactions.exists() else []
        if existing:
            previous_hash = json.loads(existing[-1].read_text(encoding="utf-8"))["audit_event"]["event_hash"]
        evidence = {
            "record_id": f"C2EVID-{request.record_body_hash[:24]}",
            "record_class": request.record_class,
            "body": dict(request.record_body),
            "operator_id": request.operator_id,
            "candidate_window_id": request.candidate_window_id,
            "candidate_fingerprint_hash": request.candidate_fingerprint_hash,
            "source_release_ids": sorted(request.source_release_ids),
            "source_record_ids": sorted(request.source_record_ids),
            "admissible_cutoff": request.admissible_cutoff,
            "frozen_at": request.requested_at,
            "authority_state": "CANDIDATE_TEST_ONLY" if self.candidate_test_mode and not self.write_authority else "FROZEN",
        }
        request_hash = canonical_sha256(request.canonical_payload())
        audit_unsigned = {
            "event_id": f"PDAUD-{request_hash[:24]}",
            "previous_event_hash": previous_hash,
            "sequence_number": sequence,
            "operator_id": request.operator_id,
            "action": "APPEND_C2_PATTERN_DISCOVERY_EVIDENCE",
            "object_id": evidence["record_id"],
            "request_hash": request_hash,
            "result": "COMMITTED",
            "timestamp": request.requested_at,
            "service_build_hash": self.service_build_hash,
        }
        event_hash = canonical_sha256(audit_unsigned)
        signature = self.signer.sign(canonical_json_bytes({**audit_unsigned, "event_hash": event_hash}))
        transaction = {
            "transaction_version": "PD.EVIDENCE.TRANSACTION.v0.1",
            "canonical": bool(self.write_authority),
            "evidence_record": evidence,
            "audit_event": {**audit_unsigned, "event_hash": event_hash, "signature": signature, "signature_algorithm": "ED25519"},
        }
        self.transactions.mkdir(parents=True, exist_ok=True)
        self._atomic_write(self._transaction_path(sequence, request.append_request_id), transaction)
        return self._persist_request_result(request, "COMMITTED") | {
            "sequence_number": sequence,
            "evidence_record_id": evidence["record_id"],
            "audit_event_hash": event_hash,
            "canonical": bool(self.write_authority),
        }

    @staticmethod
    def _atomic_write(path: Path, payload: Mapping[str, Any]) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        temporary = path.with_suffix(path.suffix + f".{os.getpid()}.tmp")
        temporary.write_bytes(canonical_json_bytes(dict(payload), trailing_newline=True))
        os.replace(temporary, path)
