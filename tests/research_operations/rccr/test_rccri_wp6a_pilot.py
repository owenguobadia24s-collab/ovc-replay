from __future__ import annotations

import json
from copy import deepcopy
from pathlib import Path

import pytest

from ovc.research_operations.rccr.assurance import evaluate_adversarial_safeguard
from ovc.research_operations.rccr.need_review import CapabilityNeedEvaluator
from ovc.research_operations.rccr.pilot import (
    ADVERSARIAL_CASES,
    EC1_PILOT_QUESTIONS,
    GOLDEN_CASES,
    GOLDEN_EXPECTED,
    PilotAssuranceRunner,
    RCCRPilotError,
    bind_ec1_pilot_questions,
    fixture_authorship_actuals,
    pilot_review_load_summary,
    validate_fixture_currentness,
    validate_historical_counterfactual,
)
from ovc.research_operations.rccr.reference import RCCRReferenceEngine

ROOT = Path(__file__).resolve().parents[3]
QUESTION_PATH = "registries/research_operations/EC1_RESEARCH_QUESTION_REGISTRY_v0_1.json"
EVIDENCE_PATH = "registries/research_operations/ec1/ec1_question_evidence_requirements_v0_1.json"
Q_BLOB = "3f8c8125e8d5513e719613fc17e8033836154396"
E_BLOB = "c97e70f0ea3801c7373f941c11a746d3c52c5bcc"
SOURCE_COMMIT = "2e5dac15a990af99c39df37a1a5cafc7b05ea36a"
SOURCE_FIRST_VALID_TIME = "2026-08-15T13:26:52Z"
FRONTIER = "rccr:ResearchCapabilityFrontier:wp6a-pilot-current-owner-state"


def load(path: str):
    return json.loads((ROOT / path).read_text(encoding="utf-8"))


def build_bundle(question_registry=None, evidence_registry=None):
    return bind_ec1_pilot_questions(
        question_registry=question_registry or load(QUESTION_PATH),
        evidence_registry=evidence_registry or load(EVIDENCE_PATH),
        question_registry_ref=f"{QUESTION_PATH}@{SOURCE_COMMIT}",
        question_registry_blob_sha=Q_BLOB,
        evidence_registry_ref=f"{EVIDENCE_PATH}@{SOURCE_COMMIT}",
        evidence_registry_blob_sha=E_BLOB,
        source_first_valid_time=SOURCE_FIRST_VALID_TIME,
        capability_frontier_id=FRONTIER,
        qa_receipt="RCCRI-WP6A-QA",
    )


def _golden_receipts():
    profile = {
        "requirement_profile_id": "rccr:ResearchRequirementProfile:wp6a-golden",
        "epistemic_requirements": ["R1"],
        "evidence_requirements": [],
        "population_requirements": [],
        "chronology_requirements": [],
        "inferential_requirements": [],
        "denominator_requirements": [],
        "comparability_requirements": [],
    }
    frontier = {"capability_frontier_id": FRONTIER}
    scenarios = {
        "G01": ("SATISFIED", [], "VALID"),
        "G02": ("UNSATISFIED", ["METHOD_GAP"], "VALID"),
        "G03": ("UNSATISFIED", ["DENOMINATOR_GAP"], "VALID"),
        "G04": ("UNSATISFIED", ["DATA_GAP"], "VALID"),
        "G05": ("UNSATISFIED", ["OWNER_SEMANTICS_GAP"], "VALID"),
        "G06": ("UNSATISFIED", ["IMPLEMENTATION_GAP"], "VALID"),
        "G07": ("UNSATISFIED", ["AUTHORITY_GAP"], "VALID"),
        "G08": ("SATISFIED", [], "EXCLUDED"),
        "G09": ("UNSATISFIED", ["INFORMATION_GAP", "COUNTERFACTUAL_EXHAUSTED"], "VALID"),
        "G10": ("NOT_EVALUABLE", ["METHOD_INFORMATION_ENTANGLED"], "VALID"),
    }
    receipts = []
    for case_id, (result, flags, protocol_state) in scenarios.items():
        assessment = RCCRReferenceEngine().assess(
            coverage_item_generation_id=f"coverage:{case_id}:wp6a",
            requirement_profile=profile,
            capability_frontier=frontier,
            requirement_evidence={"R1": {"result": result, "flags": flags, "evidence_refs": [case_id]}},
            evaluation_cutoff="2026-08-15T23:45:00+01:00",
            protocol_state=protocol_state,
            first_valid_time="2026-08-15T23:45:00+01:00",
        )
        gap = assessment["requirement_results"][0]["gap_class"]
        if case_id == "G01":
            actual = "CURRENT_STACK_SUFFICIENT"
        elif case_id == "G09":
            actual = "GENUINE_INFORMATION_GAP" if gap == "INFORMATION_GAP" else gap
        else:
            actual = gap
        receipts.append({"case_id": case_id, "actual": actual, "authority_effect": "NONE"})

    info_assessment = RCCRReferenceEngine().assess(
        coverage_item_generation_id="coverage:G11G12:wp6a",
        requirement_profile=profile,
        capability_frontier=frontier,
        requirement_evidence={"R1": {"result": "UNSATISFIED", "flags": ["INFORMATION_GAP", "COUNTERFACTUAL_EXHAUSTED"], "evidence_refs": ["G11"]}},
        evaluation_cutoff="2026-08-15T23:45:00+01:00",
        first_valid_time="2026-08-15T23:45:00+01:00",
    )
    common = dict(
        coverage_assessment=info_assessment,
        candidate_capability={"capability_id": "C2P", "owner": "OVC-C2P", "owner_contract_ref": "contract:c2p:v0.2"},
        missing_information_claim="persistent identity remains absent after smaller routes",
        ownership_test={"owner_fit": "MATCH", "semantic_ownership_evidence": ["owner:c2p"]},
        minimality_test={"smaller_route_status": "EXHAUSTED", "shadow_closure_evidence": []},
        alternative_routes=["correspondence"],
        supporting_condition="identity remains necessary",
        falsifying_condition="existing information closes gap",
        shadow_test_route="C2P_SHADOW_ONLY",
        next_owner_route="C2P_OWNER_REVIEW",
        first_valid_time="2026-08-15T23:45:00+01:00",
    )
    supported = CapabilityNeedEvaluator().evaluate(**common)
    contradicted = CapabilityNeedEvaluator().evaluate(**common, current_counterevidence=["existing-route-closes-gap"])
    receipts.extend([
        {"case_id": "G11", "actual": supported["need_status"], "authority_effect": "NONE"},
        {"case_id": "G12", "actual": contradicted["need_status"], "authority_effect": "NONE"},
    ])
    return receipts


def test_wp6a_exact_q01_q10_bootstrap_is_source_bound_and_pre_evidentiary():
    bundle = build_bundle()
    records = bundle["question_records"]
    assert tuple(row["question_id"] for row in records) == EC1_PILOT_QUESTIONS
    assert len(records) == 10
    assert bundle["bootstrap_manifest"]["authority_effect"] == "NONE"
    assert bundle["source_resolution_manifest"]["real_source_ec1_evidence_consumed"] is False
    assert bundle["source_resolution_manifest"]["protected_payloads_opened"] is False
    assert all(row["assessment_record"]["ec1_scientific_answer"] == "NOT_PRODUCED" for row in records)
    assert all(row["assessment_record"]["unsupported_information_gap_promoted"] is False for row in records)
    assert all(row["frontier_record"]["real_source_ec1_authority"] == "NONE" for row in records)


def test_wp6a_question_registry_and_evidence_registry_must_crosswalk_exactly():
    evidence = load(EVIDENCE_PATH)
    evidence["questions"][0]["canonical_question"] += " changed"
    with pytest.raises(RCCRPilotError, match="canonical question mismatch"):
        build_bundle(evidence_registry=evidence)


def test_wp6a_clean_restart_and_input_order_are_logically_identical():
    first = build_bundle()
    q = load(QUESTION_PATH)
    e = load(EVIDENCE_PATH)
    q["questions"] = list(reversed(q["questions"]))
    e["questions"] = list(reversed(e["questions"]))
    second = build_bundle(q, e)
    assert first == second


def test_wp6a_all_av01_av24_execute_and_pass_without_authority_effect():
    receipts = [evaluate_adversarial_safeguard(case_id) for case_id in ADVERSARIAL_CASES]
    assert len(receipts) == 24
    assert all(row["pass"] for row in receipts)
    assert all(row["authority_effect"] == "NONE" for row in receipts)


def test_wp6a_all_g01_g12_match_ratified_logical_classes():
    receipts = _golden_receipts()
    assert tuple(sorted(row["case_id"] for row in receipts)) == GOLDEN_CASES
    assert {row["case_id"]: row["actual"] for row in receipts} == GOLDEN_EXPECTED


def test_wp6a_full_assurance_runner_forbids_silent_sampling_and_unsupported_information_gap():
    receipts = [evaluate_adversarial_safeguard(case_id) for case_id in ADVERSARIAL_CASES] + _golden_receipts()
    result = PilotAssuranceRunner().evaluate(receipts)
    assert result["status"] == "PASS"
    assert result["adversarial_denominator"] == 24
    assert result["golden_denominator"] == 12
    assert result["executed_count"] == 36
    assert result["unsupported_information_gap_promotions"] == 0
    assert result["silent_sampling"] is False
    with pytest.raises(RCCRPilotError, match="full assurance population required"):
        PilotAssuranceRunner().evaluate(receipts[:-1])


def test_wp6a_fixture_currentness_passes_exact_dependencies_and_stale_requires_successor():
    current = {"RCCR_RULE_PACK": "r1", "DMRP_INTERFACE": "d1", "EC1_INTERFACE": "e1", "OWNER_STATE_MODEL": "o1"}
    fixtures = [
        {"fixture_id": case_id, "dependency_digests": current}
        for case_id in (*ADVERSARIAL_CASES, *GOLDEN_CASES)
    ]
    manifest = validate_fixture_currentness(fixtures=fixtures, current_dependencies=current, checked_at="2026-08-15T23:45:00+01:00")
    assert manifest["status"] == "PASS"
    assert len(manifest["fixtures"]) == 36
    stale_current = {**current, "RCCR_RULE_PACK": "r2"}
    stale = validate_fixture_currentness(fixtures=fixtures, current_dependencies=stale_current, checked_at="2026-08-15T23:46:00+01:00")
    assert stale["status"] == "BLOCK"
    assert all(row["action"] == "SUCCESSOR_GENERATION_REQUIRED" for row in stale["fixtures"])


def test_wp6a_historical_counterfactual_is_source_time_bounded_and_hindsight_denied():
    case = validate_historical_counterfactual(
        case_id="HIST-AUTHORITY-C2P",
        decision_cutoff="2026-08-15T19:34:00Z",
        artifact_refs=[{"ref": "RCCRI-WP0-owner-census@1f9fddcc", "available_at": "2026-08-15T19:33:53Z"}],
        expected_limiting_class="AUTHORITY_GAP",
        source_time_complete=True,
    )
    assert case["status"] == "SOURCE_TIME_BOUND"
    assert case["hindsight_excluded"] is True
    hindsight = validate_historical_counterfactual(
        case_id="HIST-INVALID-HINDSIGHT",
        decision_cutoff="2026-08-15T19:34:00Z",
        artifact_refs=[{"ref": "future", "available_at": "2026-08-15T20:00:00Z"}],
        expected_limiting_class="METHOD_GAP",
        source_time_complete=False,
        hindsight_refs=["future-result"],
    )
    assert hindsight["status"] == "NOT_AVAILABLE"
    assert "HINDSIGHT_INPUT_PRESENT" in hindsight["unavailable_reasons"]
    assert any(item.startswith("POST_CUTOFF_ARTIFACT") for item in hindsight["unavailable_reasons"])


def test_wp6a_review_load_30_percent_is_operational_trigger_only():
    rows = [
        {"review_latency_seconds": 60, "conflict": False, "reopened": False, "operator_escalation": False},
        {"review_latency_seconds": 120, "conflict": True, "reopened": True, "operator_escalation": True},
        {"review_latency_seconds": 180, "conflict": False, "reopened": False, "operator_escalation": False},
        {"review_latency_seconds": 240, "conflict": False, "reopened": False, "operator_escalation": False},
    ]
    summary = pilot_review_load_summary(admitted_assessment_count=10, human_review_rows=rows)
    assert summary["human_review_required_share"] == 0.4
    assert summary["review_trigger_over_30_percent"] is True
    assert summary["default_scaleout_recommendation"] == "DEFER"
    assert summary["threshold_use"] == "OPERATIONAL_PILOT_TRIGGER_ONLY_NOT_SCIENTIFIC"
    assert summary["admitted_assessment_denominator"] == 10


def test_wp6a_fixture_authorship_actuals_never_invent_human_person_days():
    actuals = fixture_authorship_actuals(
        planning_estimate_ref="docs/releases/rccr-v0-1/rccri-wp0/RCCRI_FIXTURE_AUTHORSHIP_RESOURCE_ESTIMATE.json",
        automated_execution_receipts=["CI:WP4", "CI:WP5", "CI:WP6A"],
    )
    assert actuals["human_person_day_actuals"] is None
    assert actuals["human_actuals_status"] == "UNAVAILABLE_NOT_INSTRUMENTED"
    assert actuals["independent_reviewer_effort_status"] == "PENDING_OPERATOR_REVIEW"
    assert actuals["estimate_is_not_schedule_slo"] is True
