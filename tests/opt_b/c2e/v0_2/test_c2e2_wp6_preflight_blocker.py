import json
from pathlib import Path
import unittest

ROOT = Path(__file__).resolve().parents[4]
BLOCKER = ROOT / "docs/releases/c2e-causal-episode-v0-2/c2e2-wp6/C2E2_WP6_PREFLIGHT_BLOCKER.json"
QA = ROOT / "docs/releases/c2e-causal-episode-v0-2/c2e2-wp6/C2E2_WP6_PREFLIGHT_QA_PACKET.json"
STATE = ROOT / "registries/implementation/c2e_v0_2/OVC_C2E2_STATE_v0_23.json"
POINTER = ROOT / "registries/implementation/c2e_v0_2/CURRENT_STATE_POINTER.json"
SURVEY = ROOT / "docs/releases/c2e-causal-episode-v0-2/c2e2-wp0/C2E2_C2_SOURCE_SURFACE_SURVEY_v0_1.json"
PACK = ROOT / "registries/opt_b/c2e/v0_2/C2E_EMPIRICAL_BOUNDARY_PACK_JUNE_v0_1.json"
MANIFEST = ROOT / "registries/implementation/c2e_v0_2/run_authority/C2E2_SOURCE_RUN_MANIFEST_JUNE_v0_1.json"
TOKEN_REGISTRY = ROOT / "registries/implementation/c2e_v0_2/run_authority/C2E2_SOURCE_REPLAY_AUTHORITY_REGISTRY_v0_1.json"

class C2E2WP6PreflightBlockerTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.blocker = json.loads(BLOCKER.read_text())
        cls.qa = json.loads(QA.read_text())
        cls.state = json.loads(STATE.read_text())
        cls.pointer = json.loads(POINTER.read_text())
        cls.survey = json.loads(SURVEY.read_text())
        cls.pack = json.loads(PACK.read_text())
        cls.manifest = json.loads(MANIFEST.read_text())
        cls.token = json.loads(TOKEN_REGISTRY.read_text())["tokens"][0]

    def test_bound_population_is_registered_sequence_window_population(self):
        upstream = self.blocker["upstream_population_evidence"]
        self.assertEqual(upstream["output_manifest_scope"]["opportunity_types"], ["REGISTERED_SEQUENCE_WINDOW"])
        self.assertEqual(upstream["output_manifest_scope"]["object_families"], ["AXIS_BUNDLE"])
        self.assertEqual(upstream["output_manifest_scope"]["sequence_lengths"], [2,3,4,5,6,8,12])
        self.assertEqual(upstream["scope_arithmetic"]["target_slot_total"], 4760)
        self.assertEqual(upstream["scope_arithmetic"]["request_total"], 33320)
        self.assertEqual(4760 * 7, 33320)
        self.assertEqual(self.manifest["source_population"]["counts"]["requested"], 33320)

    def test_c2e_contract_requires_base_observation_identity(self):
        self.assertIn("base C2 record identity is the deterministic C2 vNext observation_id", self.survey["binding_rule"])
        c2_record = next(row for row in self.survey["fields"] if row["normative_field"] == "c2_record_id")
        self.assertEqual(c2_record["join_key"], ["observation_id"])
        self.assertEqual(c2_record["source_record_identity"], "observation_id")
        for axis in ("LOCATION","MOTION","ORGANISATION","INTERACTION"):
            row = next(item for item in self.survey["fields"] if item["normative_field"] == axis)
            self.assertEqual(row["source_record_identity"], "profile_output_id")

    def test_authorized_pack_identity_is_population_scoped(self):
        logical = self.manifest["source_population"]["logical_population_sha256"]
        self.assertEqual(logical, "3f1089e3a4eefe94147c8c2f912e77899e4ed21fe8b3b8b85993e47bf7151ee7")
        self.assertEqual(self.pack["population_scope"]["logical_population_sha256"], logical)
        self.assertEqual(self.blocker["authorized_boundary_pack"]["population_scope_logical_sha256"], logical)

    def test_no_token_consumption_or_authority_widening(self):
        self.assertEqual(self.token["status"], "AUTHORIZED_UNCONSUMED")
        self.assertFalse(self.token["consumed"])
        self.assertFalse(self.token["invalidated"])
        self.assertFalse(self.blocker["run_executed"])
        self.assertFalse(self.blocker["token_consumed"])
        self.assertEqual(self.state["authority"]["wp6_execution"], "BLOCKED_NOT_STARTED")
        self.assertEqual(self.state["authority"]["c2e_activation"], "DENIED")
        self.assertEqual(self.pointer["active_c2e"], "NONE")
        self.assertEqual(self.pointer["active_boundary_pack"], "NONE")

    def test_qa_blocks_and_historical_gate_remains_preserved_after_supersession(self):
        self.assertEqual(self.qa["qa_disposition"], "BLOCK")
        self.assertIn("AUTHORIZED_POPULATION_UNIT_MISMATCH_C2_SEQUENCE_WINDOW_VS_C2_OBSERVATION", self.qa["blocking_warnings"])
        self.assertEqual(self.state["status"], "BLOCKED")
        self.assertTrue(self.state["operator_decision_required"])
        self.assertEqual(self.state["current_gate"], "C2E2-G6-BINDING-SUPERSESSION")
        self.assertIn(self.pointer["status"], {"BLOCKED", "APPROVED", "GATE_READY"})
        if self.pointer["status"] == "APPROVED":
            self.assertEqual(self.pointer["current_gate"], "C2E2-G6-BINDING-SUPERSESSION")
            self.assertEqual(self.pointer["operator_decision"], "SUPERSEDE")
        elif self.pointer["status"] == "GATE_READY":
            self.assertEqual(self.pointer["current_gate"], "C2E2-G6-SIGNATURE-CONTRACT-SUPERSESSION")
            self.assertTrue(self.pointer["operator_decision_required"])
            self.assertIn(
                "C2E2-G6-BINDING-SUPERSESSION.OPERATOR.SUPERSEDE.20260809T084300+0100",
                self.pointer["operator_decision_history"],
            )
        if self.pointer["status"] in {"APPROVED", "GATE_READY"}:
            self.assertEqual(self.pointer["wp6_execution"], "DENIED_UNTIL_FRESH_EXACT_C2E2_G6_RUN_AUTH_OPERATOR_DECISION")
            self.assertEqual(self.pointer["old_run_token_status"], "INVALIDATED_UNCONSUMED_BY_OPERATOR_SUPERSESSION")

if __name__ == "__main__":
    unittest.main()
