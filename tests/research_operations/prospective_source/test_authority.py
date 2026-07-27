from __future__ import annotations

import unittest

from ovc.research_operations.prospective_source.authority import AuthoritySnapshot, authority_from_mapping


class AuthoritySnapshotTests(unittest.TestCase):
    def test_authority_defaults_fail_closed(self) -> None:
        snapshot = AuthoritySnapshot()
        self.assertTrue(snapshot.pd_g4_approved)
        self.assertFalse(snapshot.rps_g4_approved)
        self.assertFalse(snapshot.write_authority)
        self.assertFalse(snapshot.live_append_enabled)
        self.assertEqual(snapshot.authority_label, "TIME_GATED_REPLAY_NON_EVIDENTIARY")

    def test_pd_g4_alone_never_enables_live_append(self) -> None:
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
        self.assertFalse(snapshot.live_append_enabled)

    def test_all_live_conditions_are_required(self) -> None:
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
        self.assertTrue(authority_from_mapping(base).live_append_enabled)
        for field in (
            "pd_g4_approved",
            "rps_g4_approved",
            "operator_key_bound",
            "bridge_healthy",
            "write_authority",
            "candidate_source_resolved",
        ):
            with self.subTest(field=field):
                value = dict(base)
                value[field] = False
                self.assertFalse(authority_from_mapping(value).live_append_enabled)

    def test_time_gated_replay_never_enables_live_append(self) -> None:
        snapshot = AuthoritySnapshot(
            rps_g4_approved=True,
            operator_key_bound=True,
            bridge_healthy=True,
            write_authority=True,
            operation_mode="TIME_GATED_REPLAY",
            source_binding_id="RPS.BINDING.TEST",
            candidate_source_resolved=True,
        )
        self.assertFalse(snapshot.live_append_enabled)


if __name__ == "__main__":
    unittest.main()
