from __future__ import annotations

import copy
import json
from pathlib import Path
import subprocess
import sys

import pytest

from ovc.research_operations.p1cdi.identity import build_semantic_projection
from ovc.research_operations.p1cdi.reference import (
    ReferenceEngineError,
    assemble_evidence_reference,
    assign_series_generation,
    build_correspondence_plane_evidence,
    replay_as_of,
    stage_correspondence,
)
from tests.research_operations.p1cdi._court_state import assert_post_review5_current_state
from tests.research_operations.p1cdi.test_p1cdii_wp1_schemas import validate_contract


ROOT = Path(__file__).resolve().parents[3]
FIXTURE = json.loads((ROOT / "fixtures/research_operations/p1cdi/P1CDII_WP4_REFERENCE_FIXTURES_v0_1.json").read_text())


def bundle(fields: dict | None = None) -> dict:
    return assign_series_generation(
        owner_semantic_binding=FIXTURE["owner_semantic_binding"],
        identity_fields=fields or FIXTURE["identity_a"],
        source_first_valid_time=FIXTURE["first_valid_time"],
    )


def existing(result: dict) -> dict:
    return {key: result[key] for key in ("series", "generation", "projection")}


def dmrp_evidence(left: str, right: str, state: str = "AFFIRMATIVELY_DEPENDENT") -> dict:
    return {
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


def test_identity_is_deterministic_schema_valid_and_exact_rediscovery_is_idempotent() -> None:
    first = bundle()
    second = bundle()
    assert first == second
    assert first["resolution"] == "NEW_SERIES"
    schemas = json.loads((ROOT / "schemas/research_operations/p1cdi/p1cdi_identity_v0_1.schema.json").read_text())
    for key in ("series", "generation", "projection"):
        validate_contract(schemas, first[key])
    rediscovered = assign_series_generation(
        owner_semantic_binding=FIXTURE["owner_semantic_binding"],
        identity_fields=copy.deepcopy(FIXTURE["identity_a"]),
        source_first_valid_time=FIXTURE["first_valid_time"],
        existing=[existing(first)],
    )
    assert rediscovered["resolution"] == "EXACT_REDISCOVERY"
    assert rediscovered["created"] is False
    assert rediscovered["generation"] == first["generation"]


def test_semantic_mutation_requires_explicit_predecessor_and_creates_immutable_successor() -> None:
    first = bundle()
    with pytest.raises(ReferenceEngineError):
        assign_series_generation(
            owner_semantic_binding=FIXTURE["owner_semantic_binding"],
            identity_fields=FIXTURE["identity_b"],
            source_first_valid_time="2026-02-01T00:00:00Z",
            existing=[existing(first)],
            predecessor_generation_id=first["generation"]["generation_id"],
        )
    successor = assign_series_generation(
        owner_semantic_binding=FIXTURE["owner_semantic_binding"],
        identity_fields=FIXTURE["identity_b"],
        source_first_valid_time="2026-02-01T00:00:00Z",
        existing=[existing(first)],
        predecessor_generation_id=first["generation"]["generation_id"],
        source_explicit_successor_ref="fixture:source:successor",
    )
    assert successor["resolution"] == "SEMANTIC_SUCCESSOR"
    assert successor["series"] == first["series"]
    assert successor["generation"]["immutable"] is True
    assert successor["generation"]["generation_id"] != first["generation"]["generation_id"]


def test_correspondence_exact_auto_admission_and_non_exact_review_only() -> None:
    first = bundle()
    same = copy.deepcopy(first["projection"])
    exact = stage_correspondence(
        left_projection=first["projection"], right_projection=same,
        left_generation_record=first["generation"], right_generation_record=first["generation"],
        planes=FIXTURE["exact_planes"], admission_basis="EXACT_CANONICAL_BYTES",
        plane_evidence_records=plane_evidence(
            FIXTURE["exact_planes"], first["projection"]["generation_id"], same["generation_id"]
        ),
        independence_evidence=[
            dmrp_evidence(
                first["projection"]["generation_id"], same["generation_id"], "INDEPENDENCE_UNKNOWN"
            )
        ],
        left_identity_history=[existing(first)],
        right_identity_history=[existing(first)],
    )
    assert exact["record"]["executability"] == "AUTO_ADMITTED"
    changed_bundle = bundle(FIXTURE["identity_b"])
    changed = changed_bundle["projection"]
    with pytest.raises(ReferenceEngineError):
        stage_correspondence(
            left_projection=first["projection"], right_projection=changed,
            planes=FIXTURE["exact_planes"], admission_basis="EXACT_CANONICAL_BYTES",
        )
    staged = stage_correspondence(
        left_projection=first["projection"], right_projection=changed,
        left_generation_record=first["generation"], right_generation_record=changed_bundle["generation"],
        planes=FIXTURE["non_exact_planes"],
        admission_basis="SOURCE_EXPLICIT_DETERMINISTIC_RELATION",
        source_relation_ref="fixture:source:relation",
        plane_evidence_records=plane_evidence(
            FIXTURE["non_exact_planes"], first["projection"]["generation_id"], changed["generation_id"]
        ),
        independence_evidence=[
            dmrp_evidence(
                first["projection"]["generation_id"],
                changed["generation_id"],
            )
        ],
        left_identity_history=[existing(first)],
        right_identity_history=[existing(changed_bundle)],
    )
    assert staged["record"]["executability"] == "REVIEW_REQUIRED"
    validate_contract(
        json.loads((ROOT / "schemas/research_operations/p1cdi/p1cdi_correspondence_v0_1.schema.json").read_text()),
        staged["record"],
    )


def test_correspondence_rejects_unregistered_plane_and_hidden_similarity_path() -> None:
    first = bundle()
    changed = build_semantic_projection(
        generation_id="fixture:generation:changed",
        owner_semantic_binding=FIXTURE["owner_semantic_binding"],
        identity_fields=FIXTURE["identity_b"],
    )
    planes = {**FIXTURE["non_exact_planes"], "semantic_relation": "SIMILAR"}
    with pytest.raises(ReferenceEngineError):
        stage_correspondence(
            left_projection=first["projection"], right_projection=changed,
            planes=planes, admission_basis="SOURCE_EXPLICIT_DETERMINISTIC_RELATION",
            source_relation_ref="fixture:source:relation",
        )


def assemble(vectors: list[dict] | None = None) -> dict:
    return assemble_evidence_reference(
        generation_id="fixture:generation:1",
        vector_inputs=vectors or FIXTURE["vector_inputs"],
        replication_records=FIXTURE["replications"],
        null_records=FIXTURE["null_bindings"],
        contradiction_records=FIXTURE["contradictions"],
        frontier_first_valid_time="2026-02-01T00:00:00Z",
    )


def test_evidence_algebra_is_order_independent_non_scalar_and_schema_valid() -> None:
    left = assemble()
    right = assemble(list(reversed(FIXTURE["vector_inputs"])))
    assert left == right
    assert "confidence_score" not in left
    assert left["vector"]["denominator"] == "CAPACITY_INCOMPLETE"
    assert left["vector"]["recurrence"] == "NOT_EVALUABLE"
    assert left["vector"]["dependence"] == "DEPENDENT"
    assert left["assessment"]["scientific_assessment_state"] == "UNRESOLVED"
    schema = json.loads((ROOT / "schemas/research_operations/p1cdi/p1cdi_evidence_v0_1.schema.json").read_text())
    for key in ("frontier", "vector", "assessment"):
        validate_contract(schema, left[key])


def test_negative_null_replication_and_typed_other_planes_are_preserved() -> None:
    result = assemble()
    assert {(row["replication_kind"], row["outcome"]) for row in result["replications"]} == {
        ("REPRODUCTION", "PRESENT"), ("SCIENTIFIC_REPLICATION", "FAILED")
    }
    assert {row["null_class"] for row in result["null_bindings"]} == {
        "NULL", "RESIDUAL", "CENSORED", "CAPACITY_INCOMPLETE", "AMBIGUOUS"
    }
    typed = result["vector"]["other_planes"]["typed_value"]
    assert {json.dumps(value) for value in typed} == {"42", '"42"'}
    assert {type(value) for value in typed} == {int, str}
    assert len(result["contradictions"]) == 1


def test_missing_independence_is_unknown_and_invalid_source_ref_fails_closed() -> None:
    vectors = copy.deepcopy(FIXTURE["vector_inputs"])
    for row in vectors:
        row["dependence"] = "INDEPENDENCE_UNKNOWN"
    assert assemble(vectors)["vector"]["dependence"] == "INDEPENDENCE_UNKNOWN"
    bad = copy.deepcopy(FIXTURE["replications"])
    bad[0]["source_refs"] = [42]
    with pytest.raises(ReferenceEngineError):
        assemble_evidence_reference(
            generation_id="fixture:generation:1", vector_inputs=FIXTURE["vector_inputs"],
            replication_records=bad, null_records=[], contradiction_records=[],
            frontier_first_valid_time="2026-02-01T00:00:00Z",
        )


def test_as_of_replay_is_correction_forward_without_hindsight() -> None:
    assert replay_as_of(records=FIXTURE["history"], as_of_time="2026-01-15T00:00:00Z")[0]["payload"]["state"] == "INITIAL"
    assert replay_as_of(records=FIXTURE["history"], as_of_time="2026-02-15T00:00:00Z")[0]["payload"]["state"] == "CORRECTED"
    assert replay_as_of(records=FIXTURE["history"], as_of_time="2026-03-15T00:00:00Z")[0]["payload"]["state"] == "FUTURE"


def test_as_of_branching_correction_is_a_conflict() -> None:
    records = copy.deepcopy(FIXTURE["history"][:2])
    branch = copy.deepcopy(records[1])
    branch["record_id"] = "fixture:history:branch"
    branch["first_valid_time"] = "2026-02-02T00:00:00Z"
    records.append(branch)
    with pytest.raises(ReferenceEngineError, match="ambiguous correction frontier"):
        replay_as_of(records=records, as_of_time="2026-02-15T00:00:00Z")


def test_clean_process_reproduction_is_byte_identical() -> None:
    command = [sys.executable, "scripts/research_operations/run_p1cdii_wp4_reference.py"]
    one = subprocess.check_output(command, cwd=ROOT)
    two = subprocess.check_output(command, cwd=ROOT)
    assert one == two
    assert json.loads(one)["authority_effect"] == "NONE"


def test_historical_wp4_court_record_stopped_at_g4_and_current_state_advances_only_after_review5_pass() -> None:
    implementation = json.loads((ROOT / "docs/programmes/p1cdi-v0-1/wp4/P1CDII_WP4_IMPLEMENTATION_PACKET_v0_1.json").read_text())
    qa = json.loads((ROOT / "docs/programmes/p1cdi-v0-1/wp4/P1CDII_WP4_QA_PACKET_v0_1.json").read_text())
    completion = json.loads((ROOT / "docs/programmes/p1cdi-v0-1/wp4/P1CDII_WP4_COMPLETION_RECORD_v0_1.json").read_text())
    state = json.loads((ROOT / "records/research_operations/p1cdi/P1CDII_PROGRAMME_STATE_v0_1.json").read_text())
    assert implementation["implementation_result"] == "PASS"
    assert implementation["semantic_acceptance"] == "NOT_TAKEN_INDEPENDENT_REVIEW_REQUIRED"
    assert qa["g4_alg_decision"] == "NOT_TAKEN"
    assert completion["gate_decision"] == "NOT_TAKEN"
    assert completion["authority_delta"] == "NONE"
    assert_post_review5_current_state(state)
    validate_contract(
        json.loads((ROOT / "schemas/research_operations/p1cdi/p1cdii_programme_state_v0_1.schema.json").read_text()),
        state,
    )
