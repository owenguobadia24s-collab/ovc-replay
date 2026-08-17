import pytest

from ovc.research_operations.prsc.replication import (
    ExposureState,
    ReplicationFirewallError,
    apply_exposure,
    assert_exposure_monotone,
    assert_zero_protected_source_reachability,
    evaluate_disjointness,
    validate_method_transport,
    validate_replication_protocol_pack,
    validate_validation_reservation,
)


def test_disjointness_passes_only_on_zero_overlap():
    decision = evaluate_disjointness(["a", "b"], ["c", "d"])
    assert decision.state == "DISJOINT"
    assert decision.overlap_refs == ()
    blocked = evaluate_disjointness(["a", "b"], ["b", "c"])
    assert blocked.state == "OVERLAP_BLOCKED"
    assert blocked.overlap_refs == ("b",)


def test_exposure_is_irreversible_and_channel_specific():
    initial = ExposureState()
    human = apply_exposure(initial, "HUMAN")
    assert human.human_exposed is True
    assert human.contaminated is True
    with pytest.raises(ReplicationFirewallError):
        assert_exposure_monotone(human, ExposureState())


def test_wp7_rejects_real_or_protected_replication():
    base = {
        "replication_protocol_id": "r",
        "candidate_ref": "c",
        "protocol_generation_ref": "g",
        "source_role": "SYNTHETIC",
        "identity_unit": "occurrence",
        "disjointness_manifest_ref": "d",
        "method_transport_manifest_ref": "m",
        "population_exposure_ledger_ref": "e",
        "real_execution_allowed": False,
        "authority_effect": "NONE",
    }
    validate_replication_protocol_pack(base)
    with pytest.raises(ReplicationFirewallError):
        validate_replication_protocol_pack({**base, "real_execution_allowed": True})
    with pytest.raises(ReplicationFirewallError):
        validate_replication_protocol_pack({**base, "source_role": "VALIDATION"})


def test_method_transport_cannot_hide_refit():
    validate_method_transport({"transport_state": "TRANSPORTED_UNCHANGED", "refit_allowed": False})
    validate_method_transport({"transport_state": "REFIT_REQUIRED", "refit_allowed": True})
    with pytest.raises(ReplicationFirewallError):
        validate_method_transport({"transport_state": "TRANSPORTED_UNCHANGED", "refit_allowed": True})


def test_validation_reservation_has_no_read_surface():
    record = {
        "validation_role": "VALIDATION",
        "reservation_state": "RESERVED_UNCONSUMED",
        "read_path_present": False,
        "source_locator_present": False,
        "credential_present": False,
        "query_present": False,
        "authority_effect": "NONE",
    }
    validate_validation_reservation(record)
    with pytest.raises(ReplicationFirewallError):
        validate_validation_reservation({**record, "query_present": True})


def test_protected_source_negative_reachability_is_zero_tolerance():
    safe = [
        {"edge_id": "dev", "source_role": "DEVELOPMENT", "reachable": "false"},
        {"edge_id": "val", "source_role": "VALIDATION", "reachable": "false"},
    ]
    assert_zero_protected_source_reachability(safe)
    with pytest.raises(ReplicationFirewallError):
        assert_zero_protected_source_reachability([
            {"edge_id": "val", "source_role": "VALIDATION", "reachable": "true"}
        ])
