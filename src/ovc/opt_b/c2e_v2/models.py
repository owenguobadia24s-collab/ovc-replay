"""Schema-facing C2E v0.2 semantic record helpers.

These helpers freeze field ownership and identity exclusions before the lifecycle
engine exists.  They create no active C2E state and perform no source replay.
"""
from __future__ import annotations

import copy
from typing import Any, Mapping, Sequence

from .serialization import digest, logical_record_hash


class C2EModelError(ValueError):
    pass


RECORD_SPECS: dict[str, dict[str, Any]] = {
    "episode_genesis": {
        "schema": "c2e_episode_genesis/v0_2",
        "id_field": "episode_id",
        "prefix": "C2E.EPISODE",
        "required": ["boundary_pack_id", "source_release_id", "instrument_id", "side", "scope_id", "scale_id", "birth_frame_id", "birth_boundary_rule_id", "birth_effective_time", "first_valid_time", "authority"],
        "identity": ["boundary_pack_id", "source_release_id", "instrument_id", "side", "scope_id", "scale_id", "birth_frame_id", "birth_boundary_rule_id", "birth_effective_time", "first_valid_time"],
        "forbidden_identity": ["member_ids", "end_time", "status", "terminal_boundary_id", "snapshot_ids", "family_id", "semantic_label", "outcome"],
    },
    "episode_snapshot": {
        "schema": "c2e_episode_snapshot/v0_2", "id_field": "snapshot_id", "prefix": "C2E.SNAPSHOT",
        "required": ["episode_id", "as_of_time", "first_valid_time", "status", "member_ids", "phase_segment_ids", "boundary_event_ids", "authority"],
        "identity": ["episode_id", "as_of_time", "first_valid_time", "status", "member_ids", "phase_segment_ids", "boundary_event_ids"],
    },
    "phase_segment": {
        "schema": "c2e_phase_segment/v0_2", "id_field": "phase_segment_id", "prefix": "C2E.PHASE",
        "required": ["episode_id", "phase_type", "start_time", "end_time", "first_valid_time", "source_record_ids", "authority"],
        "identity": ["episode_id", "phase_type", "start_time", "end_time", "first_valid_time", "source_record_ids"],
    },
    "boundary_event": {
        "schema": "c2e_boundary_event/v0_2", "id_field": "boundary_event_id", "prefix": "C2E.BOUNDARY",
        "required": ["episode_ids", "candidate_ids", "lifecycle_action", "priority_class", "compatibility_disposition", "effective_time", "confirmation_time", "first_valid_time", "collision_disposition", "reason_codes", "authority"],
        "identity": ["episode_ids", "candidate_ids", "lifecycle_action", "priority_class", "compatibility_disposition", "effective_time", "confirmation_time", "first_valid_time", "collision_disposition", "reason_codes"],
    },
    "lineage_edge": {
        "schema": "c2e_lineage_edge/v0_2", "id_field": "lineage_edge_id", "prefix": "C2E.EDGE",
        "required": ["edge_type", "parent_episode_id", "child_episode_id", "boundary_event_id", "effective_time", "first_valid_time", "authority"],
        "identity": ["edge_type", "parent_episode_id", "child_episode_id", "boundary_event_id", "effective_time", "first_valid_time"],
    },
    "membership_delta": {
        "schema": "c2e_membership_delta/v0_2", "id_field": "membership_delta_id", "prefix": "C2E.MEMBER",
        "required": ["episode_id", "frame_id", "operation", "boundary_event_id", "effective_time", "first_valid_time", "authority"],
        "identity": ["episode_id", "frame_id", "operation", "boundary_event_id", "effective_time", "first_valid_time"],
    },
    "remap_record": {
        "schema": "c2e_remap_record/v0_2", "id_field": "remap_record_id", "prefix": "C2E.REMAP",
        "required": ["from_boundary_pack_id", "to_boundary_pack_id", "from_episode_ids", "to_episode_ids", "mapping_type", "comparison_only", "first_valid_time", "authority"],
        "identity": ["from_boundary_pack_id", "to_boundary_pack_id", "from_episode_ids", "to_episode_ids", "mapping_type", "comparison_only", "first_valid_time"],
    },
    "stream_manifest": {
        "schema": "c2e_stream_manifest/v0_2", "id_field": "stream_manifest_id", "prefix": "C2E.STREAM",
        "required": ["source_binding", "boundary_pack_id", "schema_ids", "code_hashes", "ordered_record_ids", "ordered_record_hashes", "counts", "missingness", "authority"],
        "identity": ["source_binding", "boundary_pack_id", "schema_ids", "code_hashes", "ordered_record_ids", "ordered_record_hashes", "counts", "missingness", "authority"],
    },
    "checkpoint": {
        "schema": "c2e_checkpoint/v0_2", "id_field": "checkpoint_id", "prefix": "C2E.CHECKPOINT",
        "required": ["stream_manifest_id", "completed_partitions", "logical_cursor", "semantic_prefix_hash", "replaceable", "authority"],
        "identity": ["stream_manifest_id", "completed_partitions", "logical_cursor", "semantic_prefix_hash"],
    },
    "sri_handoff": {
        "schema": "c2e_sri_handoff/v0_1", "id_field": "handoff_id", "prefix": "C2E.SRI.HANDOFF",
        "required": ["episode_id", "boundary_pack_id", "source_release_id", "scope_id", "scale_id", "side", "status", "genesis_ref", "snapshot_ref", "phase_refs", "boundary_refs", "lineage_refs", "membership_refs", "availability", "first_valid_time", "authority"],
        "identity": ["episode_id", "boundary_pack_id", "source_release_id", "scope_id", "scale_id", "side", "status", "genesis_ref", "snapshot_ref", "phase_refs", "boundary_refs", "lineage_refs", "membership_refs", "availability", "first_valid_time"],
    },
}

_SORTED_LIST_FIELDS = {"member_ids", "phase_segment_ids", "boundary_event_ids", "episode_ids", "candidate_ids", "reason_codes", "source_record_ids", "from_episode_ids", "to_episode_ids", "schema_ids", "code_hashes", "completed_partitions", "phase_refs", "boundary_refs", "lineage_refs", "membership_refs"}


def _require(condition: bool, marker: str) -> None:
    if not condition:
        raise C2EModelError(marker)


def _canonical_field_value(key: str, value: Any) -> Any:
    if key in _SORTED_LIST_FIELDS:
        _require(isinstance(value, list), f"LIST_REQUIRED:{key}")
        return sorted(copy.deepcopy(value), key=str)
    return copy.deepcopy(value)


def build_record(kind: str, payload: Mapping[str, Any]) -> dict[str, Any]:
    _require(kind in RECORD_SPECS, f"UNKNOWN_RECORD_KIND:{kind}")
    spec = RECORD_SPECS[kind]
    record = {key: _canonical_field_value(key, value) for key, value in dict(payload).items()}
    for field in spec["required"]:
        _require(field in record and record[field] not in (None, ""), f"REQUIRED_FIELD:{kind}:{field}")
    if kind == "episode_genesis":
        for field in spec.get("forbidden_identity", []):
            _require(field not in record, f"GENESIS_FUTURE_FIELD_DENIED:{field}")
    if kind == "remap_record":
        _require(record["comparison_only"] is True, "REMAP_COMPARISON_ONLY_REQUIRED")
        _require(record["authority"] == "COMPARISON_ONLY", "REMAP_AUTHORITY_INVALID")
    if kind == "checkpoint":
        _require(record["replaceable"] is True, "CHECKPOINT_MUST_BE_REPLACEABLE")
        _require(record["authority"] == "OPERATIONAL_NON_SEMANTIC", "CHECKPOINT_SEMANTIC_AUTHORITY_DENIED")
    if kind == "sri_handoff":
        forbidden = {"representation", "normalization", "distance", "family", "medoid", "cluster", "sensitivity", "semantic_label", "outcome"}
        _require(not forbidden.intersection(record), "SRI_PRODUCER_OWNERSHIP_BREACH")
        _require(record["authority"] == "READ_ONLY_PRODUCER_HANDOFF", "SRI_HANDOFF_AUTHORITY_INVALID")
    identity_payload = {field: record[field] for field in spec["identity"]}
    record["schema"] = spec["schema"]
    record[spec["id_field"]] = digest(spec["prefix"], identity_payload, length=32)
    record["logical_hash"] = logical_record_hash(record)
    return record


def validate_record(kind: str, record: Mapping[str, Any]) -> dict[str, Any]:
    spec = RECORD_SPECS.get(kind)
    _require(spec is not None, f"UNKNOWN_RECORD_KIND:{kind}")
    candidate = dict(record)
    expected = build_record(kind, {key: value for key, value in candidate.items() if key not in {"schema", spec["id_field"], "logical_hash"}})
    _require(candidate.get("schema") == expected["schema"], "SCHEMA_ID_MISMATCH")
    _require(candidate.get(spec["id_field"]) == expected[spec["id_field"]], "RECORD_ID_MISMATCH")
    _require(candidate.get("logical_hash") == expected["logical_hash"], "LOGICAL_HASH_MISMATCH")
    return expected


def identity_fields(kind: str) -> Sequence[str]:
    _require(kind in RECORD_SPECS, f"UNKNOWN_RECORD_KIND:{kind}")
    return tuple(RECORD_SPECS[kind]["identity"])
