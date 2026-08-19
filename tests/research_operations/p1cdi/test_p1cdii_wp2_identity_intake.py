from __future__ import annotations

import copy
import json
from pathlib import Path

import pytest

from ovc.research_operations.p1cdi.identity import (
    build_semantic_projection,
    exact_semantic_equal,
    projection_bytes,
)
from ovc.research_operations.p1cdi.intake import build_intake_envelope, classify_exact_intake
from tests.research_operations.p1cdi.test_p1cdii_wp1_schemas import validate_contract


ROOT = Path(__file__).resolve().parents[3]
FIXTURE = json.loads(
    (ROOT / "fixtures/research_operations/p1cdi/P1CDII_WP2_RESOLVER_FIXTURES_v0_1.json").read_text()
)


def projection(generation_id: str = "p1:gen:001") -> dict:
    return build_semantic_projection(
        generation_id=generation_id,
        owner_semantic_binding="owner:ec1:path1",
        identity_fields=copy.deepcopy(FIXTURE["identity_fields"]),
    )


def envelope(source_ref: str = "ec1:result:001", source_sha256: str = "4" * 64) -> dict:
    return build_intake_envelope(
        envelope_id="p1:intake:wp2:001",
        source_ref=source_ref,
        source_sha256=source_sha256,
        source_owner="EC1",
        source_first_valid_time="2026-01-01T00:00:00Z",
        received_time="2026-08-18T00:00:00Z",
        inventory_first_valid_time="2026-08-18T00:00:00Z",
        intake_class="DISCOVERY_RESULT",
        visibility_class="PROTECTED",
    )


def test_projection_is_deterministic_and_exact_profile_bound() -> None:
    left = projection("p1:gen:left")
    right = projection("p1:gen:right")
    assert left["projection_sha256"] == right["projection_sha256"]
    assert projection_bytes(left) == projection_bytes(right)
    assert exact_semantic_equal(left, right)
    schema = json.loads(
        (ROOT / "schemas/research_operations/p1cdi/p1cdi_identity_v0_1.schema.json").read_text()
    )
    validate_contract(schema, left)

    changed = copy.deepcopy(right)
    changed["identity_fields"]["structural_predicates"] = ["predicate:b"]
    changed = build_semantic_projection(
        generation_id="p1:gen:changed",
        owner_semantic_binding=changed["owner_semantic_binding"],
        identity_fields=changed["identity_fields"],
    )
    assert not exact_semantic_equal(left, changed)

    incompatible = copy.deepcopy(right)
    incompatible["profile_id"] = "P1CDI-SEMANTIC-PROJECTION-v2"
    assert not exact_semantic_equal(left, incompatible)


def test_projection_rejects_evidence_or_physical_provenance_as_identity() -> None:
    fields = copy.deepcopy(FIXTURE["identity_fields"])
    fields["worker"] = "worker-1"
    with pytest.raises(ValueError, match="identity field contract mismatch"):
        build_semantic_projection(
            generation_id="p1:gen:bad",
            owner_semantic_binding="owner:ec1:path1",
            identity_fields=fields,
        )
    nested = copy.deepcopy(FIXTURE["identity_fields"])
    nested["applicability_scope"]["worker"] = "worker-1"
    with pytest.raises(ValueError, match="evidence/provenance"):
        build_semantic_projection(
            generation_id="p1:gen:nested-bad",
            owner_semantic_binding="owner:ec1:path1",
            identity_fields=nested,
        )


def test_projection_preserves_types_and_rejects_owner_binding_coercion() -> None:
    regression = FIXTURE["projection_type_coercion_regression"]
    valid = build_semantic_projection(
        generation_id="p1:gen:string-owner",
        owner_semantic_binding=regression["valid_owner_semantic_binding"],
        identity_fields=copy.deepcopy(FIXTURE["identity_fields"]),
    )
    malformed = copy.deepcopy(valid)
    malformed["generation_id"] = "p1:gen:integer-owner"
    malformed["owner_semantic_binding"] = regression["malformed_owner_semantic_binding"]

    with pytest.raises(ValueError, match="non-empty string"):
        projection_bytes(malformed)
    assert not exact_semantic_equal(valid, malformed)
    with pytest.raises(ValueError, match="non-empty string"):
        classify_exact_intake(
            envelope=envelope("ec1:result:type-coercion", "8" * 64),
            projection=malformed,
            existing_envelopes=[],
            existing_projections=[valid],
        )

    typed_neighbor = FIXTURE["projection_typed_value_neighbor"]
    field = typed_neighbor["identity_field"]
    number_fields = copy.deepcopy(FIXTURE["identity_fields"])
    number_fields[field] = typed_neighbor["number_value"]
    string_fields = copy.deepcopy(FIXTURE["identity_fields"])
    string_fields[field] = typed_neighbor["string_value"]
    number_projection = build_semantic_projection(
        generation_id="p1:gen:number-value",
        owner_semantic_binding="owner:typed",
        identity_fields=number_fields,
    )
    string_projection = build_semantic_projection(
        generation_id="p1:gen:string-value",
        owner_semantic_binding="owner:typed",
        identity_fields=string_fields,
    )
    assert projection_bytes(number_projection) != projection_bytes(string_projection)
    assert exact_semantic_equal(number_projection, string_projection) is typed_neighbor[
        "expected_exact_equal"
    ]

    non_string_key_fields = copy.deepcopy(FIXTURE["identity_fields"])
    non_string_key_fields["applicability_scope"] = {42: "EURUSD"}
    with pytest.raises(ValueError, match="object keys must be strings"):
        build_semantic_projection(
            generation_id="p1:gen:bad-key",
            owner_semantic_binding="owner:typed",
            identity_fields=non_string_key_fields,
        )


def test_exact_source_duplicate_is_idempotent_and_never_writes() -> None:
    item = envelope()
    result = classify_exact_intake(
        envelope=item,
        projection=projection(),
        existing_envelopes=[copy.deepcopy(item)],
        existing_projections=[],
    )
    assert result["envelope"]["intake_state"] == "DUPLICATE_EXACT"
    assert result["canonical_write"] == "DENIED"
    assert result["decision_bearing"] is False
    schema = json.loads(
        (ROOT / "schemas/research_operations/p1cdi/p1cdi_intake_v0_1.schema.json").read_text()
    )
    validate_contract(schema, result["envelope"])


def test_intake_envelope_rejects_unknown_closed_vocabulary() -> None:
    with pytest.raises(ValueError, match="source_sha256"):
        envelope(source_sha256="NOT_A_HASH")
    with pytest.raises(ValueError, match="unknown visibility_class"):
        build_intake_envelope(
            envelope_id="p1:intake:bad",
            source_ref="ec1:bad",
            source_sha256="4" * 64,
            source_owner="EC1",
            source_first_valid_time="2026-01-01T00:00:00Z",
            received_time="2026-08-18T00:00:00Z",
            inventory_first_valid_time="2026-08-18T00:00:00Z",
            intake_class="DISCOVERY_RESULT",
            visibility_class="PUBLIC_BY_DEFAULT",
        )


def test_exact_semantic_match_attaches_evidence_but_non_exact_requires_review() -> None:
    exact = classify_exact_intake(
        envelope=envelope("ec1:result:002", "5" * 64),
        projection=projection("p1:gen:new-source"),
        existing_envelopes=[],
        existing_projections=[projection("p1:gen:existing")],
    )
    assert exact["envelope"]["intake_state"] == "ADMITTED_EXISTING_DISTINCTION_EVIDENCE"

    fields = copy.deepcopy(FIXTURE["identity_fields"])
    fields["representation_dependency"] = "ALTERNATE_OWNER_BOUND"
    non_exact = build_semantic_projection(
        generation_id="p1:gen:analogue",
        owner_semantic_binding="owner:ec1:path1",
        identity_fields=fields,
    )
    review = classify_exact_intake(
        envelope=envelope("ec1:result:003", "6" * 64),
        projection=non_exact,
        existing_envelopes=[],
        existing_projections=[projection()],
        non_exact_candidate_refs=["p1:gen:existing"],
    )
    assert review["envelope"]["intake_state"] == "CORRESPONDENCE_REVIEW_REQUIRED"
    assert review["canonical_write"] == "DENIED"


def test_no_exact_or_review_candidate_is_new_but_still_advisory() -> None:
    result = classify_exact_intake(
        envelope=envelope("ec1:result:004", "7" * 64),
        projection=projection(),
        existing_envelopes=[],
        existing_projections=[],
    )
    assert result["envelope"]["intake_state"] == "ADMITTED_NEW_DISTINCTION"
    assert result["decision_bearing"] is False
    assert result["canonical_write"] == "DENIED"
