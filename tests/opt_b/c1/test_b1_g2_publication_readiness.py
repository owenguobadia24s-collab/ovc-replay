from __future__ import annotations

import json
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
GATE = ROOT / "docs/releases/opt-b-c1-v2/b1-g2/B1_G2_GATE_PACKET.json"
DECISION = ROOT / "docs/releases/opt-b-c1-v2/b1-g2/B1_G2_OPERATOR_DECISION.md"
WORKFLOW = ROOT / ".github/workflows/opt-b-c1-b1-g2-publication-readiness.yml"
VERIFIER = ROOT / "scripts/opt_b/review_c1_b1_g2_release.py"
AUTHORITY = ROOT / "registries/authority/ACTIVE_AUTHORITY.yaml"
IMPLEMENTATION = ROOT / "registries/opt_b/c1/C1_IMPLEMENTATION_REGISTRY.yaml"
RELEASES = ROOT / "registries/opt_b/c1/C1_RELEASE_REGISTRY.yaml"
STATUS = ROOT / "docs/CURRENT_STATUS.md"


class B1G2PublicationReadinessTests(unittest.TestCase):
    def test_exact_frozen_release_identities_are_bound(self) -> None:
        gate = json.loads(GATE.read_text(encoding="utf-8"))
        self.assertEqual(
            gate["decision"],
            "PASS_EXACT_FROZEN_RELEASES_PUBLICATION_READY_WP5_AUTHORISED",
        )
        self.assertEqual(gate["source_execution"]["workflow_run_id"], 30187276514)
        self.assertEqual(gate["totals"]["record_file_count"], 192)
        self.assertEqual(gate["totals"]["record_count"], 212764)
        self.assertEqual(gate["totals"]["verified_payload_bytes"], 36170710)
        self.assertEqual(
            gate["accepted_releases"]["DISCOVERY"]["manifest_sha256"],
            "6abd6d1fb74e7f3797e9add2435eaa5e487b612efd2f4b5f4f4c59679820d5d2",
        )
        self.assertEqual(
            gate["accepted_releases"]["DEVELOPMENT"]["manifest_sha256"],
            "ca83f2d9d948be426f3d80ebc91cc981f92546dfdd07268d71938d618c51f017",
        )

    def test_authority_changes_only_publication_readiness(self) -> None:
        gate = json.loads(GATE.read_text(encoding="utf-8"))
        authority = gate["authority_delta"]
        self.assertEqual(
            authority["wp5_r2_publication"],
            "AUTHORISED_EXACT_DISCOVERY_AND_DEVELOPMENT_RELEASES_ONLY",
        )
        self.assertEqual(authority["selector_activation"], "DENIED_PENDING_POST_PUBLICATION_REVIEW")
        self.assertEqual(authority["c2_consumption"], "DENIED_PENDING_SEPARATE_HANDOFF_REVIEW")
        self.assertEqual(authority["validation_consumption"], "LOCKED_UNCONSUMED")
        for key in ("probability", "exposure", "trading", "execution"):
            self.assertEqual(authority[key], "NONE")

    def test_workflow_is_non_mutating_and_reproducible(self) -> None:
        workflow = WORKFLOW.read_text(encoding="utf-8")
        self.assertIn("run-id: 30187276514", workflow)
        self.assertIn("rclone lsf --recursive", workflow)
        for command in ("copy", "sync", "delete"):
            self.assertNotIn(f"rclone {command}", workflow)
        self.assertIn("review_c1_b1_g2_release.py", workflow)
        verifier = VERIFIER.read_text(encoding="utf-8")
        self.assertIn("unmanifested or missing release files", verifier)
        self.assertIn("PASS_ABSENT", verifier)

    def test_repository_court_record_preserves_gate_and_records_wp5_successor(self) -> None:
        authority = AUTHORITY.read_text(encoding="utf-8")
        implementation = IMPLEMENTATION.read_text(encoding="utf-8")
        releases = RELEASES.read_text(encoding="utf-8")
        status = STATUS.read_text(encoding="utf-8")
        decision = DECISION.read_text(encoding="utf-8")
        self.assertIn("C1_WP5_PASS_REMOTE_VERIFIED_PENDING_B1_G4_NO_SELECTOR", authority)
        self.assertIn("work_packet: B1-G2", implementation)
        self.assertIn("next_gate: WP5_R2_PUBLICATION_AND_FULL_REMOTE_VERIFICATION", implementation)
        self.assertIn("status: WP5_PASS_REMOTE_VERIFIED_PENDING_B1_G4_REVIEW", releases)
        self.assertIn("B1-G2 result", status)
        self.assertIn("C1 selectors remain `NONE`", decision)


if __name__ == "__main__":
    unittest.main()
