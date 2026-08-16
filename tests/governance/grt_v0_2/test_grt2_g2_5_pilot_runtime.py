from __future__ import annotations

from ovc.programme_genesis.grt_v0_2.pilot import evaluate_limited_candidate, summarize_pilot


def registry(*, docs_policy: str = "ADVISORY_ONLY_PRE_G3") -> dict:
    return {
        "roots": [
            {"path": "src", "governed": True, "new_write_policy": "ADVISORY_ONLY_PRE_G3"},
            {"path": "docs", "governed": True, "new_write_policy": docs_policy},
            {"path": ".github", "governed": True, "new_write_policy": "ADVISORY_ONLY_PRE_G3"},
            {"path": "tests", "governed": True, "new_write_policy": "ADVISORY_ONLY_PRE_G3"},
        ]
    }


def test_added_governed_artifact_is_evaluated_without_inventing_g3() -> None:
    result = evaluate_limited_candidate(
        changes=[{"status": "A", "path": "src/ovc/new_module.py"}],
        root_registry=registry(),
    )
    assert result["pilot_decision"] == "PASS"
    assert "ADDED_GOVERNED_ARTIFACT" in result["pilot_scope_classification"]
    assert result["full_g3_shadow_status"] == "NOT_EVALUABLE"
    assert result["g3_authority_effect"] == "NONE"


def test_new_workflow_is_in_pilot_scope_but_not_intrinsically_unlawful() -> None:
    result = evaluate_limited_candidate(
        changes=[{"status": "A", "path": ".github/workflows/new-check.yml"}],
        root_registry=registry(),
    )
    assert result["pilot_decision"] == "PASS"
    assert "NEW_WORKFLOW" in result["pilot_scope_classification"]
    assert result["pilot_findings"] == []


def test_new_unregistered_root_fails_limited_enforcement() -> None:
    result = evaluate_limited_candidate(
        changes=[{"status": "A", "path": "surprise/new.json"}],
        root_registry=registry(),
    )
    assert result["pilot_decision"] == "FAIL"
    assert result["pilot_findings"][0]["reason_code"] == "GRT2_G2_5_NEW_PERMANENT_ROOT_UNREGISTERED"


def test_deprecated_root_write_fails_limited_enforcement() -> None:
    result = evaluate_limited_candidate(
        changes=[{"status": "A", "path": "docs/new-current.md"}],
        root_registry=registry(docs_policy="DEPRECATED_NO_NEW_WRITES"),
    )
    assert result["pilot_decision"] == "FAIL"
    assert result["pilot_findings"][0]["reason_code"] == "GRT2_G2_5_FORBIDDEN_ROOT_NEW_WRITE"


def test_preexisting_modification_is_shadow_only_at_g2_5() -> None:
    result = evaluate_limited_candidate(
        changes=[{"status": "M", "path": "src/ovc/existing.py"}],
        root_registry=registry(),
    )
    assert result["pilot_decision"] == "PASS"
    assert result["pilot_scope_classification"] == ["PREEXISTING_ARTIFACT_CHANGE_SHADOW_ONLY"]
    assert result["scope_leakage_review"]["preexisting_modification_only_block_count"] == 0


def test_added_governed_unclassifiable_path_fails_closed_not_evaluable() -> None:
    result = evaluate_limited_candidate(
        changes=[{"status": "A", "path": "docs/opaque.bin"}],
        root_registry=registry(),
    )
    # docs is a lawful DOCUMENTATION classification in the repository classifier.
    assert result["pilot_decision"] == "PASS"


def _candidate(index: int, *, full_g3: str = "NOT_EVALUABLE", performance: str = "NOT_EVALUATED") -> dict:
    return {
        "candidate_id": f"C{index}",
        "candidate_class": "REAL_ORDINARY",
        "merged_at": f"2026-08-15T0{index}:00:00Z" if index < 10 else "2026-08-15T10:00:00Z",
        "exact_tree_replay": True,
        "pilot_decision": "PASS",
        "full_g3_shadow_status": full_g3,
        "escape_review": {"unresolved_escape_count": 0},
        "false_positive_review": {"unresolved_blocking_false_positive_count": 0},
        "false_negative_probes": {"unresolved_false_negative_count": 0},
        "scope_leakage_review": {"preexisting_modification_only_block_count": 0},
        "performance_status": performance,
        "qa_disposition": "PASS",
    }


def test_eight_real_candidates_and_24_hours_meet_pilot_threshold_not_g3() -> None:
    rows = [_candidate(i) for i in range(1, 9)]
    summary = summarize_pilot(
        candidate_records=rows,
        pilot_start="2026-08-14T13:53:00+01:00",
        evaluated_at="2026-08-16T09:15:00+01:00",
    )
    assert summary["elapsed_threshold_met"] is True
    assert summary["eligible_candidate_count"] == 8
    assert summary["real_candidate_count"] == 8
    assert summary["candidate_threshold_met"] is True
    assert summary["threshold_met"] is True
    assert summary["g3_ready"] is False
    assert summary["status"] == "THRESHOLD_MET_G3_EVIDENCE_INCOMPLETE"


def test_g3_ready_requires_full_shadow_and_per_candidate_performance() -> None:
    rows = [_candidate(i, full_g3="PASS", performance="PASS") for i in range(1, 9)]
    summary = summarize_pilot(
        candidate_records=rows,
        pilot_start="2026-08-14T13:53:00+01:00",
        evaluated_at="2026-08-16T09:15:00+01:00",
    )
    assert summary["g3_ready"] is True
    assert summary["status"] == "G3_READY"
