"""Public read-only current-owner C2 vNext structural snapshot surface.

This module exposes existing C2 vNext owner records to governed consumers. It
must not change C2 algorithms, create source authority, or write active owner
state. Population-specific source bindings remain separately authorised.
"""
from __future__ import annotations

import copy
import hashlib
import json
from contextlib import contextmanager
from typing import Any, Iterable, Mapping, Sequence

from . import real_source_materialisation as c2rm

HANDOFF_ID = "C2.VNEXT.OWNER.STRUCTURAL.SNAPSHOT.READ.HANDOFF.v0.1"
SNAPSHOT_SCHEMA = "ovc-c2-vnext-owner-structural-snapshot-read/v0.1"
SOURCE_BINDING_SCHEMA = "ovc-c2-vnext-owner-source-binding/v0.1"
OWNER_AUTHORITY_ID = "AUTH.OPT-B.C2.vNext.ACTIVE.RUNTIME.v0.1"
OWNER_GENERATION_ID = "C2VNEXT.OWNER.GENERATION.ASR00.C2AR-PACKAGE-v1.READ-v0.1"
OWNER_PACKAGE_ID = "C2AR.INTEGRATED.SHADOW.PACKAGE.v1"
OWNER_PACKAGE_SHA256 = "150de1997be8801baa59db6d0fe98b11cb21a6b70525b908537aeb31bfd00cc3"
LOCAL_CLOCK = "15M"
PARENT_CLOCK = "2H_A_L"
INSTRUMENT = "GBPUSD"
SIDES = frozenset({"BID", "ASK"})


class OwnerReadSurfaceError(RuntimeError):
    pass


def _require(condition: bool, marker: str) -> None:
    if not condition:
        raise OwnerReadSurfaceError(marker)


def canonical_bytes(value: Any) -> bytes:
    return json.dumps(
        value,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False,
        allow_nan=False,
    ).encode("utf-8")


def canonical_sha256(value: Any) -> str:
    return hashlib.sha256(canonical_bytes(value)).hexdigest()


def validate_source_binding(binding: Mapping[str, Any]) -> dict[str, Any]:
    value = copy.deepcopy(dict(binding))
    required = {
        "schema", "source_binding_id", "source_authority_ref", "provider",
        "instrument", "side", "local_clock", "parent_clock", "partition_id",
        "context_start_utc", "context_end_exclusive_utc", "target_start_utc",
        "target_end_exclusive_utc", "source_slice_id", "source_manifest_sha256",
        "opt_a_release_id", "opt_a_manifest_id", "opt_a_manifest_sha256",
        "c1_release_id", "c1_manifest_id", "source_object_ids",
    }
    missing = sorted(required.difference(value))
    _require(not missing, f"SOURCE_BINDING_FIELDS_MISSING:{','.join(missing)}")
    _require(value["schema"] == SOURCE_BINDING_SCHEMA, "SOURCE_BINDING_SCHEMA_MISMATCH")
    _require(value["instrument"] == INSTRUMENT, "NEW_INSTRUMENT_AUTHORITY_DENIED")
    _require(value["side"] in SIDES, "NEW_SIDE_AUTHORITY_DENIED")
    _require(value["local_clock"] == LOCAL_CLOCK, "NEW_LOCAL_CLOCK_AUTHORITY_DENIED")
    _require(value["parent_clock"] == PARENT_CLOCK, "NEW_PARENT_CLOCK_AUTHORITY_DENIED")
    _require(bool(str(value["source_authority_ref"]).strip()), "SOURCE_AUTHORITY_REF_REQUIRED")
    _require(bool(str(value["provider"]).strip()), "PROVIDER_PROVENANCE_REQUIRED")
    _require(bool(str(value["source_binding_id"]).strip()), "SOURCE_BINDING_ID_REQUIRED")
    _require(bool(str(value["partition_id"]).strip()), "PARTITION_ID_REQUIRED")
    for key in ("source_manifest_sha256", "opt_a_manifest_sha256"):
        token = str(value[key])
        _require(len(token) == 64 and token == token.lower(), f"{key.upper()}_INVALID")
        try:
            int(token, 16)
        except ValueError as exc:
            raise OwnerReadSurfaceError(f"{key.upper()}_INVALID") from exc
    objects = value["source_object_ids"]
    _require(isinstance(objects, list) and objects, "SOURCE_OBJECT_IDS_REQUIRED")
    _require(len(set(str(item) for item in objects)) == len(objects), "SOURCE_OBJECT_IDS_DUPLICATE")
    _require(str(value["context_start_utc"]) < str(value["context_end_exclusive_utc"]), "CONTEXT_INTERVAL_INVALID")
    _require(str(value["target_start_utc"]) < str(value["target_end_exclusive_utc"]), "TARGET_INTERVAL_INVALID")
    _require(str(value["context_start_utc"]) <= str(value["target_start_utc"]), "TARGET_BEFORE_CONTEXT")
    _require(str(value["target_end_exclusive_utc"]) <= str(value["context_end_exclusive_utc"]), "TARGET_AFTER_CONTEXT")
    return value


def _validate_rows(
    rows: Sequence[Mapping[str, Any]],
    *,
    binding: Mapping[str, Any],
    expected_clock: str,
) -> list[dict[str, Any]]:
    output: list[dict[str, Any]] = []
    for ordinal, raw in enumerate(rows):
        row = copy.deepcopy(dict(raw))
        _require(str(row.get("side")) == str(binding["side"]), f"ROW_SIDE_MISMATCH:{ordinal}")
        _require(str(row.get("clock")) == expected_clock, f"ROW_CLOCK_MISMATCH:{ordinal}")
        _require(str(row.get("c1_release_id")) == str(binding["c1_release_id"]), f"ROW_C1_RELEASE_MISMATCH:{ordinal}")
        _require(str(row.get("opt_a_release_id")) == str(binding["opt_a_release_id"]), f"ROW_OPT_A_RELEASE_MISMATCH:{ordinal}")
        if row.get("source_manifest_sha256") is not None:
            _require(str(row["source_manifest_sha256"]) == str(binding["source_manifest_sha256"]), f"ROW_SOURCE_MANIFEST_MISMATCH:{ordinal}")
        if row.get("source_slice_id") is not None:
            _require(str(row["source_slice_id"]) == str(binding["source_slice_id"]), f"ROW_SOURCE_SLICE_MISMATCH:{ordinal}")
        output.append(row)
    return output


@contextmanager
def _owner_scope(binding: Mapping[str, Any]):
    """Bind the existing owner materialiser to one authorised population, then restore it."""
    overrides = {
        "CONTEXT_START": str(binding["context_start_utc"]),
        "CONTEXT_END": str(binding["context_end_exclusive_utc"]),
        "TARGET_START": str(binding["target_start_utc"]),
        "TARGET_END": str(binding["target_end_exclusive_utc"]),
        "INSTRUMENT": INSTRUMENT,
        "PARTITION_ID": str(binding["partition_id"]),
        "SOURCE_SLICE_ID": str(binding["source_slice_id"]),
        "SOURCE_MANIFEST_SHA256": str(binding["source_manifest_sha256"]),
        "C1_RELEASE_ID": str(binding["c1_release_id"]),
        "C1_MANIFEST_ID": str(binding["c1_manifest_id"]),
        "MATERIALISATION_ID": f"{HANDOFF_ID}:{binding['source_binding_id']}",
    }
    original = {key: getattr(c2rm, key) for key in overrides}
    try:
        for key, value in overrides.items():
            setattr(c2rm, key, value)
        yield
    finally:
        for key, value in original.items():
            setattr(c2rm, key, value)


def build_owner_side_result(
    source_binding: Mapping[str, Any],
    rows_15m: Sequence[Mapping[str, Any]],
    rows_2h: Sequence[Mapping[str, Any]],
) -> dict[str, Any]:
    """Run the existing owner build for one side without changing owner semantics."""
    binding = validate_source_binding(source_binding)
    local_rows = _validate_rows(rows_15m, binding=binding, expected_clock=LOCAL_CLOCK)
    parent_rows = _validate_rows(rows_2h, binding=binding, expected_clock=PARENT_CLOCK)
    with _owner_scope(binding):
        result = c2rm.build_side(str(binding["side"]), local_rows, parent_rows)
    _require(str(result.get("side")) == str(binding["side"]), "OWNER_RESULT_SIDE_MISMATCH")
    return copy.deepcopy(result)


def _unique_index(records: Iterable[Mapping[str, Any]], key: str, label: str) -> dict[str, dict[str, Any]]:
    output: dict[str, dict[str, Any]] = {}
    for raw in records:
        row = copy.deepcopy(dict(raw))
        identity = str(row.get(key, ""))
        _require(bool(identity), f"{label}_IDENTITY_MISSING")
        if identity in output:
            _require(canonical_bytes(output[identity]) == canonical_bytes(row), f"{label}_IDENTITY_CONTENT_COLLISION:{identity}")
        output[identity] = row
    return output


def _relation_index(records: Iterable[Mapping[str, Any]]) -> dict[str, dict[str, Any]]:
    return _unique_index(
        (row for row in records if row.get("relation_id") is not None),
        "relation_id",
        "RELATION",
    )


def _records_at_time(records: Iterable[Mapping[str, Any]], first_valid_time: str) -> list[dict[str, Any]]:
    result = []
    for raw in records:
        row = copy.deepcopy(dict(raw))
        observed = row.get("first_valid_time", row.get("as_of_time"))
        if observed is not None and str(observed) == first_valid_time:
            result.append(row)
    return sorted(result, key=canonical_bytes)


def build_snapshot_stream(
    side_result: Mapping[str, Any],
    source_binding: Mapping[str, Any],
) -> list[dict[str, Any]]:
    """Expose exact owner records through deterministic snapshot envelopes."""
    binding = validate_source_binding(source_binding)
    _require(str(side_result.get("side")) == str(binding["side"]), "SNAPSHOT_SIDE_MISMATCH")

    observations = _unique_index(side_result.get("complete15", []), "observation_id", "OBSERVATION")
    memberships = _unique_index(side_result.get("memberships", []), "membership_id", "HORIZON")
    levels = _unique_index(side_result.get("levels", []), "level_id", "LEVEL")
    containers = _unique_index(side_result.get("containers", []), "container_id", "CONTAINER")
    relations = _relation_index(side_result.get("relations", []))
    relation_sets = _unique_index(side_result.get("relation_sets", []), "relation_set_id", "RELATION_SET")
    profiles = _unique_index(side_result.get("profiles", []), "profile_output_id", "PROFILE")
    contexts = _unique_index(side_result.get("contexts", []), "bundle_id", "PARENT_CONTEXT")
    transitions = list(side_result.get("transitions", []))
    computability = list(side_result.get("computability", []))

    snapshots: list[dict[str, Any]] = []
    for raw_bundle in sorted(
        side_result.get("bundles", []),
        key=lambda row: (str(row.get("first_valid_time", "")), str(row.get("observation_id", ""))),
    ):
        bundle = copy.deepcopy(dict(raw_bundle))
        observation_id = str(bundle.get("observation_id", ""))
        _require(observation_id in observations, f"BUNDLE_OBSERVATION_UNRESOLVED:{observation_id}")
        observation = observations[observation_id]
        fvt = str(bundle.get("first_valid_time", ""))
        _require(fvt == str(observation.get("first_valid_time", "")), f"BUNDLE_FVT_MISMATCH:{observation_id}")
        _require(str(observation.get("interval_end", "")) == fvt, f"OBSERVATION_EFFECTIVE_FVT_CONTRACT_MISMATCH:{observation_id}")

        horizon_ids = [str(item) for item in bundle.get("horizon_membership_ids", [])]
        level_ids = [str(item) for item in bundle.get("level_ids", [])]
        container_ids = [str(item) for item in bundle.get("container_ids", [])]
        relation_set_ids = [str(item) for item in bundle.get("relation_set_ids", [])]
        profile_refs = copy.deepcopy(dict(bundle.get("profile_output_ids", {})))
        context_id = bundle.get("context_bundle_id")

        for identity in horizon_ids:
            _require(identity in memberships, f"HORIZON_REF_UNRESOLVED:{identity}")
        for identity in level_ids:
            _require(identity in levels, f"LEVEL_REF_UNRESOLVED:{identity}")
        for identity in container_ids:
            _require(identity in containers, f"CONTAINER_REF_UNRESOLVED:{identity}")
        relation_ids: list[str] = []
        for identity in relation_set_ids:
            _require(identity in relation_sets, f"RELATION_SET_REF_UNRESOLVED:{identity}")
            for relation_id in relation_sets[identity].get("relation_ids", []):
                token = str(relation_id)
                _require(token in relations, f"RELATION_REF_UNRESOLVED:{token}")
                relation_ids.append(token)
        for axis, ids in profile_refs.items():
            _require(axis in {"LOCATION", "MOTION", "ORGANISATION", "INTERACTION"}, f"PROFILE_AXIS_INVALID:{axis}")
            for identity in ids:
                _require(str(identity) in profiles, f"PROFILE_REF_UNRESOLVED:{identity}")
        if context_id is not None:
            _require(str(context_id) in contexts, f"PARENT_CONTEXT_REF_UNRESOLVED:{context_id}")

        profile_records = {
            axis: [copy.deepcopy(profiles[str(identity)]) for identity in ids]
            for axis, ids in sorted(profile_refs.items())
        }
        transition_records = _records_at_time(transitions, fvt)
        computability_records = _records_at_time(computability, fvt)

        body = {
            "schema": SNAPSHOT_SCHEMA,
            "handoff_id": HANDOFF_ID,
            "owner_authority_id": OWNER_AUTHORITY_ID,
            "owner_generation_id": OWNER_GENERATION_ID,
            "owner_package_id": OWNER_PACKAGE_ID,
            "owner_package_sha256": OWNER_PACKAGE_SHA256,
            "source_binding": copy.deepcopy(binding),
            "instrument": INSTRUMENT,
            "side": str(binding["side"]),
            "clocks": {"local": LOCAL_CLOCK, "parent": PARENT_CLOCK},
            "observation_id": observation_id,
            "interval_start": str(observation["interval_start"]),
            "interval_end": str(observation["interval_end"]),
            "effective_time": str(observation["interval_end"]),
            "first_valid_time": fvt,
            "target_eligible": bundle.get("target_eligible") is True,
            "continuity": copy.deepcopy(observation.get("continuity", {})),
            "projection_eligibility": copy.deepcopy(observation.get("projection_eligibility", {})),
            "component_refs": {
                "horizon_membership_ids": horizon_ids,
                "level_ids": level_ids,
                "container_ids": container_ids,
                "relation_set_ids": relation_set_ids,
                "profile_output_ids": profile_refs,
                "context_bundle_id": None if context_id is None else str(context_id),
                "fixed_parent_observation_id": bundle.get("fixed_parent_observation_id"),
            },
            "owner_records": {
                "observation": copy.deepcopy(observation),
                "horizon_memberships": [copy.deepcopy(memberships[item]) for item in horizon_ids],
                "levels": [copy.deepcopy(levels[item]) for item in level_ids],
                "containers": [copy.deepcopy(containers[item]) for item in container_ids],
                "relations": [copy.deepcopy(relations[item]) for item in sorted(set(relation_ids))],
                "relation_sets": [copy.deepcopy(relation_sets[item]) for item in relation_set_ids],
                "formula_profiles": profile_records,
                "parent_context": None if context_id is None else copy.deepcopy(contexts[str(context_id)]),
                "transitions": transition_records,
                "computability": computability_records,
            },
            "component_availability": {
                "observation": "PRESENT",
                "horizon": "PRESENT" if horizon_ids else "TYPED_ABSTENTION",
                "level": "PRESENT" if level_ids else "TYPED_ABSTENTION",
                "container": "PRESENT" if container_ids else "TYPED_ABSTENTION",
                "relation": "PRESENT" if relation_set_ids else "TYPED_ABSTENTION",
                "formula": "PRESENT" if any(profile_refs.values()) else "TYPED_ABSTENTION",
                "parent_context": "PRESENT" if context_id is not None else "TYPED_ABSTENTION",
                "transition": "PRESENT" if transition_records else "NOT_EMITTED_BY_BOUND_OWNER_MATERIALISATION",
                "computability": "PRESENT" if computability_records else "NOT_EMITTED_BY_BOUND_OWNER_MATERIALISATION",
            },
            "authority": {
                "read_only": True,
                "owner_state_write": "DENIED",
                "new_source_authority": "DENIED",
                "validation": "LOCKED_UNCONSUMED",
                "publication": "NONE",
                "probability_risk_exposure_execution": "NONE",
                "agent_write": "NONE",
            },
        }
        snapshots.append({**body, "snapshot_id": canonical_sha256(body)})
    return snapshots


def build_owner_snapshot_stream(
    source_binding: Mapping[str, Any],
    rows_15m: Sequence[Mapping[str, Any]],
    rows_2h: Sequence[Mapping[str, Any]],
) -> list[dict[str, Any]]:
    """Convenience public handoff: existing owner build followed by read-only envelopes."""
    result = build_owner_side_result(source_binding, rows_15m, rows_2h)
    return build_snapshot_stream(result, source_binding)
