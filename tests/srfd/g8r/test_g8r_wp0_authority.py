from __future__ import annotations

import json
from pathlib import Path
import unittest


ROOT = Path(__file__).resolve().parents[3]
RELEASE = ROOT / "docs/releases/srfd-benchmark-v0-1/srfdi-g8r-wp0"
DECISION = RELEASE / "SRFDI_G8R_G0_OPERATOR_DECISION.json"
FREEZE = RELEASE / "SRFDI_G8R_WP0_AUTHORITY_FREEZE.json"
STATE = ROOT / "registries/implementation/srfd/OVC_SRFDI_G8R_STATE_v0_2.json"
PARENT = ROOT / "registries/implementation/srfd/OVC_SRFDI_STATE_v0_1.json"


class SRFDIG8RWP0AuthorityTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.decision = json.loads(DECISION.read_text(encoding="utf-8"))
        cls.freeze = json.loads(FREEZE.read_text(encoding="utf-8"))
        cls.state = json.loads(STATE.read_text(encoding="utf-8"))
        cls.parent = json.loads(PARENT.read_text(encoding="utf-8"))

    def test_operator_pass_is_exact_and_plan_bound(self) -> None:
        self.assertEqual("SRFDI-G8R-G0", self.decision["gate_id"])
        self.assertEqual("OVC APPROVE SRFDI-G8R-G0 PASS", self.decision["operator_command"])
        self.assertEqual("PASS", self.decision["decision"])
        self.assertEqual("d90432957df146bf448287cedf4da73a8c861ebe", self.decision["baseline_main"])
        self.assertEqual(
            "f1e6515f68a97ee50c5273cb13312622376ac9650c6cf7612c48c18588fb0408",
            self.decision["plan_artifact_sha256"],
        )

    def test_pass_is_compute_only_and_preserves_reserved_authority(self) -> None:
        self.assertEqual("DENIED", self.decision["june_benchmark"])
        self.assertEqual("LOCKED_UNCONSUMED", self.decision["validation_2025"])
        self.assertEqual("NONE", self.decision["method_selection"])
        self.assertEqual("PRESERVE_DO_NOT_MERGE", self.decision["pr_371"])
        self.assertIn("SRFDI-WP9", self.decision["not_authorised"])
        self.assertIn("2025 Validation access or consumption", self.decision["not_authorised"])

    def test_science_compute_firewall_blocks_semantic_change(self) -> None:
        firewall = self.freeze["science_compute_firewall"]
        self.assertEqual("POTENTIAL_SEMANTIC_CHANGE", firewall["blocking_change_class"])
        self.assertIn("COMPUTE_ONLY_EQUIVALENT", firewall["allowed_change_classes"])
        self.assertEqual("CURRENT_JSON_REFERENCE", self.freeze["reference_oracle"])
        self.assertEqual("UNADMITTED", self.freeze["candidate_numpy_backend"])

    def test_completed_wp0_routes_to_wp1_and_preserves_g2f_stop(self) -> None:
        self.assertEqual("RUNNING", self.state["status"])
        self.assertEqual("SRFDI-G8R-WP1", self.state["active_packet"])
        self.assertEqual("SRFDI-G8R-G1", self.state["current_gate"])
        wp0 = next(item for item in self.state["packets"] if item["packet_id"] == "SRFDI-G8R-WP0")
        self.assertEqual("COMPLETED", wp0["status"])
        self.assertIn("SRFDI-G8R-G2F", self.state["mandatory_operator_stops"])
        wp3 = next(item for item in self.state["packets"] if item["packet_id"] == "SRFDI-G8R-WP3")
        self.assertIn("G8R_G2F_NOT_ACKNOWLEDGED", wp3["blockers"])
        self.assertIn("SRFDI-G8R-G2F=ACKNOWLEDGE_CONTINUE", wp3["prerequisites"])

    def test_parent_g8_and_wp9_denial_remain_unchanged(self) -> None:
        self.assertEqual("REDESIGN_REQUIRED", self.parent["status"])
        self.assertEqual("DENIED", self.parent["authority"]["market_benchmark"])
        self.assertEqual("LOCKED_UNCONSUMED", self.parent["authority"]["validation_2025"])
        wp9 = next(item for item in self.parent["packets"] if item["packet_id"] == "SRFDI-WP9")
        self.assertIn("JUNE_BENCHMARK_DENIED", wp9["blockers"])


if __name__ == "__main__":
    unittest.main()
