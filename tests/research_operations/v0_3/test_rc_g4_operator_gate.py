from __future__ import annotations

import json
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
PACKET = ROOT / "docs/releases/research-console-v0-3/rc-g4/RC_G4_C1_CONSUMPTION_OPERATOR_GATE_PACKET.json"
DECISION = ROOT / "docs/releases/research-console-v0-3/rc-g4/RC_G4_OPERATOR_DECISION.md"
STATE = ROOT / "registries/research_operations/v0_3/RO3_PROGRAMME_STATE_v0_1.json"
REGISTRY = ROOT / "registries/research_operations/v0_3/RO3_IMPLEMENTATION_REGISTRY_v0_1.yaml"
MERGE_RECEIPT = ROOT / "docs/releases/research-operations-foundation-v0-3/ro3-g4/RO3_G4_MERGE_RECEIPT.json"
ADAPTER = ROOT / "src/ovc/research_operations/v0_3/lineage_adapters.py"


class RCG4OperatorGateTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.packet = json.loads(PACKET.read_text(encoding="utf-8"))
        cls.state = json.loads(STATE.read_text(encoding="utf-8"))
        cls.receipt = json.loads(MERGE_RECEIPT.read_text(encoding="utf-8"))
        cls.registry_text = REGISTRY.read_text(encoding="utf-8")
        cls.adapter_text = ADAPTER.read_text(encoding="utf-8")
        cls.decision_text = DECISION.read_text(encoding="utf-8")

    def test_exact_ro3_g4_merge_and_operator_pass_identity(self) -> None:
        self.assertEqual(self.packet["gate_id"], "RC-G4")
        self.assertEqual(self.packet["owner"], "OPERATOR")
        self.assertEqual(self.packet["classification"], "OPERATOR_REQUIRED_NOT_AUTO_RATIFIABLE")
        self.assertEqual(self.packet["baseline_main_commit"], "80adf5cfb111a8b07788276c9867ff4fee32fb09")
        self.assertEqual(self.packet["ro3_g4"]["merge_commit"], self.receipt["merge_commit"])
        self.assertEqual(self.packet["ro3_g4"]["final_head"], self.receipt["final_head"])
        self.assertFalse(self.packet["operator_approval_required"])
        self.assertEqual(self.packet["status"], "APPROVED_PENDING_ACTIVATION")
        decision = self.packet["operator_decision"]
        self.assertEqual(decision["decision"], "PASS")
        self.assertEqual(decision["authority"], "OPERATOR")
        self.assertEqual(decision["instruction"], "@GitHub OVC APPROVE RC-G4 PASS")
        self.assertIn("Decision:** `PASS`", self.decision_text)
        self.assertIn("LOCAL_READ_ONLY_C1_PRESENTATION", self.decision_text)

    def test_schema_ids_and_blob_hashes_are_complete(self) -> None:
        schemas = self.packet["approved_projection_schemas"]
        self.assertEqual(len(schemas), 4)
        self.assertEqual(
            {item["object_id"] for item in schemas},
            {
                "RO3.C1LineageTrace.v1",
                "RO3.C1FormulaEvidenceCard.v1",
                "RO3.DownstreamTraceProjection.v1",
                "RO3.C1ConsoleProjection.v1",
            },
        )
        for item in schemas:
            self.assertRegex(item["git_blob_sha"], r"^[0-9a-f]{40}$")
            schema = json.loads((ROOT / item["path"]).read_text(encoding="utf-8"))
            self.assertEqual(schema["$id"], item["schema_id"])

    def test_gate_packet_and_ro3_adapter_remain_immutable_during_bounded_activation(self) -> None:
        current = self.packet["route_and_capability_delta"]["current"]
        approved = self.packet["route_and_capability_delta"]["approved_after_activation"]
        self.assertFalse(current["route_enabled"])
        self.assertEqual(current["route_state"], "DISABLED_PENDING_RC_G4_ACTIVATION")
        self.assertEqual(current["live_consumption_authority"], "APPROVED_PENDING_BOUNDED_ACTIVATION")
        self.assertTrue(approved["route_enabled"])
        self.assertEqual(approved["live_consumption_authority"], "LOCAL_READ_ONLY_C1_PRESENTATION")
        self.assertIn('LIVE_ROUTE_STATE = "DISABLED_PENDING_RC_G4"', self.adapter_text)
        self.assertIn('"route_enabled": False', self.adapter_text)
        self.assertTrue(
            "live_console_c1_route: ENABLED_LOCAL_READ_ONLY_IMPLEMENTATION_PENDING_QA" in self.registry_text
            or "live_console_c1_route: ENABLED_LOCAL_READ_ONLY" in self.registry_text
        )

    def test_required_rejections_and_permanent_banner_are_recorded(self) -> None:
        evidence = {item["condition"]: item["result"] for item in self.packet["acceptance_and_test_evidence"]}
        for condition in (
            "No-write projection enforcement",
            "Validation denied before path, object or record resolution",
            "Stale projection visible and route disabled",
            "C1 null reason and C2 transition compact co-render rejected",
            "Pre-RC-G4 route activation rejected",
            "Permanent downstream authority banner exact",
            "RC-G4 gate packet validation",
            "RC-G4 gate complete repository suite",
        ):
            self.assertEqual(evidence[condition], "PASS")
        self.assertEqual(
            self.packet["presentation_evidence"]["permanent_downstream_banner"],
            "DOWNSTREAM TRACE — READ ONLY. C2 AND PATTERN DISCOVERY AUTHORITY IS UNCHANGED.",
        )
        separation = self.packet["route_and_capability_delta"]["permanent_panel_separation"]
        self.assertEqual(separation["mixed_compact_object"], "DENIED")
        self.assertEqual(separation["c1_null_reason_and_c2_transition_compact_corender"], "DENIED")

    def test_reserved_authority_remains_absent(self) -> None:
        current = self.packet["current_authority"]
        self.assertEqual(current["validation_consumption"], "LOCKED_UNCONSUMED")
        self.assertEqual(current["c2_pattern_discovery_authority"], "UNCHANGED")
        self.assertEqual(current["r2_publication"], "DENIED")
        self.assertEqual(current["research_write_authority"], "DENIED_PENDING_SEPARATE_GATE")
        for key in ("repository_mutation", "market", "probability", "risk", "exposure", "trading", "execution", "agent_write"):
            self.assertEqual(current[key], "NONE")
        denied = "\n".join(self.packet["proposed_authority_delta"]["does_not_permit"])
        for phrase in ("Validation consumption", "R2 publication", "Probability, risk, exposure, trading, execution or agent-write authority"):
            self.assertIn(phrase, denied)

    def test_programme_state_lawfully_continues_through_bounded_activation(self) -> None:
        wp4 = next(item for item in self.state["packets"] if item["packet_id"] == "RO3-WP4")
        rcg4 = next(item for item in self.state["packets"] if item["packet_id"] == "RC-G4")
        activation = next(item for item in self.state["packets"] if item["packet_id"] == "RC-G4-ACTIVATION")
        self.assertIn(self.state["programme_status"], {"RUNNING", "APPROVED_PENDING_MERGE", "COMPLETED"})
        self.assertEqual(wp4["status"], "COMPLETED")
        self.assertEqual(wp4["merge_commit"], "80adf5cfb111a8b07788276c9867ff4fee32fb09")
        self.assertEqual(rcg4["status"], "COMPLETED")
        self.assertEqual(rcg4["authority_required"], "OPERATOR_REQUIRED_NOT_AUTO_RATIFIABLE")
        self.assertFalse(rcg4["operator_approval_required"])
        self.assertEqual(rcg4["decision"], "PASS")
        self.assertEqual(rcg4["decision_merge_commit"], "19066a5201e33a51b0e785dbdc932999f39fd9da")
        self.assertIn(
            rcg4["live_route_current_state"],
            {"ENABLED_LOCAL_READ_ONLY_IMPLEMENTATION_PENDING_QA", "ENABLED_LOCAL_READ_ONLY"},
        )
        self.assertIn(activation["status"], {"RUNNING", "APPROVED", "COMPLETED"})
        self.assertEqual(activation["baseline_commit"], "19066a5201e33a51b0e785dbdc932999f39fd9da")
        self.assertEqual(activation["authority_delta"], "LOCAL_READ_ONLY_C1_PRESENTATION")
        self.assertEqual(activation["authority_required"], "AUTO_EXECUTABLE_WITHIN_OPERATOR_APPROVED_DELTA")


if __name__ == "__main__":
    unittest.main()
