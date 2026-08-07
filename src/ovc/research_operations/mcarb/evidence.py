from __future__ import annotations
from dataclasses import dataclass
from typing import Any, Iterable
from .models import canonical_hash

@dataclass(frozen=True)
class EvidenceEnvelope:
    record_type: str
    source_release_id: str
    source_record_ids: tuple[str, ...]
    admissible_cutoff: str
    payload: dict[str, Any]
    artifact_refs: tuple[dict[str, Any], ...] = ()

    @property
    def record_id(self) -> str:
        return "MCARB.EVIDENCE." + canonical_hash({
            "record_type":self.record_type,
            "source_release_id":self.source_release_id,
            "source_record_ids":self.source_record_ids,
            "admissible_cutoff":self.admissible_cutoff,
            "payload":self.payload,
            "artifact_refs":self.artifact_refs,
        })[:24]

    def to_dict(self) -> dict[str, Any]:
        return {
            "record_id":self.record_id,"record_type":self.record_type,"schema_version":"v1",
            "source_release_id":self.source_release_id,"source_record_ids":list(self.source_record_ids),
            "admissible_cutoff":self.admissible_cutoff,"payload":self.payload,
            "artifact_refs":list(self.artifact_refs),"authority":"RESEARCH_EVIDENCE_ONLY",
        }


def validate_external_artifact_ref(ref: dict[str, Any]) -> None:
    required={"artifact_id","sha256","size_bytes","media_type","storage_class"}
    if set(ref) != required:
        raise ValueError("external artifact ref must have exact compact fields")
    sha=str(ref["sha256"])
    if len(sha) != 64 or any(ch not in "0123456789abcdef" for ch in sha):
        raise ValueError("artifact sha256 must be lowercase hex")
    if int(ref["size_bytes"]) < 0:
        raise ValueError("artifact size must be non-negative")
    text="|".join(str(value) for value in ref.values())
    if "://" in text or text.startswith("/") or "\\Users\\" in text or "/home/" in text:
        raise ValueError("signed URLs and machine-specific absolute paths are prohibited")


def append_audit_event(existing: Iterable[dict[str, Any]], event: dict[str, Any]) -> tuple[dict[str, Any], ...]:
    ledger=tuple(existing)
    if "event_id" not in event or not event["event_id"]:
        raise ValueError("event_id required")
    if any(item.get("event_id") == event["event_id"] for item in ledger):
        raise ValueError("append-only audit event identity already exists")
    return ledger + (dict(event),)
