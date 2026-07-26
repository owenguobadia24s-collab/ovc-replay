from __future__ import annotations

import hashlib
import json
import unittest
from pathlib import Path

from ovc.opt_b.c1 import AUTHORITY_STATE

ROOT = Path(__file__).resolve().parents[3]
GATE = ROOT / "docs" / "releases" / "opt-b-c1-v2" / "b1-g1" / "B1_G1_GATE_PACKET.json"
RECEIPT = ROOT / "docs" / "releases" / "opt-b-c1-v2" / "b1-g1" / "B1_G1_VERIFICATION_RECEIPT.json"
DECISION = ROOT / "docs" / "releases" / "opt-b-c1-v2" / "b1-g1" / "B1_G1_OPERATOR_DECISION.md"
AUTHORITY = ROOT / "registries" / "authority" / "ACTIVE_AUTHORITY.yaml"
RELEASES = ROOT / "registries" / "opt_b" / "c1" / "C1_RELEASE_REGISTRY.yaml"
IMPLEMENTATION = ROOT / "registries" / "opt_b" / "c1" / "C1_IMPLEMENTATION_REGISTRY.yaml"


class C1B1G1CandidateFreezeReviewTests(unittest.TestCase):
    def test_exact_gate_packet_and_receipt_are_bound(self) -> None:
        packet = json.loads(GATE.read_text(encoding="utf-8"))
        receipt_bytes = RECEIPT.read_bytes()
        receipt = json.loads(receipt_bytes)
        self.assertEqual(packet["decision"], "PASS_EXACT_CANDIDATE_INVENTORY_ACCEPTED_FREEZE_AUTHORISED")
        self.assertEqual(packet["source_execution"]["candidate_artifact_id"], 8626942276)
        self.assertEqual(packet["source_execution"]["candidate_archive_sha256"], receipt["archive_sha256"])
        self.assertEqual(packet["embedded_evidence"]["inventory_sha256"], receipt["inventory_sha256"])
        self.assertEqual(hashlib.sha256(receipt_bytes).hexdigest(), packet["embedded_evidence"]["verification_receipt_sha256"])
        self.assertEqual(receipt["status"], "PASS")

    def test_complete_inventory_and_record_identity_review_passed(self) -> None:
        receipt = json.loads(RECEIPT.read_text(encoding="utf-8"))
        self.assertEqual(receipt["verified_file_count"], 192)
        self.assertEqual(receipt["verified_payload_bytes"], 36169581)
        self.assertEqual(receipt["verified_record_count"], 212764)
        self.assertEqual(receipt["unique_record_ids"], 212764)
        self.assertEqual(receipt["duplicate_record_ids"], 0)
        self.assertEqual(sum(receipt["role_clock_side_counts"].values()), 212764)

    def test_historical_freeze_authority_remains_bounded(self) -> None:
        packet = json.loads(GATE.read_text(encoding="utf-8"))
        delta = packet["authority_delta"]
        self.assertEqual(delta["local_freeze"], "AUTHORISED_EXACT_CANDIDATE_ONLY")
        self.assertEqual(delta["authorised_command"], "c1 freeze-release")
        self.assertEqual(len(delta["release_ids"]), 2)
        self.assertIn("NOT_YET_FROZEN", delta["release_state_after_this_gate"])
        self.assertEqual(delta["r2_publication"], "DENIED_PENDING_SEPARATE_WP5_APPROVAL")
        self.assertEqual(delta["selector_activation"], "NONE")
        self.assertEqual(delta["c2_consumption"], "DENIED_PENDING_SEPARATE_HANDOFF_REVIEW")

    def test_current_registries_show_lawful_progression_beyond_b1_g1(self) -> None:
        authority = AUTHORITY.read_text(encoding="utf-8")
        releases = RELEASES.read_text(encoding="utf-8")
        implementation = IMPLEMENTATION.read_text(encoding="utf-8")
        self.assertEqual(AUTHORITY_STATE, "B1_G2_PUBLICATION_READY_WP5_AUTHORISED")
        self.assertIn("state: C1_B1_G2_PASS_PUBLICATION_READY_WP5_AUTHORISED_NO_SELECTOR", authority)
        self.assertIn("release_freeze: COMPLETE_WP4F_PASS", authority)
        self.assertIn("status: B1_G2_PASS_PUBLICATION_READY", releases)
        self.assertEqual(releases.count("authority_state: CANDIDATE"), 2)
        self.assertEqual(releases.count("active_selector: false"), 3)
        self.assertIn("status: B1_G2_PASS_PUBLICATION_READY_WP5_AUTHORISED", implementation)
        for text in (authority, releases, implementation):
            self.assertIn("LOCKED_UNCONSUMED", text)
        self.assertIn("selector: NONE", authority)
        self.assertIn("c2_consumption: DENIED_PENDING_SEPARATE_HANDOFF_REVIEW", authority)

    def test_operator_decision_names_rollback_and_next_packet(self) -> None:
        decision = DECISION.read_text(encoding="utf-8")
        self.assertIn("PASS — EXACT WP4 CANDIDATE INVENTORY ACCEPTED", decision)
        self.assertIn("Any failed freeze attempt is discarded in full", decision)
        self.assertIn("WP4F — durable local release freeze", decision)


if __name__ == "__main__":
    unittest.main()
