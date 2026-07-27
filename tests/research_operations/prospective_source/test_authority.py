from __future__ import annotations

from ovc.research_operations.prospective_source.authority import AuthoritySnapshot, authority_from_mapping


def test_authority_defaults_fail_closed() -> None:
    snapshot = AuthoritySnapshot()
    assert snapshot.pd_g4_approved is True
    assert snapshot.rps_g4_approved is False
    assert snapshot.write_authority is False
    assert snapshot.live_append_enabled is False
    assert snapshot.authority_label == "TIME_GATED_REPLAY_NON_EVIDENTIARY"


def test_pd_g4_alone_never_enables_live_append() -> None:
    snapshot = AuthoritySnapshot(
        pd_g4_approved=True,
        rps_g4_approved=False,
        operator_key_bound=True,
        bridge_healthy=True,
        write_authority=True,
        operation_mode="LIVE_PROSPECTIVE",
        source_binding_id="RPS.BINDING.TEST",
        candidate_source_resolved=True,
    )
    assert snapshot.live_append_enabled is False


def test_all_live_conditions_are_required() -> None:
    base = {
        "pd_g4_approved": True,
        "rps_g4_approved": True,
        "operator_key_bound": True,
        "bridge_healthy": True,
        "write_authority": True,
        "operation_mode": "LIVE_PROSPECTIVE",
        "source_binding_id": "RPS.BINDING.TEST",
        "candidate_source_resolved": True,
    }
    assert authority_from_mapping(base).live_append_enabled is True
    for field in (
        "pd_g4_approved",
        "rps_g4_approved",
        "operator_key_bound",
        "bridge_healthy",
        "write_authority",
        "candidate_source_resolved",
    ):
        value = dict(base)
        value[field] = False
        assert authority_from_mapping(value).live_append_enabled is False


def test_time_gated_replay_never_enables_live_append() -> None:
    snapshot = AuthoritySnapshot(
        rps_g4_approved=True,
        operator_key_bound=True,
        bridge_healthy=True,
        write_authority=True,
        operation_mode="TIME_GATED_REPLAY",
        source_binding_id="RPS.BINDING.TEST",
        candidate_source_resolved=True,
    )
    assert snapshot.live_append_enabled is False
