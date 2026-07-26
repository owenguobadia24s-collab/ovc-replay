from __future__ import annotations

import json
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[3]
GATE = ROOT / "docs/releases/opt-b-c1-v2/b1-g3/B1_G3_GATE_PACKET.json"
DECISION = ROOT / "docs/releases/opt-b-c1-v2/b1-g3/B1_G3_OPERATOR_DECISION.md"
RELEASES = ROOT / "registries/opt_b/c1/C1_RELEASE_REGISTRY.yaml"
SELECTORS = ROOT / "registries/opt_b/c1/C1_ACTIVE_SELECTORS.yaml"
WP5 = ROOT / "docs/releases/opt-b-c1-v2/wp5/WP5_REMOTE_VERIFICATION_RECEIPT.json"


class B1G3CandidateReleaseTests(unittest.TestCase):
    def test_gate_reconciles_exact_candidate_release_evidence(self) -> None:
        gate = json.loads(GATE.read_text(encoding="utf-8"))
        self.assertEqual(gate["gate_id"], "B1-G3")
        self.assertEqual(
            gate["decision"],
            "PASS_EXISTING_CANDIDATE_RELEASE_RECONCILED_NO_AUTHORITY_REGRESSION",
        )
        self.assertEqual(gate["totals"]["record_count"], 212764)
        self.assertEqual(gate["totals"]["record_file_count"], 192)
        self.assertEqual(gate["totals"]["verified_payload_bytes"], 36170710)
        self.assertEqual(gate["totals"]["duplicate_record_ids"], 0)

    def test_exact_release_and_parent_manifest_hashes_are_bound(self) -> None:
        gate = json.loads(GATE.read_text(encoding="utf-8"))
        self.assertEqual(
            gate["releases"]["DISCOVERY"]["manifest_sha256"],
            "6abd6d1fb74e7f3797e9add2435eaa5e487b612efd2f4b5f4f4c59679820d5d2",
        )
        self.assertEqual(
            gate["releases"]["DEVELOPMENT"]["manifest_sha256"],
            "ca83f2d9d948be426f3d80ebc91cc981f92546dfdd07268d71938d618c51f017",
        )
        self.assertEqual(
            gate["parent_opt_a_releases"]["DISCOVERY"]["manifest_sha256"],
            "0cbcafa9421449574b61bfeec24f634de99cbbbc6e7a53d09ace8f702182ab8c",
        )
        self.assertEqual(
            gate["parent_opt_a_releases"]["DEVELOPMENT"]["manifest_sha256"],
            "25e1be8a7edb0e96017c45bf35f4e788345f94b22a8ed9bb0874c86338ba64cc",
        )

    def test_historical_gate_is_preserved_after_later_shadow_activation(self) -> None:
        gate = json.loads(GATE.read_text(encoding="utf-8"))
        releases = RELEASES.read_text(encoding="utf-8")
        selectors = SELECTORS.read_text(encoding="utf-8")
        wp5 = json.loads(WP5.read_text(encoding="utf-8"))
        self.assertEqual(gate["execution_mode"], "RETROSPECTIVE_GATE_RECONCILIATION_AFTER_PUBLICATION")
        self.assertEqual(wp5["status"], "PASS_FULL_REMOTE_BYTE_VERIFICATION")
        self.assertEqual(gate["authority_delta"]["selector_activation"], "NONE")
        self.assertEqual(gate["authority_delta"]["validation_consumption"], "LOCKED_UNCONSUMED")
        self.assertEqual(
            gate["authority_delta"]["c2_consumption"],
            "DENIED_PENDING_SEPARATE_HANDOFF_REVIEW",
        )
        self.assertEqual(releases.count("authority_state: SHADOW"), 2)
        self.assertEqual(releases.count("publication_status: PUBLISHED_REMOTE_VERIFIED"), 2)
        self.assertIn("state: SHADOW", selectors)
        self.assertEqual(selectors.count("selector_state: SHADOW"), 2)
        self.assertEqual(selectors.count("selector_state: NONE"), 1)

    def test_operator_decision_names_sequence_and_next_gate(self) -> None:
        decision = DECISION.read_text(encoding="utf-8")
        self.assertIn("PASS — existing exact candidate releases reconciled", decision)
        self.assertIn("WP4 replay", decision)
        self.assertIn("WP4F durable freeze", decision)
        self.assertIn("B1-G5 Shadow activation", decision)


if __name__ == "__main__":
    unittest.main()
