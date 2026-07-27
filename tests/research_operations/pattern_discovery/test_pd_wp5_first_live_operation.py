from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from ovc.research_operations.pattern_discovery import first_live_operation as subject


class PdWp5FirstLiveOperationTests(unittest.TestCase):
    def _activation(self) -> dict[str, object]:
        return {
            "plan_id": subject.PLAN_ID,
            "gate_id": "RPS-G4",
            "decision": "PASS",
            "decision_authority": "OPERATOR",
            "source_binding_id": subject.SOURCE_BINDING_ID,
            "signing_binding_id": subject.SIGNING_BINDING_ID,
            "operator_id": subject.OPERATOR_ID,
            "active_model_release_id": subject.ACTIVE_RELEASE_ID,
            "operation_mode": "LIVE_PROSPECTIVE",
            "activation_merge_commit": subject.ACTIVATION_MERGE,
            "first_operation_limit": 1,
            "next_packet": subject.PACKET_ID,
            "next_gate": subject.GATE_ID,
            "pd_g4_approved": True,
            "rps_g4_approved": True,
            "operator_key_bound": True,
            "bridge_healthy": True,
            "write_authority": True,
            "active_research_triage": True,
            "candidate_source_resolved": False,
            "live_append_enabled": False,
            "time_gated_replay_backfill": "DENIED",
            "eligible_data_through_utc": "2026-06-25T00:00:00Z",
        }

    def _candidate(self) -> dict[str, object]:
        return {
            "operation_mode": "LIVE_PROSPECTIVE",
            "source_binding_id": subject.SOURCE_BINDING_ID,
            "signing_binding_id": subject.SIGNING_BINDING_ID,
            "operator_id": subject.OPERATOR_ID,
            "active_release_id": subject.ACTIVE_RELEASE_ID,
            "active_manifest_id": subject.ACTIVE_MANIFEST_ID,
            "active_manifest_sha256": subject.ACTIVE_MANIFEST_SHA256,
            "source_object_ids": ["C2.STATE.TEST.1", "C2.TRANSITION.TEST.1"],
            "market_window_start_utc": "2026-07-28T00:00:00Z",
            "market_window_end_utc": "2026-07-28T02:00:00Z",
            "trigger_first_valid_at": "2026-07-28T00:15:00Z",
        }

    def test_current_exact_binding_cannot_support_post_activation_candidate(self) -> None:
        blocker = subject.source_coverage_blocker(
            self._activation(),
            "2026-07-27T20:10:00Z",
        )
        self.assertIsNotNone(blocker)
        assert blocker is not None
        self.assertEqual(
            blocker["code"],
            "ACTIVE_BINDING_HAS_NO_POST_ACTIVATION_MARKET_COVERAGE",
        )
        self.assertEqual(blocker["eligible_data_through_utc"], "2026-06-25T00:00:00Z")
        self.assertEqual(blocker["replay_substitution"], "DENIED")
        self.assertEqual(blocker["smallest_lawful_resolution"], "RPS-G4A")

    def test_amendment_slice_is_strictly_after_activation(self) -> None:
        proposal = subject.amendment_proposal("2026-07-27T20:10:00Z")
        self.assertEqual(proposal["gate_id"], "RPS-G4A")
        self.assertEqual(
            proposal["slice_id"],
            "RPS.DUKASCOPY.GBPUSD.20260728_20260801.v1",
        )
        self.assertEqual(
            proposal["interval"],
            {
                "start_utc": "2026-07-28T00:00:00Z",
                "end_utc": "2026-08-01T00:00:00Z",
            },
        )
        self.assertEqual(
            proposal["streams"],
            ["M1_BID", "M1_ASK", "H1_BID", "H1_ASK"],
        )
        self.assertEqual(proposal["provider_request_before_approval"], "DENIED")
        self.assertIn("DEFER_EXECUTION", proposal["current_month_availability_condition"])

    def test_replay_or_pre_activation_candidate_is_rejected(self) -> None:
        replay = self._candidate()
        replay["operation_mode"] = "TIME_GATED_REPLAY"
        errors = subject.validate_candidate_package(replay, "2026-07-27T20:10:00Z")
        self.assertIn("candidate package must use LIVE_PROSPECTIVE", errors)

        old = self._candidate()
        old["market_window_start_utc"] = "2026-07-27T18:00:00Z"
        old["market_window_end_utc"] = "2026-07-27T20:00:00Z"
        old["trigger_first_valid_at"] = "2026-07-27T18:15:00Z"
        errors = subject.validate_candidate_package(old, "2026-07-27T20:10:00Z")
        self.assertIn("candidate is not strictly post-activation", errors)

    def test_exact_future_candidate_shape_is_valid_when_binding_has_coverage(self) -> None:
        errors = subject.validate_candidate_package(
            self._candidate(),
            "2026-07-27T20:10:00Z",
        )
        self.assertEqual(errors, [])

    def test_activation_validation_requires_all_exact_ids_and_denials(self) -> None:
        subject.validate_activation(self._activation())
        for field in (
            "source_binding_id",
            "signing_binding_id",
            "operator_id",
            "activation_merge_commit",
        ):
            value = self._activation()
            value[field] = "WRONG"
            with self.subTest(field=field):
                with self.assertRaisesRegex(subject.FirstLiveOperationError, "mismatch"):
                    subject.validate_activation(value)
        value = self._activation()
        value["time_gated_replay_backfill"] = "ALLOWED"
        with self.assertRaisesRegex(subject.FirstLiveOperationError, "backfill"):
            subject.validate_activation(value)

    def test_preflight_materialises_expected_external_blocker_without_network(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            activation_path = root / subject.ACTIVE_AUTHORITY_RECORD
            activation_path.parent.mkdir(parents=True)
            import json
            activation_path.write_text(json.dumps(self._activation()), encoding="utf-8")
            with (
                patch.object(subject, "repository_state", return_value=("main", "f" * 40)),
                patch.object(subject, "activation_cutoff", return_value="2026-07-27T20:10:00Z"),
            ):
                result, exit_code = subject.preflight(root)
        self.assertEqual(exit_code, 3)
        self.assertEqual(result["status"], "BLOCKED_POST_ACTIVATION_SOURCE_REQUIRED")
        self.assertFalse(result["provider_network_access_performed"])
        self.assertEqual(result["blockers"][0]["smallest_lawful_resolution"], "RPS-G4A")
        self.assertEqual(result["amendment_proposal"]["provider"], "DUKASCOPY")
        self.assertEqual(result["next_action"], "OVC APPROVE RPS-G4A OR DEFER")

    def test_proposed_window_is_after_mock_activation_cutoff(self) -> None:
        start = subject.parse_utc(subject.PROPOSED_WINDOW_START)
        cutoff = subject.parse_utc("2026-07-27T20:10:00Z")
        self.assertGreater(start, cutoff)
        self.assertEqual(start.tzinfo, timezone.utc)
        self.assertEqual(start, datetime(2026, 7, 28, tzinfo=timezone.utc))


if __name__ == "__main__":
    unittest.main()
