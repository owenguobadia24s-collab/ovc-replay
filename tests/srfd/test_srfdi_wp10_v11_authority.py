from __future__ import annotations

import json
from pathlib import Path
import unittest

from ovc.opt_b.srfd.wp10_v10_interface import SCIENCE_IDENTITY_SHA256
from ovc.opt_b.srfd.wp10_v11_interface import binding_from_manifest

ROOT = Path(__file__).resolve().parents[2]
BASE = ROOT / "docs/releases/srfd-benchmark-v0-1/srfdi-june-auth-v1-1"
MANIFEST = BASE / "SRFD_JUNE_AUTHORITY_MANIFEST_CANDIDATE_v1_1.json"
TOKEN = BASE / "SRFD_JUNE_AUTHORITY_TOKEN_v1_1.json"
DECISION = BASE / "SRFD_JUNE_AUTHORITY_OPERATOR_DECISION_v1_1.json"
STATE = ROOT / "registries/implementation/srfd/OVC_SRFDI_STATE_v0_48_WP10_V11_READY.json"
POINTER = ROOT / "registries/implementation/srfd/CURRENT_STATE_POINTER.json"

class SRFDIWP10V11AuthorityTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.m = json.loads(MANIFEST.read_text())
        cls.t = json.loads(TOKEN.read_text())
        cls.d = json.loads(DECISION.read_text())
        cls.s = json.loads(STATE.read_text())
        cls.p = json.loads(POINTER.read_text())
        cls.b = binding_from_manifest(cls.m)

    def test_science_is_exactly_unchanged_and_binding_is_final_main(self):
        self.assertEqual(SCIENCE_IDENTITY_SHA256, self.b.science_identity_sha256)
        self.assertEqual("28e4f92f0c5de8f8bca5125ebcefa3247eb8c88abbc3af2ba9a30ef0680666dd", self.b.logical_hash)
        self.assertEqual("550d1250ca19060a6ec9aa8ba17ceb6aeceaabb2", self.b.implementation_commit)
        self.assertEqual("79f2878d8df9430100b73701a533ba70ee7b1e2ac9ab44a4cf1f1ac8c0eaef9e", self.b.execution_binding_sha256)
        self.assertEqual("abedad36f730c61c77f75a9950301d17949afc75659a81be414f8014841147c6", self.b.storage_binding_sha256)

    def test_source_artifacts_are_exact_and_provider_fetch_is_denied(self):
        self.assertEqual(6, len(self.m["accepted_source_artifacts"]))
        self.assertEqual("GOOGLE_DRIVE_ACCEPTED_ARTIFACTS_NO_PROVIDER_FETCH", self.m["retrieval"])
        self.assertEqual("DENIED", self.m["provider_fetch"])
        self.assertEqual(9420, self.m["frozen_counts"]["source_record_count"])
        self.assertEqual(8598, self.m["frozen_counts"]["eligible_record_count"])
        self.assertEqual(36, self.m["frozen_counts"]["comparability_domain_count"])
        self.assertEqual(1944, self.m["frozen_counts"]["family_configuration_count"])
        self.assertEqual(2020, self.m["frozen_counts"]["work_unit_count"])

    def test_pr571_identities_are_preserved_only_as_forbidden_history(self):
        supersession = self.m["supersession"]
        self.assertEqual("CLOSED_UNMERGED_UNUSED_DO_NOT_REUSE", supersession["disposition"])
        self.assertEqual("1526610575dcd22b066d494c022ba2f443bb099b4f521872c2984765481c58a6", supersession["pr571_run_binding_sha256"])
        self.assertEqual("SRFD.JUNE.AUTH.f80920b2b4d03e00add6621cdda4abdc761f5abf98dae6f072e643f4aaed7f04", supersession["pr571_token_id"])
        self.assertNotEqual(supersession["pr571_run_binding_sha256"], self.b.logical_hash)
        self.assertNotEqual(supersession["pr571_token_id"], self.t["token_id"])

    def test_token_is_fresh_single_use_and_unconsumed(self):
        self.assertEqual("SRFD.JUNE.AUTH.db73f9afda234d1084f135651cb53364030f7681c5429cf99e77270cb84a5c26", self.t["token_id"])
        self.assertEqual("AUTHORIZED_UNCONSUMED", self.t["state"])
        self.assertTrue(self.t["single_use"])
        self.assertEqual("ONE_EXACT_BOUND_RUN", self.t["run_cardinality"])
        self.assertEqual(self.b.logical_hash, self.t["run_binding_sha256"])
        self.assertEqual("DENIED", self.t["provider_fetch"])
        self.assertEqual("LOCKED_UNCONSUMED", self.t["validation_2025"])

    def test_authority_requires_exact_preflight_before_consumption(self):
        self.assertEqual("PASS_AUTHORIZE_ONE_EXACT_V11_RUN_AFTER_EXACT_PREFLIGHT", self.d["decision"])
        self.assertIn("EXACT_PREFLIGHT_MUST_PASS_BEFORE_TOKEN_CONSUMPTION", self.d["conditions"])
        self.assertIn("PR571_UNMERGED_IDENTITIES_MUST_NOT_BE_REUSED", self.d["conditions"])
        self.assertEqual("READY", self.s["status"])
        self.assertFalse(self.s["authority"]["fresh_authority_token_consumed"])
        self.assertEqual("RUN_EXACT_V11_PREFLIGHT_THEN_CONSUME_TOKEN_ON_PASS_AND_EXECUTE", self.s["next_action"])

    def test_current_pointer_has_no_scientific_promotion_and_stops_at_g11(self):
        self.assertEqual("READY", self.p["status"])
        self.assertEqual("SRFDI-WP10-v1.1", self.p["active_packet"])
        self.assertEqual("AUTHORIZED_UNCONSUMED", self.p["fresh_authority_token_state"])
        self.assertEqual("DENIED", self.p["provider_fetch"])
        self.assertEqual("LOCKED_UNCONSUMED", self.p["validation_2025"])
        self.assertEqual("NONE", self.p["scientific_promotion"])
        self.assertEqual("NONE", self.p["probability_risk_exposure_execution"])
        self.assertEqual("HARD_BLOCKER_OR_SRFDI_G11_OPERATOR_SCIENTIFIC_DISPOSITION", self.p["stop_at"])

if __name__ == "__main__":
    unittest.main()
