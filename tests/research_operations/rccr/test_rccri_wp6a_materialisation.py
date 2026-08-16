from __future__ import annotations

import json
from pathlib import Path

from ovc.research_operations.rccr.core import validate_canonical_object
from ovc.research_operations.rccr.pilot import ADVERSARIAL_CASES, GOLDEN_CASES, GOLDEN_EXPECTED

ROOT = Path(__file__).resolve().parents[3]
BOOTSTRAP = "records/research_operations/rccr/v0_1/RCCRBootstrapManifest/rccr__RCCRBootstrapManifest__f64578daa0a45984c7b5677831a5e2a09a452fa4ac1664f9d71fe10d930acbf0.json"


def load(path: str):
    return json.loads((ROOT / path).read_text(encoding="utf-8"))


def test_wp6a_canonical_bootstrap_manifest_is_valid_and_bounded():
    bootstrap = load(BOOTSTRAP)
    validate_canonical_object("RCCRBootstrapManifest", bootstrap)
    assert len(bootstrap["included_item_refs"]) == 10
    assert bootstrap["excluded_item_refs"] == ["REAL_SOURCE_EC1_E1_R1_OUTPUTS", "VALIDATION_PROTECTED_CONTENT"]
    assert bootstrap["authority_effect"] == "NONE"


def test_wp6a_exact_assurance_registry_matches_ratified_population():
    registry = load("fixtures/research_operations/rccr/v0_1/RCCRI_WP6A_ASSURANCE_CASE_REGISTRY.json")
    av = tuple(row["case_id"] for row in registry["adversarial"])
    golden = tuple(row["case_id"] for row in registry["golden"])
    assert av == ADVERSARIAL_CASES
    assert golden == GOLDEN_CASES
    assert {row["case_id"]: row["expected"] for row in registry["golden"]} == GOLDEN_EXPECTED
    assert registry["population_policy"]["silent_sampling_forbidden"] is True


def test_wp6a_historical_pack_does_not_manufacture_missing_information_pressure():
    pack = load("docs/releases/rccr-v0-1/rccri-wp6a/HistoricalCounterfactualValidationPack.json")
    by_id = {row["case_id"]: row for row in pack["cases"]}
    assert by_id["HIST-INFO-01"]["status"] == "NOT_AVAILABLE"
    assert by_id["HIST-INFO-01"]["source_time_complete"] is False
    assert pack["information_gap_discipline"]["unsupported_information_gap_promotions"] == 0
    assert pack["source_time_policy"]["hindsight_forbidden"] is True


def test_wp6a_fixture_currentness_is_current_and_requires_pre_exit_recheck():
    manifest = load("docs/releases/rccr-v0-1/rccri-wp6a/RCCRI_FIXTURE_CURRENTNESS_MANIFEST.json")
    assert manifest["population"]["total"] == 36
    assert manifest["currentness"] == "PASS"
    assert manifest["stale_fixture_count"] == 0
    assert manifest["stale_fixture_rewrite_forbidden"] is True
    assert manifest["pre_pilot_exit_recheck_required"] is True


def test_wp6a_review_workaround_and_resource_evidence_are_non_authoritative():
    review = load("docs/releases/rccr-v0-1/rccri-wp6a/PilotReviewLoadLedger.json")
    workaround = load("docs/releases/rccr-v0-1/rccri-wp6a/OffRegisterWorkaroundPressureEvidence.json")
    actuals = load("docs/releases/rccr-v0-1/rccri-wp6a/FixtureAuthorshipResourceActuals.json")
    assert review["admitted_assessment_denominator"] == 10
    assert review["threshold_use"] == "OPERATIONAL_PILOT_TRIGGER_ONLY_NOT_SCIENTIFIC"
    assert workaround["pilot_route_attempt_denominator"] == 10
    assert workaround["decision_bearing_external_rationale_count"] == 0
    assert actuals["human_person_day_actuals"] is None
    assert actuals["no_invented_effort"] is True
    assert review["authority_effect"] == workaround["authority_effect"] == actuals["authority_effect"] == "NONE"


def test_wp6a_programme_state_denies_scaleout_and_routes_to_lawful_next_operator_gate():
    state = load("registries/implementation/rccr_v0_1/RCCR_V0_1_STATE_v0_7.json")
    pointer = load("registries/implementation/rccr_v0_1/CURRENT_STATE_POINTER.json")
    reviewers = load("docs/releases/rccr-v0-1/rccri-wp0/RCCRI_REVIEWER_BINDINGS.json")
    adversarial = {item["gate"]: item for item in reviewers["bindings"]}["RCCRI-G-ADVERSARIAL-REVIEW"]
    assert state["scaleout_authority"] == "DENIED"
    assert state["real_source_ec1_authority"] == "NONE"
    assert state["validation"] == "LOCKED_UNCONSUMED"
    assert state["next_operator_gate"] == "RCCRI-G-ADVERSARIAL-REVIEW"
    if adversarial["decision"] == "PENDING":
        assert pointer["next_operator_gate"] == "RCCRI-G-ADVERSARIAL-REVIEW"
        assert pointer["scaleout_authority"] == "DENIED"
    else:
        assert adversarial["decision"] == "PASS"
        decision = load(adversarial["decision_ref"])
        assert decision["decision_instruction"] == "OVC APPROVE RCCRI-G-ADVERSARIAL-REVIEW"
        if pointer["scaleout_authority"] == "DENIED":
            assert pointer["next_operator_gate"] == "RCCRI-G-PILOT-EXIT"
        else:
            assert pointer["scaleout_authority"] == "AUTHORIZED_BOUNDED_WP6B_WP7B_WP8"
            assert pointer["next_operator_gate"] is None
            assert pointer["operator_pending"] == []
            pilot_exit = load("docs/releases/rccr-v0-1/rccri-g-pilot-exit/RCCRI_G_PILOT_EXIT_OPERATOR_DECISION.json")
            assert pilot_exit["decision"] == "PASS"
            assert pilot_exit["decision_instruction"] == "OVC APPROVE RCCRI-G-PILOT-EXIT"
    assert pointer["real_source_ec1_authority"] == "NONE"
    assert pointer["validation"] == "LOCKED_UNCONSUMED"
