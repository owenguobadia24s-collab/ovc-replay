from __future__ import annotations

import copy
import hashlib
import itertools
import json
from pathlib import Path
import subprocess
import sys

import pytest

from ovc.research_operations.p1cdi.identity import build_semantic_projection
from ovc.research_operations.p1cdi.reference import (
    CONFORMANCE_SEPARATION_PRINCIPLE,
    ReferenceEngineError,
    assemble_evidence_reference,
    assign_series_generation,
    build_correspondence_plane_evidence,
    stage_correspondence,
)


ROOT = Path(__file__).resolve().parents[3]
FIXTURE = json.loads(
    (ROOT / "fixtures/research_operations/p1cdi/P1CDII_WP4_REFERENCE_FIXTURES_v0_1.json").read_text()
)
PRIOR_BLOCK = ROOT / "docs/programmes/p1cdi-v0-1/wp4/P1CDII_G4_ALG_INDEPENDENT_REVIEW_PACKET_v0_1.json"
FRESH_BLOCK = ROOT / "docs/programmes/p1cdi-v0-1/wp4/P1CDII_G4_ALG_FRESH_INDEPENDENT_REVIEW_PACKET_v0_1.json"
SOURCE_PLANES = ("core_relation", "occurrence_relation", "envelope_relation", "lineage_relation")


def new_bundle(fields: dict | None = None, when: str | None = None) -> dict:
    return assign_series_generation(
        owner_semantic_binding=FIXTURE["owner_semantic_binding"],
        identity_fields=fields or FIXTURE["identity_a"],
        source_first_valid_time=when or FIXTURE["first_valid_time"],
    )


def existing(result: dict) -> dict:
    return {key: copy.deepcopy(result[key]) for key in ("series", "generation", "projection")}


def successor(first: dict) -> dict:
    return assign_series_generation(
        owner_semantic_binding=FIXTURE["owner_semantic_binding"],
        identity_fields=FIXTURE["identity_b"],
        source_first_valid_time="2026-02-01T00:00:00Z",
        existing=[existing(first)],
        predecessor_generation_id=first["generation"]["generation_id"],
        source_explicit_successor_ref="fixture:source:successor",
    )


def dmrp(left: str, right: str, state: str = "INDEPENDENCE_UNKNOWN") -> dict:
    return {
        "record_id": "fixture:dmrp:remediation-2",
        "owner": "DMRP_EXPOSURE_INFLUENCE_RECORDS",
        "left_generation_id": left,
        "right_generation_id": right,
        "source_ref": "fixture:dmrp:remediation-2",
        "source_generation": "fixture:dmrp:generation:2",
        "source_sha256": "d" * 64,
        "current_source_ref": "fixture:dmrp:remediation-2",
        "current_source_generation": "fixture:dmrp:generation:2",
        "current_source_sha256": "d" * 64,
        "evidence_first_valid_time": "2026-02-01T00:00:00Z",
        "currentness_state": "CURRENT",
        "independence_state": state,
        "authority_effect": "NONE",
    }


def plane_records(planes: dict, left: str, right: str, selected: tuple[str, ...] = SOURCE_PLANES) -> list[dict]:
    return [
        build_correspondence_plane_evidence(
            owner=FIXTURE["owner_semantic_binding"],
            plane=plane,
            value=planes[plane],
            left_generation_id=left,
            right_generation_id=right,
            source_ref=f"fixture:source:remediation-2:{plane}",
            source_generation="fixture:source:generation:2",
            evidence_first_valid_time="2026-02-01T00:00:00Z",
        )
        for plane in selected
    ]


def complete_exact(first: dict, right: dict | None = None) -> dict:
    right = right or first
    left_id = first["projection"]["generation_id"]
    right_id = right["projection"]["generation_id"]
    return stage_correspondence(
        left_projection=first["projection"],
        right_projection=right["projection"],
        left_generation_record=first["generation"],
        right_generation_record=right["generation"],
        planes=FIXTURE["exact_planes"],
        admission_basis="EXACT_CANONICAL_BYTES",
        plane_evidence_records=plane_records(FIXTURE["exact_planes"], left_id, right_id),
        independence_evidence=[dmrp(left_id, right_id)],
        left_identity_history=[existing(first)],
        right_identity_history=[existing(right)],
    )


def assemble(vectors: list[dict], replications: list[dict] | None = None) -> dict:
    return assemble_evidence_reference(
        generation_id="fixture:generation:1",
        vector_inputs=vectors,
        replication_records=FIXTURE["replications"] if replications is None else replications,
        null_records=FIXTURE["null_bindings"],
        contradiction_records=FIXTURE["contradictions"],
        frontier_first_valid_time="2026-02-01T00:00:00Z",
    )


def test_both_independent_block_packets_remain_byte_identical() -> None:
    assert hashlib.sha256(PRIOR_BLOCK.read_bytes()).hexdigest() == "cb86d810309346eeaf8dc4e0ae7c8356ebd9b2592799462aa4975b1b7ea56e35"
    assert hashlib.sha256(FRESH_BLOCK.read_bytes()).hexdigest() == "2d6651e4fddf567292df59ed53c539de558b7afeea9b789a290ac4cc7daf2e19"


def test_cross_cutting_separation_principle_is_frozen_exactly() -> None:
    assert CONFORMANCE_SEPARATION_PRINCIPLE == (
        "SEMANTIC_EQUALITY",
        "CANONICAL_OBJECT_VALIDITY",
        "SOURCE_EVIDENCE_VALIDITY",
        "NON_SEMANTIC_PLANE_TRUTH",
        "SERIES_HISTORY_VALIDITY",
        "SCIENTIFIC_SUPPORT",
        "INDEPENDENCE",
    )


def test_exact_semantic_identity_without_plane_evidence_resolves_only_identity() -> None:
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
    assert set(result["unresolved_planes"]) == {*SOURCE_PLANES, "independence_state"}
    assert all(result["plane_admission"][plane]["value"] is None for plane in SOURCE_PLANES)
    assert "replication" not in result["plane_admission"]


def test_one_proved_plane_resolves_only_that_plane() -> None:
    first = new_bundle()
    generation_id = first["generation"]["generation_id"]
    result = stage_correspondence(
        left_projection=first["projection"],
        right_projection=copy.deepcopy(first["projection"]),
        left_generation_record=first["generation"],
        right_generation_record=first["generation"],
        planes=FIXTURE["exact_planes"],
        admission_basis="EXACT_CANONICAL_BYTES",
        plane_evidence_records=plane_records(
            FIXTURE["exact_planes"], generation_id, generation_id, ("core_relation",)
        ),
        left_identity_history=[existing(first)],
        right_identity_history=[existing(first)],
    )
    assert result["record"] is None
    assert result["plane_admission"]["core_relation"]["status"] == "RESOLVED"
    assert result["plane_admission"]["core_relation"]["value"] == "EXACT_CORE"
    for plane in ("occurrence_relation", "envelope_relation", "lineage_relation"):
        assert result["plane_admission"][plane]["status"] == "UNRESOLVED"


def test_all_plane_local_proofs_allow_one_complete_exact_record() -> None:
    result = complete_exact(new_bundle())
    assert result["record"]["executability"] == "AUTO_ADMITTED"
    assert result["unresolved_planes"] == []
    assert all(row["status"] == "RESOLVED" for row in result["plane_admission"].values())


def test_identical_bytes_cannot_imply_independence_lineage_or_replication() -> None:
    first = new_bundle()
    planes = {**FIXTURE["exact_planes"], "independence_state": "AFFIRMATIVELY_INDEPENDENT"}
    with pytest.raises(ReferenceEngineError, match="DMRP-owned"):
        stage_correspondence(
            left_projection=first["projection"],
            right_projection=copy.deepcopy(first["projection"]),
            left_generation_record=first["generation"],
            right_generation_record=first["generation"],
            planes=planes,
            admission_basis="EXACT_CANONICAL_BYTES",
            left_identity_history=[existing(first)],
            right_identity_history=[existing(first)],
        )
    partial = stage_correspondence(
        left_projection=first["projection"],
        right_projection=copy.deepcopy(first["projection"]),
        left_generation_record=first["generation"],
        right_generation_record=first["generation"],
        planes=FIXTURE["exact_planes"],
        admission_basis="EXACT_CANONICAL_BYTES",
        left_identity_history=[existing(first)],
        right_identity_history=[existing(first)],
    )
    assert partial["plane_admission"]["lineage_relation"]["value"] is None
    assert "replication" not in partial["plane_admission"]


@pytest.mark.parametrize("mutation", ["extra", "plane", "value", "source_hash", "source_content", "authority"])
def test_malformed_or_unregistered_plane_evidence_fails_closed(mutation: str) -> None:
    first = new_bundle()
    generation_id = first["generation"]["generation_id"]
    evidence = plane_records(FIXTURE["exact_planes"], generation_id, generation_id, ("core_relation",))[0]
    if mutation == "extra":
        evidence["hidden"] = True
    elif mutation == "plane":
        evidence["plane"] = "replication_status"
    elif mutation == "value":
        evidence["value"] = "PROBABLY_SAME"
    elif mutation == "source_hash":
        evidence["source_sha256"] = "e" * 64
    elif mutation == "source_content":
        evidence["source_content"]["value"] = "NO_SHARED_CORE"
    else:
        evidence["authority_effect"] = "PUBLICATION"
    with pytest.raises(ReferenceEngineError):
        stage_correspondence(
            left_projection=first["projection"],
            right_projection=copy.deepcopy(first["projection"]),
            left_generation_record=first["generation"],
            right_generation_record=first["generation"],
            planes=FIXTURE["exact_planes"],
            admission_basis="EXACT_CANONICAL_BYTES",
            plane_evidence_records=[evidence],
            left_identity_history=[existing(first)],
            right_identity_history=[existing(first)],
        )


def test_contradictory_plane_evidence_fails_closed_under_both_orders() -> None:
    first = new_bundle()
    generation_id = first["generation"]["generation_id"]
    left = plane_records(FIXTURE["exact_planes"], generation_id, generation_id, ("core_relation",))[0]
    contrary_planes = {**FIXTURE["exact_planes"], "core_relation": "NO_SHARED_CORE"}
    right = plane_records(contrary_planes, generation_id, generation_id, ("core_relation",))[0]
    for records in ([left, right], [right, left]):
        with pytest.raises(ReferenceEngineError, match="contradictory"):
            stage_correspondence(
                left_projection=first["projection"],
                right_projection=copy.deepcopy(first["projection"]),
                left_generation_record=first["generation"],
                right_generation_record=first["generation"],
                planes=FIXTURE["exact_planes"],
                admission_basis="EXACT_CANONICAL_BYTES",
                plane_evidence_records=records,
                left_identity_history=[existing(first)],
                right_identity_history=[existing(first)],
            )


def test_stale_plane_evidence_remains_unresolved() -> None:
    first = new_bundle()
    generation_id = first["generation"]["generation_id"]
    record = plane_records(FIXTURE["exact_planes"], generation_id, generation_id, ("core_relation",))[0]
    record["currentness_state"] = "STALE"
    record["current_source_generation"] = "fixture:source:generation:3"
    record["current_source_sha256"] = "e" * 64
    result = stage_correspondence(
        left_projection=first["projection"],
        right_projection=copy.deepcopy(first["projection"]),
        left_generation_record=first["generation"],
        right_generation_record=first["generation"],
        planes=FIXTURE["exact_planes"],
        admission_basis="EXACT_CANONICAL_BYTES",
        plane_evidence_records=[record],
        left_identity_history=[existing(first)],
        right_identity_history=[existing(first)],
    )
    assert result["plane_admission"]["core_relation"]["status"] == "UNRESOLVED"


@pytest.mark.parametrize("mutation", ["extra", "omitted", "record_type", "profile", "authority", "hash", "payload"])
def test_noncanonical_projection_wrappers_never_enter_admission(mutation: str) -> None:
    first = new_bundle()
    projection = copy.deepcopy(first["projection"])
    if mutation == "extra":
        projection["hidden_authority"] = "C_ADMITTED"
    elif mutation == "omitted":
        projection.pop("schema_version")
    elif mutation == "record_type":
        projection["record_type"] = "Path1CandidateProposal"
    elif mutation == "profile":
        projection["profile_id"] = "P1CDI-SEMANTIC-PROJECTION-v0"
    elif mutation == "authority":
        projection["authority_effect"] = "PUBLICATION"
    elif mutation == "hash":
        projection["projection_sha256"] = "f" * 64
    else:
        projection["identity_fields"]["structural_predicates"] = ["predicate:tampered"]
    with pytest.raises(ReferenceEngineError):
        stage_correspondence(
            left_projection=projection,
            right_projection=copy.deepcopy(first["projection"]),
            left_generation_record=first["generation"],
            right_generation_record=first["generation"],
            planes=FIXTURE["exact_planes"],
            admission_basis="EXACT_CANONICAL_BYTES",
            left_identity_history=[existing(first)],
            right_identity_history=[existing(first)],
        )


def test_stale_generation_wrapper_fails_before_complete_auto_admission() -> None:
    first = new_bundle()
    stale = copy.deepcopy(first["projection"])
    stale["generation_id"] = "p1:generation:" + "f" * 64
    left_id = stale["generation_id"]
    right_id = first["generation"]["generation_id"]
    with pytest.raises(ReferenceEngineError, match="generation binding"):
        stage_correspondence(
            left_projection=stale,
            right_projection=first["projection"],
            left_generation_record=first["generation"],
            right_generation_record=first["generation"],
            planes=FIXTURE["exact_planes"],
            admission_basis="EXACT_CANONICAL_BYTES",
            plane_evidence_records=plane_records(FIXTURE["exact_planes"], left_id, right_id),
            independence_evidence=[dmrp(left_id, right_id)],
            left_identity_history=[existing(first)],
            right_identity_history=[existing(first)],
        )


def test_identical_duplicate_vector_is_idempotent_and_order_independent() -> None:
    vectors = copy.deepcopy(FIXTURE["vector_inputs"])
    duplicate = copy.deepcopy(vectors[0])
    expected = assemble(vectors)
    assert assemble([duplicate, *vectors]) == expected
    assert assemble([*reversed(vectors), duplicate]) == expected


@pytest.mark.parametrize("field,value", [("denominator", "OWNER_UNRESOLVED"), ("source_refs", ["fixture:other-owner"]), ("generation_id", "fixture:generation:other")])
def test_same_vector_id_with_different_payload_owner_or_generation_conflicts(field: str, value: object) -> None:
    original = copy.deepcopy(FIXTURE["vector_inputs"][0])
    conflict = copy.deepcopy(original)
    conflict[field] = value
    for rows in ([original, conflict], [conflict, original]):
        with pytest.raises(ReferenceEngineError, match="conflicting canonical content"):
            assemble(rows)


def test_same_replication_id_with_different_outcome_conflicts_under_both_orders() -> None:
    original = copy.deepcopy(FIXTURE["replications"][0])
    conflict = copy.deepcopy(original)
    conflict["outcome"] = "FAILED"
    for rows in ([original, conflict], [conflict, original]):
        with pytest.raises(ReferenceEngineError, match="conflicting canonical content"):
            assemble(copy.deepcopy(FIXTURE["vector_inputs"]), replications=rows)


def test_same_record_id_across_evidence_owners_fails_closed() -> None:
    vectors = copy.deepcopy(FIXTURE["vector_inputs"])
    replications = copy.deepcopy(FIXTURE["replications"])
    replications[0]["record_id"] = vectors[0]["record_id"]
    with pytest.raises(ReferenceEngineError):
        assemble(vectors, replications=replications)


def test_same_content_under_distinct_legitimate_record_ids_is_retained() -> None:
    vectors = copy.deepcopy(FIXTURE["vector_inputs"])
    additional = copy.deepcopy(vectors[0])
    additional["record_id"] = "fixture:vector:legitimate-second-id"
    result = assemble([*vectors, additional])
    assert result["vector"]["integrity"] == "WARN"
    assert {"fixture:source:1", "fixture:source:2"} <= set(result["vector"]["source_refs"])


def test_same_plane_record_id_with_different_declared_hash_conflicts_under_both_orders() -> None:
    first = new_bundle()
    generation_id = first["generation"]["generation_id"]
    original = plane_records(FIXTURE["exact_planes"], generation_id, generation_id, ("core_relation",))[0]
    conflict = copy.deepcopy(original)
    conflict["source_sha256"] = "e" * 64
    for rows in ([original, conflict], [conflict, original]):
        with pytest.raises(ReferenceEngineError, match="conflicting canonical content"):
            stage_correspondence(
                left_projection=first["projection"],
                right_projection=copy.deepcopy(first["projection"]),
                left_generation_record=first["generation"],
                right_generation_record=first["generation"],
                planes=FIXTURE["exact_planes"],
                admission_basis="EXACT_CANONICAL_BYTES",
                plane_evidence_records=rows,
                left_identity_history=[existing(first)],
                right_identity_history=[existing(first)],
            )


def test_identical_plane_and_dmrp_source_duplicates_are_idempotent() -> None:
    first = new_bundle()
    generation_id = first["generation"]["generation_id"]
    planes = plane_records(FIXTURE["exact_planes"], generation_id, generation_id)
    independence = dmrp(generation_id, generation_id)
    result = stage_correspondence(
        left_projection=first["projection"],
        right_projection=copy.deepcopy(first["projection"]),
        left_generation_record=first["generation"],
        right_generation_record=first["generation"],
        planes=FIXTURE["exact_planes"],
        admission_basis="EXACT_CANONICAL_BYTES",
        plane_evidence_records=[*planes, copy.deepcopy(planes[0])],
        independence_evidence=[independence, copy.deepcopy(independence)],
        left_identity_history=[existing(first)],
        right_identity_history=[existing(first)],
    )
    assert result == complete_exact(first)


def test_same_dmrp_record_id_with_conflicting_state_fails_closed() -> None:
    first = new_bundle()
    generation_id = first["generation"]["generation_id"]
    original = dmrp(generation_id, generation_id)
    conflict = copy.deepcopy(original)
    conflict["independence_state"] = "AFFIRMATIVELY_INDEPENDENT"
    for rows in ([original, conflict], [conflict, original]):
        with pytest.raises(ReferenceEngineError, match="conflicting canonical content"):
            stage_correspondence(
                left_projection=first["projection"],
                right_projection=copy.deepcopy(first["projection"]),
                left_generation_record=first["generation"],
                right_generation_record=first["generation"],
                planes=FIXTURE["exact_planes"],
                admission_basis="EXACT_CANONICAL_BYTES",
                independence_evidence=rows,
                left_identity_history=[existing(first)],
                right_identity_history=[existing(first)],
            )


def test_identical_identity_bundle_duplicates_are_idempotent_under_all_orders() -> None:
    first = new_bundle()
    rows = [existing(first), existing(first)]
    results = []
    for order in (rows, list(reversed(rows))):
        results.append(
            assign_series_generation(
                owner_semantic_binding=FIXTURE["owner_semantic_binding"],
                identity_fields=FIXTURE["identity_a"],
                source_first_valid_time=FIXTURE["first_valid_time"],
                existing=order,
            )
        )
    assert results[0] == results[1]
    assert results[0]["resolution"] == "EXACT_REDISCOVERY"


def test_same_generation_with_divergent_projection_fails_under_both_orders() -> None:
    first = new_bundle()
    lawful = existing(first)
    conflict = existing(first)
    conflict["projection"] = build_semantic_projection(
        generation_id=first["generation"]["generation_id"],
        owner_semantic_binding=FIXTURE["owner_semantic_binding"],
        identity_fields=FIXTURE["identity_b"],
    )
    conflict["generation"]["projection_sha256"] = conflict["projection"]["projection_sha256"]
    for rows in ([lawful, conflict], [conflict, lawful]):
        with pytest.raises(ReferenceEngineError):
            assign_series_generation(
                owner_semantic_binding=FIXTURE["owner_semantic_binding"],
                identity_fields=FIXTURE["identity_a"],
                source_first_valid_time=FIXTURE["first_valid_time"],
                existing=rows,
            )


@pytest.mark.parametrize("field,value", [("first_generation_id", "p1:generation:unverifiable"), ("predecessor_series_refs", ["p1:series:divergent"])])
def test_same_generation_or_series_with_divergent_series_record_conflicts(field: str, value: object) -> None:
    first = new_bundle()
    lawful = existing(first)
    conflict = existing(first)
    conflict["series"][field] = value
    for rows in ([lawful, conflict], [conflict, lawful]):
        with pytest.raises(ReferenceEngineError):
            assign_series_generation(
                owner_semantic_binding=FIXTURE["owner_semantic_binding"],
                identity_fields=FIXTURE["identity_a"],
                source_first_valid_time=FIXTURE["first_valid_time"],
                existing=rows,
            )


def test_successor_without_root_generation_bundle_fails_closed() -> None:
    first = new_bundle()
    second = successor(first)
    with pytest.raises(ReferenceEngineError, match="first-generation binding"):
        assign_series_generation(
            owner_semantic_binding=FIXTURE["owner_semantic_binding"],
            identity_fields=FIXTURE["identity_b"],
            source_first_valid_time="2026-02-01T00:00:00Z",
            existing=[existing(second)],
        )


def test_invalid_deterministic_first_series_identity_fails_closed() -> None:
    first = new_bundle()
    invalid = existing(first)
    invalid["series"]["series_id"] = "p1:series:" + "f" * 64
    invalid["generation"]["series_id"] = invalid["series"]["series_id"]
    with pytest.raises(ReferenceEngineError, match="binding mismatch"):
        assign_series_generation(
            owner_semantic_binding=FIXTURE["owner_semantic_binding"],
            identity_fields=FIXTURE["identity_a"],
            source_first_valid_time=FIXTURE["first_valid_time"],
            existing=[invalid],
        )


def test_divergent_successor_history_fails_for_every_input_permutation() -> None:
    first = new_bundle()
    second = successor(first)
    divergent = existing(second)
    divergent["series"]["predecessor_series_refs"] = ["p1:series:divergent-history"]
    rows = [existing(first), existing(second), divergent]
    for order in itertools.permutations(rows):
        with pytest.raises(ReferenceEngineError):
            assign_series_generation(
                owner_semantic_binding=FIXTURE["owner_semantic_binding"],
                identity_fields=FIXTURE["identity_b"],
                source_first_valid_time="2026-02-01T00:00:00Z",
                existing=list(order),
            )


def test_verified_successor_history_is_order_independent_with_idempotent_copies() -> None:
    first = new_bundle()
    second = successor(first)
    rows = [existing(first), existing(second), existing(second)]
    outputs = []
    for order in itertools.permutations(rows):
        outputs.append(
            assign_series_generation(
                owner_semantic_binding=FIXTURE["owner_semantic_binding"],
                identity_fields=FIXTURE["identity_b"],
                source_first_valid_time="2026-02-01T00:00:00Z",
                existing=list(order),
            )
        )
    assert all(output == outputs[0] for output in outputs)
    assert outputs[0]["resolution"] == "EXACT_REDISCOVERY"


def test_remediation_2_oracle_is_deterministic_and_preserves_historical_oracles() -> None:
    command = [sys.executable, "scripts/research_operations/run_p1cdii_wp4_reference.py"]
    one = subprocess.check_output(command, cwd=ROOT)
    two = subprocess.check_output(command, cwd=ROOT)
    assert one == two
    digest = hashlib.sha256(one).hexdigest()
    assert digest not in {
        "1538a3406bcea04c047bdddf9e66f22a96b1ed78fde5b3e88427590c2104ffb8",
        "81ee71dd614606dc9fece46f5b5b0822de7b2812f1d4d641cdedc23355935c21",
    }
