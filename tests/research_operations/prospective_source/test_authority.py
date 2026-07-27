from __future__ import annotations

import unittest

from ovc.research_operations.prospective_source.authority import AuthoritySnapshot, authority_from_mapping


class AuthoritySnapshotTests(unittest.TestCase):
    def test_authority_defaults_fail_closed(self) -> None:
        snapshot = AuthoritySnapshot()
        self.assertTrue(snapshot.pd_g4_approved)
        self.assertFalse(snapshot.rps_g4_approved)
        self.assertFalse(snapshot.write_authority)
        self.assertFalse(snapshot.triage_enabled)
        self.assertFalse(snapshot.live_append_enabled)
        self.assertEqual(snapshot.authority_label, "TIME_GATED_REPLAY_NON_EVIDENTIARY")

    def test_pd_g4_alone_never_enables_live_triage_or_append(self) -> None:
        snapshot = AuthoritySnapshot(
            pd_g4_approved=True,
            rps_g4_approved=False,
            operator_key_bound=True,
            bridge_healthy=True,
            write_authority=True,
            operation_mode="LIVE_PROSPECTIVE",
            source_binding_id="RPS.BINDING.TEST",
            signing_binding_id="RPS.SIGNING.TEST",
            operator_id="OVC.OPERATOR.TEST.V1",
            candidate_source_resolved=True,
        )
        self.assertFalse(snapshot.triage_enabled)
        self.assertFalse(snapshot.live_append_enabled)
        self.assertEqual(snapshot.authority_label, "LIVE_APPEND_DISABLED_PENDING_RPS_G4")

    def test_all_global_activation_conditions_are_required(self) -> None:
        base = {
            "pd_g4_approved": True,
            "rps_g4_approved": True,
            "operator_key_bound": True,
            "bridge_healthy": True,
            "write_authority": True,
            "operation_mode": "LIVE_PROSPECTIVE",
            "source_binding_id": "RPS.BINDING.TEST",
            "signing_binding_id": "RPS.SIGNING.TEST",
            "operator_id": "OVC.OPERATOR.TEST.V1",
            "candidate_source_resolved": False,
        }
        snapshot = authority_from_mapping(base)
        self.assertTrue(snapshot.triage_enabled)
        self.assertFalse(snapshot.live_append_enabled)
        self.assertEqual(snapshot.authority_label, "ACTIVE_RESEARCH_TRIAGE")
        for field in (
            "pd_g4_approved",
            "rps_g4_approved",
            "operator_key_bound",
            "bridge_healthy",
            "write_authority",
        ):
            with self.subTest(field=field):
                value = dict(base)
                value[field] = False
                self.assertFalse(authority_from_mapping(value).triage_enabled)
        for field in ("source_binding_id", "signing_binding_id", "operator_id"):
            with self.subTest(field=field):
                value = dict(base)
                value[field] = None
                self.assertFalse(authority_from_mapping(value).triage_enabled)

    def test_candidate_resolution_is_required_only_for_append(self) -> None:
        snapshot = AuthoritySnapshot(
            rps_g4_approved=True,
            operator_key_bound=True,
            bridge_healthy=True,
            write_authority=True,
            operation_mode="LIVE_PROSPECTIVE",
            source_binding_id="RPS.BINDING.TEST",
            signing_binding_id="RPS.SIGNING.TEST",
            operator_id="OVC.OPERATOR.TEST.V1",
            candidate_source_resolved=True,
        )
        self.assertTrue(snapshot.triage_enabled)
        self.assertTrue(snapshot.live_append_enabled)
        self.assertEqual(snapshot.authority_label, "ACTIVE_RESEARCH_TRIAGE_APPEND_ENABLED")

    def test_time_gated_replay_never_enables_live_append(self) -> None:
        snapshot = AuthoritySnapshot(
            rps_g4_approved=True,
            operator_key_bound=True,
            bridge_healthy=True,
            write_authority=True,
            operation_mode="TIME_GATED_REPLAY",
            source_binding_id="RPS.BINDING.TEST",
            signing_binding_id="RPS.SIGNING.TEST",
            operator_id="OVC.OPERATOR.TEST.V1",
            candidate_source_resolved=True,
        )
        self.assertFalse(snapshot.triage_enabled)
        self.assertFalse(snapshot.live_append_enabled)
        self.assertEqual(snapshot.authority_label, "TIME_GATED_REPLAY_NON_EVIDENTIARY")

    def test_incomplete_post_approval_activation_fails_closed(self) -> None:
        snapshot = AuthoritySnapshot(
            rps_g4_approved=True,
            operation_mode="LIVE_PROSPECTIVE",
        )
        self.assertFalse(snapshot.triage_enabled)
        self.assertFalse(snapshot.live_append_enabled)
        self.assertEqual(snapshot.authority_label, "ACTIVE_RESEARCH_TRIAGE_ACTIVATION_INCOMPLETE")

    def test_non_mapping_input_fails_closed(self) -> None:
        snapshot = authority_from_mapping("FIXTURE_ONLY_NO_WRITE")  # type: ignore[arg-type]
        self.assertFalse(snapshot.triage_enabled)
        self.assertFalse(snapshot.live_append_enabled)
        self.assertEqual(snapshot.authority_label, "TIME_GATED_REPLAY_NON_EVIDENTIARY")


if __name__ == "__main__":
    unittest.main()
