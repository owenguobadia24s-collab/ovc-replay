from __future__ import annotations

import copy
import hashlib
import json
from pathlib import Path
import subprocess
import sys

import pytest

from ovc.research_operations.p1cdi.reference import (
    ReferenceEngineError,
    assemble_evidence_reference,
    assign_series_generation,
    build_correspondence_plane_evidence,
    replay_as_of,
    resolve_dmrp_independence,
    stage_correspondence,
)


ROOT = Path(__file__).resolve().parents[3]
FIXTURE = json.loads(
    (ROOT / "fixtures/research_operations/p1cdi/P1CDII_WP4_REFERENCE_FIXTURES_v0_1.json").read_text()
)
BLOCK_PACKET = ROOT / "docs/programmes/p1cdi-v0-1/wp4/P1CDII_G4_ALG_INDEPENDENT_REVIEW_PACKET_v0_1.json"


def new_bundle(fields: dict | None = None, when: str | None = None) -> dict:
    return assign_series_generation(
        owner_semantic_binding=FIXTURE["owner_semantic_binding"],
        identity_fields=fields or FIXTURE["identity_a"],
        source_first_valid_time=when or FIXTURE["first_valid_time"],
    )


def existing(result: dict) -> dict:
    return {key: copy.deepcopy(result[key]) for key in ("series", "generation", "projection")}


def successor(first: dict, prior: dict | None = None) -> dict:
    inventory = [existing(first)] if prior is None else [existing(first), existing(prior)]
    predecessor = first if prior is None else prior
    fields = copy.deepcopy(FIXTURE["identity_b"])
    if prior is not None:
        fields["structural_predicates"].append("predicate:c")
    return assign_series_generation(
        owner_semantic_binding=FIXTURE["owner_semantic_binding"],
        identity_fields=fields,
        source_first_valid_time="2026-02-01T00:00:00Z" if prior is None else "2026-03-01T00:00:00Z",
        existing=inventory,
        predecessor_generation_id=predecessor["generation"]["generation_id"],
        source_explicit_successor_ref="fixture:source:successor",
    )


def vector_inputs() -> list[dict]:
    return copy.deepcopy(FIXTURE["vector_inputs"])


def assemble(vectors: list[dict], *, replications=None, nulls=None, contradictions=None) -> dict:
    return assemble_evidence_reference(
        generation_id="fixture:generation:1",
        vector_inputs=vectors,
        replication_records=FIXTURE["replications"] if replications is None else replications,
        null_records=FIXTURE["null_bindings"] if nulls is None else nulls,
        contradiction_records=FIXTURE["contradictions"] if contradictions is None else contradictions,
        frontier_first_valid_time="2026-02-01T00:00:00Z",
    )


def dmrp(left: str, right: str, state: str, **changes) -> dict:
    record = {
        "record_id": "fixture:dmrp:1",
        "owner": "DMRP_EXPOSURE_INFLUENCE_RECORDS",
        "left_generation_id": left,
        "right_generation_id": right,
        "source_ref": "fixture:dmrp:exposure:1",
        "source_generation": "fixture:dmrp:generation:1",
        "source_sha256": "d" * 64,
        "current_source_ref": "fixture:dmrp:exposure:1",
        "current_source_generation": "fixture:dmrp:generation:1",
        "current_source_sha256": "d" * 64,
        "evidence_first_valid_time": "2026-02-01T00:00:00Z",
        "currentness_state": "CURRENT",
        "independence_state": state,
        "authority_effect": "NONE",
    }
    record.update(changes)
    return record


def projections() -> tuple[dict, dict]:
    first = new_bundle()
    return first["projection"], copy.deepcopy(first["projection"])


def plane_evidence(planes: dict, left: str, right: str) -> list[dict]:
    return [
        build_correspondence_plane_evidence(
            owner="fixture:owner:path1",
            plane=plane,
            value=planes[plane],
            left_generation_id=left,
            right_generation_id=right,
            source_ref=f"fixture:source:relation:{plane}",
            source_generation="fixture:source:generation:1",
            evidence_first_valid_time="2026-02-01T00:00:00Z",
        )
        for plane in ("core_relation", "occurrence_relation", "envelope_relation", "lineage_relation")
    ]


def test_block_packet_remains_byte_identical() -> None:
    assert hashlib.sha256(BLOCK_PACKET.read_bytes()).hexdigest() == (
        "cb86d810309346eeaf8dc4e0ae7c8356ebd9b2592799462aa4975b1b7ea56e35"
    )


def test_valid_historical_predecessor_and_sequential_successors_are_immutable() -> None:
    first = new_bundle()
    second = successor(first)
    third = successor(first, second)
    assert second["resolution"] == third["resolution"] == "SEMANTIC_SUCCESSOR"
    assert len({first["generation"]["generation_id"], second["generation"]["generation_id"], third["generation"]["generation_id"]}) == 3
    assert all(item["generation"]["immutable"] is True for item in (first, second, third))


@pytest.mark.parametrize("mutation", ["field", "hidden", "source_frontier", "source_time", "generation_id"])
def test_tampered_historical_predecessor_fails_closed(mutation: str) -> None:
    first = new_bundle()
    corrupted = existing(first)
    if mutation == "field":
        corrupted["projection"]["identity_fields"]["structural_predicates"] = ["predicate:tampered"]
    elif mutation == "hidden":
        corrupted["projection"]["hidden"] = "tamper"
    elif mutation == "source_frontier":
        corrupted["generation"]["source_frontier_id"] = "fixture:frontier:tampered"
    elif mutation == "source_time":
        corrupted["generation"]["source_first_valid_time"] = "2025-12-01T00:00:00Z"
    else:
        corrupted["generation"]["generation_id"] = "p1:generation:different-branch"
        corrupted["projection"]["generation_id"] = "p1:generation:different-branch"
    with pytest.raises(ReferenceEngineError):
        assign_series_generation(
            owner_semantic_binding=FIXTURE["owner_semantic_binding"],
            identity_fields=FIXTURE["identity_b"],
            source_first_valid_time="2026-02-01T00:00:00Z",
            existing=[corrupted],
            predecessor_generation_id=corrupted["generation"]["generation_id"],
            source_explicit_successor_ref="fixture:source:successor",
        )


def test_administrative_wrapper_change_does_not_change_exact_rediscovery() -> None:
    first = new_bundle()
    wrapper_a = {"observation_id": "a", "bundle": existing(first)}
    wrapper_b = {"observation_id": "b", "bundle": copy.deepcopy(wrapper_a["bundle"])}
    left = assign_series_generation(
        owner_semantic_binding=FIXTURE["owner_semantic_binding"], identity_fields=FIXTURE["identity_a"],
        source_first_valid_time=FIXTURE["first_valid_time"], existing=[wrapper_a["bundle"]],
    )
    right = assign_series_generation(
        owner_semantic_binding=FIXTURE["owner_semantic_binding"], identity_fields=FIXTURE["identity_a"],
        source_first_valid_time=FIXTURE["first_valid_time"], existing=[wrapper_b["bundle"]],
    )
    assert left == right
    assert left["resolution"] == "EXACT_REDISCOVERY"


@pytest.mark.parametrize("field", ["denominator", "recurrence", "dependence", "separation", "integrity"])
def test_every_closed_vector_plane_rejects_invalid_value_even_mixed_with_valid(field: str) -> None:
    vectors = vector_inputs()
    vectors[0][field] = "UNREGISTERED"
    with pytest.raises(ReferenceEngineError, match="unregistered"):
        assemble(vectors)


@pytest.mark.parametrize("key", ["unknown_plane", "effect_direktion", "confidence", "confidence_score", "effective_n", "truth", "probability", "value", "ranking"])
def test_unknown_misspelled_and_hidden_scalar_planes_are_rejected(key: str) -> None:
    vectors = vector_inputs()
    vectors[0]["other_planes"][key] = 0.99
    with pytest.raises(ReferenceEngineError):
        assemble(vectors)


def test_malformed_nested_and_typed_payloads_fail_without_coercion() -> None:
    for value in ([], {"confidence": 0.9}):
        vectors = vector_inputs()
        vectors[0]["other_planes"]["typed_value"] = value
        with pytest.raises(ReferenceEngineError, match="malformed typed evidence plane"):
            assemble(vectors)
    vectors = vector_inputs()
    vectors[0]["other_planes"]["effect_direction"] = 42
    with pytest.raises(ReferenceEngineError):
        assemble(vectors)


def test_typed_integer_string_null_and_conflicting_values_remain_distinct_and_order_independent() -> None:
    vectors = vector_inputs()
    null_vector = copy.deepcopy(vectors[0])
    null_vector["record_id"] = "fixture:vector:null"
    null_vector["source_refs"] = ["fixture:source:null"]
    null_vector["other_planes"] = {"typed_value": None, "effect_direction": "AMBIGUOUS"}
    one = assemble([*vectors, null_vector])
    two = assemble([null_vector, *reversed(vectors)])
    assert one == two
    values = one["vector"]["other_planes"]["typed_value"]
    assert {json.dumps(value) for value in values} == {"42", '"42"', "null"}
    assert "confidence_score" not in one


@pytest.mark.parametrize(
    ("group", "field", "value"),
    [
        ("replications", "replication_kind", "INVALID"),
        ("replications", "outcome", "SUCCESS"),
        ("nulls", "null_class", "MISSING"),
        ("contradictions", "contradiction_type", 42),
    ],
)
def test_schema_invalid_preserved_evidence_records_fail_closed(group: str, field: str, value: object) -> None:
    replications = copy.deepcopy(FIXTURE["replications"])
    nulls = copy.deepcopy(FIXTURE["null_bindings"])
    contradictions = copy.deepcopy(FIXTURE["contradictions"])
    target = {"replications": replications, "nulls": nulls, "contradictions": contradictions}[group]
    target[0][field] = value
    with pytest.raises(ReferenceEngineError):
        assemble(vector_inputs(), replications=replications, nulls=nulls, contradictions=contradictions)


def test_preserved_record_extra_field_is_rejected_and_negative_evidence_is_retained() -> None:
    replications = copy.deepcopy(FIXTURE["replications"])
    replications[0]["confidence"] = 0.5
    with pytest.raises(ReferenceEngineError, match="exact closed field set"):
        assemble(vector_inputs(), replications=replications)
    lawful = assemble(vector_inputs())
    assert {row["outcome"] for row in lawful["replications"]} == {"PRESENT", "FAILED"}
    assert len(lawful["null_bindings"]) == 5
    assert len(lawful["contradictions"]) == 1


def test_no_dmrp_record_never_supports_affirmative_independence() -> None:
    first = new_bundle()
    left, right = first["projection"], copy.deepcopy(first["projection"])
    unknown_planes = copy.deepcopy(FIXTURE["exact_planes"])
    accepted = stage_correspondence(
        left_projection=left, right_projection=right, planes=unknown_planes,
        left_generation_record=first["generation"], right_generation_record=first["generation"],
        admission_basis="EXACT_CANONICAL_BYTES",
        left_identity_history=[existing(first)],
        right_identity_history=[existing(first)],
    )
    assert accepted["record"] is None
    assert accepted["semantic_identity"] == "EXACT"
    assert accepted["plane_admission"]["independence_state"]["value"] == "INDEPENDENCE_UNKNOWN"
    assert accepted["plane_admission"]["independence_state"]["status"] == "UNRESOLVED"
    assert accepted["independence_reason"] == "NO_EXPOSURE_RECORD"
    affirmative = {**unknown_planes, "independence_state": "AFFIRMATIVELY_INDEPENDENT"}
    with pytest.raises(ReferenceEngineError, match="DMRP-owned"):
        stage_correspondence(
            left_projection=left, right_projection=right, planes=affirmative,
            left_generation_record=first["generation"], right_generation_record=first["generation"],
            admission_basis="EXACT_CANONICAL_BYTES",
            left_identity_history=[existing(first)],
            right_identity_history=[existing(first)],
        )


@pytest.mark.parametrize("state", ["AFFIRMATIVELY_DEPENDENT", "AFFIRMATIVELY_INDEPENDENT"])
def test_exact_current_dmrp_owner_evidence_supports_only_its_explicit_state(state: str) -> None:
    first = new_bundle()
    left, right = first["projection"], copy.deepcopy(first["projection"])
    planes = {**FIXTURE["exact_planes"], "independence_state": state}
    result = stage_correspondence(
        left_projection=left, right_projection=right, planes=planes,
        left_generation_record=first["generation"], right_generation_record=first["generation"],
        admission_basis="EXACT_CANONICAL_BYTES",
        plane_evidence_records=plane_evidence(planes, left["generation_id"], right["generation_id"]),
        independence_evidence=[dmrp(left["generation_id"], right["generation_id"], state)],
        left_identity_history=[existing(first)],
        right_identity_history=[existing(first)],
    )
    assert result["record"]["executability"] == "AUTO_ADMITTED"
    assert result["independence_reason"] == "EXPLICIT_CURRENT_DMRP_EVIDENCE"


@pytest.mark.parametrize("change", [{"owner": "RCCR"}, {"right_generation_id": "wrong"}, {"source_sha256": 42}])
def test_dmrp_owner_generation_and_source_identity_mismatch_fail_closed(change: dict) -> None:
    left, right = projections()
    with pytest.raises(ReferenceEngineError):
        resolve_dmrp_independence(
            left_generation_id=left["generation_id"], right_generation_id=right["generation_id"],
            evidence_records=[dmrp(left["generation_id"], right["generation_id"], "AFFIRMATIVELY_INDEPENDENT", **change)],
        )


def test_stale_ambiguous_and_future_dmrp_evidence_resolve_unknown() -> None:
    left, right = projections()
    stale = dmrp(
        left["generation_id"], right["generation_id"], "AFFIRMATIVELY_INDEPENDENT",
        currentness_state="STALE", current_source_generation="fixture:dmrp:generation:2",
        current_source_sha256="e" * 64,
    )
    assert resolve_dmrp_independence(
        left_generation_id=left["generation_id"], right_generation_id=right["generation_id"], evidence_records=[stale]
    )["state"] == "INDEPENDENCE_UNKNOWN"
    ambiguous = dmrp(left["generation_id"], right["generation_id"], "INDEPENDENCE_UNKNOWN")
    assert resolve_dmrp_independence(
        left_generation_id=left["generation_id"], right_generation_id=right["generation_id"], evidence_records=[ambiguous]
    )["state"] == "INDEPENDENCE_UNKNOWN"
    future = dmrp(left["generation_id"], right["generation_id"], "AFFIRMATIVELY_INDEPENDENT", evidence_first_valid_time="2026-03-01T00:00:00Z")
    assert resolve_dmrp_independence(
        left_generation_id=left["generation_id"], right_generation_id=right["generation_id"],
        evidence_records=[future], as_of_time="2026-02-01T00:00:00Z",
    )["state"] == "INDEPENDENCE_UNKNOWN"


def test_dmrp_source_advance_between_reads_cannot_be_labelled_current() -> None:
    left, right = projections()
    moved = dmrp(
        left["generation_id"], right["generation_id"], "AFFIRMATIVELY_INDEPENDENT",
        current_source_generation="fixture:dmrp:generation:2", current_source_sha256="e" * 64,
    )
    with pytest.raises(ReferenceEngineError, match="source frontier moved"):
        resolve_dmrp_independence(
            left_generation_id=left["generation_id"], right_generation_id=right["generation_id"],
            evidence_records=[moved],
        )


def test_conflicting_dmrp_exposure_states_fail_closed() -> None:
    left, right = projections()
    first = dmrp(left["generation_id"], right["generation_id"], "AFFIRMATIVELY_INDEPENDENT")
    second = dmrp(
        left["generation_id"], right["generation_id"], "AFFIRMATIVELY_DEPENDENT",
        record_id="fixture:dmrp:2", source_ref="fixture:dmrp:exposure:2",
        current_source_ref="fixture:dmrp:exposure:2",
    )
    with pytest.raises(ReferenceEngineError, match="conflicting DMRP independence"):
        resolve_dmrp_independence(
            left_generation_id=left["generation_id"], right_generation_id=right["generation_id"],
            evidence_records=[first, second],
        )


def test_similarity_or_replication_cannot_substitute_for_dmrp_independence() -> None:
    first = new_bundle()
    changed = new_bundle(FIXTURE["identity_b"])
    planes = copy.deepcopy(FIXTURE["non_exact_planes"])
    with pytest.raises(ReferenceEngineError, match="DMRP-owned"):
        stage_correspondence(
            left_projection=first["projection"], right_projection=changed["projection"],
            left_generation_record=first["generation"], right_generation_record=changed["generation"],
            planes=planes, admission_basis="SOURCE_EXPLICIT_DETERMINISTIC_RELATION",
            source_relation_ref="fixture:similarity-only",
            left_identity_history=[existing(first)],
            right_identity_history=[existing(changed)],
        )
    evidence = assemble(vector_inputs())
    assert evidence["vector"]["dependence"] == "DEPENDENT"
    assert {row["replication_kind"] for row in evidence["replications"]} == {"REPRODUCTION", "SCIENTIFIC_REPLICATION"}


def test_correction_forward_replay_remains_deterministic_and_non_rewriting() -> None:
    before = copy.deepcopy(FIXTURE["history"])
    first = replay_as_of(records=before, as_of_time="2026-02-15T00:00:00Z")
    second = replay_as_of(records=list(reversed(before)), as_of_time="2026-02-15T00:00:00Z")
    assert first == second
    assert before == FIXTURE["history"]
    assert first[0]["payload"]["state"] == "CORRECTED"


def test_remediated_oracle_is_byte_identical_in_two_clean_processes() -> None:
    command = [sys.executable, "scripts/research_operations/run_p1cdii_wp4_reference.py"]
    one = subprocess.check_output(command, cwd=ROOT)
    two = subprocess.check_output(command, cwd=ROOT)
    assert one == two
    assert hashlib.sha256(one).hexdigest() != "1538a3406bcea04c047bdddf9e66f22a96b1ed78fde5b3e88427590c2104ffb8"
