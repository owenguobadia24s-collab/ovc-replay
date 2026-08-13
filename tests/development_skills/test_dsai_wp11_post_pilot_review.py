from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
REVIEW = ROOT / "docs/releases/development-skills-architecture-v0-1/dsai-wp11/DSAI_WP11_POST_PILOT_REVIEW.json"
INCIDENTS = ROOT / "docs/releases/development-skills-architecture-v0-1/dsai-wp11/DSAI_WP11_INCIDENT_AND_CONTAINMENT_SWEEP.json"
ORCH3 = ROOT / "docs/releases/development-skills-architecture-v0-1/dsai-wp11/DSAI_WP11_ORCH3_READINESS_ASSESSMENT.json"
ORCH4 = ROOT / "docs/releases/development-skills-architecture-v0-1/dsai-wp11/DSAI_WP11_ORCH4_CONFLICT_DETECTOR_GAPS.json"
PARALLEL = ROOT / "docs/releases/development-skills-architecture-v0-1/dsai-wp11/DSAI_WP11_PARALLELISM_READINESS_ASSESSMENT.json"
TRUST = ROOT / "registries/development/skills/trusted_promotions_v0_1.json"
STATE = ROOT / "registries/implementation/dsai/OVC_DSAI_STATE_v0_29.json"


def _load(path: Path):
    return json.loads(path.read_text(encoding="utf-8"))


def test_review_metrics_have_explicit_denominators_and_no_causal_claim():
    review = _load(REVIEW)
    assert review["packet_class"] == "LOW_RISK_IMPLEMENTATION"
    assert review["authority_delta"] == "NONE"
    velocity = review["qualification_velocity"]
    assert velocity["trusted_tuple_count"] == 10
    assert velocity["promotion_event_count"] == 3
    assert velocity["first_to_last_seconds"] == 22709
    assert velocity["time_normalized_tuple_promotions_per_hour"] == 1.585
    comparison = review["mode_comparison"]
    assert comparison["denominator"]["orch1_completed_low_risk_packets"] == 1
    assert comparison["denominator"]["orch2_completed_low_risk_packets"] == 1
    assert comparison["orch1"]["pr_cycle_seconds"] == 755
    assert comparison["orch2"]["pr_cycle_seconds"] == 643
    assert comparison["observed_delta"]["pr_cycle_seconds"] == -112
    assert comparison["orch1"]["tests_job_seconds"] == 148
    assert comparison["orch2"]["tests_job_seconds"] == 145
    assert "No causal speed claim" in comparison["caution"]
    assert review["checkpoint_cache"]["benefit_denominator"] == 0
    assert review["checkpoint_cache"]["benefit_assessment"] == "NOT_MEASURED"


def test_environment_and_trusted_registry_are_exact_and_current_by_repository_registry():
    review = _load(REVIEW)
    trust = _load(TRUST)
    env = review["environment_reproducibility"]
    assert trust["effective"] is True
    assert trust["entry_count"] == 10
    assert env["trusted_tuples_on_exact_environment"] == 10
    assert env["trusted_tuple_denominator"] == 10
    assert env["exact_environment_uniformity"] == "10_OF_10"
    assert {row["environment_id"] for row in trust["entries"]} == {"windows-local-python311"}
    assert {row["environment_hash"] for row in trust["entries"]} == {env["environment_hash"]}
    assert all(row["maturity"] == "TRUSTED" and row["selection_eligible"] is True for row in trust["entries"])


def test_incident_sweep_has_no_recorded_unresolved_s3_s4_and_churn_failed_closed():
    sweep = _load(INCIDENTS)
    assert sweep["recorded_unresolved_s3"] == 0
    assert sweep["recorded_unresolved_s4"] == 0
    assert sweep["s3_s4_acceptance"] == "PASS_NO_RECORDED_UNRESOLVED_S3_S4"
    churn = next(row for row in sweep["containment_events"] if row["class"] == "MAIN_HEAD_CHURN")
    assert churn["count"] == 3
    assert churn["false_allows"] == 0
    assert churn["containment"] == "PASS_3_OF_3_FAILED_CLOSED_BEFORE_MERGE_READINESS"
    assert sweep["blocking_warnings"] == []


def test_orch3_orch4_and_parallelism_remain_deferred_without_authority_change():
    orch3 = _load(ORCH3)
    orch4 = _load(ORCH4)
    parallel = _load(PARALLEL)
    assert orch3["decision"] == "DEFER_ORCH3_NOT_READY"
    assert orch3["parallelism_policy"] == "KEEP_SERIAL_REQUIRED"
    assert orch3["proposed_authority_delta"] == "NONE"
    assert orch4["readiness"] == "NOT_READY_FOR_ORCH4_ACTIVATION"
    assert orch4["authority_delta"] == "NONE"
    assert parallel["decision"] == "NOT_READY_KEEP_SERIAL_REQUIRED"
    assert parallel["authority_delta"] == "NONE"
    assert parallel["observed_denominators"]["completed_parallel_orch2_packets"] == 0
    assert parallel["observed_denominators"]["active_orch4_conflict_detector"] == 0


def test_wp10_completed_state_is_wp11_prerequisite_and_reserved_layers_inactive():
    state = _load(STATE)
    assert state["programme_status"] == "WP10_COMPLETED_G10_PASS"
    assert state["next_packet"] == "DSAI-WP11"
    authority = state["authority"]
    assert authority["orch_2"] == "ACTIVE_BOUNDED_SINGLE_PACKET"
    assert authority["orch_3"] == "INACTIVE_NOT_AUTHORISED"
    assert authority["orch_4"] == "INACTIVE_NOT_AUTHORISED"
    assert authority["orch_5"] == "INACTIVE_NOT_AUTHORISED"
    assert authority["validation"] == "DENIED"
