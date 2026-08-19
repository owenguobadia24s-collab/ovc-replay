from __future__ import annotations

from ovc.research_operations.p2cti.firewall import project_population, project_record


def _record(**overrides):
    base = {
        "evidence_id": "evidence:001",
        "information_class": "GENERAL_METHODOLOGY",
        "visibility": "PUBLIC_SAFE",
        "owner_object_type": "THEORY_RECORD",
        "decision_bearing": False,
        "candidate_frozen": False,
        "warnings": [],
        "restricted_payload": {"must": "never leak"},
    }
    return {**base, **overrides}


def test_path1_safe_denies_candidate_defining_path2_information_without_leak() -> None:
    for information_class in (
        "PATH2_PREDICATE", "PATH2_EXAMPLE", "PATH2_FALSIFIER", "PATH2_PARAMETER_BOUNDARY", "PATH2_RESTRICTED_NEIGHBOURHOOD"
    ):
        result = project_record(_record(information_class=information_class, visibility="PATH2_RESTRICTED"), projection="PATH1_SAFE")
        assert result["admitted"] is False
        assert result["payload"] is None
        assert result["scientific_inference"] == "NONE"


def test_path2_full_does_not_expose_unfrozen_path1_candidate_without_exact_exposure() -> None:
    denied = project_record(_record(information_class="PATH1_UNFROZEN_CANDIDATE", visibility="PUBLIC_SAFE"), projection="PATH2_FULL")
    assert denied["admitted"] is False
    admitted = project_record(_record(information_class="PATH1_UNFROZEN_CANDIDATE", visibility="PUBLIC_SAFE", dmrp_exposure_evidence={"record_id": "exposure:1", "status": "RECORDED"}), projection="PATH2_FULL")
    assert admitted["admitted"] is True


def test_cross_mode_requires_freeze_exposure_and_formal_correspondence() -> None:
    base = _record(information_class="FROZEN_CANDIDATE", visibility="CROSS_MODE_POST_FREEZE", candidate_frozen=True)
    assert project_record(base, projection="CROSS_MODE_POST_FREEZE")["admitted"] is False
    with_exposure = {**base, "dmrp_exposure_evidence": {"record_id": "exposure:1", "status": "RECORDED"}}
    assert project_record(with_exposure, projection="CROSS_MODE_POST_FREEZE")["admitted"] is False
    complete = {**with_exposure, "dmrp_correspondence_evidence": {"record_id": "corr:1", "status": "FORMAL"}}
    result = project_record(complete, projection="CROSS_MODE_POST_FREEZE")
    assert result["admitted"] is True
    assert result["authority_effect"] == "NONE"


def test_rccr_source_rejects_raw_seed_as_decision_bearing() -> None:
    denied = project_record(_record(owner_object_type="THEORY_SEED", decision_bearing=True, visibility="RCCR_SOURCE_ONLY"), projection="RCCR_SOURCE")
    assert denied["admitted"] is False
    admitted = project_record(_record(owner_object_type="THEORY_RECORD", decision_bearing=True, visibility="RCCR_SOURCE_ONLY"), projection="RCCR_SOURCE")
    assert admitted["admitted"] is True


def test_population_projection_is_order_independent_and_proves_negative_reachability() -> None:
    a = _record(evidence_id="evidence:a")
    b = _record(evidence_id="evidence:b", information_class="PATH2_FALSIFIER", visibility="PATH2_RESTRICTED")
    first = project_population([a, b], projection="PATH1_SAFE")
    second = project_population([b, a], projection="PATH1_SAFE")
    assert first == second
    assert first["denied_evidence_ids"] == ["evidence:b"]
    assert first["negative_reachability_proved"] is True
    assert first["complete"] is False
    assert first["operational_reliance"] is False
    assert "must" not in repr(first)
