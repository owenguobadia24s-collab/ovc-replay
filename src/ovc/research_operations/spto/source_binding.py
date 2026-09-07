"""Fail-closed C2S-SPTO binding to the public current-owner C2 read surface.

This module consumes only the versioned public handoff.  Embedded owner records
are retained byte-for-byte under canonical JSON serialization and are never
flattened into an SPTO state ontology.
"""
from __future__ import annotations

import copy
import json
import subprocess
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Mapping, Sequence

from ovc.opt_b.c2_vnext.owner_read_surface import (
    HANDOFF_ID,
    INSTRUMENT,
    LOCAL_CLOCK,
    OWNER_AUTHORITY_ID,
    OWNER_GENERATION_ID,
    OWNER_PACKAGE_ID,
    OWNER_PACKAGE_SHA256,
    PARENT_CLOCK,
    SIDES,
    SNAPSHOT_SCHEMA,
    canonical_sha256,
    validate_source_binding,
)

PROGRAMME_ID = "OVC-EML-C2S-SPTO-CONFORMANCE-PREREG-v0.1"
PROTOCOL_ID = "OVC-EML-GRAMMAR-0002-RP-0.1-R1"
READ_AUTHORITY_ID = "AUTH.OPT-B.C2.vNext.OWNER_STRUCTURAL_SNAPSHOT.READ.v0.1"
OWNER_STREAM_SCHEMA = "ovc-c2s-sptoi-c2-owner-stream-binding/v0.1"
FACTORISED_SOURCE_SCHEMA = "ovc-c2s-sptoi-factorised-source-binding-manifest/v0.1"

READ_POINTER = "registries/opt_b/c2/vnext/CURRENT_OWNER_STRUCTURAL_SNAPSHOT_READ_SURFACE.json"
READ_AUTHORITY = "registries/opt_b/c2/vnext/C2_OWNER_STRUCTURAL_SNAPSHOT_READ_AUTHORITY_v0_1.json"
GENERATION = "registries/opt_b/c2/vnext/C2_OWNER_STRUCTURAL_SNAPSHOT_GENERATION_v0_1.json"
FIELD_CATALOG = "registries/opt_b/c2/vnext/C2_OWNER_STRUCTURAL_SNAPSHOT_FIELD_CATALOG_v0_1.json"

CONTINUITY_STATES = frozenset(
    {
        "SEGMENT_START",
        "CONTIGUOUS",
        "GAP_RESET",
        "CLOSURE_BOUNDARY",
        "PARTITION_BOUNDARY",
        "UNKNOWN_BREAK",
    }
)
BREAK_STATES = CONTINUITY_STATES - {"CONTIGUOUS"}
FORBIDDEN_GENERATING_DEPENDENCIES = (
    "ovc.opt_b.c2e",
    "ovc.opt_b.c2p",
    "ovc.opt_c",
    "ovc.opt_d",
    "validation",
    "sff",
)
FORBIDDEN_FLATTENED_FIELDS = frozenset(
    {
        "future_outcome",
        "next_state",
        "episode_id",
        "c2p_object_id",
        "c2_5_event_id",
        "c3_semantic_id",
        "probability",
        "risk",
        "exposure",
        "trade_action",
        "execution_action",
        "nearest_object",
        "best_object",
        "dominant_object",
    }
)


class SPTOBindingError(ValueError):
    """Typed, fail-closed source-binding failure."""

    def __init__(self, reason_code: str, detail: str = "") -> None:
        self.reason_code = reason_code
        self.detail = detail
        super().__init__(f"{reason_code}:{detail}" if detail else reason_code)


def _load_object(root: Path, relative: str) -> dict[str, Any]:
    try:
        value = json.loads((root / relative).read_text(encoding="utf-8"))
    except (OSError, UnicodeError, json.JSONDecodeError) as exc:
        raise SPTOBindingError("OWNER_READ_ARTIFACT_UNRESOLVED", relative) from exc
    if not isinstance(value, dict):
        raise SPTOBindingError("OWNER_READ_ARTIFACT_NOT_OBJECT", relative)
    return value


def _git_blob(root: Path, relative: str) -> str:
    proc = subprocess.run(
        ["git", "-C", str(root), "hash-object", "--", relative],
        capture_output=True,
        text=True,
        check=False,
    )
    token = proc.stdout.strip()
    if proc.returncode or len(token) != 40:
        raise SPTOBindingError("OWNER_READ_BLOB_UNRESOLVED", relative)
    return token


def resolve_owner_read_surface(root: Path) -> dict[str, Any]:
    """Resolve and verify the current public owner handoff and exact blobs."""
    pointer = _load_object(root, READ_POINTER)
    authority = _load_object(root, READ_AUTHORITY)
    generation = _load_object(root, GENERATION)
    catalog = _load_object(root, FIELD_CATALOG)

    exact = {
        "pointer.owner_authority_id": (pointer.get("owner_authority_id"), OWNER_AUTHORITY_ID),
        "pointer.read_authority_id": (pointer.get("read_authority_id"), READ_AUTHORITY_ID),
        "pointer.generation_id": (pointer.get("generation_id"), OWNER_GENERATION_ID),
        "authority.authority_id": (authority.get("authority_id"), READ_AUTHORITY_ID),
        "authority.owner_authority_id": (authority.get("owner_authority_id"), OWNER_AUTHORITY_ID),
        "authority.owner_generation_id": (authority.get("owner_generation_id"), OWNER_GENERATION_ID),
        "generation.generation_id": (generation.get("generation_id"), OWNER_GENERATION_ID),
        "generation.owner.package_id": (generation.get("owner", {}).get("package_id"), OWNER_PACKAGE_ID),
        "generation.owner.package_sha256": (
            generation.get("owner", {}).get("package_sha256"),
            OWNER_PACKAGE_SHA256,
        ),
        "catalog.owner_generation_id": (catalog.get("owner_generation_id"), OWNER_GENERATION_ID),
    }
    for field, (observed, expected) in exact.items():
        if observed != expected:
            raise SPTOBindingError("OWNER_READ_BINDING_DRIFT", field)
    if pointer.get("status") != "ACTIVE_ON_LAWFUL_MAIN_MATERIALISATION":
        raise SPTOBindingError("OWNER_READ_SURFACE_NOT_ACTIVE", str(pointer.get("status")))
    if authority.get("operator_decision") != "PASS":
        raise SPTOBindingError("OWNER_READ_AUTHORITY_NOT_PASSED")
    if pointer.get("validation") != "LOCKED_UNCONSUMED" or authority.get("source_scope", {}).get("validation") != "LOCKED_UNCONSUMED":
        raise SPTOBindingError("VALIDATION_BOUNDARY_DRIFT")

    public = generation.get("public_read_surface", {})
    bound_paths = {
        public.get("contract_path"): public.get("contract_git_blob_sha"),
        public.get("schema_path"): public.get("schema_git_blob_sha"),
        public.get("reader_code_path"): public.get("reader_code_git_blob_sha"),
    }
    if None in bound_paths or len(bound_paths) != 3:
        raise SPTOBindingError("OWNER_PUBLIC_SURFACE_BINDING_INCOMPLETE")
    for path, expected_blob in bound_paths.items():
        if _git_blob(root, str(path)) != expected_blob:
            raise SPTOBindingError("OWNER_PUBLIC_SURFACE_BLOB_DRIFT", str(path))

    component_bindings = generation.get("active_component_bindings", [])
    if len(component_bindings) != 9:
        raise SPTOBindingError("OWNER_COMPONENT_SET_INCOMPLETE", str(len(component_bindings)))
    for row in component_bindings:
        for path_key, blob_key in (
            ("implementation_path", "implementation_git_blob_sha"),
            ("schema_path", "schema_git_blob_sha"),
        ):
            if _git_blob(root, str(row.get(path_key))) != row.get(blob_key):
                raise SPTOBindingError("OWNER_COMPONENT_BLOB_DRIFT", str(row.get(path_key)))

    prohibited = set(catalog.get("prohibited_flattened_fields", []))
    if prohibited != FORBIDDEN_FLATTENED_FIELDS:
        raise SPTOBindingError("OWNER_FIELD_CATALOG_PROHIBITION_DRIFT")

    body = {
        "schema": "ovc-c2s-sptoi-owner-read-surface-resolution/v0.1",
        "programme_id": PROGRAMME_ID,
        "owner_authority_id": OWNER_AUTHORITY_ID,
        "read_authority_id": READ_AUTHORITY_ID,
        "owner_generation_id": OWNER_GENERATION_ID,
        "owner_package_id": OWNER_PACKAGE_ID,
        "owner_package_sha256": OWNER_PACKAGE_SHA256,
        "handoff_id": HANDOFF_ID,
        "snapshot_schema": SNAPSHOT_SCHEMA,
        "market_envelope": copy.deepcopy(generation["market_envelope"]),
        "chronology": copy.deepcopy(generation["chronology"]),
        "missingness_and_breaks": copy.deepcopy(generation["missingness_and_breaks"]),
        "artifact_git_blobs": {
            path: _git_blob(root, path)
            for path in (READ_POINTER, READ_AUTHORITY, GENERATION, FIELD_CATALOG)
        },
        "public_surface_git_blobs": {str(path): str(blob) for path, blob in bound_paths.items()},
        "component_bindings": copy.deepcopy(component_bindings),
        "authority_effect": "READ_ONLY_CURRENT_OWNER_BINDING_ONLY",
        "protected_source_access": "NONE",
        "validation": "LOCKED_UNCONSUMED",
    }
    return {**body, "resolution_id": canonical_sha256(body)}


def adapt_owner_snapshot(snapshot: Mapping[str, Any]) -> dict[str, Any]:
    """Validate one public owner snapshot and preserve its exact structure."""
    value = copy.deepcopy(dict(snapshot))
    required = {
        "schema",
        "snapshot_id",
        "handoff_id",
        "owner_authority_id",
        "owner_generation_id",
        "owner_package_id",
        "owner_package_sha256",
        "source_binding",
        "instrument",
        "side",
        "clocks",
        "observation_id",
        "interval_start",
        "interval_end",
        "effective_time",
        "first_valid_time",
        "target_eligible",
        "continuity",
        "projection_eligibility",
        "component_refs",
        "owner_records",
        "component_availability",
        "authority",
    }
    missing = sorted(required - set(value))
    if missing:
        raise SPTOBindingError("OWNER_SNAPSHOT_FIELDS_MISSING", ",".join(missing))
    expected = {
        "schema": SNAPSHOT_SCHEMA,
        "handoff_id": HANDOFF_ID,
        "owner_authority_id": OWNER_AUTHORITY_ID,
        "owner_generation_id": OWNER_GENERATION_ID,
        "owner_package_id": OWNER_PACKAGE_ID,
        "owner_package_sha256": OWNER_PACKAGE_SHA256,
        "instrument": INSTRUMENT,
        "clocks": {"local": LOCAL_CLOCK, "parent": PARENT_CLOCK},
    }
    for field, expected_value in expected.items():
        if value.get(field) != expected_value:
            raise SPTOBindingError("OWNER_SNAPSHOT_BINDING_MISMATCH", field)
    if value.get("side") not in SIDES:
        raise SPTOBindingError("OWNER_SNAPSHOT_SIDE_DENIED", str(value.get("side")))
    binding = validate_source_binding(value["source_binding"])
    if any(
        (
            binding["instrument"] != value["instrument"],
            binding["side"] != value["side"],
            binding["local_clock"] != value["clocks"]["local"],
            binding["parent_clock"] != value["clocks"]["parent"],
        )
    ):
        raise SPTOBindingError("OWNER_SOURCE_SCOPE_MISMATCH", str(value["snapshot_id"]))
    if value["effective_time"] != value["interval_end"]:
        raise SPTOBindingError("OWNER_EFFECTIVE_TIME_MISMATCH", str(value["observation_id"]))
    if value["first_valid_time"] != value["interval_end"]:
        raise SPTOBindingError("OWNER_FIRST_VALID_TIME_MISMATCH", str(value["observation_id"]))
    continuity = value["continuity"]
    if not isinstance(continuity, Mapping) or continuity.get("status") not in CONTINUITY_STATES:
        raise SPTOBindingError("OWNER_CONTINUITY_STATE_UNRESOLVED", str(value["observation_id"]))
    authority = value["authority"]
    if not isinstance(authority, Mapping) or authority != {
        "read_only": True,
        "owner_state_write": "DENIED",
        "new_source_authority": "DENIED",
        "validation": "LOCKED_UNCONSUMED",
        "publication": "NONE",
        "probability_risk_exposure_execution": "NONE",
        "agent_write": "NONE",
    }:
        raise SPTOBindingError("OWNER_SNAPSHOT_AUTHORITY_MISMATCH", str(value["snapshot_id"]))
    unexpected = FORBIDDEN_FLATTENED_FIELDS.intersection(value)
    if unexpected:
        raise SPTOBindingError("FORBIDDEN_FLATTENED_FIELD_REACHABLE", ",".join(sorted(unexpected)))
    declared_id = str(value.pop("snapshot_id"))
    if canonical_sha256(value) != declared_id:
        raise SPTOBindingError("OWNER_SNAPSHOT_CONTENT_ID_MISMATCH", declared_id)
    value["snapshot_id"] = declared_id
    return value


@dataclass(frozen=True)
class C2OwnerStreamBinding:
    value: Mapping[str, Any]

    @property
    def binding_id(self) -> str:
        return str(self.value["c2_owner_stream_binding_id"])

    def to_dict(self) -> dict[str, Any]:
        return copy.deepcopy(dict(self.value))


@dataclass(frozen=True)
class FactorisedSourceBindingManifest:
    value: Mapping[str, Any]

    @property
    def manifest_id(self) -> str:
        return str(self.value["factorised_source_binding_manifest_id"])

    def to_dict(self) -> dict[str, Any]:
        return copy.deepcopy(dict(self.value))


def build_c2_owner_stream_binding(
    *,
    owner_resolution: Mapping[str, Any],
    snapshots: Sequence[Mapping[str, Any]],
    population_mode: str = "SYNTHETIC_QUALIFICATION_FIXTURE",
) -> C2OwnerStreamBinding:
    """Bind an ordered current-owner stream without generating SPTO semantics."""
    if owner_resolution.get("owner_generation_id") != OWNER_GENERATION_ID:
        raise SPTOBindingError("OWNER_RESOLUTION_GENERATION_MISMATCH")
    if population_mode not in {"SYNTHETIC_QUALIFICATION_FIXTURE", "CONSUMED_DATA_CONFORMANCE"}:
        raise SPTOBindingError("REAL_SOURCE_AUTHORITY_REQUIRED", population_mode)
    if not snapshots:
        raise SPTOBindingError("OWNER_SNAPSHOT_STREAM_EMPTY")
    adapted = [adapt_owner_snapshot(item) for item in snapshots]
    ordered = sorted(adapted, key=lambda row: (str(row["first_valid_time"]), str(row["snapshot_id"])))
    if adapted != ordered:
        raise SPTOBindingError("OWNER_SNAPSHOT_STREAM_NOT_CANONICALLY_ORDERED")
    ids = [str(row["snapshot_id"]) for row in adapted]
    if len(ids) != len(set(ids)):
        raise SPTOBindingError("OWNER_SNAPSHOT_STREAM_DUPLICATE_ID")
    source_bindings = {canonical_sha256(row["source_binding"]): row["source_binding"] for row in adapted}
    if len(source_bindings) != 1:
        raise SPTOBindingError("OWNER_SNAPSHOT_STREAM_SOURCE_BINDING_DRIFT")

    continuity_counts = {state: 0 for state in sorted(CONTINUITY_STATES)}
    missing_counts: dict[str, int] = {}
    for row in adapted:
        continuity_counts[str(row["continuity"]["status"])] += 1
        for component, status in row["component_availability"].items():
            if status not in {"PRESENT", "AVAILABLE", "COMPUTABLE"}:
                key = f"{component}:{status}"
                missing_counts[key] = missing_counts.get(key, 0) + 1
    source_binding = copy.deepcopy(next(iter(source_bindings.values())))
    body = {
        "schema": OWNER_STREAM_SCHEMA,
        "programme_id": PROGRAMME_ID,
        "protocol_id": PROTOCOL_ID,
        "owner_resolution_id": owner_resolution.get("resolution_id"),
        "owner_authority_id": OWNER_AUTHORITY_ID,
        "read_authority_id": READ_AUTHORITY_ID,
        "owner_generation_id": OWNER_GENERATION_ID,
        "owner_snapshot_schema": SNAPSHOT_SCHEMA,
        "source_binding": source_binding,
        "population_mode": population_mode,
        "snapshot_ids": ids,
        "chronology": {
            "first_effective_time": adapted[0]["effective_time"],
            "last_effective_time": adapted[-1]["effective_time"],
            "effective_time_rule": "OWNER_OBSERVATION_INTERVAL_END",
            "first_valid_time_rule": "OWNER_OBSERVATION_FIRST_VALID_TIME_DISTINCT_ROLE",
            "future_join_policy": "FAIL_CLOSED",
        },
        "population_accounting": {
            "raw_snapshot_count": len(adapted),
            "target_eligible_count": sum(row["target_eligible"] is True for row in adapted),
            "warmup_or_non_target_count": sum(row["target_eligible"] is not True for row in adapted),
            "continuity_counts": continuity_counts,
            "missing_component_counts": dict(sorted(missing_counts.items())),
            "denominator_policy": "COMPLETE_RAW_OWNER_STREAM_NO_SURVIVOR_FILTER",
        },
        "record_policy": "EXACT_OWNER_RECORDS_PRESERVED_NO_FLATTENING_NO_REPAIR",
        "break_policy": "OWNER_TYPED_BREAKS_PRESERVED_AND_CROSS_BREAK_JOIN_DENIED",
        "missingness_policy": "OWNER_TYPED_ABSENCE_PRESERVED_NO_NEUTRAL_IMPUTATION",
        "candidate_generation": "DENIED",
        "protected_source_access": "NONE",
        "validation": "LOCKED_UNCONSUMED",
        "forbidden_dependency_reachability": "NONE",
    }
    return C2OwnerStreamBinding({**body, "c2_owner_stream_binding_id": canonical_sha256(body)})


def build_factorised_source_binding_manifest(
    *,
    owner_stream_binding: C2OwnerStreamBinding,
    dense_interstitial_binding: Mapping[str, Any] | None = None,
) -> FactorisedSourceBindingManifest:
    """Declare exact primary/secondary roles without inventing dense evidence."""
    owner = owner_stream_binding.to_dict()
    if owner.get("owner_generation_id") != OWNER_GENERATION_ID:
        raise SPTOBindingError("FACTORISED_PRIMARY_OWNER_BINDING_INVALID")
    dense = copy.deepcopy(dict(dense_interstitial_binding)) if dense_interstitial_binding is not None else None
    if dense is not None:
        required = {
            "dense_evidence_binding_id",
            "owner_authority_ref",
            "owner_generation_id",
            "source_release_id",
            "source_object_ids",
            "admitted_outputs",
        }
        missing = sorted(required - set(dense))
        if missing:
            raise SPTOBindingError("DENSE_EVIDENCE_BINDING_FIELDS_MISSING", ",".join(missing))
        if dense["owner_authority_ref"] != READ_AUTHORITY_ID or dense["owner_generation_id"] != OWNER_GENERATION_ID:
            raise SPTOBindingError("DENSE_EVIDENCE_OWNER_BINDING_MISMATCH")
        if set(dense["admitted_outputs"]) != {
            "MicroCarrierContextView",
            "MicroOperationView",
            "MicroFactorisedPath",
        }:
            raise SPTOBindingError("DENSE_EVIDENCE_OUTPUT_SCOPE_MISMATCH")
    eligible = dense is not None
    body = {
        "schema": FACTORISED_SOURCE_SCHEMA,
        "programme_id": PROGRAMME_ID,
        "protocol_id": PROTOCOL_ID,
        "profile": "FACTORISED_RICH",
        "primary_source": {
            "role": "REQUIRED_PRIMARY_STATE_TARGET_SPINE",
            "type": "OWNER_STRUCTURAL_SNAPSHOT_STREAM",
            "c2_owner_stream_binding_id": owner["c2_owner_stream_binding_id"],
            "owner_generation_id": OWNER_GENERATION_ID,
            "may_be_repaired_by_secondary": False,
        },
        "secondary_source": {
            "role": "REQUIRED_SECONDARY_GENERATING_EVIDENCE",
            "type": "DENSE_INTERSTITIAL_C2_EVIDENCE",
            "binding": dense,
            "status": "BOUND" if eligible else "REQUIRED_NOT_YET_BOUND_WP6",
            "may_generate": ["MicroCarrierContextView", "MicroOperationView", "MicroFactorisedPath"],
            "may_create_replace_or_repair_owner_state_or_target": False,
        },
        "c2e": "FORBIDDEN_PRIMARY_OR_SECONDARY_GENERATING_DEPENDENCY",
        "c2p": "NON_GENERATING_OPTIONAL_ONLY_IF_PROTOCOL_PERMITS",
        "opt_c_opt_d_validation_sff": "UNREACHABLE_FROM_CANDIDATE_GENERATING_PATH",
        "factorised_rich_execution_eligible": eligible,
        "status": "COMPLETE" if eligible else "PARTIAL_SECONDARY_SOURCE_PENDING",
        "protected_source_access": "NONE",
        "authority_effect": "NONE_SOURCE_ROLE_BINDING_ONLY",
    }
    return FactorisedSourceBindingManifest(
        {**body, "factorised_source_binding_manifest_id": canonical_sha256(body)}
    )
