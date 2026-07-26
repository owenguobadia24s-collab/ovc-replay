from __future__ import annotations

import unittest
from pathlib import Path

import ovc
from ovc.opt_a import AUTHORITY_STATE as OPT_A_STATE
from ovc.opt_b.c1 import AUTHORITY_STATE as C1_STATE
from ovc.opt_b.c2 import AUTHORITY_STATE as C2_STATE


ROOT = Path(__file__).resolve().parents[1]
ALLOWED_REPOSITORY_STATES = {
    "state: V2_FOUNDATION_NO_MARKET_AUTHORITY",
    "state: V2_FOUNDATION_RESET_COMPLETE_NO_MARKET_AUTHORITY",
    "state: V2_OBSERVATION_CONSTRUCTION_REVIEW_PASS_NO_MARKET_AUTHORITY",
    "state: V2_ROLE_RELEASE_FREEZE_PASS_NO_MARKET_AUTHORITY",
    "state: V2_REMOTE_PUBLICATION_REVIEW_PASS_NO_MARKET_AUTHORITY",
    "state: V2_SELECTOR_SET_ACTIVE_NO_DOWNSTREAM_MARKET_AUTHORITY",
    "state: C1_WP1_BOUNDARY_PASS_NO_C1_MARKET_AUTHORITY",
    "state: C1_WP2_CONTRACT_FREEZE_PASS_NO_C1_MARKET_AUTHORITY",
    "state: C1_WP3_REFERENCE_ENGINE_PASS_NO_C1_MARKET_AUTHORITY",
    "state: C1_B1_G0_PASS_WP4_REPLAY_AUTHORISED_NO_C1_RELEASE_AUTHORITY",
    "state: C1_WP4_REPLAY_QA_PASS_LOCAL_CANDIDATE_NO_PUBLICATION_AUTHORITY",
    "state: C1_B1_G1_PASS_EXACT_CANDIDATE_FREEZE_AUTHORISED_NO_PUBLICATION_AUTHORITY",
    "state: C1_B1_G2_PASS_PUBLICATION_READY_WP5_AUTHORISED_NO_SELECTOR",
    "state: C1_WP5_PASS_REMOTE_VERIFIED_PENDING_B1_G4_NO_SELECTOR",
    "state: C1_B1_G5_PASS_SHADOW_ACTIVE_C2_DENIED",
    "state: C1_B1_G5_SHADOW_C2_G5_LOCAL_CANDIDATES_NO_SELECTOR",
}


class ActiveTreeFoundationTests(unittest.TestCase):
    def test_clean_namespaces_import(self) -> None:
        self.assertEqual(ovc.__version__, "0.2.0")
        self.assertEqual(OPT_A_STATE, "DESIGN_AND_FIXTURES_ONLY")
        self.assertEqual(C1_STATE, "B1_G5_SHADOW_SELECTED_C2_DENIED")
        self.assertEqual(C2_STATE, "DESIGN_AND_FIXTURES_ONLY")

    def test_legacy_engine_is_not_in_active_source_tree(self) -> None:
        self.assertFalse((ROOT / "src" / "ovc_opt_b").exists())
        self.assertTrue((ROOT / "legacy" / "quarantine" / "abcd-engine-v1-c0ad7ba").is_dir())

    def test_authority_registry_limits_activation_to_opt_a_and_c1_shadow(self) -> None:
        authority = (ROOT / "registries" / "authority" / "ACTIVE_AUTHORITY.yaml").read_text(encoding="utf-8")
        repository_state = next(line for line in authority.splitlines() if line.startswith("state: "))
        self.assertIn(repository_state, ALLOWED_REPOSITORY_STATES)
        self.assertIn("  opt_a: ACTIVE", authority)
        self.assertIn("  opt_b_c1: SHADOW", authority)
        for selector in ("opt_b_c2", "c2e", "c2_5", "c3", "opt_c", "opt_d"):
            self.assertIn(f"  {selector}: NONE", authority)
        self.assertIn("runtime_imports: DENIED", authority)
        self.assertIn("discovery_seed_eligibility: DENIED", authority)
        self.assertIn("market_replay: COMPLETE_WP4_PASS", authority)
        self.assertIn("release_freeze: COMPLETE_WP4F_PASS", authority)
        self.assertIn("r2_publication: COMPLETE_WP5_REMOTE_VERIFIED", authority)
        self.assertIn("selector: SHADOW", authority)
        self.assertIn("local_candidate_release: FROZEN_DISCOVERY_AND_DEVELOPMENT_LOCAL_ONLY", authority)
        self.assertIn("candidate_determinism: PASS_TWO_INDEPENDENT_BYTE_IDENTICAL_MATERIALIZATIONS", authority)
        self.assertIn("publication: NONE", authority)
        self.assertIn("activation: NONE", authority)
        self.assertIn("validation_consumption: LOCKED_UNCONSUMED", authority)


if __name__ == "__main__":
    unittest.main()
