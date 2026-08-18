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


def _source_ref(index: int = 0) -> dict[str, str]:
    source = BUNDLE["entries"][index]["source_object_ref"]
    return {
        "owner_programme": source["owner_programme"],
        "object_type": source["object_type"],
        "object_id": source["object_id"],
        "semantic_generation": source["semantic_generation"],
        "content_sha256": source["content_sha256"],
    }


def _question_ref(index: int = 0) -> dict[str, str]:
    return {
        "owner_programme": "RESEARCH_OPERATIONS_DMRP_PATH2",
        "question_id": f"RQ-P2CTII-WP4-{index:02d}",
        "semantic_generation": "v0.1",
        "content_sha256": f"{index + 2:x}" * 64,
    }


def _rccr_ref(index: int = 0) -> dict[str, str]:
    return {
        "owner_programme": "RCCR",
        "object_type": "RCCR_ASSESSMENT",
        "object_id": f"RCCR-WP4-{index:02d}",
        "semantic_generation": "v0.1",
        "content_sha256": f"{index + 5:x}" * 64,
    }


def _demand(demand_class: str, index: int = 0, status: str = "OPEN") -> dict:
    kwargs = {}
    if demand_class in {"METHOD_GAP", "INFORMATION_GAP", "DATA_GAP", "ARCHITECTURE_NEED_HYPOTHESIS"}:
        kwargs = {"classification_owner": "RCCR", "rccr_assessment_ref": _rccr_ref(index)}
    return build_research_demand(
        source_ref=_source_ref(index), research_question_ref=_question_ref(index),
        demand_class=demand_class, source_frontier_id=FRONTIER, status=status, **kwargs,
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
            evidence_refs=["WP4-EXACT-EVIDENCE"], source_relation_ref="owner://relation/1",
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
        evidence_refs=["owner-byte#relation"], source_relation_ref="owner://relation/ancestry",
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
        evidence_refs=["owner-byte#relation"], source_relation_ref="owner://relation/duplicate",
    )
    assert duplicate["payload"]["admission_disposition"] == "PROPOSED_REVIEW_REQUIRED"
    reviewed = build_relation(
        relation_type="GENERALISES", left_generation_ref=_ref(0), right_generation_ref=_ref(1),
        qualification="HUMAN_RESEARCH_OPERATIONS_DECISION", source_frontier_id=FRONTIER,
        evidence_refs=["human-decision://1"],
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
        evidence_refs=["review://2"],
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
    assert demand["payload"]["research_question_ref"]["question_id"]
    assert demand["authority_effect"] == "NONE"
    assert not {"truth_score", "value_score", "alpha_score"}.intersection(demand["payload"])


def test_gap_and_capability_classification_remains_rccr_owned() -> None:
    with pytest.raises(DemandValidationError):
        build_research_demand(
            source_ref=_source_ref(), research_question_ref=_question_ref(),
            demand_class="METHOD_GAP", source_frontier_id=FRONTIER,
            classification_owner="RESEARCH_OPERATIONS_DMRP_PATH2", rccr_assessment_ref=_rccr_ref(),
        )
    malformed = _rccr_ref()
    malformed["owner_programme"] = "P2CTI"
    with pytest.raises(DemandValidationError):
        build_research_demand(
            source_ref=_source_ref(), research_question_ref=_question_ref(),
            demand_class="ARCHITECTURE_NEED_HYPOTHESIS", source_frontier_id=FRONTIER,
            classification_owner="RCCR", rccr_assessment_ref=malformed,
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
        assert result["currentness_state"] == "CURRENT"
        assert result["visibility_state"] == "REFERENCE_ONLY"
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
    engine = ReferenceQueryEngine(generation_bundle=BUNDLE)
    with pytest.raises(QueryValidationError):
        engine.query("PROMOTE_THEORY")
    active = deepcopy(BUNDLE)
    active["operational_current_pointer_published"] = True
    with pytest.raises(QueryValidationError):
        ReferenceQueryEngine(generation_bundle=active)


def test_relation_evidence_order_is_deterministic() -> None:
    kwargs = {
        "relation_type": "DESCENDS_FROM", "left_generation_ref": _ref(0),
        "right_generation_ref": _ref(1), "qualification": "SOURCE_EXPLICIT_DETERMINISTIC",
        "source_frontier_id": FRONTIER, "source_relation_ref": "owner://relation/order",
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
    assert first.decode().strip() == "b07072a42e07f73a02a466d4f1a89a7828609ef86fb03a359e50c0d2a38b7abf"


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
    }
    for path, expected in packet["exact_artifact_hashes"].items():
        if path not in decision_materialisation_artifacts:
            assert hashlib.sha256((ROOT / path).read_bytes()).hexdigest() == expected


def test_fresh_g4_alg_block_is_materialised_byte_exact_and_routes_only_to_remediation() -> None:
    review_path = (
        ROOT
        / "docs/programmes/p2cti-v0-1/wp4/"
        "P2CTII_G4_ALG_FRESH_INDEPENDENT_REVIEW_PACKET_v0_1.json"
    )
    review = json.loads(review_path.read_text(encoding="utf-8"))
    state = json.loads(
        (ROOT / "records/research_operations/p2cti/P2CTII_PROGRAMME_STATE_v0_1.json")
        .read_text(encoding="utf-8")
    )
    assert hashlib.sha256(review_path.read_bytes()).hexdigest() == (
        "a8b31cd18c2d65168d0c5b49a89e45d9ac14845a156d9675725e63a1aa89efb3"
    )
    assert review["decision"] == "BLOCK"
    assert review["authority_delta"] == "NONE"
    assert state["status"] == "BLOCKED_AWAITING_P2CTII-WP4-REMEDIATION-1"
    assert state["p2ctii_g4_alg_status"] == "BLOCK"
    assert state["next_packet"] == "P2CTII-WP4-REMEDIATION-1"
    assert state["wp5_authorised"] is False
    assert state["g4_alg_remediation_author_may_grant_pass"] is False
    assert state["authority_delta"] == "NONE"
