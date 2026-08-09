import copy
import hashlib
import json
from pathlib import Path
import unittest

ROOT = Path(__file__).resolve().parents[4]
MANIFEST = ROOT / "registries/implementation/c2e_v0_2/run_authority/C2E2_SOURCE_RUN_MANIFEST_JUNE_v0_1.json"
AUTH = ROOT / "registries/implementation/c2e_v0_2/run_authority/C2E2_SOURCE_REPLAY_AUTHORITY_REGISTRY_v0_1.json"
PACK = ROOT / "registries/opt_b/c2e/v0_2/C2E_EMPIRICAL_BOUNDARY_PACK_JUNE_v0_1.json"
ENVELOPE = ROOT / "registries/implementation/c2e_v0_2/run_authority/C2E2_EXACT_RESOURCE_ENVELOPE_JUNE_v0_1.json"
DECISION = ROOT / "docs/releases/c2e-causal-episode-v0-2/c2e2-g6-supersession-20260809/C2E2_G6_RUN_AUTH_OPERATOR_PASS_SUPERSESSION.json"
QA = ROOT / "docs/releases/c2e-causal-episode-v0-2/c2e2-g6-supersession-20260809/C2E2_G6_RUN_AUTH_QA_PACKET.json"
STATE = ROOT / "registries/implementation/c2e_v0_2/OVC_C2E2_STATE_v0_22.json"
POINTER = ROOT / "registries/implementation/c2e_v0_2/CURRENT_STATE_POINTER.json"
HISTORICAL_DEFER = ROOT / "docs/releases/c2e-causal-episode-v0-2/c2e2-g6/C2E2_G6_RUN_AUTH_OPERATOR_DECISION.json"
HISTORICAL_AG0 = ROOT / "docs/releases/c2e-causal-episode-v0-2/c2e-ag0/C2E_AG0_OPERATOR_DECISION.json"


def logical_hash(value):
    body = copy.deepcopy(value)
    body.pop("logical_sha256", None)
    return hashlib.sha256(json.dumps(body, sort_keys=True, separators=(",", ":"), ensure_ascii=False, allow_nan=False).encode()).hexdigest()


class C2E2G6RunAuthSupersessionTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.manifest = json.loads(MANIFEST.read_text())
        cls.registry = json.loads(AUTH.read_text())
        cls.token = cls.registry["tokens"][0]
        cls.pack = json.loads(PACK.read_text())
        cls.envelope = json.loads(ENVELOPE.read_text())
        cls.decision = json.loads(DECISION.read_text())
        cls.qa = json.loads(QA.read_text())
        cls.state = json.loads(STATE.read_text())
        cls.pointer = json.loads(POINTER.read_text())

    def test_operator_pass_is_exact_and_preserves_reserved_boundaries(self):
        command = "OVC APPROVE C2E2-G6-RUN-AUTH PASS, CONTINUE THROUGH WP6, OPERATOR APPROVAL TO AUTO-COMPLETE/RATIFY ALL REMAINING OBJECTS TO PROGRAMME COMPLETION"
        self.assertEqual(self.decision["operator_command"], command)
        self.assertEqual(self.decision["decision"], "PASS")
        self.assertEqual(self.decision["normalized_run_authority_disposition"], "AUTHORIZE_EXACT_RUN")
        delta = self.decision["authority_delta"]
        self.assertEqual(delta["wp6_execution"], "AUTHORIZED_ONE_EXACT_SINGLE_USE_SHADOW_REAL_SOURCE_REPLAY")
        self.assertEqual(delta["active_c2e"], "NONE")
        self.assertEqual(delta["active_boundary_pack"], "NONE")
        self.assertEqual(delta["c2e_ag0_ag1_ag2_ag3_auto_ratification"], "DENIED_OPERATOR_RESERVED")
        self.assertEqual(delta["validation_consumption"], "DENIED")

    def test_exact_manifest_reconstructs_and_binds_all_prerequisites(self):
        self.assertEqual(logical_hash(self.manifest), self.manifest["logical_sha256"])
        self.assertEqual(self.manifest["run_manifest_id"], "C2E2.WP6.JUNE.EXACT.v1")
        self.assertEqual(self.manifest["boundary_pack"]["logical_sha256"], self.pack["logical_sha256"])
        self.assertEqual(self.manifest["resource_envelope"]["logical_sha256"], self.envelope["logical_sha256"])
        source = self.manifest["source_population"]
        self.assertEqual(source["input_binding_sha256"], "126a703b89bfef8fc60a4beb1248b20b424621334c8fff254c122555e44663f8")
        self.assertEqual(source["logical_population_sha256"], "3f1089e3a4eefe94147c8c2f912e77899e4ed21fe8b3b8b85993e47bf7151ee7")
        self.assertEqual(source["counts"], {"requested":33320,"computable":27996,"censored":1638,"not_evaluable":3686})
        self.assertEqual(len(self.manifest["raw_source_objects"]), 4)
        self.assertEqual(self.manifest["execution_requirements"]["provider_intake"], "NONE")
        self.assertEqual(self.manifest["execution_requirements"]["validation_consumption"], "NONE")

    def test_token_is_single_use_exact_and_unconsumed(self):
        self.assertEqual(logical_hash(self.token), self.token["logical_sha256"])
        self.assertTrue(self.token["single_use"])
        self.assertTrue(self.token["reuse_prohibited"])
        self.assertFalse(self.token["consumed"])
        self.assertFalse(self.token["invalidated"])
        self.assertEqual(self.token["status"], "AUTHORIZED_UNCONSUMED")
        self.assertEqual(self.token["run_manifest_logical_sha256"], self.manifest["logical_sha256"])
        self.assertEqual(self.token["boundary_pack_logical_sha256"], self.pack["logical_sha256"])
        self.assertEqual(self.token["resource_envelope_logical_sha256"], self.envelope["logical_sha256"])
        self.assertEqual(self.token["reserved_post_wp6_authority"], "DENIED_OPERATOR_REQUIRED")

    def test_resource_envelope_is_exact_fail_closed_and_not_scientific_threshold(self):
        self.assertEqual(self.envelope["limits"], {"max_wall_clock_seconds":14400,"max_peak_rss_bytes":17179869184,"max_external_output_bytes":10737418240,"worker_count":1})
        self.assertEqual(self.envelope["capacity_semantics"]["on_exceed"], "CAPACITY_EXCEEDED_SAFE_STOP")
        self.assertEqual(self.manifest["execution_requirements"]["clean_run_count"], 2)
        self.assertTrue(self.manifest["execution_requirements"]["restart_equivalence_required"])
        self.assertTrue(self.manifest["execution_requirements"]["no_sampling_or_top_k_substitution"])

    def test_historical_defer_and_ag0_defer_are_preserved(self):
        self.assertTrue(HISTORICAL_DEFER.is_file())
        self.assertTrue(HISTORICAL_AG0.is_file())
        historical_g6 = json.loads(HISTORICAL_DEFER.read_text())
        historical_ag0 = json.loads(HISTORICAL_AG0.read_text())
        self.assertEqual(historical_g6["decision"], "DEFER")
        self.assertEqual(historical_ag0["decision"], "DEFER")
        self.assertIn("C2E2-G6-RUN-AUTH.OPERATOR.DEFER.20260808T194700+0100", self.decision["historical_decisions_preserved"])
        self.assertIn("C2E-AG0.OPERATOR.DEFER.20260808T205200+0100", self.decision["historical_decisions_preserved"])

    def test_state_and_pointer_authorize_only_wp6_shadow_run(self):
        self.assertIn(self.state["status"], {"QA_REVIEW", "APPROVED"})
        self.assertEqual(self.state["authority"]["active_boundary_pack"], "NONE")
        self.assertEqual(self.state["authority"]["c2e_activation"], "DENIED")
        self.assertIn(self.pointer["wp6_execution"], {"AUTHORIZED_PENDING_MERGE_ASSURANCE", "AUTHORIZED_NOT_STARTED"})
        self.assertEqual(self.pointer["active_c2e"], "NONE")
        self.assertEqual(self.pointer["active_boundary_pack"], "NONE")
        self.assertEqual(self.pointer["run_token_id"], self.token["token_id"])

    def test_qa_has_no_blocker_and_requires_exact_head_before_merge(self):
        self.assertEqual(self.qa["blocking_warnings"], [])
        self.assertEqual(self.qa["unresolved_issues"], [])
        self.assertIn(self.qa["qa_disposition"], {"PASS_PENDING_EXACT_HEAD_ASSURANCE", "PASS"})


if __name__ == "__main__":
    unittest.main()
