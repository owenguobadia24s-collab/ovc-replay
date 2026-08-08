import json
from pathlib import Path
import unittest

ROOT = Path(__file__).resolve().parents[4]
BASE = ROOT / "docs/releases/c2e-causal-episode-v0-2/c2e2-wp0"
SURVEY = BASE / "C2E2_C2_SOURCE_SURFACE_SURVEY_v0_1.json"
PREFLIGHT = BASE / "C2E2_WP0_PREFLIGHT.json"
PRS = BASE / "C2E2_WP0_OPEN_PR_INVENTORY.json"
MATRIX = BASE / "C2E2_WP0_SUPERSESSION_MATRIX.json"
QA = BASE / "C2E2_WP0_QA_PACKET.json"
STATE = ROOT / "registries/implementation/c2e_v0_2/OVC_C2E2_STATE_v0_2.json"
ACCEPTED_STATE = ROOT / "registries/implementation/c2e_v0_2/OVC_C2E2_STATE_v0_3.json"
POINTER = ROOT / "registries/implementation/c2e_v0_2/CURRENT_STATE_POINTER.json"
RO_C2E = ROOT / "registries/research_operations/c2e/OVC_C2E_PROGRAMME_STATE_v0_1.json"
C2AR = ROOT / "registries/opt_b/c2/vnext/C2_INTEGRATED_SHADOW_PACKAGE_APPROVED_v1.jsonc"


class C2E2WP0PreflightTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.survey = json.loads(SURVEY.read_text())
        cls.preflight = json.loads(PREFLIGHT.read_text())
        cls.prs = json.loads(PRS.read_text())
        cls.matrix = json.loads(MATRIX.read_text())
        cls.qa = json.loads(QA.read_text())
        cls.state = json.loads(STATE.read_text())
        cls.accepted_state = json.loads(ACCEPTED_STATE.read_text())
        cls.pointer = json.loads(POINTER.read_text())
        cls.ro = json.loads(RO_C2E.read_text())
        cls.c2ar = json.loads(C2AR.read_text())

    def test_exact_main_and_c2ar_binding(self):
        self.assertEqual(self.preflight["execution_time_main"], "496066204a147e661484e5d5edcfd6a6d84351f2")
        self.assertEqual(self.survey["c2ar_package_sha256"], "150de1997be8801baa59db6d0fe98b11cb21a6b70525b908537aeb31bfd00cc3")
        self.assertEqual(self.c2ar["package_sha256"], self.survey["c2ar_package_sha256"])
        self.assertEqual(self.c2ar["research_consumer_permission"], "READ_ONLY_SHADOW_RESEARCH_ONLY")
        self.assertFalse(self.c2ar["active"])
        self.assertFalse(self.c2ar["canonical"])

    def test_all_required_fields_are_direct_or_lawful_join(self):
        allowed = {"DIRECTLY_AVAILABLE", "AVAILABLE_BY_LAWFUL_JOIN"}
        required = [row for row in self.survey["fields"] if row["required"]]
        self.assertEqual(len(required), self.survey["summary"]["required_fields"])
        self.assertTrue(required)
        self.assertTrue(all(row["availability_disposition"] in allowed for row in required))
        self.assertEqual(self.survey["summary"]["required_missing"], 0)
        self.assertEqual(self.survey["summary"]["ambiguous_source"], 0)
        self.assertEqual(self.survey["summary"]["forbidden_derivation"], 0)
        for row in required:
            self.assertTrue((ROOT / row["physical_source"]).exists(), row["physical_source"])

    def test_four_structural_axes_and_quality_is_not_structural(self):
        names = {row["normative_field"] for row in self.survey["fields"]}
        self.assertTrue({"LOCATION", "MOTION", "ORGANISATION", "INTERACTION"}.issubset(names))
        self.assertNotIn("QUALITY", names)
        self.assertIn("technical_computability", names)
        self.assertIn("assurance_consumer_eligibility_authority", names)

    def test_no_reverse_dependency_is_admitted(self):
        forbidden = " ".join(self.survey["forbidden_sources_checked"])
        for token in ("FDI/C2G", "C2.5", "C3", "outcomes/future", "research queues"):
            self.assertIn(token, forbidden)
        self.assertEqual(self.preflight["sri_consumer_status"], "NO_REPOSITORY_AUTHORITATIVE_SRI_IMPLEMENTATION_CONTRACT_FOUND_AT_BASELINE")

    def test_historical_block_and_open_pr_ancestry_are_preserved(self):
        self.assertEqual(self.ro["status"], "BLOCKED")
        self.assertEqual(self.ro["current_gate"], "C2E-G1")
        self.assertTrue(all(not item["lawful_c2e2_base"] for item in self.prs["open_prs"]))
        self.assertEqual(self.matrix["historical_bytes_rewritten"], False)

    def test_wp0_predecision_and_accepted_lifecycle_preserve_source_replay_denial(self):
        self.assertEqual(self.state["status"], "QA_REVIEW")
        self.assertEqual(self.state["current_gate"], "C2E2-G1")
        self.assertEqual(self.accepted_state["status"], "READY")
        self.assertEqual(self.accepted_state["current_packet"], "C2E2-WP1")
        self.assertEqual(self.accepted_state["current_gate"], "C2E2-G2")
        self.assertEqual(self.qa["status"], "PASS")
        self.assertEqual(self.qa["recommendation"], "PASS")
        self.assertEqual(self.qa["blocking_warnings"], [])
        self.assertFalse(self.qa["assertions"]["real_source_replay_performed"])
        self.assertEqual(self.state["authority"]["real_source_replay"], "DENIED_PENDING_C2E2_G6_RUN_AUTH")
        self.assertEqual(self.accepted_state["authority"]["real_source_replay"], "DENIED_PENDING_C2E2_G6_RUN_AUTH")
        self.assertEqual(self.pointer["real_source_replay"], "DENIED_PENDING_C2E2_G6_RUN_AUTH")
        self.assertEqual(self.pointer["active_c2e"], "NONE")


if __name__ == "__main__":
    unittest.main()
