from __future__ import annotations

from ovc.programme_genesis.grt_v0_2.g3_readiness import (
    anomaly_extent,
    anomaly_subject_key,
    evaluate_candidate_evidence,
    reconcile_observer_transition_candidates,
    summarize_g3_readiness,
)


def _topology(commit: str, anomalies: list[dict], components: list[dict]) -> dict:
    return {
        "portfolio": {"source_commit": commit},
        "anomalies": anomalies,
        "components": components,
    }


def test_anomaly_subject_key_ignores_observer_anomaly_id_and_denominator_churn() -> None:
    components = [{"component_id": "C1", "path": "src/ovc/x.py"}]
    a = {
        "anomaly_id": "GRT.ANOM.old",
        "anomaly_code": "IMPLEMENTATION_WITHOUT_PROGRAMME_OWNER",
        "affected_component_ids": ["C1"],
        "affected_programme_ids": [],
        "denominator": {"count": 10},
    }
    b = dict(a, anomaly_id="GRT.ANOM.new", denominator={"count": 999})
    topology = _topology("a" * 40, [a], components)
    assert anomaly_subject_key(a, topology) == anomaly_subject_key(b, topology)


def test_unresolved_dependency_extent_preserves_expansion() -> None:
    assert anomaly_extent({
        "anomaly_code": "UNRESOLVED_DEPENDENCY",
        "detail": "3 repository-like path reference(s) do not resolve to a scanned tracked component.",
    }) == {"unresolved_reference_count": 3}


def test_transition_reconciliation_fails_closed_on_novel_or_expanded_condition() -> None:
    components = [{"component_id": "C1", "path": "src/ovc/x.py"}]
    baseline = _topology(
        "a" * 40,
        [{
            "anomaly_id": "old",
            "anomaly_code": "UNRESOLVED_DEPENDENCY",
            "affected_component_ids": ["C1"],
            "affected_programme_ids": [],
            "detail": "1 repository-like path reference(s) do not resolve to a scanned tracked component.",
        }],
        components,
    )
    current = _topology(
        "b" * 40,
        [
            {
                "anomaly_id": "expanded",
                "anomaly_code": "UNRESOLVED_DEPENDENCY",
                "affected_component_ids": ["C1"],
                "affected_programme_ids": [],
                "detail": "2 repository-like path reference(s) do not resolve to a scanned tracked component.",
            },
            {
                "anomaly_id": "novel",
                "anomaly_code": "ORPHAN_SCHEMA",
                "affected_component_ids": ["C1"],
                "affected_programme_ids": [],
                "detail": "new observer condition",
            },
        ],
        components,
    )
    result = reconcile_observer_transition_candidates(
        baseline_topology=baseline,
        current_topology=current,
    )
    assert result["stable_expanded_count"] == 1
    assert result["novel_observer_condition_count"] == 1
    assert result["transition_debt_zero_proven"] is False
    assert result["baseline_expansion_zero_proven"] is False


def test_g3_summary_never_converts_missing_evidence_into_gate_ready() -> None:
    record = {
        "candidate_id": "C",
        "full_g3_shadow_status": "PASS",
        "unresolved_escape_count": 0,
        "blocking_false_positive_count": 0,
        "unresolved_false_negative_count": 0,
        "scope_leakage_count": 0,
        "performance_status": "PASS",
        "qa_disposition": "PASS",
    }
    summary = summarize_g3_readiness(
        pilot_records=[record],
        historical_records=[record] * 10,
        transition_reconciliation={
            "transition_debt_zero_proven": False,
            "baseline_expansion_zero_proven": True,
        },
        candidate_floor_ready=True,
    )
    assert summary["status"] == "EVIDENCE_INCOMPLETE"
    assert "PRE_G3_TRANSITION_DEBT_ZERO_NOT_PROVEN" in summary["reason_codes"]


def test_complete_shadow_may_preserve_a_constitutional_would_block() -> None:
    record = {
        "candidate_id": "C",
        "full_g3_shadow_status": "PASS",
        "full_g3_candidate_admission": "FAIL",
        "new_or_expanded_debt_count": 2,
        "unresolved_escape_count": 0,
        "blocking_false_positive_count": 0,
        "unresolved_false_negative_count": 0,
        "scope_leakage_count": 0,
        "performance_status": "PASS",
        "qa_disposition": "PASS",
    }
    assert evaluate_candidate_evidence(record)["status"] == "PASS"
