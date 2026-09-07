"""Integrated source-free assurance and measured capacity for C2S-SPTOI WP10."""

from __future__ import annotations

import copy
import json
import platform
import time
import tracemalloc
from pathlib import Path
from typing import Any, Iterable, Mapping

from .factorised_diagnostics import SPECIFICATIONS, build_diagnostic_pack
from .factorised_mechanics import (
    DECLARED_REPRESENTATIONS,
    PROTOCOL_SHA256,
    build_derivation_manifest,
    canonical_bytes,
    content_id,
    synthetic_qualification_fixture,
)
from .factorised_nulls import (
    NULL_SPECS,
    REPLICAS_PER_NULL,
    assess_null_adequacy,
    build_null_qualification_pack,
    derive_representation_bundle,
    synthetic_null_events,
    transform_null_world,
)


PACKET_ID = "C2S-SPTOI-WP10"
WALL_BUDGET_MS = 120_000
PEAK_MEMORY_BUDGET_BYTES = 268_435_456


class IntegratedAssuranceError(ValueError):
    def __init__(self, reason_code: str, detail: str):
        super().__init__(f"{reason_code}: {detail}")
        self.reason_code = reason_code
        self.detail = detail


def _freeze(value: Any) -> Any:
    return json.loads(json.dumps(value, sort_keys=True))


def _without_identity(value: Mapping[str, Any], key: str) -> dict[str, Any]:
    body = copy.deepcopy(dict(value))
    body.pop(key, None)
    return body


def build_reference_snapshot() -> dict[str, Any]:
    mechanics = synthetic_qualification_fixture()
    nulls = build_null_qualification_pack()
    diagnostics = build_diagnostic_pack()
    body = {
        "mechanics": mechanics,
        "nulls": nulls,
        "diagnostics": diagnostics,
        "retention": {
            "representations": list(DECLARED_REPRESENTATIONS),
            "null_families": sorted(NULL_SPECS),
            "null_replica_count": len(nulls["replicas"]),
            "diagnostic_controls": list(SPECIFICATIONS),
            "support_map_count": len(mechanics["frontier_records"]),
            "trace_count": len(mechanics["trace_set"]["traces"]),
        },
    }
    body = _freeze(body)
    body["snapshot_id"] = content_id("IntegratedAssuranceSnapshot/v1", body)
    return body


def _load_filed(root: Path, relative: str) -> dict[str, Any]:
    path = root / relative
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise IntegratedAssuranceError("CORRUPT_ARTIFACT", relative) from exc
    if not isinstance(value, dict):
        raise IntegratedAssuranceError("INCOMPLETE_ARTIFACT", relative)
    return value


def verify_content_addressed_artifact(
    value: Mapping[str, Any], *, identity_key: str, contract: str, required: Iterable[str]
) -> None:
    missing = sorted(set(required) - set(value))
    if missing:
        raise IntegratedAssuranceError("INCOMPLETE_ARTIFACT", ",".join(missing))
    identity = value.get(identity_key)
    if not isinstance(identity, str) or identity != content_id(contract, _without_identity(value, identity_key)):
        raise IntegratedAssuranceError("CORRUPT_ARTIFACT", identity_key)


def build_artifact_reuse_snapshot(root: Path) -> dict[str, Any]:
    mechanics = _load_filed(
        root,
        "docs/programmes/c2s-sptoi-v0-1/wp6/C2S_SPTOI_WP6_SYNTHETIC_QUALIFICATION_FIXTURE_v0_1.json",
    )
    nulls = _load_filed(
        root,
        "docs/programmes/c2s-sptoi-v0-1/wp8/C2S_SPTOI_WP8_FACTORISED_NULL_QUALIFICATION_PACK_v0_1.json",
    )
    diagnostics = _load_filed(
        root,
        "docs/programmes/c2s-sptoi-v0-1/wp9/C2S_SPTOI_WP9_FACTORISED_DIAGNOSTIC_QUALIFICATION_PACK_v0_1.json",
    )
    verify_content_addressed_artifact(
        mechanics,
        identity_key="bundle_id",
        contract="FactorisedMechanicsSyntheticFixture/v1",
        required=("frontier_records", "trace_set", "derivation_manifest", "bundle_id"),
    )
    verify_content_addressed_artifact(
        nulls,
        identity_key="pack_id",
        contract="FactorisedNullQualificationPack/v1",
        required=("replicas", "family_assessments", "pack_id"),
    )
    verify_content_addressed_artifact(
        diagnostics,
        identity_key="pack_id",
        contract="FactorisedDiagnosticQualificationPack/v1",
        required=("population_manifest", "specification_opportunity_ledger", "pack_id"),
    )
    body = {
        "mechanics": mechanics,
        "nulls": nulls,
        "diagnostics": diagnostics,
        "retention": {
            "representations": list(DECLARED_REPRESENTATIONS),
            "null_families": sorted(NULL_SPECS),
            "null_replica_count": len(nulls["replicas"]),
            "diagnostic_controls": list(SPECIFICATIONS),
            "support_map_count": len(mechanics["frontier_records"]),
            "trace_count": len(mechanics["trace_set"]["traces"]),
        },
    }
    body = _freeze(body)
    body["snapshot_id"] = content_id("IntegratedAssuranceSnapshot/v1", body)
    return body


def _null_shard(null_ids: Iterable[str]) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    source = synthetic_null_events()
    replicas: list[dict[str, Any]] = []
    assessments = {}
    for null_id in null_ids:
        if null_id not in NULL_SPECS:
            raise IntegratedAssuranceError("UNKNOWN_NULL_SHARD", null_id)
        adequate_count = 0
        for replica_index in range(REPLICAS_PER_NULL):
            world = transform_null_world(null_id, replica_index, source)
            bundle = derive_representation_bundle(world)
            assessment = assess_null_adequacy(null_id, source, world, bundle)
            adequate_count += int(assessment["adequate"])
            replicas.append(
                {
                    "null_id": null_id,
                    "replica_index": replica_index,
                    "seed_hex": world["seed_hex"],
                    "source_world_id": world["source_world_id"],
                    "representation_bundle_id": bundle["representation_bundle_id"],
                    "adequacy_assessment_id": assessment["assessment_id"],
                    "adequate": assessment["adequate"],
                }
            )
        assessments[null_id] = {
            **NULL_SPECS[null_id],
            "replica_count": REPLICAS_PER_NULL,
            "adequate_replica_count": adequate_count,
            "adequate": adequate_count == REPLICAS_PER_NULL,
            "inadequate_disposition": "AFFECTED_CLAIM_NOT_EVALUABLE_NO_SUBSTITUTION",
        }
    return _freeze(replicas), _freeze(assessments)


def build_sharded_null_pack(shards: Iterable[Iterable[str]]) -> dict[str, Any]:
    replicas: list[dict[str, Any]] = []
    family_assessments: dict[str, Any] = {}
    seen: set[str] = set()
    for shard in shards:
        shard_ids = tuple(shard)
        if seen.intersection(shard_ids):
            raise IntegratedAssuranceError("DUPLICATE_NULL_SHARD", ",".join(shard_ids))
        seen.update(shard_ids)
        part_replicas, part_assessments = _null_shard(shard_ids)
        replicas.extend(part_replicas)
        family_assessments.update(part_assessments)
    if seen != set(NULL_SPECS):
        raise IntegratedAssuranceError("INCOMPLETE_NULL_SHARDS", str(sorted(set(NULL_SPECS) - seen)))
    order = {null_id: index for index, null_id in enumerate(NULL_SPECS)}
    replicas.sort(key=lambda row: (order[row["null_id"]], row["replica_index"]))
    family_assessments = {null_id: family_assessments[null_id] for null_id in NULL_SPECS}
    source = synthetic_null_events()
    pack = {
        "schema": "ovc-c2s-sptoi-factorised-null-qualification-pack/v0.1",
        "protocol_sha256": PROTOCOL_SHA256,
        "source_fixture_id": content_id("FactorisedNullSyntheticSource/v1", source),
        "null_specs": NULL_SPECS,
        "family_assessments": family_assessments,
        "replicas": replicas,
        "primary_replica_count": 5 * REPLICAS_PER_NULL,
        "sensitivity_replica_count": REPLICAS_PER_NULL,
        "total_replica_count": len(replicas),
        "all_representations_derived_from_one_world_per_replica": True,
        "independent_representation_draws": False,
        "protected_source_access": "NONE",
        "factorised_evidence_execution": "DENIED",
        "result": "PASS_SOURCE_FREE_NULL_QUALIFICATION",
        "authority_effect": "NONE_NULL_MECHANICS_QUALIFICATION_ONLY",
    }
    pack = _freeze(pack)
    pack["pack_id"] = content_id("FactorisedNullQualificationPack/v1", pack)
    return pack


def measure_capacity(root: Path) -> dict[str, Any]:
    tracemalloc.start()
    start = time.perf_counter_ns()
    reference = build_reference_snapshot()
    artifact = build_artifact_reuse_snapshot(root)
    sharded = build_sharded_null_pack((("FG-NC", "FG-NO"), ("FG-NORD", "FG-NCORE"), ("FG-NFO", "FG-NBROAD")))
    elapsed_ms = max(1, (time.perf_counter_ns() - start + 999_999) // 1_000_000)
    _, peak = tracemalloc.get_traced_memory()
    tracemalloc.stop()
    return {
        "environment": {
            "python_implementation": platform.python_implementation(),
            "python_version": platform.python_version(),
            "platform": platform.platform(),
        },
        "wall_time_ms": elapsed_ms,
        "peak_traced_memory_bytes": peak,
        "wall_budget_ms": WALL_BUDGET_MS,
        "peak_memory_budget_bytes": PEAK_MEMORY_BUDGET_BYTES,
        "reference_snapshot_id": reference["snapshot_id"],
        "artifact_reuse_snapshot_id": artifact["snapshot_id"],
        "sharded_null_pack_id": sharded["pack_id"],
    }


def build_integrated_assurance_receipt(root: Path, measured_capacity: Mapping[str, Any]) -> dict[str, Any]:
    reference = build_reference_snapshot()
    artifact = build_artifact_reuse_snapshot(root)
    sharded = build_sharded_null_pack((("FG-NC", "FG-NO"), ("FG-NORD", "FG-NCORE"), ("FG-NFO", "FG-NBROAD")))
    if reference != artifact:
        raise IntegratedAssuranceError("REFERENCE_OPTIMIZED_DIVERGENCE", "snapshot bytes differ")
    if sharded != reference["nulls"]:
        raise IntegratedAssuranceError("SHARD_DIVERGENCE", "null pack differs")
    retention = reference["retention"]
    expected_retention = {
        "representations": len(DECLARED_REPRESENTATIONS),
        "null_families": len(NULL_SPECS),
        "null_replicas": len(NULL_SPECS) * REPLICAS_PER_NULL,
        "diagnostic_controls": len(SPECIFICATIONS),
        "support_maps": len(DECLARED_REPRESENTATIONS),
        "traces": len(DECLARED_REPRESENTATIONS),
    }
    observed_retention = {
        "representations": len(retention["representations"]),
        "null_families": len(retention["null_families"]),
        "null_replicas": retention["null_replica_count"],
        "diagnostic_controls": len(retention["diagnostic_controls"]),
        "support_maps": retention["support_map_count"],
        "traces": retention["trace_count"],
    }
    if observed_retention != expected_retention:
        raise IntegratedAssuranceError("CAPACITY_FEATURE_REMOVAL", str(observed_retention))
    if measured_capacity["wall_time_ms"] > measured_capacity["wall_budget_ms"]:
        raise IntegratedAssuranceError("CAPACITY_WALL_EXCEEDED", str(measured_capacity["wall_time_ms"]))
    if measured_capacity["peak_traced_memory_bytes"] > measured_capacity["peak_memory_budget_bytes"]:
        raise IntegratedAssuranceError("CAPACITY_MEMORY_EXCEEDED", str(measured_capacity["peak_traced_memory_bytes"]))
    derivation = reference["mechanics"]["derivation_manifest"]
    changed = build_derivation_manifest(
        derivation["output_contract"],
        derivation["output_id"],
        {**dict(derivation["dependencies"]), "protocol": "f" * 64},
    )
    if changed.manifest_id == derivation["manifest_id"]:
        raise IntegratedAssuranceError("DERIVATION_DEPENDENCY_NOT_BOUND", "protocol mutation")
    null_rows = reference["nulls"]["replicas"]
    shared_world_retained = all(
        row["source_world_id"] and row["representation_bundle_id"] for row in null_rows
    ) and len({(row["null_id"], row["replica_index"]) for row in null_rows}) == len(null_rows)
    if not shared_world_retained:
        raise IntegratedAssuranceError("NULL_WORLD_COUPLING_LOST", "replica identity")
    body = {
        "schema": "ovc-c2s-sptoi-integrated-assurance-receipt/v0.1",
        "programme_id": "OVC-EML-C2S-SPTO-CONFORMANCE-PREREG-v0.1",
        "packet_id": PACKET_ID,
        "reference_snapshot_id": reference["snapshot_id"],
        "artifact_reuse_snapshot_id": artifact["snapshot_id"],
        "sharded_null_pack_id": sharded["pack_id"],
        "equivalence": {
            "reference_vs_artifact_reuse": "PASS_BYTE_IDENTICAL",
            "reference_vs_sharded_nulls": "PASS_BYTE_IDENTICAL",
            "restart_and_rebuild": "PASS_REQUIRED_BY_FRESH_PROCESS_TEST",
        },
        "failure_assurance": {
            "corrupt_json": "FAIL_CLOSED_CORRUPT_ARTIFACT",
            "content_identity_mismatch": "FAIL_CLOSED_CORRUPT_ARTIFACT",
            "incomplete_artifact": "FAIL_CLOSED_INCOMPLETE_ARTIFACT",
            "incomplete_shards": "FAIL_CLOSED_INCOMPLETE_NULL_SHARDS",
        },
        "retention": {
            "expected": expected_retention,
            "observed": observed_retention,
            "support_maps_retained": True,
            "trace_set_retained": True,
            "joint_null_worlds_retained": shared_world_retained,
            "capacity_feature_removal": "NONE",
        },
        "derivation_dependency_change": {
            "original_manifest_id": derivation["manifest_id"],
            "mutated_manifest_id": changed.manifest_id,
            "changed": True,
        },
        "measured_capacity": _freeze(measured_capacity),
        "capacity_result": "PASS_MEASURED_WITHOUT_FEATURE_REMOVAL",
        "protected_source_access": "NONE",
        "factorised_evidence_execution": "DENIED",
        "validation": "LOCKED_UNCONSUMED",
        "scientific_claims": "NONE",
        "authority_effect": "NONE_INTEGRATED_SOURCE_FREE_ASSURANCE_ONLY",
    }
    body = _freeze(body)
    body["receipt_id"] = content_id("IntegratedAssuranceReceipt/v1", body)
    return body
