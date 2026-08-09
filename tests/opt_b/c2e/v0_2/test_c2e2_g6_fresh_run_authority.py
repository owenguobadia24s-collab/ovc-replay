import copy
import hashlib
import json
from pathlib import Path
import unittest

from ovc.opt_b.c2e_v2.boundary_pack import freeze_pack

ROOT = Path(__file__).resolve().parents[4]
BASE = ROOT / "registries/implementation/c2e_v0_2"
RUN_AUTH = BASE / "run_authority"
DECISION = ROOT / "docs/releases/c2e-causal-episode-v0-2/c2e2-wp6/C2E2_G6_RUN_AUTH_OPERATOR_DECISION.json"
TOKEN = RUN_AUTH / "C2E2_G6_RUN_AUTH_TOKEN_v0_2.json"
AUTH_REGISTRY = RUN_AUTH / "C2E2_SOURCE_REPLAY_AUTHORITY_REGISTRY_v0_2.json"
MANIFEST = RUN_AUTH / "C2E2_SOURCE_RUN_MANIFEST_JUNE_OBSERVATION_v0_2.json"
ENVELOPE = RUN_AUTH / "C2E2_RESOURCE_ENVELOPE_JUNE_OBSERVATION_v0_2.json"
PACK = ROOT / "registries/opt_b/c2e/v0_2/C2E_EMPIRICAL_BOUNDARY_PACK_JUNE_STABLE_v0_2.json"
STATE = BASE / "OVC_C2E2_STATE_v0_28.json"
POINTER = BASE / "CURRENT_STATE_POINTER.json"

def logical_hash(value):
    body = copy.deepcopy(value)
    body.pop("logical_sha256", None)
    return hashlib.sha256(
        json.dumps(body, sort_keys=True, separators=(",", ":"), ensure_ascii=False, allow_nan=False).encode()
    ).hexdigest()

class C2E2FreshG6RunAuthorityTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.decision = json.loads(DECISION.read_text())
        cls.token = json.loads(TOKEN.read_text())
        cls.registry = json.loads(AUTH_REGISTRY.read_text())
        cls.manifest = json.loads(MANIFEST.read_text())
        cls.envelope = json.loads(ENVELOPE.read_text())
        cls.pack = json.loads(PACK.read_text())
        cls.state = json.loads(STATE.read_text())
        cls.pointer = json.loads(POINTER.read_text())

    def test_operator_authority_is_exact_single_use_and_inactive(self):
        self.assertEqual(self.decision["operator_command"], "OVC APPROVE C2E2-G6-RUN-AUTH")
        self.assertEqual(self.decision["decision"], "AUTHORIZE_EXACT_RUN")
        self.assertEqual(self.decision["activation_effect"], "NONE")
        self.assertEqual(self.token["status"], "AUTHORIZED_UNCONSUMED")
        self.assertTrue(self.token["single_use"])
        self.assertTrue(self.token["reuse_prohibited"])
        self.assertFalse(self.token["consumed"])
        self.assertFalse(self.token["invalidated"])
        self.assertEqual(self.token["reserved_post_wp6_authority"], "DENIED_OPERATOR_REQUIRED")
        self.assertEqual(self.pointer["active_c2e"], "NONE")
        self.assertEqual(self.pointer["active_boundary_pack"], "NONE")
        self.assertEqual(self.state["authority"]["c2e_activation"], "DENIED")

    def test_exact_replacement_objects_are_mutually_bound(self):
        self.assertEqual(logical_hash(self.decision), self.decision["logical_sha256"])
        self.assertEqual(logical_hash(self.token), self.token["logical_sha256"])
        self.assertEqual(logical_hash(self.manifest), self.manifest["logical_sha256"])
        self.assertEqual(logical_hash(self.envelope), self.envelope["logical_sha256"])
        frozen_pack = freeze_pack(self.pack)
        self.assertEqual(frozen_pack["boundary_pack_id"], self.pack["boundary_pack_id"])
        self.assertEqual(frozen_pack["logical_sha256"], self.pack["logical_sha256"])
        self.assertEqual(self.token["run_manifest_logical_sha256"], self.manifest["logical_sha256"])
        self.assertEqual(self.token["resource_envelope_logical_sha256"], self.envelope["logical_sha256"])
        self.assertEqual(self.token["boundary_pack_logical_sha256"], self.pack["logical_sha256"])
        self.assertEqual(self.manifest["boundary_pack"]["logical_sha256"], self.pack["logical_sha256"])
        self.assertEqual(self.manifest["resource_envelope"]["logical_sha256"], self.envelope["logical_sha256"])

    def test_exact_observation_population_is_frozen_without_sampling(self):
        source = self.manifest["source_population"]
        self.assertEqual(source["materialisation_id"], "C2VNEXT.JUNE.REAL.OBSERVATION.MATERIALISATION.v1")
        self.assertEqual(source["materialisation_logical_sha256"], "de9689f65e5067a80d91265742f5ecc0214bf397d96ea037f4edeb6a251afe6d")
        self.assertEqual(source["logical_population_sha256"], "46f02ed89c9c4a3d4b3ef2046b7aa32489c5b63a526dbb8151896331d0ae896d")
        self.assertEqual(source["target_frame_count"], 4072)
        self.assertEqual(source["instrument_id"], "GBPUSD")
        self.assertEqual(source["sides"], ["ASK", "BID"])
        self.assertEqual(source["clock_ids"], ["UTC_15M"])
        self.assertEqual(source["parent_clock_ids"], ["2H_A_L"])
        self.assertTrue(self.manifest["execution_requirements"]["no_sampling_or_top_k_substitution"])
        self.assertEqual(self.manifest["execution_requirements"]["provider_intake"], "NONE")
        self.assertEqual(self.manifest["execution_requirements"]["validation_consumption"], "NONE")

    def test_history_is_append_only_and_old_token_never_reused(self):
        old = self.registry["historical_tokens"][0]
        self.assertEqual(old["token_id"], "C2E2.G6.TOKEN.81c25e8dae79234d60858274")
        self.assertEqual(old["status"], "INVALIDATED_UNCONSUMED_BY_OPERATOR_SUPERSESSION")
        self.assertTrue(old["invalidated"])
        self.assertFalse(old["consumed"])
        self.assertTrue(old["reuse_prohibited"])
        self.assertEqual(self.registry["tokens"][0]["token_id"], self.token["token_id"])
        self.assertEqual(self.pointer["old_run_token_id"], old["token_id"])
        self.assertEqual(self.pointer["old_run_token_status"], old["status"])
        self.assertIn(
            "C2E2-G6-RUN-AUTH.OPERATOR.AUTHORIZE_EXACT_RUN.20260809T145800+0100",
            self.pointer["operator_decision_history"],
        )

    def test_current_state_advances_only_to_authorized_not_started_wp6(self):
        self.assertEqual(self.pointer["status"], "APPROVED")
        self.assertEqual(self.pointer["wp6_execution"], "AUTHORIZED_NOT_STARTED")
        self.assertEqual(self.pointer["real_source_replay"], "AUTHORIZED_NOT_STARTED")
        self.assertEqual(self.state["status"], "APPROVED")
        self.assertEqual(self.state["authority"]["wp6_execution"], "AUTHORIZED_NOT_STARTED")
        self.assertEqual(self.state["authority"]["real_source_replay"], "AUTHORIZED_NOT_STARTED")
        self.assertEqual(self.pointer["replacement_run_token_id"], self.token["token_id"])
        self.assertEqual(self.pointer["replacement_boundary_pack_id"], self.pack["boundary_pack_id"])
        self.assertEqual(self.pointer["replacement_resource_envelope_id"], self.envelope["envelope_id"])

if __name__ == "__main__":
    unittest.main()
