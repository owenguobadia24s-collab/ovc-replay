import json
from pathlib import Path
import unittest

from ovc.opt_b.c2_vnext.integrated_shadow import (
    APPROVED_COMPONENTS,
    DENIED_AUTHORITIES,
    build_integrated_manifest,
    run_real_component_smoke,
    verify_replay_equivalence,
)

ROOT = Path(__file__).resolve().parents[1]
BASE = ROOT / "docs/releases/c2-anatomy-observation-redesign-v0-2/c2ar-wp11"
REGISTRY = ROOT / "registries/opt_b/c2/vnext/C2_INTEGRATED_SHADOW_PACKAGE_v1.jsonc"
STATE = ROOT / "registries/opt_b/c2/anatomy_redesign/OVC_C2AR_WP11_QA_REVIEW_STATE_v0_3.jsonc"
FIXTURE = ROOT / "fixtures/opt_b/c2/vnext/c2ar_wp5_5_canonical_smoke_v0_1.json"

class C2ARWP11IntegratedShadowTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.manifest = json.loads((BASE / "C2AR_WP11_INTEGRATED_MANIFEST.json").read_text())
        cls.registry = json.loads(REGISTRY.read_text())
        cls.state = json.loads(STATE.read_text())
        cls.fixture = json.loads(FIXTURE.read_text())

    def test_builder_is_deterministic_and_matches_materialized_manifest(self):
        first = build_integrated_manifest()
        second = build_integrated_manifest()
        self.assertEqual(first, second)
        self.assertEqual(first, self.manifest)
        self.assertEqual(first["package_sha256"], self.registry["package_sha256"])

    def test_exact_component_allowlist_has_no_unapproved_or_active_component(self):
        rows = self.manifest["components"]
        self.assertEqual(len(rows), 11)
        self.assertEqual(len({row["component"] for row in rows}), 11)
        self.assertEqual(tuple(rows), APPROVED_COMPONENTS)
        self.assertFalse(self.manifest["active"])
        self.assertFalse(self.manifest["canonical"])
        self.assertFalse(self.manifest["publication"])
        self.assertEqual(self.manifest["active_c2"], "UNCHANGED_READ_ONLY")
        self.assertIn("SELECTOR_ACTIVATION_OR_REPLACEMENT", DENIED_AUTHORITIES)

    def test_real_component_smoke_is_deterministic_and_authority_neutral(self):
        first = run_real_component_smoke(self.fixture)
        second = run_real_component_smoke(self.fixture)
        self.assertEqual(first, second)
        self.assertEqual(first["status"], "PASS")
        self.assertEqual(first["real_component_stages"], ["observation","horizon","level","container","relation"])
        self.assertEqual(first["fixture_bound_mocked_boundaries"], self.fixture["mocked_components"])
        self.assertFalse(first["active"])
        self.assertFalse(first["canonical"])
        self.assertFalse(first["topology_smoke"]["chronology"]["horizon_has_future_member"])

    def test_full_replay_evidence_is_reused_only_by_exact_blob_equivalence(self):
        receipt = json.loads((BASE / "C2AR_WP11_FULL_REPLAY_EQUIVALENCE_RECEIPT.json").read_text())
        verified = verify_replay_equivalence(receipt["verified_module_blobs"])
        self.assertEqual(verified["status"], "PASS")
        self.assertEqual(verified["logical_population_sha256"], "3f1089e3a4eefe94147c8c2f912e77899e4ed21fe8b3b8b85993e47bf7151ee7")
        self.assertEqual(receipt["claim"], "REUSE_ACCEPTED_FULL_REPLAY_EVIDENCE_NO_NEW_MARKET_REPLAY_CLAIM")

    def test_crosswalk_lifecycle_preserves_maintained_shadow_and_operator_trigger(self):
        crosswalk = json.loads((BASE / "C2AR_WP11_CROSSWALK_STATUS.json").read_text())
        self.assertEqual(crosswalk["state"], "MAINTAINED_SHADOW")
        self.assertEqual(crosswalk["mapping_policy"]["freeze_trigger"], "ACTIVATION_PLAN_APPROVED")
        self.assertFalse(crosswalk["automatic_freeze"])
        self.assertFalse(crosswalk["automatic_deprecation"])
        self.assertEqual(crosswalk["legacy_benchmark_mappings"]["status"], "DEFERRED")

    def test_negative_results_and_scope_warnings_remain_visible(self):
        negative = json.loads((BASE / "C2AR_WP11_NEGATIVE_RESULT_INDEX.json").read_text())
        self.assertEqual(negative["population"]["requested"], 33320)
        self.assertEqual(negative["population"]["computable"], 27996)
        self.assertEqual(len(negative["candidate_warnings"]), 2)
        self.assertTrue(all(not row["fallback_used"] for row in negative["candidate_warnings"]))
        self.assertTrue(negative["scope_limitations"]["all_14_zero_2h_a_l_matches"])
        self.assertFalse(negative["hidden_negative_results"])

    def test_activation_input_is_non_effective_and_reserved_authority_remains_denied(self):
        activation = json.loads((BASE / "C2AR_WP11_ACTIVATION_PLAN_INPUT.json").read_text())
        self.assertFalse(activation["automatic_activation"])
        self.assertEqual(activation["authority_effect"], "NONE")
        self.assertEqual(activation["status"], "PREPARED_NON_EFFECTIVE")
        self.assertEqual(set(self.manifest["denied_authorities"]), set(DENIED_AUTHORITIES))

    def test_qa_and_state_are_predecision_and_auto_ratifable_only_after_assurance(self):
        qa = json.loads((BASE / "C2AR_WP11_QA_PACKET.json").read_text())
        self.assertEqual(qa["status"], "QA_REVIEW")
        self.assertEqual(qa["blocking_warnings"], [])
        self.assertEqual(qa["reserved_authority_delta"], "NONE")
        self.assertEqual(self.state["status"], "QA_REVIEW")
        self.assertEqual(self.state["authority_required"], "AUTO_IF_NO_RESERVED_DELTA")
        self.assertEqual(self.state["authority"]["active_c2"], "UNCHANGED_READ_ONLY")
        self.assertEqual(self.state["blockers"], [])

if __name__ == "__main__":
    unittest.main()
