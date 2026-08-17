from __future__ import annotations

from copy import deepcopy
import hashlib
from typing import Any, Iterable, Mapping

from .core import canonical_json_bytes


class RCCRCloseoutError(ValueError):
    """Raised when RCCR terminal closeout evidence is incomplete or authority-unsafe."""


def _digest(value: Any) -> str:
    return hashlib.sha256(canonical_json_bytes(value)).hexdigest()


def _stable(rows: Iterable[Mapping[str, Any]]) -> list[dict[str, Any]]:
    values = [deepcopy(dict(row)) for row in rows]
    values.sort(key=canonical_json_bytes)
    return values


def reconcile_source_frontier(
    *,
    admission_manifest: Mapping[str, Any],
    bootstrap_wave: Mapping[str, Any],
    current_pointer: Mapping[str, Any],
) -> dict[str, Any]:
    """Reconcile the exact WP6B source wave against the current RCCR authority frontier."""
    if admission_manifest.get("schema") != "ovc-rccr-wp6b-source-admission/v1":
        raise RCCRCloseoutError("SOURCE_ADMISSION_SCHEMA_INVALID")
    if bootstrap_wave.get("schema") != "ovc-rccr-bootstrap-wave/v1":
        raise RCCRCloseoutError("BOOTSTRAP_WAVE_SCHEMA_INVALID")
    if admission_manifest.get("admission_mode") != "EXACT_ID_ALLOWLIST_ONLY":
        raise RCCRCloseoutError("SOURCE_ADMISSION_NOT_EXACT_ID")
    if admission_manifest.get("interesting_file_ingestion") != "FORBIDDEN":
        raise RCCRCloseoutError("ARBITRARY_SOURCE_DISCOVERY_NOT_DENIED")
    admitted = _stable(admission_manifest.get("admitted_sources", []))
    excluded = _stable(admission_manifest.get("explicit_exclusions", []))
    if int(bootstrap_wave.get("admitted_source_count", -1)) != len(admitted):
        raise RCCRCloseoutError("ADMITTED_SOURCE_DENOMINATOR_MISMATCH")
    if int(bootstrap_wave.get("excluded_source_count", -1)) != len(excluded):
        raise RCCRCloseoutError("EXCLUDED_SOURCE_DENOMINATOR_MISMATCH")
    source_ids = [str(row.get("source_id", "")) for row in admitted]
    if any(not source_id for source_id in source_ids) or len(source_ids) != len(set(source_ids)):
        raise RCCRCloseoutError("SOURCE_ID_INVALID_OR_DUPLICATE")
    if any(str(row.get("authority_effect", "NONE")) != "NONE" for row in admitted):
        raise RCCRCloseoutError("SOURCE_AUTHORITY_EFFECT_FORBIDDEN")
    if bootstrap_wave.get("arbitrary_repository_scan") is not False:
        raise RCCRCloseoutError("ARBITRARY_REPOSITORY_SCAN_NOT_DENIED")
    owner_frontier = deepcopy(admission_manifest.get("owner_authority_frontier", {}))
    if owner_frontier != bootstrap_wave.get("owner_authority_frontier"):
        raise RCCRCloseoutError("OWNER_FRONTIER_WAVE_MISMATCH")
    if owner_frontier != current_pointer.get("owner_authority_frontier"):
        raise RCCRCloseoutError("OWNER_FRONTIER_CURRENT_POINTER_MISMATCH")
    consumption = deepcopy(admission_manifest.get("rccr_consumption_boundary", {}))
    if consumption != bootstrap_wave.get("rccr_consumption_boundary") or consumption != current_pointer.get("rccr_consumption_boundary"):
        raise RCCRCloseoutError("RCCR_CONSUMPTION_BOUNDARY_MISMATCH")
    if owner_frontier.get("validation", {}).get("state") != "LOCKED_UNCONSUMED":
        raise RCCRCloseoutError("VALIDATION_NOT_LOCKED")
    if consumption.get("owner_capability_activation") != "DENIED" or consumption.get("validation_consumption") != "DENIED":
        raise RCCRCloseoutError("OWNER_OR_VALIDATION_CONSUMPTION_NOT_DENIED")
    payload = {
        "schema": "ovc-rccr-source-reconciliation/v1",
        "admission_mode": "EXACT_ID_ALLOWLIST_ONLY",
        "admitted_source_ids": sorted(source_ids),
        "excluded_source_ids": sorted(str(row.get("source_id", "")) for row in excluded),
        "owner_authority_frontier": owner_frontier,
        "rccr_consumption_boundary": consumption,
        "authority_effect": "NONE",
    }
    payload["reconciliation_id"] = _digest(payload)
    return payload


def build_rebuild_restart_receipt(
    *,
    durable_records: Iterable[Mapping[str, Any]],
    read_models: Iterable[Mapping[str, Any]],
    source_reconciliation: Mapping[str, Any],
) -> dict[str, Any]:
    """Produce a deterministic closeout receipt independent of input enumeration order."""
    records = _stable(durable_records)
    models = _stable(read_models)
    if not records:
        raise RCCRCloseoutError("DURABLE_RECORD_SET_EMPTY")
    if any(str(record.get("authority_effect", "NONE")) != "NONE" for record in records):
        raise RCCRCloseoutError("DURABLE_RECORD_AUTHORITY_EFFECT_FORBIDDEN")
    if any(str(model.get("authority_effect", "NONE")) != "NONE" for model in models):
        raise RCCRCloseoutError("READ_MODEL_AUTHORITY_EFFECT_FORBIDDEN")
    if any(model.get("write_routes") not in (None, "DENIED") for model in models):
        raise RCCRCloseoutError("READ_MODEL_WRITE_ROUTE_FORBIDDEN")
    if source_reconciliation.get("authority_effect") != "NONE" or not source_reconciliation.get("reconciliation_id"):
        raise RCCRCloseoutError("SOURCE_RECONCILIATION_INVALID")
    receipt = {
        "schema": "ovc-rccr-rebuild-restart-receipt/v1",
        "durable_record_count": len(records),
        "durable_record_digest": _digest(records),
        "read_model_count": len(models),
        "read_model_digest": _digest(models),
        "source_reconciliation_id": source_reconciliation["reconciliation_id"],
        "restart_semantics": "CLEAN_REBUILD_FROM_DURABLE_INPUTS",
        "write_routes": "DENIED",
        "authority_effect": "NONE",
    }
    receipt["receipt_id"] = _digest(receipt)
    return receipt


def validate_terminal_authority(pointer: Mapping[str, Any]) -> None:
    if pointer.get("authority_effect") != "NONE":
        raise RCCRCloseoutError("TERMINAL_AUTHORITY_EFFECT_NONZERO")
    frontier = pointer.get("owner_authority_frontier", {})
    boundary = pointer.get("rccr_consumption_boundary", {})
    if frontier.get("validation", {}).get("state") != "LOCKED_UNCONSUMED":
        raise RCCRCloseoutError("TERMINAL_VALIDATION_NOT_LOCKED")
    if boundary.get("owner_capability_activation") != "DENIED":
        raise RCCRCloseoutError("TERMINAL_OWNER_ACTIVATION_NOT_DENIED")
    if boundary.get("validation_consumption") != "DENIED":
        raise RCCRCloseoutError("TERMINAL_VALIDATION_CONSUMPTION_NOT_DENIED")
