from __future__ import annotations

from datetime import datetime, timezone
import json
from pathlib import Path
from typing import Any, Mapping, Sequence

from ovc.development.identity import canonical_json_bytes, canonical_sha256
from ovc.development.skills.siq_core import QueueState


def build_siq_receipt(
    *,
    state: QueueState,
    event: str,
    packet_id: str | None = None,
    movement_classification: str | None = None,
    assurance_reused: Sequence[str] = (),
    assurance_rerun: Sequence[str] = (),
    decision: str,
    merge_sha: str | None = None,
    reason_codes: Sequence[str] = (),
    observed_at_utc: str | None = None,
) -> dict[str, Any]:
    target = next((row for row in state.candidates if row.packet_id == packet_id), None)
    logical = {
        "queue_id": state.queue_id,
        "queue_generation": state.generation,
        "event": str(event),
        "packet_id": None if packet_id is None else str(packet_id),
        "ready_sequence": target.ready_sequence if target else None,
        "candidate_head_sha": target.candidate_head_sha if target else None,
        "queue_state": target.queue_state if target else None,
        "lease_state": "HELD" if state.lease_holder_packet_id else "FREE",
        "lease_holder_packet_id": state.lease_holder_packet_id,
        "movement_classification": movement_classification,
        "assurance_reused": sorted(map(str, assurance_reused)),
        "assurance_rerun": sorted(map(str, assurance_rerun)),
        "decision": str(decision),
        "merge_sha": merge_sha,
        "reason_codes": sorted(map(str, reason_codes)),
        "parallel_merge": False,
        "merge_authority": "NONE",
        "scientific_governance_authority": "NONE",
        "observability_only": True,
        "ready_status_is_authority": False,
        "queue_position_is_authority": False,
        "lease_ownership_is_authority": False,
        "successful_assurance_is_authority": False,
        "orchestration_selection_is_authority": False,
        "execution_started_observed": False,
        "execution_completed_observed": False,
    }
    payload = {
        "schema": "ovc-serialized-integration-queue-diagnostic-receipt/v1",
        "observed_at_utc": observed_at_utc
        or datetime.now(timezone.utc).isoformat(timespec="microseconds").replace("+00:00", "Z"),
        **logical,
        "authority_effect": "NONE_OBSERVABILITY_ONLY",
    }
    payload["record_id"] = canonical_sha256(logical, role="SIQ_DIAGNOSTIC_RECEIPT")
    return payload


def persist_siq_receipt(receipt: Mapping[str, Any], root: Path | str) -> Path:
    if receipt.get("schema") != "ovc-serialized-integration-queue-diagnostic-receipt/v1":
        raise ValueError("unsupported SIQ receipt schema")
    if receipt.get("observability_only") is not True:
        raise ValueError("SIQ receipts must remain observability only")
    if receipt.get("merge_authority") != "NONE":
        raise ValueError("SIQ receipt cannot carry merge authority")
    if receipt.get("authority_effect") != "NONE_OBSERVABILITY_ONLY":
        raise ValueError("SIQ receipt cannot carry governance authority")
    path = Path(root) / f"SIQ_DIAGNOSTIC_{receipt['record_id']}.json"
    path.parent.mkdir(parents=True, exist_ok=True)
    data = canonical_json_bytes(dict(receipt)) + b"\n"
    if path.exists() and path.read_bytes() != data:
        raise ValueError("SIQ receipt identity collision")
    if not path.exists():
        path.write_bytes(data)
    return path


def load_siq_receipt(path: Path | str) -> dict[str, Any]:
    value = json.loads(Path(path).read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise ValueError("SIQ receipt root must be an object")
    if value.get("schema") != "ovc-serialized-integration-queue-diagnostic-receipt/v1":
        raise ValueError("unsupported SIQ receipt schema")
    if value.get("observability_only") is not True or value.get("merge_authority") != "NONE":
        raise ValueError("SIQ receipt authority separation violated")
    return value
