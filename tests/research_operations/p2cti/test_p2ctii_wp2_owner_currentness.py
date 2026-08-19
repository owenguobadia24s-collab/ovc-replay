from __future__ import annotations

import copy
import json
from pathlib import Path
import re

import pytest

from ovc.research_operations.p2cti.currentness import (
    build_source_frontier,
    dependency_bounded_invalidation,
    evaluate_two_point_currentness,
    require_g2_alg_for_decision_bearing_pointer,
)
from ovc.research_operations.p2cti.identity import generation_id, series_id
from ovc.research_operations.p2cti.sources import resolve_owner_predicate


ROOT = Path(__file__).resolve().parents[3]
FIXTURE = json.loads(
    (ROOT / "fixtures/research_operations/p2cti/P2CTII_WP2_OWNER_CURRENTNESS_FIXTURES_v0_1.json").read_text()
)
OWNER_REGISTRY = json.loads(
    (ROOT / "registries/research_operations/p2cti/P2CTI_OWNER_SOURCE_REGISTRY_v0_1.json").read_text()
)


def _resolve(schema_root: dict, reference: str) -> dict:
    if not reference.startswith("#/"):
        raise AssertionError(f"non-local schema reference: {reference}")
    node: object = schema_root
    for part in reference[2:].split("/"):
        assert isinstance(node, dict)
        node = node[part]
    assert isinstance(node, dict)
    return node


def _validate_schema(schema: dict, instance: object, root: dict | None = None) -> None:
    """Validate the closed WP1 schema vocabulary without optional packages."""

    root = root or schema
    if "$ref" in schema:
        _validate_schema(_resolve(root, schema["$ref"]), instance, root)
        return
    if "oneOf" in schema:
        matches = 0
        for branch in schema["oneOf"]:
            try:
                _validate_schema(branch, instance, root)
            except (AssertionError, KeyError, TypeError):
                continue
            matches += 1
        assert matches == 1
        return
    if "const" in schema:
        assert instance == schema["const"]
    if "enum" in schema:
        assert instance in schema["enum"]
    expected = schema.get("type")
    if expected is not None:
        allowed = [expected] if isinstance(expected, str) else expected
        checks = {
            "object": lambda value: isinstance(value, dict),
            "array": lambda value: isinstance(value, list),
            "string": lambda value: isinstance(value, str),
            "boolean": lambda value: isinstance(value, bool),
            "null": lambda value: value is None,
        }
        assert any(checks[kind](instance) for kind in allowed)
    if isinstance(instance, dict):
        properties = schema.get("properties", {})
        assert not (set(schema.get("required", [])) - set(instance))
        if schema.get("additionalProperties") is False:
            assert not (set(instance) - set(properties))
        for name, value in instance.items():
            if name in properties:
                _validate_schema(properties[name], value, root)
    if isinstance(instance, list):
        assert len(instance) >= schema.get("minItems", 0)
        if "maxItems" in schema:
            assert len(instance) <= schema["maxItems"]
        if schema.get("uniqueItems"):
            encoded = [json.dumps(value, sort_keys=True, separators=(",", ":")) for value in instance]
            assert len(encoded) == len(set(encoded))
        if isinstance(schema.get("items"), dict):
            for value in instance:
                _validate_schema(schema["items"], value, root)
    if isinstance(instance, str):
        assert len(instance) >= schema.get("minLength", 0)
        if "pattern" in schema:
            assert re.search(schema["pattern"], instance) is not None


def _frontier(rows: list[dict], *, unresolved: tuple[str, ...] = ()) -> dict:
    return build_source_frontier(copy.deepcopy(rows), unresolved_reasons=unresolved)


def _generation(frontier_id: str) -> tuple[str, str]:
    series = series_id()
    generation = generation_id(
        series=series,
        generation_ordinal=0,
        member_entry_ids=["p2cti:entry:" + "a" * 64],
        source_frontier=frontier_id,
    )
    return series, generation


def test_declared_owner_resolution_is_order_independent_and_advisory() -> None:
    evidence = FIXTURE["owner_evidence"]
    forward = resolve_owner_predicate(
        object_type="THEORY_RECORD",
        predicate="EVIDENCE_STATE",
        evidence=evidence,
        owner_registry=OWNER_REGISTRY,
    )
    reverse = resolve_owner_predicate(
        object_type="THEORY_RECORD",
        predicate="EVIDENCE_STATE",
        evidence=list(reversed(evidence)),
        owner_registry=OWNER_REGISTRY,
    )
    assert forward == reverse
    assert forward["resolution_state"] == "RESOLVED"
    assert forward["controlling_owner"] == "RESEARCH_OPERATIONS_DMRP_PATH2"
    assert forward["semantic_generation"] == "1"
    assert forward["visibility_state"] == "REFERENCE_ONLY"
    assert forward["decision_bearing"] is False


def test_missing_wrong_owner_and_generation_conflict_fail_closed() -> None:
    missing = resolve_owner_predicate(
        object_type="THEORY_RECORD",
        predicate="EVIDENCE_STATE",
        evidence=[],
        owner_registry=OWNER_REGISTRY,
    )
    assert missing["resolution_state"] == "UNRESOLVED"
    assert missing["warnings"] == ["OWNER_SOURCE_MISSING"]

    wrong = copy.deepcopy(FIXTURE["owner_evidence"][0])
    wrong["owner_programme"] = "CONVENIENT_NON_OWNER"
    conflict = resolve_owner_predicate(
        object_type="THEORY_RECORD",
        predicate="EVIDENCE_STATE",
        evidence=[wrong],
        owner_registry=OWNER_REGISTRY,
    )
    assert conflict["resolution_state"] == "CONFLICT"
    assert conflict["warnings"] == ["STATE_OWNER_CONFLICT"]

    advanced = copy.deepcopy(FIXTURE["owner_evidence"][0])
    advanced["semantic_generation"] = "2"
    advanced["source_sha256"] = "3" * 64
    generation_conflict = resolve_owner_predicate(
        object_type="THEORY_RECORD",
        predicate="EVIDENCE_STATE",
        evidence=[FIXTURE["owner_evidence"][0], advanced],
        owner_registry=OWNER_REGISTRY,
    )
    assert generation_conflict["resolution_state"] == "CONFLICT"


def test_recency_path_title_and_convenience_fields_are_rejected() -> None:
    recency_biased = copy.deepcopy(FIXTURE["owner_evidence"][0])
    recency_biased["observed_at"] = "2099-01-01T00:00:00Z"
    with pytest.raises(ValueError, match="exact closed field set"):
        resolve_owner_predicate(
            object_type="THEORY_RECORD",
            predicate="EVIDENCE_STATE",
            evidence=[recency_biased],
            owner_registry=OWNER_REGISTRY,
        )


def test_source_frontier_is_order_independent_and_schema_conformant() -> None:
    before = _frontier(FIXTURE["frontier_before"])
    reverse = _frontier(list(reversed(FIXTURE["frontier_before"])))
    assert before["frontier_id"] == reverse["frontier_id"]
    assert before["content_sha256"] == reverse["content_sha256"]
    schema = json.loads(
        (ROOT / "schemas/research_operations/p2cti/p2cti_source_frontier_v0_1.schema.json").read_text()
    )
    _validate_schema(schema, before)


def test_two_point_equal_frontier_is_current_but_not_decision_bearing() -> None:
    before = _frontier(FIXTURE["frontier_before"])
    same = _frontier(list(reversed(FIXTURE["frontier_before"])))
    series, generation = _generation(before["frontier_id"])
    result = evaluate_two_point_currentness(
        series_id=series,
        generation_id=generation,
        prebuild_frontier=before,
        prepublish_frontier=same,
    )
    assert result["currentness_state"] == "CURRENT"
    assert result["frontiers_equal"] is True
    assert result["decision_bearing"] is False
    assert result["operational_pointer_switched"] is False
    assert result["historical_generation_disposition"] == "RETAINED_ADDRESSABLE"
    schema = json.loads(
        (ROOT / "schemas/research_operations/p2cti/p2cti_current_pointer_v0_1.schema.json").read_text()
    )
    _validate_schema(schema, result["advisory_pointer"])


def test_generation_advance_and_incomplete_frontier_never_fall_back() -> None:
    before = _frontier(FIXTURE["frontier_before"])
    advanced = _frontier(FIXTURE["frontier_generation_advanced"])
    series, generation = _generation(before["frontier_id"])
    moved = evaluate_two_point_currentness(
        series_id=series,
        generation_id=generation,
        prebuild_frontier=before,
        prepublish_frontier=advanced,
    )
    assert moved["currentness_state"] == "SOURCE_GENERATION_ADVANCED"
    assert moved["decision_bearing"] is False

    incomplete = _frontier(
        FIXTURE["frontier_generation_advanced"], unresolved=("OWNER_SOURCE_MISSING",)
    )
    unresolved = evaluate_two_point_currentness(
        series_id=series,
        generation_id=generation,
        prebuild_frontier=before,
        prepublish_frontier=incomplete,
    )
    assert unresolved["currentness_state"] == "UNRESOLVED"
    assert unresolved["warnings"] == ["CURRENTNESS_UNRESOLVED"]


def test_dependency_invalidation_is_exact_and_preserves_history() -> None:
    before = _frontier(FIXTURE["frontier_before"])
    advanced = _frontier(FIXTURE["frontier_generation_advanced"])
    result = dependency_bounded_invalidation(
        previous_frontier=before,
        current_frontier=advanced,
        generation_dependencies={
            "p2cti:generation:affected": [
                "RESEARCH_OPERATIONS_DMRP_PATH2|records/research_operations/path2/theory-001.json"
            ],
            "p2cti:generation:unaffected": [
                "RCCR|records/research_operations/rccr/assessment-001.json"
            ],
        },
    )
    assert result["affected_generation_ids"] == ["p2cti:generation:affected"]
    assert result["unaffected_generation_ids"] == ["p2cti:generation:unaffected"]
    assert result["historical_generations_preserved"] is True
    assert result["invalidation_scope"] == "EXACT_DEPENDENCIES_ONLY"


def test_g2_alg_is_a_hard_decision_bearing_pointer_boundary() -> None:
    with pytest.raises(PermissionError, match="P2CTII-G2-ALG"):
        require_g2_alg_for_decision_bearing_pointer(g2_alg_status="NOT_TAKEN")


def test_fresh_review_pass_is_materialised_without_rewriting_prior_block() -> None:
    review = json.loads(
        (ROOT / "docs/programmes/p2cti-v0-1/wp2/P2CTII_G2_ALG_CONSOLIDATED_REVIEW_PACKET_v0_1.json").read_text()
    )
    state = json.loads(
        (ROOT / "records/research_operations/p2cti/P2CTII_PROGRAMME_STATE_v0_1.json").read_text()
    )
    remediation_qa = json.loads(
        (ROOT / "docs/programmes/p2cti-v0-1/wp2/P2CTII_WP2_REMEDIATION_1_QA_PACKET_v0_1.json").read_text()
    )
    remediation_decision = json.loads(
        (ROOT / "docs/programmes/p2cti-v0-1/wp2/P2CTII_WP2_REMEDIATION_1_DECISION_v0_1.json").read_text()
    )
    fresh_review = json.loads(
        (ROOT / "docs/programmes/p2cti-v0-1/wp2/P2CTII_G2_ALG_FRESH_REVIEW_COMMISSION_v0_1.json").read_text()
    )
    fresh_decision = json.loads(
        (
            ROOT
            / "docs/programmes/p2cti-v0-1/wp2/P2CTII_G2_ALG_FRESH_INDEPENDENT_REVIEW_PACKET_v0_1.json"
        ).read_text()
    )
    assert review["gate_class"] == "INDEPENDENT_NON_OPERATOR_BLOCKING"
    assert review["reviewer_binding"]["status"] == "BOUND"
    assert review["gate_decision"] == "BLOCK"
    assert review["decision_bearing_pointer"] == "DENIED"
    assert review["operational_current_pointer_publication"] == "DENIED_SEPARATELY_GOVERNED"
    assert remediation_qa["status"] == "PASS_EXACT_FINAL"
    assert remediation_qa["p2ctii_g2_alg_decision"] == "UNRESOLVED_REQUIRES_FRESH_CONFLICT_FREE_INDEPENDENT_REVIEW"
    assert remediation_decision["decision"] == "PASS_REMEDIATION"
    assert remediation_decision["p2ctii_g2_alg"]["status"] == "UNRESOLVED"
    assert fresh_review["status"] == "COMMISSIONED_AWAITING_CONFLICT_FREE_REVIEWER_BINDING"
    assert fresh_review["reviewer_binding"]["reviewer_identity"] is None
    assert fresh_decision["gate_decision"] == "PASS"
    assert fresh_decision["authority_delta"] == "NONE"
    assert fresh_decision["programme_state_materialised_by_this_packet"] is False
    assert state["packet_id"] in {
        "P2CTII-G2-ALG",
        "P2CTII-WP3",
        "P2CTII-G4-ALG",
        "P2CTII-WP4-REMEDIATION-1",
        "P2CTII-G4-ALG-FRESH-INDEPENDENT-REVIEW-AFTER-WP4-REMEDIATION-1",
        "P2CTII-WP4-REMEDIATION-2",
    }
    assert state["status"] in {
        "COMPLETED",
        "APPROVED",
        "AWAITING_CONFLICT_FREE_INDEPENDENT_REVIEW",
        "BLOCKED_AWAITING_P2CTII-WP4-REMEDIATION-1",
        "IMPLEMENTED_AWAITING_EXACT_FINAL_ASSURANCE",
        "PASS_REMEDIATION_AWAITING_MATERIALISATION",
        "BLOCKED_AWAITING_P2CTII-WP4-REMEDIATION-2",
    }
    assert state["next_packet"] in {
        "P2CTII-WP3",
        "P2CTII-WP4",
        "P2CTII-G4-ALG",
        "P2CTII-WP4-REMEDIATION-1",
        "P2CTII-WP4-REMEDIATION-1-QA-DECISION",
        "P2CTII-G4-ALG-FRESH-INDEPENDENT-REVIEW-AFTER-WP4-REMEDIATION-1",
        "P2CTII-WP4-REMEDIATION-2",
        "P2CTII-G4-ALG-FRESH-INDEPENDENT-REVIEW-AFTER-WP4-REMEDIATION-2",
        "P2CTII-WP5",
    }
    if state["packet_id"] in {"P2CTII-WP3", "P2CTII-G4-ALG"}:
        assert any(
            packet["packet_id"] == "P2CTII-WP3"
            and packet["decision"] == "P2CTII-G3_DELEGATED_PASS"
            for packet in state["completed_packets"]
        )
    assert state["p2ctii_g2_alg_status"] == "PASS"
    assert state["currentness_resolver_status"] == "MECHANICALLY_QUALIFIED_G2_ALG_PASS"
    assert state["decision_bearing_currentness_eligibility"] == (
        "MECHANICALLY_QUALIFIED_NOT_OPERATIONALLY_PUBLISHED"
    )
    assert state["operational_current_pointer_publication"] == "DENIED_SEPARATELY_GOVERNED"
    assert state["remediation_author_may_grant_g2_alg_pass"] is False
    assert state["wp3_authorised"] is True
    if state["packet_id"] == (
        "P2CTII-G4-ALG-FRESH-INDEPENDENT-REVIEW-AFTER-WP4-REMEDIATION-1"
    ):
        assert state["p2ctii_g4_alg_status"] == "BLOCK"
        assert state["blockers"] == [
            "P2CTII_G4_ALG_FRESH_BLOCK_001_OWNER_PROVENANCE_AND_CANONICAL_EVIDENCE_ORDER",
            "P2CTII_G4_ALG_FRESH_BLOCK_002_RESEARCH_QUESTION_AND_FRONTIER_CURRENTNESS_NOT_AUTHORITATIVELY_BOUND",
            "P2CTII_G4_ALG_FRESH_BLOCK_003_QUERY_CONSTITUENT_COHERENCE_AND_WARNING_PROPAGATION",
            "P2CTII_G4_ALG_FRESH_BLOCK_004_CROSS_MODE_CURRENT_EXPOSURE_AND_FORMAL_CORRESPONDENCE_NOT_BOUND",
            "P2CTII_G4_ALG_FRESH_BLOCK_005_QUERY_COLLECTION_ORDER_NOT_CANONICAL",
        ]
    elif state.get("p2ctii_g4_alg_status") == "BLOCK":
        assert state["blockers"] == [
            "P2CTII_G4_ALG_BLOCK_001_OWNER_GENERATION_AND_SOURCE_EVIDENCE_NOT_RESOLVED",
            "P2CTII_G4_ALG_BLOCK_002_RESEARCH_QUESTION_CURRENTNESS_NOT_BOUND",
            "P2CTII_G4_ALG_BLOCK_003_QUERY_STATE_COHERENCE_AND_CONFLICT_PRESERVATION_GAP",
            "P2CTII_G4_ALG_BLOCK_004_QUERY_VISIBILITY_AND_EXPOSURE_ENFORCEMENT_GAP",
            "P2CTII_G4_ALG_BLOCK_005_QUERY_RETURN_ALIAS_MUTATES_HELD_STATE",
        ]
    elif state["packet_id"] == "P2CTII-WP4-REMEDIATION-1":
        assert state["blockers"] == [
            "P2CTII_G4_ALG_FRESH_INDEPENDENT_REVIEW_REQUIRED",
        ]
    elif state["packet_id"] == "P2CTII-WP4-REMEDIATION-2":
        assert state["blockers"] == [
            "P2CTII_G4_ALG_FRESH_INDEPENDENT_REVIEW_AFTER_REMEDIATION_2_REQUIRED",
        ]
    else:
        assert state["blockers"] == []
