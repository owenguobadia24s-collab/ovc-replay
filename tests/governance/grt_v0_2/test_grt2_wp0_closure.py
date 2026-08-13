from __future__ import annotations

import json
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[3]
WP0 = ROOT / "docs/programmes/grt-v0-2/wp0"
STATE_ROOT = ROOT / "registries/implementation/grt_v0_2"


class GRT2WP0ClosureEvidenceTests(unittest.TestCase):
    def test_exact_b0_receipt(self) -> None:
        receipt = json.loads((WP0 / "GRT2_B0_REPRODUCTION_RECEIPT.json").read_text(encoding="utf-8"))
        self.assertEqual(receipt["reproduction"], "PASS_EXACT")
        self.assertEqual(receipt["source_commit"], "100b3fa342c5dee7c96a7a4e5af9e80dac3ddfe4")
        self.assertEqual(receipt["source_tree"], "91374c54bde0e0b61ac51705f6434d4f2b0d8417")
        self.assertEqual(receipt["topology_sha256"], "4120468ecb1c1f484ab073c851287706f4fb45ad0e99fc355b4624094bb795f2")
        self.assertEqual(receipt["raw_warning_count"], 569)
        self.assertEqual(receipt["anomaly_count"], 1364)
        self.assertEqual(receipt["member_records"]["count"], 569)
        self.assertEqual(receipt["member_records"]["unique_anomaly_ids"], 569)
        self.assertEqual(receipt["member_records"]["unique_payload_hashes"], 569)
        self.assertEqual(
            receipt["member_records"]["membership_sha256"],
            "3587c224c07360751923e5718c5bedb432ce4a5c8cccd4061f73dd53ef07de5d",
        )
        self.assertEqual(sum(receipt["warning_category_counts"].values()), 569)
        self.assertEqual(receipt["determinism"]["result"], "PASS")
        self.assertEqual(
            receipt["artifact"]["file_sha256"],
            "88abf0dcb9cceeb0299d354d8a19804c6bbee3bbfdc38f8ef3847402d1c97e5f",
        )

    def test_current_census_is_observation_only(self) -> None:
        receipt = json.loads((WP0 / "GRT2_CURRENT_DEBT_CENSUS_RECEIPT.json").read_text(encoding="utf-8"))
        self.assertEqual(receipt["baseline_commit"], "d392c4572e539a399e461212b4991db55ae46477")
        self.assertEqual(receipt["baseline_tree"], "dc0fe43b365ae669544759a6a2227ca059736395")
        self.assertEqual(receipt["topology_sha256"], "9dbd7ad006d5cb2715ad2e5df1f64e50e5698e9bfd7282493de7fda1fcdeb029")
        self.assertEqual(receipt["raw_warning_count"], 588)
        self.assertEqual(receipt["anomaly_count"], 1456)
        self.assertEqual(sum(receipt["warning_category_counts"].values()), 588)
        self.assertEqual(receipt["lineage_classification"]["status"], "DEFERRED_TO_GRT2_WP2")
        self.assertEqual(receipt["transition_debt_status"], "NOT_EVALUATED_AT_WP0")
        self.assertEqual(receipt["gate_effect"], "NOT_A_GRT2_G1_PASS_DENOMINATOR")
        self.assertEqual(
            receipt["artifact"]["file_sha256"],
            "7fc788e45c56d646dd2d3f2b4b5fd6b7421c326261fffa2feeab38ea7b16cb5b",
        )

    def test_g1_decision_and_qa_are_non_enforcing_pass(self) -> None:
        qa = json.loads((WP0 / "GRT2_WP0_QA_PACKET.json").read_text(encoding="utf-8"))
        gate = json.loads((WP0 / "GRT2_G1_GATE_PACKET.json").read_text(encoding="utf-8"))
        decision = json.loads((WP0 / "GRT2_G1_DECISION.json").read_text(encoding="utf-8"))
        self.assertEqual(qa["qa_recommendation"], "PASS")
        self.assertEqual(qa["blockers"], [])
        self.assertEqual(gate["authority_classification"], "AUTO_RATIFIABLE")
        self.assertEqual(gate["decision"], "PASS")
        self.assertEqual(gate["unresolved_issues"], [])
        self.assertEqual(gate["current_authority"]["constitution"], "INACTIVE")
        self.assertEqual(gate["current_authority"]["enforcement"], "NONE")
        self.assertEqual(
            gate["changed_files"]["write_domains"],
            [
                "docs/programmes/grt-v0-2/wp0",
                "registries/implementation/grt_v0_2",
                "src/ovc/programme_genesis/grt_v0_2",
                "scripts/governance/grt_v0_2",
                "tests/governance/grt_v0_2",
                "tests/authority/test_active_namespace_allowlist.py",
            ],
        )
        self.assertEqual(decision["decision"], "PASS")
        self.assertEqual(decision["reserved_authority_delta"], "NONE")
        self.assertEqual(decision["next_packet"], "GRT2-WP1")

    def test_programme_state_is_approved_without_merge_claim(self) -> None:
        state = json.loads((STATE_ROOT / "OVC_GRT2_STATE_v0_1.json").read_text(encoding="utf-8"))
        pointer = json.loads((STATE_ROOT / "CURRENT_STATE_POINTER.json").read_text(encoding="utf-8"))
        self.assertEqual(state["status"], "APPROVED")
        self.assertEqual(state["packet_id"], "GRT2-WP0")
        self.assertEqual(state["gate_id"], "GRT2-G1")
        self.assertEqual(state["opening_b0_reproduced_members"], 569)
        self.assertEqual(state["active_enforcement"], "NONE")
        self.assertIsNone(state["merge_commit"])
        self.assertEqual(state["next_packet"], "GRT2-WP1")
        self.assertEqual(pointer["status"], "APPROVED")
        self.assertEqual(pointer["next_packet"], "GRT2-WP1")

    def test_temporary_exact_replay_hook_is_removed(self) -> None:
        workflow = (ROOT / ".github/workflows/tests.yml").read_text(encoding="utf-8")
        self.assertNotIn("GRT2 WP0 exact B0", workflow)
        self.assertNotIn("Fetch exact history required by GRT2 WP0", workflow)
        self.assertNotIn("grt2-wp0-reconciliation", workflow)
        self.assertIn("Complete repository suite", workflow)


if __name__ == "__main__":
    unittest.main()
