"""Identity-rich revised-C2 -> C2EInputFrame v0.2 adapter."""
from __future__ import annotations

import copy
from datetime import datetime, timezone
from typing import Any, Mapping

from .dependency import normalize_dependency_results
from .firewall import FirewallError, scan_forbidden
from .serialization import digest, sha256_hex
from .source_binding import SourceBindingError, validate_source_binding

UTC = timezone.utc
STRUCTURAL_AXES = ("LOCATION", "MOTION", "ORGANISATION", "INTERACTION")
ALLOWED_TOP_LEVEL = {
    "source_binding", "identity", "chronology", "structural", "context",
    "evidence", "lineage", "parent_records", "diagnostic_namespace",
}


class C2EHandoffError(ValueError):
    pass


def _require(condition: bool, marker: str) -> None:
    if not condition:
        raise C2EHandoffError(marker)


def _parse_time(value: str) -> datetime:
    try:
        result = datetime.fromisoformat(str(value).replace("Z", "+00:00"))
    except ValueError as exc:
        raise C2EHandoffError("INVALID_TIME") from exc
    _require(result.tzinfo is not None, "TIMEZONE_REQUIRED")
    return result.astimezone(UTC)


def _iso(value: str) -> str:
    return _parse_time(value).isoformat().replace("+00:00", "Z")


def _ids(value: Any, marker: str) -> list[str]:
    _require(isinstance(value, list), marker)
    result = [str(item) for item in value]
    _require(len(result) == len(set(result)), f"DUPLICATE:{marker}")
    return sorted(result)


def _parent_index(records: Any, frame_fvt: datetime, cutoff: datetime) -> dict[str, dict[str, Any]]:
    _require(isinstance(records, list), "PARENT_RECORDS_REQUIRED")
    result: dict[str, dict[str, Any]] = {}
    for raw in records:
        row = copy.deepcopy(dict(raw))
        record_id = str(row.get("record_id", ""))
        _require(bool(record_id), "PARENT_RECORD_ID_REQUIRED")
        _require(record_id not in result, "DUPLICATE_PARENT_RECORD")
        parent_fvt = _parse_time(str(row.get("first_valid_time", "")))
        _require(parent_fvt <= frame_fvt, "TIME_PARENT_NOT_FIRST_VALID")
        _require(parent_fvt <= cutoff, "TIME_FUTURE_INPUT_DENIED")
        result[record_id] = {
            "record_id": record_id,
            "kind": str(row.get("kind", "UNSPECIFIED")),
            "first_valid_time": _iso(str(row["first_valid_time"])),
            "content_sha256": row.get("content_sha256"),
        }
    return result


def _validate_reference_ids(reference_ids: list[str], parents: Mapping[str, Any], marker: str) -> None:
    missing = sorted(item for item in reference_ids if item not in parents)
    _require(not missing, f"AVAIL_REFERENCE_MISSING:{marker}:{','.join(missing)}")


def build_input_frame(payload: Mapping[str, Any]) -> dict[str, Any]:
    raw = copy.deepcopy(dict(payload))
    unknown = sorted(set(raw) - ALLOWED_TOP_LEVEL)
    _require(not unknown, f"UNKNOWN_HANDOFF_FIELD:{','.join(unknown)}")
    diagnostic = raw.pop("diagnostic_namespace", None)
    try:
        scan_forbidden(raw)
        binding = validate_source_binding(raw.get("source_binding", {}))
    except (FirewallError, SourceBindingError) as exc:
        raise C2EHandoffError(str(exc)) from exc

    identity = copy.deepcopy(dict(raw.get("identity", {})))
    chronology = copy.deepcopy(dict(raw.get("chronology", {})))
    structural = copy.deepcopy(dict(raw.get("structural", {})))
    context = copy.deepcopy(dict(raw.get("context", {})))
    evidence = copy.deepcopy(dict(raw.get("evidence", {})))
    lineage = copy.deepcopy(dict(raw.get("lineage", {})))

    for key in (
        "instrument_id", "side", "scope_id", "scale_id", "clock_id",
        "lattice_id", "observation_id", "c2_record_id",
        "parameter_pack_id", "contract_id", "schema_id",
    ):
        _require(bool(identity.get(key)), f"IDENTITY_REQUIRED:{key}")
    _require(identity["side"] in {"BID", "ASK"}, "SIDE_INVALID")
    _require(identity["c2_record_id"] == identity["observation_id"], "C2_RECORD_OBSERVATION_ID_MISMATCH")

    for key in ("source_time", "first_valid_time", "evaluation_cutoff", "continuity_segment_id"):
        _require(bool(chronology.get(key)), f"CHRONOLOGY_REQUIRED:{key}")
    source_time = _parse_time(str(chronology["source_time"]))
    frame_fvt = _parse_time(str(chronology["first_valid_time"]))
    cutoff = _parse_time(str(chronology["evaluation_cutoff"]))
    _require(source_time <= frame_fvt, "SOURCE_TIME_AFTER_FVT")
    _require(frame_fvt <= cutoff, "FRAME_NOT_FIRST_VALID_AT_CUTOFF")
    if chronology.get("candidate_onset_time") is not None:
        _require(_parse_time(str(chronology["candidate_onset_time"])) <= frame_fvt, "CANDIDATE_ONSET_AFTER_FVT")

    parents = _parent_index(raw.get("parent_records", []), frame_fvt, cutoff)

    structural_keys = set(structural)
    _require("QUALITY" not in structural_keys, "QUALITY_STRUCTURAL_AXIS_DENIED")
    for axis in STRUCTURAL_AXES:
        key = f"{axis.lower()}_record_ids"
        _require(key in structural, f"STRUCTURAL_AXIS_REQUIRED:{axis}")
        values = _ids(structural[key], key)
        _validate_reference_ids(values, parents, axis)
        structural[key] = values
    for key in ("level_record_ids", "container_record_ids", "transition_record_ids", "run_record_ids"):
        values = _ids(structural.get(key, []), key)
        _validate_reference_ids(values, parents, key)
        structural[key] = values
    relation_set_id = structural.get("relation_set_id")
    if relation_set_id is not None:
        relation_set_id = str(relation_set_id)
        _validate_reference_ids([relation_set_id], parents, "relation_set_id")
        structural["relation_set_id"] = relation_set_id

    context_bundle = context.get("context_resolution_bundle_id")
    if context_bundle is not None:
        context_bundle = str(context_bundle)
        _validate_reference_ids([context_bundle], parents, "context_resolution_bundle_id")
        context["context_resolution_bundle_id"] = context_bundle
    for key in ("fixed_parent_links", "structural_object_links", "parent_axis_links"):
        values = _ids(context.get(key, []), key)
        _validate_reference_ids(values, parents, key)
        context[key] = values

    dependency_results = normalize_dependency_results(evidence.get("dependency_results", []))
    for key in ("availability_status", "technical_status", "authority_state"):
        _require(bool(evidence.get(key)), f"EVIDENCE_REQUIRED:{key}")
    assurance = evidence.get("assurance", [])
    _require(isinstance(assurance, list), "ASSURANCE_LIST_REQUIRED")
    reason_codes = evidence.get("reason_codes", [])
    _require(isinstance(reason_codes, list), "REASON_CODES_LIST_REQUIRED")
    evidence = {
        "dependency_results": dependency_results,
        "availability_status": str(evidence["availability_status"]),
        "technical_status": str(evidence["technical_status"]),
        "assurance": copy.deepcopy(assurance),
        "consumer_eligibility": str(evidence.get("consumer_eligibility", "NOT_EVALUATED")),
        "authority_state": str(evidence["authority_state"]),
        "reason_codes": sorted({str(item) for item in reason_codes}),
    }

    parent_ids = sorted(parents)
    declared_parent_ids = sorted({str(item) for item in lineage.get("parent_record_ids", [])})
    _require(declared_parent_ids == parent_ids, "LINEAGE_PARENT_INVENTORY_MISMATCH")
    _require(bool(lineage.get("artifact_hashes")), "LINEAGE_ARTIFACT_HASH_REQUIRED")
    _require(bool(lineage.get("source_build_commit")), "LINEAGE_SOURCE_COMMIT_REQUIRED")

    frame_identity = {
        "source_release_id": binding["source_release_id"],
        "source_manifest_id": binding["source_manifest_id"],
        "c2_release_id": binding["c2_release_id"],
        "c2_contract_id": binding["c2_contract_id"],
        "c2ar_package_sha256": binding["c2ar_package_sha256"],
        "instrument_id": identity["instrument_id"],
        "side": identity["side"],
        "scope_id": identity["scope_id"],
        "scale_id": identity["scale_id"],
        "clock_id": identity["clock_id"],
        "lattice_id": identity["lattice_id"],
        "observation_id": identity["observation_id"],
        "c2_record_id": identity["c2_record_id"],
        "parameter_pack_id": identity["parameter_pack_id"],
        "contract_id": identity["contract_id"],
        "schema_id": identity["schema_id"],
        "first_valid_time": _iso(str(chronology["first_valid_time"])),
        "continuity_segment_id": chronology["continuity_segment_id"],
        "predecessor_observation_id": chronology.get("predecessor_observation_id"),
        "parent_record_ids": parent_ids,
    }
    frame = {
        "schema": "c2e_input_frame/v0_2",
        "source_binding": binding,
        "identity": identity,
        "chronology": {
            "source_time": _iso(str(chronology["source_time"])),
            "candidate_onset_time": _iso(str(chronology["candidate_onset_time"])) if chronology.get("candidate_onset_time") else None,
            "first_valid_time": _iso(str(chronology["first_valid_time"])),
            "evaluation_cutoff": _iso(str(chronology["evaluation_cutoff"])),
            "continuity_segment_id": str(chronology["continuity_segment_id"]),
            "predecessor_observation_id": chronology.get("predecessor_observation_id"),
        },
        "structural": structural,
        "context": context,
        "evidence": evidence,
        "lineage": {
            "parent_record_ids": parent_ids,
            "artifact_hashes": copy.deepcopy(lineage["artifact_hashes"]),
            "source_build_commit": str(lineage["source_build_commit"]),
        },
        "authority": "INACTIVE_NONCANONICAL_BUILD_TEST_ONLY",
    }
    frame["frame_id"] = digest("C2E.FRAME", frame_identity)
    frame["lineage_hash"] = sha256_hex(frame["lineage"])
    frame["logical_hash"] = sha256_hex(frame)
    if diagnostic is not None:
        frame["diagnostic_namespace"] = copy.deepcopy(diagnostic)
    return frame
