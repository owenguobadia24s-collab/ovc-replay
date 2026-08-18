from __future__ import annotations

from collections import Counter
from collections.abc import Mapping
from typing import Any

from ovc.research_operations.canonical import canonical_sha256

from .currentness import build_source_frontier, evaluate_two_point_currentness
from .identity import entry_id, generation_id, logical_id, series_id


_CLASSES = {
    "EXTERNAL_THEORY_RECORD": 7,
    "IN_HOUSE_THEORY_RECORD": 19,
    "ARCHITECTURE_NEED_SEED": 4,
}
_CENSUS_FIELDS = {
    "schema", "census_id", "programme_id", "packet_id", "baseline_main",
    "baseline_tree", "membership_unit", "expected_counts", "actual_counts",
    "source_binding_manifest_ref", "source_documents", "members", "invariants",
}
_MEMBER_FIELDS = {
    "ordinal", "subject_id", "subject_class", "title", "source_artifact_id",
    "source_sha256", "drive_file_id", "drive_folder_id", "source_state",
}
_RECEIPT_FIELDS = {"schema", "receipt_id", "method", "documents", "authority_effect"}
_DOCUMENT_FIELDS = {
    "source_artifact_id", "title", "drive_file_id", "drive_folder_id", "byte_size",
    "sha256", "reproduced_subject_ids", "exact_bytes_reproduced",
}


class BootstrapValidationError(ValueError):
    """Generation-0 cannot be rebuilt from exact, complete source evidence."""


def _hashed(body: Mapping[str, Any]) -> dict[str, Any]:
    value = dict(body)
    value["content_sha256"] = canonical_sha256(value)
    return value


def _validate_census(census: Mapping[str, Any]) -> list[dict[str, Any]]:
    if not isinstance(census, Mapping) or set(census) != _CENSUS_FIELDS:
        raise BootstrapValidationError("source census must use the exact closed field set")
    if census["schema"] != "ovc-p2cti-bootstrap-source-census/v0.1":
        raise BootstrapValidationError("source census schema is invalid")
    if census["census_id"] != "P2CTII-WP0-SOURCE-CENSUS-30-v0.1":
        raise BootstrapValidationError("source census identity is invalid")
    expected = {**_CLASSES, "TOTAL": 30}
    if census["expected_counts"] != expected or census["actual_counts"] != expected:
        raise BootstrapValidationError("source census counts are not the exact Generation-0 contract")
    if type(census["members"]) is not list or len(census["members"]) != 30:
        raise BootstrapValidationError("Generation-0 requires exactly 30 census members")
    members: list[dict[str, Any]] = []
    for raw in census["members"]:
        if type(raw) is not dict or set(raw) != _MEMBER_FIELDS:
            raise BootstrapValidationError("census member must use the exact closed field set")
        if any(type(raw[name]) is not str or not raw[name] for name in _MEMBER_FIELDS - {"ordinal"}):
            raise BootstrapValidationError("census member string fields must be non-empty")
        if type(raw["ordinal"]) is not int:
            raise BootstrapValidationError("census member ordinal must be an integer")
        members.append(dict(raw))
    if [row["ordinal"] for row in members] != list(range(1, 31)):
        raise BootstrapValidationError("census ordinals must be exact and contiguous")
    ids = [row["subject_id"] for row in members]
    if len(ids) != len(set(ids)):
        raise BootstrapValidationError("duplicate Generation-0 subject_id")
    if Counter(row["subject_class"] for row in members) != Counter(_CLASSES):
        raise BootstrapValidationError("Generation-0 class distribution is invalid")
    documents = census["source_documents"]
    if type(documents) is not dict or set(documents) != {
        "P2-EXT-THEORYRECORD-DRAFT-REGISTER-v0.1", "P2-INHOUSE-THEORY-BACKLOG-v0.1"
    }:
        raise BootstrapValidationError("source document binding set is not exact")
    for row in members:
        document = documents.get(row["source_artifact_id"])
        if type(document) is not dict or any(
            row[name] != document[document_name]
            for name, document_name in (
                ("source_sha256", "sha256"),
                ("drive_file_id", "drive_file_id"),
                ("drive_folder_id", "drive_folder_id"),
            )
        ):
            raise BootstrapValidationError(f"member source binding mismatch: {row['subject_id']}")
    invariants = census["invariants"]
    if type(invariants) is not dict or any(
        invariants.get(name) is not True
        for name in (
            "no_fabricated_member", "no_omitted_member", "no_duplicate_subject_id",
            "seed_not_coerced_to_theory_record",
        )
    ) or invariants.get("scientific_payload_copied_into_p2cti") is not False:
        raise BootstrapValidationError("source census invariants are not fail-closed")
    return members


def _validate_reproduction(
    receipt: Mapping[str, Any], census: Mapping[str, Any], members: list[dict[str, Any]]
) -> dict[str, dict[str, Any]]:
    if not isinstance(receipt, Mapping) or set(receipt) != _RECEIPT_FIELDS:
        raise BootstrapValidationError("source reproduction receipt must use the exact closed field set")
    if receipt["schema"] != "ovc-p2ctii-wp3-source-reproduction/v0.1":
        raise BootstrapValidationError("source reproduction schema is invalid")
    if receipt["authority_effect"] != "NONE" or receipt["method"] != "EXACT_RAW_BYTES_AND_LOCATOR":
        raise BootstrapValidationError("source reproduction method or authority effect is invalid")
    documents = receipt["documents"]
    if type(documents) is not list or len(documents) != 2:
        raise BootstrapValidationError("both exact source documents must be reproduced")
    by_id: dict[str, dict[str, Any]] = {}
    for raw in documents:
        if type(raw) is not dict or set(raw) != _DOCUMENT_FIELDS:
            raise BootstrapValidationError("reproduced document must use the exact closed field set")
        if raw["exact_bytes_reproduced"] is not True or type(raw["byte_size"]) is not int or raw["byte_size"] <= 0:
            raise BootstrapValidationError("source bytes were not independently reproduced")
        artifact = raw["source_artifact_id"]
        if type(artifact) is not str or artifact in by_id:
            raise BootstrapValidationError("duplicate or invalid reproduced source artifact")
        expected_document = census["source_documents"].get(artifact)
        if type(expected_document) is not dict or any(
            raw[name] != expected_document[name]
            for name in ("title", "drive_file_id", "drive_folder_id", "sha256")
        ):
            raise BootstrapValidationError(f"exact source locator/hash mismatch: {artifact}")
        expected_ids = sorted(row["subject_id"] for row in members if row["source_artifact_id"] == artifact)
        if raw["reproduced_subject_ids"] != expected_ids:
            raise BootstrapValidationError(f"source subjects are not exactly reproducible: {artifact}")
        by_id[artifact] = dict(raw)
    if set(by_id) != set(census["source_documents"]):
        raise BootstrapValidationError("source reproduction omitted a bound document")
    return by_id


def build_generation_zero(
    *, census: Mapping[str, Any], source_reproduction: Mapping[str, Any],
    rccr_pointer_ref: str, rccr_pointer_sha256: str, rccr_semantic_generation: str,
    g2_alg_status: str,
) -> dict[str, Any]:
    """Losslessly rebuild the advisory Generation-0 inventory from exact sources."""

    if g2_alg_status != "PASS":
        raise BootstrapValidationError("P2CTII-G2-ALG PASS is required for WP3")
    if any(type(value) is not str or not value for value in (
        rccr_pointer_ref, rccr_pointer_sha256, rccr_semantic_generation
    )) or len(rccr_pointer_sha256) != 64:
        raise BootstrapValidationError("exact RCCR current-source identity is required")
    members = _validate_census(census)
    reproduced = _validate_reproduction(source_reproduction, census, members)
    census_sha = canonical_sha256(census)
    frontier = build_source_frontier([
        {
            "owner_programme": "RCCR",
            "source_ref": rccr_pointer_ref,
            "source_sha256": rccr_pointer_sha256,
            "semantic_generation": rccr_semantic_generation,
            "authority_refs": ["P2CTII-G2-ALG-PASS"],
            "required": True,
        },
        {
            "owner_programme": "RESEARCH_OPERATIONS_DMRP_PATH2",
            "source_ref": "registries/research_operations/p2cti/P2CTII_BOOTSTRAP_SOURCE_CENSUS_v0_1.json",
            "source_sha256": census_sha,
            "semantic_generation": census["census_id"],
            "authority_refs": ["P2CTII-WP0", "P2CTII-G2-ALG-PASS"],
            "required": True,
        },
    ])
    series = _hashed({
        "schema_family": "P2CTI_INVENTORY", "schema_version": "0.1",
        "object_type": "PATH2_THEORY_INVENTORY_SERIES", "series_id": series_id(),
        "lifecycle": "OPEN", "authority_effect": "NONE",
    })
    entries: list[dict[str, Any]] = []
    for row in members:
        owner_ref = {
            "owner_programme": "RESEARCH_OPERATIONS_DMRP_PATH2",
            "object_type": row["subject_class"],
            "object_id": row["subject_id"],
            "semantic_generation": "v0.1",
            "source_path": f"google-drive://{row['drive_file_id']}#{row['subject_id']}",
            "content_sha256": row["source_sha256"],
            "authority_refs": [census["census_id"], "P2CTII-G2-ALG-PASS"],
            "scientific_payload_copied": False,
        }
        eid = entry_id(
            series=series["series_id"], subject_id=row["subject_id"],
            subject_class=row["subject_class"], owner_object_id=row["subject_id"],
            owner_semantic_generation="v0.1",
        )
        entries.append(_hashed({
            "schema_family": "P2CTI_INVENTORY", "schema_version": "0.1",
            "object_type": "PATH2_THEORY_INVENTORY_ENTRY", "entry_id": eid,
            "series_id": series["series_id"], "subject_id": row["subject_id"],
            "subject_class": row["subject_class"], "source_object_ref": owner_ref,
            "source_locator": {
                "provider": "GOOGLE_DRIVE", "locator": row["drive_file_id"],
                "portable_parent_locator": row["drive_folder_id"],
            },
            "capture_state": "SOURCE_BOUND", "currentness_state": "CURRENT",
            "authority_refs": [census["census_id"], "P2CTII-G2-ALG-PASS"],
            "authority_effect": "NONE",
        }))
    entries.sort(key=lambda item: item["subject_id"])
    gid = generation_id(
        series=series["series_id"], generation_ordinal=0,
        member_entry_ids=[entry["entry_id"] for entry in entries],
        source_frontier=frontier["frontier_id"],
    )
    generation = _hashed({
        "schema_family": "P2CTI_INVENTORY", "schema_version": "0.1",
        "object_type": "PATH2_THEORY_INVENTORY_GENERATION", "generation_id": gid,
        "series_id": series["series_id"], "generation_ordinal": 0,
        "member_entry_ids": sorted(entry["entry_id"] for entry in entries),
        "source_frontier_id": frontier["frontier_id"], "completeness_state": "COMPLETE",
        "authority_effect": "NONE",
    })
    entry_hashes = sorted(entry["content_sha256"] for entry in entries)
    root_hash = canonical_sha256({"entry_content_sha256": entry_hashes})
    manifest_identity = {
        "generation_id": gid, "source_frontier_id": frontier["frontier_id"],
        "generation_root_sha256": root_hash,
    }
    manifest = _hashed({
        "schema_family": "P2CTI_INVENTORY", "schema_version": "0.1",
        "object_type": "P2CTI_GENERATION_MANIFEST",
        "manifest_id": logical_id("generation_manifest", manifest_identity),
        "generation_id": gid, "entry_content_sha256": entry_hashes,
        "source_frontier_id": frontier["frontier_id"],
        "generation_root_sha256": root_hash, "authority_effect": "NONE",
    })
    currentness = evaluate_two_point_currentness(
        series_id=series["series_id"], generation_id=gid,
        prebuild_frontier=frontier, prepublish_frontier=frontier,
    )
    duplicate_screen = _hashed({
        "schema": "ovc-p2ctii-wp3-duplicate-screen/v0.1",
        "generation_id": gid, "basis": "EXACT_SUBJECT_ID_AND_SOURCE_OBJECT_REF",
        "screened_subject_count": 30, "duplicate_groups": [],
        "semantic_inference_performed": False, "authority_effect": "NONE",
    })
    return _hashed({
        "schema": "ovc-p2ctii-generation-zero-bundle/v0.1",
        "series": series, "generation": generation, "entries": entries,
        "generation_manifest": manifest, "source_frontier": frontier,
        "currentness_evaluation": currentness, "duplicate_screen": duplicate_screen,
        "source_reproduction_receipt_id": source_reproduction["receipt_id"],
        "source_reproduction_sha256": canonical_sha256({
            **source_reproduction,
            "documents": [reproduced[key] for key in sorted(reproduced)],
        }),
        "source_document_byte_sizes": {
            key: reproduced[key]["byte_size"] for key in sorted(reproduced)
        },
        "historical_generation_disposition": "RETAINED_ADDRESSABLE",
        "operational_current_pointer_published": False,
        "scientific_payload_copied": False,
        "authority_effect": "NONE",
    })
