from __future__ import annotations

from copy import deepcopy
import json
import hashlib
import os
from pathlib import Path
import subprocess
import sys

import pytest

from ovc.research_operations.p2cti.demand import (
    DEMAND_CLASSES,
    DemandValidationError,
    build_research_demand,
    next_theory_work,
)
from ovc.research_operations.p2cti.query import QUERY_FAMILIES, QueryValidationError, ReferenceQueryEngine
from ovc.research_operations.p2cti.relations import (
    RelationValidationError,
    build_duplicate_screen,
    build_relation,
    preserve_relation_ambiguity,
    preserve_relation_conflict,
)


ROOT = Path(__file__).resolve().parents[3]
BUNDLE = json.loads(
    (ROOT / "records/research_operations/p2cti/P2CTII_GENERATION_0_v0_1.json").read_text(encoding="utf-8")
)
FRONTIER = BUNDLE["generation"]["source_frontier_id"]


def _ref(index: int) -> dict[str, str]:
    source = BUNDLE["entries"][index]["source_object_ref"]
    return {
        "owner_programme": source["owner_programme"],
        "object_id": source["object_id"],
        "semantic_generation": source["semantic_generation"],
        "content_sha256": source["content_sha256"],
    }


def _source_ref(index: int = 0) -> dict:
    return deepcopy(BUNDLE["entries"][index]["source_object_ref"])


def _question_ref(index: int = 0) -> dict:
    return {
        "owner_programme": "RESEARCH_OPERATIONS_DMRP_PATH2",
        "object_type": "RESEARCH_PROTOCOL",
        "object_id": f"RQ-P2CTII-WP4-{index:02d}",
        "semantic_generation": "v0.1",
        "source_path": f"owner://research-question/{index}",
        "content_sha256": f"{index + 2:x}" * 64,
        "authority_refs": ["P2CTII-G3-PASS"],
        "scientific_payload_copied": False,
    }


def _rccr_ref(index: int = 0) -> dict:
    return {
        "owner_programme": "RCCR",
        "object_type": "RCCR_ASSESSMENT",
        "object_id": f"RCCR-WP4-{index:02d}",
        "semantic_generation": "v0.1",
        "source_path": f"owner://rccr/assessment/{index}",
        "content_sha256": f"{index + 5:x}" * 64,
        "authority_refs": ["RCCR-GATE"],
        "scientific_payload_copied": False,
    }


def _owner_evidence(reference: dict, predicate: str, state: str = "RESOLVED", object_type: str | None = None) -> dict:
    return {
        "object_type": object_type or reference["object_type"], "predicate": predicate,
        "owner_programme": reference["owner_programme"], "source_ref": reference["source_path"],
        "semantic_generation": reference["semantic_generation"],
        "source_sha256": reference["content_sha256"],
        "authority_refs": reference["authority_refs"], "resolution_state": state,
    }


def _relation_kwargs(relation_type: str, left: dict | None = None, right: dict | None = None) -> dict:
    left, right = left or _ref(0), right or _ref(1)
    owner_ref = {
        "owner_programme": "RESEARCH_OPERATIONS_DMRP_PATH2", "object_type": "THEORY_RECORD",
        "object_id": f"OWNER-REL-{relation_type}", "semantic_generation": "v0.1",
        "source_path": f"owner://relation/{relation_type}", "content_sha256": "a" * 64,
        "authority_refs": ["P2CTII-G3-PASS"], "scientific_payload_copied": False,
    }
    evidence = {
        **owner_ref, "relation_type": relation_type, "left_generation_ref": left,
        "right_generation_ref": right, "source_frontier_id": FRONTIER,
        "resolution_state": "RESOLVED", "evidence_origin": "OWNER_EXPLICIT",
    }
    return {
        "source_relation_ref": owner_ref, "owner_relation_evidence": [evidence],
        "current_generation_bundle": BUNDLE,
    }


def _visibility(*records: dict) -> dict:
    relation_ids = []
    demand_ids = []
    for record in records:
        payload = record.get("payload", {})
        relation_ids.extend(payload[key] for key in ("relation_id", "screen_id", "ambiguity_id", "conflict_id") if key in payload)
        if "demand_id" in payload:
            demand_ids.append(payload["demand_id"])
    return {
        "schema": "ovc-p2cti-query-visibility-context/v0.1", "consumer_class": "WP4_REFERENCE_TEST",
        "visibility_state": "REFERENCE_ONLY", "source_frontier_id": FRONTIER,
        "allowed_query_families": sorted(QUERY_FAMILIES),
        "visible_subject_ids": sorted(entry["subject_id"] for entry in BUNDLE["entries"]),
        "visible_relation_ids": sorted(relation_ids), "visible_demand_ids": sorted(demand_ids),
        "allow_history": True, "allow_aggregate_counts": True,
        "resolution_state": "RESOLVED", "authority_effect": "NONE",
    }


def _exposure_evidence() -> dict:
    return {
        "object_type": "DMRP_EXPOSURE", "predicate": "PATH1_PATH2_EXPOSURE",
        "owner_programme": "DMRP", "source_ref": "dmrp://exposure/wp4",
        "semantic_generation": "v0.1", "source_sha256": "e" * 64,
        "authority_refs": ["DMRP-EXPOSURE-BOUNDARY"], "resolution_state": "RESOLVED",
    }


def _demand(demand_class: str, index: int = 0, status: str = "OPEN") -> dict:
    kwargs = {}
    if demand_class in {"METHOD_GAP", "INFORMATION_GAP", "DATA_GAP", "ARCHITECTURE_NEED_HYPOTHESIS"}:
        rccr = _rccr_ref(index)
        kwargs = {"classification_owner": "RCCR", "rccr_assessment_ref": rccr,
                  "rccr_owner_evidence": [_owner_evidence(rccr, "GAP_CLASS")]}
    source, question = _source_ref(index), _question_ref(index)
    return build_research_demand(
        source_ref=source, research_question_ref=question,
        demand_class=demand_class, source_frontier_id=FRONTIER, status=status, **kwargs,
        source_owner_evidence=[_owner_evidence(source, "THEORY_IDENTITY", object_type="THEORY_RECORD")],
        question_owner_evidence=[_owner_evidence(question, "THEORY_BINDING")],
        research_question_status="CURRENT",
    )


def test_closed_typed_relation_families_bind_exact_semantic_generations() -> None:
    types = {
        "DUPLICATE_OF", "NEAR_DUPLICATE_OF", "SPECIAL_CASE_OF", "GENERALISES",
        "COMPETES_WITH", "DESCENDS_FROM", "CHALLENGES_METHOD_OF", "ROUTES_TO",
        "INDICATES_ARCHITECTURE_NEED", "CROSS_MODE_RELATED", "EVIDENCE_FOR", "SUPERSEDES",
    }
    for relation_type in types:
        qualification = (
            "INDEPENDENT_RULE_REVIEWED"
            if relation_type in {"DUPLICATE_OF", "NEAR_DUPLICATE_OF", "SPECIAL_CASE_OF", "GENERALISES"}
            else "SOURCE_EXPLICIT_DETERMINISTIC"
        )
        record = build_relation(
            relation_type=relation_type, left_generation_ref=_ref(0), right_generation_ref=_ref(1),
            qualification=qualification, source_frontier_id=FRONTIER,
            evidence_refs=["WP4-EXACT-EVIDENCE"], **_relation_kwargs(relation_type),
        )
        assert record["payload"]["left_generation_ref"]["semantic_generation"] == "v0.1"
        assert record["payload"]["right_generation_ref"]["semantic_generation"] == "v0.1"
        assert record["payload"]["identity_collapse_allowed"] is False
        assert record["payload"]["semantic_promotion"] is False
        assert record["authority_effect"] == "NONE"
    with pytest.raises(RelationValidationError):
        build_relation(
            relation_type="TITLE_LOOKS_SIMILAR", left_generation_ref=_ref(0), right_generation_ref=_ref(1),
            qualification="PROPOSED_MACHINE_ASSISTED", source_frontier_id=FRONTIER, evidence_refs=[],
        )


def test_source_explicit_auto_admission_is_narrow_and_sensitive_semantics_are_reviewed() -> None:
    ancestry = build_relation(
        relation_type="DESCENDS_FROM", left_generation_ref=_ref(0), right_generation_ref=_ref(1),
        qualification="SOURCE_EXPLICIT_DETERMINISTIC", source_frontier_id=FRONTIER,
        evidence_refs=["owner-byte#relation"], **_relation_kwargs("DESCENDS_FROM"),
    )
    assert ancestry["payload"]["admission_disposition"] == "ADMITTED_SOURCE_EXPLICIT"
    with pytest.raises(RelationValidationError):
        build_relation(
            relation_type="DESCENDS_FROM", left_generation_ref=_ref(0), right_generation_ref=_ref(1),
            qualification="SOURCE_EXPLICIT_DETERMINISTIC", source_frontier_id=FRONTIER,
            evidence_refs=["owner-byte#relation"],
        )
    duplicate = build_relation(
        relation_type="DUPLICATE_OF", left_generation_ref=_ref(0), right_generation_ref=_ref(1),
        qualification="SOURCE_EXPLICIT_DETERMINISTIC", source_frontier_id=FRONTIER,
        evidence_refs=["owner-byte#relation"], **_relation_kwargs("DUPLICATE_OF"),
    )
    assert duplicate["payload"]["admission_disposition"] == "PROPOSED_REVIEW_REQUIRED"
    reviewed = build_relation(
        relation_type="GENERALISES", left_generation_ref=_ref(0), right_generation_ref=_ref(1),
        qualification="HUMAN_RESEARCH_OPERATIONS_DECISION", source_frontier_id=FRONTIER,
        evidence_refs=["human-decision://1"], **_relation_kwargs("GENERALISES"),
    )
    assert reviewed["payload"]["admission_disposition"] == "ADMITTED_REVIEWED"


def test_machine_similarity_and_near_duplicate_never_collapse_identity() -> None:
    relation = build_relation(
        relation_type="NEAR_DUPLICATE_OF", left_generation_ref=_ref(0), right_generation_ref=_ref(1),
        qualification="PROPOSED_MACHINE_ASSISTED", source_frontier_id=FRONTIER,
        evidence_refs=["retrieval-run://1"],
    )
    screen = build_duplicate_screen(
        subject_refs=[_ref(0), _ref(1)], source_frontier_id=FRONTIER,
        method_class="LLM_RETRIEVAL", machine_signal="ADVISORY_TEXTUAL_NEIGHBOUR",
    )
    assert relation["payload"]["admission_disposition"] == "PROPOSED_REVIEW_REQUIRED"
    assert relation["payload"]["qualification"] == "PROPOSED_MACHINE_ASSISTED"
    assert screen["payload"]["screen_result"] == "NEAR_DUPLICATE_PROPOSED"
    assert screen["payload"]["identity_collapse_allowed"] is False
    assert screen["payload"]["authority_class"] == "ADVISORY_ONLY"


def test_exact_duplicate_screen_does_not_alias_distinct_inventory_entries() -> None:
    screen = build_duplicate_screen(
        subject_refs=[_ref(0), _ref(0)], source_frontier_id=FRONTIER,
        method_class="EXACT_SOURCE_IDENTITY",
    )
    assert screen["payload"]["screen_result"] == "EXACT_SAME_SOURCE_GENERATION"
    assert screen["payload"]["identity_collapse_allowed"] is False


def test_ambiguity_conflict_and_successor_reassessment_are_preserved() -> None:
    first = build_relation(
        relation_type="COMPETES_WITH", left_generation_ref=_ref(0), right_generation_ref=_ref(1),
        qualification="AMBIGUOUS", source_frontier_id=FRONTIER, evidence_refs=["evidence://1"],
    )
    second = build_relation(
        relation_type="SPECIAL_CASE_OF", left_generation_ref=_ref(0), right_generation_ref=_ref(1),
        qualification="INDEPENDENT_RULE_REVIEWED", source_frontier_id=FRONTIER,
        evidence_refs=["review://2"], **_relation_kwargs("SPECIAL_CASE_OF"),
    )
    ambiguity = preserve_relation_ambiguity(
        subject_refs=[_ref(0), _ref(1)],
        competing_relation_refs=[first["payload"]["relation_id"], second["payload"]["relation_id"]],
        source_frontier_id=FRONTIER,
    )
    conflict = preserve_relation_conflict(
        subject_refs=[_ref(0), _ref(1)],
        accepted_relation_refs=[first["payload"]["relation_id"], second["payload"]["relation_id"]],
        source_frontier_id=FRONTIER,
    )
    assert ambiguity["payload"]["review_state"] == "UNRESOLVED"
    assert conflict["payload"]["blocking_effect"] == "RELATION_DECISION_BLOCKED"
    successor = deepcopy(_ref(1))
    successor["semantic_generation"] = "v0.2"
    successor["content_sha256"] = "f" * 64
    reassessed = build_relation(
        relation_type="COMPETES_WITH", left_generation_ref=_ref(0), right_generation_ref=successor,
        qualification="AMBIGUOUS", source_frontier_id=FRONTIER, evidence_refs=["evidence://1"],
    )
    assert reassessed["payload"]["relation_id"] != first["payload"]["relation_id"]
    assert first["payload"]["right_generation_ref"]["semantic_generation"] == "v0.1"


@pytest.mark.parametrize("demand_class", sorted(DEMAND_CLASSES))
def test_research_demand_has_exact_source_and_question_binding(demand_class: str) -> None:
    demand = _demand(demand_class)
    assert demand["payload"]["source_ref"]["object_id"]
    assert demand["payload"]["research_question_ref"]["object_id"]
    assert demand["authority_effect"] == "NONE"
    assert not {"truth_score", "value_score", "alpha_score"}.intersection(demand["payload"])


def test_gap_and_capability_classification_remains_rccr_owned() -> None:
    with pytest.raises(DemandValidationError):
        build_research_demand(
            source_ref=_source_ref(), research_question_ref=_question_ref(),
            demand_class="METHOD_GAP", source_frontier_id=FRONTIER,
            classification_owner="RESEARCH_OPERATIONS_DMRP_PATH2", rccr_assessment_ref=_rccr_ref(),
            source_owner_evidence=[_owner_evidence(_source_ref(), "THEORY_IDENTITY", object_type="THEORY_RECORD")],
            question_owner_evidence=[_owner_evidence(_question_ref(), "THEORY_BINDING")],
            research_question_status="CURRENT",
        )
    malformed = _rccr_ref()
    malformed["owner_programme"] = "P2CTI"
    with pytest.raises(DemandValidationError):
        build_research_demand(
            source_ref=_source_ref(), research_question_ref=_question_ref(),
            demand_class="ARCHITECTURE_NEED_HYPOTHESIS", source_frontier_id=FRONTIER,
            classification_owner="RCCR", rccr_assessment_ref=malformed,
            source_owner_evidence=[_owner_evidence(_source_ref(), "THEORY_IDENTITY", object_type="THEORY_RECORD")],
            question_owner_evidence=[_owner_evidence(_question_ref(), "THEORY_BINDING")],
            research_question_status="CURRENT",
        )


def test_next_theory_work_applies_eligibility_before_preference_and_method_before_architecture() -> None:
    method = _demand("METHOD_GAP", 0)
    architecture = _demand("ARCHITECTURE_NEED_HYPOTHESIS", 1)
    replication = _demand("REPLICATION_NEED", 2)
    ids = [row["payload"]["demand_id"] for row in (method, architecture, replication)]
    result = next_theory_work(
        demand_records=[architecture, replication, method],
        eligibility={
            ids[0]: {"eligible": True, "reason_codes": ["METHOD_AVAILABLE"]},
            ids[1]: {"eligible": True, "reason_codes": ["RCCR_NEED_EVIDENCE_BOUND"]},
            ids[2]: {"eligible": False, "reason_codes": ["OWNER_SOURCE_MISSING"]},
        },
        preference_classes={ids[0]: "DEFERRED_PREFERENCE", ids[1]: "PREFERRED", ids[2]: "PREFERRED"},
        authority_refs=["P2CTII-G3-PASS", "P2CTII-WP4-AUTO"],
    )
    assert [row["demand_class"] for row in result["recommendations"]] == [
        "METHOD_GAP", "ARCHITECTURE_NEED_HYPOTHESIS"
    ]
    assert result["excluded"] == [{"demand_id": ids[2], "reason": "NOT_ELIGIBLE_OR_NOT_OPEN"}]
    assert result["advisory_only"] is True
    assert result["execution_authority"] is False
    assert result["theory_semantic_promotion"] is False


def test_next_theory_work_fails_without_eligibility_or_authority() -> None:
    demand = _demand("REPLICATION_NEED")
    with pytest.raises(DemandValidationError):
        next_theory_work(demand_records=[demand], eligibility={}, authority_refs=["WP4"])
    with pytest.raises(DemandValidationError):
        next_theory_work(
            demand_records=[demand],
            eligibility={demand["payload"]["demand_id"]: {"eligible": True, "reason_codes": ["READY"]}},
            authority_refs=[],
        )


def test_reference_query_engine_implements_every_registered_family_with_full_envelope() -> None:
    relation = build_relation(
        relation_type="CROSS_MODE_RELATED", left_generation_ref=_ref(0), right_generation_ref=_ref(1),
        qualification="PROPOSED_MACHINE_ASSISTED", source_frontier_id=FRONTIER,
        evidence_refs=["retrieval://cross-mode"],
    )
    screen = build_duplicate_screen(
        subject_refs=[_ref(0), _ref(1)], source_frontier_id=FRONTIER,
        method_class="MACHINE_RETRIEVAL", machine_signal="ADVISORY_NEIGHBOUR",
    )
    method = _demand("METHOD_GAP", 0)
    architecture = _demand("ARCHITECTURE_NEED_HYPOTHESIS", 1, status="BLOCKED")
    engine = ReferenceQueryEngine(
        generation_bundle=BUNDLE, relations=[relation], duplicate_screens=[screen],
        demands=[method, architecture], historical_generations=[],
        visibility_context=_visibility(relation, screen, method, architecture),
        exposure_owner_evidence=[_exposure_evidence()],
    )
    subject = _ref(0)["object_id"]
    method_id = method["payload"]["demand_id"]
    calls = {
        "SEARCH": {"text": "TH-", "limit": 2},
        "GET_THEORY": {"subject_id": subject},
        "WHY_HERE": {"subject_id": subject},
        "CURRENT_STATE": {"subject_id": subject},
        "HISTORY": {},
        "RELATIONS": {"subject_id": subject},
        "DUPLICATE_SCREEN": {"subject_id": subject},
        "OPEN_DEMAND": {},
        "WHY_BLOCKED": {"demand_id": architecture["payload"]["demand_id"], "reason_codes": ["RCCR_REVIEW"]},
        "UNBLOCK_PATH": {"demand_id": architecture["payload"]["demand_id"], "required_evidence_refs": ["rccr://review"]},
        "NEXT_THEORY_WORK": {
            "eligibility": {
                method_id: {"eligible": True, "reason_codes": ["METHOD_AVAILABLE"]},
                architecture["payload"]["demand_id"]: {"eligible": False, "reason_codes": ["RCCR_REVIEW"]},
            },
            "authority_refs": ["P2CTII-WP4-AUTO"],
        },
        "ARCHITECTURE_NEED": {},
        "CROSS_MODE": {},
        "PORTFOLIO_STATE": {},
    }
    assert set(calls) == QUERY_FAMILIES
    for family, params in calls.items():
        result = engine.query(family, **params)
        assert result["generation_id"] == BUNDLE["generation"]["generation_id"]
        assert result["source_frontier_id"] == FRONTIER
        assert result["visibility_state"] == "REFERENCE_ONLY"
        if family == "RELATIONS":
            assert result["currentness_state"] == "REASSESSMENT_REQUIRED"
            assert result["completeness_state"] == "UNRESOLVED"
            assert "RELATION_CONSTITUENT_NOT_CURRENT" in result["warnings"]
            assert "RELATION_OWNER_EVIDENCE_UNRESOLVED" in result["warnings"]
        elif family == "CROSS_MODE":
            assert result["currentness_state"] == "REASSESSMENT_REQUIRED"
            assert result["completeness_state"] == "UNRESOLVED"
            assert result["result"] == []
            assert "CROSS_MODE_FORMAL_CORRESPONDENCE_REQUIRED" in result["warnings"]
            assert "CROSS_MODE_RELATION_NOT_CURRENT" in result["warnings"]
        else:
            assert result["currentness_state"] == "CURRENT"
            assert result["completeness_state"] == "COMPLETE"
        assert result["read_only"] is True
        assert result["decision_bearing"] is False
        assert result["semantic_promotion"] is False
        assert result["authority_effect"] == "NONE"
    search = engine.query("SEARCH", text="TH-", limit=2)
    assert search["warnings"] == ["RESULT_SET_TRUNCATED_EXPLICITLY"]
    assert search["result"]["truncation"] == {"returned": 2, "available": 30, "silent": False}
    assert engine.query("PORTFOLIO_STATE")["result"]["composite_score"] is None


def test_query_engine_rejects_unknown_family_and_operational_pointer() -> None:
    engine = ReferenceQueryEngine(generation_bundle=BUNDLE, visibility_context=_visibility())
    with pytest.raises(QueryValidationError):
        engine.query("PROMOTE_THEORY")
    active = deepcopy(BUNDLE)
    active["operational_current_pointer_published"] = True
    with pytest.raises(QueryValidationError):
        ReferenceQueryEngine(generation_bundle=active, visibility_context=_visibility())


def test_relation_evidence_order_is_deterministic() -> None:
    kwargs = {
        "relation_type": "DESCENDS_FROM", "left_generation_ref": _ref(0),
        "right_generation_ref": _ref(1), "qualification": "SOURCE_EXPLICIT_DETERMINISTIC",
        "source_frontier_id": FRONTIER, **_relation_kwargs("DESCENDS_FROM"),
    }
    first = build_relation(**kwargs, evidence_refs=["evidence://b", "evidence://a"])
    second = build_relation(**kwargs, evidence_refs=["evidence://a", "evidence://b"])
    assert first == second


def test_wp4_reference_fixture_reproduces_in_two_clean_processes() -> None:
    command = [sys.executable, str(ROOT / "scripts/research_operations/run_p2ctii_wp4_reference.py")]
    env = {**os.environ, "PYTHONHASHSEED": "random"}
    first = subprocess.run(command, cwd=ROOT, env=env, check=True, capture_output=True).stdout
    second = subprocess.run(command, cwd=ROOT, env=env, check=True, capture_output=True).stdout
    assert first == second
    assert first.decode().strip() == "c9c96fc80def2eebc06bfb910e517138b45b9b5168cdcff5863a25b54dae95d9"


def test_g4_alg_packet_is_exact_unbound_and_blocks_wp5() -> None:
    packet = json.loads(
        (ROOT / "docs/programmes/p2cti-v0-1/wp4/P2CTII_G4_ALG_CONSOLIDATED_REVIEW_PACKET_v0_1.json")
        .read_text(encoding="utf-8")
    )
    assert packet["status"] == "READY_FOR_CONFLICT_FREE_INDEPENDENT_REVIEW"
    assert packet["decision"] == "UNRESOLVED"
    assert packet["authority_delta"] == "NONE"
    assert packet["reviewer_binding"] == {
        "reviewer_identity": None,
        "independence_declaration": None,
        "conflict_free_from_wp4_implementation": None,
        "status": "UNBOUND",
    }
    assert packet["wp5_authorised"] is False
    assert packet["exact_next_route"] == (
        "MATERIALISE_WP4_THEN_COMMISSION_CONFLICT_FREE_INDEPENDENT_P2CTII-G4-ALG_REVIEW"
    )
    decision_materialisation_artifacts = {
        "records/research_operations/p2cti/P2CTII_PROGRAMME_STATE_v0_1.json",
        "tests/research_operations/p2cti/test_p2ctii_wp2_owner_currentness.py",
        "tests/research_operations/p2cti/test_p2ctii_wp4_relations_demand_query.py",
        "src/ovc/research_operations/p2cti/relations.py",
        "src/ovc/research_operations/p2cti/demand.py",
        "src/ovc/research_operations/p2cti/query.py",
        "scripts/research_operations/run_p2ctii_wp4_reference.py",
        "fixtures/research_operations/p2cti/P2CTII_WP4_REFERENCE_FIXTURE_v0_1.json",
    }
    for path, expected in packet["exact_artifact_hashes"].items():
        if path not in decision_materialisation_artifacts:
            assert hashlib.sha256((ROOT / path).read_bytes()).hexdigest() == expected


def test_fresh_g4_alg_block_remains_byte_exact_during_bounded_remediation() -> None:
    review_path = (
        ROOT
        / "docs/programmes/p2cti-v0-1/wp4/"
        "P2CTII_G4_ALG_FRESH_INDEPENDENT_REVIEW_PACKET_v0_1.json"
    )
    review = json.loads(review_path.read_text(encoding="utf-8"))
    post_remediation_review_path = (
        ROOT
        / "docs/programmes/p2cti-v0-1/wp4/"
        "P2CTII_G4_ALG_FRESH_INDEPENDENT_REVIEW_AFTER_REMEDIATION_1_PACKET_v0_1.json"
    )
    post_remediation_review = json.loads(
        post_remediation_review_path.read_text(encoding="utf-8")
    )
    state = json.loads(
        (ROOT / "records/research_operations/p2cti/P2CTII_PROGRAMME_STATE_v0_1.json")
        .read_text(encoding="utf-8")
    )
    assert hashlib.sha256(review_path.read_bytes()).hexdigest() == (
        "a8b31cd18c2d65168d0c5b49a89e45d9ac14845a156d9675725e63a1aa89efb3"
    )
    assert review["decision"] == "BLOCK"
    assert review["authority_delta"] == "NONE"
    assert hashlib.sha256(post_remediation_review_path.read_bytes()).hexdigest() == (
        "3f5db3fcac072addac14f8f073ab1ea13d500bcd12884d6a1d26f23740fae7c1"
    )
    assert post_remediation_review["decision"] == "BLOCK"
    assert post_remediation_review["authority_delta"] == "NONE"
    if state.get("p2ctii_g4_alg_status") == "PASS":
        assert state["wp5_authorised"] is True
        assert state["blockers"] == []
        assert state["packet_id"] in {
            "P2CTII-G4-ALG",
            "P2CTII-WP5",
            "P2CTII-WP6",
            "P2CTII-WP7",
            "P2CTII-WP8",
            "P2CTII-WP9",
            "P2CTII-G-OBSERVABILITY-ACTIVATE",
        }
        if state["packet_id"] == "P2CTII-G4-ALG":
            assert state["status"] == "APPROVED"
            assert state["next_packet"] == "P2CTII-WP5"
        else:
            assert state["status"] in {"APPROVED", "COMPLETED", "GATE_READY"}
            assert state["next_packet"] in {
                "P2CTII-WP6",
                "P2CTII-WP7",
                "P2CTII-WP8",
                "P2CTII-WP9",
                "P2CTII-G-OBSERVABILITY-ACTIVATE",
            }
    else:
        assert state["status"] == "PASS_REMEDIATION_AWAITING_MATERIALISATION"
        assert state["p2ctii_g4_alg_status"] == "UNRESOLVED_PRIOR_BLOCKS_PRESERVED"
        assert state["next_packet"] == (
            "P2CTII-G4-ALG-FRESH-INDEPENDENT-REVIEW-AFTER-WP4-REMEDIATION-2"
        )
        assert state["wp5_authorised"] is False
    assert state["g4_alg_remediation_author_may_grant_pass"] is False
    assert state["authority_delta"] == "NONE"
