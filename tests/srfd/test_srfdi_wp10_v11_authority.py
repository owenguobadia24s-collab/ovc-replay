from __future__ import annotations

import json
from pathlib import Path
import unittest

from ovc.opt_b.srfd.wp10_v10_interface import SCIENCE_IDENTITY_SHA256
from ovc.opt_b.srfd.wp10_v11_interface import binding_from_manifest, mint_single_use_token

ROOT = Path(__file__).resolve().parents[2]
BASE = ROOT / "docs/releases/srfd-benchmark-v0-1/srfdi-june-auth-v1-1"
MANIFEST = BASE / "SRFD_JUNE_AUTHORITY_MANIFEST_CANDIDATE_v1_1.json"
TOKEN = BASE / "SRFD_JUNE_AUTHORITY_TOKEN_v1_1.json"
DECISION = BASE / "SRFD_JUNE_AUTHORITY_OPERATOR_DECISION_v1_1.json"
READY_STATE = ROOT / "registries/implementation/srfd/OVC_SRFDI_STATE_v0_48_WP10_V11_READY.json"
BLOCKED_STATE = ROOT / "registries/implementation/srfd/OVC_SRFDI_STATE_v0_49_WP10_V11_PREFLIGHT_ENV_BLOCKED.json"
POINTER = ROOT / "registries/implementation/srfd/CURRENT_STATE_POINTER.json"
BLOCKER = ROOT / "docs/releases/srfd-benchmark-v0-1/srfdi-wp10-v1-1/SRFDI_WP10_V11_PREFLIGHT_ENVIRONMENT_BLOCKER.json"


class SRFDIWP10V11AuthorityTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.m = json.loads(MANIFEST.read_text())
        cls.t = json.loads(TOKEN.read_text())
        cls.d = json.loads(DECISION.read_text())
        cls.ready = json.loads(READY_STATE.read_text())
        cls.blocked = json.loads(BLOCKED_STATE.read_text())
        cls.p = json.loads(POINTER.read_text())
        cls.blocker = json.loads(BLOCKER.read_text())
        cls.b = binding_from_manifest(cls.m)

    def test_science_is_exactly_unchanged_and_binding_is_latest_main(self):
        self.assertEqual(SCIENCE_IDENTITY_SHA256, self.b.science_identity_sha256)
        self.assertEqual("3029d32692f20e724d95ed0b63acf79b1709769f4b8603e9371acee50cd642b5", self.b.logical_hash)
        self.assertEqual("28a3679e0f5c2a242db3c2e0618c8966ed2e311b", self.b.implementation_commit)
        self.assertEqual("e510917cde9443eec2ad4333cde08e360b7c9a3685f7a8d1d33027c00a15b869", self.b.execution_binding_sha256)
        self.assertEqual("89e8fae3987ea733edcb49ab1c696a9a17cf283f8a9a53051e481d2b4b774948", self.b.storage_binding_sha256)
        self.assertFalse(self.m["main_churn_reconciliation"]["srfd_runtime_changed"])

    def test_source_artifacts_are_exact_and_provider_fetch_is_denied(self):
        self.assertEqual(6, len(self.m["accepted_source_artifacts"]))
        self.assertEqual("GOOGLE_DRIVE_ACCEPTED_ARTIFACTS_NO_PROVIDER_FETCH", self.m["retrieval"])
        self.assertEqual("DENIED", self.m["provider_fetch"])
        self.assertEqual(9420, self.m["frozen_counts"]["source_record_count"])
        self.assertEqual(8598, self.m["frozen_counts"]["eligible_record_count"])
        self.assertEqual(36, self.m["frozen_counts"]["comparability_domain_count"])
        self.assertEqual(1944, self.m["frozen_counts"]["family_configuration_count"])
        self.assertEqual(2020, self.m["frozen_counts"]["work_unit_count"])

    def test_stale_unmerged_authority_generations_are_not_reused(self):
        stale = {row["pr"]: row for row in self.m["superseded_unmerged_authority_generations"]}
        self.assertEqual({571, 574}, set(stale))
        for row in stale.values():
            self.assertEqual("CLOSED_UNMERGED_UNUSED_DO_NOT_REUSE", row["disposition"])
            self.assertNotEqual(row["run_binding_sha256"], self.b.logical_hash)
            self.assertNotEqual(row["token_id"], self.t["token_id"])

    def test_token_is_fresh_single_use_unconsumed_and_reconstructible(self):
        self.assertEqual("SRFD.JUNE.AUTH.7b52e77176fa43d246891ec61d3d0130afe8cb7b5e296f3a705dc83e7fe95b9f", self.t["token_id"])
        self.assertEqual("AUTHORIZED_UNCONSUMED", self.t["state"])
        self.assertTrue(self.t["single_use"])
        self.assertEqual("ONE_EXACT_BOUND_RUN", self.t["run_cardinality"])
        self.assertEqual(self.b.logical_hash, self.t["run_binding_sha256"])
        rebuilt = mint_single_use_token(self.b, operator_decision_id=self.d["decision_id"])
        self.assertEqual(self.t["token_id"], rebuilt["token_id"])
        self.assertEqual("DENIED", self.t["provider_fetch"])
        self.assertEqual("LOCKED_UNCONSUMED", self.t["validation_2025"])

    def test_authority_decision_required_exact_preflight_and_ready_history_is_preserved(self):
        self.assertEqual("PASS_AUTHORIZE_ONE_EXACT_V11_RUN_AFTER_EXACT_PREFLIGHT", self.d["decision"])
        self.assertIn("EXACT_PREFLIGHT_MUST_PASS_BEFORE_TOKEN_CONSUMPTION", self.d["conditions"])
        self.assertIn("PR574_STALE_BASE_IDENTITIES_MUST_NOT_BE_REUSED", self.d["conditions"])
        self.assertEqual("READY", self.ready["status"])
        self.assertFalse(self.ready["authority"]["fresh_authority_token_consumed"])
        self.assertEqual("RUN_EXACT_V11_PREFLIGHT_THEN_CONSUME_TOKEN_ON_PASS_AND_EXECUTE", self.ready["next_action"])
        self.assertEqual("BLOCKED", self.blocked["status"])
        self.assertFalse(self.blocked["authority"]["token_consumed"])
        self.assertEqual("EXECUTION_ENVIRONMENT_MISMATCH", self.blocked["reason_code"])

    def test_current_pointer_preserves_authority_but_stops_at_exact_preflight_blocker(self):
        self.assertEqual("BLOCKED", self.p["status"])
        self.assertEqual("SRFDI-G10", self.p["current_gate"])
        self.assertEqual("SRFDI-WP10-v1.1", self.p["active_packet"])
        self.assertEqual("AUTHORIZED_UNCONSUMED_BLOCKED_PREFLIGHT_ENVIRONMENT_DRIFT", self.p["fresh_authority_token_state"])
        self.assertFalse(self.p["fresh_authority_token_consumed"])
        self.assertEqual("EXECUTION_ENVIRONMENT_MISMATCH_DEPENDENCY_INVENTORY", self.p["failure_reason"])
        self.assertEqual(str(BLOCKER.relative_to(ROOT)).replace("\\", "/"), self.p["failure_receipt"])
        self.assertFalse(self.blocker["science_execution_started"])
        self.assertFalse(self.blocker["token_consumed"])
        self.assertEqual("DENIED", self.p["provider_fetch"])
        self.assertEqual("LOCKED_UNCONSUMED", self.p["validation_2025"])
        self.assertEqual("NONE", self.p["scientific_promotion"])
        self.assertEqual("NONE", self.p["probability_risk_exposure_execution"])
        self.assertEqual("HARD_BLOCKER", self.p["stop_at"])
        self.assertTrue(self.p["operator_decision_required"])


if __name__ == "__main__":
    unittest.main()
