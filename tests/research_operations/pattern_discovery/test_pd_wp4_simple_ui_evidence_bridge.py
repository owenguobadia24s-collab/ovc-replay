from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from apps.research_console.pattern_discovery import AUTHORITY
from apps.research_console.pattern_discovery_fixtures import pattern_discovery_fixture_bundle
from ovc.research_operations.pattern_discovery import (
    AppendRequest,
    EvidenceBridgeError,
    LocalEvidenceBridge,
    SourceResolver,
    build_candidate_detail,
    build_cluster_view,
    build_price_strip,
    build_review_queue_item,
)


class FixtureEd25519Signer:
    algorithm = "ED25519"
    operator_id = "operator.fixture"

    def sign(self, payload: bytes) -> str:
        import hashlib
        return "FIXTURE-ED25519-" + hashlib.sha256(payload).hexdigest()


class PatternDiscoveryWP4Tests(unittest.TestCase):
    def test_simple_ui_has_exactly_three_views_and_write_is_disabled(self) -> None:
        bundle = pattern_discovery_fixture_bundle()
        self.assertEqual(AUTHORITY["views"], ["Queue", "Candidate Detail", "Clusters"])
        self.assertEqual(AUTHORITY["research_write"], "OPERATOR_GATE_REQUIRED")
        self.assertEqual(len(bundle["queue_items"]), 1)
        candidate_id = bundle["queue_items"][0]["candidate_window_id"]
        self.assertIn(candidate_id, bundle["candidate_details"])
        self.assertIn("PROVISIONAL", bundle["cluster_view"]["authority_banner"])

    def test_review_projections_preserve_lineage_and_permitted_classes(self) -> None:
        bundle = pattern_discovery_fixture_bundle()
        item = bundle["queue_items"][0]
        detail = bundle["candidate_details"][item["candidate_window_id"]]
        self.assertEqual(item["authority"], "READ_ONLY_CANDIDATE")
        self.assertTrue(detail["source_lineage"]["c2_record_ids"])
        self.assertEqual(len(detail["permitted_review_classes"]), 5)
        self.assertNotIn("PROMOTE_ARCHETYPE", bundle["cluster_view"]["permitted_actions"])
        self.assertIn("PROMOTE_ARCHETYPE", bundle["cluster_view"]["prohibited_actions"])

    def test_price_strip_uses_exact_opt_a_release_and_cannot_outrun_c2(self) -> None:
        candidate = {
            "status": "READY_FOR_REVIEW",
            "opt_a_release_id": "OPT-A.GBPUSD.DISCOVERY.v2",
            "clock": "15M",
            "window_start_utc": "2026-07-27T08:00:00Z",
            "trigger_first_valid_at": "2026-07-27T08:15:00Z",
            "window_end_utc": "2026-07-27T08:30:00Z",
            "represented_c2_time": "2026-07-27T08:30:00Z",
            "closure_reason": "STABLE_RESOLUTION",
        }
        bars = [
            {"bar_id": "A1", "release_id": "OPT-A.GBPUSD.DISCOVERY.v2", "clock": "15M", "bar_end_utc": "2026-07-27T08:00:00Z", "open": "1", "high": "2", "low": "0", "close": "1.1"},
            {"bar_id": "A2", "release_id": "OPT-A.GBPUSD.DISCOVERY.v2", "clock": "15M", "bar_end_utc": "2026-07-27T08:15:00Z", "open": "1.1", "high": "2", "low": "1", "close": "1.2"},
            {"bar_id": "OTHER", "release_id": "OTHER", "clock": "15M", "bar_end_utc": "2026-07-27T08:15:00Z", "close": "9"},
        ]
        strip = build_price_strip(candidate, opt_a_bars=bars, boundary_references=[{"reference_id": "L1", "value": "1.2", "reference_type": "LEVEL", "source_c2_record_id": "C2S1"}])
        self.assertEqual(strip["status"], "AVAILABLE")
        self.assertEqual(strip["source_release_id"], candidate["opt_a_release_id"])
        self.assertEqual([row["bar_id"] for row in strip["bars"]], ["A1", "A2"])
        self.assertEqual(strip["boundary_references"][0]["source_c2_record_id"], "C2S1")

        too_new = bars + [{"bar_id": "A3", "release_id": candidate["opt_a_release_id"], "clock": "15M", "bar_end_utc": "2026-07-27T08:45:00Z", "close": "1.3"}]
        candidate_late = dict(candidate)
        candidate_late["window_end_utc"] = "2026-07-27T08:45:00Z"
        with self.assertRaisesRegex(Exception, "may not outrun"):
            build_price_strip(candidate_late, opt_a_bars=too_new)

    def test_source_resolver_prevents_manual_or_mismatched_ids(self) -> None:
        candidate = {
            "window_id": "PDW-1",
            "operation_mode": "LIVE_PROSPECTIVE",
            "trigger_first_valid_at": "2026-07-27T08:15:00Z",
            "source_release_id": "C2-REL-1",
            "source_c2_record_ids": ["C2S-1", "C2S-2"],
        }
        fingerprint = {"fingerprint_id": "FP-1", "candidate_window_id": "PDW-1", "source_release_id": "C2-REL-1"}
        resolver = SourceResolver({"PDW-1": candidate}, {"FP-1": fingerprint})
        resolved = resolver.resolve("PDW-1", "FP-1")
        self.assertEqual(resolved["source_record_ids"], ["C2S-1", "C2S-2"])
        bad = dict(fingerprint)
        bad["candidate_window_id"] = "OTHER"
        with self.assertRaisesRegex(EvidenceBridgeError, "mismatch"):
            SourceResolver({"PDW-1": candidate}, {"FP-1": bad}).resolve("PDW-1", "FP-1")

    def _request(self, *, request_id: str = "REQ-1", sequence: int = 1, nonce: str = "N-1", body=None, mode: str = "LIVE_PROSPECTIVE") -> AppendRequest:
        return AppendRequest(
            append_request_id=request_id,
            operator_id="operator.fixture",
            session_id="SESSION-1",
            nonce=nonce,
            expected_sequence_number=sequence,
            candidate_window_id="PDW-1",
            candidate_fingerprint_hash="FPHASH-1",
            source_release_ids=("C2-REL-1",),
            source_record_ids=("C2S-1", "C2S-2"),
            admissible_cutoff="2026-07-27T08:15:00Z",
            record_class="STATE_FIDELITY_REVIEW",
            record_body=body or {"observation": "C2 represents the boundary interaction coherently.", "limitation": "Parent context needs review."},
            requested_at="2026-07-27T09:00:00Z",
            ui_build_hash="UI-BUILD-1",
            operation_mode=mode,
        )

    def test_bridge_is_disabled_until_operator_gate(self) -> None:
        with tempfile.TemporaryDirectory() as root:
            bridge = LocalEvidenceBridge(root, signer=FixtureEd25519Signer(), service_build_hash="BUILD-1")
            with self.assertRaisesRegex(EvidenceBridgeError, "OPERATOR_GATE_REQUIRED"):
                bridge.submit(self._request(), session_token=bridge.session_token, freeze_confirmed=True)
            self.assertFalse(list(Path(root).rglob("*.json")))

    def test_candidate_bridge_is_atomic_idempotent_and_audit_chained(self) -> None:
        with tempfile.TemporaryDirectory() as root:
            bridge = LocalEvidenceBridge(root, signer=FixtureEd25519Signer(), service_build_hash="BUILD-1", candidate_test_mode=True)
            first = bridge.submit(self._request(), session_token=bridge.session_token, freeze_confirmed=True)
            second = bridge.submit(self._request(), session_token=bridge.session_token, freeze_confirmed=True)
            self.assertEqual(first, second)
            self.assertEqual(first["status"], "COMMITTED")
            self.assertFalse(first["canonical"])
            transactions = list((Path(root) / "transactions").glob("*.json"))
            self.assertEqual(len(transactions), 1)
            transaction = json.loads(transactions[0].read_text(encoding="utf-8"))
            self.assertIn("evidence_record", transaction)
            self.assertIn("audit_event", transaction)
            self.assertEqual(transaction["audit_event"]["signature_algorithm"], "ED25519")
            self.assertEqual(transaction["audit_event"]["previous_event_hash"], "GENESIS")

    def test_bridge_rejects_replay_duplicate_body_sequence_and_exposure_fields(self) -> None:
        with tempfile.TemporaryDirectory() as root:
            bridge = LocalEvidenceBridge(root, signer=FixtureEd25519Signer(), service_build_hash="BUILD-1", candidate_test_mode=True)
            replay = bridge.submit(self._request(mode="NON_EVIDENTIARY_REPLAY"), session_token=bridge.session_token, freeze_confirmed=True)
            self.assertEqual(replay["status"], "REJECTED")
            self.assertEqual(replay["rejection_reason"], "REPLAY_OR_FIXTURE_CONTAMINATION")

        with tempfile.TemporaryDirectory() as root:
            bridge = LocalEvidenceBridge(root, signer=FixtureEd25519Signer(), service_build_hash="BUILD-1", candidate_test_mode=True)
            exposure = bridge.submit(self._request(body={"observation": "x", "probability": 0.7}), session_token=bridge.session_token, freeze_confirmed=True)
            self.assertEqual(exposure["rejection_reason"], "PROHIBITED_EXPOSURE_FIELD")

        with tempfile.TemporaryDirectory() as root:
            bridge = LocalEvidenceBridge(root, signer=FixtureEd25519Signer(), service_build_hash="BUILD-1", candidate_test_mode=True)
            bridge.submit(self._request(), session_token=bridge.session_token, freeze_confirmed=True)
            with self.assertRaisesRegex(EvidenceBridgeError, "same evidence body"):
                bridge.submit(self._request(request_id="REQ-2", sequence=2, nonce="N-2"), session_token=bridge.session_token, freeze_confirmed=True)


if __name__ == "__main__":
    unittest.main()
