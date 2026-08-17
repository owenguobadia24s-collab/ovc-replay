from ovc.research_operations.prsc.preregistration import (
    PRSCPreregistrationError,
    build_preregistration_bundle,
    build_protocol_generation,
    build_readiness_receipt,
    run_synthetic_candidate_to_q08,
)


def _protocol(state="DRAFT"):
    return build_protocol_generation(
        protocol_series_id="PRSC.EC1.G1",
        generation=1,
        scientific_generation="OVC-EC1-DISCOVERY-2021_2023-G1",
        method_pack_refs=["m2", "m1"],
        hypothesis_family_registry_ref="family-registry",
        claim_template_refs=["P1C", "P1A", "P1B"],
        reviewer_constitution_ref="reviewers",
        source_namespaces=["PRSC_SYNTHETIC", "EC1"],
        preregistration_state=state,
    )


def _bundle(exposed=False):
    return build_preregistration_bundle(
        protocol_generation=_protocol("READY_FOR_OPERATOR_FREEZE"),
        method_pack_refs=["m1", "m2"],
        hypothesis_family_registry_ref="family-registry",
        claim_template_refs=["P1A", "P1B", "P1C"],
        fatality_disposition_rule_refs=["fatality-rules"],
        reviewer_constitution_ref="reviewers",
        pre_e1_information_only=True,
        e1_decision_bearing_inspected=exposed,
        synthetic_candidate_ref="candidate-synthetic-1",
    )


def test_protocol_identity_is_deterministic_and_build_ahead_cannot_freeze():
    assert _protocol() == _protocol()
    try:
        _protocol("FROZEN")
    except PRSCPreregistrationError:
        pass
    else:
        raise AssertionError("build-ahead must not create FROZEN protocol")


def test_synthetic_candidate_to_q08_has_no_real_or_freeze_effect():
    result = run_synthetic_candidate_to_q08("candidate-synthetic-1")
    assert result["real_source_read"] is False
    assert result["candidate_freeze_effect"] == "NONE"
    assert result["q08"]["status"] == "SYNTHETIC_ONLY"


def test_wp9_build_ahead_is_ready_but_not_operator_ready_before_g8_alg():
    receipt = build_readiness_receipt(_bundle(), g8_alg_status="NOT_YET_PASSED")
    assert receipt["status"] == "BUILD_AHEAD_READY"
    assert receipt["e1_exposure_status"] == "PRE_E1_CLEAN"
    assert receipt["authority_effect"] == "NONE"


def test_g8_alg_pass_only_makes_receipt_ready_for_operator_decision():
    receipt = build_readiness_receipt(_bundle(), g8_alg_status="PASS")
    assert receipt["status"] == "READY_FOR_OPERATOR_DECISION"
    assert receipt["operator_gate"] == "PRSCI-G-PREREG"


def test_e1_decision_bearing_exposure_blocks_same_generation():
    receipt = build_readiness_receipt(_bundle(exposed=True), g8_alg_status="PASS")
    assert receipt["status"] == "BLOCKED"
    assert receipt["e1_exposure_status"] == "E1_DECISION_BEARING_EXPOSED"


def test_pre_e1_false_fails_closed():
    try:
        build_preregistration_bundle(
            protocol_generation=_protocol(),
            method_pack_refs=["m1"],
            hypothesis_family_registry_ref="family-registry",
            claim_template_refs=["P1A"],
            fatality_disposition_rule_refs=["fatality-rules"],
            reviewer_constitution_ref="reviewers",
            pre_e1_information_only=False,
            e1_decision_bearing_inspected=False,
            synthetic_candidate_ref="candidate-synthetic-1",
        )
    except PRSCPreregistrationError:
        pass
    else:
        raise AssertionError("non-pre-E1 bundle must fail closed")
