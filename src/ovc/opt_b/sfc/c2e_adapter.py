from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Mapping, Sequence

from .serialization import logical_hash

REQUIRED_PRODUCER_FIELDS = (
    "episode_id", "boundary_pack_id", "source_release_id", "instrument_id", "side",
    "scope_id", "scale_id", "lifecycle_status", "genesis_reference",
    "snapshot_reference", "phase_segment_references", "boundary_event_references",
    "lineage_edge_references", "membership_references", "availability_missingness",
    "first_valid_time", "source_lineage",
)
FORBIDDEN_KEYS = frozenset({
    "family_id", "family_ids", "prototype_id", "distance_result", "similarity_result",
    "future_return", "mfe", "mae", "outcome", "outcomes", "validation_label",
    "probability", "risk", "exposure", "trade", "execution",
})
STRUCTURAL_AXES = ("LOCATION", "MOTION", "ORGANISATION", "INTERACTION")


class SFCSourceError(ValueError):
    pass


def _parse_time(value: str) -> datetime:
    try:
        parsed = datetime.fromisoformat(str(value).replace("Z", "+00:00"))
    except ValueError as exc:
        raise SFCSourceError("SFC_SOURCE_SCHEMA_INVALID:INVALID_TIME") from exc
    if parsed.tzinfo is None:
        raise SFCSourceError("SFC_SOURCE_SCHEMA_INVALID:TIMEZONE_REQUIRED")
    return parsed.astimezone(timezone.utc)


def _scan(value: Any, path: str = "$") -> None:
    if isinstance(value, Mapping):
        for key, child in value.items():
            if str(key).lower() in FORBIDDEN_KEYS:
                raise SFCSourceError(f"SFC_FORBIDDEN_FIELD:{path}.{key}")
            _scan(child, f"{path}.{key}")
    elif isinstance(value, Sequence) and not isinstance(value, (str, bytes, bytearray)):
        for index, child in enumerate(value):
            _scan(child, f"{path}[{index}]")


def adapt_c2e_handoff(record: Mapping[str, Any], *, source_objects: Mapping[str, Mapping[str, Any]], evaluation_cutoff: str) -> dict[str, Any]:
    """Validate the exact read-only C2E handoff and lawful joined C2 structural objects.

    Historical MG ledgers do not contain the required producer binding and therefore fail
    with SFC_SOURCE_SCHEMA_INVALID rather than being treated as a fallback.
    """
    raw = dict(record)
    _scan(raw)
    missing = [field for field in REQUIRED_PRODUCER_FIELDS if field not in raw or raw[field] in (None, "")]
    if missing:
        raise SFCSourceError("SFC_SOURCE_SCHEMA_INVALID:MISSING:" + ",".join(sorted(missing)))
    if raw.get("producer_contract_id") != "C2E_TO_SRI_STREAM_HANDOFF_CONTRACT_v0_1":
        raise SFCSourceError("SFC_SOURCE_SCHEMA_INVALID:PRODUCER_CONTRACT_BINDING")
    if raw.get("producer_contract_blob") != "31ba923f68bfd18dd2e3091b0fe7cb21de5b772d":
        raise SFCSourceError("SFC_SOURCE_SCHEMA_INVALID:PRODUCER_CONTRACT_HASH")
    if raw.get("side") not in {"BID", "ASK"}:
        raise SFCSourceError("SFC_SOURCE_SCHEMA_INVALID:SIDE")

    fvt = _parse_time(str(raw["first_valid_time"]))
    cutoff = _parse_time(evaluation_cutoff)
    if fvt > cutoff:
        raise SFCSourceError("SFC_SOURCE_SCHEMA_INVALID:FUTURE_C2E_RECORD")

    joined: dict[str, dict[str, Any]] = {}
    referenced: set[str] = set()
    for field in ("membership_references", "phase_segment_references", "boundary_event_references", "lineage_edge_references"):
        values = raw.get(field)
        if not isinstance(values, list):
            raise SFCSourceError(f"SFC_SOURCE_SCHEMA_INVALID:{field.upper()}_LIST_REQUIRED")
        referenced.update(str(item) for item in values)
    for ref in sorted(referenced):
        if ref not in source_objects:
            raise SFCSourceError("SFC_SOURCE_SCHEMA_INVALID:LINEAGE_REFERENCE_MISSING:" + ref)
        obj = dict(source_objects[ref])
        _scan(obj)
        obj_fvt = _parse_time(str(obj.get("first_valid_time", "")))
        if obj_fvt > cutoff:
            raise SFCSourceError("SFC_SOURCE_SCHEMA_INVALID:FUTURE_JOIN:" + ref)
        joined[ref] = obj

    lineage = raw.get("source_lineage")
    if not isinstance(lineage, Mapping) or not lineage.get("source_build_commit") or not lineage.get("artifact_hashes"):
        raise SFCSourceError("SFC_SOURCE_SCHEMA_INVALID:SOURCE_LINEAGE_REQUIRED")

    payload = {
        "producer_contract_id": raw["producer_contract_id"],
        "producer_contract_blob": raw["producer_contract_blob"],
        "episode_id": str(raw["episode_id"]),
        "boundary_pack_id": str(raw["boundary_pack_id"]),
        "source_release_id": str(raw["source_release_id"]),
        "instrument_id": str(raw["instrument_id"]),
        "side": str(raw["side"]),
        "scope_id": str(raw["scope_id"]),
        "scale_id": str(raw["scale_id"]),
        "lifecycle_status": str(raw["lifecycle_status"]),
        "genesis_reference": str(raw["genesis_reference"]),
        "snapshot_reference": str(raw["snapshot_reference"]),
        "phase_segment_references": sorted(str(x) for x in raw["phase_segment_references"]),
        "boundary_event_references": sorted(str(x) for x in raw["boundary_event_references"]),
        "lineage_edge_references": sorted(str(x) for x in raw["lineage_edge_references"]),
        "membership_references": sorted(str(x) for x in raw["membership_references"]),
        "availability_missingness": raw["availability_missingness"],
        "first_valid_time": str(raw["first_valid_time"]),
        "record_hashes": dict(raw.get("record_hashes", {})),
        "source_lineage": dict(lineage),
        "source_objects": joined,
        "evaluation_cutoff": evaluation_cutoff,
        "authority_state": "READ_ONLY_SFC_CONSUMER",
    }
    payload["source_record_hash"] = logical_hash(payload)
    return payload


def extract_structural_axes(adapted: Mapping[str, Any]) -> dict[str, list[Any]]:
    axes: dict[str, list[Any]] = {axis: [] for axis in STRUCTURAL_AXES}
    for ref, obj in sorted(dict(adapted["source_objects"]).items()):
        structural = obj.get("structural")
        if not isinstance(structural, Mapping):
            continue
        if "QUALITY" in structural:
            raise SFCSourceError("SFC_FORBIDDEN_FIELD:QUALITY_STRUCTURAL_AXIS")
        for axis in STRUCTURAL_AXES:
            if axis in structural and structural[axis] is not None:
                axes[axis].append(structural[axis])
    return axes
