import json
from pathlib import Path
import unittest

ROOT = Path(__file__).resolve().parents[4]
BASE = ROOT / "docs/releases/c2e-causal-episode-v0-2/c2e2-g6-supersession-20260808"
PREFLIGHT = BASE / "C2E2_G6_JUNE_SUPERSESSION_PREFLIGHT.json"
REQUEST = BASE / "C2E2_G6_JUNE_OPERATOR_PASS_REQUEST.json"
QA = BASE / "C2E2_G6_JUNE_BLOCKER_QA_PACKET.json"
STATE = ROOT / "registries/implementation/c2e_v0_2/OVC_C2E2_STATE_v0_20.json"
POINTER = ROOT / "registries/implementation/c2e_v0_2/CURRENT_STATE_POINTER.json"
HISTORICAL_G6 = ROOT / "docs/releases/c2e-causal-episode-v0-2/c2e2-g6/C2E2_G6_RUN_AUTH_OPERATOR_DECISION.json"


class C2E2G6JuneSupersessionBlockTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.preflight = json.loads(PREFLIGHT.read_text())
        cls.request = json.loads(REQUEST.read_text())
        cls.qa = json.loads(QA.read_text())
        cls.state = json.loads(STATE.read_text())
        cls.pointer = json.loads(POINTER.read_text())
        cls.historical_g6 = json.loads(HISTORICAL_G6.read_text())

    def test_operator_pass_request_is_append_only_and_historical_defer_survives(self):
        self.assertEqual(self.request["gate_id"], "C2E2-G6-RUN-AUTH")
        self.assertEqual(self.request["decision_effect"], "REQUEST_RECORDED_PENDING_FAIL_CLOSED_PREREQUISITE_EVALUATION")
        self.assertIn(self.historical_g6["decision_id"], self.request["historical_decisions_preserved"])
        self.assertEqual(self.historical_g6["decision"], "DEFER")

    def test_exact_june_revised_c2_source_and_readability_are_bound(self):
        source = self.preflight["source_population"]
        self.assertEqual(source["status"], "PASS_FROZEN_AND_IDENTIFIED")
        self.assertEqual(source["c2_package_id"], "C2AR.INTEGRATED.SHADOW.PACKAGE.v1")
        self.assertEqual(source["c2_package_sha256"], "150de1997be8801baa59db6d0fe98b11cb21a6b70525b908537aeb31bfd00cc3")
        self.assertEqual(source["input_binding_sha256"], "126a703b89bfef8fc60a4beb1248b20b424621334c8fff254c122555e44663f8")
        self.assertEqual(source["logical_population_sha256"], "3f1089e3a4eefe94147c8c2f912e77899e4ed21fe8b3b8b85993e47bf7151ee7")
        self.assertEqual(source["source_manifest_sha256"], "1578b555f3d5aa2822b603141261f86a047096030e5faacd4380ef2c6d4f52e3")
        self.assertEqual(source["requested_records"], 33320)
        self.assertEqual(self.preflight["external_payload_readability"]["status"], "PASS_VERIFIED_READ_ONLY")
        self.assertEqual(self.preflight["c2e_input_surface"]["required_missing"], 0)

    def test_missing_empirical_pack_and_exact_resource_envelope_block_before_run(self):
        blockers = set(self.preflight["blocking_reason_codes"])
        self.assertEqual(self.preflight["preflight_result"], "BLOCK_PRE_RUN")
        self.assertEqual(self.preflight["empirical_boundary_pack"]["eligible_pack_ids"], [])
        self.assertEqual(self.preflight["empirical_boundary_pack"]["status"], "FAIL_MISSING_PREREGISTERED_EMPIRICAL_PACK")
        self.assertEqual(self.preflight["c2e_resource_envelope"]["status"], "FAIL_OPERATOR_ENVELOPE_NOT_EXACTLY_SPECIFIED")
        self.assertIn("EMPIRICAL_BOUNDARY_PACK_NOT_AVAILABLE_UNDER_SEPARATE_PREREG_AUTHORITY", blockers)
        self.assertIn("EXACT_C2E_RESOURCE_ENVELOPE_UNSPECIFIED", blockers)
        self.assertIsNone(self.preflight["run_token"])
        self.assertEqual(self.preflight["wp6_execution"], "NOT_STARTED")

    def test_qa_is_block_and_no_reserved_authority_is_granted(self):
        self.assertEqual(self.qa["qa_disposition"], "BLOCK")
        self.assertFalse(self.qa["correctable_inside_current_packet"])
        self.assertIsNone(self.qa["run_token"])
        self.assertEqual(self.qa["authority_delta"], "NONE")
        self.assertEqual(self.state["status"], "BLOCKED")
        self.assertEqual(self.state["effective_gate_state"], "BLOCKED_PREREQUISITES_UNSATISFIED")
        self.assertEqual(self.state["authority"]["wp6_execution"], "DENIED_NOT_STARTED")
        self.assertEqual(self.state["authority"]["active_boundary_pack"], "NONE")
        self.assertEqual(self.pointer["status"], "BLOCKED")
        self.assertIsNone(self.pointer["run_token"])
        self.assertEqual(self.pointer["active_c2e"], "NONE")
        self.assertEqual(self.pointer["active_boundary_pack"], "NONE")

    def test_no_raw_market_data_is_committed_by_preflight(self):
        self.assertFalse(self.preflight["raw_market_data_committed"])
        self.assertEqual(self.preflight["provider_intake"], "NONE")
        self.assertEqual(self.preflight["validation_consumption"], "NONE")


if __name__ == "__main__":
    unittest.main()
