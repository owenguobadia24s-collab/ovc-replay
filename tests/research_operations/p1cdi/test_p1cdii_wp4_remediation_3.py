from __future__ import annotations

import copy
import hashlib
import json
from pathlib import Path

import pytest

from ovc.research_operations.p1cdi.reference import (
    ReferenceEngineError,
    assign_series_generation,
    build_correspondence_plane_evidence,
    stage_correspondence,
)


ROOT = Path(__file__).resolve().parents[3]
FIXTURE = json.loads(
    (ROOT / "fixtures/research_operations/p1cdi/P1CDII_WP4_REFERENCE_FIXTURES_v0_1.json").read_text()
)
SOURCE_PLANES = ("core_relation", "occurrence_relation", "envelope_relation", "lineage_relation")


def new_bundle(fields: dict | None = None, when: str | None = None) -> dict:
    return assign_series_generation(
        owner_semantic_binding=FIXTURE["owner_semantic_binding"],
        identity_fields=fields or FIXTURE["identity_a"],
        source_first_valid_time=when or FIXTURE["first_valid_time"],
    )


def existing(result: dict) -> dict:
    return {key: copy.deepcopy(result[key]) for key in ("series", "generation", "projection")}


def plane_records(generation_id: str) -> list[dict]:
    return [
        build_correspondence_plane_evidence(
            owner=FIXTURE["owner_semantic_binding"],
            plane=plane,
            value=FIXTURE["exact_planes"][plane],
            left_generation_id=generation_id,
            right_generation_id=generation_id,
            source_ref=f"fixture:source:remediation-3:{plane}",
            source_generation="fixture:source:generation:3",
            evidence_first_valid_time="2026-02-01T00:00:00Z",
        )
        for plane in SOURCE_PLANES
    ]


def dmrp(generation_id: str) -> dict:
    return {
        "record_id": "fixture:dmrp:remediation-3",
        "owner": "DMRP_EXPOSURE_INFLUENCE_RECORDS",
        "left_generation_id": generation_id,
        "right_generation_id": generation_id,
        "source_ref": "fixture:dmrp:remediation-3",
        "source_generation": "fixture:dmrp:generation:3",
        "source_sha256": "d" * 64,
        "current_source_ref": "fixture:dmrp:remediation-3",
        "current_source_generation": "fixture:dmrp:generation:3",
        "current_source_sha256": "d" * 64,
        "evidence_first_valid_time": "2026-02-01T00:00:00Z",
        "currentness_state": "CURRENT",
        "independence_state": "INDEPENDENCE_UNKNOWN",
        "authority_effect": "NONE",
    }


def stage_exact(first: dict, *, planes: list[dict] | None = None, independence: list[dict] | None = None) -> dict:
    generation_id = first["generation"]["generation_id"]
    return stage_correspondence(
        left_projection=first["projection"],
        right_projection=copy.deepcopy(first["projection"]),
        left_generation_record=first["generation"],
        right_generation_record=first["generation"],
        planes=FIXTURE["exact_planes"],
        admission_basis="EXACT_CANONICAL_BYTES",
        plane_evidence_records=plane_records(generation_id) if planes is None else planes,
        independence_evidence=[dmrp(generation_id)] if independence is None else independence,
        left_identity_history=[existing(first)],
        right_identity_history=[existing(first)],
    )


def successor(first: dict, when: str) -> dict:
    return assign_series_generation(
        owner_semantic_binding=FIXTURE["owner_semantic_binding"],
        identity_fields=FIXTURE["identity_b"],
        source_first_valid_time=when,
        existing=[existing(first)],
        predecessor_generation_id=first["generation"]["generation_id"],
        source_explicit_successor_ref="fixture:source:remediation-3:successor",
    )


def test_all_three_prior_block_packets_remain_byte_identical() -> None:
    paths = {
        "P1CDII_G4_ALG_INDEPENDENT_REVIEW_PACKET_v0_1.json": "cb86d810309346eeaf8dc4e0ae7c8356ebd9b2592799462aa4975b1b7ea56e35",
        "P1CDII_G4_ALG_FRESH_INDEPENDENT_REVIEW_PACKET_v0_1.json": "2d6651e4fddf567292df59ed53c539de558b7afeea9b789a290ac4cc7daf2e19",
        "P1CDII_G4_ALG_FRESH_INDEPENDENT_REVIEW_2_PACKET_v0_1.json": "894d31b1dd1c7408f3fd3f7d65f917fe744c72b23bef33a15560992fdb6b7580",
    }
    base = ROOT / "docs/programmes/p1cdi-v0-1/wp4"
    assert {
        name: hashlib.sha256((base / name).read_bytes()).hexdigest()
        for name in paths
    } == paths


def test_partial_admission_rejects_stale_generation_wrapper_before_any_plane_result() -> None:
    first = new_bundle()
    stale = copy.deepcopy(first["projection"])
    stale["generation_id"] = "p1:generation:" + "f" * 64
    with pytest.raises(ReferenceEngineError, match="stale or mismatched generation binding"):
        stage_correspondence(
            left_projection=stale,
            right_projection=first["projection"],
            left_generation_record=first["generation"],
            right_generation_record=first["generation"],
            planes=FIXTURE["exact_planes"],
            admission_basis="EXACT_CANONICAL_BYTES",
            left_identity_history=[existing(first)],
            right_identity_history=[existing(first)],
        )


def test_right_hand_stale_wrapper_is_equally_rejected_on_partial_path() -> None:
    first = new_bundle()
    stale = copy.deepcopy(first["projection"])
    stale["generation_id"] = "p1:generation:" + "e" * 64
    with pytest.raises(ReferenceEngineError, match="stale or mismatched generation binding"):
        stage_correspondence(
            left_projection=first["projection"],
            right_projection=stale,
            left_generation_record=first["generation"],
            right_generation_record=first["generation"],
            planes=FIXTURE["exact_planes"],
            admission_basis="EXACT_CANONICAL_BYTES",
            left_identity_history=[existing(first)],
            right_identity_history=[existing(first)],
        )


def test_partial_admission_without_generation_proof_fails_closed() -> None:
    first = new_bundle()
    with pytest.raises(ReferenceEngineError, match="requires an exact generation binding"):
        stage_correspondence(
            left_projection=first["projection"],
            right_projection=copy.deepcopy(first["projection"]),
            planes=FIXTURE["exact_planes"],
            admission_basis="EXACT_CANONICAL_BYTES",
        )


def test_lawfully_bound_partial_admission_remains_plane_local() -> None:
    first = new_bundle()
    result = stage_correspondence(
        left_projection=first["projection"],
        right_projection=copy.deepcopy(first["projection"]),
        left_generation_record=first["generation"],
        right_generation_record=first["generation"],
        planes=FIXTURE["exact_planes"],
        admission_basis="EXACT_CANONICAL_BYTES",
        left_identity_history=[existing(first)],
        right_identity_history=[existing(first)],
    )
    assert result["semantic_identity"] == "EXACT"
    assert result["record"] is None
    assert result["executability"] == "BLOCKED_UNRESOLVED_PLANES"


@pytest.mark.parametrize("collision_owner", ["plane", "dmrp"])
def test_cross_plane_dmrp_record_id_collision_fails_before_auto_admission(collision_owner: str) -> None:
    first = new_bundle()
    generation_id = first["generation"]["generation_id"]
    planes = plane_records(generation_id)
    independence = dmrp(generation_id)
    if collision_owner == "plane":
        independence["record_id"] = planes[0]["record_id"]
    else:
        planes[0]["record_id"] = independence["record_id"]
    with pytest.raises(ReferenceEngineError, match="conflicting canonical content"):
        stage_exact(first, planes=planes, independence=[independence])


def test_distinct_plane_and_dmrp_record_identities_still_auto_admit_exact_proof() -> None:
    result = stage_exact(new_bundle())
    assert result["record"]["executability"] == "AUTO_ADMITTED"
    assert result["unresolved_planes"] == []
    assert result["authority_effect"] == "NONE"


@pytest.mark.parametrize(
    "when",
    [
        "2025-01-01T00:00:00Z",
        "2026-01-01T00:00:00Z",
        "2026-01-01T01:00:00+01:00",
    ],
)
def test_retrograde_or_equal_semantic_successor_time_fails_closed(when: str) -> None:
    first = new_bundle(when="2026-01-01T00:00:00Z")
    with pytest.raises(ReferenceEngineError, match="must move strictly forward"):
        successor(first, when)


@pytest.mark.parametrize(
    "when",
    ["2026-01-01T00:00:00.000001Z", "2025-12-31T20:00:00-05:00"],
)
def test_strictly_forward_semantic_successor_remains_deterministic(when: str) -> None:
    first = new_bundle(when="2026-01-01T00:00:00Z")
    result = successor(first, when)
    assert result["resolution"] == "SEMANTIC_SUCCESSOR"
    assert result["created"] is True
    assert result["predecessor_generation_id"] == first["generation"]["generation_id"]
    assert result["authority_effect"] == "NONE"


def test_new_series_is_not_subject_to_successor_time_comparison() -> None:
    result = new_bundle(when="2025-01-01T00:00:00Z")
    assert result["resolution"] == "NEW_SERIES"
    assert result["created"] is True
    assert result["authority_effect"] == "NONE"
